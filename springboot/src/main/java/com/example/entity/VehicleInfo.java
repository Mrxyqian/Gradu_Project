package com.example.entity;

import java.math.BigDecimal;
import com.fasterxml.jackson.annotation.JsonProperty;

public class VehicleInfo {
    private Integer id;
    private String creatorEmployeeNo;
    private Integer typeRisk;
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

    public String getCreatorEmployeeNo() {
        return creatorEmployeeNo;
    }

    public void setCreatorEmployeeNo(String creatorEmployeeNo) {
        this.creatorEmployeeNo = creatorEmployeeNo;
    }

    public Integer getTypeRisk() {
        return typeRisk;
    }

    public void setTypeRisk(Integer typeRisk) {
        this.typeRisk = typeRisk;
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
