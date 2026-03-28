package com.example.entity;

import java.math.BigDecimal;

public class ClaimTypes {
    private Integer id;
    private BigDecimal costClaimsYear;
    private BigDecimal costClaimsByType;
    private String claimsType;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public BigDecimal getCostClaimsYear() {
        return costClaimsYear;
    }

    public void setCostClaimsYear(BigDecimal costClaimsYear) {
        this.costClaimsYear = costClaimsYear;
    }

    public BigDecimal getCostClaimsByType() {
        return costClaimsByType;
    }

    public void setCostClaimsByType(BigDecimal costClaimsByType) {
        this.costClaimsByType = costClaimsByType;
    }

    public String getClaimsType() {
        return claimsType;
    }

    public void setClaimsType(String claimsType) {
        this.claimsType = claimsType;
    }
}
