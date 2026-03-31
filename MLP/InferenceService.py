"""
InferenceService.py
车险理赔预测 —— 在线推理服务核心实现

职责：
  1. 加载训练产物（best_model / scaler / best_threshold）
  2. 构建与训练期一致的特征顺序与缺失填充参考
  3. 接收业务侧保单记录，完成批量在线推理
"""

from __future__ import annotations

import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import torch

try:
    from .DataLoader import build_inference_reference, preprocess_for_inference
    from .Model import InsuranceMLP
except ImportError:
    from DataLoader import build_inference_reference, preprocess_for_inference
    from Model import InsuranceMLP


_TORCH_LOAD_KWARGS = {"weights_only": False}


RAW_TO_CAMEL = {
    "ID": "id",
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
    "Date_lapse": "dateLapse",
    "Payment": "payment",
    "Premium": "premium",
    "Cost_claims_year": "costClaimsYear",
    "N_claims_year": "nClaimsYear",
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

CAMEL_TO_RAW = {v: k for k, v in RAW_TO_CAMEL.items()}

IGNORED_LABEL_FIELDS = {"dateLapse", "costClaimsYear", "nClaimsYear"}


class InsuranceInferenceService:
    """在线推理服务，支持单条和批量保单预测。"""

    def __init__(
        self,
        base_dir: Optional[str] = None,
        risk_low_threshold: float = 0.30,
        risk_high_threshold: float = 0.60,
    ):
        self.base_dir = Path(base_dir or Path(__file__).resolve().parent)
        self.csv_path = self.base_dir / "DataSet" / "Motor vehicle insurance data.csv"
        self.scaler_path = self.base_dir / "outputs" / "scaler.pkl"
        self.best_model_path = self.base_dir / "outputs" / "best_model.pth"
        self.best_threshold_path = self.base_dir / "outputs" / "best_threshold.pt"

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.risk_low_threshold = risk_low_threshold
        self.risk_high_threshold = risk_high_threshold
        self.max_batch_size = 10

        self.scaler = None
        self.model = None
        self.reference = None
        self.classification_threshold = 0.5
        self.model_version = ""
        self.ready = False
        self.load_error = ""

    def load(self) -> None:
        """加载模型、标准化器和训练期参考信息。"""
        try:
            self._validate_files()
            self.reference = self._build_reference()
            self.scaler = self._load_scaler()
            self.model = self._load_model()
            self.classification_threshold = self._load_threshold()
            self.model_version = self._build_model_version()
            self.ready = True
            self.load_error = ""
        except Exception as exc:
            self.ready = False
            self.load_error = str(exc)
            raise

    def ensure_ready(self) -> None:
        if not self.ready:
            if self.load_error:
                raise RuntimeError(f"推理服务未就绪: {self.load_error}")
            raise RuntimeError("推理服务未就绪，请先加载模型产物")

    def predict_single(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return self.predict_batch([record])[0]

    def predict_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.ensure_ready()

        if not records:
            raise ValueError("至少需要 1 条保单记录进行预测")
        if len(records) > self.max_batch_size:
            raise ValueError(f"单次最多支持 {self.max_batch_size} 条保单记录")

        normalized_records = [self.normalize_record(record) for record in records]
        source_ids = [self.extract_source_id(record) for record in records]

        x_tensor, _ = preprocess_for_inference(normalized_records, self.reference, self.scaler)
        x_tensor = x_tensor.to(self.device)

        with torch.no_grad():
            clf_logit, reg_pred = self.model(x_tensor)
            claim_probs = torch.sigmoid(clf_logit).cpu().numpy()
            claim_amounts = torch.expm1(reg_pred.clamp(min=0)).cpu().numpy()

        results = []
        generated_at = datetime.now().isoformat(timespec="seconds")
        for index, (source_id, claim_prob, claim_amount) in enumerate(
            zip(source_ids, claim_probs, claim_amounts),
            start=1,
        ):
            claim_prob = float(claim_prob)
            claim_amount = float(claim_amount)
            results.append({
                "requestIndex": index,
                "sourceId": source_id,
                "claimProbability": round(claim_prob, 6),
                "claimProbabilityPercent": round(claim_prob * 100, 2),
                "claimFlag": int(claim_prob >= self.classification_threshold),
                "riskLevel": self.map_risk_level(claim_prob),
                "expectedClaimAmount": round(claim_amount, 2),
                "thresholdUsed": round(float(self.classification_threshold), 6),
                "modelVersion": self.model_version,
                "generatedAt": generated_at,
            })

        return results

    def get_contract(self) -> Dict[str, Any]:
        """返回给 Spring Boot / 前端联调时使用的接口契约。"""
        return {
            "serviceName": "motor-insurance-claim-prediction",
            "version": "1.0.0",
            "maxBatchSize": self.max_batch_size,
            "device": str(self.device),
            "classificationThreshold": round(float(self.classification_threshold), 6) if self.ready else None,
            "riskLevelRule": {
                "low": f"claimProbability < {self.risk_low_threshold:.2f}",
                "medium": f"{self.risk_low_threshold:.2f} <= claimProbability < {self.risk_high_threshold:.2f}",
                "high": f"claimProbability >= {self.risk_high_threshold:.2f}",
            },
            "ignoredFields": sorted(IGNORED_LABEL_FIELDS),
            "singlePredictEndpoint": {
                "method": "POST",
                "path": "/predict",
                "body": {
                    "record": {
                        "id": 100001,
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
                    }
                },
            },
            "batchPredictEndpoint": {
                "method": "POST",
                "path": "/predict/batch",
                "body": {
                    "records": [
                        {"id": 100001, "typeRisk": 3, "premium": 1800.0},
                        {"id": 100002, "typeRisk": 2, "premium": 2600.0},
                    ]
                },
            },
            "responseFields": [
                {"name": "sourceId", "type": "integer|null", "description": "原保单 ID，用于业务系统回写"},
                {"name": "claimProbability", "type": "float", "description": "理赔概率，取值范围 0~1"},
                {"name": "claimProbabilityPercent", "type": "float", "description": "理赔概率百分比"},
                {"name": "claimFlag", "type": "integer", "description": "按最优分类阈值判定的是否理赔"},
                {"name": "riskLevel", "type": "string", "description": "风险等级：LOW / MEDIUM / HIGH"},
                {"name": "expectedClaimAmount", "type": "float", "description": "预计理赔金额，单位元"},
                {"name": "thresholdUsed", "type": "float", "description": "当前分类阈值"},
                {"name": "modelVersion", "type": "string", "description": "模型版本标识"},
                {"name": "generatedAt", "type": "string", "description": "推理完成时间"},
            ],
        }

    def health(self) -> Dict[str, Any]:
        return {
            "status": "UP" if self.ready else "DOWN",
            "ready": self.ready,
            "device": str(self.device),
            "classificationThreshold": round(float(self.classification_threshold), 6) if self.ready else None,
            "modelVersion": self.model_version if self.ready else None,
            "artifacts": {
                "csvPath": str(self.csv_path),
                "scalerPath": str(self.scaler_path),
                "bestModelPath": str(self.best_model_path),
                "bestThresholdPath": str(self.best_threshold_path),
            },
            "error": self.load_error or None,
        }

    @staticmethod
    def extract_source_id(record: Dict[str, Any]) -> Optional[int]:
        for key in ("id", "ID", "policyId"):
            value = record.get(key)
            if value is not None and value != "":
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
        return None

    def map_risk_level(self, claim_probability: float) -> str:
        if claim_probability < self.risk_low_threshold:
            return "LOW"
        if claim_probability < self.risk_high_threshold:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {}
        for key, value in record.items():
            raw_key = CAMEL_TO_RAW.get(key, key)
            normalized[raw_key] = value
        return normalized

    def _validate_files(self) -> None:
        missing = [str(path) for path in (
            self.csv_path, self.scaler_path, self.best_model_path
        ) if not path.exists()]
        if missing:
            raise FileNotFoundError(f"以下推理产物不存在: {missing}")

    def _build_reference(self) -> Dict[str, Any]:
        df_raw = pd.read_csv(self.csv_path)
        return build_inference_reference(df_raw)

    def _load_scaler(self):
        with open(self.scaler_path, "rb") as file:
            return pickle.load(file)

    def _load_model(self) -> InsuranceMLP:
        checkpoint = torch.load(self.best_model_path, map_location=self.device, **_TORCH_LOAD_KWARGS)
        input_dim = checkpoint.get("input_dim", len(self.reference["feature_columns"]))

        if input_dim != len(self.reference["feature_columns"]):
            raise RuntimeError(
                f"模型输入维度({input_dim})与训练特征维度({len(self.reference['feature_columns'])})不一致"
            )

        model = InsuranceMLP(input_dim=input_dim)
        model.load_state_dict(checkpoint["model"])
        model.to(self.device)
        model.eval()
        return model

    def _load_threshold(self) -> float:
        if not self.best_threshold_path.exists():
            return 0.5
        saved = torch.load(self.best_threshold_path, map_location="cpu", **_TORCH_LOAD_KWARGS)
        return float(saved.get("best_threshold", 0.5))

    def _build_model_version(self) -> str:
        mtime = datetime.fromtimestamp(self.best_model_path.stat().st_mtime).strftime("%Y%m%d%H%M%S")
        return f"{self.best_model_path.stem}-{mtime}"
