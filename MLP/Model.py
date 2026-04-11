from __future__ import annotations

"""
Model.py
车险理赔预测分类模型定义。

当前项目仅保留单任务二分类结构：
1. 共享残差式 MLP 主干
2. 单一分类头输出理赔概率对应的 logit
3. 推理加载仅支持当前版本 checkpoint 结构
"""

from typing import Any, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int, dropout: float = 0.25):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden_dim)
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.drop = nn.Dropout(dropout)
        self.act = nn.GELU()
        self.shortcut = (
            nn.Linear(in_dim, hidden_dim, bias=False)
            if in_dim != hidden_dim
            else nn.Identity()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.shortcut(x)
        out = self.act(self.norm1(self.fc1(x)))
        out = self.drop(out)
        out = self.norm2(self.fc2(out))
        return self.act(out + residual)


class SharedBackbone(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] = (256, 512, 512, 256, 256),
        dropout: float = 0.25,
    ):
        super().__init__()
        hidden_dims = tuple(int(dim) for dim in hidden_dims)
        if not hidden_dims:
            raise ValueError("hidden_dims must contain at least one dimension")

        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dims[0]),
            nn.LayerNorm(hidden_dims[0]),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        blocks: list[nn.Module] = []
        prev_dim = hidden_dims[0]
        for hidden_dim in hidden_dims[1:]:
            blocks.append(ResidualBlock(prev_dim, hidden_dim, dropout=dropout))
            prev_dim = hidden_dim
        self.blocks = nn.Sequential(*blocks)
        self.output_dim = prev_dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_proj(x)
        if len(self.blocks) > 0:
            x = self.blocks(x)
        return x


class ClassificationHead(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int = 64, dropout: float = 0.15):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


class InsuranceMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] = (256, 512, 512, 256, 256),
        head_hidden_dim: int = 64,
        input_dropout: float = 0.0,
        backbone_dropout: float = 0.25,
        head_dropout: float = 0.15,
        head_samples: int = 1,
    ):
        super().__init__()
        self.input_dropout = nn.Dropout(float(input_dropout)) if input_dropout > 0 else nn.Identity()
        self.backbone = SharedBackbone(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            dropout=backbone_dropout,
        )
        self.clf_head = ClassificationHead(
            self.backbone.output_dim,
            hidden_dim=head_hidden_dim,
            dropout=head_dropout,
        )
        self.head_samples = max(int(head_samples), 1)
        self._init_weights()

    def _init_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, nonlinearity="relu")
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_dropout(x)
        return self.backbone(x)

    def forward_logits(self, x: torch.Tensor) -> torch.Tensor:
        shared = self.forward_features(x)
        if self.head_samples <= 1:
            return self.clf_head(shared)
        logits = [self.clf_head(shared) for _ in range(self.head_samples)]
        return torch.stack(logits, dim=0).mean(dim=0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.forward_logits(x)


class ClaimClassificationLoss(nn.Module):
    def __init__(self, pos_weight: float = 4.10, label_smoothing: float = 0.0):
        super().__init__()
        self.register_buffer(
            "pos_weight_tensor",
            torch.tensor([float(pos_weight)], dtype=torch.float32),
        )
        self.label_smoothing = float(label_smoothing)

    def set_pos_weight(self, pos_weight: float) -> None:
        self.pos_weight_tensor.data = torch.tensor(
            [float(pos_weight)],
            dtype=torch.float32,
            device=self.pos_weight_tensor.device,
        )

    def _smooth_targets(self, targets: torch.Tensor) -> torch.Tensor:
        if self.label_smoothing <= 0:
            return targets
        return targets * (1.0 - self.label_smoothing) + 0.5 * self.label_smoothing

    def forward(self, clf_logit: torch.Tensor, y_clf: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        y_clf = y_clf.float().view_as(clf_logit)
        target = self._smooth_targets(y_clf)
        clf_loss = F.binary_cross_entropy_with_logits(
            clf_logit,
            target,
            pos_weight=self.pos_weight_tensor.to(clf_logit.device),
        )
        return clf_loss, clf_loss

    def get_loss_config(self) -> dict[str, float]:
        return {
            "pos_weight": float(self.pos_weight_tensor.item()),
            "label_smoothing": float(self.label_smoothing),
        }


def _resolve_hidden_dims(model_config: dict[str, Any], state_dict: dict[str, torch.Tensor]) -> tuple[int, ...]:
    configured = model_config.get("hidden_dims")
    if configured:
        return tuple(int(item) for item in configured)
    return _infer_hidden_dims_from_state_dict(state_dict)


def _infer_hidden_dims_from_state_dict(state_dict: dict[str, torch.Tensor]) -> tuple[int, ...]:
    input_proj_key = "backbone.input_proj.0.weight"
    if input_proj_key not in state_dict:
        raise RuntimeError(f"Unsupported checkpoint structure: missing '{input_proj_key}'")

    hidden_dims = [int(state_dict[input_proj_key].shape[0])]
    block_indices = sorted(
        {
            int(key.split(".")[2])
            for key in state_dict
            if key.startswith("backbone.blocks.") and key.endswith("fc1.weight")
        }
    )
    for index in block_indices:
        hidden_dims.append(int(state_dict[f"backbone.blocks.{index}.fc1.weight"].shape[0]))
    return tuple(hidden_dims)


def build_model_from_checkpoint(checkpoint: dict[str, Any], input_dim: int) -> InsuranceMLP:
    state_dict = checkpoint.get("model")
    if not isinstance(state_dict, dict):
        raise RuntimeError("Checkpoint is missing a valid 'model' state_dict")

    required_keys = {
        "backbone.input_proj.0.weight",
        "clf_head.net.0.weight",
    }
    missing_keys = [key for key in required_keys if key not in state_dict]
    if missing_keys:
        raise RuntimeError(
            "Unsupported checkpoint structure for inference loading: "
            + ", ".join(missing_keys)
        )

    model_config = checkpoint.get("model_config") or {}
    hidden_dims = _resolve_hidden_dims(model_config, state_dict)
    head_hidden_dim = int(
        model_config.get("head_hidden_dim", state_dict["clf_head.net.0.weight"].shape[0])
    )
    model = InsuranceMLP(
        input_dim=input_dim,
        hidden_dims=hidden_dims,
        head_hidden_dim=head_hidden_dim,
        input_dropout=float(model_config.get("input_dropout", 0.0)),
        backbone_dropout=float(model_config.get("backbone_dropout", 0.25)),
        head_dropout=float(model_config.get("head_dropout", 0.15)),
        head_samples=int(model_config.get("head_samples", 1)),
    )
    model.load_state_dict(state_dict)
    return model


__all__ = [
    "ResidualBlock",
    "SharedBackbone",
    "ClassificationHead",
    "InsuranceMLP",
    "ClaimClassificationLoss",
    "build_model_from_checkpoint",
]
