from __future__ import annotations

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch

if __package__:
    from .DataLoader import build_inference_reference, preprocess_for_inference
    from .DatabaseUtils import load_training_dataframe
    from .Model import build_model_from_checkpoint
else:
    from DataLoader import build_inference_reference, preprocess_for_inference
    from DatabaseUtils import load_training_dataframe
    from Model import build_model_from_checkpoint


_TORCH_LOAD_KWARGS = {"weights_only": False}


RAW_TO_CAMEL = {
    "Date_start_contract": "dateStartContract",
    "Date_last_renewal": "dateLastRenewal",
    "Date_next_renewal": "dateNextRenewal",
    "Distribution_channel": "distributionChannel",
    "Date_birth": "dateBirth",
    "Date_driving_licence": "dateDrivingLicence",
    "Seniority": "seniority",
    "Policies_in_force": "policiesInForce",
    "Max_policies": "maxPolicies",
    "Max_products": "maxProducts",
    "Lapse": "lapse",
    "Payment": "payment",
    "Premium": "premium",
    "N_claims_history": "nClaimsHistory",
    "R_Claims_history": "rClaimsHistory",
    "Type_risk": "typeRisk",
    "Area": "area",
    "Second_driver": "secondDriver",
    "Year_matriculation": "yearMatriculation",
    "Power": "power",
    "Cylinder_capacity": "cylinderCapacity",
    "Value_vehicle": "valueVehicle",
    "N_doors": "nDoors",
    "Type_fuel": "typeFuel",
    "Length": "length",
    "Weight": "weight",
}

CAMEL_TO_RAW = {value: key for key, value in RAW_TO_CAMEL.items()}


class InsuranceInferenceService:
    def __init__(
        self,
        base_dir: Optional[str] = None,
        risk_low_threshold: float = 0.30,
        risk_high_threshold: float = 0.60,
    ):
        self.base_dir = Path(base_dir or Path(__file__).resolve().parent)
        self.train_table = "train_data"
        self.scaler_path = self.base_dir / "outputs" / "scaler.pkl"
        self.reference_path = self.base_dir / "outputs" / "preprocess_reference.pkl"
        self.best_model_path = self.base_dir / "outputs" / "best_model.pth"
        self.best_threshold_path = self.base_dir / "outputs" / "best_threshold.pt"
        self.saved_weights_dir = self.base_dir / "outputs" / "saved_weights"

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.risk_low_threshold = risk_low_threshold
        self.risk_high_threshold = risk_high_threshold
        self.max_batch_size = 1

        self.reference: Optional[Dict[str, Any]] = None
        self.bundle_cache: Dict[str, Dict[str, Any]] = {}
        self.classification_threshold = 0.5
        self.model_version = ""
        self.default_model_version: Optional[str] = None
        self.ready = False
        self.load_error = ""

    def load(self) -> None:
        try:
            self.reference = self._build_reference()
            self.bundle_cache = {}
            default_bundle = self._load_bundle()
            self.classification_threshold = float(default_bundle["classificationThreshold"])
            self.model_version = default_bundle["modelVersion"]
            self.default_model_version = default_bundle["modelVersion"]
            self.ready = True
            self.load_error = ""
        except Exception as exc:
            self.ready = False
            self.load_error = str(exc)
            raise

    def ensure_ready(self) -> None:
        if not self.ready:
            if self.load_error:
                raise RuntimeError(f"Inference service is not ready: {self.load_error}")
            raise RuntimeError("Inference service is not ready")

    def predict_single(self, record: Dict[str, Any], model_version: Optional[str] = None) -> Dict[str, Any]:
        return self.predict_batch([record], model_version=model_version)[0]

    def predict_batch(
        self,
        records: List[Dict[str, Any]],
        model_version: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self.ensure_ready()
        if not records:
            raise ValueError("At least one record is required")
        if len(records) > self.max_batch_size:
            raise ValueError(f"At most {self.max_batch_size} record is supported per request")

        bundle = self._load_bundle(model_version)
        normalized_records = [self.normalize_record(record) for record in records]
        x_tensor, _ = preprocess_for_inference(
            normalized_records,
            bundle["reference"],
            bundle["scaler"],
        )
        x_tensor = x_tensor.to(self.device)

        with torch.no_grad():
            logits = bundle["model"](x_tensor)
            claim_probs = torch.sigmoid(logits).cpu().numpy()

        generated_at = datetime.now().isoformat(timespec="seconds")
        results: List[Dict[str, Any]] = []
        for index, claim_prob in enumerate(claim_probs, start=1):
            probability = float(claim_prob)
            results.append(
                {
                    "requestIndex": index,
                    "claimProbability": round(probability, 6),
                    "claimProbabilityPercent": round(probability * 100, 2),
                    "claimFlag": int(probability >= bundle["classificationThreshold"]),
                    "riskLevel": self.map_risk_level(probability),
                    "thresholdUsed": round(float(bundle["classificationThreshold"]), 6),
                    "modelVersion": bundle["modelVersion"],
                    "generatedAt": generated_at,
                }
            )
        return results

    def list_model_versions(self) -> Dict[str, Any]:
        versions = self._discover_saved_versions()
        if not versions:
            fallback_version = self._build_fallback_version()
            if fallback_version is None:
                return {"defaultModelVersion": None, "versions": []}
            return {
                "defaultModelVersion": fallback_version["modelVersion"],
                "versions": [fallback_version],
            }

        return {
            "defaultModelVersion": versions[0]["modelVersion"],
            "versions": versions,
        }

    def get_contract(self) -> Dict[str, Any]:
        model_versions = self.list_model_versions()
        return {
            "serviceName": "motor-insurance-claim-prediction",
            "version": "2.0.0",
            "maxBatchSize": self.max_batch_size,
            "device": str(self.device),
            "classificationThreshold": round(float(self.classification_threshold), 6) if self.ready else None,
            "defaultModelVersion": model_versions["defaultModelVersion"],
            "riskLevelRule": {
                "low": f"claimProbability < {self.risk_low_threshold:.2f}",
                "medium": f"{self.risk_low_threshold:.2f} <= claimProbability < {self.risk_high_threshold:.2f}",
                "high": f"claimProbability >= {self.risk_high_threshold:.2f}",
            },
            "singlePredictEndpoint": {
                "method": "POST",
                "path": "/predict",
                "body": {
                    "modelVersion": model_versions["defaultModelVersion"],
                    "record": {
                        "dateStartContract": "2019-01-01",
                        "dateLastRenewal": "2019-12-01",
                        "dateNextRenewal": "2020-12-01",
                        "distributionChannel": 0,
                        "dateBirth": "1988-08-12",
                        "dateDrivingLicence": "2008-06-01",
                        "seniority": 5,
                        "policiesInForce": 2,
                        "maxPolicies": 3,
                        "maxProducts": 2,
                        "lapse": 0,
                        "payment": 0,
                        "premium": 1800.0,
                        "nClaimsHistory": 1,
                        "rClaimsHistory": 0.2,
                        "typeRisk": 3,
                        "area": 1,
                        "secondDriver": 0,
                        "yearMatriculation": 2018,
                        "power": 130,
                        "cylinderCapacity": 1600,
                        "valueVehicle": 90000.0,
                        "nDoors": 4,
                        "typeFuel": "P",
                        "length": 4.6,
                        "weight": 1450,
                    },
                },
            },
            "modelVersions": model_versions["versions"],
            "responseFields": [
                {"name": "claimProbability", "type": "float"},
                {"name": "claimProbabilityPercent", "type": "float"},
                {"name": "claimFlag", "type": "integer"},
                {"name": "riskLevel", "type": "string"},
                {"name": "thresholdUsed", "type": "float"},
                {"name": "modelVersion", "type": "string"},
                {"name": "generatedAt", "type": "string"},
            ],
        }

    def health(self) -> Dict[str, Any]:
        return {
            "status": "UP" if self.ready else "DOWN",
            "ready": self.ready,
            "device": str(self.device),
            "classificationThreshold": round(float(self.classification_threshold), 6) if self.ready else None,
            "modelVersion": self.model_version if self.ready else None,
            "defaultModelVersion": self.default_model_version,
            "availableModelVersions": self.list_model_versions()["versions"],
            "artifacts": {
                "trainTable": self.train_table,
                "scalerPath": str(self.scaler_path),
                "referencePath": str(self.reference_path),
                "bestModelPath": str(self.best_model_path),
                "bestThresholdPath": str(self.best_threshold_path),
            },
            "error": self.load_error or None,
        }

    def map_risk_level(self, claim_probability: float) -> str:
        if claim_probability < self.risk_low_threshold:
            return "LOW"
        if claim_probability < self.risk_high_threshold:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for key, value in record.items():
            raw_key = CAMEL_TO_RAW.get(key, key)
            normalized[raw_key] = value
        return normalized

    def _build_reference(self) -> Dict[str, Any]:
        if self.reference_path.exists():
            with open(self.reference_path, "rb") as file:
                return pickle.load(file)
        return build_inference_reference(load_training_dataframe(self.train_table))

    @staticmethod
    def _load_pickle(path: Path):
        with open(path, "rb") as file:
            return pickle.load(file)

    def _load_reference(self, reference_path: Optional[Path]) -> Dict[str, Any]:
        if reference_path is not None and reference_path.exists():
            return self._load_pickle(reference_path)
        if self.reference is None:
            self.reference = self._build_reference()
        return self.reference

    def _load_model(self, model_path: Path, reference: Dict[str, Any]):
        checkpoint = torch.load(model_path, map_location=self.device, **_TORCH_LOAD_KWARGS)
        input_dim = checkpoint.get("input_dim", len(reference["feature_columns"]))
        if input_dim != len(reference["feature_columns"]):
            raise RuntimeError(
                f"Model input dimension {input_dim} does not match feature dimension {len(reference['feature_columns'])}"
            )
        model = build_model_from_checkpoint(checkpoint, input_dim=input_dim)
        model.to(self.device)
        model.eval()
        return model

    def _load_threshold(self, threshold_path: Optional[Path]) -> float:
        if threshold_path is None or not threshold_path.exists():
            return 0.5
        saved = torch.load(threshold_path, map_location="cpu", **_TORCH_LOAD_KWARGS)
        return float(saved.get("best_threshold", 0.5))

    def _load_bundle(self, model_version: Optional[str] = None) -> Dict[str, Any]:
        resolved_version = model_version or self._get_default_model_version()
        if not resolved_version:
            raise RuntimeError("No available model version was found")

        cached_bundle = self.bundle_cache.get(resolved_version)
        if cached_bundle is not None:
            return cached_bundle

        bundle_info = self._resolve_bundle_info(resolved_version)
        reference = self._load_reference(bundle_info.get("referencePath"))
        scaler = self._load_pickle(bundle_info["scalerPath"])
        try:
            model = self._load_model(bundle_info["modelPath"], reference)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load model version '{bundle_info['modelVersion']}': {exc}"
            ) from exc

        bundle = {
            "modelVersion": bundle_info["modelVersion"],
            "displayName": bundle_info["displayName"],
            "model": model,
            "scaler": scaler,
            "reference": reference,
            "classificationThreshold": self._load_threshold(bundle_info.get("thresholdPath")),
            "checkpointType": bundle_info.get("checkpointType"),
            "savedAt": bundle_info.get("savedAt"),
        }
        self.bundle_cache[resolved_version] = bundle
        return bundle

    def _get_default_model_version(self) -> Optional[str]:
        versions = self._discover_saved_versions()
        if versions:
            return versions[0]["modelVersion"]
        fallback_version = self._build_fallback_version()
        return fallback_version["modelVersion"] if fallback_version else None

    def _resolve_bundle_info(self, model_version: str) -> Dict[str, Any]:
        for version in self._discover_saved_versions():
            if version["modelVersion"] == model_version:
                return {
                    "modelVersion": version["modelVersion"],
                    "displayName": version["displayName"],
                    "modelPath": Path(version["filePath"]),
                    "scalerPath": Path(version["scalerPath"]),
                    "referencePath": Path(version["referencePath"]) if version.get("referencePath") else None,
                    "thresholdPath": Path(version["bestThresholdPath"]) if version.get("bestThresholdPath") else None,
                    "checkpointType": version.get("checkpointType"),
                    "savedAt": version.get("savedAt"),
                }

        fallback_version = self._build_fallback_version()
        if fallback_version and fallback_version["modelVersion"] == model_version:
            return {
                "modelVersion": fallback_version["modelVersion"],
                "displayName": fallback_version["displayName"],
                "modelPath": Path(fallback_version["filePath"]),
                "scalerPath": Path(fallback_version["scalerPath"]),
                "referencePath": Path(fallback_version["referencePath"]) if fallback_version.get("referencePath") else None,
                "thresholdPath": Path(fallback_version["bestThresholdPath"]) if fallback_version.get("bestThresholdPath") else None,
                "checkpointType": fallback_version.get("checkpointType"),
                "savedAt": fallback_version.get("savedAt"),
            }

        raise ValueError(f"Model version not found: {model_version}")

    def _discover_saved_versions(self) -> List[Dict[str, Any]]:
        if not self.saved_weights_dir.exists():
            return []

        versions: List[Dict[str, Any]] = []
        for metadata_path in self.saved_weights_dir.glob("*.json"):
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            file_path = Path(str(metadata.get("filePath", "")).strip())
            related_artifacts = metadata.get("relatedArtifacts") or {}
            scaler_path = Path(str(related_artifacts.get("scalerPath", "")).strip())
            reference_path_raw = str(related_artifacts.get("referencePath", "")).strip()
            reference_path = Path(reference_path_raw) if reference_path_raw else None
            threshold_path_raw = str(related_artifacts.get("bestThresholdPath", "")).strip()
            threshold_path = Path(threshold_path_raw) if threshold_path_raw else None

            if not file_path.exists() or not scaler_path.exists():
                continue

            final_metrics = (metadata.get("summary") or {}).get("finalMetrics") or {}
            versions.append(
                {
                    "modelVersion": metadata.get("fileName") or file_path.name,
                    "displayName": metadata.get("fileName") or file_path.name,
                    "fileName": metadata.get("fileName") or file_path.name,
                    "filePath": str(file_path),
                    "savedAt": metadata.get("savedAt"),
                    "checkpointType": metadata.get("checkpointType", "best"),
                    "jobId": metadata.get("jobId"),
                    "auc": final_metrics.get("auc"),
                    "f1": final_metrics.get("f1"),
                    "accuracy": final_metrics.get("accuracy"),
                    "scalerPath": str(scaler_path),
                    "referencePath": str(reference_path) if reference_path else None,
                    "bestThresholdPath": str(threshold_path) if threshold_path else None,
                    "isFallback": False,
                }
            )

        versions.sort(
            key=lambda item: (item.get("savedAt") or "", item.get("fileName") or ""),
            reverse=True,
        )
        return versions

    def _build_fallback_version(self) -> Optional[Dict[str, Any]]:
        if not self.best_model_path.exists() or not self.scaler_path.exists():
            return None

        mtime = datetime.fromtimestamp(self.best_model_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "modelVersion": self.best_model_path.name,
            "displayName": f"{self.best_model_path.stem} (default)",
            "fileName": self.best_model_path.name,
            "filePath": str(self.best_model_path),
            "savedAt": mtime,
            "checkpointType": "best",
            "jobId": None,
            "auc": None,
            "f1": None,
            "accuracy": None,
            "scalerPath": str(self.scaler_path),
            "referencePath": str(self.reference_path) if self.reference_path.exists() else None,
            "bestThresholdPath": str(self.best_threshold_path) if self.best_threshold_path.exists() else None,
            "isFallback": True,
        }
