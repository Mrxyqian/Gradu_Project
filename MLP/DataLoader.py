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

# 原始输入字段（推理阶段用于补全缺失列、对齐训练字段）
RAW_FEATURE_COLS = [
    "Date_start_contract",
    "Date_last_renewal",
    "Date_next_renewal",
    "Distribution_channel",
    "Date_birth",
    "Date_driving_licence",
    "Seniority",
    "Policies_in_force",
    "Max_policies",
    "Max_products",
    "Lapse",
    "Payment",
    "Premium",
    "N_claims_history",
    "R_Claims_history",
    "Type_risk",
    "Area",
    "Second_driver",
    "Year_matriculation",
    "Power",
    "Cylinder_capacity",
    "Value_vehicle",
    "N_doors",
    "Type_fuel",
    "Length",
    "Weight",
]


# ─────────────────────────────────────────────
# 2. 特征工程函数
# ─────────────────────────────────────────────

def parse_date(series: pd.Series) -> pd.Series:
    """兼容训练集与业务系统的多种日期格式，解析失败置 NaT"""
    parsed = pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")
    if parsed.isna().any():
        missing_mask = parsed.isna()
        parsed.loc[missing_mask] = pd.to_datetime(series[missing_mask], format="%Y/%m/%d", errors="coerce")
    if parsed.isna().any():
        missing_mask = parsed.isna()
        parsed.loc[missing_mask] = pd.to_datetime(series[missing_mask], format="%Y-%m-%d", errors="coerce")
    return parsed


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


def build_inference_reference(df_raw: pd.DataFrame) -> dict:
    """
    基于训练原始数据构建在线推理所需的参考信息：
      - 训练后的特征顺序
      - 各特征缺失填充值
      - 原始类别 / 缺失补全默认值
    """
    df_raw = df_raw.copy()
    feature_df, _, _ = clean_and_engineer(df_raw)

    length_medians = (
        df_raw.groupby("Type_risk")["Length"]
        .median()
        .dropna()
        .to_dict()
        if "Type_risk" in df_raw.columns and "Length" in df_raw.columns
        else {}
    )

    raw_type_fuel = df_raw["Type_fuel"] if "Type_fuel" in df_raw.columns else pd.Series(dtype=object)
    type_fuel_mode = raw_type_fuel.dropna().mode()
    type_fuel_mode = type_fuel_mode.iloc[0] if not type_fuel_mode.empty else "P"

    return {
        "raw_feature_columns": RAW_FEATURE_COLS.copy(),
        "feature_columns": feature_df.columns.tolist(),
        "feature_fill_values": {
            col: float(feature_df[col].median()) for col in feature_df.columns
        },
        "raw_defaults": {
            "type_fuel_mode": type_fuel_mode,
            "global_length_median": float(df_raw["Length"].dropna().median()) if "Length" in df_raw.columns else 0.0,
            "length_medians_by_type_risk": {
                int(k): float(v) for k, v in length_medians.items()
            },
        },
    }


def clean_and_engineer_for_inference(
    df: pd.DataFrame,
    reference: dict,
) -> pd.DataFrame:
    """
    在线推理专用预处理：
      - 不依赖真实标签列
      - 自动补全缺失原始字段
      - 严格按训练阶段特征顺序输出
    """
    df = df.copy()

    for col in reference["raw_feature_columns"]:
        if col not in df.columns:
            df[col] = np.nan

    # 训练阶段不允许进入模型的字段，推理阶段直接忽略
    df.drop(columns=DROP_COLS, inplace=True, errors="ignore")

    # 原始数值列统一转数值，日期列和燃料类型单独处理
    raw_numeric_cols = [col for col in reference["raw_feature_columns"] if col not in DATE_COLS + ["Type_fuel"]]
    for col in raw_numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 日期特征工程
    df = engineer_date_features(df)

    # 燃料类型：兼容 P / D / 0 / 1
    fuel_default = reference["raw_defaults"]["type_fuel_mode"]
    fuel_series = df["Type_fuel"].replace("", np.nan).fillna(fuel_default)
    df["Type_fuel"] = fuel_series.map({
        "P": 0, "D": 1,
        "p": 0, "d": 1,
        0: 0, 1: 1,
        "0": 0, "1": 1,
    })
    df["Type_fuel"] = pd.to_numeric(df["Type_fuel"], errors="coerce").fillna(
        0 if str(fuel_default).upper() == "P" else 1
    )

    # Length 缺失时优先按风险类型填充，再退化到全局中位数
    length_defaults = reference["raw_defaults"]["length_medians_by_type_risk"]
    global_length = reference["raw_defaults"]["global_length_median"]
    df["Length"] = pd.to_numeric(df["Length"], errors="coerce")
    df["Type_risk"] = pd.to_numeric(df["Type_risk"], errors="coerce")
    df["Length"] = df["Length"].fillna(df["Type_risk"].map(length_defaults))
    df["Length"] = df["Length"].fillna(global_length)

    # 历史理赔频率缺失时按 0 处理
    df["R_Claims_history"] = pd.to_numeric(df["R_Claims_history"], errors="coerce").fillna(0)

    # 严格按训练期特征顺序对齐
    feature_df = df.reindex(columns=reference["feature_columns"])

    for col in reference["feature_columns"]:
        feature_df[col] = pd.to_numeric(feature_df[col], errors="coerce")
        feature_df[col] = feature_df[col].fillna(reference["feature_fill_values"].get(col, 0.0))
        feature_df[col] = feature_df[col].astype(np.float32)

    return feature_df


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


def preprocess_for_inference(
    records: list[dict],
    reference: dict,
    scaler,
) -> tuple[torch.Tensor, pd.DataFrame]:
    """
    批量在线推理预处理入口。
    records 中的字段名应为训练原始字段名（如 Date_start_contract）。
    """
    feature_df = clean_and_engineer_for_inference(pd.DataFrame(records), reference)
    X = feature_df.values.astype(np.float32)
    X = scaler.transform(X).astype(np.float32)
    return torch.tensor(X, dtype=torch.float32), feature_df


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
