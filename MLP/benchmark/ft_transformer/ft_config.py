from __future__ import annotations

"""
FT-Transformer 训练配置

复用与 MLP 相同的数据管线配置（DataConfig / LossConfig / OptimizerConfig / SchedulerConfig
直接复制自 TrainConfig，确保对比公平。新增 FTModelConfig 段存放 Transformer 专属参数。
"""

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parents[2]  # MLP/
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "ft_transformer"
DEFAULT_TRAIN_DATA_CSV_PATH = BASE_DIR / "DataSet" / "train_data.csv"


@dataclass
class PathConfig:
    train_table: str = str(DEFAULT_TRAIN_DATA_CSV_PATH)
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
class FTModelConfig:
    d_token: int = 192
    n_layers: int = 3
    n_heads: int = 8
    attn_dropout: float = 0.15
    ff_dropout: float = 0.15
    ff_factor: float = 4.0 / 3.0


@dataclass
class LossConfig:
    pos_weight: float = 3.10
    label_smoothing: float = 0.05


@dataclass
class OptimizerConfig:
    optimizer: str = "adamw"
    lr: float = 1e-4
    weight_decay: float = 8e-3
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
    patience: int = 5
    min_delta: float = 5e-5
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
    threshold_min_recall: Optional[float] = 0.830


@dataclass
class FTConfig:
    path: PathConfig = field(default_factory=PathConfig)
    data: DataConfig = field(default_factory=DataConfig)
    model: FTModelConfig = field(default_factory=FTModelConfig)
    loss: LossConfig = field(default_factory=LossConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    train: TrainSectionConfig = field(default_factory=TrainSectionConfig)

    def summary(self) -> None:
        print("=" * 60)
        print("     FT-Transformer 车险理赔预测 —— 训练配置摘要")
        print("=" * 60)
        print(json.dumps(dataclasses.asdict(self), indent=2, ensure_ascii=False))
        print("=" * 60)
