import pandas as pd

# df = pd.read_csv('./DataSet/Motor vehicle insurance data.csv')
# has_missing = df.isnull().any()
# print(has_missing)  # 输出每列是否有缺失值:Date_lapse,Type_fuel,Length

import os
import numpy as np

# =========================
# 原地清洗机动车保险数据
# 说明：
# 1) 不修改数据集结构，不删除列，不新增业务字段。
# 2) 不做字符映射/one-hot 等额外转换。
# 3) 缺失值和异常值处理后，直接覆盖写回原文件。
# =========================

INPUT_FILE = r"./DataSet/Motor vehicle insurance data.csv"


def read_csv_auto_encoding(path: str) -> pd.DataFrame:
    """优先按 utf-8-sig 读取，失败则尝试 gbk，尽量适配中文环境。"""
    for enc in ("utf-8-sig", "gbk", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            pass
    # 兜底：交给 pandas 自动报错，便于定位问题
    return pd.read_csv(path, low_memory=False)


def fill_length_by_risk_mode(df: pd.DataFrame) -> pd.DataFrame:
    """
    Length 缺失值处理：
    - 先按相同 Type_risk 分组，用该组 Length 的众数填充；
    - 若该组没有可用众数，则用全局众数填充。

    这样既符合“参考相同 Type_risk 下其他车辆长度的众数”的要求，
    又能保持 Length 字段原始数值类型（通常为数值型）。
    """
    if "Length" not in df.columns or "Type_risk" not in df.columns:
        return df

    global_mode = df["Length"].mode(dropna=True)
    global_mode_value = global_mode.iloc[0] if len(global_mode) > 0 else np.nan

    def _fill_group(s: pd.Series) -> pd.Series:
        mode = s.mode(dropna=True)
        fill_value = mode.iloc[0] if len(mode) > 0 else global_mode_value
        return s.fillna(fill_value)

    df["Length"] = df.groupby("Type_risk", group_keys=False)["Length"].transform(_fill_group)
    # 若仍有极少数缺失（例如整列全空），再用全局众数兜底
    if df["Length"].isna().any():
        df["Length"] = df["Length"].fillna(global_mode_value)
    return df


def fill_type_fuel_by_risk_mode(df: pd.DataFrame) -> pd.DataFrame:
    """
    Type_fuel 缺失值处理：
    - 先按相同 Type_risk 分组，用该组 Type_fuel 的众数填充；
    - 若该组没有可用众数，则用全局众数填充。

    Type_fuel 是类别型字段（如 P / D），用众数填充最稳妥，且不改变字段类型。
    """
    if "Type_fuel" not in df.columns or "Type_risk" not in df.columns:
        return df

    global_mode = df["Type_fuel"].mode(dropna=True)
    global_mode_value = global_mode.iloc[0] if len(global_mode) > 0 else np.nan

    def _fill_group(s: pd.Series) -> pd.Series:
        mode = s.mode(dropna=True)
        fill_value = mode.iloc[0] if len(mode) > 0 else global_mode_value
        return s.fillna(fill_value)

    df["Type_fuel"] = df.groupby("Type_risk", group_keys=False)["Type_fuel"].transform(_fill_group)
    if df["Type_fuel"].isna().any():
        df["Type_fuel"] = df["Type_fuel"].fillna(global_mode_value)
    return df


def clip_outliers_iqr(df: pd.DataFrame) -> pd.DataFrame:
    """
    简单异常值检测与处理：IQR 剪裁（Winsorize/Clip）。

    策略：
    - 对明显的数值型业务字段做 IQR 异常检测；
    - 超出 [Q1 - 1.5*IQR, Q3 + 1.5*IQR] 的值直接截断到边界；
    - 不修改列顺序、不新增列。

    说明：
    - 不处理日期字符串列（如 Date_*），避免改变原字段类型；
    - 不处理 ID；
    - 不处理明显的类别编码列（如 Type_risk、Area、Second_driver、Payment、Distribution_channel、N_doors），
      以免把编码类字段“剪坏”。
    """
    exclude_cols = {
        "ID",
        "Type_risk",
        "Area",
        "Second_driver",
        "Payment",
        "Distribution_channel",
        "N_doors",
    }

    # 仅对数值列做处理
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    for col in numeric_cols:
        if col in exclude_cols:
            continue
        if col not in df.columns:
            continue

        s = df[col]
        # 全空、常数列或样本太少时跳过
        if s.dropna().shape[0] < 4 or s.nunique(dropna=True) <= 1:
            continue

        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        # 剪裁异常值，保持列结构不变
        clipped = s.clip(lower=lower, upper=upper)

        # 如果原列是整数型，剪裁后四舍五入并转回原 dtype，避免类型变化
        if pd.api.types.is_integer_dtype(s.dtype):
            clipped = clipped.round().astype(s.dtype)

        df[col] = clipped

    return df


def main():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"未找到文件：{INPUT_FILE}。请把脚本放在 CSV 同目录，或修改 INPUT_FILE 路径。")

    df = read_csv_auto_encoding(INPUT_FILE)

    # 保留原始数据结构，不做字段重排
    original_columns = df.columns.tolist()
    original_dtypes = df.dtypes.to_dict()

    # =========================
    # 1) 缺失值处理
    # =========================
    # Date_lapse 按你的要求不处理
    df = fill_length_by_risk_mode(df)
    df = fill_type_fuel_by_risk_mode(df)

    # =========================
    # 2) 简单异常值处理
    # =========================
    df = clip_outliers_iqr(df)

    # 恢复原字段顺序（防止任何潜在操作引入顺序变化）
    df = df[original_columns]

    # 尽量保持原 dtype：对因处理过程中可能轻微变化的整数列做回转
    for col, dtype in original_dtypes.items():
        if col in df.columns and pd.api.types.is_integer_dtype(dtype):
            # 若存在缺失，先不强行转，避免报错；这里理论上已被填充
            try:
                df[col] = df[col].round().astype(dtype)
            except Exception:
                pass
        elif col in df.columns and pd.api.types.is_float_dtype(dtype):
            try:
                df[col] = df[col].astype(dtype)
            except Exception:
                pass
        # object / category / datetime 等类型保持原样，不做额外转换

    # 原地覆盖写回
    df.to_csv(INPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"处理完成，已原地覆盖写回：{INPUT_FILE}")
    print("当前缺失值统计：")
    print(df.isna().sum())


if __name__ == "__main__":
    main()
