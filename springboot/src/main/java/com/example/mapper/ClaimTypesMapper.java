package com.example.mapper;

import com.example.entity.ClaimTypes;
import org.apache.ibatis.annotations.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public interface ClaimTypesMapper {

    @Insert("INSERT INTO claim_types (ID, Cost_claims_year, Cost_claims_by_type, Claims_type) " +
            "VALUES (#{id}, #{costClaimsYear}, #{costClaimsByType}, #{claimsType})")
    void insert(ClaimTypes claimTypes);

    @Delete("DELETE FROM claim_types WHERE ID = #{id}")
    void deleteById(Integer id);

    @Update("UPDATE claim_types SET Cost_claims_year = #{costClaimsYear}, " +
            "Cost_claims_by_type = #{costClaimsByType}, Claims_type = #{claimsType} WHERE ID = #{id}")
    void updateById(ClaimTypes claimTypes);

    @Select("SELECT * FROM claim_types WHERE ID = #{id}")
    ClaimTypes selectById(Integer id);

    List<ClaimTypes> selectAll(ClaimTypes claimTypes);

    @Select("SELECT Claims_type as claimsType, Cost_claims_by_type as costClaimsByType, " +
            "Cost_claims_year as costClaimsYear FROM claim_types ORDER BY Cost_claims_by_type DESC")
    List<Map<String, Object>> statisticsByClaimType();

    @Select("SELECT SUM(Cost_claims_year) as totalCostClaimsYear, " +
            "SUM(Cost_claims_by_type) as totalCostClaimsByType FROM claim_types")
    Map<String, Object> overallClaimsStatistics();

    @Select("SELECT Claims_type as claimsType, Cost_claims_by_type as costClaimsByType, " +
            "(Cost_claims_by_type / (SELECT SUM(Cost_claims_by_type) FROM claim_types)) * 100 as percentage " +
            "FROM claim_types ORDER BY percentage DESC")
    List<Map<String, Object>> claimsCostPercentage();

    @Select("SELECT * FROM claim_types WHERE Claims_type LIKE CONCAT('%', #{claimsType}, '%') ORDER BY ID DESC")
    List<ClaimTypes> selectByClaimsType(String claimsType);

    @Select("SELECT * FROM claim_types WHERE Cost_claims_by_type >= #{minCost} ORDER BY Cost_claims_by_type DESC")
    List<ClaimTypes> selectByMinCost(BigDecimal minCost);
}
