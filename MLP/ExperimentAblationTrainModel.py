from __future__ import annotations

from typing import Any, Callable

if __package__:
    from . import AblationTrainModel as system_ablation_train_model
    from .AblationModel import AblationLossOptions, AblationModelOptions
    from .ExperimentDataLoader import build_dataloaders as build_csv_dataloaders
    from .ExperimentTrainConfig import Config
else:
    import AblationTrainModel as system_ablation_train_model
    from AblationModel import AblationLossOptions, AblationModelOptions
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


def run_ablation_training(
    cfg: Config,
    *,
    model_options: AblationModelOptions | None = None,
    loss_options: AblationLossOptions | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    original_loader = system_ablation_train_model.build_dataloaders
    original_table = getattr(cfg.path, "train_table", None)
    setattr(cfg.path, "train_table", cfg.path.csv_path)

    try:
        system_ablation_train_model.build_dataloaders = _build_csv_loader_adapter(cfg.path.csv_path)
        result = system_ablation_train_model.run_ablation_training(
            cfg,
            model_options=model_options,
            loss_options=loss_options,
            progress_callback=progress_callback,
        )
    finally:
        system_ablation_train_model.build_dataloaders = original_loader
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


def train_ablation(
    cfg: Config,
    *,
    model_options: AblationModelOptions | None = None,
    loss_options: AblationLossOptions | None = None,
):
    result = run_ablation_training(
        cfg,
        model_options=model_options,
        loss_options=loss_options,
    )
    return result["model"], result["rawTestMetrics"], result["summary"]["finalThreshold"]


__all__ = ["run_ablation_training", "train_ablation"]
