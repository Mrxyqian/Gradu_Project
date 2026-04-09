"""
model.py
车险理赔预测 —— 双任务 MLP 网络结构定义

网络设计要点：
  - 共享主干 (Shared Backbone)：深层残差 MLP，提取通用表示
  - 分类头 (Classification Head)：预测当年是否发生理赔（BCEWithLogitsLoss）
  - 回归头 (Regression Head)：预测当年理赔金额 log1p(Cost_claims_year)（MSELoss）
  - 残差连接 (Residual Block)：缓解深层网络梯度消失
  - LayerNorm + Dropout：提升泛化能力，防止过拟合
  - 输入维度动态适配：由 Dataloader.py 中 build_dataloaders() 返回的 input_dim 决定
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


# ─────────────────────────────────────────────
# 1. 残差块（ResidualBlock）
# ─────────────────────────────────────────────

class ResidualBlock(nn.Module):
    """
    全连接残差块：
        x → Linear → LayerNorm → GELU → Dropout → Linear → LayerNorm → + x → GELU

    当输入维度与隐层维度不一致时，通过 projection 层对齐。
    """
    def __init__(self, in_dim: int, hidden_dim: int, dropout: float = 0.3):
        super().__init__()
        self.fc1   = nn.Linear(in_dim, hidden_dim)
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.fc2   = nn.Linear(hidden_dim, hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.drop  = nn.Dropout(dropout)
        self.act   = nn.GELU()

        # 维度对齐的 shortcut
        self.shortcut = (
            nn.Linear(in_dim, hidden_dim, bias=False)
            if in_dim != hidden_dim
            else nn.Identity()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.shortcut(x)
        out = self.act(self.norm1(self.fc1(x)))
        out = self.drop(out)
        out = self.norm2(self.fc2(out))
        return self.act(out + residual)


# ─────────────────────────────────────────────
# 2. 共享主干网络（SharedBackbone）
# ─────────────────────────────────────────────

class SharedBackbone(nn.Module):
    """
    输入投影层 + 多层残差块，输出固定维度的表示向量。

    网络宽度设计（input_dim ≈ 28~32）：
        input → 256 → 512 → 512 → 256 → 256
    采用"先扩宽后收窄"的沙漏结构，先升维提取丰富特征，再压缩为紧凑表示。
    """

    def __init__(self, input_dim: int, dropout: float = 0.3):
        super().__init__()

        # 输入投影：将原始特征映射到第一个隐层
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        # 主干残差块序列
        self.blocks = nn.Sequential(
            ResidualBlock(256, 512, dropout=dropout),   # 扩宽
            ResidualBlock(512, 512, dropout=dropout),   # 深化
            ResidualBlock(512, 256, dropout=dropout),   # 收窄
            ResidualBlock(256, 256, dropout=dropout),   # 精炼
        )

        self.output_dim = 256

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_proj(x)
        x = self.blocks(x)
        return x


# ─────────────────────────────────────────────
# 3. 任务专属头（Task Heads）
# ─────────────────────────────────────────────

class ClassificationHead(nn.Module):
    """
    二分类头：是否发生理赔
    输出 logit（未经 Sigmoid），配合 BCEWithLogitsLoss 使用。
    """

    def __init__(self, in_dim: int, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),   # 输出单个 logit
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)   # shape: (B,)


class RegressionHead(nn.Module):
    """
    回归头：预测 log1p(理赔金额)
    输出无界实数，推理时用 torch.expm1() 还原为原始金额。
    """

    def __init__(self, in_dim: int, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),   # 输出单个回归值
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)   # shape: (B,)


# ─────────────────────────────────────────────
# 4. 完整双任务模型（InsuranceMLP）
# ─────────────────────────────────────────────

class InsuranceMLP(nn.Module):
    """
    车险理赔双任务预测模型。

    前向传播返回:
        clf_logit : (B,) —— 理赔发生概率的 logit
        reg_pred  : (B,) —— log1p(理赔金额) 的预测值

    推理时:
        claim_prob   = torch.sigmoid(clf_logit)
        claim_amount = torch.expm1(reg_pred.clamp(min=0))

    参数:
        input_dim   : 特征维度（由 Dataloader 动态传入）
        backbone_dropout : 主干网络 Dropout 概率
        head_dropout     : 任务头 Dropout 概率
    """

    def __init__(
        self,
        input_dim: int,
        backbone_dropout: float = 0.3,
        head_dropout: float = 0.2,
    ):
        super().__init__()
        self.backbone = SharedBackbone(input_dim, dropout=backbone_dropout)
        self.clf_head = ClassificationHead(self.backbone.output_dim, dropout=head_dropout)
        self.reg_head = RegressionHead(self.backbone.output_dim, dropout=head_dropout)

        # 权重初始化
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        shared = self.backbone(x)
        clf_logit = self.clf_head(shared)
        reg_pred  = self.reg_head(shared)
        return clf_logit, reg_pred


# ─────────────────────────────────────────────
# 5. 双任务损失函数（不确定性加权版）
# ─────────────────────────────────────────────

class DualTaskLoss(nn.Module):
    """
    双任务不确定性加权损失（Kendall & Gal, 2018）：

        L = (1 / (2 * σ_clf²)) * BCE + (1 / (2 * σ_reg²)) * MSE + log(σ_clf) + log(σ_reg)

    核心思想：
      - 用两个可学习的对数方差参数 log_var_clf、log_var_reg
        自动学习每个任务的不确定性，从而动态平衡两个任务的损失尺度。
      - 分类损失（BCE）通常量级 0.1~0.5，回归损失（MSE in log空间）通常 0.5~2.0，
        直接相加会让回归任务主导梯度；不确定性加权可自动对齐两者量级。
      - + log(σ) 正则项防止 σ 趋向无穷（即任务权重趋向零）。

    回归损失仅在实际有理赔（y_clf == 1）的样本上计算，
    避免零金额样本对回归头产生噪声梯度。

    参数:
        pos_weight   : BCE 正样本权重，用于缓解类别不平衡
                       建议值 = (负样本数 / 正样本数) ≈ 85909 / 19646 ≈ 4.37
        init_log_var_clf : 分类任务 log_var 初始值（默认 0.0，即初始权重≈0.5）
        init_log_var_reg : 回归任务 log_var 初始值（默认 0.0）
    """

    def __init__(
        self,
        pos_weight: float = 4.37,
        init_log_var_clf: float = 0.0,
        init_log_var_reg: float = 0.0,
        # 以下两个参数保留兼容旧接口，不再直接使用（由 log_var 动态替代）
        w_clf: float = 1.0,
        w_reg: float = 1.0,
    ):
        super().__init__()
        # 可学习的对数方差参数（对应各任务的噪声不确定性）
        self.log_var_clf = nn.Parameter(torch.tensor(init_log_var_clf))
        self.log_var_reg = nn.Parameter(torch.tensor(init_log_var_reg))

        self.bce = nn.BCEWithLogitsLoss(
            pos_weight=torch.tensor([pos_weight])
        )
        self.mse = nn.MSELoss(reduction="mean")

    def forward(
        self,
        clf_logit: torch.Tensor,
        reg_pred: torch.Tensor,
        y_clf: torch.Tensor,
        y_reg: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        返回:
            total_loss, clf_loss（原始，未加权）, reg_loss（原始，未加权）
        """
        # ── 原始任务损失 ────────────────────────
        clf_loss = self.bce(clf_logit, y_clf)

        mask = y_clf > 0
        if mask.sum() > 0:
            reg_loss = self.mse(reg_pred[mask], y_reg[mask])
        else:
            reg_loss = torch.tensor(0.0, device=clf_logit.device)

        # ── 不确定性加权合并 ────────────────────
        # precision_clf = exp(-log_var_clf) = 1 / σ_clf²
        # L_clf_weighted = precision_clf / 2 * clf_loss + log_var_clf / 2
        # 同理 reg 任务
        precision_clf = torch.exp(-self.log_var_clf)
        precision_reg = torch.exp(-self.log_var_reg)

        total_loss = (
            precision_clf * clf_loss + 0.5 * self.log_var_clf
            + precision_reg * reg_loss + 0.5 * self.log_var_reg
        )

        return total_loss, clf_loss, reg_loss

    def get_task_weights(self) -> dict:
        """返回当前动态权重，便于记录到 TensorBoard。"""
        return {
            "weight_clf": torch.exp(-self.log_var_clf).item(),
            "weight_reg": torch.exp(-self.log_var_reg).item(),
        }


# ─────────────────────────────────────────────
# 6. 推理工具函数
# ─────────────────────────────────────────────

@torch.no_grad()
def predict(
    model: InsuranceMLP,
    x: torch.Tensor,
    threshold: float = 0.5,
    device: str = "cpu",
) -> dict:
    """
    对输入张量进行推理，返回：
        - claim_prob   : 理赔概率 (0~1)
        - claim_flag   : 是否理赔的二值预测 (0/1)
        - claim_amount : 预测理赔金额（原始尺度，非 log）
    """
    model.eval()
    x = x.to(device)
    clf_logit, reg_pred = model(x)
    claim_prob   = torch.sigmoid(clf_logit).cpu()
    claim_flag   = (claim_prob >= threshold).long()
    claim_amount = torch.expm1(reg_pred.clamp(min=0)).cpu()
    return {
        "claim_prob":   claim_prob.numpy(),
        "claim_flag":   claim_flag.numpy(),
        "claim_amount": claim_amount.numpy(),
    }


# ─────────────────────────────────────────────
# 7. 快速调试 & 参数统计
# ─────────────────────────────────────────────

if __name__ == "__main__":
    INPUT_DIM = 28   # Dataloader 实际输出的维度，调试时用近似值

    model = InsuranceMLP(input_dim=INPUT_DIM)
    print(model)

    total_params = sum(p.numel() for p in model.parameters())
    trainable    = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n总参数量:    {total_params:,}")
    print(f"可训练参数:  {trainable:,}")

    # 模拟前向传播
    dummy_x = torch.randn(16, INPUT_DIM)
    clf_out, reg_out = model(dummy_x)
    print(f"\n分类输出形状: {clf_out.shape}")
    print(f"回归输出形状: {reg_out.shape}")

    # 损失计算测试
    criterion = DualTaskLoss(pos_weight=4.37)
    y_clf_fake = torch.randint(0, 2, (16,)).float()
    y_reg_fake = torch.rand(16) * 10
    total, clf_l, reg_l = criterion(clf_out, reg_out, y_clf_fake, y_reg_fake)
    weights = criterion.get_task_weights()
    print(f"\n总损失: {total.item():.4f}  分类损失: {clf_l.item():.4f}  回归损失: {reg_l.item():.4f}")
    print(f"当前动态权重: clf={weights['weight_clf']:.4f}  reg={weights['weight_reg']:.4f}")

    # 推理测试
    result = predict(model, dummy_x)
    print(f"\n推理结果示例（前5条）:")
    print(f"  理赔概率:  {result['claim_prob'][:5]}")
    print(f"  是否理赔:  {result['claim_flag'][:5]}")
    print(f"  预计金额:  {result['claim_amount'][:5]}")