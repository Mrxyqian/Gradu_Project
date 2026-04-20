from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

if __package__:
    from .InferenceService import InsuranceInferenceService, RAW_TO_CAMEL
    from .TrainingManager import training_manager
else:
    from InferenceService import InsuranceInferenceService, RAW_TO_CAMEL
    from TrainingManager import training_manager


app = FastAPI(
    title="Motor Insurance Claim Prediction FastAPI",
    version="2.1.0",
    description="MLP classification service for model training management and manual prediction.",
)

service = InsuranceInferenceService()


class PolicyRecordInput(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
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
    )

    dateStartContract: Optional[str] = Field(None)
    dateLastRenewal: Optional[str] = Field(None)
    dateNextRenewal: Optional[str] = Field(None)
    distributionChannel: Optional[int] = Field(None)
    dateBirth: Optional[str] = Field(None)
    dateDrivingLicence: Optional[str] = Field(None)
    seniority: Optional[int] = Field(None)
    policiesInForce: Optional[int] = Field(None)
    maxPolicies: Optional[int] = Field(None)
    maxProducts: Optional[int] = Field(None)
    lapse: Optional[int] = Field(None)
    payment: Optional[int] = Field(None)
    premium: Optional[float] = Field(None)
    nClaimsHistory: Optional[int] = Field(None)
    rClaimsHistory: Optional[float] = Field(None)
    typeRisk: Optional[int] = Field(None)
    area: Optional[int] = Field(None)
    secondDriver: Optional[int] = Field(None)
    yearMatriculation: Optional[int] = Field(None)
    power: Optional[int] = Field(None)
    cylinderCapacity: Optional[int] = Field(None)
    valueVehicle: Optional[float] = Field(None)
    nDoors: Optional[int] = Field(None)
    typeFuel: Optional[str] = Field(None)
    length: Optional[float] = Field(None)
    weight: Optional[int] = Field(None)

    @model_validator(mode="before")
    def convert_raw_dataset_keys(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(values, dict):
            return values
        normalized: Dict[str, Any] = {}
        for key, value in values.items():
            normalized[RAW_TO_CAMEL.get(key, key)] = value
        return normalized


class SinglePredictionRequest(BaseModel):
    modelVersion: Optional[str] = Field(None)
    record: PolicyRecordInput


class FactorExplanation(BaseModel):
    featureKey: str
    featureCode: str
    featureName: str
    currentValue: Optional[Any] = None
    baselineValue: Optional[Any] = None
    currentDisplay: str
    baselineDisplay: str
    probabilityDelta: float
    probabilityDeltaPercent: float
    impactLabel: str
    explanation: str


class PredictionResult(BaseModel):
    requestIndex: int
    claimProbability: float
    claimProbabilityPercent: float
    claimFlag: int
    riskLevel: str
    thresholdUsed: float
    modelVersion: str
    generatedAt: str
    explanationSummary: str = ""
    positiveFactors: list[FactorExplanation] = Field(default_factory=list)
    negativeFactors: list[FactorExplanation] = Field(default_factory=list)


class SinglePredictionResponse(BaseModel):
    code: str = "200"
    msg: str = "ok"
    data: PredictionResult


class TrainingStartRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    numEpochs: int = Field(80, ge=1, le=500)
    batchSize: int = Field(128, ge=8, le=4096)
    optimizer: Literal["adamw", "adam", "sgd"] = Field("adamw")
    learningRate: float = Field(2e-4, gt=0, le=1)
    earlyStopMetric: Literal[
        "auc",
        "pr_auc",
        "loss",
        "clf_loss",
        "accuracy",
        "f1",
        "precision",
        "recall",
    ] = Field("auc")
    thresholdMetric: Literal["f1", "precision", "recall"] = Field("f1")
    thresholdMinRecall: Optional[float] = Field(0.83, ge=0.0, le=1.0)
    hiddenDims: list[int] = Field(default_factory=lambda: [128, 256, 256, 128, 128], min_length=1, max_length=10)
    headHiddenDim: int = Field(32, ge=1, le=4096)

    @model_validator(mode="after")
    def validate_hidden_dims(self) -> "TrainingStartRequest":
        if any(int(dim) <= 0 for dim in self.hiddenDims):
            raise ValueError("hiddenDims must contain positive integers")
        return self


class SaveWeightsRequest(BaseModel):
    checkpointType: Literal["best", "last"] = Field("best")
    fileName: str = Field(..., min_length=1, max_length=120)


@app.on_event("startup")
def startup_event() -> None:
    try:
        service.load()
    except Exception:
        pass


@app.get("/", tags=["system"])
def index() -> Dict[str, Any]:
    return {
        "service": "motor-insurance-claim-prediction",
        "status": "UP" if service.ready else "DOWN",
        "docs": "/docs",
        "contract": "/contract",
    }


@app.get("/health", tags=["system"])
def health() -> Dict[str, Any]:
    return service.health()


@app.get("/contract", tags=["system"])
def contract() -> Dict[str, Any]:
    return service.get_contract()


@app.post("/predict", response_model=SinglePredictionResponse, tags=["prediction"])
def predict_single(request: SinglePredictionRequest) -> Dict[str, Any]:
    try:
        result = service.predict_single(
            request.record.model_dump(exclude_none=True),
            model_version=request.modelVersion,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "code": "200",
        "msg": "Prediction completed",
        "data": result,
    }


@app.get("/models/versions", tags=["model"])
def list_model_versions() -> Dict[str, Any]:
    try:
        data = service.list_model_versions()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {
        "code": "200",
        "msg": "Model versions loaded",
        "data": data,
    }


@app.post("/training/start", tags=["training"])
def start_training(request: TrainingStartRequest) -> Dict[str, Any]:
    try:
        job = training_manager.start_training(request.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "code": "200",
        "msg": "Training job started",
        "data": job,
    }


@app.get("/training/jobs/latest", tags=["training"])
def latest_training_job() -> Dict[str, Any]:
    return {
        "code": "200",
        "msg": "ok",
        "data": training_manager.get_latest_job(),
    }


@app.get("/training/jobs/{job_id}", tags=["training"])
def get_training_job(job_id: str) -> Dict[str, Any]:
    job = training_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Training job not found")
    return {
        "code": "200",
        "msg": "ok",
        "data": job,
    }


@app.post("/training/jobs/{job_id}/save-weights", tags=["training"])
def save_training_weights(job_id: str, request: SaveWeightsRequest) -> Dict[str, Any]:
    try:
        result = training_manager.save_weights(
            job_id=job_id,
            checkpoint_type=request.checkpointType,
            file_name=request.fileName,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "code": "200",
        "msg": "Weights saved",
        "data": result,
    }


@app.get("/training/jobs/{job_id}/figures/{figure_key}", tags=["training"])
def get_training_figure(job_id: str, figure_key: str) -> FileResponse:
    try:
        figure_path = training_manager.get_figure_file(job_id, figure_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return FileResponse(
        path=figure_path,
        media_type="image/png",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-store",
        },
    )


@app.post("/training/jobs/{job_id}/discard", tags=["training"])
def discard_training_job(job_id: str) -> Dict[str, Any]:
    try:
        result = training_manager.discard_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "code": "200",
        "msg": "Training job discarded",
        "data": result,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("FastAPIApp:app", host="0.0.0.0", port=8000, reload=False)
