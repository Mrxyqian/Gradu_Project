from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset


DROP_COLS = [
    "ID",
    "Date_lapse",
    "Cost_claims_year",
    "N_claims_year",
]

DATE_COLS = [
    "Date_start_contract",
    "Date_last_renewal",
    "Date_next_renewal",
    "Date_birth",
    "Date_driving_licence",
]

TARGET_COLUMN = "N_claims_year"
TARGET_AMOUNT_COLUMN = "Cost_claims_year"
REFERENCE_DATE = pd.Timestamp("2020-01-01")

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

RAW_NUMERIC_COLS = [
    column for column in RAW_FEATURE_COLS if column not in DATE_COLS + ["Type_fuel"]
]

CLIP_COLS = [
    "Premium",
    "Value_vehicle",
    "Power",
    "Cylinder_capacity",
    "Weight",
    "Length",
]


def parse_date(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")
    if parsed.isna().any():
        missing_mask = parsed.isna()
        parsed.loc[missing_mask] = pd.to_datetime(
            series[missing_mask], format="%Y/%m/%d", errors="coerce"
        )
    if parsed.isna().any():
        missing_mask = parsed.isna()
        parsed.loc[missing_mask] = pd.to_datetime(
            series[missing_mask], format="%Y-%m-%d", errors="coerce"
        )
    return parsed


def date_to_days(series: pd.Series, ref: pd.Timestamp = REFERENCE_DATE) -> pd.Series:
    return (series - ref).dt.days.fillna(0).astype(np.float32)


def engineer_date_features(df: pd.DataFrame) -> pd.DataFrame:
    feature_df = df.copy()
    for column in DATE_COLS:
        feature_df[column] = parse_date(feature_df[column])

    for column in DATE_COLS:
        feature_df[f"{column}_days"] = date_to_days(feature_df[column])

    feature_df["driving_experience_years"] = (
        (REFERENCE_DATE - feature_df["Date_driving_licence"]).dt.days / 365.25
    ).clip(lower=0).fillna(0).astype(np.float32)
    feature_df["insured_age_years"] = (
        (REFERENCE_DATE - feature_df["Date_birth"]).dt.days / 365.25
    ).clip(lower=0).fillna(0).astype(np.float32)
    feature_df["contract_duration_years"] = (
        (feature_df["Date_last_renewal"] - feature_df["Date_start_contract"]).dt.days / 365.25
    ).clip(lower=0).fillna(0).astype(np.float32)
    feature_df["vehicle_age_years"] = (
        REFERENCE_DATE.year - pd.to_numeric(feature_df["Year_matriculation"], errors="coerce")
    ).clip(lower=0).fillna(0).astype(np.float32)
    return feature_df.drop(columns=DATE_COLS, errors="ignore")


def _ensure_raw_columns(df: pd.DataFrame) -> pd.DataFrame:
    feature_df = df.copy()
    for column in RAW_FEATURE_COLS:
        if column not in feature_df.columns:
            feature_df[column] = np.nan
    return feature_df


def _coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    feature_df = df.copy()
    for column in columns:
        if column in feature_df.columns:
            feature_df[column] = pd.to_numeric(feature_df[column], errors="coerce")
    return feature_df


def _infer_type_fuel_mode(df: pd.DataFrame) -> str:
    if "Type_fuel" not in df.columns:
        return "P"
    series = df["Type_fuel"].dropna().astype(str).str.upper()
    if series.empty:
        return "P"
    return str(series.mode().iloc[0]).upper()


def _infer_length_defaults(df: pd.DataFrame) -> tuple[dict[int, float], float]:
    type_risk = pd.to_numeric(df.get("Type_risk"), errors="coerce")
    length = pd.to_numeric(df.get("Length"), errors="coerce")
    stats_df = pd.DataFrame({"Type_risk": type_risk, "Length": length}).dropna()
    medians = {
        int(risk): float(value)
        for risk, value in stats_df.groupby("Type_risk")["Length"].median().items()
        if pd.notna(risk) and pd.notna(value)
    }
    global_median = float(length.median()) if length.notna().any() else 0.0
    return medians, global_median


def _encode_type_fuel(series: pd.Series, default_value: str) -> pd.Series:
    fallback = str(default_value or "P").upper()
    mapped = series.replace("", np.nan).fillna(fallback).map(
        {
            "P": 0,
            "D": 1,
            "p": 0,
            "d": 1,
            "0": 0,
            "1": 1,
            0: 0,
            1: 1,
        }
    )
    fill_value = 0.0 if fallback == "P" else 1.0
    return pd.to_numeric(mapped, errors="coerce").fillna(fill_value).astype(np.float32)


def _apply_length_fill(
    df: pd.DataFrame,
    length_defaults: dict[int, float],
    global_default: float,
) -> pd.Series:
    length = pd.to_numeric(df.get("Length"), errors="coerce")
    type_risk = pd.to_numeric(df.get("Type_risk"), errors="coerce")
    return (
        length.fillna(type_risk.map(length_defaults))
        .fillna(float(global_default))
        .astype(np.float32)
    )


def _build_fill_values(feature_df: pd.DataFrame) -> dict[str, float]:
    fill_values: dict[str, float] = {}
    for column in feature_df.columns:
        numeric = pd.to_numeric(feature_df[column], errors="coerce")
        median = numeric.median()
        fill_values[column] = float(median) if pd.notna(median) else 0.0
    return fill_values


def prepare_features(
    df: pd.DataFrame,
    *,
    raw_defaults: dict | None = None,
    feature_columns: list[str] | None = None,
    fill_values: dict[str, float] | None = None,
) -> pd.DataFrame:
    feature_df = _ensure_raw_columns(df)
    feature_df = _coerce_numeric(
        feature_df,
        RAW_NUMERIC_COLS + [TARGET_COLUMN, TARGET_AMOUNT_COLUMN],
    )
    feature_df = engineer_date_features(feature_df)

    if raw_defaults is None:
        fuel_mode = _infer_type_fuel_mode(feature_df)
        length_defaults, global_length_median = _infer_length_defaults(feature_df)
    else:
        fuel_mode = str(raw_defaults.get("type_fuel_mode", "P")).upper()
        length_defaults = {
            int(key): float(value)
            for key, value in (raw_defaults.get("length_medians_by_type_risk") or {}).items()
        }
        global_length_median = float(raw_defaults.get("global_length_median", 0.0))

    feature_df["Type_fuel"] = _encode_type_fuel(feature_df["Type_fuel"], fuel_mode)
    feature_df["Length"] = _apply_length_fill(feature_df, length_defaults, global_length_median)
    feature_df["R_Claims_history"] = (
        pd.to_numeric(feature_df.get("R_Claims_history"), errors="coerce")
        .fillna(0)
        .astype(np.float32)
    )

    feature_df = feature_df.drop(columns=DROP_COLS, errors="ignore")

    if feature_columns is not None:
        feature_df = feature_df.reindex(columns=feature_columns)

    if fill_values is None:
        fill_values = _build_fill_values(feature_df)

    for column in feature_df.columns:
        numeric = pd.to_numeric(feature_df[column], errors="coerce")
        feature_df[column] = numeric.fillna(float(fill_values.get(column, 0.0))).astype(np.float32)

    for column in CLIP_COLS:
        if column in feature_df.columns and feature_df[column].notna().any():
            upper = feature_df[column].quantile(0.999)
            if pd.notna(upper):
                feature_df[column] = feature_df[column].clip(upper=float(upper))

    return feature_df


def clean_and_engineer(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    if TARGET_COLUMN not in df.columns:
        raise KeyError(f"Missing target column: {TARGET_COLUMN}")
    labels = (
        pd.to_numeric(df[TARGET_COLUMN], errors="coerce").fillna(0).gt(0).astype(np.float32)
    )
    return prepare_features(df), labels


def build_inference_reference(df_raw: pd.DataFrame) -> dict:
    raw_source = _ensure_raw_columns(df_raw.copy())
    raw_source = _coerce_numeric(raw_source, RAW_NUMERIC_COLS + [TARGET_COLUMN, TARGET_AMOUNT_COLUMN])

    length_defaults, global_length_median = _infer_length_defaults(raw_source)
    raw_defaults = {
        "type_fuel_mode": _infer_type_fuel_mode(raw_source),
        "global_length_median": float(global_length_median),
        "length_medians_by_type_risk": length_defaults,
    }

    feature_df = prepare_features(raw_source, raw_defaults=raw_defaults)
    return {
        "raw_feature_columns": RAW_FEATURE_COLS.copy(),
        "feature_columns": feature_df.columns.tolist(),
        "feature_fill_values": _build_fill_values(feature_df),
        "raw_defaults": raw_defaults,
    }


def clean_and_engineer_for_inference(df: pd.DataFrame, reference: dict) -> pd.DataFrame:
    return prepare_features(
        df,
        raw_defaults=reference["raw_defaults"],
        feature_columns=reference["feature_columns"],
        fill_values=reference["feature_fill_values"],
    )


class InsuranceDataset(Dataset):
    def __init__(self, features: np.ndarray, labels: np.ndarray):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32)
        self.targets = self.labels

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.features[index], self.labels[index]


def build_dataloaders(
    csv_path: str,
    batch_size: int = 512,
    val_ratio: float = 0.15,
    test_ratio: float = 0.10,
    random_seed: int = 42,
    scaler_save_path: str = "scaler.pkl",
    num_workers: int = 4,
) -> tuple[DataLoader, DataLoader, DataLoader, int]:
    dataset_path = Path(csv_path)
    scaler_path = Path(scaler_save_path)
    scaler_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] Loading dataset: {dataset_path}")
    df_raw = pd.read_csv(dataset_path)

    print("[2/5] Building classification features")
    feature_df, labels = clean_and_engineer(df_raw)
    features = feature_df.to_numpy(dtype=np.float32)
    labels_np = labels.to_numpy(dtype=np.float32)

    print("[3/5] Creating train/val/test split")
    x_train_val, x_test, y_train_val, y_test = train_test_split(
        features,
        labels_np,
        test_size=test_ratio,
        random_state=random_seed,
        stratify=labels_np,
    )
    val_size = val_ratio / (1 - test_ratio)
    x_train, x_val, y_train, y_val = train_test_split(
        x_train_val,
        y_train_val,
        test_size=val_size,
        random_state=random_seed,
        stratify=y_train_val,
    )

    print("[4/5] Fitting scaler")
    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train).astype(np.float32)
    x_val = scaler.transform(x_val).astype(np.float32)
    x_test = scaler.transform(x_test).astype(np.float32)

    with open(scaler_path, "wb") as file:
        pickle.dump(scaler, file)

    print("[5/5] Building PyTorch dataloaders")
    train_dataset = InsuranceDataset(x_train, y_train)
    val_dataset = InsuranceDataset(x_val, y_val)
    test_dataset = InsuranceDataset(x_test, y_test)

    pin_memory = torch.cuda.is_available()
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=len(train_dataset) > batch_size,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size * 2,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size * 2,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )

    input_dim = int(x_train.shape[1])
    positive_rate = float(labels_np.mean()) if len(labels_np) else 0.0
    print(
        f"Done. input_dim={input_dim}, train={len(train_dataset)}, val={len(val_dataset)}, "
        f"test={len(test_dataset)}, positive_rate={positive_rate:.4f}"
    )
    return train_loader, val_loader, test_loader, input_dim


def preprocess_single(
    record: dict,
    scaler_path: str = "scaler.pkl",
    reference: dict | None = None,
) -> torch.Tensor:
    scaler_file = Path(scaler_path)
    with open(scaler_file, "rb") as file:
        scaler = pickle.load(file)

    record_df = pd.DataFrame([record])
    if reference is None:
        feature_df = prepare_features(record_df)
    else:
        feature_df = clean_and_engineer_for_inference(record_df, reference)
    features = scaler.transform(feature_df.to_numpy(dtype=np.float32)).astype(np.float32)
    return torch.tensor(features, dtype=torch.float32)


def preprocess_for_inference(
    records: list[dict],
    reference: dict,
    scaler,
) -> tuple[torch.Tensor, pd.DataFrame]:
    feature_df = clean_and_engineer_for_inference(pd.DataFrame(records), reference)
    features = scaler.transform(feature_df.to_numpy(dtype=np.float32)).astype(np.float32)
    return torch.tensor(features, dtype=torch.float32), feature_df


__all__ = [
    "DROP_COLS",
    "DATE_COLS",
    "TARGET_COLUMN",
    "TARGET_AMOUNT_COLUMN",
    "REFERENCE_DATE",
    "RAW_FEATURE_COLS",
    "InsuranceDataset",
    "build_dataloaders",
    "build_inference_reference",
    "clean_and_engineer",
    "clean_and_engineer_for_inference",
    "engineer_date_features",
    "parse_date",
    "prepare_features",
    "preprocess_for_inference",
    "preprocess_single",
]
