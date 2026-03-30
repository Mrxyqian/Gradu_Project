"""
trainModel.py
车险理赔预测 —— 完整训练流程

功能覆盖：
  ✅ 双任务训练（分类 + 回归）
  ✅ 混合精度训练（AMP）
  ✅ 梯度裁剪
  ✅ 学习率调度（Cosine Warmup / ReduceOnPlateau / StepLR）
  ✅ Early Stopping
  ✅ 断点续训（resume_from）
  ✅ 模型检查点保存（best / last / 每 epoch 可选）
  ✅ TensorBoard 指标记录
  ✅ 验证集评估（AUC-ROC、F1、精确率、召回率、RMSE）
  ✅ 测试集最终评估报告

使用方式：
    python trainModel.py
"""

import os
import time
import math
import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.cuda.amp import GradScaler, autocast

# PyTorch 2.6+ 默认 weights_only=True。
# 检查点由本项目训练脚本生成，来源可信，直接用 weights_only=False 加载。
# 若仍希望严格模式，可改用 add_safe_globals 逐一注册所需类型。
_TORCH_LOAD_KWARGS = {"weights_only": False}
from torch.optim.lr_scheduler import (
    CosineAnnealingLR,
    ReduceLROnPlateau,
    StepLR,
    LinearLR,
    SequentialLR,
)
from torch.utils.tensorboard import SummaryWriter
from sklearn.metrics import (
    roc_auc_score,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    classification_report,
)

from TrainConfig import Config
from DataLoader import build_dataloaders
from Model import InsuranceMLP, DualTaskLoss


# ─────────────────────────────────────────────
# 最优分类阈值搜索
# ─────────────────────────────────────────────

def search_best_threshold(
    probs: np.ndarray,
    labels: np.ndarray,
    metric: str = "f1",
    beta: float = 1.0,
    n_candidates: int = 200,
) -> tuple[float, float]:
    """
    在验证集上遍历候选阈值，找到使目标指标最优的阈值。

    参数:
        probs       : 模型输出的正类概率，shape (N,)
        labels      : 真实标签（0/1），shape (N,)
        metric      : 优化目标 'f1' | 'precision' | 'recall'
        beta        : Fbeta 的 beta 值（仅 metric='f1' 时生效）
        n_candidates: 搜索的阈值候选数量（在 [0.05, 0.95] 均匀采样）

    返回:
        best_threshold, best_score
    """
    thresholds = np.linspace(0.05, 0.95, n_candidates)
    best_threshold = 0.5
    best_score = -1.0

    for t in thresholds:
        preds = (probs >= t).astype(int)
        if metric == "f1":
            # beta=1 时用标准 f1_score；beta≠1 时用 fbeta_score
            if beta == 1.0:
                score = f1_score(labels, preds, zero_division=0)
            else:
                score = fbeta_score(labels, preds, beta=beta, zero_division=0)
        elif metric == "precision":
            score = precision_score(labels, preds, zero_division=0)
        elif metric == "recall":
            score = recall_score(labels, preds, zero_division=0)
        else:
            raise ValueError(f"未知 metric: {metric}，可选: f1 / precision / recall")

        if score > best_score:
            best_score = score
            best_threshold = t

    return float(best_threshold), float(best_score)


# ─────────────────────────────────────────────
# 日志初始化
# ─────────────────────────────────────────────

def setup_logger(log_path: str) -> logging.Logger:
    logger = logging.getLogger("InsuranceTrain")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s  %(message)s", "%Y-%m-%d %H:%M:%S")

    # 控制台输出
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # 文件输出
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ─────────────────────────────────────────────
# 优化器构建
# ─────────────────────────────────────────────

def build_optimizer(model: nn.Module, cfg: Config) -> torch.optim.Optimizer:
    oc = cfg.optimizer
    params = model.parameters()

    if oc.optimizer == "adamw":
        return torch.optim.AdamW(
            params,
            lr=oc.lr,
            betas=(oc.beta1, oc.beta2),
            eps=oc.eps,
            weight_decay=oc.weight_decay,
        )
    elif oc.optimizer == "adam":
        return torch.optim.Adam(
            params,
            lr=oc.lr,
            betas=(oc.beta1, oc.beta2),
            eps=oc.eps,
            weight_decay=oc.weight_decay,
        )
    elif oc.optimizer == "sgd":
        return torch.optim.SGD(
            params,
            lr=oc.lr,
            momentum=oc.momentum,
            nesterov=oc.nesterov,
            weight_decay=oc.weight_decay,
        )
    else:
        raise ValueError(f"未知优化器: {oc.optimizer}，可选: adamw / adam / sgd")


# ─────────────────────────────────────────────
# 学习率调度器构建
# ─────────────────────────────────────────────

def build_scheduler(optimizer: torch.optim.Optimizer, cfg: Config):
    sc = cfg.scheduler
    tc = cfg.train

    if sc.scheduler == "cosine_warmup":
        # 线性 Warmup → Cosine Annealing
        warmup = LinearLR(
            optimizer,
            start_factor=1e-3,
            end_factor=1.0,
            total_iters=sc.warmup_epochs,
        )
        cosine = CosineAnnealingLR(
            optimizer,
            T_max=max(tc.num_epochs - sc.warmup_epochs, 1),
            eta_min=sc.min_lr,
        )
        return SequentialLR(
            optimizer,
            schedulers=[warmup, cosine],
            milestones=[sc.warmup_epochs],
        ), "epoch"

    elif sc.scheduler == "reduce_on_plateau":
        return ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=sc.plateau_factor,
            patience=sc.plateau_patience,
            min_lr=sc.plateau_min_lr,
        ), "plateau"

    elif sc.scheduler == "step":
        return StepLR(optimizer, step_size=sc.step_size, gamma=sc.gamma), "epoch"

    elif sc.scheduler == "none":
        return None, "none"

    else:
        raise ValueError(f"未知调度器: {sc.scheduler}")


# ─────────────────────────────────────────────
# Early Stopping
# ─────────────────────────────────────────────

class EarlyStopping:
    """
    监控指定验证集指标，连续 patience 个 epoch 无改善则触发停止。

    支持两种模式：
      - mode='min'：监控 loss 类指标，越小越好（如 total_loss、clf_loss）
      - mode='max'：监控性能类指标，越大越好（如 AUC、F1）
    """

    def __init__(self, patience: int, min_delta: float = 1e-4, mode: str = "min"):
        self.patience    = patience
        self.min_delta   = min_delta
        self.mode        = mode
        self.best_value  = float("inf") if mode == "min" else float("-inf")
        self.counter     = 0
        self.should_stop = False

    def step(self, value: float) -> bool:
        """返回 True 表示当前 epoch 为新的最优，False 表示未改善。"""
        if self.mode == "min":
            improved = value < self.best_value - self.min_delta
        else:
            improved = value > self.best_value + self.min_delta

        if improved:
            self.best_value = value
            self.counter    = 0
            return True
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
            return False


# ─────────────────────────────────────────────
# 检查点保存 / 加载
# ─────────────────────────────────────────────

def save_checkpoint(path: str, epoch: int, model: nn.Module,
                    optimizer: torch.optim.Optimizer,
                    scheduler, best_loss: float, cfg: Config):
    torch.save({
        "epoch":      epoch,
        "model":      model.state_dict(),
        "optimizer":  optimizer.state_dict(),
        "scheduler":  scheduler.state_dict() if scheduler and hasattr(scheduler, "state_dict") else None,
        "best_loss":  best_loss,
        "input_dim":  cfg.model.input_dim,
    }, path)


def load_checkpoint(path: str, model: nn.Module,
                    optimizer: torch.optim.Optimizer,
                    scheduler, device: torch.device, logger: logging.Logger):
    ckpt = torch.load(path, map_location=device, **_TORCH_LOAD_KWARGS)
    model.load_state_dict(ckpt["model"])
    optimizer.load_state_dict(ckpt["optimizer"])
    if scheduler and ckpt.get("scheduler"):
        scheduler.load_state_dict(ckpt["scheduler"])
    start_epoch = ckpt["epoch"] + 1
    best_loss   = ckpt.get("best_loss", float("inf"))
    logger.info(f"✅ 从检查点恢复: {path}  (epoch={ckpt['epoch']}, best_loss={best_loss:.6f})")
    return start_epoch, best_loss


# ─────────────────────────────────────────────
# 单 Epoch 训练
# ─────────────────────────────────────────────

def train_one_epoch(
    model:      nn.Module,
    loader:     torch.utils.data.DataLoader,
    optimizer:  torch.optim.Optimizer,
    criterion:  DualTaskLoss,
    scaler:     GradScaler,
    device:     torch.device,
    cfg:        Config,
    epoch:      int,
    logger:     logging.Logger,
    writer:     SummaryWriter,
) -> dict:
    model.train()
    total_loss_sum = clf_loss_sum = reg_loss_sum = 0.0
    n_batches = len(loader)
    global_step = epoch * n_batches

    for batch_idx, (X, y_clf, y_reg) in enumerate(loader):
        X     = X.to(device, non_blocking=True)
        y_clf = y_clf.to(device, non_blocking=True)
        y_reg = y_reg.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        # 混合精度前向
        with autocast(enabled=cfg.train.use_amp and device.type == "cuda"):
            clf_logit, reg_pred = model(X)
            total_loss, clf_loss, reg_loss = criterion(clf_logit, reg_pred, y_clf, y_reg)

        # 反向传播
        scaler.scale(total_loss).backward()

        # 梯度裁剪
        if cfg.train.grad_clip > 0:
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), cfg.train.grad_clip)

        scaler.step(optimizer)
        scaler.update()

        total_loss_sum += total_loss.item()
        clf_loss_sum   += clf_loss.item()
        reg_loss_sum   += reg_loss.item()

        # 批次级日志
        if (batch_idx + 1) % cfg.train.log_interval == 0:
            logger.info(
                f"  Epoch {epoch:03d} [{batch_idx+1:4d}/{n_batches}] "
                f"loss={total_loss.item():.4f}  "
                f"clf={clf_loss.item():.4f}  "
                f"reg={reg_loss.item():.4f}"
            )
            writer.add_scalar("train/batch_loss",     total_loss.item(), global_step + batch_idx)
            writer.add_scalar("train/batch_clf_loss", clf_loss.item(),   global_step + batch_idx)
            writer.add_scalar("train/batch_reg_loss", reg_loss.item(),   global_step + batch_idx)

    return {
        "loss":     total_loss_sum / n_batches,
        "clf_loss": clf_loss_sum   / n_batches,
        "reg_loss": reg_loss_sum   / n_batches,
    }


# ─────────────────────────────────────────────
# 验证 / 测试评估
# ─────────────────────────────────────────────

@torch.no_grad()
def evaluate(
    model:     nn.Module,
    loader:    torch.utils.data.DataLoader,
    criterion: DualTaskLoss,
    device:    torch.device,
    cfg:       Config,
    split:     str = "val",
) -> dict:
    model.eval()
    total_loss_sum = clf_loss_sum = reg_loss_sum = 0.0

    all_probs   = []
    all_labels  = []
    all_reg_pred  = []
    all_reg_true  = []

    for X, y_clf, y_reg in loader:
        X     = X.to(device, non_blocking=True)
        y_clf = y_clf.to(device, non_blocking=True)
        y_reg = y_reg.to(device, non_blocking=True)

        with autocast(enabled=cfg.train.use_amp and device.type == "cuda"):
            clf_logit, reg_pred = model(X)
            total_loss, clf_loss, reg_loss = criterion(clf_logit, reg_pred, y_clf, y_reg)

        total_loss_sum += total_loss.item()
        clf_loss_sum   += clf_loss.item()
        reg_loss_sum   += reg_loss.item()

        probs = torch.sigmoid(clf_logit).cpu().numpy()
        all_probs.extend(probs)
        all_labels.extend(y_clf.cpu().numpy())

        # 仅收集有理赔样本的回归预测（用于 RMSE 计算）
        mask = y_clf.cpu().numpy() > 0
        if mask.sum() > 0:
            all_reg_pred.extend(reg_pred.cpu().numpy()[mask])
            all_reg_true.extend(y_reg.cpu().numpy()[mask])

    n = len(loader)
    all_probs  = np.array(all_probs)
    all_labels = np.array(all_labels)

    # 分类指标
    preds  = (all_probs >= cfg.train.clf_threshold).astype(int)
    auc    = roc_auc_score(all_labels, all_probs)
    f1     = f1_score(all_labels, preds, zero_division=0)
    prec   = precision_score(all_labels, preds, zero_division=0)
    rec    = recall_score(all_labels, preds, zero_division=0)

    # 回归指标（RMSE，原始金额尺度）
    if len(all_reg_pred) > 0:
        reg_pred_arr = np.array(all_reg_pred)
        reg_true_arr = np.array(all_reg_true)
        # 还原 log1p 变换，计算真实金额 RMSE
        rmse = float(np.sqrt(np.mean(
            (np.expm1(np.clip(reg_pred_arr, 0, None)) - np.expm1(reg_true_arr)) ** 2
        )))
        log_rmse = float(np.sqrt(np.mean((reg_pred_arr - reg_true_arr) ** 2)))
    else:
        rmse = log_rmse = 0.0

    return {
        "loss":     total_loss_sum / n,
        "clf_loss": clf_loss_sum   / n,
        "reg_loss": reg_loss_sum   / n,
        "auc":      auc,
        "f1":       f1,
        "precision": prec,
        "recall":   rec,
        "rmse":     rmse,
        "log_rmse": log_rmse,
        # 保存以备最终报告
        "_probs":   all_probs,
        "_labels":  all_labels,
    }


# ─────────────────────────────────────────────
# 主训练函数
# ─────────────────────────────────────────────

def train(cfg: Config):
    # ── 设备 ─────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ── 日志 & TensorBoard ───────────────────
    log_file = str(Path(cfg.path.output_dir) / "train.log")
    logger   = setup_logger(log_file)
    writer   = SummaryWriter(log_dir=cfg.path.log_dir)

    logger.info(f"使用设备: {device}")
    cfg.summary()

    # ── 固定随机种子 ──────────────────────────
    seed = cfg.data.random_seed
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # ── 构建 DataLoader ───────────────────────
    logger.info("━" * 50)
    logger.info("构建 DataLoader ...")
    train_loader, val_loader, test_loader, input_dim = build_dataloaders(
        csv_path      = cfg.path.csv_path,
        batch_size    = cfg.data.batch_size,
        val_ratio     = cfg.data.val_ratio,
        test_ratio    = cfg.data.test_ratio,
        random_seed   = cfg.data.random_seed,
        scaler_save_path = cfg.path.scaler_path,
        num_workers   = cfg.data.num_workers,
    )
    cfg.model.input_dim = input_dim   # 动态写回配置
    logger.info(f"输入特征维度: {input_dim}")

    # ── 构建模型 ──────────────────────────────
    logger.info("━" * 50)
    logger.info("初始化模型 ...")
    model = InsuranceMLP(
        input_dim        = cfg.model.input_dim,
        backbone_dropout = cfg.model.backbone_dropout,
        head_dropout     = cfg.model.head_dropout,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"模型总参数量: {total_params:,}")

    # ── 损失函数 ──────────────────────────────
    criterion = DualTaskLoss(
        pos_weight       = cfg.loss.pos_weight,
        init_log_var_clf = cfg.loss.init_log_var_clf,
        init_log_var_reg = cfg.loss.init_log_var_reg,
    ).to(device)

    # ── 优化器 & 调度器 ───────────────────────
    optimizer           = build_optimizer(model, cfg)
    scheduler, sched_mode = build_scheduler(optimizer, cfg)

    # ── AMP Scaler ────────────────────────────
    amp_scaler = GradScaler(enabled=cfg.train.use_amp and device.type == "cuda")

    # ── 断点续训 ──────────────────────────────
    start_epoch = 0
    best_val_loss = float("inf")
    if cfg.train.resume_from and Path(cfg.train.resume_from).exists():
        start_epoch, best_val_loss = load_checkpoint(
            cfg.train.resume_from, model, optimizer, scheduler, device, logger
        )

    # ── Early Stopping ────────────────────────
    # 根据配置选择监控指标和模式
    _es_mode = "max" if cfg.train.early_stop_metric == "auc" else "min"
    early_stopper = EarlyStopping(
        patience  = cfg.train.patience,
        min_delta = cfg.train.min_delta,
        mode      = _es_mode,
    ) if cfg.train.early_stop else None

    # 最优阈值（训练过程中在验证集上动态更新）
    best_threshold = cfg.train.clf_threshold

    # ── 训练主循环 ────────────────────────────
    logger.info("━" * 50)
    logger.info(f"开始训练  共 {cfg.train.num_epochs} epochs")
    logger.info("━" * 50)

    for epoch in range(start_epoch, cfg.train.num_epochs):
        t0 = time.time()

        # —— 训练 ——
        train_metrics = train_one_epoch(
            model, train_loader, optimizer, criterion,
            amp_scaler, device, cfg, epoch, logger, writer,
        )

        # —— 验证 ——
        val_metrics = evaluate(model, val_loader, criterion, device, cfg, split="val")

        elapsed = time.time() - t0
        lr_now  = optimizer.param_groups[0]["lr"]

        # —— 自动阈值搜索（在验证集 probs 上进行）——
        if cfg.train.auto_threshold:
            best_threshold, thresh_score = search_best_threshold(
                val_metrics["_probs"],
                val_metrics["_labels"],
                metric=cfg.train.threshold_metric,
                beta=cfg.train.threshold_beta,
            )
            # 用最优阈值重新计算 F1/Precision/Recall 用于日志展示
            preds_opt = (val_metrics["_probs"] >= best_threshold).astype(int)
            val_f1_opt  = f1_score(val_metrics["_labels"], preds_opt, zero_division=0)
            val_prec_opt = precision_score(val_metrics["_labels"], preds_opt, zero_division=0)
            val_rec_opt  = recall_score(val_metrics["_labels"], preds_opt, zero_division=0)
        else:
            val_f1_opt   = val_metrics["f1"]
            val_prec_opt = val_metrics["precision"]
            val_rec_opt  = val_metrics["recall"]
            thresh_score = val_metrics["f1"]

        logger.info(
            f"Epoch {epoch:03d}/{cfg.train.num_epochs-1} "
            f"[{elapsed:.1f}s]  lr={lr_now:.2e}  "
            f"train_loss={train_metrics['loss']:.4f}  "
            f"val_loss={val_metrics['loss']:.4f}  "
            f"val_auc={val_metrics['auc']:.4f}  "
            f"val_f1={val_f1_opt:.4f}(thr={best_threshold:.3f})  "
            f"prec={val_prec_opt:.4f}  rec={val_rec_opt:.4f}  "
            f"val_rmse={val_metrics['rmse']:.1f}"
        )

        # —— TensorBoard ——
        for k, v in train_metrics.items():
            writer.add_scalar(f"train/{k}", v, epoch)
        for k, v in val_metrics.items():
            if not k.startswith("_"):
                writer.add_scalar(f"val/{k}", v, epoch)
        writer.add_scalar("train/lr", lr_now, epoch)
        writer.add_scalar("val/best_threshold", best_threshold, epoch)
        writer.add_scalar("val/f1_at_best_threshold", val_f1_opt, epoch)
        # 记录不确定性加权的动态任务权重
        task_weights = criterion.get_task_weights()
        writer.add_scalar("loss/weight_clf", task_weights["weight_clf"], epoch)
        writer.add_scalar("loss/weight_reg", task_weights["weight_reg"], epoch)

        # —— 学习率调度 ——
        if sched_mode == "epoch" and scheduler:
            scheduler.step()
        elif sched_mode == "plateau" and scheduler:
            scheduler.step(val_metrics["loss"])

        # —— 检查点保存（以 AUC 或配置指标为准）——
        _monitor_value = val_metrics.get(cfg.train.early_stop_metric, val_metrics["loss"])
        # loss 类指标需取负值统一为"越大越好"判断
        is_best = False
        if early_stopper:
            is_best = early_stopper.step(_monitor_value)
        else:
            if _es_mode == "max":
                is_best = _monitor_value > best_val_loss
            else:
                is_best = _monitor_value < best_val_loss

        if is_best:
            best_val_loss = _monitor_value
            save_checkpoint(
                cfg.path.best_model_path, epoch, model, optimizer, scheduler, best_val_loss, cfg
            )
            # 同时保存此时的最优阈值
            torch.save({"best_threshold": best_threshold},
                       str(Path(cfg.path.output_dir) / "best_threshold.pt"))
            logger.info(
                f"  💾 Best model saved  "
                f"({cfg.train.early_stop_metric}={best_val_loss:.6f}, "
                f"threshold={best_threshold:.3f})"
            )

        # 每 epoch 存档（可选）
        if cfg.train.save_every_epoch:
            epoch_path = str(Path(cfg.path.output_dir) / f"epoch_{epoch:03d}.pth")
            save_checkpoint(epoch_path, epoch, model, optimizer, scheduler, best_val_loss, cfg)

        # 最后一个 epoch 的存档
        save_checkpoint(
            cfg.path.last_model_path, epoch, model, optimizer, scheduler, best_val_loss, cfg
        )

        # —— Early Stopping 判断 ——
        if early_stopper and early_stopper.should_stop:
            logger.info(f"⛔ Early Stopping 触发 (patience={cfg.train.patience})，提前结束训练")
            break

    writer.close()
    logger.info("━" * 50)
    logger.info("训练结束")

    # ─────────────────────────────────────────
    # 测试集最终评估（加载 best model）
    # ─────────────────────────────────────────
    logger.info("━" * 50)
    logger.info("加载 Best Model 进行测试集评估 ...")
    ckpt = torch.load(cfg.path.best_model_path, map_location=device, **_TORCH_LOAD_KWARGS)
    model.load_state_dict(ckpt["model"])

    test_metrics = evaluate(model, test_loader, criterion, device, cfg, split="test")

    # 加载训练过程中搜索到的最优阈值
    threshold_path = str(Path(cfg.path.output_dir) / "best_threshold.pt")
    if cfg.train.auto_threshold and Path(threshold_path).exists():
        saved = torch.load(threshold_path, map_location="cpu", **_TORCH_LOAD_KWARGS)
        final_threshold = saved["best_threshold"]
        logger.info(f"使用验证集最优阈值: {final_threshold:.4f}")
    else:
        final_threshold = cfg.train.clf_threshold
        logger.info(f"使用固定阈值: {final_threshold:.4f}")

    # 用最终阈值重新计算测试集分类指标
    final_preds = (test_metrics["_probs"] >= final_threshold).astype(int)
    final_f1    = f1_score(test_metrics["_labels"], final_preds, zero_division=0)
    final_prec  = precision_score(test_metrics["_labels"], final_preds, zero_division=0)
    final_rec   = recall_score(test_metrics["_labels"], final_preds, zero_division=0)

    # 显示最终动态任务权重
    task_weights = criterion.get_task_weights()

    logger.info("=" * 50)
    logger.info("  📊 测试集最终指标")
    logger.info("=" * 50)
    logger.info(f"  总损失       : {test_metrics['loss']:.4f}")
    logger.info(f"  分类损失     : {test_metrics['clf_loss']:.4f}")
    logger.info(f"  回归损失     : {test_metrics['reg_loss']:.4f}")
    logger.info(f"  动态任务权重 : clf={task_weights['weight_clf']:.4f}  reg={task_weights['weight_reg']:.4f}")
    logger.info(f"  AUC-ROC      : {test_metrics['auc']:.4f}")
    logger.info(f"  分类阈值     : {final_threshold:.4f}")
    logger.info(f"  F1 Score     : {final_f1:.4f}")
    logger.info(f"  Precision    : {final_prec:.4f}")
    logger.info(f"  Recall       : {final_rec:.4f}")
    logger.info(f"  RMSE (原始¥) : {test_metrics['rmse']:.2f}")
    logger.info(f"  RMSE (log)   : {test_metrics['log_rmse']:.4f}")
    logger.info("=" * 50)

    # 详细分类报告
    report = classification_report(
        test_metrics["_labels"], final_preds,
        target_names=["无理赔", "有理赔"],
        digits=4,
    )
    logger.info(f"\n分类详细报告:\n{report}")

    return model, test_metrics, final_threshold


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    cfg = Config()

    # ── 在此处覆盖默认参数（可选）──────────────
    # cfg.train.num_epochs   = 80
    # cfg.data.batch_size    = 256
    # cfg.optimizer.lr       = 1e-4
    # cfg.train.resume_from  = "outputs/last_model.pth"
    # ───────────────────────────────────────────

    train(cfg)