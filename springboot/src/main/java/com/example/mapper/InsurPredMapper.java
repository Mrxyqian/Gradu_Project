package com.example.mapper;

import com.example.entity.InsurPred;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

public interface InsurPredMapper {

    @Insert("INSERT INTO insur_pred (ID, claim_probability, claim_flag, risk_level, threshold_used, model_version, prediction_time, explanation_summary, positive_factors_json, negative_factors_json) " +
            "VALUES (#{id}, #{claimProbability}, #{claimFlag}, #{riskLevel}, #{thresholdUsed}, #{modelVersion}, #{predictionTime}, #{explanationSummary}, #{positiveFactorsJson}, #{negativeFactorsJson})")
    @Options(useGeneratedKeys = true, keyProperty = "predId", keyColumn = "pred_id")
    void insert(InsurPred insurPred);

    @Delete("DELETE FROM insur_pred WHERE pred_id = #{predId}")
    void deleteByPredId(Integer predId);

    @Select("SELECT pred_id as predId, ID as id, claim_probability as claimProbability, claim_flag as claimFlag, " +
            "risk_level as riskLevel, threshold_used as thresholdUsed, model_version as modelVersion, " +
            "prediction_time as predictionTime, explanation_summary as explanationSummary, " +
            "positive_factors_json as positiveFactorsJson, negative_factors_json as negativeFactorsJson " +
            "FROM insur_pred WHERE pred_id = #{predId}")
    InsurPred selectByPredId(Integer predId);

    List<InsurPred> selectAll(InsurPred insurPred);

    @Select("SELECT risk_level as riskLevel, COUNT(*) as count FROM insur_pred GROUP BY risk_level ORDER BY count DESC")
    List<Map<String, Object>> riskLevelDistribution();

    @Select("SELECT " +
            "CAST(FLOOR(claim_probability * 10) / 10 AS DECIMAL(3,1)) as bucketStart, " +
            "CAST(LEAST(FLOOR(claim_probability * 10) / 10 + 0.1, 1.0) AS DECIMAL(3,1)) as bucketEnd, " +
            "COUNT(*) as count " +
            "FROM insur_pred " +
            "GROUP BY FLOOR(claim_probability * 10) " +
            "ORDER BY bucketStart")
    List<Map<String, Object>> claimProbabilityHistogram();

    @Select("SELECT COUNT(*) as totalCount, " +
            "AVG(claim_probability) as avgClaimProbability, " +
            "AVG(CASE WHEN claim_flag = 1 THEN 1 ELSE 0 END) as positivePredictionRate " +
            "FROM insur_pred")
    Map<String, Object> overallStatistics();
}
