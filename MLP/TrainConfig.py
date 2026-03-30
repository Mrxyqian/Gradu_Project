"""
config.py
车险理赔预测 —— 训练超参数与路径配置中心

所有可调参数集中在此文件，trainModel.py 直接 import 使用，
无需修改训练代码本身。
"""

from dataclasses import dataclass, field
from pathlib import Path


# ─────────────────────────────────────────────
# 路径配置
# ─────────────────────────────────────────────

@dataclass
class PathConfig:
    # 数据
    csv_path:        str = "./DataSet/Motor vehicle insurance data.csv"

    # 训练产物输出目录
    output_dir:      str = "outputs"

    # Scaler 持久化路径（供推理复用）
    scaler_path:     str = "outputs/scaler.pkl"

    # 模型检查点
    # best_*  : 验证集最优权重（用于最终评估与部署）
    # last_*  : 最后一个 epoch 权重（用于断点续训）
    best_model_path: str = "outputs/best_model.pth"
    last_model_path: str = "outputs/last_model.pth"

    # TensorBoard 日志目录
    log_dir:         str = "outputs/runs"

    def __post_init__(self):
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# 数据加载配置
# ─────────────────────────────────────────────

@dataclass
class DataConfig:
    val_ratio:    float = 0.15   # 验证集比例（从 train+val 中划出）
    test_ratio:   float = 0.10   # 测试集比例
    random_seed:  int   = 42     # 全局随机种子，保证可复现
    batch_size:   int   = 128    # 训练批大小；显存不足时调小为 256
    num_workers:  int   = 2      # DataLoader 并行线程数；Windows 建议设 0


# ─────────────────────────────────────────────
# 模型结构配置
# ─────────────────────────────────────────────

@dataclass
class ModelConfig:
    # input_dim 由 Dataloader 动态返回，此处留 -1 作为占位
    # trainModel.py 会在构建 DataLoader 后自动填入
    input_dim:          int   = -1

    backbone_dropout:   float = 0.25   # 主干残差块 Dropout 概率
    head_dropout:       float = 0.15   # 分类头/回归头 Dropout 概率


# ─────────────────────────────────────────────
# 损失函数配置
# ─────────────────────────────────────────────

@dataclass
class LossConfig:
    # 正样本权重：缓解理赔/非理赔样本不平衡
    # 计算公式：负样本数 / 正样本数 ≈ 85909 / 19646 ≈ 4.37
    pos_weight: float = 4.10

    # 不确定性加权损失的初始 log_var 值（对应 Kendall & Gal 2018）
    # 两个参数均为可学习参数，此处仅为初始化值
    # init_log_var = 0.0 时，初始有效权重 = exp(0) = 1.0（等权起步）
    # 若希望训练初期更侧重分类任务，可将 init_log_var_clf 设为负值（如 -0.5）
    # 使初始分类权重 = exp(0.5) ≈ 1.65，高于回归权重
    init_log_var_clf: float = -0.5   # 初始偏向分类任务（主任务）
    init_log_var_reg: float = 0.5    # 初始降低回归任务权重（次要任务）

    # 以下两个字段保留以兼容旧配置文件，不再参与损失计算
    w_clf: float = 1.0
    w_reg: float = 1.0


# ─────────────────────────────────────────────
# 优化器配置
# ─────────────────────────────────────────────

@dataclass
class OptimizerConfig:
    # 优化器选择：'adamw'（推荐）| 'adam' | 'sgd'
    optimizer:    str   = "adamw"

    lr:           float = 2e-4   # 初始学习率；AdamW 常用 1e-4 ~ 5e-4
    weight_decay: float = 7e-5   # L2 正则化强度；防止过拟合

    # AdamW / Adam 专属参数
    beta1:        float = 0.9
    beta2:        float = 0.999
    eps:          float = 1e-8

    # SGD 专属参数（仅 optimizer='sgd' 时生效）
    momentum:     float = 0.9
    nesterov:     bool  = True


# ─────────────────────────────────────────────
# 学习率调度器配置
# ─────────────────────────────────────────────

@dataclass
class SchedulerConfig:
    # 调度器策略：
    #   'cosine_warmup' —— 线性 Warmup + Cosine Annealing（推荐）
    #   'reduce_on_plateau' —— 验证集 loss 不降则 lr 衰减
    #   'step' —— 每 step_size 个 epoch 乘以 gamma
    #   'none' —— 不使用调度器
    scheduler: str = "cosine_warmup"

    # cosine_warmup 参数
    warmup_epochs: int   = 5       # Warmup 阶段 epoch 数
    min_lr:        float = 1e-6    # Cosine 退火最低学习率

    # reduce_on_plateau 参数
    plateau_factor:   float = 0.5   # lr 缩减倍数
    plateau_patience: int   = 5     # 容忍不提升的 epoch 数
    plateau_min_lr:   float = 1e-6

    # step 调度参数
    step_size: int   = 10
    gamma:     float = 0.5


# ─────────────────────────────────────────────
# 训练流程配置
# ─────────────────────────────────────────────

@dataclass
class TrainConfig:
    num_epochs:        int   = 100     # 总训练 epoch 数

    # Early Stopping
    early_stop:        bool  = True    # 是否启用 Early Stopping
    patience:          int   = 20      # 连续 N 个 epoch 验证集无提升则停止
    min_delta:         float = 1e-4    # 判断"有提升"的最小阈值
    # Early Stopping 监控指标：
    #   'auc'       —— 监控验证集 AUC-ROC（推荐，分类主任务的核心指标，不受阈值影响）
    #   'total_loss'—— 监控验证集总损失（会受回归任务波动干扰）
    #   'clf_loss'  —— 仅监控分类损失
    early_stop_metric: str   = "auc"

    # 混合精度训练（需要 GPU 支持 FP16，CPU 训练时自动关闭）
    use_amp:           bool  = True

    # 梯度裁剪（防止梯度爆炸）
    grad_clip:         float = 1.0    # 设为 0.0 则禁用

    # 断点续训
    resume_from:       str   = ""     # 填入 .pth 路径则从该检查点恢复训练，否则从头开始

    # 日志与检查点
    log_interval:      int   = 100    # 每 N 个 batch 打印一次训练日志
    save_every_epoch:  bool  = False  # True=每 epoch 都存档；False=只保留 best & last

    # 分类阈值设置
    # clf_threshold = 0.5 为固定阈值，适用于类别均衡场景
    # 不平衡数据集建议开启自动搜索（auto_threshold=True），
    # 将在验证集上遍历候选阈值，找到 F1 最优点，平衡 Precision 与 Recall
    clf_threshold:     float = 0.5    # 固定阈值（auto_threshold=False 时生效）
    auto_threshold:    bool  = True   # True=在验证集上自动搜索最优阈值
    threshold_metric:  str   = "f1"   # 自动搜索的优化目标：'f1' | 'precision' | 'recall'
    threshold_beta:    float = 1.3    # Fbeta 中 beta 的值：>1 偏重召回，<1 偏重精确率
                                      # beta=1 即标准 F1；若业务上漏赔代价 > 误判，可设 beta=2


# ─────────────────────────────────────────────
# 统一入口：Config
# ─────────────────────────────────────────────

@dataclass
class Config:
    """
    将所有子配置聚合为单一对象，trainModel.py 只需：

        from config import Config
        cfg = Config()
    """
    path:      PathConfig      = field(default_factory=PathConfig)
    data:      DataConfig      = field(default_factory=DataConfig)
    model:     ModelConfig     = field(default_factory=ModelConfig)
    loss:      LossConfig      = field(default_factory=LossConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    train:     TrainConfig     = field(default_factory=TrainConfig)

    def summary(self):
        """打印完整配置摘要，便于实验记录。"""
        import json, dataclasses
        print("=" * 60)
        print("         车险理赔预测模型 —— 训练配置摘要")
        print("=" * 60)
        print(json.dumps(dataclasses.asdict(self), indent=2, ensure_ascii=False))
        print("=" * 60)


# ─────────────────────────────────────────────
# 快速调试
# ─────────────────────────────────────────────

if __name__ == "__main__":
    cfg = Config()
    cfg.summary()