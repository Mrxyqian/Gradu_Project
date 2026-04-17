ALTER TABLE insur_pred
    ADD COLUMN explanation_summary TEXT NULL COMMENT '单条预测解释摘要' AFTER prediction_time,
    ADD COLUMN positive_factors_json LONGTEXT NULL COMMENT '主要风险提升因素(JSON)' AFTER explanation_summary,
    ADD COLUMN negative_factors_json LONGTEXT NULL COMMENT '风险缓释因素(JSON)' AFTER positive_factors_json;
