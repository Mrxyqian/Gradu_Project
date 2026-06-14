from __future__ import annotations

"""
FT-Transformer 模型定义

基于 "Revisiting Deep Learning Models for Tabular Data" (Gorishniy et al., NeurIPS 2021)
对纯数值型表格数据，将每个特征映射为 token embedding，通过 Transformer 编码器
捕捉特征间的交互关系。

架构：
  FeatureTokenizer → [CLS] → Transformer Encoder (Pre-LN) → CLS Head → Logit
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class FeatureTokenizer(nn.Module):
    """将每个数值特征独立映射为 d_token 维的 token embedding。

    w_j * x_j + b_j  对每个特征 j，w_j、b_j ∈ R^d_token
    等价于 n_features 个独立的 Linear(1, d_token)。
    """

    def __init__(self, n_features: int, d_token: int):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(n_features, d_token))
        self.bias = nn.Parameter(torch.empty(n_features, d_token))
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))
        fan_in, _ = nn.init._calculate_fan_in_and_fan_out(
            self.weight.unsqueeze(1)
        )
        bound = 1.0 / math.sqrt(fan_in) if fan_in > 0 else 0.0
        nn.init.uniform_(self.bias, -bound, bound)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, n_features) → (batch, n_features, d_token)"""
        return x.unsqueeze(-1) * self.weight + self.bias


class FTTransformer(nn.Module):
    """FT-Transformer 二分类模型。

    参数
    ----
    n_features : int
        输入特征维度。
    d_token : int
        每个特征的 token embedding 维度（同时也是 Transformer 的模型维度）。
    n_layers : int
        Transformer 编码器层数。
    n_heads : int
        多头注意力的头数。d_token 必须能被 n_heads 整除。
    attn_dropout : float
        注意力 dropout 概率。
    ff_dropout : float
        前馈网络 dropout 概率。
    ff_factor : float
        FFN 隐藏层维度 = d_token * ff_factor（论文默认 4/3）。
    """

    def __init__(
        self,
        n_features: int,
        d_token: int = 192,
        n_layers: int = 3,
        n_heads: int = 8,
        attn_dropout: float = 0.15,
        ff_dropout: float = 0.15,
        ff_factor: float = 4.0 / 3.0,
    ):
        super().__init__()
        if d_token % n_heads != 0:
            raise ValueError(
                f"d_token ({d_token}) must be divisible by n_heads ({n_heads})"
            )

        self.n_features = n_features
        self.d_token = d_token
        self.n_layers = n_layers
        self.n_heads = n_heads

        self.tokenizer = FeatureTokenizer(n_features, d_token)
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_token))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_token,
            nhead=n_heads,
            dim_feedforward=int(d_token * ff_factor),
            dropout=attn_dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,  # Pre-LN
        )
        self.encoder = nn.TransformerEncoder(
            encoder_layer, num_layers=n_layers
        )

        self.cls_norm = nn.LayerNorm(d_token)
        self.head = nn.Linear(d_token, 1)

        self._init_weights()

    def _init_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, nonlinearity="relu")
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, n_features) → logits: (batch,)"""
        tokens = self.tokenizer(x)
        batch_size = tokens.shape[0]
        cls = self.cls_token.expand(batch_size, -1, -1)
        tokens = torch.cat([cls, tokens], dim=1)
        tokens = self.encoder(tokens)
        cls_out = tokens[:, 0, :]
        cls_out = self.cls_norm(cls_out)
        return self.head(cls_out).squeeze(-1)

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """返回 CLS 特征向量，可用于进一步分析。"""
        tokens = self.tokenizer(x)
        batch_size = tokens.shape[0]
        cls = self.cls_token.expand(batch_size, -1, -1)
        tokens = torch.cat([cls, tokens], dim=1)
        tokens = self.encoder(tokens)
        cls_out = tokens[:, 0, :]
        return self.cls_norm(cls_out)


def build_ft_model_from_checkpoint(
    checkpoint: dict,
    n_features: int,
) -> FTTransformer:
    """从 checkpoint 重建 FT-Transformer 模型。"""
    state_dict = checkpoint.get("model")
    if not isinstance(state_dict, dict):
        raise RuntimeError("Checkpoint is missing a valid 'model' state_dict")

    model_config = checkpoint.get("model_config") or {}
    model = FTTransformer(
        n_features=n_features,
        d_token=int(model_config.get("d_token", 192)),
        n_layers=int(model_config.get("n_layers", 3)),
        n_heads=int(model_config.get("n_heads", 8)),
        attn_dropout=float(model_config.get("attn_dropout", 0.15)),
        ff_dropout=float(model_config.get("ff_dropout", 0.15)),
        ff_factor=float(model_config.get("ff_factor", 4.0 / 3.0)),
    )
    model.load_state_dict(state_dict)
    return model
