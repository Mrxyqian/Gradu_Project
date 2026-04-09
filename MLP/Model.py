from __future__ import annotations

from typing import Optional, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F


class InputStem(nn.Module):
    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        input_dropout: float = 0.05,
    ):
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


class GatedResidualBlock(nn.Module):
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


class FeatureBackbone(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] = (256, 384, 256, 128),
        input_dropout: float = 0.05,
        dropout: float = 0.20,
    ):
        super().__init__()
        if not hidden_dims:
            raise ValueError("hidden_dims must contain at least one dimension")

        self.stem = InputStem(
            input_dim=input_dim,
            output_dim=hidden_dims[0],
            input_dropout=input_dropout,
        )

        blocks: list[nn.Module] = []
        prev_dim = hidden_dims[0]
        for hidden_dim in hidden_dims[1:]:
            blocks.append(GatedResidualBlock(prev_dim, hidden_dim, dropout=dropout))
            prev_dim = hidden_dim
        self.blocks = nn.Sequential(*blocks)
        self.final_norm = nn.LayerNorm(prev_dim)
        self.output_dim = prev_dim

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        outputs = self.stem(inputs)
        if len(self.blocks) > 0:
            outputs = self.blocks(outputs)
        return self.final_norm(outputs)


class ClassificationHead(nn.Module):
    def __init__(
        self,
        in_dim: int,
        hidden_dim: int = 160,
        dropout: float = 0.20,
        n_samples: int = 4,
    ):
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


class InsuranceMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] = (256, 384, 256, 128),
        head_hidden_dim: int = 160,
        input_dropout: float = 0.05,
        backbone_dropout: float = 0.20,
        head_dropout: float = 0.20,
        head_samples: int = 4,
    ):
        super().__init__()
        self.backbone = FeatureBackbone(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            input_dropout=input_dropout,
            dropout=backbone_dropout,
        )
        self.classifier = ClassificationHead(
            in_dim=self.backbone.output_dim,
            hidden_dim=head_hidden_dim,
            dropout=head_dropout,
            n_samples=head_samples,
        )
        self._init_weights()

    def _init_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, (nn.LayerNorm, nn.BatchNorm1d)):
                if module.weight is not None:
                    nn.init.ones_(module.weight)
                if module.bias is not None:
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
        focal_gamma: float = 2.0,
        focal_alpha: Optional[float] = 0.75,
        bce_weight: float = 1.0,
        focal_weight: float = 0.35,
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
        self.focal_gamma = float(focal_gamma)
        self.focal_alpha = None if focal_alpha is None else float(focal_alpha)
        self.bce_weight = float(bce_weight)
        self.focal_weight = float(focal_weight)
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

    def _smooth_targets(self, targets: torch.Tensor) -> torch.Tensor:
        smoothed_targets = targets.float()
        if self.label_smoothing > 0:
            smoothed_targets = (
                smoothed_targets * (1.0 - self.label_smoothing)
                + 0.5 * self.label_smoothing
            )
        return smoothed_targets

    def compute_loss(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        hard_targets = targets.float().view_as(logits)
        smoothed_targets = self._smooth_targets(hard_targets)

        bce = F.binary_cross_entropy_with_logits(
            logits,
            smoothed_targets,
            pos_weight=self.pos_weight_tensor.to(logits.device),
        )

        if self.focal_weight <= 0:
            return self.bce_weight * bce

        per_sample_bce = F.binary_cross_entropy_with_logits(
            logits,
            smoothed_targets,
            pos_weight=self.pos_weight_tensor.to(logits.device),
            reduction="none",
        )
        probs = torch.sigmoid(logits)
        p_t = probs * hard_targets + (1.0 - probs) * (1.0 - hard_targets)
        focal_factor = torch.pow((1.0 - p_t).clamp_min(1e-6), self.focal_gamma)

        if self.focal_alpha is None:
            alpha_factor = 1.0
        else:
            alpha_factor = hard_targets * self.focal_alpha + (1.0 - hard_targets) * (
                1.0 - self.focal_alpha
            )

        focal = (alpha_factor * focal_factor * per_sample_bce).mean()
        return self.bce_weight * bce + self.focal_weight * focal

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
            "bce_weight": float(self.bce_weight),
            "focal_weight": float(self.focal_weight),
            "focal_gamma": float(self.focal_gamma),
            "focal_alpha": float(self.focal_alpha) if self.focal_alpha is not None else -1.0,
        }


DualTaskLoss = ClaimClassificationLoss


class LegacyResidualBlock(nn.Module):
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


class LegacyFeatureBackbone(nn.Module):
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
            blocks.append(LegacyResidualBlock(prev_dim, hidden_dim, dropout=dropout))
            prev_dim = hidden_dim
        self.blocks = nn.Sequential(*blocks)
        self.output_dim = prev_dim

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        outputs = self.input_proj(inputs)
        if len(self.blocks) > 0:
            outputs = self.blocks(outputs)
        return outputs


class LegacyClassificationHead(nn.Module):
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


class LegacyInsuranceMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] = (256, 512, 256),
        head_hidden_dim: int = 128,
        backbone_dropout: float = 0.25,
        head_dropout: float = 0.10,
    ):
        super().__init__()
        self.backbone = LegacyFeatureBackbone(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            dropout=backbone_dropout,
        )
        self.classifier = LegacyClassificationHead(
            in_dim=self.backbone.output_dim,
            hidden_dim=head_hidden_dim,
            dropout=head_dropout,
        )

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


def _infer_current_hidden_dims(state_dict: dict[str, torch.Tensor]) -> tuple[int, ...]:
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


def _infer_legacy_hidden_dims(state_dict: dict[str, torch.Tensor]) -> tuple[int, ...]:
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


def build_model_from_checkpoint(
    checkpoint: dict,
    input_dim: int,
) -> nn.Module:
    state_dict = checkpoint["model"]

    if "backbone.stem.proj.weight" in state_dict:
        hidden_dims = _infer_current_hidden_dims(state_dict)
        head_hidden_dim = int(state_dict["classifier.trunk.0.weight"].shape[0])
        model = InsuranceMLP(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            head_hidden_dim=head_hidden_dim,
        )
    elif "backbone.input_proj.0.weight" in state_dict:
        hidden_dims = _infer_legacy_hidden_dims(state_dict)
        head_hidden_dim = int(state_dict["classifier.net.0.weight"].shape[0])
        model = LegacyInsuranceMLP(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            head_hidden_dim=head_hidden_dim,
        )
    else:
        raise RuntimeError("Unsupported checkpoint structure for inference loading")

    model.load_state_dict(state_dict)
    return model


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
    "InputStem",
    "GatedResidualBlock",
    "FeatureBackbone",
    "ClassificationHead",
    "InsuranceMLP",
    "LegacyResidualBlock",
    "LegacyFeatureBackbone",
    "LegacyClassificationHead",
    "LegacyInsuranceMLP",
    "ClaimClassificationLoss",
    "DualTaskLoss",
    "build_model_from_checkpoint",
    "predict",
]
