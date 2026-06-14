from __future__ import annotations

"""
FT-Transformer 训练流程

复用 DataLoader.build_dataloaders 确保与 MLP 使用相同的数据划分，
复用 Model.ClaimClassificationLoss 确保对比公平。
"""

import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.cuda.amp import GradScaler, autocast
from torch.optim.lr_scheduler import (
    CosineAnnealingLR,
    LinearLR,
    ReduceLROnPlateau,
    SequentialLR,
    StepLR,
)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from DataLoader import (
    FEATURE_ENGINEERING_STRATEGY,
    FEATURE_ENGINEERING_VERSION,
    OBSERVATION_DATE_COL,
    build_dataloaders,
)
from Model import ClaimClassificationLoss
from TrainModel import (
    EarlyStopping,
    build_optimizer,
    build_scheduler,
    close_logger,
    generate_training_figure_artifacts,
    resolve_monitor_metric,
    safe_round,
    search_best_threshold,
    serialize_metrics,
    set_random_seed,
    setup_logger,
)

from .ft_config import FTConfig
from .ft_model import FTTransformer


def build_ft_model_config_payload(cfg: FTConfig) -> Dict[str, Any]:
    return {
        "architecture": "ft_transformer",
        "task_type": "classification_only",
        "d_token": cfg.model.d_token,
        "n_layers": cfg.model.n_layers,
        "n_heads": cfg.model.n_heads,
        "attn_dropout": cfg.model.attn_dropout,
        "ff_dropout": cfg.model.ff_dropout,
        "ff_factor": cfg.model.ff_factor,
    }


def save_checkpoint(
    path: str,
    epoch: int,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler,
    best_monitor_value: float,
    best_threshold: float,
    cfg: FTConfig,
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
            "best_threshold": best_threshold,
            "n_features": cfg.model.n_features if hasattr(cfg.model, "n_features") else -1,
            "model_config": build_ft_model_config_payload(cfg),
        },
        path,
    )


def train_one_epoch(
    model: FTTransformer,
    loader,
    optimizer: torch.optim.Optimizer,
    criterion: ClaimClassificationLoss,
    amp_scaler: GradScaler,
    device: torch.device,
    use_amp: bool,
    grad_clip: float,
    clf_threshold: float,
    log_interval: int,
    epoch: int,
    logger: logging.Logger,
) -> Dict[str, Any]:
    model.train()

    total_loss = 0.0
    total_clf_loss = 0.0
    total_samples = 0
    all_probs: list[np.ndarray] = []
    all_labels: list[np.ndarray] = []

    for batch_idx, (features, labels) in enumerate(loader, start=1):
        features = features.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        batch_size = int(features.size(0))

        optimizer.zero_grad(set_to_none=True)
        with autocast(enabled=use_amp):
            logits = model(features)
            loss, clf_loss = criterion(logits, labels)

        if use_amp:
            amp_scaler.scale(loss).backward()
            if grad_clip and grad_clip > 0:
                amp_scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            amp_scaler.step(optimizer)
            amp_scaler.update()
        else:
            loss.backward()
            if grad_clip and grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()

        total_loss += float(loss.item()) * batch_size
        total_clf_loss += float(clf_loss.item()) * batch_size
        total_samples += batch_size
        all_probs.append(torch.sigmoid(logits.detach()).cpu().numpy())
        all_labels.append(labels.detach().cpu().numpy())

        if log_interval and batch_idx % log_interval == 0:
            logger.info(
                "Epoch %03d batch %04d/%04d loss=%.6f clf_loss=%.6f",
                epoch + 1,
                batch_idx,
                len(loader),
                float(loss.item()),
                float(clf_loss.item()),
            )

    probs = np.concatenate(all_probs) if all_probs else np.empty(0, dtype=np.float32)
    labels_np = np.concatenate(all_labels) if all_labels else np.empty(0, dtype=np.float32)
    labels_int = labels_np.astype(int)
    preds = (probs >= float(clf_threshold)).astype(int)

    return {
        "loss": total_loss / max(total_samples, 1),
        "clf_loss": total_clf_loss / max(total_samples, 1),
        "accuracy": accuracy_score(labels_int, preds) if labels_int.size else 0.0,
        "_probs": probs,
        "_labels": labels_int,
    }


@torch.no_grad()
def evaluate(
    model: FTTransformer,
    loader,
    criterion: ClaimClassificationLoss,
    device: torch.device,
    use_amp: bool,
    clf_threshold: float,
    split: str = "val",
) -> Dict[str, Any]:
    model.eval()

    total_loss = 0.0
    total_clf_loss = 0.0
    total_samples = 0
    all_probs: list[np.ndarray] = []
    all_labels: list[np.ndarray] = []

    for features, labels in loader:
        features = features.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        batch_size = int(features.size(0))

        with autocast(enabled=use_amp):
            logits = model(features)
            loss, clf_loss = criterion(logits, labels)

        all_probs.append(torch.sigmoid(logits).cpu().numpy())
        all_labels.append(labels.cpu().numpy())
        total_loss += float(loss.item()) * batch_size
        total_clf_loss += float(clf_loss.item()) * batch_size
        total_samples += batch_size

    probs = np.concatenate(all_probs) if all_probs else np.empty(0, dtype=np.float32)
    labels = np.concatenate(all_labels) if all_labels else np.empty(0, dtype=np.float32)
    labels_int = labels.astype(int)
    preds = (probs >= float(clf_threshold)).astype(int)

    auc = (
        float(roc_auc_score(labels_int, probs))
        if labels_int.size > 0 and np.unique(labels_int).size > 1
        else 0.5
    )
    pr_auc = (
        float(average_precision_score(labels_int, probs))
        if labels_int.size > 0 and np.unique(labels_int).size > 1
        else float(labels_int.mean()) if labels_int.size > 0 else 0.0
    )

    return {
        "split": split,
        "loss": total_loss / max(total_samples, 1),
        "clf_loss": total_clf_loss / max(total_samples, 1),
        "auc": auc,
        "pr_auc": pr_auc,
        "accuracy": accuracy_score(labels_int, preds) if labels_int.size else 0.0,
        "balanced_accuracy": (
            balanced_accuracy_score(labels_int, preds) if labels_int.size else 0.0
        ),
        "f1": f1_score(labels_int, preds, zero_division=0) if labels_int.size else 0.0,
        "precision": precision_score(labels_int, preds, zero_division=0) if labels_int.size else 0.0,
        "recall": recall_score(labels_int, preds, zero_division=0) if labels_int.size else 0.0,
        "_probs": probs,
        "_labels": labels_int,
    }


def ft_run_training(
    cfg: FTConfig,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    output_dir = Path(cfg.path.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    Path(cfg.path.log_dir).mkdir(parents=True, exist_ok=True)

    log_file = output_dir / "ft_train.log"
    best_threshold_path = output_dir / "best_threshold.pt"
    logger = setup_logger(str(log_file))

    try:
        set_random_seed(cfg.data.random_seed)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("FT-Transformer training on device: %s", device)

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

        train_targets = train_loader.dataset.targets.detach().cpu().numpy()
        positive_count = float(train_targets.sum())
        negative_count = float(len(train_targets) - positive_count)
        resolved_pos_weight = float(cfg.loss.pos_weight)
        if resolved_pos_weight <= 0 and positive_count > 0:
            resolved_pos_weight = negative_count / positive_count
        resolved_pos_weight = max(resolved_pos_weight, 1.0)

        logger.info(
            "Resolved pos_weight=%.6f (positive=%d, negative=%d)",
            resolved_pos_weight,
            int(positive_count),
            int(negative_count),
        )
        logger.info("Input dimension: %d", input_dim)

        model = FTTransformer(
            n_features=input_dim,
            d_token=cfg.model.d_token,
            n_layers=cfg.model.n_layers,
            n_heads=cfg.model.n_heads,
            attn_dropout=cfg.model.attn_dropout,
            ff_dropout=cfg.model.ff_dropout,
            ff_factor=cfg.model.ff_factor,
        ).to(device)

        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        logger.info(
            "FT-Transformer: total params=%d, trainable=%d",
            total_params,
            trainable_params,
        )

        criterion = ClaimClassificationLoss(
            pos_weight=resolved_pos_weight,
            label_smoothing=cfg.loss.label_smoothing,
        ).to(device)
        optimizer = build_optimizer(model, cfg)
        monitor_key, monitor_mode = resolve_monitor_metric(cfg.train.early_stop_metric)
        scheduler, scheduler_mode = build_scheduler(optimizer, cfg)
        amp_scaler = GradScaler(enabled=bool(cfg.train.use_amp and device.type == "cuda"))
        use_amp = bool(cfg.train.use_amp and device.type == "cuda")

        early_stopper = (
            EarlyStopping(cfg.train.patience, cfg.train.min_delta, mode=monitor_mode)
            if cfg.train.early_stop
            else None
        )

        # Training history
        history: Dict[str, list] = {
            "epochs": [],
            "trainLoss": [],
            "trainClfLoss": [],
            "trainAccuracy": [],
            "valLoss": [],
            "valClfLoss": [],
            "valAuc": [],
            "valPrAuc": [],
            "valAccuracy": [],
            "valBalancedAccuracy": [],
            "valF1": [],
            "valPrecision": [],
            "valRecall": [],
            "learningRate": [],
            "bestThreshold": [],
            "epochSeconds": [],
        }

        start_epoch = 0
        best_monitor_value = float("inf") if monitor_mode == "min" else float("-inf")
        best_threshold = float(cfg.train.clf_threshold)
        last_epoch_index = start_epoch - 1

        logger.info("Starting training. Monitor metric: %s (mode=%s)", monitor_key, monitor_mode)

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
                use_amp=use_amp,
                grad_clip=cfg.train.grad_clip,
                clf_threshold=cfg.train.clf_threshold,
                log_interval=cfg.train.log_interval,
                epoch=epoch,
                logger=logger,
            )

            val_metrics = evaluate(
                model=model,
                loader=val_loader,
                criterion=criterion,
                device=device,
                use_amp=use_amp,
                clf_threshold=cfg.train.clf_threshold,
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
                        "Threshold search could not satisfy min_recall=%.4f; "
                        "falling back. (recall=%.4f, precision=%.4f)",
                        float(cfg.train.threshold_min_recall),
                        float(threshold_search_info["selectedRecall"]),
                        float(threshold_search_info["selectedPrecision"]),
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
                    val_metrics["_labels"], threshold_preds
                ),
                "f1": f1_score(val_metrics["_labels"], threshold_preds, zero_division=0),
                "precision": precision_score(val_metrics["_labels"], threshold_preds, zero_division=0),
                "recall": recall_score(val_metrics["_labels"], threshold_preds, zero_division=0),
            }

            current_lr = float(optimizer.param_groups[0]["lr"])
            elapsed = time.time() - epoch_start
            monitor_value = val_metrics[monitor_key]

            logger.info(
                "Epoch %03d/%03d lr=%.2e train_loss=%.4f train_acc=%.4f "
                "val_loss=%.4f val_pr_auc=%.4f val_acc=%.4f val_f1=%.4f "
                "val_precision=%.4f val_recall=%.4f thr=%.3f",
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
                save_checkpoint(
                    cfg.path.best_model_path,
                    epoch,
                    model,
                    optimizer,
                    scheduler,
                    best_monitor_value,
                    best_threshold,
                    cfg,
                )
                torch.save({"best_threshold": best_threshold}, best_threshold_path)
                logger.info(
                    "Saved best FT-Transformer checkpoint (%s=%.6f, threshold=%.4f)",
                    monitor_key,
                    best_monitor_value,
                    best_threshold,
                )

            save_checkpoint(
                cfg.path.last_model_path,
                epoch,
                model,
                optimizer,
                scheduler,
                best_monitor_value,
                best_threshold,
                cfg,
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

            for key, value in epoch_record.items():
                if key in history:
                    history[key].append(value)

            if early_stopper is not None and early_stopper.should_stop:
                logger.info("Early stopping triggered at epoch %d", epoch + 1)
                break

        # Ensure best model is saved
        if not Path(cfg.path.best_model_path).exists():
            save_checkpoint(
                cfg.path.best_model_path,
                max(last_epoch_index, 0),
                model,
                optimizer,
                scheduler,
                best_monitor_value,
                best_threshold,
                cfg,
            )
            torch.save({"best_threshold": best_threshold}, best_threshold_path)

        # Load best model for final test evaluation
        best_checkpoint = torch.load(
            cfg.path.best_model_path, map_location=device, weights_only=False
        )
        model.load_state_dict(best_checkpoint["model"])
        final_threshold = float(best_checkpoint.get("best_threshold", best_threshold))
        if best_threshold_path.exists():
            saved_threshold = torch.load(best_threshold_path, map_location="cpu", weights_only=False)
            final_threshold = float(saved_threshold.get("best_threshold", final_threshold))

        test_metrics = evaluate(
            model=model,
            loader=test_loader,
            criterion=criterion,
            device=device,
            use_amp=use_amp,
            clf_threshold=final_threshold,
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
            "precision": safe_round(precision_score(test_metrics["_labels"], test_preds, zero_division=0)),
            "recall": safe_round(recall_score(test_metrics["_labels"], test_preds, zero_division=0)),
        }

        report = classification_report(
            test_metrics["_labels"],
            test_preds,
            target_names=["No Claim", "Claim"],
            digits=4,
            zero_division=0,
        )
        cm = confusion_matrix(test_metrics["_labels"], test_preds, labels=[0, 1])
        logger.info("FT-Transformer Classification Report:\n%s", report)

        summary = {
            "epochsCompleted": len(history["epochs"]),
            "configuredEpochs": cfg.train.num_epochs,
            "stoppedEarly": bool(early_stopper and early_stopper.should_stop),
            "monitorMetric": monitor_key,
            "bestMonitorValue": safe_round(best_monitor_value),
            "finalThreshold": safe_round(final_threshold),
            "resolvedPosWeight": safe_round(resolved_pos_weight),
            "trainPositiveRate": safe_round(float(positive_count / max(len(train_targets), 1))),
            "thresholdSelection": {
                "metric": cfg.train.threshold_metric,
                "beta": safe_round(cfg.train.threshold_beta),
                "minRecall": safe_round(cfg.train.threshold_min_recall)
                if cfg.train.threshold_min_recall is not None
                else None,
            },
            "featureEngineering": {
                "version": FEATURE_ENGINEERING_VERSION,
                "strategy": FEATURE_ENGINEERING_STRATEGY,
                "observationDateColumn": OBSERVATION_DATE_COL,
            },
            "finalMetrics": final_metrics,
            "lossConfig": serialize_metrics(criterion.get_loss_config()),
            "classificationReport": report,
            "confusionMatrix": {
                "labels": ["No Claim", "Claim"],
                "matrix": cm.astype(int).tolist(),
            },
            "modelParams": {
                "total": total_params,
                "trainable": trainable_params,
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
            "trainTable": cfg.path.train_table,
            "featureEngineering": {
                "version": FEATURE_ENGINEERING_VERSION,
                "strategy": FEATURE_ENGINEERING_STRATEGY,
                "observationDateColumn": OBSERVATION_DATE_COL,
            },
            "scalerPath": str(Path(cfg.path.scaler_path).resolve()),
            "referencePath": str(Path(cfg.path.reference_path).resolve()),
            "bestModelPath": str(Path(cfg.path.best_model_path).resolve()),
            "lastModelPath": str(Path(cfg.path.last_model_path).resolve()),
            "bestThresholdPath": str(best_threshold_path.resolve()),
        }
        artifacts.update(figure_artifacts)

        logger.info("FT-Transformer training completed.")
        logger.info(
            "Test metrics: AUC=%.4f, F1=%.4f, Precision=%.4f, Recall=%.4f",
            final_metrics["auc"],
            final_metrics["f1"],
            final_metrics["precision"],
            final_metrics["recall"],
        )

        return {
            "model": model,
            "rawTestMetrics": test_metrics,
            "history": history,
            "summary": summary,
            "artifacts": artifacts,
        }
    finally:
        close_logger(logger)


def ft_train(cfg: FTConfig = None):
    """独立训练入口。"""
    if cfg is None:
        cfg = FTConfig()
    cfg.summary()
    result = ft_run_training(cfg)
    return result["model"], result["rawTestMetrics"], result["summary"]["finalThreshold"]


if __name__ == "__main__":
    ft_train()
