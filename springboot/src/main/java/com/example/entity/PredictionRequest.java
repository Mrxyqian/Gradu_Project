package com.example.entity;

public class PredictionRequest {
    private MotorInsurance record;
    private String modelVersion;

    public MotorInsurance getRecord() {
        return record;
    }

    public void setRecord(MotorInsurance record) {
        this.record = record;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(String modelVersion) {
        this.modelVersion = modelVersion;
    }
}