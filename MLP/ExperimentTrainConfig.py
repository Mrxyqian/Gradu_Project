from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_PATH = BASE_DIR / "DataSet" / "Motor vehicle insurance data.csv"
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs"


@dataclass
class PathConfig:
    csv_path: str = str(DEFAULT_DATASET_PATH)
    output_dir: str = str(DEFAULT_OUTPUT_DIR)
    scaler_path: str = str(DEFAULT_OUTPUT_DIR / "scaler.pkl")
    reference_path: str = str(DEFAULT_OUTPUT_DIR / "preprocess_reference.pkl")
    best_model_path: str = str(DEFAULT_OUTPUT_DIR / "best_model.pth")
    last_model_path: str = str(DEFAULT_OUTPUT_DIR / "last_model.pth")
    log_dir: str = str(DEFAULT_OUTPUT_DIR / "runs")

    def __post_init__(self) -> None:
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)


@dataclass
class DataConfig:
    val_ratio: float = 0.15
    test_ratio: float = 0.10
    random_seed: int = 42
    batch_size: int = 128
    num_workers: int = 0
    balanced_sampling: bool = False
    sampler_alpha: float = 0.75


@dataclass
class ModelConfig:
    input_dim: int = -1
    hidden_dims: tuple[int, ...] = (256, 512, 512, 256, 256)
    head_hidden_dim: int = 64
    input_dropout: float = 0.0
    backbone_dropout: float = 0.25
    head_dropout: float = 0.15
    head_samples: int = 1


@dataclass
class LossConfig:
    pos_weight: float = 4.10
    label_smoothing: float = 0.0


@dataclass
class OptimizerConfig:
    optimizer: str = "adamw"
    lr: float = 2e-4
    weight_decay: float = 7e-5
    beta1: float = 0.9
    beta2: float = 0.999
    eps: float = 1e-8
    momentum: float = 0.9
    nesterov: bool = True


@dataclass
class SchedulerConfig:
    scheduler: str = "cosine_warmup"
    warmup_epochs: int = 5
    min_lr: float = 1e-6
    plateau_factor: float = 0.5
    plateau_patience: int = 5
    plateau_min_lr: float = 1e-6
    step_size: int = 10
    gamma: float = 0.5


@dataclass
class TrainSectionConfig:
    num_epochs: int = 100
    early_stop: bool = True
    patience: int = 20
    min_delta: float = 1e-4
    early_stop_metric: str = "auc"
    use_amp: bool = True
    grad_clip: float = 1.0
    resume_from: str = ""
    log_interval: int = 100
    save_every_epoch: bool = False
    clf_threshold: float = 0.5
    auto_threshold: bool = True
    threshold_metric: str = "f1"
    threshold_beta: float = 1.3


@dataclass
class Config:
    path: PathConfig = field(default_factory=PathConfig)
    data: DataConfig = field(default_factory=DataConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    loss: LossConfig = field(default_factory=LossConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    train: TrainSectionConfig = field(default_factory=TrainSectionConfig)

    def summary(self) -> None:
        print("=" * 60)
        print("         Vehicle Claim Classification Experiment Config")
        print("=" * 60)
        print(json.dumps(dataclasses.asdict(self), indent=2, ensure_ascii=False))
        print("=" * 60)


__all__ = [
    "BASE_DIR",
    "DEFAULT_DATASET_PATH",
    "DEFAULT_OUTPUT_DIR",
    "PathConfig",
    "DataConfig",
    "ModelConfig",
    "LossConfig",
    "OptimizerConfig",
    "SchedulerConfig",
    "TrainSectionConfig",
    "Config",
]
