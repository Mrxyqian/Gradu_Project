package com.example.entity;

import java.math.BigDecimal;
import com.fasterxml.jackson.annotation.JsonProperty;

public class MotorInsurance {
    private Integer id;
    private String dateStartContract;
    private String dateLastRenewal;
    private String dateNextRenewal;
    private String dateBirth;
    private String dateDrivingLicence;
    private Integer distributionChannel;
    private Integer seniority;
    private Integer policiesInForce;
    private Integer maxPolicies;
    private Integer maxProducts;
    private Integer lapse;
    private String dateLapse;
    private Integer payment;
    private BigDecimal premium;
    private BigDecimal costClaimsYear;
    private Integer nClaimsYear;
    private Integer nClaimsHistory;
    private BigDecimal rClaimsHistory;
    private Integer typeRisk;
    private Integer area;
    private Integer secondDriver;
    private Integer yearMatriculation;
    private Integer power;
    private Integer cylinderCapacity;
    private BigDecimal valueVehicle;
    @JsonProperty("nDoors")
    private Integer nDoors;
    private String typeFuel;
    private BigDecimal length;
    private Integer weight;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getDateStartContract() {
        return dateStartContract;
    }

    public void setDateStartContract(String dateStartContract) {
        this.dateStartContract = dateStartContract;
    }

    public String getDateLastRenewal() {
        return dateLastRenewal;
    }

    public void setDateLastRenewal(String dateLastRenewal) {
        this.dateLastRenewal = dateLastRenewal;
    }

    public String getDateNextRenewal() {
        return dateNextRenewal;
    }

    public void setDateNextRenewal(String dateNextRenewal) {
        this.dateNextRenewal = dateNextRenewal;
    }

    public String getDateBirth() {
        return dateBirth;
    }

    public void setDateBirth(String dateBirth) {
        this.dateBirth = dateBirth;
    }

    public String getDateDrivingLicence() {
        return dateDrivingLicence;
    }

    public void setDateDrivingLicence(String dateDrivingLicence) {
        this.dateDrivingLicence = dateDrivingLicence;
    }

    public Integer getDistributionChannel() {
        return distributionChannel;
    }

    public void setDistributionChannel(Integer distributionChannel) {
        this.distributionChannel = distributionChannel;
    }

    public Integer getSeniority() {
        return seniority;
    }

    public void setSeniority(Integer seniority) {
        this.seniority = seniority;
    }

    public Integer getPoliciesInForce() {
        return policiesInForce;
    }

    public void setPoliciesInForce(Integer policiesInForce) {
        this.policiesInForce = policiesInForce;
    }

    public Integer getMaxPolicies() {
        return maxPolicies;
    }

    public void setMaxPolicies(Integer maxPolicies) {
        this.maxPolicies = maxPolicies;
    }

    public Integer getMaxProducts() {
        return maxProducts;
    }

    public void setMaxProducts(Integer maxProducts) {
        this.maxProducts = maxProducts;
    }

    public Integer getLapse() {
        return lapse;
    }

    public void setLapse(Integer lapse) {
        this.lapse = lapse;
    }

    public String getDateLapse() {
        return dateLapse;
    }

    public void setDateLapse(String dateLapse) {
        this.dateLapse = dateLapse;
    }

    public Integer getPayment() {
        return payment;
    }

    public void setPayment(Integer payment) {
        this.payment = payment;
    }

    public BigDecimal getPremium() {
        return premium;
    }

    public void setPremium(BigDecimal premium) {
        this.premium = premium;
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

    public Integer getSecondDriver() {
        return secondDriver;
    }

    public void setSecondDriver(Integer secondDriver) {
        this.secondDriver = secondDriver;
    }

    public Integer getYearMatriculation() {
        return yearMatriculation;
    }

    public void setYearMatriculation(Integer yearMatriculation) {
        this.yearMatriculation = yearMatriculation;
    }

    public Integer getPower() {
        return power;
    }

    public void setPower(Integer power) {
        this.power = power;
    }

    public Integer getCylinderCapacity() {
        return cylinderCapacity;
    }

    public void setCylinderCapacity(Integer cylinderCapacity) {
        this.cylinderCapacity = cylinderCapacity;
    }

    public BigDecimal getValueVehicle() {
        return valueVehicle;
    }

    public void setValueVehicle(BigDecimal valueVehicle) {
        this.valueVehicle = valueVehicle;
    }

    public Integer getNDoors() {
        return nDoors;
    }

    public void setNDoors(Integer nDoors) {
        this.nDoors = nDoors;
    }

    public String getTypeFuel() {
        return typeFuel;
    }

    public void setTypeFuel(String typeFuel) {
        this.typeFuel = typeFuel;
    }

    public BigDecimal getLength() {
        return length;
    }

    public void setLength(BigDecimal length) {
        this.length = length;
    }

    public Integer getWeight() {
        return weight;
    }

    public void setWeight(Integer weight) {
        this.weight = weight;
    }
}
