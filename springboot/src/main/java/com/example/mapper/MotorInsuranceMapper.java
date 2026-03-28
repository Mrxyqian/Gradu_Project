package com.example.mapper;

import com.example.entity.MotorInsurance;
import org.apache.ibatis.annotations.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public interface MotorInsuranceMapper {

    @Insert("INSERT INTO motor_insurance (ID, Date_start_contract, Date_last_renewal, Date_next_renewal, " +
            "Date_birth, Date_driving_licence, Distribution_channel, Seniority, Policies_in_force, " +
            "Max_policies, Max_products, Lapse, Date_lapse, Payment, Premium, Cost_claims_year, " +
            "N_claims_year, N_claims_history, R_Claims_history, Type_risk, Area, Second_driver, " +
            "Year_matriculation, Power, Cylinder_capacity, Value_vehicle, N_doors, Type_fuel, Length, Weight) " +
            "VALUES (#{id}, #{dateStartContract}, #{dateLastRenewal}, #{dateNextRenewal}, " +
            "#{dateBirth}, #{dateDrivingLicence}, #{distributionChannel}, #{seniority}, #{policiesInForce}, " +
            "#{maxPolicies}, #{maxProducts}, #{lapse}, #{dateLapse}, #{payment}, #{premium}, #{costClaimsYear}, " +
            "#{nClaimsYear}, #{nClaimsHistory}, #{rClaimsHistory}, #{typeRisk}, #{area}, #{secondDriver}, " +
            "#{yearMatriculation}, #{power}, #{cylinderCapacity}, #{valueVehicle}, #{nDoors}, #{typeFuel}, #{length}, #{weight})")
    void insert(MotorInsurance motorInsurance);

    @Delete("DELETE FROM motor_insurance WHERE ID = #{id}")
    void deleteById(Integer id);

    @Update("UPDATE motor_insurance SET Date_start_contract = #{dateStartContract}, Date_last_renewal = #{dateLastRenewal}, " +
            "Date_next_renewal = #{dateNextRenewal}, Date_birth = #{dateBirth}, Date_driving_licence = #{dateDrivingLicence}, " +
            "Distribution_channel = #{distributionChannel}, Seniority = #{seniority}, Policies_in_force = #{policiesInForce}, " +
            "Max_policies = #{maxPolicies}, Max_products = #{maxProducts}, Lapse = #{lapse}, Date_lapse = #{dateLapse}, " +
            "Payment = #{payment}, Premium = #{premium}, Cost_claims_year = #{costClaimsYear}, N_claims_year = #{nClaimsYear}, " +
            "N_claims_history = #{nClaimsHistory}, R_Claims_history = #{rClaimsHistory}, Type_risk = #{typeRisk}, " +
            "Area = #{area}, Second_driver = #{secondDriver}, Year_matriculation = #{yearMatriculation}, Power = #{power}, " +
            "Cylinder_capacity = #{cylinderCapacity}, Value_vehicle = #{valueVehicle}, N_doors = #{nDoors}, Type_fuel = #{typeFuel}, " +
            "Length = #{length}, Weight = #{weight} WHERE ID = #{id}")
    void updateById(MotorInsurance motorInsurance);

    @Select("SELECT * FROM motor_insurance WHERE ID = #{id}")
    MotorInsurance selectById(Integer id);

    List<MotorInsurance> selectAll(MotorInsurance motorInsurance);

    @Select("SELECT Type_risk as typeRisk, COUNT(*) as count, SUM(Premium) as totalPremium, " +
            "SUM(Cost_claims_year) as totalClaimsCost FROM motor_insurance GROUP BY Type_risk")
    List<Map<String, Object>> statisticsByRiskType();

    @Select("SELECT Area as area, COUNT(*) as count, SUM(Premium) as totalPremium, " +
            "SUM(Cost_claims_year) as totalClaimsCost FROM motor_insurance GROUP BY Area")
    List<Map<String, Object>> statisticsByArea();

    @Select("SELECT Payment as payment, COUNT(*) as count, SUM(Premium) as totalPremium FROM motor_insurance GROUP BY Payment")
    List<Map<String, Object>> statisticsByPayment();

    @Select("SELECT SUM(Premium) as totalPremium, SUM(Cost_claims_year) as totalClaimsCost, " +
            "SUM(N_claims_year) as totalClaimsCount, AVG(R_Claims_history) as avgClaimsRatio FROM motor_insurance")
    Map<String, Object> overallStatistics();

    @Select("SELECT Type_fuel as typeFuel, COUNT(*) as count, AVG(Power) as avgPower, " +
            "AVG(Cylinder_capacity) as avgCylinderCapacity FROM motor_insurance GROUP BY Type_fuel")
    List<Map<String, Object>> statisticsByFuelType();

    @Select("SELECT Year_matriculation as yearMatriculation, COUNT(*) as count, " +
            "AVG(Value_vehicle) as avgVehicleValue FROM motor_insurance GROUP BY Year_matriculation ORDER BY Year_matriculation")
    List<Map<String, Object>> statisticsByMatriculationYear();

    @Select("SELECT Distribution_channel as distributionChannel, COUNT(*) as count, " +
            "SUM(Premium) as totalPremium, SUM(Policies_in_force) as totalPoliciesInForce FROM motor_insurance GROUP BY Distribution_channel")
    List<Map<String, Object>> statisticsByDistributionChannel();
}
