from __future__ import annotations

"""
Model.py
车险理赔预测 —— 单任务分类 MLP 网络结构定义

当前版本聚焦单任务分类：
  - 使用残差式共享主干提取表格特征
  - 仅输出理赔概率对应的分类 logit
  - 保留旧双任务权重加载所需的最小兼容逻辑
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
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

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
    def __init__(
        self,
        pos_weight: float = 4.10,
        label_smoothing: float = 0.0,
    ):
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


class _CompatibleInputStem(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, input_dropout: float = 0.02):
        super().__init__()
        self.net = nn.Sequential(
            nn.BatchNorm1d(input_dim),
            nn.Dropout(input_dropout),
            nn.Linear(input_dim, output_dim),
            nn.BatchNorm1d(output_dim),
            nn.ReLU(inplace=True),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.net(inputs)


class _CompatibleMLPBlock(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, dropout: float = 0.12):
        super().__init__()
        self.linear = nn.Linear(in_dim, out_dim)
        self.norm = nn.BatchNorm1d(out_dim)
        self.activation = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(dropout)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        outputs = self.linear(inputs)
        outputs = self.norm(outputs)
        outputs = self.activation(outputs)
        return self.dropout(outputs)


class _CompatibleFeatureBackbone(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int],
        input_dropout: float = 0.02,
        dropout: float = 0.12,
    ):
        super().__init__()
        self.stem = _CompatibleInputStem(
            input_dim=input_dim,
            output_dim=hidden_dims[0],
            input_dropout=input_dropout,
        )
        blocks: list[nn.Module] = []
        prev_dim = hidden_dims[0]
        for hidden_dim in hidden_dims[1:]:
            blocks.append(_CompatibleMLPBlock(prev_dim, hidden_dim, dropout=dropout))
            prev_dim = hidden_dim
        self.layers = nn.Sequential(*blocks)
        self.output_dim = prev_dim

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        outputs = self.stem(inputs)
        if len(self.layers) > 0:
            outputs = self.layers(outputs)
        return outputs


class _CompatibleClassificationHead(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int = 96, dropout: float = 0.10, n_samples: int = 1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(inplace=True),
        )
        self.dropouts = nn.ModuleList(
            [nn.Dropout(dropout) for _ in range(max(int(n_samples), 1))]
        )
        self.output = nn.Linear(hidden_dim, 1)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        features = self.net(features)
        logits = [self.output(dropout(features)) for dropout in self.dropouts]
        return torch.stack(logits, dim=0).mean(dim=0).squeeze(-1)


class _CompatibleSimpleMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int],
        head_hidden_dim: int,
        input_dropout: float,
        backbone_dropout: float,
        head_dropout: float,
        head_samples: int,
    ):
        super().__init__()
        self.backbone = _CompatibleFeatureBackbone(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            input_dropout=input_dropout,
            dropout=backbone_dropout,
        )
        self.classifier = _CompatibleClassificationHead(
            in_dim=self.backbone.output_dim,
            hidden_dim=head_hidden_dim,
            dropout=head_dropout,
            n_samples=head_samples,
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.backbone(inputs))


class _CompatibleAdvancedInputStem(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, input_dropout: float = 0.05):
        super().__init__()
        self.input_norm = nn.BatchNorm1d(input_dim)
        self.input_dropout = nn.Dropout(input_dropout)
        self.proj = nn.Linear(input_dim, output_dim)
        self.proj_norm = nn.LayerNorm(output_dim)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        outputs = self.input_norm(inputs)
        outputs = self.input_dropout(outputs)
        outputs = self.proj(outputs)
        outputs = self.proj_norm(outputs)
        return F.silu(outputs)


class _CompatibleAdvancedBlock(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, dropout: float = 0.20):
        super().__init__()
        hidden_dim = max(out_dim, in_dim)
        self.pre_norm = nn.LayerNorm(in_dim)
        self.gate_proj = nn.Linear(in_dim, hidden_dim * 2)
        self.out_proj = nn.Linear(hidden_dim, out_dim)
        self.dropout = nn.Dropout(dropout)
        self.shortcut = (
            nn.Linear(in_dim, out_dim, bias=False) if in_dim != out_dim else nn.Identity()
        )
        self.out_norm = nn.LayerNorm(out_dim)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        residual = self.shortcut(inputs)
        outputs = self.pre_norm(inputs)
        values, gates = self.gate_proj(outputs).chunk(2, dim=-1)
        outputs = F.silu(values) * torch.sigmoid(gates)
        outputs = self.dropout(outputs)
        outputs = self.out_proj(outputs)
        outputs = self.dropout(outputs)
        outputs = self.out_norm(outputs + residual)
        return F.silu(outputs)


class _CompatibleAdvancedBackbone(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int],
        input_dropout: float = 0.05,
        dropout: float = 0.20,
    ):
        super().__init__()
        self.stem = _CompatibleAdvancedInputStem(
            input_dim=input_dim,
            output_dim=hidden_dims[0],
            input_dropout=input_dropout,
        )
        blocks: list[nn.Module] = []
        prev_dim = hidden_dims[0]
        for hidden_dim in hidden_dims[1:]:
            blocks.append(_CompatibleAdvancedBlock(prev_dim, hidden_dim, dropout=dropout))
            prev_dim = hidden_dim
        self.blocks = nn.Sequential(*blocks)
        self.final_norm = nn.LayerNorm(prev_dim)
        self.output_dim = prev_dim

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        outputs = self.stem(inputs)
        if len(self.blocks) > 0:
            outputs = self.blocks(outputs)
        return self.final_norm(outputs)


class _CompatibleAdvancedHead(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int = 160, dropout: float = 0.20, n_samples: int = 4):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
        )
        self.dropouts = nn.ModuleList(
            [nn.Dropout(dropout) for _ in range(max(int(n_samples), 1))]
        )
        self.output = nn.Linear(hidden_dim, 1)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        features = self.trunk(features)
        logits = [self.output(dropout(features)) for dropout in self.dropouts]
        return torch.stack(logits, dim=0).mean(dim=0).squeeze(-1)


class _CompatibleAdvancedMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int],
        head_hidden_dim: int,
        input_dropout: float,
        backbone_dropout: float,
        head_dropout: float,
        head_samples: int,
    ):
        super().__init__()
        self.backbone = _CompatibleAdvancedBackbone(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            input_dropout=input_dropout,
            dropout=backbone_dropout,
        )
        self.classifier = _CompatibleAdvancedHead(
            in_dim=self.backbone.output_dim,
            hidden_dim=head_hidden_dim,
            dropout=head_dropout,
            n_samples=head_samples,
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.backbone(inputs))


def _as_tuple(value: Any, fallback: tuple[int, ...]) -> tuple[int, ...]:
    if value is None:
        return fallback
    return tuple(int(item) for item in value)


def _infer_residual_backbone_hidden_dims(state_dict: dict[str, torch.Tensor]) -> tuple[int, ...]:
    hidden_dims = [int(state_dict["backbone.input_proj.0.weight"].shape[0])]
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


def _infer_simple_hidden_dims(state_dict: dict[str, torch.Tensor]) -> tuple[int, ...]:
    hidden_dims = [int(state_dict["backbone.stem.net.2.weight"].shape[0])]
    layer_indices = sorted(
        {
            int(key.split(".")[2])
            for key in state_dict
            if key.startswith("backbone.layers.") and key.endswith("linear.weight")
        }
    )
    for index in layer_indices:
        hidden_dims.append(int(state_dict[f"backbone.layers.{index}.linear.weight"].shape[0]))
    return tuple(hidden_dims)


def _infer_advanced_hidden_dims(state_dict: dict[str, torch.Tensor]) -> tuple[int, ...]:
    hidden_dims = [int(state_dict["backbone.stem.proj.weight"].shape[0])]
    block_indices = sorted(
        {
            int(key.split(".")[2])
            for key in state_dict
            if key.startswith("backbone.blocks.") and key.endswith("out_proj.weight")
        }
    )
    for index in block_indices:
        hidden_dims.append(int(state_dict[f"backbone.blocks.{index}.out_proj.weight"].shape[0]))
    return tuple(hidden_dims)


def build_model_from_checkpoint(checkpoint: dict, input_dim: int) -> nn.Module:
    state_dict = checkpoint["model"]
    model_config = checkpoint.get("model_config") or {}

    if "backbone.input_proj.0.weight" in state_dict and (
        "clf_head.net.0.weight" in state_dict or "reg_head.net.0.weight" in state_dict
    ):
        hidden_dims = _as_tuple(
            model_config.get("hidden_dims"),
            _infer_residual_backbone_hidden_dims(state_dict),
        )
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
        filtered_state_dict = {
            key: value
            for key, value in state_dict.items()
            if not key.startswith("reg_head.")
        }
        model.load_state_dict(filtered_state_dict, strict=False)
        return model

    if "backbone.input_proj.0.weight" in state_dict and "classifier.net.0.weight" in state_dict:
        remapped_state_dict = {}
        for key, value in state_dict.items():
            if key.startswith("classifier."):
                remapped_state_dict[key.replace("classifier.", "clf_head.", 1)] = value
            else:
                remapped_state_dict[key] = value
        hidden_dims = _as_tuple(
            model_config.get("hidden_dims"),
            _infer_residual_backbone_hidden_dims(remapped_state_dict),
        )
        head_hidden_dim = int(
            model_config.get("head_hidden_dim", remapped_state_dict["clf_head.net.0.weight"].shape[0])
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
        model.load_state_dict(remapped_state_dict, strict=False)
        return model

    if "backbone.stem.net.2.weight" in state_dict:
        hidden_dims = _as_tuple(
            model_config.get("hidden_dims"),
            _infer_simple_hidden_dims(state_dict),
        )
        head_hidden_dim = int(
            model_config.get("head_hidden_dim", state_dict["classifier.net.0.weight"].shape[0])
        )
        model = _CompatibleSimpleMLP(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            head_hidden_dim=head_hidden_dim,
            input_dropout=float(model_config.get("input_dropout", 0.02)),
            backbone_dropout=float(model_config.get("backbone_dropout", 0.12)),
            head_dropout=float(model_config.get("head_dropout", 0.10)),
            head_samples=int(model_config.get("head_samples", 1)),
        )
        model.load_state_dict(state_dict)
        return model

    if "backbone.stem.proj.weight" in state_dict:
        hidden_dims = _as_tuple(
            model_config.get("hidden_dims"),
            _infer_advanced_hidden_dims(state_dict),
        )
        head_hidden_dim = int(
            model_config.get("head_hidden_dim", state_dict["classifier.trunk.0.weight"].shape[0])
        )
        model = _CompatibleAdvancedMLP(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            head_hidden_dim=head_hidden_dim,
            input_dropout=float(model_config.get("input_dropout", 0.05)),
            backbone_dropout=float(model_config.get("backbone_dropout", 0.20)),
            head_dropout=float(model_config.get("head_dropout", 0.20)),
            head_samples=int(model_config.get("head_samples", 4)),
        )
        model.load_state_dict(state_dict)
        return model

    raise RuntimeError("Unsupported checkpoint structure for inference loading")


@torch.no_grad()
def predict(
    model: nn.Module,
    x: torch.Tensor,
    threshold: float = 0.5,
    device: str = "cpu",
) -> dict[str, torch.Tensor]:
    model.eval()
    features = x.to(device)
    logits = model(features)
    claim_prob = torch.sigmoid(logits).cpu()
    claim_flag = (claim_prob >= threshold).long()
    return {
        "claim_prob": claim_prob.numpy(),
        "claim_flag": claim_flag.numpy(),
    }


__all__ = [
    "ResidualBlock",
    "SharedBackbone",
    "ClassificationHead",
    "InsuranceMLP",
    "ClaimClassificationLoss",
    "build_model_from_checkpoint",
    "predict",
]
