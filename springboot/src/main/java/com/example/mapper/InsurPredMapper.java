package com.example.mapper;

import com.example.entity.InsurPred;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

public interface InsurPredMapper {

    @Insert("INSERT INTO insur_pred (ID, claim_probability, claim_flag, risk_level, expected_claim_amount, " +
            "threshold_used, model_version, prediction_time) VALUES (#{id}, #{claimProbability}, #{claimFlag}, " +
            "#{riskLevel}, #{expectedClaimAmount}, #{thresholdUsed}, #{modelVersion}, #{predictionTime})")
    @Options(useGeneratedKeys = true, keyProperty = "predId", keyColumn = "pred_id")
    void insert(InsurPred insurPred);

    @Delete("DELETE FROM insur_pred WHERE pred_id = #{predId}")
    void deleteByPredId(Integer predId);

    @Select("SELECT * FROM insur_pred WHERE pred_id = #{predId}")
    InsurPred selectByPredId(Integer predId);

    List<InsurPred> selectAll(InsurPred insurPred);

    @Select("SELECT risk_level as riskLevel, COUNT(*) as count FROM insur_pred GROUP BY risk_level ORDER BY count DESC")
    List<Map<String, Object>> riskLevelDistribution();

    @Select("SELECT " +
            "CAST(FLOOR(expected_claim_amount / 500) * 500 AS SIGNED) as bucketStart, " +
            "CAST(FLOOR(expected_claim_amount / 500) * 500 + 500 AS SIGNED) as bucketEnd, " +
            "COUNT(*) as count " +
            "FROM insur_pred " +
            "GROUP BY FLOOR(expected_claim_amount / 500) " +
            "ORDER BY bucketStart")
    List<Map<String, Object>> claimAmountHistogram();

    @Select("SELECT COUNT(*) as totalCount, " +
            "AVG(claim_probability) as avgClaimProbability, " +
            "AVG(expected_claim_amount) as avgExpectedClaimAmount " +
            "FROM insur_pred")
    Map<String, Object> overallStatistics();

    List<Map<String, Object>> countByBusinessIds(@Param("ids") List<Integer> ids);
}
