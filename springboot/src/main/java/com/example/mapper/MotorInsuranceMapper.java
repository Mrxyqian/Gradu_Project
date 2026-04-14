package com.example.mapper;

import com.example.entity.MotorInsurance;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;
import java.util.Map;

public interface MotorInsuranceMapper {

    String BASE_COLUMNS = "ID as id, creator_employee_no as creatorEmployeeNo, " +
            "Date_start_contract as dateStartContract, Date_last_renewal as dateLastRenewal, " +
            "Date_next_renewal as dateNextRenewal, Date_birth as dateBirth, " +
            "Date_driving_licence as dateDrivingLicence, Distribution_channel as distributionChannel, " +
            "Seniority as seniority, Policies_in_force as policiesInForce, Max_policies as maxPolicies, " +
            "Max_products as maxProducts, Lapse as lapse, Date_lapse as dateLapse, Payment as payment, " +
            "Premium as premium, Type_risk as typeRisk, Area as area, Second_driver as secondDriver";

    @Insert("INSERT INTO motor_insurance (ID, creator_employee_no, Date_start_contract, Date_last_renewal, Date_next_renewal, " +
            "Date_birth, Date_driving_licence, Distribution_channel, Seniority, Policies_in_force, " +
            "Max_policies, Max_products, Lapse, Date_lapse, Payment, Premium, Type_risk, Area, Second_driver) " +
            "VALUES (#{id}, #{creatorEmployeeNo}, #{dateStartContract}, #{dateLastRenewal}, #{dateNextRenewal}, " +
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

    @Select("SELECT " + BASE_COLUMNS + " FROM motor_insurance WHERE ID = #{id}")
    MotorInsurance selectById(Integer id);

    List<MotorInsurance> selectAll(MotorInsurance motorInsurance);

    List<MotorInsurance> selectByIds(List<Integer> ids);

    @Select({
            "<script>",
            "SELECT Type_risk as typeRisk, COUNT(*) as count, SUM(Cost_claims_year) as totalClaimsCost, ",
            "SUM(N_claims_year) as totalClaimsCount FROM claim_record ",
            "<if test='creatorEmployeeNo != null and creatorEmployeeNo != \"\"'>WHERE creator_employee_no = #{creatorEmployeeNo}</if> ",
            "GROUP BY Type_risk",
            "</script>"
    })
    List<Map<String, Object>> statisticsByRiskType(@Param("creatorEmployeeNo") String creatorEmployeeNo);

    @Select({
            "<script>",
            "SELECT Area as area, COUNT(*) as count, SUM(Cost_claims_year) as totalClaimsCost, ",
            "SUM(N_claims_year) as totalClaimsCount FROM claim_record ",
            "<if test='creatorEmployeeNo != null and creatorEmployeeNo != \"\"'>WHERE creator_employee_no = #{creatorEmployeeNo}</if> ",
            "GROUP BY Area",
            "</script>"
    })
    List<Map<String, Object>> statisticsByArea(@Param("creatorEmployeeNo") String creatorEmployeeNo);

    @Select({
            "<script>",
            "SELECT Payment as payment, COUNT(*) as count, SUM(Premium) as totalPremium FROM motor_insurance ",
            "<if test='creatorEmployeeNo != null and creatorEmployeeNo != \"\"'>WHERE creator_employee_no = #{creatorEmployeeNo}</if> ",
            "GROUP BY Payment",
            "</script>"
    })
    List<Map<String, Object>> statisticsByPayment(@Param("creatorEmployeeNo") String creatorEmployeeNo);

    @Select({
            "<script>",
            "SELECT ",
            "stats.totalPremium as totalPremium, ",
            "CASE ",
            "WHEN stats.totalPremium = 0 THEN 0 ",
            "ELSE (stats.totalPremium - stats.totalClaimsCost) / stats.totalPremium ",
            "END as premiumProfitRate, ",
            "stats.policyCount2018 as policyCount2018, ",
            "stats.avgHistoryClaimRate as avgHistoryClaimRate ",
            "FROM (",
            "SELECT ",
            "COALESCE((SELECT SUM(Premium) FROM motor_insurance ",
            "<if test='creatorEmployeeNo != null and creatorEmployeeNo != \"\"'>WHERE creator_employee_no = #{creatorEmployeeNo}</if>",
            "), 0) as totalPremium, ",
            "COALESCE((SELECT SUM(Cost_claims_year) FROM claim_record ",
            "<if test='creatorEmployeeNo != null and creatorEmployeeNo != \"\"'>WHERE creator_employee_no = #{creatorEmployeeNo}</if>",
            "), 0) as totalClaimsCost, ",
            "COALESCE((SELECT SUM(CASE WHEN RIGHT(TRIM(Date_start_contract), 4) = '2018' THEN 1 ELSE 0 END) FROM motor_insurance ",
            "<if test='creatorEmployeeNo != null and creatorEmployeeNo != \"\"'>WHERE creator_employee_no = #{creatorEmployeeNo}</if>",
            "), 0) as policyCount2018, ",
            "COALESCE((SELECT AVG(COALESCE(N_claims_history, 0)) FROM claim_record ",
            "<if test='creatorEmployeeNo != null and creatorEmployeeNo != \"\"'>WHERE creator_employee_no = #{creatorEmployeeNo}</if>",
            "), 0) as avgHistoryClaimRate",
            ") stats",
            "</script>"
    })
    Map<String, Object> overallStatistics(@Param("creatorEmployeeNo") String creatorEmployeeNo);

    @Select({
            "<script>",
            "SELECT Type_fuel as typeFuel, COUNT(*) as count, AVG(Power) as avgPower, ",
            "AVG(Cylinder_capacity) as avgCylinderCapacity FROM vehicle_info ",
            "<if test='creatorEmployeeNo != null and creatorEmployeeNo != \"\"'>WHERE creator_employee_no = #{creatorEmployeeNo}</if> ",
            "GROUP BY Type_fuel",
            "</script>"
    })
    List<Map<String, Object>> statisticsByFuelType(@Param("creatorEmployeeNo") String creatorEmployeeNo);

    @Select({
            "<script>",
            "SELECT Year_matriculation as yearMatriculation, COUNT(*) as count, ",
            "AVG(Value_vehicle) as avgVehicleValue FROM vehicle_info ",
            "<if test='creatorEmployeeNo != null and creatorEmployeeNo != \"\"'>WHERE creator_employee_no = #{creatorEmployeeNo}</if> ",
            "GROUP BY Year_matriculation ORDER BY Year_matriculation",
            "</script>"
    })
    List<Map<String, Object>> statisticsByMatriculationYear(@Param("creatorEmployeeNo") String creatorEmployeeNo);

    @Select({
            "<script>",
            "SELECT Distribution_channel as distributionChannel, COUNT(*) as count, ",
            "SUM(Premium) as totalPremium, SUM(Policies_in_force) as totalPoliciesInForce FROM motor_insurance ",
            "<if test='creatorEmployeeNo != null and creatorEmployeeNo != \"\"'>WHERE creator_employee_no = #{creatorEmployeeNo}</if> ",
            "GROUP BY Distribution_channel",
            "</script>"
    })
    List<Map<String, Object>> statisticsByDistributionChannel(@Param("creatorEmployeeNo") String creatorEmployeeNo);
}