package com.example.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;

public class ClaimTypes {
    private Integer id;
    private String creatorEmployeeNo;
    private BigDecimal costClaimsYear;
    @JsonProperty("nClaimsYear")
    private Integer nClaimsYear;
    @JsonProperty("nClaimsHistory")
    private Integer nClaimsHistory;
    @JsonProperty("rClaimsHistory")
    private BigDecimal rClaimsHistory;
    private Integer typeRisk;
    private Integer area;
    private Integer historyClaimStatus;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getCreatorEmployeeNo() {
        return creatorEmployeeNo;
    }

    public void setCreatorEmployeeNo(String creatorEmployeeNo) {
        this.creatorEmployeeNo = creatorEmployeeNo;
    }

    public BigDecimal getCostClaimsYear() {
        return costClaimsYear;
    }

    public void setCostClaimsYear(BigDecimal costClaimsYear) {
        this.costClaimsYear = costClaimsYear;
    }

    public Integer getNClaimsYear() {
        return nClaimsYear;
    }

    public void setNClaimsYear(Integer nClaimsYear) {
        this.nClaimsYear = nClaimsYear;
    }

    public Integer getNClaimsHistory() {
        return nClaimsHistory;
    }

    public void setNClaimsHistory(Integer nClaimsHistory) {
        this.nClaimsHistory = nClaimsHistory;
    }

    public BigDecimal getRClaimsHistory() {
        return rClaimsHistory;
    }

    public void setRClaimsHistory(BigDecimal rClaimsHistory) {
        this.rClaimsHistory = rClaimsHistory;
    }

    public Integer getTypeRisk() {
        return typeRisk;
    }

    public void setTypeRisk(Integer typeRisk) {
        this.typeRisk = typeRisk;
    }

    public Integer getArea() {
        return area;
    }

    public void setArea(Integer area) {
        this.area = area;
    }

    public Integer getHistoryClaimStatus() {
        return historyClaimStatus;
    }

    public void setHistoryClaimStatus(Integer historyClaimStatus) {
        this.historyClaimStatus = historyClaimStatus;
    }
}
