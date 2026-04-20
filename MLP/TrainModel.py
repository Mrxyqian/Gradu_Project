from __future__ import annotations

"""
TrainModel.py
车险理赔预测 —— 分类任务训练流程

当前训练流程仅服务于分类任务：
  - 使用 BCEWithLogitsLoss 完成理赔概率学习
  - 输出 AUC、PR-AUC、F1、Precision、Recall 等分类指标
  - 保留训练管理器依赖的 run_training 返回结构
"""

import logging
import random
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import matplotlib
import numpy as np
import torch
import torch.nn as nn
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
from torch.utils.tensorboard import SummaryWriter

if __package__:
    from .DataLoader import (
        FEATURE_ENGINEERING_STRATEGY,
        FEATURE_ENGINEERING_VERSION,
        OBSERVATION_DATE_COL,
        build_dataloaders,
    )
    from .Model import ClaimClassificationLoss, InsuranceMLP
    from .TrainConfig import Config
else:
    from DataLoader import (
        FEATURE_ENGINEERING_STRATEGY,
        FEATURE_ENGINEERING_VERSION,
        OBSERVATION_DATE_COL,
        build_dataloaders,
    )
    from Model import ClaimClassificationLoss, InsuranceMLP
    from TrainConfig import Config


_TORCH_LOAD_KWARGS = {"weights_only": False}


def set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def safe_round(value: Any, digits: int = 6) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(numeric):
        return None
    return round(numeric, digits)


def serialize_metrics(metrics: Dict[str, Any], digits: int = 6) -> Dict[str, Optional[float]]:
    return {
        key: safe_round(value, digits)
        for key, value in metrics.items()
        if not key.startswith("_")
    }


def setup_logger(log_path: str) -> logging.Logger:
    logger = logging.getLogger(f"ClaimClassificationTrain.{Path(log_path).resolve()}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def close_logger(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass


def safe_progress_callback(
    callback: Optional[Callable[[Dict[str, Any]], None]],
    payload: Dict[str, Any],
    logger: logging.Logger,
) -> None:
    if callback is None:
        return
    try:
        callback(deepcopy(payload))
    except Exception as exc:
        logger.warning("Progress callback failed: %s", exc)


def add_scalar_if_not_none(
    writer: Optional[SummaryWriter],
    tag: str,
    value: Optional[float],
    step: int,
) -> None:
    if writer is None or value is None:
        return
    writer.add_scalar(tag, value, step)


def save_professional_line_chart(
    output_path: Path,
    x_data: list[Any],
    series_items: list[Dict[str, Any]],
    title: str,
    y_label: str,
    y_lim: Optional[tuple[float, float]] = None,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), dpi=180)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f8fafc")

    for item in series_items:
        ax.plot(
            x_data,
            item["data"],
            label=item["label"],
            color=item["color"],
            linewidth=2.2,
            marker="o",
            markersize=4,
        )

    ax.set_title(title, fontsize=15, fontweight="bold", pad=14)
    ax.set_xlabel("Epoch", fontsize=11)
    ax.set_ylabel(y_label, fontsize=11)
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.35)
    ax.legend(frameon=False, fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if len(x_data) == 1:
        single_epoch = float(x_data[0])
        ax.set_xlim(single_epoch - 0.5, single_epoch + 0.5)
    else:
        ax.set_xlim(min(x_data), max(x_data))
    if y_lim is not None:
        ax.set_ylim(*y_lim)
    ax.tick_params(labelsize=10)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def save_confusion_matrix_chart(
    output_path: Path,
    confusion_matrix_data: list[list[int]],
    labels: list[str],
) -> None:
    matrix = np.asarray(confusion_matrix_data, dtype=np.int64)
    fig, ax = plt.subplots(figsize=(7.2, 6.2), dpi=180)
    fig.patch.set_facecolor("#ffffff")
    image = ax.imshow(matrix, cmap="Blues")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

    ax.set_title("Confusion Matrix", fontsize=15, fontweight="bold", pad=14)
    ax.set_xlabel("Predicted Label", fontsize=11)
    ax.set_ylabel("True Label", fontsize=11)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_yticklabels(labels, fontsize=10)

    threshold = matrix.max() / 2 if matrix.size else 0
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            value = int(matrix[row, col])
            ax.text(
                col,
                row,
                str(value),
                ha="center",
                va="center",
                color="white" if value > threshold else "#0f172a",
                fontsize=12,
                fontweight="bold",
            )

    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def generate_training_figure_artifacts(
    output_dir: Path,
    history: Dict[str, list],
    summary: Dict[str, Any],
) -> Dict[str, Any]:
    epochs = history.get("epochs") or []
    if not epochs:
        return {}

    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    figure_files = {
        "lossCurve": "loss_curve.png",
        "accuracyCurve": "accuracy_curve.png",
        "valPrAucCurve": "val_pr_auc_curve.png",
        "confusionMatrix": "confusion_matrix.png",
    }

    save_professional_line_chart(
        figure_dir / figure_files["lossCurve"],
        epochs,
        [
            {"label": "Train Loss", "data": history.get("trainLoss", []), "color": "#2563eb"},
            {"label": "Validation Loss", "data": history.get("valLoss", []), "color": "#059669"},
        ],
        title="Training and Validation Loss",
        y_label="Loss",
    )
    save_professional_line_chart(
        figure_dir / figure_files["accuracyCurve"],
        epochs,
        [
            {"label": "Train Accuracy", "data": history.get("trainAccuracy", []), "color": "#7c3aed"},
            {"label": "Validation Accuracy", "data": history.get("valAccuracy", []), "color": "#ea580c"},
        ],
        title="Training and Validation Accuracy",
        y_label="Accuracy",
        y_lim=(0.0, 1.0),
    )
    save_professional_line_chart(
        figure_dir / figure_files["valPrAucCurve"],
        epochs,
        [
            {"label": "Validation PR-AUC", "data": history.get("valPrAuc", []), "color": "#db2777"},
        ],
        title="Validation PR-AUC",
        y_label="PR-AUC",
        y_lim=(0.0, 1.0),
    )

    confusion_payload = summary.get("confusionMatrix") or {}
    save_confusion_matrix_chart(
        figure_dir / figure_files["confusionMatrix"],
        confusion_payload.get("matrix") or [[0, 0], [0, 0]],
        confusion_payload.get("labels") or ["No Claim", "Claim"],
    )

    return {
        "figureDir": str(figure_dir.resolve()),
        "figureFiles": figure_files,
    }


def search_best_threshold(
    probs: np.ndarray,
    labels: np.ndarray,
    metric: str = "f1",
    beta: float = 1.0,
    min_recall: Optional[float] = None,
    n_candidates: int = 200,
) -> tuple[float, float, Dict[str, Any]]:
    if probs.size == 0:
        return 0.5, 0.0, {
            "metric": metric,
            "beta": beta,
            "minRecall": min_recall,
            "constraintSatisfied": False,
            "selectedPrecision": 0.0,
            "selectedRecall": 0.0,
        }

    thresholds = np.linspace(0.05, 0.95, n_candidates)
    # thresholds = np.unique(
    #     np.clip(
    #         np.concatenate([np.linspace(0.05, 0.95, n_candidates), probs.astype(np.float64)]),
    #         0.0,
    #         1.0,
    #     )
    # )
    candidates: list[Dict[str, float]] = []

    for threshold in thresholds:
        preds = (probs >= threshold).astype(int)
        precision = precision_score(labels, preds, zero_division=0)
        recall = recall_score(labels, preds, zero_division=0)
        if metric == "f1":
            score = (
                f1_score(labels, preds, zero_division=0)
                if beta == 1.0
                else fbeta_score(labels, preds, beta=beta, zero_division=0)
            )
        elif metric == "precision":
            score = precision
        elif metric == "recall":
            score = recall
        else:
            raise ValueError(f"Unsupported threshold metric: {metric}")

        candidates.append(
            {
                "threshold": float(threshold),
                "score": float(score),
                "precision": float(precision),
                "recall": float(recall),
            }
        )

    recall_floor = None if min_recall is None else float(min_recall)
    feasible_candidates = candidates
    constraint_satisfied = False
    if recall_floor is not None:
        feasible_candidates = [
            candidate for candidate in candidates if candidate["recall"] >= recall_floor
        ]
        constraint_satisfied = bool(feasible_candidates)

    ranking_pool = feasible_candidates if feasible_candidates else candidates
    if feasible_candidates:
        best_candidate = max(
            ranking_pool,
            key=lambda candidate: (
                candidate["score"],
                candidate["precision"],
                candidate["recall"],
                candidate["threshold"],
            ),
        )
    else:
        best_candidate = max(
            ranking_pool,
            key=lambda candidate: (
                candidate["recall"],
                candidate["precision"],
                candidate["score"],
                -candidate["threshold"],
            ),
        )

    return best_candidate["threshold"], best_candidate["score"], {
        "metric": metric,
        "beta": beta,
        "minRecall": recall_floor,
        "constraintSatisfied": constraint_satisfied,
        "selectedPrecision": best_candidate["precision"],
        "selectedRecall": best_candidate["recall"],
    }


def init_history() -> Dict[str, list]:
    return {
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


def append_history(history: Dict[str, list], epoch_record: Dict[str, Any]) -> None:
    history["epochs"].append(epoch_record["epoch"])
    history["trainLoss"].append(epoch_record["trainLoss"])
    history["trainClfLoss"].append(epoch_record["trainClfLoss"])
    history["trainAccuracy"].append(epoch_record["trainAccuracy"])
    history["valLoss"].append(epoch_record["valLoss"])
    history["valClfLoss"].append(epoch_record["valClfLoss"])
    history["valAuc"].append(epoch_record["valAuc"])
    history["valPrAuc"].append(epoch_record["valPrAuc"])
    history["valAccuracy"].append(epoch_record["valAccuracy"])
    history["valBalancedAccuracy"].append(epoch_record["valBalancedAccuracy"])
    history["valF1"].append(epoch_record["valF1"])
    history["valPrecision"].append(epoch_record["valPrecision"])
    history["valRecall"].append(epoch_record["valRecall"])
    history["learningRate"].append(epoch_record["learningRate"])
    history["bestThreshold"].append(epoch_record["bestThreshold"])
    history["epochSeconds"].append(epoch_record["epochSeconds"])


def build_latest_epoch(history: Dict[str, list]) -> Optional[Dict[str, Any]]:
    if not history["epochs"]:
        return None
    last_idx = -1
    return {
        "epoch": history["epochs"][last_idx],
        "trainLoss": history["trainLoss"][last_idx],
        "trainClfLoss": history["trainClfLoss"][last_idx],
        "trainAccuracy": history["trainAccuracy"][last_idx],
        "valLoss": history["valLoss"][last_idx],
        "valClfLoss": history["valClfLoss"][last_idx],
        "valAuc": history["valAuc"][last_idx],
        "valPrAuc": history["valPrAuc"][last_idx],
        "valAccuracy": history["valAccuracy"][last_idx],
        "valBalancedAccuracy": history["valBalancedAccuracy"][last_idx],
        "valF1": history["valF1"][last_idx],
        "valPrecision": history["valPrecision"][last_idx],
        "valRecall": history["valRecall"][last_idx],
        "learningRate": history["learningRate"][last_idx],
        "bestThreshold": history["bestThreshold"][last_idx],
        "epochSeconds": history["epochSeconds"][last_idx],
    }


def resolve_monitor_metric(metric_name: str) -> tuple[str, str]:
    metric = (metric_name or "auc").strip().lower()
    mapping = {
        "loss": ("loss", "min"),
        "total_loss": ("loss", "min"),
        "clf_loss": ("clf_loss", "min"),
        "auc": ("auc", "max"),
        "pr_auc": ("pr_auc", "max"),
        "average_precision": ("pr_auc", "max"),
        "accuracy": ("accuracy", "max"),
        "balanced_accuracy": ("balanced_accuracy", "max"),
        "f1": ("f1", "max"),
        "precision": ("precision", "max"),
        "recall": ("recall", "max"),
    }
    if metric not in mapping:
        raise ValueError(f"Unsupported early-stop metric: {metric_name}")
    return mapping[metric]


def build_optimizer(model: nn.Module, cfg: Config) -> torch.optim.Optimizer:
    optimizer_cfg = cfg.optimizer
    params = model.parameters()

    if optimizer_cfg.optimizer == "adamw":
        return torch.optim.AdamW(
            params,
            lr=optimizer_cfg.lr,
            betas=(optimizer_cfg.beta1, optimizer_cfg.beta2),
            eps=optimizer_cfg.eps,
            weight_decay=optimizer_cfg.weight_decay,
        )
    if optimizer_cfg.optimizer == "adam":
        return torch.optim.Adam(
            params,
            lr=optimizer_cfg.lr,
            betas=(optimizer_cfg.beta1, optimizer_cfg.beta2),
            eps=optimizer_cfg.eps,
            weight_decay=optimizer_cfg.weight_decay,
        )
    if optimizer_cfg.optimizer == "sgd":
        return torch.optim.SGD(
            params,
            lr=optimizer_cfg.lr,
            momentum=optimizer_cfg.momentum,
            nesterov=optimizer_cfg.nesterov,
            weight_decay=optimizer_cfg.weight_decay,
        )
    raise ValueError(f"Unsupported optimizer: {optimizer_cfg.optimizer}")


def build_scheduler(optimizer: torch.optim.Optimizer, cfg: Config):
    scheduler_cfg = cfg.scheduler
    train_cfg = cfg.train

    if scheduler_cfg.scheduler == "cosine_warmup":
        warmup_epochs = max(1, scheduler_cfg.warmup_epochs)
        warmup = LinearLR(
            optimizer,
            start_factor=1e-3,
            end_factor=1.0,
            total_iters=warmup_epochs,
        )
        cosine = CosineAnnealingLR(
            optimizer,
            T_max=max(train_cfg.num_epochs - warmup_epochs, 1),
            eta_min=scheduler_cfg.min_lr,
        )
        return SequentialLR(
            optimizer,
            schedulers=[warmup, cosine],
            milestones=[warmup_epochs],
        ), "epoch"
    if scheduler_cfg.scheduler == "reduce_on_plateau":
        return ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=scheduler_cfg.plateau_factor,
            patience=scheduler_cfg.plateau_patience,
            min_lr=scheduler_cfg.plateau_min_lr,
        ), "plateau"
    if scheduler_cfg.scheduler == "step":
        return StepLR(
            optimizer,
            step_size=scheduler_cfg.step_size,
            gamma=scheduler_cfg.gamma,
        ), "epoch"
    if scheduler_cfg.scheduler == "none":
        return None, "none"
    raise ValueError(f"Unsupported scheduler: {scheduler_cfg.scheduler}")

class EarlyStopping:
    def __init__(self, patience: int, min_delta: float = 1e-4, mode: str = "min"):
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.best_value = float("inf") if mode == "min" else float("-inf")
        self.counter = 0
        self.should_stop = False

    def step(self, value: float) -> bool:
        improved = (
            value < self.best_value - self.min_delta
            if self.mode == "min"
            else value > self.best_value + self.min_delta
        )
        if improved:
            self.best_value = value
            self.counter = 0
            return True

        self.counter += 1
        if self.counter >= self.patience:
            self.should_stop = True
        return False


def build_model_config_payload(cfg: Config) -> Dict[str, Any]:
    return {
        "architecture": "claim_classifier_residual_mlp",
        "task_type": "classification_only",
        "hidden_dims": list(cfg.model.hidden_dims),
        "head_hidden_dim": cfg.model.head_hidden_dim,
        "input_dropout": cfg.model.input_dropout,
        "backbone_dropout": cfg.model.backbone_dropout,
        "head_dropout": cfg.model.head_dropout,
        "head_samples": cfg.model.head_samples,
    }


def save_checkpoint(
    path: str,
    epoch: int,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler,
    best_monitor_value: float,
    best_threshold: float,
    cfg: Config,
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
            "model_config": build_model_config_payload(cfg),
        },
        path,
    )


def load_checkpoint(
    path: str,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler,
    device: torch.device,
    logger: logging.Logger,
    monitor_mode: str,
) -> tuple[int, float, float]:
    checkpoint = torch.load(path, map_location=device, **_TORCH_LOAD_KWARGS)
    model.load_state_dict(checkpoint["model"])
    optimizer.load_state_dict(checkpoint["optimizer"])
    if scheduler is not None and checkpoint.get("scheduler") is not None:
        scheduler.load_state_dict(checkpoint["scheduler"])

    start_epoch = int(checkpoint.get("epoch", 0)) + 1
    default_best = float("inf") if monitor_mode == "min" else float("-inf")
    best_monitor_value = float(
        checkpoint.get("best_monitor_value", checkpoint.get("best_loss", default_best))
    )
    best_threshold = float(checkpoint.get("best_threshold", 0.5))
    logger.info(
        "Resumed from checkpoint %s (epoch=%s, best_monitor=%.6f, threshold=%.4f)",
        path,
        checkpoint.get("epoch", 0),
        best_monitor_value,
        best_threshold,
    )
    return start_epoch, best_monitor_value, best_threshold


def train_one_epoch(
    model: InsuranceMLP,
    loader,
    optimizer: torch.optim.Optimizer,
    criterion: ClaimClassificationLoss,
    amp_scaler: GradScaler,
    device: torch.device,
    cfg: Config,
    epoch: int,
    logger: logging.Logger,
) -> Dict[str, Optional[float]]:
    model.train()
    use_amp = bool(cfg.train.use_amp and device.type == "cuda")

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
            if cfg.train.grad_clip and cfg.train.grad_clip > 0:
                amp_scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.train.grad_clip)
            amp_scaler.step(optimizer)
            amp_scaler.update()
        else:
            loss.backward()
            if cfg.train.grad_clip and cfg.train.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.train.grad_clip)
            optimizer.step()

        total_loss += float(loss.item()) * batch_size
        total_clf_loss += float(clf_loss.item()) * batch_size
        total_samples += batch_size
        all_probs.append(torch.sigmoid(logits.detach()).cpu().numpy())
        all_labels.append(labels.detach().cpu().numpy())

        if cfg.train.log_interval and batch_idx % cfg.train.log_interval == 0:
            logger.info(
                "Epoch %03d batch %04d/%04d loss=%.6f clf_loss=%.6f",
                epoch + 1,
                batch_idx,
                len(loader),
                float(loss.item()),
                float(clf_loss.item()),
            )

    probs = np.concatenate(all_probs) if all_probs else np.empty(0, dtype=np.float32)
    labels = np.concatenate(all_labels) if all_labels else np.empty(0, dtype=np.float32)
    labels_int = labels.astype(int)
    preds = (probs >= float(cfg.train.clf_threshold)).astype(int)

    return {
        "loss": total_loss / max(total_samples, 1),
        "clf_loss": total_clf_loss / max(total_samples, 1),
        "accuracy": accuracy_score(labels_int, preds) if labels_int.size else 0.0,
        "_probs": probs,
        "_labels": labels_int,
    }


@torch.no_grad()
def evaluate(
    model: InsuranceMLP,
    loader,
    criterion: ClaimClassificationLoss,
    device: torch.device,
    cfg: Config,
    split: str = "val",
) -> Dict[str, Any]:
    model.eval()
    use_amp = bool(cfg.train.use_amp and device.type == "cuda")

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
    preds = (probs >= float(cfg.train.clf_threshold)).astype(int)

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


def build_monitor_value(
    monitor_key: str,
    val_metrics: Dict[str, Any],
    threshold_metrics: Dict[str, float],
) -> float:
    if monitor_key in threshold_metrics:
        return float(threshold_metrics[monitor_key])
    return float(val_metrics[monitor_key])


def run_training(
    cfg: Config,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
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

        model = InsuranceMLP(
            input_dim=cfg.model.input_dim,
            hidden_dims=cfg.model.hidden_dims,
            head_hidden_dim=cfg.model.head_hidden_dim,
            input_dropout=cfg.model.input_dropout,
            backbone_dropout=cfg.model.backbone_dropout,
            head_dropout=cfg.model.head_dropout,
            head_samples=cfg.model.head_samples,
        ).to(device)
        criterion = ClaimClassificationLoss(
            pos_weight=resolved_pos_weight,
            label_smoothing=cfg.loss.label_smoothing,
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
                "message": "训练准备完成，开始进入 epoch 训练",
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
                threshold_search_score = float(cfg.train.clf_threshold)
                threshold_search_info = {
                    "metric": cfg.train.threshold_metric,
                    "beta": cfg.train.threshold_beta,
                    "minRecall": cfg.train.threshold_min_recall,
                    "constraintSatisfied": cfg.train.threshold_min_recall is None,
                    "selectedPrecision": None,
                    "selectedRecall": None,
                }

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
            monitor_value = build_monitor_value(monitor_key, val_metrics, threshold_metrics)

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
            add_scalar_if_not_none(writer, "val/balanced_accuracy", threshold_metrics["balanced_accuracy"], epoch)
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
                    "Saved best checkpoint (%s=%.6f, threshold=%.4f)",
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

            if cfg.train.save_every_epoch:
                epoch_path = output_dir / f"epoch_{epoch + 1:03d}.pth"
                save_checkpoint(
                    str(epoch_path),
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
                    "message": f"已完成第 {epoch + 1}/{cfg.train.num_epochs} 个 epoch",
                },
                logger,
            )

            if early_stopper is not None and early_stopper.should_stop:
                logger.info("Early stopping triggered at epoch %d", epoch + 1)
                break

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

        best_checkpoint = torch.load(cfg.path.best_model_path, map_location=device, **_TORCH_LOAD_KWARGS)
        model.load_state_dict(best_checkpoint["model"])
        final_threshold = float(best_checkpoint.get("best_threshold", best_threshold))
        if best_threshold_path.exists():
            saved_threshold = torch.load(best_threshold_path, map_location="cpu", **_TORCH_LOAD_KWARGS)
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
                "message": "训练完成",
            },
            logger,
        )

        return {
            "model": model,
            "rawTestMetrics": test_metrics,
            "history": history,
            "summary": summary,
            "artifacts": artifacts,
        }
    finally:
        if writer is not None:
            writer.close()
        close_logger(logger)


def train(cfg: Config):
    result = run_training(cfg)
    return result["model"], result["rawTestMetrics"], result["summary"]["finalThreshold"]


__all__ = [
    "EarlyStopping",
    "append_history",
    "build_latest_epoch",
    "build_optimizer",
    "build_scheduler",
    "evaluate",
    "init_history",
    "load_checkpoint",
    "resolve_monitor_metric",
    "run_training",
    "safe_round",
    "search_best_threshold",
    "serialize_metrics",
    "setup_logger",
    "train",
    "train_one_epoch",
]
