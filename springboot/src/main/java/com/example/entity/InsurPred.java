package com.example.entity;

import java.math.BigDecimal;

public class InsurPred {
    private Integer predId;
    private Integer id;
    private BigDecimal claimProbability;
    private Integer claimFlag;
    private String riskLevel;
    private BigDecimal expectedClaimAmount;
    private BigDecimal thresholdUsed;
    private String modelVersion;
    private String predictionTime;

    public Integer getPredId() {
        return predId;
    }

    public void setPredId(Integer predId) {
        this.predId = predId;
    }

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public BigDecimal getClaimProbability() {
        return claimProbability;
    }

    public void setClaimProbability(BigDecimal claimProbability) {
        this.claimProbability = claimProbability;
    }

    public Integer getClaimFlag() {
        return claimFlag;
    }

    public void setClaimFlag(Integer claimFlag) {
        this.claimFlag = claimFlag;
    }

    public String getRiskLevel() {
        return riskLevel;
    }

    public void setRiskLevel(String riskLevel) {
        this.riskLevel = riskLevel;
    }

    public BigDecimal getExpectedClaimAmount() {
        return expectedClaimAmount;
    }

    public void setExpectedClaimAmount(BigDecimal expectedClaimAmount) {
        this.expectedClaimAmount = expectedClaimAmount;
    }

    public BigDecimal getThresholdUsed() {
        return thresholdUsed;
    }

    public void setThresholdUsed(BigDecimal thresholdUsed) {
        this.thresholdUsed = thresholdUsed;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(String modelVersion) {
        this.modelVersion = modelVersion;
    }

    public String getPredictionTime() {
        return predictionTime;
    }

    public void setPredictionTime(String predictionTime) {
        this.predictionTime = predictionTime;
    }
}
