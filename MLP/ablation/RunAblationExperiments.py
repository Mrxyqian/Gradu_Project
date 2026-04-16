from __future__ import annotations

"""
RunAblationExperiments.py
车险理赔预测论文实验脚本

用途：
1. 对比三种不同主干隐藏层结构
2. 对比是否启用不平衡采样
3. 对比不同优化器（AdamW / Adam / SGD）
4. 自动汇总每次实验的变量与最终指标，便于写入论文

默认实验设计：
1. 网络结构对比：3 组
2. 不平衡采样对比：2 组
3. 优化器对比：3 组

总计：3 + 2 + 3 = 8 组

运行示例：
    python .\RunAblationExperiments.py

可选参数示例：
    python .\RunAblationExperiments.py --num-epochs 80 --batch-size 128 --output-tag thesis_v1
"""

import argparse
import csv
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

if __package__ in (None, ""):
    CURRENT_DIR = Path(__file__).resolve().parent
    PARENT_DIR = CURRENT_DIR.parent
    if str(CURRENT_DIR) not in sys.path:
        sys.path.insert(0, str(CURRENT_DIR))
    if str(PARENT_DIR) not in sys.path:
        sys.path.insert(0, str(PARENT_DIR))

if __package__:
    from .ExperimentTrainConfig import Config, DEFAULT_OUTPUT_DIR
    from .ExperimentTrainModel import run_training
else:
    from ExperimentTrainConfig import Config, DEFAULT_OUTPUT_DIR
    from ExperimentTrainModel import run_training


DEFAULT_BACKBONES = [
    {
        "name": "backbone_A_shallow",
        "hidden_dims": (128, 256, 128),
        "description": "浅层对称结构，参数量较小，训练速度较快",
    },
    {
        "name": "backbone_B_medium",
        "hidden_dims": (256, 256, 256),
        "description": "中等深度结构，层间维度统一，便于观察稳定性",
    },
    {
        "name": "backbone_C_deep",
        "hidden_dims": (256, 512, 512, 256, 256),
        "description": "较深主干结构，与当前项目默认主干保持一致",
    },
]

DEFAULT_BACKBONE = DEFAULT_BACKBONES[2]
DEFAULT_SAMPLING = True
DEFAULT_OPTIMIZER = "adamw"
DEFAULT_SAMPLING_OPTIONS = [False, True]
DEFAULT_OPTIMIZERS = ["adamw", "adam", "sgd"]

RESULT_FIELDS = [
    "experimentIndex",
    "experimentName",
    "backboneName",
    "hiddenDims",
    "balancedSampling",
    "optimizer",
    "experimentGroup",
    "numEpochs",
    "batchSize",
    "randomSeed",
    "auc",
    "f1",
    "recall",
    "precision",
    "prAuc",
    "accuracy",
    "balancedAccuracy",
    "loss",
    "finalThreshold",
    "epochsCompleted",
    "stoppedEarly",
    "status",
    "runDir",
    "startedAt",
    "finishedAt",
    "durationSeconds",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行车险理赔分类模型论文对比实验")
    parser.add_argument("--output-tag", type=str, default="", help="输出目录标签，便于区分不同批次实验")
    parser.add_argument("--num-epochs", type=int, default=80, help="每组实验的训练轮数")
    parser.add_argument("--batch-size", type=int, default=256, help="批大小")
    parser.add_argument("--random-seed", type=int, default=42, help="随机种子")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="验证集比例")
    parser.add_argument("--test-ratio", type=float, default=0.10, help="测试集比例")
    parser.add_argument("--num-workers", type=int, default=0, help="DataLoader 工作线程数")
    parser.add_argument("--head-hidden-dim", type=int, default=64, help="分类头隐藏层维度")
    parser.add_argument("--sampler-alpha", type=float, default=0.75, help="不平衡采样强度参数")
    parser.add_argument("--early-stop-metric", type=str, default="auc", help="早停监控指标")
    parser.add_argument("--threshold-metric", type=str, default="f1", help="阈值搜索指标")
    parser.add_argument("--threshold-beta", type=float, default=1.0, help="F-beta 中的 beta 参数")
    parser.add_argument("--csv-path", type=str, default="", help="数据集路径，默认使用项目配置路径")
    parser.add_argument("--disable-amp", action="store_true", help="禁用 AMP 混合精度训练")
    return parser.parse_args()


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_compact() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def ensure_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in RESULT_FIELDS})


def write_markdown(path: Path, rows: List[Dict[str, Any]]) -> None:
    headers = [
        "序号",
        "实验分组",
        "主干结构",
        "隐藏层",
        "不平衡采样",
        "优化器",
        "AUC-ROC",
        "F1",
        "Recall",
        "状态",
    ]
    lines = [
        "# 论文对比实验结果",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for row in rows:
        lines.append(
            "| {idx} | {group} | {backbone} | {dims} | {sampling} | {optimizer} | {auc} | {f1} | {recall} | {status} |".format(
                idx=row.get("experimentIndex", ""),
                group=row.get("experimentGroup", ""),
                backbone=row.get("backboneName", ""),
                dims=row.get("hiddenDims", ""),
                sampling="是" if row.get("balancedSampling") else "否",
                optimizer=row.get("optimizer", ""),
                auc=row.get("auc", ""),
                f1=row.get("f1", ""),
                recall=row.get("recall", ""),
                status=row.get("status", ""),
            )
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def persist_outputs(base_dir: Path, rows: List[Dict[str, Any]], meta: Dict[str, Any]) -> None:
    ordered_rows = sorted(rows, key=lambda item: int(item.get("experimentIndex", 0)))
    ensure_json(base_dir / "experiment_plan_and_results.json", {"meta": meta, "results": ordered_rows})
    write_csv(base_dir / "experiment_results.csv", ordered_rows)
    write_markdown(base_dir / "experiment_results.md", ordered_rows)


def build_experiment_plan() -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []
    index = 1

    for backbone in DEFAULT_BACKBONES:
        plan.append(
            {
                "experimentIndex": index,
                "experimentGroup": "network_structure",
                "backboneName": backbone["name"],
                "hiddenDims": tuple(backbone["hidden_dims"]),
                "backboneDescription": backbone["description"],
                "balancedSampling": DEFAULT_SAMPLING,
                "optimizer": DEFAULT_OPTIMIZER,
                "experimentName": f"{index:02d}_structure_{backbone['name']}",
            }
        )
        index += 1

    for balanced_sampling in DEFAULT_SAMPLING_OPTIONS:
        plan.append(
            {
                "experimentIndex": index,
                "experimentGroup": "balanced_sampling",
                "backboneName": DEFAULT_BACKBONE["name"],
                "hiddenDims": tuple(DEFAULT_BACKBONE["hidden_dims"]),
                "backboneDescription": DEFAULT_BACKBONE["description"],
                "balancedSampling": balanced_sampling,
                "optimizer": DEFAULT_OPTIMIZER,
                "experimentName": f"{index:02d}_sampling_{'balanced' if balanced_sampling else 'plain'}",
            }
        )
        index += 1

    for optimizer in DEFAULT_OPTIMIZERS:
        plan.append(
            {
                "experimentIndex": index,
                "experimentGroup": "optimizer",
                "backboneName": DEFAULT_BACKBONE["name"],
                "hiddenDims": tuple(DEFAULT_BACKBONE["hidden_dims"]),
                "backboneDescription": DEFAULT_BACKBONE["description"],
                "balancedSampling": DEFAULT_SAMPLING,
                "optimizer": optimizer,
                "experimentName": f"{index:02d}_optimizer_{optimizer}",
            }
        )
        index += 1

    return plan


def apply_output_paths(cfg: Config, run_dir: Path) -> None:
    cfg.path.output_dir = str(run_dir)
    cfg.path.scaler_path = str(run_dir / "scaler.pkl")
    cfg.path.best_model_path = str(run_dir / "best_model.pth")
    cfg.path.last_model_path = str(run_dir / "last_model.pth")
    cfg.path.log_dir = str(run_dir / "runs")


def build_config(args: argparse.Namespace, experiment: Dict[str, Any], run_dir: Path) -> Config:
    cfg = Config()
    apply_output_paths(cfg, run_dir)

    if args.csv_path:
        cfg.path.csv_path = args.csv_path

    cfg.data.batch_size = args.batch_size
    cfg.data.random_seed = args.random_seed
    cfg.data.val_ratio = args.val_ratio
    cfg.data.test_ratio = args.test_ratio
    cfg.data.num_workers = args.num_workers
    cfg.data.balanced_sampling = bool(experiment["balancedSampling"])
    cfg.data.sampler_alpha = args.sampler_alpha

    cfg.model.hidden_dims = tuple(int(dim) for dim in experiment["hiddenDims"])
    cfg.model.head_hidden_dim = args.head_hidden_dim

    cfg.optimizer.optimizer = str(experiment["optimizer"])

    cfg.train.num_epochs = args.num_epochs
    cfg.train.early_stop_metric = args.early_stop_metric
    cfg.train.threshold_metric = args.threshold_metric
    cfg.train.threshold_beta = args.threshold_beta
    cfg.train.use_amp = not args.disable_amp
    cfg.train.save_every_epoch = False

    return cfg


def build_result_row(
    experiment: Dict[str, Any],
    cfg: Config,
    run_dir: Path,
    result: Dict[str, Any] | None,
    started_at: str,
    finished_at: str,
    duration_seconds: float,
    status: str,
    error: str = "",
) -> Dict[str, Any]:
    final_metrics = {}
    summary = {}
    if result:
        summary = result.get("summary") or {}
        final_metrics = summary.get("finalMetrics") or {}

    return {
        "experimentIndex": experiment["experimentIndex"],
        "experimentName": experiment["experimentName"],
        "backboneName": experiment["backboneName"],
        "hiddenDims": "-".join(str(dim) for dim in experiment["hiddenDims"]),
        "balancedSampling": experiment["balancedSampling"],
        "optimizer": experiment["optimizer"],
        "experimentGroup": experiment["experimentGroup"],
        "numEpochs": cfg.train.num_epochs,
        "batchSize": cfg.data.batch_size,
        "randomSeed": cfg.data.random_seed,
        "auc": final_metrics.get("auc"),
        "f1": final_metrics.get("f1"),
        "recall": final_metrics.get("recall"),
        "precision": final_metrics.get("precision"),
        "prAuc": final_metrics.get("prAuc"),
        "accuracy": final_metrics.get("accuracy"),
        "balancedAccuracy": final_metrics.get("balancedAccuracy"),
        "loss": final_metrics.get("loss"),
        "finalThreshold": summary.get("finalThreshold"),
        "epochsCompleted": summary.get("epochsCompleted"),
        "stoppedEarly": summary.get("stoppedEarly"),
        "status": status,
        "runDir": str(run_dir.resolve()),
        "startedAt": started_at,
        "finishedAt": finished_at,
        "durationSeconds": round(duration_seconds, 2),
        "error": error,
    }


def save_single_experiment_snapshot(
    run_dir: Path,
    experiment: Dict[str, Any],
    cfg: Config,
    row: Dict[str, Any],
    result: Dict[str, Any] | None,
) -> None:
    payload = {
        "experiment": experiment,
        "resolvedConfig": {
            "csvPath": cfg.path.csv_path,
            "batchSize": cfg.data.batch_size,
            "randomSeed": cfg.data.random_seed,
            "valRatio": cfg.data.val_ratio,
            "testRatio": cfg.data.test_ratio,
            "balancedSampling": cfg.data.balanced_sampling,
            "samplerAlpha": cfg.data.sampler_alpha,
            "hiddenDims": list(cfg.model.hidden_dims),
            "headHiddenDim": cfg.model.head_hidden_dim,
            "optimizer": cfg.optimizer.optimizer,
            "numEpochs": cfg.train.num_epochs,
            "earlyStopMetric": cfg.train.early_stop_metric,
            "thresholdMetric": cfg.train.threshold_metric,
            "thresholdBeta": cfg.train.threshold_beta,
            "useAmp": cfg.train.use_amp,
        },
        "resultRow": row,
        "trainingSummary": (result or {}).get("summary"),
        "artifacts": (result or {}).get("artifacts"),
    }
    ensure_json(run_dir / "experiment_result.json", payload)


def print_plan(plan: Iterable[Dict[str, Any]]) -> None:
    print("=" * 90)
    print("车险理赔分类模型论文实验计划")
    print("=" * 90)
    for item in plan:
        print(
            f"[{item['experimentIndex']:02d}] "
            f"group={item['experimentGroup']} | "
            f"{item['backboneName']} | hidden_dims={item['hiddenDims']} | "
            f"balanced_sampling={item['balancedSampling']} | optimizer={item['optimizer']}"
        )
    print("=" * 90)


def main() -> None:
    args = parse_args()
    plan = build_experiment_plan()
    print_plan(plan)

    batch_name = f"ablation_{now_compact()}"
    if args.output_tag.strip():
        batch_name += f"_{args.output_tag.strip()}"

    base_dir = Path(DEFAULT_OUTPUT_DIR) / "ablation_study" / batch_name
    base_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "createdAt": now_text(),
        "baseDir": str(base_dir.resolve()),
        "csvPath": args.csv_path or str(Config().path.csv_path),
        "fixedSettings": {
            "numEpochs": args.num_epochs,
            "batchSize": args.batch_size,
            "randomSeed": args.random_seed,
            "valRatio": args.val_ratio,
            "testRatio": args.test_ratio,
            "numWorkers": args.num_workers,
            "headHiddenDim": args.head_hidden_dim,
            "samplerAlpha": args.sampler_alpha,
            "earlyStopMetric": args.early_stop_metric,
            "thresholdMetric": args.threshold_metric,
            "thresholdBeta": args.threshold_beta,
            "useAmp": not args.disable_amp,
        },
        "experimentFactors": {
            "backbones": DEFAULT_BACKBONES,
            "defaultBackbone": DEFAULT_BACKBONE,
            "defaultBalancedSampling": DEFAULT_SAMPLING,
            "defaultOptimizer": DEFAULT_OPTIMIZER,
            "balancedSampling": DEFAULT_SAMPLING_OPTIONS,
            "optimizers": DEFAULT_OPTIMIZERS,
        },
        "totalExperiments": len(plan),
    }
    ensure_json(base_dir / "experiment_plan.json", {"meta": meta, "plan": plan})

    results: List[Dict[str, Any]] = []

    for experiment in plan:
        run_dir = base_dir / experiment["experimentName"]
        run_dir.mkdir(parents=True, exist_ok=True)
        cfg = build_config(args, experiment, run_dir)

        started_at = now_text()
        started_ts = time.time()
        print(
            f"\n>>> 开始实验 {experiment['experimentIndex']}/{len(plan)}: "
            f"{experiment['experimentName']}"
        )

        try:
            result = run_training(cfg)
            finished_at = now_text()
            duration_seconds = time.time() - started_ts

            row = build_result_row(
                experiment=experiment,
                cfg=cfg,
                run_dir=run_dir,
                result=result,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration_seconds,
                status="success",
            )
            results.append(row)
            save_single_experiment_snapshot(run_dir, experiment, cfg, row, result)

            print(
                "    完成: AUC={auc} | F1={f1} | Recall={recall} | 用时={seconds:.2f}s".format(
                    auc=row.get("auc"),
                    f1=row.get("f1"),
                    recall=row.get("recall"),
                    seconds=duration_seconds,
                )
            )
        except Exception as exc:
            finished_at = now_text()
            duration_seconds = time.time() - started_ts
            error_text = f"{type(exc).__name__}: {exc}"
            traceback_text = traceback.format_exc()

            row = build_result_row(
                experiment=experiment,
                cfg=cfg,
                run_dir=run_dir,
                result=None,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration_seconds,
                status="failed",
                error=error_text,
            )
            results.append(row)

            ensure_json(
                run_dir / "experiment_result.json",
                {
                    "experiment": experiment,
                    "error": error_text,
                    "traceback": traceback_text,
                },
            )
            print(f"    失败: {error_text}")

        persist_outputs(base_dir, results, meta)

    success_rows = [row for row in results if row.get("status") == "success"]
    success_rows.sort(
        key=lambda item: (
            -(safe_float(item.get("auc")) or -1.0),
            -(safe_float(item.get("f1")) or -1.0),
            -(safe_float(item.get("recall")) or -1.0),
        )
    )

    print("\n" + "=" * 90)
    print("全部实验完成")
    print(f"结果目录: {base_dir.resolve()}")
    if success_rows:
        best = success_rows[0]
        print(
            "最佳实验: {name} | AUC={auc} | F1={f1} | Recall={recall}".format(
                name=best["experimentName"],
                auc=best["auc"],
                f1=best["f1"],
                recall=best["recall"],
            )
        )
    else:
        print("本次没有成功完成的实验，请检查日志。")
    print("=" * 90)


if __name__ == "__main__":
    main()
