from __future__ import annotations

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch

if __package__:
    from .DataLoader import (
        FEATURE_ENGINEERING_STRATEGY,
        FEATURE_ENGINEERING_VERSION,
        OBSERVATION_DATE_COL,
        RAW_FEATURE_COLS,
        build_inference_reference,
        build_raw_feature_defaults,
        preprocess_for_inference,
        validate_inference_reference,
    )
    from .DatabaseUtils import load_training_dataframe
    from .Model import build_model_from_checkpoint
else:
    from DataLoader import (
        FEATURE_ENGINEERING_STRATEGY,
        FEATURE_ENGINEERING_VERSION,
        OBSERVATION_DATE_COL,
        RAW_FEATURE_COLS,
        build_inference_reference,
        build_raw_feature_defaults,
        preprocess_for_inference,
        validate_inference_reference,
    )
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

RISK_LEVEL_TEXT = {
    "LOW": "低风险",
    "MEDIUM": "中风险",
    "HIGH": "高风险",
}

FEATURE_LABELS = {
    "Date_start_contract": "合同持续时长",
    "Date_last_renewal": "最近续保时点",
    "Date_next_renewal": "距下次续保时长",
    "Distribution_channel": "分销渠道",
    "Date_birth": "被保人年龄",
    "Date_driving_licence": "驾驶经验",
    "Seniority": "合作年数",
    "Policies_in_force": "当前生效保单数",
    "Max_policies": "历史最高保单数",
    "Max_products": "历史最高产品数",
    "Lapse": "失效保单数",
    "Payment": "缴费方式",
    "Premium": "净保费",
    "N_claims_history": "历史索赔次数",
    "R_Claims_history": "历史出险率",
    "Type_risk": "风险类型",
    "Area": "地区",
    "Second_driver": "第二驾驶员",
    "Year_matriculation": "车龄",
    "Power": "马力",
    "Cylinder_capacity": "排量",
    "Value_vehicle": "车辆价值",
    "N_doors": "车门数",
    "Type_fuel": "燃料类型",
    "Length": "车长",
    "Weight": "车重",
}

CATEGORICAL_VALUE_LABELS = {
    "Distribution_channel": {0: "代理人", 1: "保险经纪"},
    "Payment": {0: "年缴", 1: "半年缴"},
    "Type_risk": {1: "摩托车", 2: "货车", 3: "乘用车", 4: "农用车"},
    "Area": {0: "农村", 1: "城市"},
    "Second_driver": {0: "无", 1: "有"},
    "Type_fuel": {"P": "汽油", "D": "柴油"},
}

DATE_FIELDS = {
    "Date_start_contract",
    "Date_last_renewal",
    "Date_next_renewal",
    "Date_birth",
    "Date_driving_licence",
}

INTEGER_FIELDS = {
    "Seniority",
    "Policies_in_force",
    "Max_policies",
    "Max_products",
    "Lapse",
    "N_claims_history",
    "Distribution_channel",
    "Payment",
    "Type_risk",
    "Area",
    "Second_driver",
    "Year_matriculation",
    "Power",
    "Cylinder_capacity",
    "N_doors",
    "Weight",
}

PERCENT_FIELDS = {"R_Claims_history"}
MONEY_FIELDS = {"Premium", "Value_vehicle"}
METER_FIELDS = {"Length"}
KG_FIELDS = {"Weight"}

TEMPORAL_FEATURE_NOTES = {
    "Date_birth": "以最近续保日期为时间观测点换算后的被保人年龄",
    "Date_driving_licence": "以最近续保日期为时间观测点换算后的驾驶经验",
    "Date_start_contract": "以最近续保日期为时间观测点换算后的合同持续时长",
    "Date_next_renewal": "以最近续保日期为时间观测点换算后的距下次续保时长",
    "Date_last_renewal": "该字段本身就是时间观测点，会联动影响年龄、驾驶经验、合同持续时长、车龄和续保阶段的计算",
    "Year_matriculation": "以最近续保日期为时间观测点换算后的车龄",
}


class InsuranceInferenceService:
    def __init__(
        self,
        base_dir: Optional[str] = None,
        risk_low_threshold: float = 0.30,
        risk_high_threshold: float = 0.60,
    ):
        self.base_dir = Path(base_dir or Path(__file__).resolve().parent)
        self.train_table = str(self.base_dir / "DataSet" / "train_data.csv")
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
            self._refresh_service_state()
        except Exception as exc:
            self.ready = False
            self.load_error = str(exc)
            raise

    def _refresh_service_state(self, model_version: Optional[str] = None) -> Dict[str, Any]:
        self.reference = self._build_reference()
        self.bundle_cache = {}
        bundle = self._load_bundle(model_version)
        self._activate_bundle(bundle)
        self.default_model_version = self._get_default_model_version()
        self.ready = True
        self.load_error = ""
        return bundle

    def _activate_bundle(self, bundle: Dict[str, Any]) -> None:
        self.classification_threshold = float(bundle["classificationThreshold"])
        self.model_version = bundle["modelVersion"]

    def ensure_ready(self, model_version: Optional[str] = None) -> None:
        needs_reload = not self.ready
        if model_version is not None:
            needs_reload = needs_reload or (
                model_version != self.model_version and model_version not in self.bundle_cache
            )
        if not needs_reload:
            return

        try:
            self._refresh_service_state(model_version)
            return
        except Exception as exc:
            self.ready = False
            self.load_error = str(exc)
            if self.load_error:
                raise RuntimeError(f"Inference service is not ready: {self.load_error}") from exc
            raise RuntimeError("Inference service is not ready") from exc

    def predict_single(self, record: Dict[str, Any], model_version: Optional[str] = None) -> Dict[str, Any]:
        return self.predict_batch([record], model_version=model_version)[0]

    def predict_batch(
        self,
        records: List[Dict[str, Any]],
        model_version: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self.ensure_ready(model_version=model_version)
        if not records:
            raise ValueError("At least one record is required")
        if len(records) > self.max_batch_size:
            raise ValueError(f"At most {self.max_batch_size} record is supported per request")

        bundle = self._load_bundle(model_version)
        self._activate_bundle(bundle)
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
            result = {
                "requestIndex": index,
                "claimProbability": round(probability, 6),
                "claimProbabilityPercent": round(probability * 100, 2),
                "claimFlag": int(probability >= bundle["classificationThreshold"]),
                "riskLevel": self.map_risk_level(probability),
                "thresholdUsed": round(float(bundle["classificationThreshold"]), 6),
                "modelVersion": bundle["modelVersion"],
                "generatedAt": generated_at,
            }
            result.update(
                self._build_local_explanation(
                    normalized_records[index - 1],
                    probability,
                    bundle,
                )
            )
            results.append(result)
        return results

    def list_model_versions(self) -> Dict[str, Any]:
        compatible_versions = [
            version for version in self._discover_saved_versions() if version.get("isCompatible")
        ]
        if not compatible_versions:
            fallback_version = self._build_fallback_version()
            if fallback_version is None or not fallback_version.get("isCompatible"):
                return {"defaultModelVersion": None, "versions": []}
            return {
                "defaultModelVersion": fallback_version["modelVersion"],
                "versions": [fallback_version],
            }

        return {
            "defaultModelVersion": compatible_versions[0]["modelVersion"],
            "versions": compatible_versions,
        }

    def get_contract(self) -> Dict[str, Any]:
        model_versions = self.list_model_versions()
        return {
            "serviceName": "motor-insurance-claim-prediction",
            "version": "2.1.0",
            "maxBatchSize": self.max_batch_size,
            "device": str(self.device),
            "classificationThreshold": round(float(self.classification_threshold), 6) if self.ready else None,
            "defaultModelVersion": model_versions["defaultModelVersion"],
            "featureEngineering": {
                "version": FEATURE_ENGINEERING_VERSION,
                "strategy": FEATURE_ENGINEERING_STRATEGY,
                "observationDateColumn": OBSERVATION_DATE_COL,
            },
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
                {"name": "explanationSummary", "type": "string"},
                {"name": "positiveFactors", "type": "array"},
                {"name": "negativeFactors", "type": "array"},
            ],
        }

    def health(self) -> Dict[str, Any]:
        if not self.ready:
            try:
                self.ensure_ready()
            except Exception:
                pass
        return {
            "status": "UP" if self.ready else "DOWN",
            "ready": self.ready,
            "device": str(self.device),
            "classificationThreshold": round(float(self.classification_threshold), 6) if self.ready else None,
            "modelVersion": self.model_version if self.ready else None,
            "defaultModelVersion": self.default_model_version,
            "featureEngineering": {
                "version": FEATURE_ENGINEERING_VERSION,
                "strategy": FEATURE_ENGINEERING_STRATEGY,
                "observationDateColumn": OBSERVATION_DATE_COL,
            },
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
                return self._ensure_reference_extras(validate_inference_reference(pickle.load(file)))
        return self._ensure_reference_extras(
            validate_inference_reference(
                build_inference_reference(load_training_dataframe(self.train_table))
            )
        )

    @staticmethod
    def _load_pickle(path: Path):
        with open(path, "rb") as file:
            return pickle.load(file)

    def _load_reference(self, reference_path: Optional[Path]) -> Dict[str, Any]:
        if reference_path is not None and reference_path.exists():
            return self._ensure_reference_extras(
                validate_inference_reference(self._load_pickle(reference_path))
            )
        if self.reference is None:
            self.reference = self._build_reference()
        return self.reference

    def _ensure_reference_extras(self, reference: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(reference)
        enriched["raw_feature_columns"] = list(
            enriched.get("raw_feature_columns") or RAW_FEATURE_COLS
        )
        if enriched.get("raw_feature_defaults"):
            return enriched
        training_df = load_training_dataframe(self.train_table)
        enriched["raw_feature_defaults"] = build_raw_feature_defaults(training_df)
        return enriched

    def _predict_probability_from_normalized_record(
        self,
        record: Dict[str, Any],
        bundle: Dict[str, Any],
    ) -> float:
        x_tensor, _ = preprocess_for_inference(
            [record],
            bundle["reference"],
            bundle["scaler"],
        )
        x_tensor = x_tensor.to(self.device)
        with torch.no_grad():
            logits = bundle["model"](x_tensor)
            probability = torch.sigmoid(logits).cpu().numpy()[0]
        return float(probability)

    @staticmethod
    def _has_explainable_value(value: Any) -> bool:
        return value is not None and value != ""

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _format_feature_value(self, feature_key: str, value: Any) -> str:
        if not self._has_explainable_value(value):
            return "未填写"

        if feature_key in DATE_FIELDS:
            return str(value).replace("/", "-")

        if feature_key in CATEGORICAL_VALUE_LABELS:
            mapping = CATEGORICAL_VALUE_LABELS[feature_key]
            if feature_key == "Type_fuel":
                mapped = mapping.get(str(value).upper())
                return mapped or str(value)
            int_value = self._coerce_int(value)
            return mapping.get(int_value, str(value))

        if feature_key in PERCENT_FIELDS:
            numeric = self._coerce_float(value)
            if numeric is None:
                return str(value)
            return f"{numeric * 100:.2f}%"

        if feature_key in MONEY_FIELDS:
            numeric = self._coerce_float(value)
            if numeric is None:
                return str(value)
            return f"{numeric:,.2f}"

        if feature_key in METER_FIELDS:
            numeric = self._coerce_float(value)
            if numeric is None:
                return str(value)
            return f"{numeric:.2f} 米"

        if feature_key in KG_FIELDS:
            numeric = self._coerce_float(value)
            if numeric is None:
                return str(value)
            return f"{int(round(numeric))} kg"

        if feature_key in INTEGER_FIELDS:
            numeric = self._coerce_int(value)
            if numeric is None:
                return str(value)
            return str(numeric)

        numeric = self._coerce_float(value)
        if numeric is None:
            return str(value)
        return f"{numeric:.2f}"

    @staticmethod
    def _parse_date_value(value: Any) -> Optional[datetime]:
        if value is None or value == "":
            return None
        raw = str(value).strip()
        if not raw:
            return None
        for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _format_date_display(date_value: Optional[datetime]) -> str:
        if date_value is None:
            return "未填写"
        return date_value.strftime("%Y-%m-%d")

    @staticmethod
    def _format_years_display(years: Optional[float], suffix: str = "年") -> str:
        if years is None:
            return "未填写"
        return f"{years:.1f} {suffix}"

    @staticmethod
    def _format_days_display(days: Optional[int]) -> str:
        if days is None:
            return "未填写"
        if days >= 0:
            return f"{days} 天"
        return f"已过期 {abs(days)} 天"

    @staticmethod
    def _safe_elapsed_years(later: Optional[datetime], earlier: Optional[datetime]) -> Optional[float]:
        if later is None or earlier is None:
            return None
        return max((later - earlier).days / 365.25, 0.0)

    @staticmethod
    def _safe_day_delta(later: Optional[datetime], earlier: Optional[datetime]) -> Optional[int]:
        if later is None or earlier is None:
            return None
        return int((later - earlier).days)

    @staticmethod
    def _safe_vehicle_age(observation_date: Optional[datetime], matriculation_year: Any) -> Optional[float]:
        if observation_date is None:
            return None
        try:
            vehicle_year = int(float(matriculation_year))
        except (TypeError, ValueError):
            return None
        return max(float(observation_date.year - vehicle_year), 0.0)

    def _build_temporal_semantic_meta(
        self,
        feature_key: str,
        current_value: Any,
        baseline_value: Any,
        normalized_record: Dict[str, Any],
    ) -> Optional[Dict[str, str]]:
        observation_date = self._parse_date_value(normalized_record.get("Date_last_renewal"))
        observation_display = self._format_date_display(observation_date)

        if feature_key == "Date_birth":
            current_age = self._safe_elapsed_years(observation_date, self._parse_date_value(current_value))
            baseline_age = self._safe_elapsed_years(observation_date, self._parse_date_value(baseline_value))
            if current_age is None or baseline_age is None:
                return None
            return {
                "featureName": FEATURE_LABELS[feature_key],
                "currentDisplay": self._format_years_display(current_age, "岁"),
                "baselineDisplay": self._format_years_display(baseline_age, "岁"),
                "semanticNote": f"{TEMPORAL_FEATURE_NOTES[feature_key]}（观测点：{observation_display}）",
            }

        if feature_key == "Date_driving_licence":
            current_years = self._safe_elapsed_years(observation_date, self._parse_date_value(current_value))
            baseline_years = self._safe_elapsed_years(observation_date, self._parse_date_value(baseline_value))
            if current_years is None or baseline_years is None:
                return None
            return {
                "featureName": FEATURE_LABELS[feature_key],
                "currentDisplay": self._format_years_display(current_years),
                "baselineDisplay": self._format_years_display(baseline_years),
                "semanticNote": f"{TEMPORAL_FEATURE_NOTES[feature_key]}（观测点：{observation_display}）",
            }

        if feature_key == "Date_start_contract":
            current_years = self._safe_elapsed_years(observation_date, self._parse_date_value(current_value))
            baseline_years = self._safe_elapsed_years(observation_date, self._parse_date_value(baseline_value))
            if current_years is None or baseline_years is None:
                return None
            return {
                "featureName": FEATURE_LABELS[feature_key],
                "currentDisplay": self._format_years_display(current_years),
                "baselineDisplay": self._format_years_display(baseline_years),
                "semanticNote": f"{TEMPORAL_FEATURE_NOTES[feature_key]}（观测点：{observation_display}）",
            }

        if feature_key == "Date_next_renewal":
            current_days = self._safe_day_delta(self._parse_date_value(current_value), observation_date)
            baseline_days = self._safe_day_delta(self._parse_date_value(baseline_value), observation_date)
            if current_days is None or baseline_days is None:
                return None
            return {
                "featureName": FEATURE_LABELS[feature_key],
                "currentDisplay": self._format_days_display(current_days),
                "baselineDisplay": self._format_days_display(baseline_days),
                "semanticNote": f"{TEMPORAL_FEATURE_NOTES[feature_key]}（观测点：{observation_display}）",
            }

        if feature_key == "Date_last_renewal":
            current_date = self._parse_date_value(current_value)
            baseline_date = self._parse_date_value(baseline_value)
            if current_date is None or baseline_date is None:
                return None
            return {
                "featureName": FEATURE_LABELS[feature_key],
                "currentDisplay": self._format_date_display(current_date),
                "baselineDisplay": self._format_date_display(baseline_date),
                "semanticNote": TEMPORAL_FEATURE_NOTES[feature_key],
            }

        if feature_key == "Year_matriculation":
            current_age = self._safe_vehicle_age(observation_date, current_value)
            baseline_age = self._safe_vehicle_age(observation_date, baseline_value)
            if current_age is None or baseline_age is None:
                return None
            return {
                "featureName": FEATURE_LABELS[feature_key],
                "currentDisplay": self._format_years_display(current_age),
                "baselineDisplay": self._format_years_display(baseline_age),
                "semanticNote": f"{TEMPORAL_FEATURE_NOTES[feature_key]}（观测点：{observation_display}）",
            }

        return None

    def _build_factor_item(
        self,
        feature_key: str,
        current_value: Any,
        baseline_value: Any,
        probability_delta: float,
        normalized_record: Dict[str, Any],
    ) -> Dict[str, Any]:
        temporal_meta = self._build_temporal_semantic_meta(
            feature_key,
            current_value,
            baseline_value,
            normalized_record,
        )
        feature_name = temporal_meta["featureName"] if temporal_meta else FEATURE_LABELS.get(feature_key, feature_key)
        current_display = (
            temporal_meta["currentDisplay"]
            if temporal_meta
            else self._format_feature_value(feature_key, current_value)
        )
        baseline_display = (
            temporal_meta["baselineDisplay"]
            if temporal_meta
            else self._format_feature_value(feature_key, baseline_value)
        )
        impact_label = (
            f"使理赔概率上升 {abs(probability_delta) * 100:.2f} 个百分点"
            if probability_delta >= 0
            else f"使理赔概率下降 {abs(probability_delta) * 100:.2f} 个百分点"
        )
        if temporal_meta:
            explanation = (
                f"{temporal_meta['semanticNote']}。当前{feature_name}为 {current_display}，"
                f"相较于训练样本中的典型水平 {baseline_display}，{impact_label}。"
            )
        else:
            explanation = (
                f"当前{feature_name}为 {current_display}，相较于训练样本中的典型水平 {baseline_display}，"
                f"{impact_label}。"
            )
        return {
            "featureKey": feature_key,
            "featureCode": RAW_TO_CAMEL.get(feature_key, feature_key),
            "featureName": feature_name,
            "currentValue": current_value,
            "baselineValue": baseline_value,
            "currentDisplay": current_display,
            "baselineDisplay": baseline_display,
            "probabilityDelta": round(float(probability_delta), 6),
            "probabilityDeltaPercent": round(float(probability_delta) * 100, 2),
            "impactLabel": impact_label,
            "explanation": explanation,
        }

    def _build_explanation_summary(
        self,
        risk_level: str,
        positive_factors: List[Dict[str, Any]],
        negative_factors: List[Dict[str, Any]],
    ) -> str:
        risk_text = RISK_LEVEL_TEXT.get(risk_level, risk_level)
        positive_names = "、".join(item["featureName"] for item in positive_factors[:3])
        negative_names = "、".join(item["featureName"] for item in negative_factors[:2])

        if positive_names and negative_names:
            return (
                f"本次保单被判定为{risk_text}，模型认为最主要的风险提升因素是{positive_names}；"
                f"相对起到缓释作用的因素是{negative_names}。"
            )
        if positive_names:
            return f"本次保单被判定为{risk_text}，模型认为最主要的风险提升因素是{positive_names}。"
        if negative_names:
            return f"本次保单被判定为{risk_text}，当前更显著的风险缓释因素是{negative_names}。"
        return f"本次保单被判定为{risk_text}，各项特征的影响较为分散，没有特别突出的单一因素。"

    def _build_local_explanation(
        self,
        normalized_record: Dict[str, Any],
        probability: float,
        bundle: Dict[str, Any],
    ) -> Dict[str, Any]:
        raw_feature_defaults = bundle["reference"].get("raw_feature_defaults") or {}
        impacts: List[Dict[str, Any]] = []

        for feature_key in bundle["reference"].get("raw_feature_columns") or RAW_FEATURE_COLS:
            current_value = normalized_record.get(feature_key)
            if not self._has_explainable_value(current_value):
                continue

            baseline_value = raw_feature_defaults.get(feature_key)
            if baseline_value is None:
                continue

            ablated_record = dict(normalized_record)
            ablated_record[feature_key] = baseline_value
            ablated_probability = self._predict_probability_from_normalized_record(
                ablated_record,
                bundle,
            )
            probability_delta = probability - ablated_probability
            if abs(probability_delta) < 1e-4:
                continue

            impacts.append(
                self._build_factor_item(
                    feature_key,
                    current_value,
                    baseline_value,
                    probability_delta,
                    normalized_record,
                )
            )

        positive_factors = sorted(
            [item for item in impacts if item["probabilityDelta"] > 0],
            key=lambda item: abs(item["probabilityDelta"]),
            reverse=True,
        )[:3]
        negative_factors = sorted(
            [item for item in impacts if item["probabilityDelta"] < 0],
            key=lambda item: abs(item["probabilityDelta"]),
            reverse=True,
        )[:2]

        return {
            "explanationSummary": self._build_explanation_summary(
                self.map_risk_level(probability),
                positive_factors,
                negative_factors,
            ),
            "positiveFactors": positive_factors,
            "negativeFactors": negative_factors,
        }

    @staticmethod
    def _load_scaler(scaler_path: Path, reference: Dict[str, Any]):
        with open(scaler_path, "rb") as file:
            scaler = pickle.load(file)

        expected_dim = len(reference["feature_columns"])
        scaler_dim = getattr(scaler, "n_features_in_", None)
        if scaler_dim is None and hasattr(scaler, "mean_"):
            scaler_dim = len(scaler.mean_)
        if scaler_dim is not None and int(scaler_dim) != expected_dim:
            raise RuntimeError(
                f"Scaler feature dimension {int(scaler_dim)} does not match feature dimension {expected_dim}"
            )
        return scaler

    def _validate_version_metadata(self, version: Dict[str, Any]) -> Dict[str, Any]:
        validated = dict(version)
        reference_path_raw = validated.get("referencePath")
        if not reference_path_raw:
            validated["isCompatible"] = False
            validated["compatibilityError"] = "Missing preprocess reference artifact for this model version"
            return validated

        try:
            reference = validate_inference_reference(self._load_pickle(Path(reference_path_raw)))
            self._load_scaler(Path(validated["scalerPath"]), reference)
        except Exception as exc:
            validated["isCompatible"] = False
            validated["compatibilityError"] = str(exc)
            return validated

        feature_engineering = validated.get("featureEngineering") or {}
        version_value = feature_engineering.get("version")
        strategy_value = feature_engineering.get("strategy")
        observation_date_value = feature_engineering.get("observationDateColumn")
        if (
            version_value is not None
            and (
                version_value != FEATURE_ENGINEERING_VERSION
                or strategy_value != FEATURE_ENGINEERING_STRATEGY
                or observation_date_value != OBSERVATION_DATE_COL
            )
        ):
            validated["isCompatible"] = False
            validated["compatibilityError"] = (
                "Model version feature engineering metadata does not match the active inference pipeline"
            )
            return validated

        validated["isCompatible"] = True
        validated["compatibilityError"] = None
        return validated

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

        bundle_info = self._resolve_bundle_info(resolved_version)
        current_signature = self._build_artifact_signature(bundle_info)
        cached_bundle = self.bundle_cache.get(resolved_version)
        if cached_bundle is not None and cached_bundle.get("artifactSignature") == current_signature:
            return cached_bundle

        reference = self._load_reference(bundle_info.get("referencePath"))
        try:
            scaler = self._load_scaler(bundle_info["scalerPath"], reference)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load scaler for model version '{bundle_info['modelVersion']}': {exc}"
            ) from exc
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
            "artifactSignature": current_signature,
        }
        self.bundle_cache[resolved_version] = bundle
        return bundle

    @staticmethod
    def _build_artifact_signature(bundle_info: Dict[str, Any]) -> tuple[tuple[str, str, int | None], ...]:
        signature_items: list[tuple[str, str, int | None]] = []
        for key in ("modelPath", "scalerPath", "referencePath", "thresholdPath"):
            path_value = bundle_info.get(key)
            if path_value is None:
                signature_items.append((key, "", None))
                continue
            path_obj = Path(path_value).resolve()
            mtime_ns = path_obj.stat().st_mtime_ns if path_obj.exists() else None
            signature_items.append((key, str(path_obj), mtime_ns))
        return tuple(signature_items)

    def _get_default_model_version(self) -> Optional[str]:
        for version in self._discover_saved_versions():
            if version.get("isCompatible"):
                return version["modelVersion"]
        fallback_version = self._build_fallback_version()
        if fallback_version and fallback_version.get("isCompatible"):
            return fallback_version["modelVersion"]
        return None

    def _resolve_bundle_info(self, model_version: str) -> Dict[str, Any]:
        for version in self._discover_saved_versions():
            if version["modelVersion"] == model_version:
                if not version.get("isCompatible"):
                    raise ValueError(
                        f"Model version '{model_version}' is incompatible: {version.get('compatibilityError')}"
                    )
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
            if not fallback_version.get("isCompatible"):
                raise ValueError(
                    f"Model version '{model_version}' is incompatible: {fallback_version.get('compatibilityError')}"
                )
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
            feature_engineering = (
                (metadata.get("summary") or {}).get("featureEngineering")
                or (related_artifacts.get("featureEngineering") or {})
            )
            versions.append(
                self._validate_version_metadata(
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
                    "featureEngineering": feature_engineering,
                    "scalerPath": str(scaler_path),
                    "referencePath": str(reference_path) if reference_path else None,
                    "bestThresholdPath": str(threshold_path) if threshold_path else None,
                    "isFallback": False,
                }
                )
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
        return self._validate_version_metadata({
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
            "featureEngineering": {
                "version": FEATURE_ENGINEERING_VERSION,
                "strategy": FEATURE_ENGINEERING_STRATEGY,
                "observationDateColumn": OBSERVATION_DATE_COL,
            },
            "scalerPath": str(self.scaler_path),
            "referencePath": str(self.reference_path) if self.reference_path.exists() else None,
            "bestThresholdPath": str(self.best_threshold_path) if self.best_threshold_path.exists() else None,
            "isFallback": True,
        })
