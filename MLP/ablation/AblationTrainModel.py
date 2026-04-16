from __future__ import annotations

"""
AblationTrainModel.py

Dedicated training entry for ablation experiments. It reuses the common
training utilities from TrainModel.py, while swapping in the standalone
ablation model and loss definitions.
"""

import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import torch
from torch.cuda.amp import GradScaler
from torch.utils.tensorboard import SummaryWriter
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

if __package__ in (None, ""):
    CURRENT_DIR = Path(__file__).resolve().parent
    PARENT_DIR = CURRENT_DIR.parent
    if str(CURRENT_DIR) not in sys.path:
        sys.path.insert(0, str(CURRENT_DIR))
    if str(PARENT_DIR) not in sys.path:
        sys.path.insert(0, str(PARENT_DIR))

if __package__:
    from .AblationModel import (
        AblationClaimClassificationLoss,
        AblationInsuranceMLP,
        AblationLossOptions,
        AblationModelOptions,
    )
    from ..DataLoader import build_dataloaders
    from ..TrainConfig import Config
    from ..TrainModel import (
        _TORCH_LOAD_KWARGS,
        EarlyStopping,
        add_scalar_if_not_none,
        append_history,
        build_latest_epoch,
        build_optimizer,
        build_scheduler,
        close_logger,
        evaluate,
        generate_training_figure_artifacts,
        init_history,
        load_checkpoint,
        resolve_monitor_metric,
        safe_progress_callback,
        safe_round,
        search_best_threshold,
        set_random_seed,
        setup_logger,
        train_one_epoch,
    )
else:
    from AblationModel import (
        AblationClaimClassificationLoss,
        AblationInsuranceMLP,
        AblationLossOptions,
        AblationModelOptions,
    )
    from DataLoader import build_dataloaders
    from TrainConfig import Config
    from TrainModel import (
        _TORCH_LOAD_KWARGS,
        EarlyStopping,
        add_scalar_if_not_none,
        append_history,
        build_latest_epoch,
        build_optimizer,
        build_scheduler,
        close_logger,
        evaluate,
        generate_training_figure_artifacts,
        init_history,
        load_checkpoint,
        resolve_monitor_metric,
        safe_progress_callback,
        safe_round,
        search_best_threshold,
        set_random_seed,
        setup_logger,
        train_one_epoch,
    )


def build_ablation_model_config_payload(
    cfg: Config,
    model_options: AblationModelOptions,
) -> Dict[str, Any]:
    return {
        "architecture": "ablation_claim_classifier_mlp",
        "task_type": "classification_only",
        "hidden_dims": list(cfg.model.hidden_dims),
        "head_hidden_dim": cfg.model.head_hidden_dim,
        "input_dropout": cfg.model.input_dropout,
        "backbone_dropout": cfg.model.backbone_dropout,
        "head_dropout": cfg.model.head_dropout,
        "head_samples": cfg.model.head_samples,
        "ablation_model_options": model_options.to_dict(),
    }


def build_ablation_loss_config_payload(
    cfg: Config,
    loss_options: AblationLossOptions,
    resolved_pos_weight: float,
) -> Dict[str, Any]:
    return {
        "configured_pos_weight": float(cfg.loss.pos_weight),
        "resolved_pos_weight": float(resolved_pos_weight),
        "label_smoothing": float(cfg.loss.label_smoothing),
        "ablation_loss_options": loss_options.to_dict(),
    }


def save_ablation_checkpoint(
    path: str,
    epoch: int,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler,
    best_monitor_value: float,
    best_threshold: float,
    cfg: Config,
    model_options: AblationModelOptions,
    loss_options: AblationLossOptions,
    resolved_pos_weight: float,
) -> None:
    torch.save(
        {
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict()
            if scheduler is not None and hasattr(scheduler, "state_dict")
            else None,
            "best_monitor_value": best_monitor_value,
            "best_loss": best_monitor_value,
            "best_threshold": best_threshold,
            "input_dim": cfg.model.input_dim,
            "model_config": build_ablation_model_config_payload(cfg, model_options),
            "loss_config": build_ablation_loss_config_payload(
                cfg,
                loss_options,
                resolved_pos_weight,
            ),
        },
        path,
    )


def resolve_ablation_pos_weight(
    cfg: Config,
    loss_options: AblationLossOptions,
    *,
    positive_count: float,
    negative_count: float,
) -> float:
    if not loss_options.use_pos_weight:
        return 1.0

    strategy = str(loss_options.pos_weight_strategy).strip().lower()
    if strategy == "auto":
        if positive_count <= 0:
            return 1.0
        return max(float(negative_count / positive_count), 1.0)
    if strategy == "fixed":
        resolved_pos_weight = float(cfg.loss.pos_weight)
        if resolved_pos_weight <= 0 and positive_count > 0:
            resolved_pos_weight = negative_count / positive_count
        return max(float(resolved_pos_weight), 1.0)
    raise ValueError(f"Unsupported pos_weight_strategy: {loss_options.pos_weight_strategy}")


def run_ablation_training(
    cfg: Config,
    *,
    model_options: AblationModelOptions | None = None,
    loss_options: AblationLossOptions | None = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    model_options = model_options or AblationModelOptions()
    loss_options = loss_options or AblationLossOptions()

    output_dir = Path(cfg.path.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    Path(cfg.path.log_dir).mkdir(parents=True, exist_ok=True)

    log_file = output_dir / "train.log"
    best_threshold_path = output_dir / "best_threshold.pt"
    logger = setup_logger(str(log_file))
    writer: Optional[SummaryWriter] = None

    try:
        set_random_seed(cfg.data.random_seed)
        writer = SummaryWriter(log_dir=cfg.path.log_dir)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Using device: %s", device)

        train_loader, val_loader, test_loader, input_dim = build_dataloaders(
            table_name=cfg.path.train_table,
            batch_size=cfg.data.batch_size,
            val_ratio=cfg.data.val_ratio,
            test_ratio=cfg.data.test_ratio,
            random_seed=cfg.data.random_seed,
            scaler_save_path=cfg.path.scaler_path,
            reference_save_path=cfg.path.reference_path,
            num_workers=cfg.data.num_workers,
            balanced_sampling=cfg.data.balanced_sampling,
            sampler_alpha=cfg.data.sampler_alpha,
        )
        cfg.model.input_dim = input_dim

        train_targets = train_loader.dataset.targets.detach().cpu().numpy()
        positive_count = float(train_targets.sum())
        negative_count = float(len(train_targets) - positive_count)
        resolved_pos_weight = resolve_ablation_pos_weight(
            cfg,
            loss_options,
            positive_count=positive_count,
            negative_count=negative_count,
        )

        logger.info(
            "Resolved pos_weight=%.6f (enabled=%s, strategy=%s, positive=%d, negative=%d)",
            resolved_pos_weight,
            loss_options.use_pos_weight,
            loss_options.pos_weight_strategy,
            int(positive_count),
            int(negative_count),
        )

        model = AblationInsuranceMLP(
            input_dim=cfg.model.input_dim,
            hidden_dims=cfg.model.hidden_dims,
            head_hidden_dim=cfg.model.head_hidden_dim,
            input_dropout=cfg.model.input_dropout,
            backbone_dropout=cfg.model.backbone_dropout,
            head_dropout=cfg.model.head_dropout,
            head_samples=cfg.model.head_samples,
            options=model_options,
        ).to(device)
        criterion = AblationClaimClassificationLoss(
            pos_weight=resolved_pos_weight,
            label_smoothing=cfg.loss.label_smoothing,
            options=loss_options,
        ).to(device)
        optimizer = build_optimizer(model, cfg)
        monitor_key, monitor_mode = resolve_monitor_metric(cfg.train.early_stop_metric)
        scheduler, scheduler_mode = build_scheduler(optimizer, cfg)
        amp_scaler = GradScaler(enabled=bool(cfg.train.use_amp and device.type == "cuda"))
        early_stopper = (
            EarlyStopping(cfg.train.patience, cfg.train.min_delta, mode=monitor_mode)
            if cfg.train.early_stop
            else None
        )

        history = init_history()
        start_epoch = 0
        best_monitor_value = float("inf") if monitor_mode == "min" else float("-inf")
        best_threshold = float(cfg.train.clf_threshold)

        if cfg.train.resume_from:
            resume_path = Path(cfg.train.resume_from)
            if resume_path.exists():
                start_epoch, best_monitor_value, best_threshold = load_checkpoint(
                    str(resume_path),
                    model,
                    optimizer,
                    scheduler,
                    device,
                    logger,
                    monitor_mode,
                )
            else:
                logger.warning("Resume checkpoint does not exist: %s", resume_path)

        safe_progress_callback(
            progress_callback,
            {
                "status": "running",
                "currentEpoch": max(start_epoch, 0),
                "totalEpochs": cfg.train.num_epochs,
                "progress": 0.0,
                "latestEpoch": None,
                "history": history,
                "message": "Ablation training started",
            },
            logger,
        )

        last_epoch_index = start_epoch - 1
        for epoch in range(start_epoch, cfg.train.num_epochs):
            epoch_start = time.time()
            last_epoch_index = epoch

            train_metrics = train_one_epoch(
                model=model,
                loader=train_loader,
                optimizer=optimizer,
                criterion=criterion,
                amp_scaler=amp_scaler,
                device=device,
                cfg=cfg,
                epoch=epoch,
                logger=logger,
            )
            val_metrics = evaluate(
                model=model,
                loader=val_loader,
                criterion=criterion,
                device=device,
                cfg=cfg,
                split="val",
            )

            if cfg.train.auto_threshold:
                best_threshold, threshold_search_score, threshold_search_info = search_best_threshold(
                    val_metrics["_probs"],
                    val_metrics["_labels"],
                    metric=cfg.train.threshold_metric,
                    beta=cfg.train.threshold_beta,
                    min_recall=cfg.train.threshold_min_recall,
                )
                if (
                    cfg.train.threshold_min_recall is not None
                    and not threshold_search_info["constraintSatisfied"]
                ):
                    logger.warning(
                        "Threshold search could not satisfy min_recall=%.4f on validation set; "
                        "falling back to the highest-recall candidate (selected recall=%.4f, precision=%.4f, score=%.4f)",
                        float(cfg.train.threshold_min_recall),
                        float(threshold_search_info["selectedRecall"]),
                        float(threshold_search_info["selectedPrecision"]),
                        float(threshold_search_score),
                    )
            else:
                best_threshold = float(cfg.train.clf_threshold)

            threshold_preds = (val_metrics["_probs"] >= best_threshold).astype(int)
            train_threshold_preds = (train_metrics["_probs"] >= best_threshold).astype(int)
            train_accuracy = (
                accuracy_score(train_metrics["_labels"], train_threshold_preds)
                if train_metrics["_labels"].size
                else 0.0
            )
            threshold_metrics = {
                "accuracy": accuracy_score(val_metrics["_labels"], threshold_preds),
                "balanced_accuracy": balanced_accuracy_score(
                    val_metrics["_labels"],
                    threshold_preds,
                ),
                "f1": f1_score(val_metrics["_labels"], threshold_preds, zero_division=0),
                "precision": precision_score(
                    val_metrics["_labels"],
                    threshold_preds,
                    zero_division=0,
                ),
                "recall": recall_score(
                    val_metrics["_labels"],
                    threshold_preds,
                    zero_division=0,
                ),
            }

            current_lr = float(optimizer.param_groups[0]["lr"])
            elapsed = time.time() - epoch_start
            monitor_value = (
                float(threshold_metrics[monitor_key])
                if monitor_key in threshold_metrics
                else float(val_metrics[monitor_key])
            )

            logger.info(
                "Epoch %03d/%03d lr=%.2e train_loss=%.4f train_acc=%.4f val_loss=%.4f val_pr_auc=%.4f val_acc=%.4f val_f1=%.4f val_precision=%.4f val_recall=%.4f thr=%.3f",
                epoch + 1,
                cfg.train.num_epochs,
                current_lr,
                train_metrics["loss"],
                train_accuracy,
                val_metrics["loss"],
                val_metrics["pr_auc"],
                threshold_metrics["accuracy"],
                threshold_metrics["f1"],
                threshold_metrics["precision"],
                threshold_metrics["recall"],
                best_threshold,
            )

            add_scalar_if_not_none(writer, "train/loss", train_metrics["loss"], epoch)
            add_scalar_if_not_none(writer, "train/clf_loss", train_metrics["clf_loss"], epoch)
            add_scalar_if_not_none(writer, "train/accuracy", train_accuracy, epoch)
            add_scalar_if_not_none(writer, "val/loss", val_metrics["loss"], epoch)
            add_scalar_if_not_none(writer, "val/clf_loss", val_metrics["clf_loss"], epoch)
            add_scalar_if_not_none(writer, "val/auc", val_metrics["auc"], epoch)
            add_scalar_if_not_none(writer, "val/pr_auc", val_metrics["pr_auc"], epoch)
            add_scalar_if_not_none(writer, "val/accuracy", threshold_metrics["accuracy"], epoch)
            add_scalar_if_not_none(
                writer,
                "val/balanced_accuracy",
                threshold_metrics["balanced_accuracy"],
                epoch,
            )
            add_scalar_if_not_none(writer, "val/f1", threshold_metrics["f1"], epoch)
            add_scalar_if_not_none(writer, "val/precision", threshold_metrics["precision"], epoch)
            add_scalar_if_not_none(writer, "val/recall", threshold_metrics["recall"], epoch)
            add_scalar_if_not_none(writer, "train/lr", current_lr, epoch)
            add_scalar_if_not_none(writer, "val/best_threshold", best_threshold, epoch)

            if scheduler_mode == "epoch" and scheduler is not None:
                scheduler.step()
            elif scheduler_mode == "plateau" and scheduler is not None:
                scheduler.step(val_metrics["loss"])

            if early_stopper is not None:
                is_best = early_stopper.step(monitor_value)
            elif monitor_mode == "max":
                is_best = monitor_value > best_monitor_value
            else:
                is_best = monitor_value < best_monitor_value

            if is_best:
                best_monitor_value = monitor_value
                save_ablation_checkpoint(
                    cfg.path.best_model_path,
                    epoch,
                    model,
                    optimizer,
                    scheduler,
                    best_monitor_value,
                    best_threshold,
                    cfg,
                    model_options,
                    loss_options,
                    resolved_pos_weight,
                )
                torch.save({"best_threshold": best_threshold}, best_threshold_path)
                logger.info(
                    "Saved best checkpoint (%s=%.6f, threshold=%.4f)",
                    monitor_key,
                    best_monitor_value,
                    best_threshold,
                )

            save_ablation_checkpoint(
                cfg.path.last_model_path,
                epoch,
                model,
                optimizer,
                scheduler,
                best_monitor_value,
                best_threshold,
                cfg,
                model_options,
                loss_options,
                resolved_pos_weight,
            )

            if cfg.train.save_every_epoch:
                epoch_path = output_dir / f"epoch_{epoch + 1:03d}.pth"
                save_ablation_checkpoint(
                    str(epoch_path),
                    epoch,
                    model,
                    optimizer,
                    scheduler,
                    best_monitor_value,
                    best_threshold,
                    cfg,
                    model_options,
                    loss_options,
                    resolved_pos_weight,
                )

            epoch_record = {
                "epoch": epoch + 1,
                "trainLoss": safe_round(train_metrics["loss"]),
                "trainClfLoss": safe_round(train_metrics["clf_loss"]),
                "trainAccuracy": safe_round(train_accuracy),
                "valLoss": safe_round(val_metrics["loss"]),
                "valClfLoss": safe_round(val_metrics["clf_loss"]),
                "valAuc": safe_round(val_metrics["auc"]),
                "valPrAuc": safe_round(val_metrics["pr_auc"]),
                "valAccuracy": safe_round(threshold_metrics["accuracy"]),
                "valBalancedAccuracy": safe_round(threshold_metrics["balanced_accuracy"]),
                "valF1": safe_round(threshold_metrics["f1"]),
                "valPrecision": safe_round(threshold_metrics["precision"]),
                "valRecall": safe_round(threshold_metrics["recall"]),
                "learningRate": safe_round(current_lr, 8),
                "bestThreshold": safe_round(best_threshold),
                "epochSeconds": safe_round(elapsed, 2),
                "isBest": is_best,
            }
            append_history(history, epoch_record)

            safe_progress_callback(
                progress_callback,
                {
                    "status": "running",
                    "currentEpoch": epoch + 1,
                    "totalEpochs": cfg.train.num_epochs,
                    "progress": safe_round((epoch + 1) / max(cfg.train.num_epochs, 1), 4),
                    "latestEpoch": epoch_record,
                    "history": history,
                    "message": f"Ablation epoch {epoch + 1}/{cfg.train.num_epochs} completed",
                },
                logger,
            )

            if early_stopper is not None and early_stopper.should_stop:
                logger.info("Early stopping triggered at epoch %d", epoch + 1)
                break

        if not Path(cfg.path.best_model_path).exists():
            save_ablation_checkpoint(
                cfg.path.best_model_path,
                max(last_epoch_index, 0),
                model,
                optimizer,
                scheduler,
                best_monitor_value,
                best_threshold,
                cfg,
                model_options,
                loss_options,
                resolved_pos_weight,
            )
            torch.save({"best_threshold": best_threshold}, best_threshold_path)

        best_checkpoint = torch.load(
            cfg.path.best_model_path,
            map_location=device,
            **_TORCH_LOAD_KWARGS,
        )
        model.load_state_dict(best_checkpoint["model"])
        final_threshold = float(best_checkpoint.get("best_threshold", best_threshold))
        if best_threshold_path.exists():
            saved_threshold = torch.load(
                best_threshold_path,
                map_location="cpu",
                **_TORCH_LOAD_KWARGS,
            )
            final_threshold = float(saved_threshold.get("best_threshold", final_threshold))

        test_metrics = evaluate(
            model=model,
            loader=test_loader,
            criterion=criterion,
            device=device,
            cfg=cfg,
            split="test",
        )
        test_preds = (test_metrics["_probs"] >= final_threshold).astype(int)

        final_metrics = {
            "loss": safe_round(test_metrics["loss"]),
            "clfLoss": safe_round(test_metrics["clf_loss"]),
            "auc": safe_round(test_metrics["auc"]),
            "prAuc": safe_round(test_metrics["pr_auc"]),
            "accuracy": safe_round(accuracy_score(test_metrics["_labels"], test_preds)),
            "balancedAccuracy": safe_round(
                balanced_accuracy_score(test_metrics["_labels"], test_preds)
            ),
            "f1": safe_round(f1_score(test_metrics["_labels"], test_preds, zero_division=0)),
            "precision": safe_round(
                precision_score(test_metrics["_labels"], test_preds, zero_division=0)
            ),
            "recall": safe_round(
                recall_score(test_metrics["_labels"], test_preds, zero_division=0)
            ),
        }

        report = classification_report(
            test_metrics["_labels"],
            test_preds,
            target_names=["No Claim", "Claim"],
            digits=4,
            zero_division=0,
        )
        cm = confusion_matrix(test_metrics["_labels"], test_preds, labels=[0, 1])
        logger.info("Classification report:\n%s", report)

        summary = {
            "epochsCompleted": len(history["epochs"]),
            "configuredEpochs": cfg.train.num_epochs,
            "stoppedEarly": bool(early_stopper and early_stopper.should_stop),
            "monitorMetric": monitor_key,
            "bestMonitorValue": safe_round(best_monitor_value),
            "finalThreshold": safe_round(final_threshold),
            "resolvedPosWeight": safe_round(resolved_pos_weight),
            "trainPositiveRate": safe_round(float(positive_count / max(len(train_targets), 1))),
            "finalMetrics": final_metrics,
            "lossConfig": criterion.get_loss_config(),
            "ablationModelOptions": model_options.to_dict(),
            "ablationLossOptions": loss_options.to_dict(),
            "classificationReport": report,
            "confusionMatrix": {
                "labels": ["No Claim", "Claim"],
                "matrix": cm.astype(int).tolist(),
            },
        }
        figure_artifacts: Dict[str, Any] = {}
        try:
            figure_artifacts = generate_training_figure_artifacts(
                output_dir=output_dir,
                history=history,
                summary=summary,
            )
        except Exception as exc:
            logger.warning("Failed to generate matplotlib figures: %s", exc)

        artifacts = {
            "outputDir": str(output_dir.resolve()),
            "logFile": str(log_file.resolve()),
            "tensorboardDir": str(Path(cfg.path.log_dir).resolve()),
            "scalerPath": str(Path(cfg.path.scaler_path).resolve()),
            "bestModelPath": str(Path(cfg.path.best_model_path).resolve()),
            "lastModelPath": str(Path(cfg.path.last_model_path).resolve()),
            "bestThresholdPath": str(best_threshold_path.resolve()),
        }
        artifacts.update(figure_artifacts)

        safe_progress_callback(
            progress_callback,
            {
                "status": "completed",
                "currentEpoch": len(history["epochs"]),
                "totalEpochs": cfg.train.num_epochs,
                "progress": 1.0,
                "latestEpoch": build_latest_epoch(history),
                "history": history,
                "summary": summary,
                "artifacts": artifacts,
                "message": "Ablation training completed",
            },
            logger,
        )

        return {
            "model": model,
            "rawTestMetrics": test_metrics,
            "history": history,
            "summary": summary,
            "artifacts": artifacts,
            "experimentConfig": {
                "modelOptions": model_options.to_dict(),
                "lossOptions": loss_options.to_dict(),
            },
        }
    finally:
        if writer is not None:
            writer.close()
        close_logger(logger)


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


__all__ = [
    "build_ablation_loss_config_payload",
    "build_ablation_model_config_payload",
    "resolve_ablation_pos_weight",
    "run_ablation_training",
    "save_ablation_checkpoint",
    "train_ablation",
]
