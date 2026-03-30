"""
Dataloader.py
车险理赔预测 —— 数据清洗、特征工程与 PyTorch DataLoader 定义

双任务输出：
  - Task 1 (分类): 当年是否发生理赔  (binary: N_claims_year > 0)
  - Task 2 (回归): 当年理赔金额       (continuous: Cost_claims_year, 仅对已赔付保单有意义)
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import torch
from torch.utils.data import Dataset, DataLoader
import pickle
import os


# ─────────────────────────────────────────────
# 1. 字段配置
# ─────────────────────────────────────────────

# 直接丢弃：无预测价值 / 高度泄漏标签信息 / 纯标识符
DROP_COLS = [
    "ID",            # 保单标识符，无预测意义
    "Date_lapse",    # 70 408 条缺失，且为结果变量（退保日期）
    # 以下两列是当年理赔的直接结果，作为目标变量而非输入特征
    "Cost_claims_year",
    "N_claims_year",
]

# 日期字段 → 需要转成数值特征
DATE_COLS = [
    "Date_start_contract",
    "Date_last_renewal",
    "Date_next_renewal",
    "Date_birth",
    "Date_driving_licence",
]

# 目标列（从原始 DataFrame 中提取后再 drop）
TARGET_CLF = "N_claims_year"    # 分类：是否理赔
TARGET_REG = "Cost_claims_year"  # 回归：理赔金额

REFERENCE_DATE = pd.Timestamp("2020-01-01")  # 用于计算"距今天数"


# ─────────────────────────────────────────────
# 2. 特征工程函数
# ─────────────────────────────────────────────

def parse_date(series: pd.Series) -> pd.Series:
    """DD/MM/YYYY → Timestamp，解析失败置 NaT"""
    return pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")


def date_to_days(series: pd.Series, ref: pd.Timestamp = REFERENCE_DATE) -> pd.Series:
    """日期 → 距参考日的天数（负数=更早），NaT → 0（中性填充）"""
    delta = (series - ref).dt.days
    return delta.fillna(0).astype(np.float32)


def engineer_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """将所有日期字段转换为数值特征，并派生有意义的衍生字段"""
    df = df.copy()

    for col in DATE_COLS:
        df[col] = parse_date(df[col])

    # 距参考日天数
    for col in DATE_COLS:
        df[col + "_days"] = date_to_days(df[col])

    # 驾龄（年）：驾照发放 → 合同参考期
    df["driving_experience_years"] = (
        (REFERENCE_DATE - df["Date_driving_licence"]).dt.days / 365.25
    ).clip(lower=0).fillna(0).astype(np.float32)

    # 投保人年龄（年）
    df["insured_age_years"] = (
        (REFERENCE_DATE - df["Date_birth"]).dt.days / 365.25
    ).clip(lower=0).fillna(0).astype(np.float32)

    # 当前保单年限（年）
    df["contract_duration_years"] = (
        (df["Date_last_renewal"] - df["Date_start_contract"]).dt.days / 365.25
    ).clip(lower=0).fillna(0).astype(np.float32)

    # 车龄（年）
    df["vehicle_age_years"] = (
        REFERENCE_DATE.year - df["Year_matriculation"]
    ).clip(lower=0).astype(np.float32)

    # 删除原始日期列（已转为数值）
    df.drop(columns=DATE_COLS, inplace=True)

    return df


def clean_and_engineer(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    主清洗与特征工程流程。

    返回:
        X  : 特征 DataFrame
        y_clf : 分类目标 (0/1)
        y_reg : 回归目标 (float, log1p 变换)
    """
    df = df.copy()

    # ── 提取目标变量（在 drop 前保存）────────────────────────
    y_clf = (df[TARGET_CLF] > 0).astype(np.float32)
    y_reg = np.log1p(df[TARGET_REG].clip(lower=0)).astype(np.float32)

    # ── 删除无用列 ───────────────────────────────────────────
    df.drop(columns=DROP_COLS, inplace=True, errors="ignore")

    # ── 日期特征工程 ─────────────────────────────────────────
    df = engineer_date_features(df)

    # ── 类别型字段处理 ───────────────────────────────────────
    # Type_fuel: P→0, D→1，缺失→众数填充
    fuel_mode = df["Type_fuel"].mode()[0]
    df["Type_fuel"] = df["Type_fuel"].fillna(fuel_mode).map({"P": 0, "D": 1}).astype(np.float32)

    # ── 数值型缺失值处理 ─────────────────────────────────────
    # Length: 约 10 329 条缺失，按 Type_risk 分组用中位数填充
    # （摩托车/农用车本身无"Length"，因此需分组区别对待）
    df["Length"] = df.groupby("Type_risk")["Length"].transform(
        lambda x: x.fillna(x.median())
    )
    # 若某 Type_risk 全缺则用全局中位数补底
    global_length_median = df["Length"].median()
    df["Length"] = df["Length"].fillna(global_length_median).astype(np.float32)

    # R_Claims_history: 理论上无缺失，但保险起见
    df["R_Claims_history"] = df["R_Claims_history"].fillna(0).astype(np.float32)

    # ── 确保所有列为 float32 ─────────────────────────────────
    for col in df.select_dtypes(include=["int64", "float64"]).columns:
        df[col] = df[col].astype(np.float32)

    # ── 极端值截断（上 99.9 分位）────────────────────────────
    CLIP_COLS = ["Premium", "Value_vehicle", "Power", "Cylinder_capacity",
                 "Weight", "Length", "Cost_claims_year"]
    for col in CLIP_COLS:
        if col in df.columns:
            upper = df[col].quantile(0.999)
            df[col] = df[col].clip(upper=upper)

    return df, y_clf, y_reg


# ─────────────────────────────────────────────
# 3. PyTorch Dataset
# ─────────────────────────────────────────────

class InsuranceDataset(Dataset):
    """
    PyTorch Dataset，同时支持双任务（分类 + 回归）。

    参数:
        X       : numpy array，shape (N, F)
        y_clf   : numpy array，shape (N,)  —— 是否理赔（0/1）
        y_reg   : numpy array，shape (N,)  —— log1p(理赔金额)
    """

    def __init__(self, X: np.ndarray, y_clf: np.ndarray, y_reg: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y_clf = torch.tensor(y_clf, dtype=torch.float32)
        self.y_reg = torch.tensor(y_reg, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y_clf[idx], self.y_reg[idx]


# ─────────────────────────────────────────────
# 4. 主入口：build_dataloaders
# ─────────────────────────────────────────────

def build_dataloaders(
    csv_path: str,
    batch_size: int = 512,
    val_ratio: float = 0.15,
    test_ratio: float = 0.10,
    random_seed: int = 42,
    scaler_save_path: str = "scaler.pkl",
    num_workers: int = 4,
) -> tuple[DataLoader, DataLoader, DataLoader, int]:
    """
    端到端构建训练/验证/测试 DataLoader。

    返回:
        train_loader, val_loader, test_loader, input_dim
    """
    # 1. 读取原始数据
    print("[1/5] 读取数据 ...")
    df_raw = pd.read_csv(csv_path)
    print(f"      原始数据形状: {df_raw.shape}")

    # 2. 清洗与特征工程
    print("[2/5] 数据清洗与特征工程 ...")
    X_df, y_clf, y_reg = clean_and_engineer(df_raw)
    print(f"      特征维度: {X_df.shape[1]}  |  理赔率: {y_clf.mean():.4f}")

    X = X_df.values.astype(np.float32)
    y_clf_np = y_clf.values
    y_reg_np = y_reg.values

    # 3. 数据集拆分（先分出 test，再从剩余中分 val）
    print("[3/5] 划分数据集 ...")
    X_trainval, X_test, yc_trainval, yc_test, yr_trainval, yr_test = train_test_split(
        X, y_clf_np, y_reg_np,
        test_size=test_ratio,
        random_state=random_seed,
        stratify=y_clf_np,  # 按理赔标签分层，保证类别比例一致
    )
    val_size = val_ratio / (1 - test_ratio)
    X_train, X_val, yc_train, yc_val, yr_train, yr_val = train_test_split(
        X_trainval, yc_trainval, yr_trainval,
        test_size=val_size,
        random_state=random_seed,
        stratify=yc_trainval,
    )
    print(f"      训练集: {len(X_train)}  验证集: {len(X_val)}  测试集: {len(X_test)}")

    # 4. 特征标准化（仅在训练集上 fit）
    print("[4/5] 特征标准化 ...")
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype(np.float32)
    X_val   = scaler.transform(X_val).astype(np.float32)
    X_test  = scaler.transform(X_test).astype(np.float32)

    # 持久化 scaler，推理阶段复用
    with open(scaler_save_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"      Scaler 已保存至: {scaler_save_path}")

    # 5. 构建 DataLoader
    print("[5/5] 构建 DataLoader ...")
    train_ds = InsuranceDataset(X_train, yc_train, yr_train)
    val_ds   = InsuranceDataset(X_val,   yc_val,   yr_val)
    test_ds  = InsuranceDataset(X_test,  yc_test,  yr_test)

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size * 2,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size * 2,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )

    input_dim = X_train.shape[1]
    print(f"✅ DataLoader 构建完成，输入维度: {input_dim}")
    return train_loader, val_loader, test_loader, input_dim


# ─────────────────────────────────────────────
# 5. 推理阶段：单条样本预处理（可选工具函数）
# ─────────────────────────────────────────────

def preprocess_single(
    record: dict,
    scaler_path: str = "scaler.pkl",
) -> torch.Tensor:
    """
    将单条原始保单记录（dict）转换为模型输入张量，供在线推理使用。
    record 的键与 CSV 原始列名一致。
    """
    df = pd.DataFrame([record])
    X_df, _, _ = clean_and_engineer(df)
    X = X_df.values.astype(np.float32)
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
    X = scaler.transform(X).astype(np.float32)
    return torch.tensor(X, dtype=torch.float32)


# ─────────────────────────────────────────────
# 6. 快速调试入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    CSV_PATH = "./DataSet/Motor vehicle insurance data.csv"

    train_loader, val_loader, test_loader, input_dim = build_dataloaders(
        csv_path=CSV_PATH,
        batch_size=512,
        num_workers=0,   # Windows 调试时设 0
    )

    # 验证一个 batch 的形状
    X_batch, yc_batch, yr_batch = next(iter(train_loader))
    print(f"\nBatch 形状: X={X_batch.shape}, y_clf={yc_batch.shape}, y_reg={yr_batch.shape}")
    print(f"输入维度: {input_dim}")