from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, WeightedRandomSampler

if __package__ in (None, ""):
    CURRENT_DIR = Path(__file__).resolve().parent
    PARENT_DIR = CURRENT_DIR.parent
    if str(CURRENT_DIR) not in sys.path:
        sys.path.insert(0, str(CURRENT_DIR))
    if str(PARENT_DIR) not in sys.path:
        sys.path.insert(0, str(PARENT_DIR))

if __package__:
    from ..DataLoader import InsuranceDataset, build_inference_reference, clean_and_engineer
else:
    from DataLoader import InsuranceDataset, build_inference_reference, clean_and_engineer


def build_dataloaders(
    csv_path: str,
    batch_size: int = 128,
    val_ratio: float = 0.15,
    test_ratio: float = 0.10,
    random_seed: int = 42,
    scaler_save_path: str = "scaler.pkl",
    reference_save_path: str = "preprocess_reference.pkl",
    num_workers: int = 2,
    balanced_sampling: bool = False,
    sampler_alpha: float = 0.75,
) -> tuple[DataLoader, DataLoader, DataLoader, int]:
    dataset_path = Path(csv_path)
    scaler_path = Path(scaler_save_path)
    reference_path = Path(reference_save_path)
    scaler_path.parent.mkdir(parents=True, exist_ok=True)
    reference_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] Loading dataset: {dataset_path}")
    df_raw = pd.read_csv(dataset_path)

    with open(reference_path, "wb") as file:
        pickle.dump(build_inference_reference(df_raw), file)

    print("[2/5] Data cleaning and feature engineering")
    feature_df, labels = clean_and_engineer(df_raw)
    features = feature_df.to_numpy(dtype=np.float32)
    labels_np = labels.to_numpy(dtype=np.float32)

    print("[3/5] Splitting dataset")
    x_trainval, x_test, y_trainval, y_test = train_test_split(
        features,
        labels_np,
        test_size=test_ratio,
        random_state=random_seed,
        stratify=labels_np,
    )
    val_size = val_ratio / (1 - test_ratio)
    x_train, x_val, y_train, y_val = train_test_split(
        x_trainval,
        y_trainval,
        test_size=val_size,
        random_state=random_seed,
        stratify=y_trainval,
    )

    print("[4/5] Feature scaling")
    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train).astype(np.float32)
    x_val = scaler.transform(x_val).astype(np.float32)
    x_test = scaler.transform(x_test).astype(np.float32)

    with open(scaler_path, "wb") as file:
        pickle.dump(scaler, file)

    print("[5/5] Building dataloaders")
    train_ds = InsuranceDataset(x_train, y_train)
    val_ds = InsuranceDataset(x_val, y_val)
    test_ds = InsuranceDataset(x_test, y_test)

    pin_memory = torch.cuda.is_available()
    train_sampler = None
    if balanced_sampling and len(train_ds) > 0:
        train_labels = y_train.astype(np.int64)
        class_counts = np.bincount(train_labels, minlength=2).astype(np.float64)
        class_counts[class_counts == 0] = 1.0
        class_weights = np.power(class_counts.max() / class_counts, float(sampler_alpha))
        sample_weights = class_weights[train_labels]
        train_sampler = WeightedRandomSampler(
            weights=torch.as_tensor(sample_weights, dtype=torch.double),
            num_samples=len(sample_weights),
            replacement=True,
        )

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=train_sampler is None,
        sampler=train_sampler,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=len(train_ds) > batch_size,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size * 2,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size * 2,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )

    input_dim = x_train.shape[1]
    positive_rate = float(labels_np.mean()) if len(labels_np) else 0.0
    print(
        f"Done. input_dim={input_dim}, train={len(train_ds)}, val={len(val_ds)}, "
        f"test={len(test_ds)}, positive_rate={positive_rate:.4f}"
    )
    return train_loader, val_loader, test_loader, int(input_dim)


__all__ = ["build_dataloaders"]
