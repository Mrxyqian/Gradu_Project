package com.example.mapper;

import com.example.entity.MotorInsurance;
import org.apache.ibatis.annotations.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public interface MotorInsuranceMapper {

    @Insert("INSERT INTO motor_insurance (ID, Date_start_contract, Date_last_renewal, Date_next_renewal, " +
            "Date_birth, Date_driving_licence, Distribution_channel, Seniority, Policies_in_force, " +
            "Max_policies, Max_products, Lapse, Date_lapse, Payment, Premium, Type_risk, Area, Second_driver) " +
            "VALUES (#{id}, #{dateStartContract}, #{dateLastRenewal}, #{dateNextRenewal}, " +
            "#{dateBirth}, #{dateDrivingLicence}, #{distributionChannel}, #{seniority}, #{policiesInForce}, " +
            "#{maxPolicies}, #{maxProducts}, #{lapse}, #{dateLapse}, #{payment}, #{premium}, #{typeRisk}, #{area}, #{secondDriver})")
    void insert(MotorInsurance motorInsurance);

    @Delete("DELETE FROM motor_insurance WHERE ID = #{id}")
    void deleteById(Integer id);

    @Update("UPDATE motor_insurance SET Date_start_contract = #{dateStartContract}, Date_last_renewal = #{dateLastRenewal}, " +
            "Date_next_renewal = #{dateNextRenewal}, Date_birth = #{dateBirth}, Date_driving_licence = #{dateDrivingLicence}, " +
            "Distribution_channel = #{distributionChannel}, Seniority = #{seniority}, Policies_in_force = #{policiesInForce}, " +
            "Max_policies = #{maxPolicies}, Max_products = #{maxProducts}, Lapse = #{lapse}, Date_lapse = #{dateLapse}, " +
            "Payment = #{payment}, Premium = #{premium}, Type_risk = #{typeRisk}, " +
            "Area = #{area}, Second_driver = #{secondDriver} WHERE ID = #{id}")
    void updateById(MotorInsurance motorInsurance);

    @Select("SELECT * FROM motor_insurance WHERE ID = #{id}")
    MotorInsurance selectById(Integer id);

    List<MotorInsurance> selectAll(MotorInsurance motorInsurance);

    List<MotorInsurance> selectByIds(List<Integer> ids);

    @Select("SELECT Type_risk as typeRisk, COUNT(*) as count, SUM(Cost_claims_year) as totalClaimsCost, " +
            "SUM(N_claims_year) as totalClaimsCount FROM claim_record GROUP BY Type_risk")
    List<Map<String, Object>> statisticsByRiskType();

    @Select("SELECT Area as area, COUNT(*) as count, SUM(Cost_claims_year) as totalClaimsCost, " +
            "SUM(N_claims_year) as totalClaimsCount FROM claim_record GROUP BY Area")
    List<Map<String, Object>> statisticsByArea();

    @Select("SELECT Payment as payment, COUNT(*) as count, SUM(Premium) as totalPremium FROM motor_insurance GROUP BY Payment")
    List<Map<String, Object>> statisticsByPayment();

    @Select("SELECT " +
            "stats.totalPremium as totalPremium, " +
            "CASE " +
            "WHEN stats.totalPremium = 0 THEN 0 " +
            "ELSE (stats.totalPremium - stats.totalClaimsCost) / stats.totalPremium " +
            "END as premiumProfitRate, " +
            "stats.policyCount2018 as policyCount2018, " +
            "stats.avgHistoryClaimRate as avgHistoryClaimRate " +
            "FROM (" +
            "SELECT " +
            "COALESCE((SELECT SUM(Premium) FROM motor_insurance), 0) as totalPremium, " +
            "COALESCE((SELECT SUM(Cost_claims_year) FROM claim_record), 0) as totalClaimsCost, " +
            "COALESCE((SELECT SUM(CASE WHEN RIGHT(TRIM(Date_start_contract), 4) = '2018' THEN 1 ELSE 0 END) FROM motor_insurance), 0) as policyCount2018, " +
            "COALESCE((SELECT AVG(COALESCE(N_claims_history, 0)) FROM claim_record), 0) as avgHistoryClaimRate" +
            ") stats")
    Map<String, Object> overallStatistics();

    @Select("SELECT Type_fuel as typeFuel, COUNT(*) as count, AVG(Power) as avgPower, " +
            "AVG(Cylinder_capacity) as avgCylinderCapacity FROM vehicle_info GROUP BY Type_fuel")
    List<Map<String, Object>> statisticsByFuelType();

    @Select("SELECT Year_matriculation as yearMatriculation, COUNT(*) as count, " +
            "AVG(Value_vehicle) as avgVehicleValue FROM vehicle_info GROUP BY Year_matriculation ORDER BY Year_matriculation")
    List<Map<String, Object>> statisticsByMatriculationYear();

    @Select("SELECT Distribution_channel as distributionChannel, COUNT(*) as count, " +
            "SUM(Premium) as totalPremium, SUM(Policies_in_force) as totalPoliciesInForce FROM motor_insurance GROUP BY Distribution_channel")
    List<Map<String, Object>> statisticsByDistributionChannel();
}
