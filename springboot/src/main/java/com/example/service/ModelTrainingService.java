package com.example.service;

import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONNull;
import cn.hutool.json.JSONUtil;
import com.example.common.SessionUserUtil;
import com.example.exception.CustomException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class ModelTrainingService {

    @Value("${fastapi.base-url:http://localhost:8000}")
    private String fastApiBaseUrl;

    @Value("${fastapi.timeout:30000}")
    private Integer fastApiTimeout;

    @Resource
    private JdbcTemplate jdbcTemplate;

    public Object startTraining(Map<String, Object> payload, HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        ensureTrainDataTableInitialized();
        return postForData("/training/start", payload);
    }

    public Object getLatestJob(HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        return getForData("/training/jobs/latest");
    }

    public Object getJob(String jobId, HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        return getForData("/training/jobs/" + jobId);
    }

    public Object saveWeights(String jobId, Map<String, Object> payload, HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        return postForData("/training/jobs/" + jobId + "/save-weights", payload);
    }

    public Object discardJob(String jobId, HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        return postForData("/training/jobs/" + jobId + "/discard", new LinkedHashMap<>());
    }

    public ResponseEntity<byte[]> getFigure(String jobId, String figureKey, HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        String url = fastApiBaseUrl + "/training/jobs/" + jobId + "/figures/" + figureKey;
        try (HttpResponse response = HttpRequest.get(url)
                .timeout(fastApiTimeout)
                .execute()) {
            if (response.getStatus() < 200 || response.getStatus() >= 300) {
                throw new CustomException("获取训练图像失败: " + response.body());
            }

            String contentType = response.header("Content-Type");
            MediaType mediaType = MediaType.APPLICATION_OCTET_STREAM;
            if (contentType != null && !contentType.trim().isEmpty()) {
                mediaType = MediaType.parseMediaType(contentType);
            }

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_OCTET_STREAM.equals(mediaType) ? MediaType.IMAGE_PNG : mediaType);
            headers.setCacheControl("no-cache, no-store, must-revalidate");
            headers.set(HttpHeaders.CONTENT_DISPOSITION, "inline");
            return new ResponseEntity<>(response.bodyBytes(), headers, HttpStatus.OK);
        } catch (CustomException e) {
            throw e;
        } catch (Exception e) {
            throw new CustomException("调用 FastAPI 模型训练图像服务异常: " + e.getMessage());
        }
    }

    public Object getTrainDataOverview(HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        ensureTrainDataTableInitialized();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("totalCount", jdbcTemplate.queryForObject("SELECT COUNT(*) FROM train_data", Integer.class));
        result.put("distinctIdCount", jdbcTemplate.queryForObject("SELECT COUNT(DISTINCT ID) FROM train_data", Integer.class));
        result.put("availableYears", jdbcTemplate.queryForList(
                "SELECT DISTINCT RIGHT(TRIM(Date_start_contract), 4) AS contractYear " +
                        "FROM motor_insurance WHERE Date_start_contract IS NOT NULL AND TRIM(Date_start_contract) <> '' " +
                        "ORDER BY contractYear DESC",
                String.class
        ));
        return result;
    }

    public Object importTrainData(Integer contractYear, Boolean overwriteExisting, HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        ensureTrainDataTableInitialized();

        boolean overwrite = Boolean.TRUE.equals(overwriteExisting);
        String candidateWhere = buildYearWhere("m", contractYear);
        String eligibleFrom =
                " FROM motor_insurance m " +
                "INNER JOIN claim_record c ON c.ID = m.ID " +
                "INNER JOIN vehicle_info v ON v.ID = m.ID " +
                buildYearWhere("m", contractYear);
        String skippedWhere = buildSkippedWhere(contractYear);
        Object[] yearArgs = buildYearArgs(contractYear);

        Integer candidateCount = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM motor_insurance m" + candidateWhere,
                Integer.class,
                yearArgs
        );
        Integer eligibleCount = jdbcTemplate.queryForObject(
                "SELECT COUNT(*)" + eligibleFrom,
                Integer.class,
                yearArgs
        );
        Integer existingCount = jdbcTemplate.queryForObject(
                "SELECT COUNT(DISTINCT t.ID) FROM train_data t INNER JOIN (SELECT m.ID" + eligibleFrom + ") eligible ON eligible.ID = t.ID",
                Integer.class,
                yearArgs
        );
        List<Integer> conflictIds = existingCount != null && existingCount > 0
                ? jdbcTemplate.queryForList(
                "SELECT t.ID FROM train_data t INNER JOIN (SELECT m.ID" + eligibleFrom + ") eligible ON eligible.ID = t.ID ORDER BY t.ID LIMIT 20",
                Integer.class,
                yearArgs
        )
                : new ArrayList<>();
        List<Integer> skippedIds = jdbcTemplate.queryForList(
                "SELECT m.ID FROM motor_insurance m " +
                        "LEFT JOIN claim_record c ON c.ID = m.ID " +
                        "LEFT JOIN vehicle_info v ON v.ID = m.ID" +
                        skippedWhere +
                        " ORDER BY m.ID",
                Integer.class,
                yearArgs
        );

        int conflictCount = existingCount == null ? 0 : existingCount;
        if (conflictCount > 0 && !overwrite) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("contractYear", contractYear);
            result.put("candidateCount", candidateCount == null ? 0 : candidateCount);
            result.put("eligibleCount", eligibleCount == null ? 0 : eligibleCount);
            result.put("processedCount", 0);
            result.put("insertedCount", 0);
            result.put("updatedCount", 0);
            result.put("conflictCount", conflictCount);
            result.put("conflictIds", conflictIds);
            result.put("requiresOverwriteConfirm", true);
            result.put("skippedCount", skippedIds.size());
            result.put("skippedIds", skippedIds);
            result.put("trainDataTotalCount", jdbcTemplate.queryForObject("SELECT COUNT(*) FROM train_data", Integer.class));
            result.put("trainDataDistinctIdCount", jdbcTemplate.queryForObject("SELECT COUNT(DISTINCT ID) FROM train_data", Integer.class));
            return result;
        }

        if (eligibleCount != null && eligibleCount > 0) {
            jdbcTemplate.update(
                    "INSERT INTO train_data (" +
                            "ID, Date_start_contract, Date_last_renewal, Date_next_renewal, Date_birth, Date_driving_licence, " +
                            "Distribution_channel, Seniority, Policies_in_force, Max_policies, Max_products, Lapse, Date_lapse, Payment, Premium, " +
                            "Cost_claims_year, N_claims_year, N_claims_history, R_Claims_history, Type_risk, Area, Second_driver, " +
                            "Year_matriculation, Power, Cylinder_capacity, Value_vehicle, N_doors, Type_fuel, Length, Weight) " +
                            "SELECT m.ID, m.Date_start_contract, m.Date_last_renewal, m.Date_next_renewal, m.Date_birth, m.Date_driving_licence, " +
                            "m.Distribution_channel, m.Seniority, m.Policies_in_force, m.Max_policies, m.Max_products, m.Lapse, m.Date_lapse, m.Payment, m.Premium, " +
                            "c.Cost_claims_year, c.N_claims_year, c.N_claims_history, c.R_Claims_history, c.Type_risk, c.Area, m.Second_driver, " +
                            "v.Year_matriculation, v.Power, v.Cylinder_capacity, v.Value_vehicle, v.N_doors, v.Type_fuel, v.Length, v.Weight" +
                            eligibleFrom +
                            " ON DUPLICATE KEY UPDATE " +
                            "Date_start_contract = VALUES(Date_start_contract), " +
                            "Date_last_renewal = VALUES(Date_last_renewal), " +
                            "Date_next_renewal = VALUES(Date_next_renewal), " +
                            "Date_birth = VALUES(Date_birth), " +
                            "Date_driving_licence = VALUES(Date_driving_licence), " +
                            "Distribution_channel = VALUES(Distribution_channel), " +
                            "Seniority = VALUES(Seniority), " +
                            "Policies_in_force = VALUES(Policies_in_force), " +
                            "Max_policies = VALUES(Max_policies), " +
                            "Max_products = VALUES(Max_products), " +
                            "Lapse = VALUES(Lapse), " +
                            "Date_lapse = VALUES(Date_lapse), " +
                            "Payment = VALUES(Payment), " +
                            "Premium = VALUES(Premium), " +
                            "Cost_claims_year = VALUES(Cost_claims_year), " +
                            "N_claims_year = VALUES(N_claims_year), " +
                            "N_claims_history = VALUES(N_claims_history), " +
                            "R_Claims_history = VALUES(R_Claims_history), " +
                            "Type_risk = VALUES(Type_risk), " +
                            "Area = VALUES(Area), " +
                            "Second_driver = VALUES(Second_driver), " +
                            "Year_matriculation = VALUES(Year_matriculation), " +
                            "Power = VALUES(Power), " +
                            "Cylinder_capacity = VALUES(Cylinder_capacity), " +
                            "Value_vehicle = VALUES(Value_vehicle), " +
                            "N_doors = VALUES(N_doors), " +
                            "Type_fuel = VALUES(Type_fuel), " +
                            "Length = VALUES(Length), " +
                            "Weight = VALUES(Weight)",
                    yearArgs
            );
        }

        int processedCount = eligibleCount == null ? 0 : eligibleCount;
        int updatedCount = overwrite ? conflictCount : 0;
        int insertedCount = Math.max(processedCount - updatedCount, 0);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("contractYear", contractYear);
        result.put("candidateCount", candidateCount == null ? 0 : candidateCount);
        result.put("processedCount", processedCount);
        result.put("insertedCount", insertedCount);
        result.put("updatedCount", updatedCount);
        result.put("conflictCount", conflictCount);
        result.put("conflictIds", conflictIds);
        result.put("requiresOverwriteConfirm", false);
        result.put("skippedCount", skippedIds.size());
        result.put("skippedIds", skippedIds);
        result.put("trainDataTotalCount", jdbcTemplate.queryForObject("SELECT COUNT(*) FROM train_data", Integer.class));
        result.put("trainDataDistinctIdCount", jdbcTemplate.queryForObject("SELECT COUNT(DISTINCT ID) FROM train_data", Integer.class));
        return result;
    }

    private void ensureTrainDataTableInitialized() {
        Integer backupExists = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'motor_insurance_backup_20260413_idfix'",
                Integer.class
        );
        if (backupExists == null || backupExists == 0) {
            throw new CustomException("训练备份表 motor_insurance_backup_20260413_idfix 不存在");
        }

        Integer trainDataExists = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'train_data'",
                Integer.class
        );
        if (trainDataExists == null || trainDataExists == 0) {
            jdbcTemplate.execute("CREATE TABLE train_data LIKE motor_insurance_backup_20260413_idfix");
            jdbcTemplate.execute("INSERT INTO train_data SELECT * FROM motor_insurance_backup_20260413_idfix");
        }

        Integer primaryKeyExists = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = DATABASE() AND table_name = 'train_data' AND constraint_type = 'PRIMARY KEY'",
                Integer.class
        );
        if (primaryKeyExists == null || primaryKeyExists == 0) {
            Integer duplicateIdCount = jdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM (SELECT ID FROM train_data GROUP BY ID HAVING COUNT(*) > 1) duplicated_ids",
                    Integer.class
            );
            if (duplicateIdCount != null && duplicateIdCount > 0) {
                throw new CustomException("train_data 瀛樺湪閲嶅 ID锛屾棤娉曡缃负涓婚敭");
            }

            Integer idIndexExists = jdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'train_data' AND index_name = 'idx_train_data_id'",
                    Integer.class
            );
            if (idIndexExists != null && idIndexExists > 0) {
                jdbcTemplate.execute("ALTER TABLE train_data DROP INDEX idx_train_data_id, ADD PRIMARY KEY (ID)");
            } else {
                jdbcTemplate.execute("ALTER TABLE train_data ADD PRIMARY KEY (ID)");
            }
        }
    }

    private Object[] buildYearArgs(Integer contractYear) {
        if (contractYear == null) {
            return new Object[0];
        }
        return new Object[]{String.valueOf(contractYear)};
    }

    private String buildYearWhere(String alias, Integer contractYear) {
        if (contractYear == null) {
            return "";
        }
        return " WHERE RIGHT(TRIM(" + alias + ".Date_start_contract), 4) = ?";
    }

    private String buildSkippedWhere(Integer contractYear) {
        if (contractYear == null) {
            return " WHERE (c.ID IS NULL OR v.ID IS NULL)";
        }
        return " WHERE RIGHT(TRIM(m.Date_start_contract), 4) = ? AND (c.ID IS NULL OR v.ID IS NULL)";
    }

    private Object getForData(String path) {
        String url = fastApiBaseUrl + path;
        try (HttpResponse response = HttpRequest.get(url)
                .timeout(fastApiTimeout)
                .execute()) {
            return extractData(response, "获取模型训练信息失败");
        } catch (CustomException e) {
            throw e;
        } catch (Exception e) {
            throw new CustomException("调用 FastAPI 模型训练服务异常: " + e.getMessage());
        }
    }

    private Object postForData(String path, Object payload) {
        String url = fastApiBaseUrl + path;
        try (HttpResponse response = HttpRequest.post(url)
                .timeout(fastApiTimeout)
                .header("Content-Type", "application/json")
                .body(JSONUtil.toJsonStr(payload))
                .execute()) {
            return extractData(response, "调用模型训练服务失败");
        } catch (CustomException e) {
            throw e;
        } catch (Exception e) {
            throw new CustomException("调用 FastAPI 模型训练服务异常: " + e.getMessage());
        }
    }

    private Object extractData(HttpResponse response, String defaultMessage) {
        String body = response.body();
        JSONObject responseObj = parseResponse(body);

        if (response.getStatus() < 200 || response.getStatus() >= 300) {
            throw new CustomException(defaultMessage + ": " + extractErrorMessage(responseObj, body));
        }

        if (responseObj == null) {
            throw new CustomException(defaultMessage + ": 返回结果不是有效的 JSON");
        }

        if (!"200".equals(responseObj.getStr("code"))) {
            throw new CustomException(defaultMessage + ": " + responseObj.getStr("msg", "未知错误"));
        }
        return normalizeJsonValue(responseObj.get("data"));
    }

    private JSONObject parseResponse(String body) {
        try {
            return JSONUtil.parseObj(body);
        } catch (Exception e) {
            return null;
        }
    }

    private String extractErrorMessage(JSONObject responseObj, String rawBody) {
        if (responseObj == null) {
            return rawBody == null || rawBody.trim().isEmpty() ? "未知错误" : rawBody;
        }
        String detail = responseObj.getStr("detail");
        if (detail != null && !detail.trim().isEmpty()) {
            return detail;
        }
        String msg = responseObj.getStr("msg");
        if (msg != null && !msg.trim().isEmpty()) {
            return msg;
        }
        return rawBody == null || rawBody.trim().isEmpty() ? "未知错误" : rawBody;
    }

    private Object normalizeJsonValue(Object value) {
        if (value == null || value instanceof JSONNull) {
            return null;
        }

        if (value instanceof JSONObject) {
            JSONObject jsonObject = (JSONObject) value;
            Map<String, Object> map = new LinkedHashMap<>();
            for (String key : jsonObject.keySet()) {
                map.put(key, normalizeJsonValue(jsonObject.get(key)));
            }
            return map;
        }

        if (value instanceof JSONArray) {
            JSONArray jsonArray = (JSONArray) value;
            List<Object> list = new ArrayList<>();
            for (Object item : jsonArray) {
                list.add(normalizeJsonValue(item));
            }
            return list;
        }

        if (value instanceof Map) {
            Map<?, ?> rawMap = (Map<?, ?>) value;
            Map<String, Object> map = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
                map.put(String.valueOf(entry.getKey()), normalizeJsonValue(entry.getValue()));
            }
            return map;
        }

        if (value instanceof Iterable) {
            List<Object> list = new ArrayList<>();
            for (Object item : (Iterable<?>) value) {
                list.add(normalizeJsonValue(item));
            }
            return list;
        }

        return value;
    }
}
