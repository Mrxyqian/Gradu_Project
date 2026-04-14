from __future__ import annotations

"""
AblationModel.py

Independent model definition for ablation experiments.
It keeps the original residual MLP as the default behavior, while exposing
architecture and loss toggles so experiments can be configured by parameters
instead of editing model internals repeatedly.
"""

from dataclasses import asdict, dataclass
from typing import Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F


SUPPORTED_NORM_TYPES = {"layernorm", "none"}
SUPPORTED_ACTIVATIONS = {"gelu", "relu", "silu"}
SUPPORTED_HEAD_TYPES = {"mlp", "linear"}
DEFAULT_ABLATION_HIDDEN_DIMS = (64, 128, 128, 64, 32)
DEFAULT_ABLATION_HEAD_HIDDEN_DIM = 16


@dataclass
class AblationModelOptions:
    use_residual: bool = True
    norm_type: str = "layernorm"
    activation: str = "gelu"
    head_type: str = "mlp"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class AblationLossOptions:
    use_pos_weight: bool = True
    pos_weight_strategy: str = "fixed"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalize_choice(value: str, *, supported: set[str], label: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in supported:
        raise ValueError(f"Unsupported {label}: {value}")
    return normalized


def _build_norm(norm_type: str, dim: int) -> nn.Module:
    normalized = _normalize_choice(norm_type, supported=SUPPORTED_NORM_TYPES, label="norm_type")
    if normalized == "layernorm":
        return nn.LayerNorm(dim)
    return nn.Identity()


def _build_activation(activation: str) -> nn.Module:
    normalized = _normalize_choice(
        activation,
        supported=SUPPORTED_ACTIVATIONS,
        label="activation",
    )
    if normalized == "gelu":
        return nn.GELU()
    if normalized == "relu":
        return nn.ReLU()
    return nn.SiLU()


class AblationBlock(nn.Module):
    def __init__(
        self,
        in_dim: int,
        hidden_dim: int,
        *,
        dropout: float = 0.25,
        options: AblationModelOptions | None = None,
    ):
        super().__init__()
        options = options or AblationModelOptions()
        self.use_residual = bool(options.use_residual)
        self.fc1 = nn.Linear(in_dim, hidden_dim)
        self.norm1 = _build_norm(options.norm_type, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.norm2 = _build_norm(options.norm_type, hidden_dim)
        self.drop = nn.Dropout(dropout)
        self.act1 = _build_activation(options.activation)
        self.act2 = _build_activation(options.activation)
        self.shortcut = (
            nn.Linear(in_dim, hidden_dim, bias=False)
            if self.use_residual and in_dim != hidden_dim
            else nn.Identity()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.fc1(x)
        out = self.norm1(out)
        out = self.act1(out)
        out = self.drop(out)
        out = self.fc2(out)
        out = self.norm2(out)
        if self.use_residual:
            out = out + self.shortcut(x)
        return self.act2(out)


class AblationBackbone(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] = DEFAULT_ABLATION_HIDDEN_DIMS,
        *,
        dropout: float = 0.25,
        options: AblationModelOptions | None = None,
    ):
        super().__init__()
        hidden_dims = tuple(int(dim) for dim in hidden_dims)
        if not hidden_dims:
            raise ValueError("hidden_dims must contain at least one dimension")

        options = options or AblationModelOptions()
        self.options = options
        first_dim = hidden_dims[0]
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, first_dim),
            _build_norm(options.norm_type, first_dim),
            _build_activation(options.activation),
            nn.Dropout(dropout),
        )

        blocks: list[nn.Module] = []
        prev_dim = first_dim
        for hidden_dim in hidden_dims[1:]:
            blocks.append(
                AblationBlock(
                    prev_dim,
                    hidden_dim,
                    dropout=dropout,
                    options=options,
                )
            )
            prev_dim = hidden_dim
        self.blocks = nn.Sequential(*blocks)
        self.output_dim = prev_dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_proj(x)
        if len(self.blocks) > 0:
            x = self.blocks(x)
        return x


class AblationClassificationHead(nn.Module):
    def __init__(
        self,
        in_dim: int,
        *,
        hidden_dim: int = 64,
        dropout: float = 0.15,
        options: AblationModelOptions | None = None,
    ):
        super().__init__()
        options = options or AblationModelOptions()
        head_type = _normalize_choice(
            options.head_type,
            supported=SUPPORTED_HEAD_TYPES,
            label="head_type",
        )
        if head_type == "linear":
            self.net = nn.Linear(in_dim, 1)
        else:
            self.net = nn.Sequential(
                nn.Linear(in_dim, hidden_dim),
                _build_norm(options.norm_type, hidden_dim),
                _build_activation(options.activation),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, 1),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.net(x)
        return logits.squeeze(-1)


class AblationInsuranceMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] = DEFAULT_ABLATION_HIDDEN_DIMS,
        head_hidden_dim: int = DEFAULT_ABLATION_HEAD_HIDDEN_DIM,
        input_dropout: float = 0.0,
        backbone_dropout: float = 0.25,
        head_dropout: float = 0.15,
        head_samples: int = 1,
        options: AblationModelOptions | None = None,
    ):
        super().__init__()
        self.options = options or AblationModelOptions()
        self.input_dropout = (
            nn.Dropout(float(input_dropout)) if input_dropout > 0 else nn.Identity()
        )
        self.backbone = AblationBackbone(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            dropout=backbone_dropout,
            options=self.options,
        )
        self.clf_head = AblationClassificationHead(
            self.backbone.output_dim,
            hidden_dim=head_hidden_dim,
            dropout=head_dropout,
            options=self.options,
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


class AblationClaimClassificationLoss(nn.Module):
    def __init__(
        self,
        pos_weight: float = 4.10,
        label_smoothing: float = 0.0,
        *,
        options: AblationLossOptions | None = None,
    ):
        super().__init__()
        self.options = options or AblationLossOptions()
        effective_pos_weight = float(pos_weight) if self.options.use_pos_weight else 1.0
        self.register_buffer(
            "pos_weight_tensor",
            torch.tensor([effective_pos_weight], dtype=torch.float32),
        )
        self.label_smoothing = float(label_smoothing)

    def set_pos_weight(self, pos_weight: float) -> None:
        effective_pos_weight = float(pos_weight) if self.options.use_pos_weight else 1.0
        self.pos_weight_tensor.data = torch.tensor(
            [effective_pos_weight],
            dtype=torch.float32,
            device=self.pos_weight_tensor.device,
        )

    def _smooth_targets(self, targets: torch.Tensor) -> torch.Tensor:
        if self.label_smoothing <= 0:
            return targets
        return targets * (1.0 - self.label_smoothing) + 0.5 * self.label_smoothing

    def forward(
        self,
        clf_logit: torch.Tensor,
        y_clf: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        y_clf = y_clf.float().view_as(clf_logit)
        target = self._smooth_targets(y_clf)
        clf_loss = F.binary_cross_entropy_with_logits(
            clf_logit,
            target,
            pos_weight=self.pos_weight_tensor.to(clf_logit.device),
        )
        return clf_loss, clf_loss

    def get_loss_config(self) -> dict[str, object]:
        return {
            "pos_weight": float(self.pos_weight_tensor.item()),
            "label_smoothing": float(self.label_smoothing),
            "use_pos_weight": bool(self.options.use_pos_weight),
            "pos_weight_strategy": str(self.options.pos_weight_strategy),
        }


__all__ = [
    "AblationBlock",
    "AblationBackbone",
    "AblationClassificationHead",
    "AblationClaimClassificationLoss",
    "AblationInsuranceMLP",
    "AblationLossOptions",
    "AblationModelOptions",
    "DEFAULT_ABLATION_HEAD_HIDDEN_DIM",
    "DEFAULT_ABLATION_HIDDEN_DIMS",
    "SUPPORTED_ACTIVATIONS",
    "SUPPORTED_HEAD_TYPES",
    "SUPPORTED_NORM_TYPES",
]
