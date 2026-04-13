from __future__ import annotations

"""
RunPaperAblations.py

Automatic ablation runner for the first two planned studies:
1. Backbone component ablation
2. Imbalance-handling ablation

The goal is to change experiment parameters in one place instead of editing
model code before every run.
"""

import argparse
import csv
import json
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev
from time import time
from typing import Any

if __package__:
    from .AblationModel import (
        AblationLossOptions,
        AblationModelOptions,
        DEFAULT_ABLATION_HEAD_HIDDEN_DIM,
        DEFAULT_ABLATION_HIDDEN_DIMS,
    )
    from .AblationTrainModel import run_ablation_training
    from .TrainConfig import Config, DEFAULT_OUTPUT_DIR
else:
    from AblationModel import (
        AblationLossOptions,
        AblationModelOptions,
        DEFAULT_ABLATION_HEAD_HIDDEN_DIM,
        DEFAULT_ABLATION_HIDDEN_DIMS,
    )
    from AblationTrainModel import run_ablation_training
    from TrainConfig import Config, DEFAULT_OUTPUT_DIR


AVAILABLE_GROUPS = ("components", "imbalance")
FIXED_THRESHOLD = 0.5
DEFAULT_ABLATION_BATCH_SIZE = 512
RUN_RESULT_FIELDS = [
    "experimentIndex",
    "experimentName",
    "experimentKey",
    "experimentGroup",
    "description",
    "seed",
    "useResidual",
    "normType",
    "activation",
    "headType",
    "usePosWeight",
    "posWeightStrategy",
    "balancedSampling",
    "autoThreshold",
    "clfThreshold",
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
SUMMARY_FIELDS = [
    "experimentIndex",
    "experimentName",
    "experimentKey",
    "experimentGroup",
    "description",
    "numRuns",
    "aucMean",
    "aucStd",
    "f1Mean",
    "f1Std",
    "recallMean",
    "recallStd",
    "precisionMean",
    "precisionStd",
    "prAucMean",
    "prAucStd",
    "accuracyMean",
    "accuracyStd",
]


@dataclass
class ExperimentSpec:
    key: str
    group: str
    slug: str
    description: str
    model_option_overrides: dict[str, Any] = field(default_factory=dict)
    loss_option_overrides: dict[str, Any] = field(default_factory=dict)
    data_overrides: dict[str, Any] = field(default_factory=dict)
    model_overrides: dict[str, Any] = field(default_factory=dict)
    optimizer_overrides: dict[str, Any] = field(default_factory=dict)
    scheduler_overrides: dict[str, Any] = field(default_factory=dict)
    train_overrides: dict[str, Any] = field(default_factory=dict)


SHARED_BASELINE = ExperimentSpec(
    key="baseline_original",
    group="shared_baseline",
    slug="baseline_original",
    description="Original residual MLP with LayerNorm, GELU, MLP head, weighted BCE, and automatic threshold search.",
)

COMPONENT_ABLATIONS = [
    ExperimentSpec(
        key="component_no_residual",
        group="components",
        slug="no_residual",
        description="Replace residual blocks with plain feed-forward blocks while keeping the same hidden dimensions.",
        model_option_overrides={"use_residual": False},
    ),
    ExperimentSpec(
        key="component_no_norm",
        group="components",
        slug="no_norm",
        description="Remove LayerNorm from the input projection, backbone blocks, and classification head.",
        model_option_overrides={"norm_type": "none"},
    ),
    ExperimentSpec(
        key="component_relu_activation",
        group="components",
        slug="relu_activation",
        description="Keep the architecture unchanged but replace GELU with ReLU.",
        model_option_overrides={"activation": "relu"},
    ),
    ExperimentSpec(
        key="component_linear_head",
        group="components",
        slug="linear_head",
        description="Replace the two-layer MLP classification head with a single linear layer.",
        model_option_overrides={"head_type": "linear"},
    ),
]

IMBALANCE_ABLATIONS = [
    ExperimentSpec(
        key="imbalance_weighted_fixed_threshold",
        group="imbalance",
        slug="weighted_fixed_threshold",
        description="Keep weighted BCE but disable automatic threshold search and use a fixed threshold of 0.5.",
        train_overrides={"auto_threshold": False, "clf_threshold": FIXED_THRESHOLD},
    ),
    ExperimentSpec(
        key="imbalance_unweighted_auto_threshold",
        group="imbalance",
        slug="unweighted_auto_threshold",
        description="Disable positive-class weighting but keep automatic threshold search.",
        loss_option_overrides={"use_pos_weight": False},
    ),
    ExperimentSpec(
        key="imbalance_unweighted_fixed_threshold",
        group="imbalance",
        slug="unweighted_fixed_threshold",
        description="Disable positive-class weighting and use a fixed threshold of 0.5.",
        loss_option_overrides={"use_pos_weight": False},
        train_overrides={"auto_threshold": False, "clf_threshold": FIXED_THRESHOLD},
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the first two paper-ready ablation experiment groups."
    )
    parser.add_argument(
        "--groups",
        type=str,
        default="components,imbalance",
        help="Comma-separated groups to run: components, imbalance",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="42",
        help="Comma-separated random seeds, for example: 42,52,62",
    )
    parser.add_argument("--output-tag", type=str, default="", help="Optional output tag")
    parser.add_argument("--csv-path", type=str, default="", help="Optional dataset path")
    parser.add_argument("--num-epochs", type=int, default=80, help="Training epochs")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_ABLATION_BATCH_SIZE,
        help="Batch size",
    )
    parser.add_argument("--num-workers", type=int, default=0, help="DataLoader workers")
    parser.add_argument(
        "--head-hidden-dim",
        type=int,
        default=DEFAULT_ABLATION_HEAD_HIDDEN_DIM,
        help="Head hidden size",
    )
    parser.add_argument("--learning-rate", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--weight-decay", type=float, default=7e-5, help="Weight decay")
    parser.add_argument("--optimizer", type=str, default="adamw", help="Optimizer name")
    parser.add_argument("--warmup-epochs", type=int, default=5, help="Warmup epochs")
    parser.add_argument("--min-lr", type=float, default=1e-6, help="Minimum learning rate")
    parser.add_argument("--early-stop-metric", type=str, default="auc", help="Early-stop metric")
    parser.add_argument("--threshold-metric", type=str, default="f1", help="Threshold search metric")
    parser.add_argument("--threshold-beta", type=float, default=1.2, help="F-beta for threshold search")
    parser.add_argument("--disable-amp", action="store_true", help="Disable AMP")
    return parser.parse_args()


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_compact() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_groups(value: str) -> list[str]:
    groups = [item.strip().lower() for item in str(value).split(",") if item.strip()]
    invalid = [item for item in groups if item not in AVAILABLE_GROUPS]
    if invalid:
        raise ValueError(f"Unsupported groups: {', '.join(invalid)}")
    return groups or list(AVAILABLE_GROUPS)


def parse_seeds(value: str) -> list[int]:
    seeds = [int(item.strip()) for item in str(value).split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required")
    return seeds


def ensure_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def safe_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def summarize_metric(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1:
        return round(values[0], 6), 0.0
    return round(mean(values), 6), round(stdev(values), 6)


def build_plan(groups: list[str]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    templates: list[ExperimentSpec] = []

    def add(template: ExperimentSpec) -> None:
        if template.key in seen:
            return
        seen.add(template.key)
        templates.append(template)

    if "components" in groups or "imbalance" in groups:
        add(SHARED_BASELINE)
    if "components" in groups:
        for template in COMPONENT_ABLATIONS:
            add(template)
    if "imbalance" in groups:
        for template in IMBALANCE_ABLATIONS:
            add(template)

    plan: list[dict[str, Any]] = []
    for index, template in enumerate(templates, start=1):
        plan.append(
            {
                "experimentIndex": index,
                "experimentName": f"{index:02d}_{template.group}_{template.slug}",
                "spec": template,
            }
        )
    return plan


def apply_output_paths(cfg: Config, run_dir: Path) -> None:
    cfg.path.output_dir = str(run_dir)
    cfg.path.scaler_path = str(run_dir / "scaler.pkl")
    cfg.path.best_model_path = str(run_dir / "best_model.pth")
    cfg.path.last_model_path = str(run_dir / "last_model.pth")
    cfg.path.log_dir = str(run_dir / "runs")


def apply_section_overrides(section: Any, overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        setattr(section, key, value)


def build_runtime_config(
    args: argparse.Namespace,
    *,
    seed: int,
    run_dir: Path,
    spec: ExperimentSpec,
) -> tuple[Config, AblationModelOptions, AblationLossOptions]:
    cfg = Config()
    apply_output_paths(cfg, run_dir)

    if args.csv_path:
        cfg.path.csv_path = args.csv_path

    cfg.data.random_seed = seed
    cfg.data.batch_size = args.batch_size
    cfg.data.num_workers = args.num_workers
    cfg.model.hidden_dims = tuple(DEFAULT_ABLATION_HIDDEN_DIMS)
    cfg.model.head_hidden_dim = args.head_hidden_dim
    cfg.optimizer.optimizer = args.optimizer
    cfg.optimizer.lr = args.learning_rate
    cfg.optimizer.weight_decay = args.weight_decay
    cfg.scheduler.scheduler = "cosine_warmup"
    cfg.scheduler.warmup_epochs = args.warmup_epochs
    cfg.scheduler.min_lr = args.min_lr
    cfg.train.num_epochs = args.num_epochs
    cfg.train.early_stop_metric = args.early_stop_metric
    cfg.train.threshold_metric = args.threshold_metric
    cfg.train.threshold_beta = args.threshold_beta
    cfg.train.use_amp = not args.disable_amp

    apply_section_overrides(cfg.data, spec.data_overrides)
    apply_section_overrides(cfg.model, spec.model_overrides)
    apply_section_overrides(cfg.optimizer, spec.optimizer_overrides)
    apply_section_overrides(cfg.scheduler, spec.scheduler_overrides)
    apply_section_overrides(cfg.train, spec.train_overrides)

    model_options = AblationModelOptions()
    for key, value in spec.model_option_overrides.items():
        setattr(model_options, key, value)

    loss_options = AblationLossOptions()
    for key, value in spec.loss_option_overrides.items():
        setattr(loss_options, key, value)

    return cfg, model_options, loss_options


def build_run_row(
    *,
    plan_item: dict[str, Any],
    spec: ExperimentSpec,
    seed: int,
    cfg: Config,
    model_options: AblationModelOptions,
    loss_options: AblationLossOptions,
    result: dict[str, Any] | None,
    run_dir: Path,
    started_at: str,
    finished_at: str,
    duration_seconds: float,
    status: str,
    error: str = "",
) -> dict[str, Any]:
    final_metrics = ((result or {}).get("summary") or {}).get("finalMetrics") or {}
    summary = (result or {}).get("summary") or {}
    return {
        "experimentIndex": plan_item["experimentIndex"],
        "experimentName": plan_item["experimentName"],
        "experimentKey": spec.key,
        "experimentGroup": spec.group,
        "description": spec.description,
        "seed": seed,
        "useResidual": model_options.use_residual,
        "normType": model_options.norm_type,
        "activation": model_options.activation,
        "headType": model_options.head_type,
        "usePosWeight": loss_options.use_pos_weight,
        "posWeightStrategy": loss_options.pos_weight_strategy,
        "balancedSampling": cfg.data.balanced_sampling,
        "autoThreshold": cfg.train.auto_threshold,
        "clfThreshold": cfg.train.clf_threshold,
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


def build_summary_rows(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in run_rows:
        if row.get("status") != "success":
            continue
        grouped.setdefault(str(row["experimentKey"]), []).append(row)

    summary_rows: list[dict[str, Any]] = []
    for _, rows in grouped.items():
        sample = rows[0]
        auc_mean, auc_std = summarize_metric(
            [value for value in (safe_float(row.get("auc")) for row in rows) if value is not None]
        )
        f1_mean, f1_std = summarize_metric(
            [value for value in (safe_float(row.get("f1")) for row in rows) if value is not None]
        )
        recall_mean, recall_std = summarize_metric(
            [value for value in (safe_float(row.get("recall")) for row in rows) if value is not None]
        )
        precision_mean, precision_std = summarize_metric(
            [value for value in (safe_float(row.get("precision")) for row in rows) if value is not None]
        )
        pr_auc_mean, pr_auc_std = summarize_metric(
            [value for value in (safe_float(row.get("prAuc")) for row in rows) if value is not None]
        )
        accuracy_mean, accuracy_std = summarize_metric(
            [value for value in (safe_float(row.get("accuracy")) for row in rows) if value is not None]
        )

        summary_rows.append(
            {
                "experimentIndex": sample["experimentIndex"],
                "experimentName": sample["experimentName"],
                "experimentKey": sample["experimentKey"],
                "experimentGroup": sample["experimentGroup"],
                "description": sample["description"],
                "numRuns": len(rows),
                "aucMean": auc_mean,
                "aucStd": auc_std,
                "f1Mean": f1_mean,
                "f1Std": f1_std,
                "recallMean": recall_mean,
                "recallStd": recall_std,
                "precisionMean": precision_mean,
                "precisionStd": precision_std,
                "prAucMean": pr_auc_mean,
                "prAucStd": pr_auc_std,
                "accuracyMean": accuracy_mean,
                "accuracyStd": accuracy_std,
            }
        )

    summary_rows.sort(key=lambda item: int(item["experimentIndex"]))
    return summary_rows


def write_markdown_summary(path: Path, summary_rows: list[dict[str, Any]]) -> None:
    headers = [
        "Index",
        "Group",
        "Experiment",
        "Runs",
        "AUC",
        "F1",
        "Recall",
        "Precision",
    ]
    lines = [
        "# Paper Ablation Summary",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for row in summary_rows:
        lines.append(
            "| {index} | {group} | {name} | {runs} | {auc_mean} +- {auc_std} | {f1_mean} +- {f1_std} | {recall_mean} +- {recall_std} | {precision_mean} +- {precision_std} |".format(
                index=row["experimentIndex"],
                group=row["experimentGroup"],
                name=row["experimentName"],
                runs=row["numRuns"],
                auc_mean=row["aucMean"],
                auc_std=row["aucStd"],
                f1_mean=row["f1Mean"],
                f1_std=row["f1Std"],
                recall_mean=row["recallMean"],
                recall_std=row["recallStd"],
                precision_mean=row["precisionMean"],
                precision_std=row["precisionStd"],
            )
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_plan(plan: list[dict[str, Any]], seeds: list[int]) -> None:
    print("=" * 100)
    print("Paper ablation plan")
    print("=" * 100)
    print(f"Seeds: {seeds}")
    for item in plan:
        spec: ExperimentSpec = item["spec"]
        print(
            f"[{item['experimentIndex']:02d}] {item['experimentName']} | "
            f"group={spec.group} | {spec.description}"
        )
    print("=" * 100)


def main() -> None:
    args = parse_args()
    groups = parse_groups(args.groups)
    seeds = parse_seeds(args.seeds)
    plan = build_plan(groups)
    print_plan(plan, seeds)

    batch_name = f"paper_ablation_{now_compact()}"
    if args.output_tag.strip():
        batch_name += f"_{args.output_tag.strip()}"
    base_dir = Path(DEFAULT_OUTPUT_DIR) / "paper_ablation" / batch_name
    base_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "createdAt": now_text(),
        "baseDir": str(base_dir.resolve()),
        "datasetPath": args.csv_path or str(Config().path.csv_path),
        "groups": groups,
        "seeds": seeds,
        "fixedSettings": {
            "numEpochs": args.num_epochs,
            "batchSize": args.batch_size,
            "numWorkers": args.num_workers,
            "headHiddenDim": args.head_hidden_dim,
            "learningRate": args.learning_rate,
            "weightDecay": args.weight_decay,
            "optimizer": args.optimizer,
            "warmupEpochs": args.warmup_epochs,
            "minLr": args.min_lr,
            "earlyStopMetric": args.early_stop_metric,
            "thresholdMetric": args.threshold_metric,
            "thresholdBeta": args.threshold_beta,
            "useAmp": not args.disable_amp,
        },
        "plan": [
            {
                "experimentIndex": item["experimentIndex"],
                "experimentName": item["experimentName"],
                "spec": asdict(item["spec"]),
            }
            for item in plan
        ],
    }
    ensure_json(base_dir / "experiment_plan.json", meta)

    run_rows: list[dict[str, Any]] = []

    for plan_item in plan:
        spec: ExperimentSpec = plan_item["spec"]
        experiment_dir = base_dir / plan_item["experimentName"]
        experiment_dir.mkdir(parents=True, exist_ok=True)

        for seed in seeds:
            run_dir = experiment_dir / f"seed_{seed}"
            run_dir.mkdir(parents=True, exist_ok=True)
            cfg, model_options, loss_options = build_runtime_config(
                args,
                seed=seed,
                run_dir=run_dir,
                spec=spec,
            )

            started_at = now_text()
            started_ts = time()
            print(
                f"\n>>> Running {plan_item['experimentName']} | seed={seed} | "
                f"group={spec.group}"
            )

            try:
                result = run_ablation_training(
                    cfg,
                    model_options=model_options,
                    loss_options=loss_options,
                )
                finished_at = now_text()
                duration_seconds = time() - started_ts
                row = build_run_row(
                    plan_item=plan_item,
                    spec=spec,
                    seed=seed,
                    cfg=cfg,
                    model_options=model_options,
                    loss_options=loss_options,
                    result=result,
                    run_dir=run_dir,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_seconds=duration_seconds,
                    status="success",
                )
                run_rows.append(row)
                ensure_json(
                    run_dir / "experiment_result.json",
                    {
                        "experiment": asdict(spec),
                        "seed": seed,
                        "resolvedConfig": {
                            "config": asdict(cfg),
                            "modelOptions": model_options.to_dict(),
                            "lossOptions": loss_options.to_dict(),
                        },
                        "resultRow": row,
                        "trainingSummary": result.get("summary"),
                        "artifacts": result.get("artifacts"),
                    },
                )
                print(
                    "    Completed: AUC={auc} | F1={f1} | Recall={recall} | Time={seconds:.2f}s".format(
                        auc=row.get("auc"),
                        f1=row.get("f1"),
                        recall=row.get("recall"),
                        seconds=duration_seconds,
                    )
                )
            except Exception as exc:
                finished_at = now_text()
                duration_seconds = time() - started_ts
                error_text = f"{type(exc).__name__}: {exc}"
                row = build_run_row(
                    plan_item=plan_item,
                    spec=spec,
                    seed=seed,
                    cfg=cfg,
                    model_options=model_options,
                    loss_options=loss_options,
                    result=None,
                    run_dir=run_dir,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_seconds=duration_seconds,
                    status="failed",
                    error=error_text,
                )
                run_rows.append(row)
                ensure_json(
                    run_dir / "experiment_result.json",
                    {
                        "experiment": asdict(spec),
                        "seed": seed,
                        "error": error_text,
                        "traceback": traceback.format_exc(),
                    },
                )
                print(f"    Failed: {error_text}")

            summary_rows = build_summary_rows(run_rows)
            write_csv(base_dir / "experiment_runs.csv", run_rows, RUN_RESULT_FIELDS)
            write_csv(base_dir / "experiment_summary.csv", summary_rows, SUMMARY_FIELDS)
            write_markdown_summary(base_dir / "experiment_summary.md", summary_rows)
            ensure_json(
                base_dir / "experiment_results.json",
                {
                    "meta": meta,
                    "runs": run_rows,
                    "summary": summary_rows,
                },
            )

    summary_rows = build_summary_rows(run_rows)
    print("\n" + "=" * 100)
    print("All paper ablation experiments completed")
    print(f"Output directory: {base_dir.resolve()}")
    if summary_rows:
        best = max(
            summary_rows,
            key=lambda item: (
                safe_float(item.get("aucMean")) or -1.0,
                safe_float(item.get("f1Mean")) or -1.0,
                safe_float(item.get("recallMean")) or -1.0,
            ),
        )
        print(
            "Best experiment: {name} | AUC={auc} | F1={f1} | Recall={recall}".format(
                name=best["experimentName"],
                auc=best["aucMean"],
                f1=best["f1Mean"],
                recall=best["recallMean"],
            )
        )
    else:
        print("No successful experiment runs were produced.")
    print("=" * 100)


if __name__ == "__main__":
    main()
