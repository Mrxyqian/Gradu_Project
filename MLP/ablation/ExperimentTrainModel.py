from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

if __package__ in (None, ""):
    CURRENT_DIR = Path(__file__).resolve().parent
    PARENT_DIR = CURRENT_DIR.parent
    if str(CURRENT_DIR) not in sys.path:
        sys.path.insert(0, str(CURRENT_DIR))
    if str(PARENT_DIR) not in sys.path:
        sys.path.insert(0, str(PARENT_DIR))

if __package__:
    from .. import TrainModel as system_train_model
    from .ExperimentDataLoader import build_dataloaders as build_csv_dataloaders
    from .ExperimentTrainConfig import Config
else:
    import TrainModel as system_train_model
    from ExperimentDataLoader import build_dataloaders as build_csv_dataloaders
    from ExperimentTrainConfig import Config


def _build_csv_loader_adapter(csv_path: str):
    def _adapter(
        table_name: str = "",
        batch_size: int = 128,
        val_ratio: float = 0.15,
        test_ratio: float = 0.10,
        random_seed: int = 42,
        scaler_save_path: str = "scaler.pkl",
        reference_save_path: str = "preprocess_reference.pkl",
        num_workers: int = 2,
        balanced_sampling: bool = False,
        sampler_alpha: float = 0.75,
    ):
        return build_csv_dataloaders(
            csv_path=csv_path,
            batch_size=batch_size,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            random_seed=random_seed,
            scaler_save_path=scaler_save_path,
            reference_save_path=reference_save_path,
            num_workers=num_workers,
            balanced_sampling=balanced_sampling,
            sampler_alpha=sampler_alpha,
        )

    return _adapter


def run_training(
    cfg: Config,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    original_loader = system_train_model.build_dataloaders
    original_table = getattr(cfg.path, "train_table", None)
    setattr(cfg.path, "train_table", cfg.path.csv_path)

    try:
        system_train_model.build_dataloaders = _build_csv_loader_adapter(cfg.path.csv_path)
        result = system_train_model.run_training(cfg, progress_callback=progress_callback)
    finally:
        system_train_model.build_dataloaders = original_loader
        if original_table is None:
            try:
                delattr(cfg.path, "train_table")
            except AttributeError:
                pass
        else:
            setattr(cfg.path, "train_table", original_table)

    artifacts = result.setdefault("artifacts", {})
    artifacts.pop("trainTable", None)
    artifacts["csvPath"] = cfg.path.csv_path
    return result


def train(cfg: Config):
    result = run_training(cfg)
    return result["model"], result["rawTestMetrics"], result["summary"]["finalThreshold"]


__all__ = ["run_training", "train"]
