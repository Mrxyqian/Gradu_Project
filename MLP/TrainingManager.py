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

    def _load_latest_snapshot(self) -> None:
        snapshot_files = sorted(
            self.base_dir.glob("*/job_state.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for snapshot_file in snapshot_files:
            try:
                snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
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

        cfg.data.batch_size = int(params["batchSize"])
        cfg.data.random_seed = int(params["randomSeed"])
        cfg.data.val_ratio = float(params["valRatio"])
        cfg.data.test_ratio = float(params["testRatio"])
        cfg.data.num_workers = int(params["numWorkers"])

        cfg.model.backbone_dropout = float(params["backboneDropout"])
        cfg.model.head_dropout = float(params["headDropout"])

        cfg.loss.pos_weight = float(params["posWeight"])
        cfg.loss.init_log_var_clf = float(params["initLogVarClf"])
        cfg.loss.init_log_var_reg = float(params.get("initLogVarReg", 0.0))

        cfg.optimizer.optimizer = str(params["optimizer"])
        cfg.optimizer.lr = float(params["learningRate"])
        cfg.optimizer.weight_decay = float(params["weightDecay"])

        cfg.scheduler.scheduler = str(params["scheduler"])
        cfg.scheduler.warmup_epochs = int(params["warmupEpochs"])
        cfg.scheduler.min_lr = float(params["minLr"])
        cfg.scheduler.step_size = int(params["stepSize"])
        cfg.scheduler.gamma = float(params["gamma"])
        cfg.scheduler.plateau_factor = float(params["plateauFactor"])
        cfg.scheduler.plateau_patience = int(params["plateauPatience"])
        cfg.scheduler.plateau_min_lr = float(params["plateauMinLr"])

        cfg.train.num_epochs = int(params["numEpochs"])
        cfg.train.early_stop = bool(params["earlyStop"])
        cfg.train.patience = int(params["patience"])
        cfg.train.min_delta = float(params["minDelta"])
        cfg.train.early_stop_metric = str(params["earlyStopMetric"])
        cfg.train.use_amp = bool(params["useAmp"])
        cfg.train.grad_clip = float(params["gradClip"])
        cfg.train.save_every_epoch = bool(params["saveEveryEpoch"])
        cfg.train.auto_threshold = bool(params["autoThreshold"])
        cfg.train.clf_threshold = float(params["clfThreshold"])
        cfg.train.threshold_metric = str(params["thresholdMetric"])
        cfg.train.threshold_beta = float(params["thresholdBeta"])
        cfg.train.log_interval = 100
        cfg.train.resume_from = ""
        return cfg

    def _persist_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        snapshot_path = Path(job["runDir"]) / "job_state.json"
        write_json(snapshot_path, job)

    def _update_job(self, job_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.update(make_json_safe(payload))
            self._persist_job(job_id)

    def start_training(self, params: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if self._active_job_id and self._jobs.get(self._active_job_id, {}).get("status") == "running":
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
                    "trainRegLoss": [],
                    "valLoss": [],
                    "valClfLoss": [],
                    "valRegLoss": [],
                    "valAuc": [],
                    "valAccuracy": [],
                    "valF1": [],
                    "valPrecision": [],
                    "valRecall": [],
                    "valRmse": [],
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
                job["status"] = "completed"
                job["message"] = "训练完成"
                job["finishedAt"] = iso_now()
                job["progress"] = 1.0
                job["currentEpoch"] = result["summary"]["epochsCompleted"]
                job["totalEpochs"] = result["summary"]["configuredEpochs"]
                job["history"] = make_json_safe(result["history"])
                if result["history"]["epochs"]:
                    last_idx = -1
                    job["latestEpoch"] = {
                        "epoch": result["history"]["epochs"][last_idx],
                        "trainLoss": result["history"]["trainLoss"][last_idx],
                        "trainClfLoss": result["history"]["trainClfLoss"][last_idx],
                        "trainRegLoss": result["history"]["trainRegLoss"][last_idx],
                        "valLoss": result["history"]["valLoss"][last_idx],
                        "valClfLoss": result["history"]["valClfLoss"][last_idx],
                        "valRegLoss": result["history"]["valRegLoss"][last_idx],
                        "valAuc": result["history"]["valAuc"][last_idx],
                        "valAccuracy": result["history"]["valAccuracy"][last_idx],
                        "valF1": result["history"]["valF1"][last_idx],
                        "valPrecision": result["history"]["valPrecision"][last_idx],
                        "valRecall": result["history"]["valRecall"][last_idx],
                        "valRmse": result["history"]["valRmse"][last_idx],
                        "learningRate": result["history"]["learningRate"][last_idx],
                        "bestThreshold": result["history"]["bestThreshold"][last_idx],
                        "epochSeconds": result["history"]["epochSeconds"][last_idx],
                    }
                job["summary"] = make_json_safe(result["summary"])
                job["artifacts"] = make_json_safe(result["artifacts"])
                job["error"] = None
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
            return deepcopy(job) if job else None

    def get_latest_job(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._active_job_id and self._active_job_id in self._jobs:
                return deepcopy(self._jobs[self._active_job_id])
            if not self._jobs:
                return None
            latest_job = max(
                self._jobs.values(),
                key=lambda item: item.get("createdAt") or "",
            )
            return deepcopy(latest_job)

    def save_weights(self, job_id: str, checkpoint_type: str, file_name: str) -> Dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError("未找到对应的训练任务")
            if job.get("status") != "completed":
                raise ValueError("仅支持在训练完成后保存权重文件")
            artifacts = job.get("artifacts") or {}

        checkpoint_map = {
            "best": artifacts.get("bestModelPath"),
            "last": artifacts.get("lastModelPath"),
        }
        source_path = checkpoint_map.get(checkpoint_type)
        if checkpoint_type not in checkpoint_map:
            raise ValueError("checkpointType 仅支持 best 或 last")
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
            "summary": artifacts and self.get_job(job_id).get("summary"),
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


training_manager = TrainingJobManager()
