package com.example.mapper;

import com.example.entity.ClaimTypes;
import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

public interface ClaimTypesMapper {

    @Insert("INSERT INTO claim_record (ID, creator_employee_no, Cost_claims_year, N_claims_year, N_claims_history, " +
            "R_Claims_history, Type_risk, Area) VALUES (#{id}, #{creatorEmployeeNo}, #{costClaimsYear}, #{nClaimsYear}, " +
            "#{nClaimsHistory}, #{rClaimsHistory}, #{typeRisk}, #{area})")
    void insert(ClaimTypes claimTypes);

    @Delete("DELETE FROM claim_record WHERE ID = #{id}")
    void deleteById(Integer id);

    @Update("UPDATE claim_record SET Cost_claims_year = #{costClaimsYear}, " +
            "N_claims_year = #{nClaimsYear}, N_claims_history = #{nClaimsHistory}, " +
            "R_Claims_history = #{rClaimsHistory}, Type_risk = #{typeRisk}, Area = #{area} WHERE ID = #{id}")
    void updateById(ClaimTypes claimTypes);

    @Select("SELECT ID as id, creator_employee_no as creatorEmployeeNo, Cost_claims_year as costClaimsYear, N_claims_year as nClaimsYear, " +
            "N_claims_history as nClaimsHistory, R_Claims_history as rClaimsHistory, " +
            "Type_risk as typeRisk, Area as area FROM claim_record WHERE ID = #{id}")
    ClaimTypes selectById(Integer id);

    List<ClaimTypes> selectAll(ClaimTypes claimTypes);

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
}
