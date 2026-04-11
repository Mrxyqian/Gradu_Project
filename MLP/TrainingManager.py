from __future__ import annotations

import dataclasses
import json
import math
import re
import shutil
import threading
import traceback
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

if __package__:
    from .TrainConfig import BASE_DIR, Config
    from .TrainModel import run_training
else:
    from TrainConfig import BASE_DIR, Config
    from TrainModel import run_training


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def make_json_safe(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if dataclasses.is_dataclass(value):
        return make_json_safe(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]
    return value


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(make_json_safe(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class TrainingJobManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or (BASE_DIR / "outputs" / "training_jobs"))
        self.saved_weights_dir = BASE_DIR / "outputs" / "saved_weights"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.saved_weights_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._active_job_id: Optional[str] = None
        self._load_latest_snapshot()

    @staticmethod
    def _sanitize_job_snapshot(job: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not job:
            return job
        artifacts = job.get("artifacts")
        if isinstance(artifacts, dict):
            artifacts.pop("figureUrls", None)
        return job

    def _resolve_run_dir(self, job: Dict[str, Any]) -> Path:
        run_dir = Path(job["runDir"]).resolve()
        base_dir = self.base_dir.resolve()
        if run_dir != base_dir and base_dir not in run_dir.parents:
            raise ValueError("训练任务目录不在允许的输出范围内")
        return run_dir

    def _load_latest_snapshot(self) -> None:
        snapshot_files = sorted(
            self.base_dir.glob("*/job_state.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for snapshot_file in snapshot_files:
            try:
                snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
                self._sanitize_job_snapshot(snapshot)
                if snapshot.get("status") == "running":
                    snapshot["status"] = "failed"
                    snapshot["finishedAt"] = iso_now()
                    snapshot["error"] = "服务重启后，进行中的训练任务无法自动恢复"
                    snapshot["message"] = "训练任务已中断"
                    write_json(snapshot_file, snapshot)
                job_id = snapshot.get("jobId")
                if job_id:
                    self._jobs[job_id] = snapshot
                break
            except Exception:
                continue

    def _build_config(self, params: Dict[str, Any], run_dir: Path) -> Config:
        cfg = Config()
        run_dir.mkdir(parents=True, exist_ok=True)
        cfg.path.output_dir = str(run_dir)
        cfg.path.scaler_path = str(run_dir / "scaler.pkl")
        cfg.path.best_model_path = str(run_dir / "best_model.pth")
        cfg.path.last_model_path = str(run_dir / "last_model.pth")
        cfg.path.log_dir = str(run_dir / "runs")

        cfg.data.batch_size = int(params.get("batchSize", cfg.data.batch_size))
        cfg.data.random_seed = int(params.get("randomSeed", cfg.data.random_seed))
        cfg.data.val_ratio = float(params.get("valRatio", cfg.data.val_ratio))
        cfg.data.test_ratio = float(params.get("testRatio", cfg.data.test_ratio))
        cfg.data.num_workers = int(params.get("numWorkers", cfg.data.num_workers))

        hidden_dims = params.get("hiddenDims")
        if hidden_dims:
            cfg.model.hidden_dims = tuple(int(dim) for dim in hidden_dims)
        cfg.model.head_hidden_dim = int(params.get("headHiddenDim", cfg.model.head_hidden_dim))
        cfg.model.backbone_dropout = float(params.get("backboneDropout", cfg.model.backbone_dropout))
        cfg.model.head_dropout = float(params.get("headDropout", cfg.model.head_dropout))

        cfg.loss.pos_weight = float(params.get("posWeight", cfg.loss.pos_weight))

        cfg.optimizer.optimizer = str(params.get("optimizer", cfg.optimizer.optimizer))
        cfg.optimizer.lr = float(params.get("learningRate", cfg.optimizer.lr))
        cfg.optimizer.weight_decay = float(params.get("weightDecay", cfg.optimizer.weight_decay))

        cfg.scheduler.scheduler = "cosine_warmup"
        cfg.scheduler.warmup_epochs = int(params.get("warmupEpochs", cfg.scheduler.warmup_epochs))
        cfg.scheduler.min_lr = float(params.get("minLr", cfg.scheduler.min_lr))
        cfg.scheduler.step_size = int(params.get("stepSize", cfg.scheduler.step_size))
        cfg.scheduler.gamma = float(params.get("gamma", cfg.scheduler.gamma))
        cfg.scheduler.plateau_factor = float(params.get("plateauFactor", cfg.scheduler.plateau_factor))
        cfg.scheduler.plateau_patience = int(params.get("plateauPatience", cfg.scheduler.plateau_patience))
        cfg.scheduler.plateau_min_lr = float(params.get("plateauMinLr", cfg.scheduler.plateau_min_lr))

        cfg.train.num_epochs = int(params.get("numEpochs", cfg.train.num_epochs))
        cfg.train.early_stop = bool(params.get("earlyStop", cfg.train.early_stop))
        cfg.train.patience = int(params.get("patience", cfg.train.patience))
        cfg.train.min_delta = float(params.get("minDelta", cfg.train.min_delta))
        cfg.train.early_stop_metric = str(params.get("earlyStopMetric", cfg.train.early_stop_metric))
        cfg.train.use_amp = bool(params.get("useAmp", cfg.train.use_amp))
        cfg.train.grad_clip = float(params.get("gradClip", cfg.train.grad_clip))
        cfg.train.save_every_epoch = bool(params.get("saveEveryEpoch", cfg.train.save_every_epoch))
        cfg.train.auto_threshold = bool(params.get("autoThreshold", cfg.train.auto_threshold))
        cfg.train.clf_threshold = float(params.get("clfThreshold", cfg.train.clf_threshold))
        cfg.train.threshold_metric = str(params.get("thresholdMetric", cfg.train.threshold_metric))
        cfg.train.threshold_beta = float(params.get("thresholdBeta", cfg.train.threshold_beta))
        cfg.train.log_interval = 100
        cfg.train.resume_from = ""
        return cfg

    def _persist_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        self._sanitize_job_snapshot(job)
        snapshot_path = Path(job["runDir"]) / "job_state.json"
        write_json(snapshot_path, job)

    def _update_job(self, job_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.update(make_json_safe(payload))
            self._sanitize_job_snapshot(job)
            self._persist_job(job_id)

    def start_training(self, params: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            active_job = self._jobs.get(self._active_job_id or "", {})
            if self._active_job_id and active_job.get("status") == "running":
                raise RuntimeError("当前已有训练任务在运行，请等待完成后再启动新的训练")

            job_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
            run_dir = self.base_dir / job_id
            cfg = self._build_config(params, run_dir)
            job = {
                "jobId": job_id,
                "status": "running",
                "message": "训练任务已创建",
                "createdAt": iso_now(),
                "startedAt": iso_now(),
                "finishedAt": None,
                "currentEpoch": 0,
                "totalEpochs": cfg.train.num_epochs,
                "progress": 0.0,
                "latestEpoch": None,
                "history": {
                    "epochs": [],
                    "trainLoss": [],
                    "trainClfLoss": [],
                    "trainAccuracy": [],
                    "valLoss": [],
                    "valClfLoss": [],
                    "valAuc": [],
                    "valPrAuc": [],
                    "valAccuracy": [],
                    "valBalancedAccuracy": [],
                    "valF1": [],
                    "valPrecision": [],
                    "valRecall": [],
                    "learningRate": [],
                    "bestThreshold": [],
                    "epochSeconds": [],
                },
                "summary": None,
                "artifacts": None,
                "savedWeights": [],
                "requestParams": make_json_safe(params),
                "resolvedConfig": make_json_safe(dataclasses.asdict(cfg)),
                "runDir": str(run_dir.resolve()),
                "error": None,
                "errorDetail": None,
            }
            self._jobs[job_id] = job
            self._active_job_id = job_id
            self._persist_job(job_id)

        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, cfg),
            daemon=True,
            name=f"training-job-{job_id}",
        )
        thread.start()
        return self.get_job(job_id)

    def _run_job(self, job_id: str, cfg: Config) -> None:
        try:
            result = run_training(
                cfg,
                progress_callback=lambda payload: self._update_job(job_id, payload),
            )
            with self._lock:
                job = self._jobs.get(job_id)
                if not job:
                    return

                history = make_json_safe(result["history"])
                summary = make_json_safe(result["summary"])
                artifacts = make_json_safe(result["artifacts"])
                latest_epoch = None
                if result["history"]["epochs"]:
                    index = -1
                    latest_epoch = {
                        "epoch": history["epochs"][index],
                        "trainLoss": history["trainLoss"][index],
                        "trainClfLoss": history["trainClfLoss"][index],
                        "trainAccuracy": history["trainAccuracy"][index],
                        "valLoss": history["valLoss"][index],
                        "valClfLoss": history["valClfLoss"][index],
                        "valAuc": history["valAuc"][index],
                        "valPrAuc": history["valPrAuc"][index],
                        "valAccuracy": history["valAccuracy"][index],
                        "valBalancedAccuracy": history["valBalancedAccuracy"][index],
                        "valF1": history["valF1"][index],
                        "valPrecision": history["valPrecision"][index],
                        "valRecall": history["valRecall"][index],
                        "learningRate": history["learningRate"][index],
                        "bestThreshold": history["bestThreshold"][index],
                        "epochSeconds": history["epochSeconds"][index],
                    }

                job["status"] = "completed"
                job["message"] = "训练完成"
                job["finishedAt"] = iso_now()
                job["progress"] = 1.0
                job["currentEpoch"] = summary["epochsCompleted"]
                job["totalEpochs"] = summary["configuredEpochs"]
                job["history"] = history
                job["latestEpoch"] = latest_epoch
                job["summary"] = summary
                job["artifacts"] = artifacts
                job["error"] = None
                job["errorDetail"] = None
                self._sanitize_job_snapshot(job)
                self._active_job_id = None
                self._persist_job(job_id)
        except Exception as exc:
            with self._lock:
                job = self._jobs.get(job_id)
                if not job:
                    return
                job["status"] = "failed"
                job["message"] = "训练失败"
                job["finishedAt"] = iso_now()
                job["error"] = str(exc)
                job["errorDetail"] = traceback.format_exc()
                self._active_job_id = None
                self._persist_job(job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return self._sanitize_job_snapshot(deepcopy(job)) if job else None

    def get_latest_job(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._active_job_id and self._active_job_id in self._jobs:
                return self._sanitize_job_snapshot(deepcopy(self._jobs[self._active_job_id]))
            if not self._jobs:
                return None
            latest_job = max(
                self._jobs.values(),
                key=lambda item: item.get("createdAt") or "",
            )
            return self._sanitize_job_snapshot(deepcopy(latest_job))

    def save_weights(self, job_id: str, checkpoint_type: str, file_name: str) -> Dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError("未找到对应的训练任务")
            if job.get("status") != "completed":
                raise ValueError("仅支持在训练完成后保存权重文件")
            artifacts = deepcopy(job.get("artifacts") or {})
            self._sanitize_job_snapshot({"artifacts": artifacts})

        checkpoint_map = {
            "best": artifacts.get("bestModelPath"),
            "last": artifacts.get("lastModelPath"),
        }
        if checkpoint_type not in checkpoint_map:
            raise ValueError("checkpointType 仅支持 best 或 last")

        source_path = checkpoint_map[checkpoint_type]
        if not source_path or not Path(source_path).exists():
            raise ValueError("待保存的权重文件不存在")

        normalized_name = re.sub(r"[^A-Za-z0-9._-]+", "-", (file_name or "").strip()).strip("-.")
        if not normalized_name:
            raise ValueError("文件名不能为空")
        if not normalized_name.lower().endswith(".pth"):
            normalized_name += ".pth"

        target_path = self.saved_weights_dir / normalized_name
        if target_path.exists():
            raise ValueError("目标权重文件已存在，请更换文件名")

        shutil.copy2(source_path, target_path)
        metadata = {
            "jobId": job_id,
            "checkpointType": checkpoint_type,
            "fileName": target_path.name,
            "filePath": str(target_path.resolve()),
            "savedAt": iso_now(),
            "sourcePath": str(Path(source_path).resolve()),
            "summary": self.get_job(job_id).get("summary"),
            "relatedArtifacts": artifacts,
        }
        metadata_path = target_path.with_suffix(".json")
        write_json(metadata_path, metadata)

        saved_record = {
            "checkpointType": checkpoint_type,
            "fileName": target_path.name,
            "filePath": str(target_path.resolve()),
            "metadataPath": str(metadata_path.resolve()),
            "savedAt": metadata["savedAt"],
        }

        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.setdefault("savedWeights", []).append(saved_record)
                self._persist_job(job_id)

        return saved_record

    def get_figure_file(self, job_id: str, figure_key: str) -> Path:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError("未找到对应的训练任务")
            artifacts = job.get("artifacts") or {}
            figure_files = artifacts.get("figureFiles") or {}
            file_name = figure_files.get(figure_key)
            if not file_name:
                raise ValueError("未找到对应的图像文件")
            run_dir = self._resolve_run_dir(job)

        figure_path = (run_dir / "figures" / file_name).resolve()
        if run_dir not in figure_path.parents:
            raise ValueError("图像文件路径不合法")
        if not figure_path.exists() or not figure_path.is_file():
            raise ValueError("图像文件不存在")
        return figure_path

    def discard_job(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError("未找到对应的训练任务")
            if job.get("status") == "running":
                raise ValueError("训练任务仍在运行中，暂不支持丢弃")
            if job.get("savedWeights"):
                raise ValueError("当前训练成果已保存，不能直接丢弃")
            run_dir = self._resolve_run_dir(job)

        if run_dir.exists():
            shutil.rmtree(run_dir)

        with self._lock:
            self._jobs.pop(job_id, None)
            if self._active_job_id == job_id:
                self._active_job_id = None

        return {
            "jobId": job_id,
            "discarded": True,
            "discardedAt": iso_now(),
        }


training_manager = TrainingJobManager()
