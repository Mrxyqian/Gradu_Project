package com.example.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public class InsurPred {
    private Integer predId;
    private Integer id;
    private BigDecimal claimProbability;
    private Integer claimFlag;
    private String riskLevel;
    private BigDecimal thresholdUsed;
    private String modelVersion;
    private String predictionTime;
    private String explanationSummary;
    private String positiveFactorsJson;
    private String negativeFactorsJson;
    private List<Map<String, Object>> positiveFactors;
    private List<Map<String, Object>> negativeFactors;

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

    public String getExplanationSummary() {
        return explanationSummary;
    }

    public void setExplanationSummary(String explanationSummary) {
        this.explanationSummary = explanationSummary;
    }

    @JsonIgnore
    public String getPositiveFactorsJson() {
        return positiveFactorsJson;
    }

    public void setPositiveFactorsJson(String positiveFactorsJson) {
        this.positiveFactorsJson = positiveFactorsJson;
    }

    @JsonIgnore
    public String getNegativeFactorsJson() {
        return negativeFactorsJson;
    }

    public void setNegativeFactorsJson(String negativeFactorsJson) {
        this.negativeFactorsJson = negativeFactorsJson;
    }

    public List<Map<String, Object>> getPositiveFactors() {
        return positiveFactors;
    }

    public void setPositiveFactors(List<Map<String, Object>> positiveFactors) {
        this.positiveFactors = positiveFactors;
    }

    public List<Map<String, Object>> getNegativeFactors() {
        return negativeFactors;
    }

    public void setNegativeFactors(List<Map<String, Object>> negativeFactors) {
        this.negativeFactors = negativeFactors;
    }
}
