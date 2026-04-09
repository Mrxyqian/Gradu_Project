from __future__ import annotations

from typing import Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, dropout: float = 0.25):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, out_dim)
        self.norm1 = nn.LayerNorm(out_dim)
        self.fc2 = nn.Linear(out_dim, out_dim)
        self.norm2 = nn.LayerNorm(out_dim)
        self.dropout = nn.Dropout(dropout)
        self.activation = nn.GELU()
        self.shortcut = (
            nn.Linear(in_dim, out_dim, bias=False) if in_dim != out_dim else nn.Identity()
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        residual = self.shortcut(inputs)
        outputs = self.activation(self.norm1(self.fc1(inputs)))
        outputs = self.dropout(outputs)
        outputs = self.norm2(self.fc2(outputs))
        return self.activation(outputs + residual)


class FeatureBackbone(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] = (256, 512, 256),
        dropout: float = 0.25,
    ):
        super().__init__()
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

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        outputs = self.input_proj(inputs)
        if len(self.blocks) > 0:
            outputs = self.blocks(outputs)
        return outputs


class ClassificationHead(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int = 128, dropout: float = 0.10):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.net(features).squeeze(-1)


class InsuranceMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] = (256, 512, 256),
        head_hidden_dim: int = 128,
        backbone_dropout: float = 0.25,
        head_dropout: float = 0.10,
    ):
        super().__init__()
        self.backbone = FeatureBackbone(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            dropout=backbone_dropout,
        )
        self.classifier = ClassificationHead(
            in_dim=self.backbone.output_dim,
            hidden_dim=head_hidden_dim,
            dropout=head_dropout,
        )
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

    def forward_features(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.backbone(inputs)

    def forward_logits(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.forward_features(inputs))

    def forward(
        self,
        inputs: torch.Tensor,
        return_dummy_regression: bool = True,
    ):
        logits = self.forward_logits(inputs)
        if return_dummy_regression:
            return logits, torch.zeros_like(logits)
        return logits


class ClaimClassificationLoss(nn.Module):
    def __init__(
        self,
        pos_weight: float = 1.0,
        label_smoothing: float = 0.0,
        init_log_var_clf: float = 0.0,
        init_log_var_reg: float = 0.0,
        w_clf: float = 1.0,
        w_reg: float = 0.0,
    ):
        super().__init__()
        self.register_buffer(
            "pos_weight_tensor",
            torch.tensor([float(pos_weight)], dtype=torch.float32),
        )
        self.label_smoothing = float(label_smoothing)
        self.init_log_var_clf = float(init_log_var_clf)
        self.init_log_var_reg = float(init_log_var_reg)
        self.w_clf = float(w_clf)
        self.w_reg = float(w_reg)

    def set_pos_weight(self, pos_weight: float) -> None:
        self.pos_weight_tensor.data = torch.tensor(
            [float(pos_weight)],
            dtype=torch.float32,
            device=self.pos_weight_tensor.device,
        )

    def compute_loss(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        smoothed_targets = targets.float()
        if self.label_smoothing > 0:
            smoothed_targets = (
                smoothed_targets * (1.0 - self.label_smoothing)
                + 0.5 * self.label_smoothing
            )
        return F.binary_cross_entropy_with_logits(
            logits,
            smoothed_targets,
            pos_weight=self.pos_weight_tensor.to(logits.device),
        )

    def forward(self, logits: torch.Tensor, *args):
        if len(args) == 1:
            targets = args[0]
        elif len(args) >= 3:
            targets = args[1]
        else:
            raise TypeError("ClaimClassificationLoss expects targets or legacy dual-task arguments")

        clf_loss = self.compute_loss(logits, targets)
        reg_loss = logits.new_tensor(0.0)
        total_loss = self.w_clf * clf_loss
        return total_loss, clf_loss, reg_loss

    def get_task_weights(self) -> dict[str, float]:
        return {
            "weight_clf": float(self.w_clf),
            "weight_reg": float(self.w_reg),
        }


DualTaskLoss = ClaimClassificationLoss


@torch.no_grad()
def predict(
    model: InsuranceMLP,
    x: torch.Tensor,
    threshold: float = 0.5,
    device: str = "cpu",
) -> dict[str, torch.Tensor]:
    model.eval()
    features = x.to(device)
    logits = model(features, return_dummy_regression=False)
    claim_prob = torch.sigmoid(logits).cpu()
    claim_flag = (claim_prob >= threshold).long()
    claim_amount = torch.zeros_like(claim_prob)
    return {
        "claim_prob": claim_prob.numpy(),
        "claim_flag": claim_flag.numpy(),
        "claim_amount": claim_amount.numpy(),
    }


__all__ = [
    "ResidualBlock",
    "FeatureBackbone",
    "ClassificationHead",
    "InsuranceMLP",
    "ClaimClassificationLoss",
    "DualTaskLoss",
    "predict",
]
