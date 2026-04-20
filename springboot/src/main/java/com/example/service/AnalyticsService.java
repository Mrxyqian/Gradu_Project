package com.example.service;

import com.example.common.DateUtil;
import com.example.common.SessionUserUtil;
import com.example.entity.AnalyticsFilters;
import com.example.entity.AnalyticsQueryRequest;
import com.example.exception.CustomException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class AnalyticsService {

    private static final String SUBJECT_POLICY = "policy";
    private static final String SUBJECT_CLAIM = "claim";
    private static final String METRIC_POLICY_COUNT = "policyCount";
    private static final String METRIC_TOTAL_PREMIUM = "totalPremium";
    private static final String METRIC_AVG_PREMIUM = "avgPremium";
    private static final String METRIC_CLAIM_RECORD_COUNT = "claimRecordCount";
    private static final String METRIC_TOTAL_CLAIMS_COST = "totalClaimsCost";
    private static final String METRIC_AVG_CLAIMS_COST = "avgClaimsCost";
    private static final String METRIC_CLAIM_FREQUENCY = "claimFrequency";
    private static final String METRIC_LOSS_RATIO = "lossRatio";

    private static final Map<String, String> GROUP_BY_COLUMNS = new LinkedHashMap<>();
    private static final Map<String, String> GROUP_BY_LABELS = new LinkedHashMap<>();
    private static final Map<String, String> METRIC_SQL = new LinkedHashMap<>();
    private static final Map<String, List<String>> SUBJECT_DEFAULT_METRICS = new LinkedHashMap<>();
    private static final Map<String, String> SUBJECT_DEFAULT_GROUP_BY = new LinkedHashMap<>();
    private static final Set<String> RATIO_METRICS = new LinkedHashSet<>(Arrays.asList(
            METRIC_CLAIM_FREQUENCY,
            METRIC_LOSS_RATIO
    ));

    static {
        GROUP_BY_COLUMNS.put("typeRisk", "m.Type_risk");
        GROUP_BY_COLUMNS.put("area", "m.Area");
        GROUP_BY_COLUMNS.put("distributionChannel", "m.Distribution_channel");
        GROUP_BY_COLUMNS.put("payment", "m.Payment");
        GROUP_BY_COLUMNS.put("contractStartDate", "m.Date_start_contract");
        GROUP_BY_COLUMNS.put("typeFuel", "v.Type_fuel");
        GROUP_BY_COLUMNS.put("yearMatriculation", "v.Year_matriculation");
        GROUP_BY_COLUMNS.put("secondDriver", "m.Second_driver");

        GROUP_BY_LABELS.put("typeRisk", "风险类型");
        GROUP_BY_LABELS.put("area", "地区");
        GROUP_BY_LABELS.put("distributionChannel", "分销渠道");
        GROUP_BY_LABELS.put("payment", "缴费方式");
        GROUP_BY_LABELS.put("contractStartDate", "合同开始日期");
        GROUP_BY_LABELS.put("typeFuel", "燃料类型");
        GROUP_BY_LABELS.put("yearMatriculation", "车辆注册年份");
        GROUP_BY_LABELS.put("secondDriver", "第二驾驶员");

        METRIC_SQL.put(METRIC_POLICY_COUNT, "COUNT(DISTINCT m.ID) AS policyCount");
        METRIC_SQL.put(METRIC_TOTAL_PREMIUM, "ROUND(COALESCE(SUM(m.Premium), 0), 2) AS totalPremium");
        METRIC_SQL.put(METRIC_AVG_PREMIUM, "ROUND(COALESCE(AVG(m.Premium), 0), 2) AS avgPremium");
        METRIC_SQL.put(METRIC_CLAIM_RECORD_COUNT, "COUNT(c.ID) AS claimRecordCount");
        METRIC_SQL.put(METRIC_TOTAL_CLAIMS_COST, "ROUND(COALESCE(SUM(c.Cost_claims_year), 0), 2) AS totalClaimsCost");
        METRIC_SQL.put(METRIC_AVG_CLAIMS_COST,
                "ROUND(CASE WHEN COUNT(c.ID) = 0 THEN 0 ELSE COALESCE(SUM(c.Cost_claims_year), 0) / COUNT(c.ID) END, 2) AS avgClaimsCost");
        METRIC_SQL.put(METRIC_CLAIM_FREQUENCY,
                "ROUND(CASE WHEN COUNT(DISTINCT m.ID) = 0 THEN 0 ELSE COUNT(c.ID) / COUNT(DISTINCT m.ID) END, 4) AS claimFrequency");
        METRIC_SQL.put(METRIC_LOSS_RATIO,
                "ROUND(CASE WHEN COALESCE(SUM(m.Premium), 0) = 0 THEN 0 ELSE COALESCE(SUM(c.Cost_claims_year), 0) / SUM(m.Premium) END, 4) AS lossRatio");

        SUBJECT_DEFAULT_METRICS.put(SUBJECT_POLICY, Arrays.asList(
                METRIC_POLICY_COUNT,
                METRIC_TOTAL_PREMIUM,
                METRIC_AVG_PREMIUM
        ));
        SUBJECT_DEFAULT_METRICS.put(SUBJECT_CLAIM, Arrays.asList(
                METRIC_CLAIM_RECORD_COUNT,
                METRIC_TOTAL_CLAIMS_COST,
                METRIC_LOSS_RATIO
        ));
        SUBJECT_DEFAULT_GROUP_BY.put(SUBJECT_POLICY, "distributionChannel");
        SUBJECT_DEFAULT_GROUP_BY.put(SUBJECT_CLAIM, "typeRisk");
    }

    @Resource
    private JdbcTemplate jdbcTemplate;

    public Map<String, Object> query(AnalyticsQueryRequest request, HttpSession session) {
        SessionUserUtil.requireLogin(session);

        String subject = normalizeSubject(request == null ? null : request.getSubject());
        String groupBy = normalizeGroupBy(request == null ? null : request.getGroupBy(), subject);
        List<String> metrics = normalizeMetrics(request == null ? null : request.getMetrics(), subject);
        String sortBy = normalizeSortBy(request == null ? null : request.getSortBy(), metrics);
        String sortOrder = normalizeSortOrder(request == null ? null : request.getSortOrder());
        int topN = normalizeTopN(request == null ? null : request.getTopN());
        AnalyticsFilters filters = request == null || request.getFilters() == null ? new AnalyticsFilters() : request.getFilters();

        List<Object> params = new ArrayList<>();
        String whereClause = buildWhereClause(filters, SessionUserUtil.resolveDataScopeEmployeeNo(session), params);
        String fromClause = buildFromClause();

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("subject", subject);
        response.put("groupBy", groupBy);
        response.put("groupByLabel", GROUP_BY_LABELS.get(groupBy));
        response.put("metrics", metrics);
        response.put("ratioMetrics", RATIO_METRICS);
        response.put("summary", querySummary(metrics, fromClause, whereClause, params));
        response.put("rows", queryRows(groupBy, metrics, sortBy, sortOrder, topN, fromClause, whereClause, params));
        return response;
    }

    private String normalizeSubject(String subject) {
        if (SUBJECT_POLICY.equals(subject) || SUBJECT_CLAIM.equals(subject)) {
            return subject;
        }
        return SUBJECT_POLICY;
    }

    private String normalizeGroupBy(String groupBy, String subject) {
        if (GROUP_BY_COLUMNS.containsKey(groupBy)) {
            return groupBy;
        }
        return SUBJECT_DEFAULT_GROUP_BY.get(subject);
    }

    private List<String> normalizeMetrics(List<String> metrics, String subject) {
        List<String> source = metrics == null || metrics.isEmpty() ? SUBJECT_DEFAULT_METRICS.get(subject) : metrics;
        LinkedHashSet<String> normalized = new LinkedHashSet<>();
        for (String metric : source) {
            if (METRIC_SQL.containsKey(metric)) {
                normalized.add(metric);
            }
        }
        if (normalized.isEmpty()) {
            normalized.addAll(SUBJECT_DEFAULT_METRICS.get(subject));
        }
        return new ArrayList<>(normalized);
    }

    private String normalizeSortBy(String sortBy, List<String> metrics) {
        if (sortBy != null && METRIC_SQL.containsKey(sortBy)) {
            return sortBy;
        }
        return metrics.get(0);
    }

    private String normalizeSortOrder(String sortOrder) {
        return "asc".equalsIgnoreCase(sortOrder) ? "ASC" : "DESC";
    }

    private int normalizeTopN(Integer topN) {
        if (topN == null || topN <= 0) {
            return 10;
        }
        return Math.min(topN, 50);
    }

    private String buildFromClause() {
        return " FROM motor_insurance m " +
                "LEFT JOIN claim_record c ON c.ID = m.ID " +
                "LEFT JOIN vehicle_info v ON v.ID = m.ID ";
    }

    private String buildWhereClause(AnalyticsFilters filters, String scopedEmployeeNo, List<Object> params) {
        List<String> conditions = new ArrayList<>();
        if (scopedEmployeeNo != null && !scopedEmployeeNo.trim().isEmpty()) {
            conditions.add("m.creator_employee_no = ?");
            params.add(scopedEmployeeNo);
        }
        if (filters.getContractYear() != null) {
            conditions.add("RIGHT(TRIM(m.Date_start_contract), 4) = ?");
            params.add(String.valueOf(filters.getContractYear()));
        }
        if (filters.getTypeRisk() != null) {
            conditions.add("m.Type_risk = ?");
            params.add(filters.getTypeRisk());
        }
        if (filters.getArea() != null) {
            conditions.add("m.Area = ?");
            params.add(filters.getArea());
        }
        if (filters.getDistributionChannel() != null) {
            conditions.add("m.Distribution_channel = ?");
            params.add(filters.getDistributionChannel());
        }
        if (filters.getPayment() != null) {
            conditions.add("m.Payment = ?");
            params.add(filters.getPayment());
        }
        if (filters.getSecondDriver() != null) {
            conditions.add("m.Second_driver = ?");
            params.add(filters.getSecondDriver());
        }
        if (filters.getTypeFuel() != null && !filters.getTypeFuel().trim().isEmpty()) {
            conditions.add("v.Type_fuel = ?");
            params.add(filters.getTypeFuel().trim());
        }
        if (filters.getYearMatriculationStart() != null) {
            conditions.add("v.Year_matriculation >= ?");
            params.add(filters.getYearMatriculationStart());
        }
        if (filters.getYearMatriculationEnd() != null) {
            conditions.add("v.Year_matriculation <= ?");
            params.add(filters.getYearMatriculationEnd());
        }

        if (conditions.isEmpty()) {
            return "";
        }
        return " WHERE " + String.join(" AND ", conditions);
    }

    private Map<String, Object> querySummary(List<String> metrics, String fromClause, String whereClause, List<Object> params) {
        String sql = "SELECT " + buildMetricSelect(metrics) + fromClause + whereClause;
        Map<String, Object> summary = jdbcTemplate.queryForMap(sql, params.toArray());
        return normalizeNumbers(summary);
    }

    private List<Map<String, Object>> queryRows(String groupBy,
                                                List<String> metrics,
                                                String sortBy,
                                                String sortOrder,
                                                int topN,
                                                String fromClause,
                                                String whereClause,
                                                List<Object> params) {
        if (!GROUP_BY_COLUMNS.containsKey(groupBy)) {
            return Collections.emptyList();
        }

        String groupExpression = GROUP_BY_COLUMNS.get(groupBy);
        String sql = "SELECT " + groupExpression + " AS groupKey, " +
                buildMetricSelect(metrics) +
                fromClause +
                whereClause +
                " GROUP BY " + groupExpression +
                " HAVING groupKey IS NOT NULL AND TRIM(CAST(groupKey AS CHAR)) <> ''" +
                " ORDER BY " + sortBy + " " + sortOrder +
                " LIMIT " + topN;

        List<Map<String, Object>> rows = jdbcTemplate.queryForList(sql, params.toArray());
        List<Map<String, Object>> normalizedRows = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Map<String, Object> normalized = normalizeNumbers(row);
            Object groupKey = normalized.get("groupKey");
            normalized.put("groupName", formatGroupName(groupBy, groupKey));
            normalizedRows.add(normalized);
        }
        return normalizedRows;
    }

    private String buildMetricSelect(List<String> metrics) {
        List<String> fragments = new ArrayList<>();
        for (String metric : metrics) {
            String sql = METRIC_SQL.get(metric);
            if (sql != null) {
                fragments.add(sql);
            }
        }
        if (fragments.isEmpty()) {
            throw new CustomException("未选择有效的统计指标");
        }
        return String.join(", ", fragments);
    }

    private Map<String, Object> normalizeNumbers(Map<String, Object> source) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : source.entrySet()) {
            Object value = entry.getValue();
            if (value instanceof BigDecimal) {
                BigDecimal decimal = (BigDecimal) value;
                result.put(entry.getKey(), decimal.stripTrailingZeros().scale() < 0 ? decimal.setScale(0) : decimal);
            } else {
                result.put(entry.getKey(), value);
            }
        }
        return result;
    }

    private String formatGroupName(String groupBy, Object groupKey) {
        if (groupKey == null) {
            return "未填写";
        }
        switch (groupBy) {
            case "typeRisk":
                return getTypeRiskText(groupKey);
            case "area":
                return "0".equals(String.valueOf(groupKey)) ? "农村" : "城市";
            case "distributionChannel":
                return "0".equals(String.valueOf(groupKey)) ? "代理人" : "保险经纪";
            case "payment":
                return "0".equals(String.valueOf(groupKey)) ? "年缴" : "半年缴";
            case "contractStartDate":
                return DateUtil.convertDDMMYYYYToYYYYMMDD(String.valueOf(groupKey));
            case "typeFuel":
                return "P".equalsIgnoreCase(String.valueOf(groupKey)) ? "汽油" : "柴油";
            case "secondDriver":
                return "0".equals(String.valueOf(groupKey)) ? "否" : "是";
            default:
                return String.valueOf(groupKey);
        }
    }

    private String getTypeRiskText(Object value) {
        String key = String.valueOf(value);
        switch (key) {
            case "1":
                return "摩托车";
            case "2":
                return "货车";
            case "3":
                return "乘用车";
            case "4":
                return "农用车";
            default:
                return key;
        }
    }
}
