#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型对比实验入口

在同一数据划分下依次训练 MLP 和 FT-Transformer，汇总对比结果。
输出对比表格（控制台）和 JSON 文件（MLP/outputs/benchmark_results.json）。

用法:
    cd MLP
    python -m benchmark.compare
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure MLP/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from TrainConfig import Config as MLPConfig
from TrainModel import run_training as mlp_run_training
from benchmark.ft_transformer.ft_config import FTConfig
from benchmark.ft_transformer.ft_train import ft_run_training


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs" / "benchmark"


def get_mlp_config() -> MLPConfig:
    """创建 MLP 训练配置（使用独立的输出目录，不影响现有模型）。"""
    cfg = MLPConfig()
    mlp_output = OUTPUT_DIR / "mlp"
    mlp_output.mkdir(parents=True, exist_ok=True)
    cfg.path.output_dir = str(mlp_output)
    cfg.path.scaler_path = str(mlp_output / "scaler.pkl")
    cfg.path.reference_path = str(mlp_output / "preprocess_reference.pkl")
    cfg.path.best_model_path = str(mlp_output / "best_model.pth")
    cfg.path.last_model_path = str(mlp_output / "last_model.pth")
    cfg.path.log_dir = str(mlp_output / "runs")
    return cfg


def get_ft_config() -> FTConfig:
    """创建 FT-Transformer 训练配置。"""
    cfg = FTConfig()
    ft_output = OUTPUT_DIR / "ft_transformer"
    ft_output.mkdir(parents=True, exist_ok=True)
    cfg.path.output_dir = str(ft_output)
    cfg.path.scaler_path = str(ft_output / "scaler.pkl")
    cfg.path.reference_path = str(ft_output / "preprocess_reference.pkl")
    cfg.path.best_model_path = str(ft_output / "best_model.pth")
    cfg.path.last_model_path = str(ft_output / "last_model.pth")
    cfg.path.log_dir = str(ft_output / "runs")
    return cfg


def format_table(rows: list[dict], col_keys: list[str], col_names: list[str]) -> str:
    """生成对齐的 markdown 表格字符串。"""
    col_widths = [max(len(name), max((len(str(r.get(k, ""))) for r in rows), default=0)) for k, name in zip(col_keys, col_names)]
    header = "| " + " | ".join(name.ljust(col_widths[i]) for i, name in enumerate(col_names)) + " |"
    separator = "|-" + "-|-".join("-" * col_widths[i] for i in range(len(col_widths))) + "-|"
    body_lines = []
    for row in rows:
        cells = [str(row.get(k, "")).ljust(col_widths[i]) for i, k in enumerate(col_keys)]
        body_lines.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, separator] + body_lines)


def run_benchmark():
    print("=" * 70)
    print("  车险理赔预测 —— 模型对比实验")
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = {}

    # ---------- 1. MLP ----------
    print("\n" + "=" * 70)
    print("  [1/2] 训练 Residual MLP (基线)")
    print("=" * 70)
    mlp_cfg = get_mlp_config()
    mlp_cfg.summary()
    mlp_result = mlp_run_training(mlp_cfg)
    mlp_summary = mlp_result["summary"]
    mlp_metrics = mlp_summary["finalMetrics"]
    results["Residual MLP"] = {
        "AUC": mlp_metrics["auc"],
        "PR-AUC": mlp_metrics["prAuc"],
        "F1": mlp_metrics["f1"],
        "Precision": mlp_metrics["precision"],
        "Recall": mlp_metrics["recall"],
        "Accuracy": mlp_metrics["accuracy"],
        "Balanced Acc": mlp_metrics["balancedAccuracy"],
        "Epochs": mlp_summary["epochsCompleted"],
        "Threshold": mlp_summary["finalThreshold"],
    }

    # ---------- 2. FT-Transformer ----------
    print("\n" + "=" * 70)
    print("  [2/2] 训练 FT-Transformer")
    print("=" * 70)
    ft_cfg = get_ft_config()
    ft_cfg.summary()
    ft_result = ft_run_training(ft_cfg)
    ft_summary = ft_result["summary"]
    ft_metrics = ft_summary["finalMetrics"]
    results["FT-Transformer"] = {
        "AUC": ft_metrics["auc"],
        "PR-AUC": ft_metrics["prAuc"],
        "F1": ft_metrics["f1"],
        "Precision": ft_metrics["precision"],
        "Recall": ft_metrics["recall"],
        "Accuracy": ft_metrics["accuracy"],
        "Balanced Acc": ft_metrics["balancedAccuracy"],
        "Epochs": ft_summary["epochsCompleted"],
        "Threshold": ft_summary["finalThreshold"],
        "Params": ft_summary.get("modelParams", {}).get("total", "N/A"),
    }

    # ---------- 汇总 ----------
    print("\n" + "=" * 70)
    print("  对比结果")
    print("=" * 70)

    col_keys = ["Model", "AUC", "PR-AUC", "F1", "Precision", "Recall", "Accuracy", "Balanced Acc", "Epochs"]
    col_names = ["Model", "AUC", "PR-AUC", "F1", "Precision", "Recall", "Accuracy", "Bal Acc", "Epochs"]

    table_rows = []
    for model_name, metrics in results.items():
        row = {"Model": model_name}
        row.update(metrics)
        table_rows.append(row)

    table = format_table(table_rows, col_keys, col_names)
    print(table)

    # ---------- 分类报告对比 ----------
    print("\n--- Residual MLP 分类报告 ---")
    print(mlp_summary.get("classificationReport", "N/A"))
    print("\n--- FT-Transformer 分类报告 ---")
    print(ft_summary.get("classificationReport", "N/A"))

    # ---------- 保存 JSON ----------
    output_path = OUTPUT_DIR / "benchmark_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "results": results,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n结果已保存至: {output_path}")

    return results


if __name__ == "__main__":
    run_benchmark()
