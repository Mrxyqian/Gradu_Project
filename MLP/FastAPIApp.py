"""
FastAPIApp.py
车险理赔预测 —— FastAPI 接口入口

运行示例：
    uvicorn FastAPIApp:app --host 0.0.0.0 --port 8000 --reload

若从项目根目录启动：
    uvicorn MLP.FastAPIApp:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

from collections import Counter
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
    title="车险理赔预测 FastAPI 服务",
    version="1.1.0",
    description=(
        "负责加载已训练好的 MLP 分类模型，"
        "对业务系统传入的 motor_insurance 保单记录执行单条或批量在线推理。"
    ),
)

service = InsuranceInferenceService()


class PolicyRecordInput(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
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
        }
    )

    id: Optional[int] = Field(None, description="保单 ID，仅用于结果回传")
    dateStartContract: Optional[str] = Field(None, description="合同开始日期，推荐 YYYY-MM-DD")
    dateLastRenewal: Optional[str] = Field(None, description="最后续保日期，推荐 YYYY-MM-DD")
    dateNextRenewal: Optional[str] = Field(None, description="下次续保日期，推荐 YYYY-MM-DD")
    distributionChannel: Optional[int] = Field(None, description="分销渠道：0 代理人，1 保险经纪")
    dateBirth: Optional[str] = Field(None, description="被保险人出生日期，推荐 YYYY-MM-DD")
    dateDrivingLicence: Optional[str] = Field(None, description="驾照签发日期，推荐 YYYY-MM-DD")
    seniority: Optional[int] = Field(None, description="与保险机构关联总年数")
    policiesInForce: Optional[int] = Field(None, description="当前有效保单数")
    maxPolicies: Optional[int] = Field(None, description="历史最高保单数")
    maxProducts: Optional[int] = Field(None, description="历史最高产品数")
    lapse: Optional[int] = Field(None, description="失效保单数")
    dateLapse: Optional[str] = Field(None, description="合同终止日期，推理时忽略")
    payment: Optional[int] = Field(None, description="缴费方式：0 年缴，1 半年缴")
    premium: Optional[float] = Field(None, description="净保费")
    costClaimsYear: Optional[float] = Field(None, description="当年索赔成本，推理时忽略")
    nClaimsYear: Optional[int] = Field(None, description="当年索赔次数，推理时忽略")
    nClaimsHistory: Optional[int] = Field(None, description="历史索赔次数")
    rClaimsHistory: Optional[float] = Field(None, description="历史索赔频率比")
    typeRisk: Optional[int] = Field(None, description="风险类型：1 摩托车，2 货车，3 乘用车，4 农用车")
    area: Optional[int] = Field(None, description="区域：0 农村，1 城市")
    secondDriver: Optional[int] = Field(None, description="是否有第二驾驶员：0 否，1 是")
    yearMatriculation: Optional[int] = Field(None, description="车辆注册年份")
    power: Optional[int] = Field(None, description="车辆马力")
    cylinderCapacity: Optional[int] = Field(None, description="车辆排量")
    valueVehicle: Optional[float] = Field(None, description="车辆价值")
    nDoors: Optional[int] = Field(None, description="车门数")
    typeFuel: Optional[str] = Field(None, description="燃料类型：P 汽油，D 柴油")
    length: Optional[float] = Field(None, description="车辆长度")
    weight: Optional[int] = Field(None, description="车辆重量")

    @model_validator(mode="before")
    def convert_raw_dataset_keys(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(values, dict):
            return values

        normalized = {}
        for key, value in values.items():
            camel_key = RAW_TO_CAMEL.get(key, key)
            if camel_key == "policyId":
                camel_key = "id"
            normalized[camel_key] = value
        return normalized

class SinglePredictionRequest(BaseModel):
    modelVersion: Optional[str] = Field(None, description="指定模型权重版本，不传则默认使用最新已保存版本")
    record: PolicyRecordInput


class BatchPredictionRequest(BaseModel):
    modelVersion: Optional[str] = Field(None, description="指定模型权重版本，不传则默认使用最新已保存版本")
    records: list[PolicyRecordInput] = Field(
        ...,
        description="待预测保单列表，单次最多 10 条",
        min_length=1,
        max_length=10,
    )


class PredictionResult(BaseModel):
    requestIndex: int
    sourceId: Optional[int]
    claimProbability: float
    claimProbabilityPercent: float
    claimFlag: int
    riskLevel: str
    thresholdUsed: float
    modelVersion: str
    generatedAt: str


class SinglePredictionResponse(BaseModel):
    code: str = "200"
    msg: str = "预测成功"
    data: PredictionResult


class BatchPredictionResponse(BaseModel):
    code: str = "200"
    msg: str = "批量预测成功"
    data: Dict[str, Any]


class TrainingStartRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    numEpochs: int = Field(100, ge=1, le=500, description="训练轮数")
    batchSize: int = Field(128, ge=8, le=4096, description="批大小")
    optimizer: Literal["adamw", "adam", "sgd"] = Field("adamw", description="优化器")
    learningRate: float = Field(2e-4, gt=0, le=1, description="学习率")
    earlyStopMetric: Literal["auc", "pr_auc", "loss", "clf_loss", "accuracy", "balanced_accuracy", "f1", "precision", "recall"] = Field(
        "auc", description="监控指标"
    )
    thresholdMetric: Literal["f1", "precision", "recall"] = Field("f1", description="阈值搜索目标")
    hiddenDims: list[int] = Field(
        default_factory=lambda: [256, 512, 512, 256, 256],
        min_length=1,
        max_length=10,
        description="主干隐藏层维度列表",
    )
    headHiddenDim: int = Field(64, ge=1, le=4096, description="分类头隐藏层维度")

    @model_validator(mode="after")
    def validate_hidden_dims(self) -> "TrainingStartRequest":
        if any(int(dim) <= 0 for dim in self.hiddenDims):
            raise ValueError("hiddenDims 中的每一项都必须是正整数")
        return self


class SaveWeightsRequest(BaseModel):
    checkpointType: Literal["best", "last"] = Field("best", description="保存 best 或 last 权重")
    fileName: str = Field(..., min_length=1, max_length=120, description="目标权重文件名")


@app.on_event("startup")
def startup_event() -> None:
    try:
        service.load()
    except Exception:
        # 允许在推理产物缺失时先启动服务，以便管理员通过 Web 页面发起训练。
        pass


@app.get("/", tags=["系统"])
def index() -> Dict[str, Any]:
    return {
        "service": "motor-insurance-claim-prediction",
        "status": "UP" if service.ready else "DOWN",
        "docs": "/docs",
        "contract": "/contract",
    }


@app.get("/health", tags=["系统"])
def health() -> Dict[str, Any]:
    return service.health()


@app.get("/contract", tags=["系统"])
def contract() -> Dict[str, Any]:
    return service.get_contract()


@app.post("/predict", response_model=SinglePredictionResponse, tags=["预测"])
def predict_single(request: SinglePredictionRequest) -> Dict[str, Any]:
    try:
        result = service.predict_batch(
            [request.record.model_dump(exclude_none=True)],
            model_version=request.modelVersion,
        )[0]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "code": "200",
        "msg": "预测成功",
        "data": result,
    }


@app.post("/predict/batch", response_model=BatchPredictionResponse, tags=["预测"])
def predict_batch(request: BatchPredictionRequest) -> Dict[str, Any]:
    try:
        results = service.predict_batch([
            record.model_dump(exclude_none=True) for record in request.records
        ], model_version=request.modelVersion)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    risk_counter = Counter(item["riskLevel"] for item in results)
    summary = {
        "total": len(results),
        "riskLevelDistribution": dict(risk_counter),
        "averageClaimProbability": round(
            sum(item["claimProbability"] for item in results) / len(results), 6
        ),
    }

    return {
        "code": "200",
        "msg": "批量预测成功",
        "data": {
            "summary": summary,
            "results": results,
        },
    }


@app.get("/models/versions", tags=["模型版本"])
def list_model_versions() -> Dict[str, Any]:
    try:
        data = service.list_model_versions()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "code": "200",
        "msg": "查询模型版本成功",
        "data": data,
    }


@app.post("/training/start", tags=["训练"])
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
        "msg": "训练任务已启动",
        "data": job,
    }


@app.get("/training/jobs/latest", tags=["训练"])
def latest_training_job() -> Dict[str, Any]:
    return {
        "code": "200",
        "msg": "查询成功",
        "data": training_manager.get_latest_job(),
    }


@app.get("/training/jobs/{job_id}", tags=["训练"])
def get_training_job(job_id: str) -> Dict[str, Any]:
    job = training_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="未找到对应的训练任务")

    return {
        "code": "200",
        "msg": "查询成功",
        "data": job,
    }


@app.post("/training/jobs/{job_id}/save-weights", tags=["训练"])
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
        "msg": "权重文件保存成功",
        "data": result,
    }


@app.get("/training/jobs/{job_id}/figures/{figure_key}", tags=["训练"])
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


@app.post("/training/jobs/{job_id}/discard", tags=["训练"])
def discard_training_job(job_id: str) -> Dict[str, Any]:
    try:
        result = training_manager.discard_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "code": "200",
        "msg": "训练任务成果已丢弃",
        "data": result,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("FastAPIApp:app", host="0.0.0.0", port=8000, reload=False)
