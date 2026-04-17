package com.example.service;

import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONNull;
import cn.hutool.json.JSONUtil;
import com.example.common.SessionUserUtil;
import com.example.entity.ClaimTypes;
import com.example.entity.InsurPred;
import com.example.entity.MotorInsurance;
import com.example.entity.VehicleInfo;
import com.example.exception.CustomException;
import com.example.mapper.ClaimTypesMapper;
import com.example.mapper.InsurPredMapper;
import com.example.mapper.MotorInsuranceMapper;
import com.example.mapper.VehicleInfoMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class InsurPredService {

    @Resource
    private InsurPredMapper insurPredMapper;
    @Resource
    private MotorInsuranceMapper motorInsuranceMapper;
    @Resource
    private ClaimTypesMapper claimTypesMapper;
    @Resource
    private VehicleInfoMapper vehicleInfoMapper;

    @Value("${fastapi.base-url:http://localhost:8000}")
    private String fastApiBaseUrl;

    @Value("${fastapi.timeout:30000}")
    private Integer fastApiTimeout;

    public InsurPred predictAndSave(MotorInsurance record, String modelVersion) {
        if (record == null) {
            throw new CustomException("预测记录不能为空");
        }

        JSONObject resultObject = callFastApiPredict(record, modelVersion);
        InsurPred insurPred = convertToInsurPred(resultObject, 0);
        insurPredMapper.insert(insurPred);
        return hydrateExplanationFields(insurPredMapper.selectByPredId(insurPred.getPredId()));
    }

    public InsurPred predictAndSaveByPolicyId(Integer id, String modelVersion, HttpSession session) {
        if (id == null || id <= 0) {
            throw new CustomException("保单编号不能为空且必须大于0");
        }

        MotorInsurance record = buildPredictionRecordById(id, session);
        JSONObject resultObject = callFastApiPredict(record, modelVersion);
        InsurPred insurPred = convertToInsurPred(resultObject, id);
        insurPredMapper.insert(insurPred);
        return hydrateExplanationFields(insurPredMapper.selectByPredId(insurPred.getPredId()));
    }

    public void deleteByPredId(Integer predId) {
        insurPredMapper.deleteByPredId(predId);
    }

    public InsurPred selectByPredId(Integer predId) {
        return hydrateExplanationFields(insurPredMapper.selectByPredId(predId));
    }

    public PageInfo<InsurPred> selectPage(Integer pageNum, Integer pageSize, InsurPred insurPred) {
        PageHelper.startPage(pageNum, pageSize);
        List<InsurPred> insurPredList = insurPredMapper.selectAll(insurPred);
        return PageInfo.of(insurPredList);
    }

    public List<Map<String, Object>> riskLevelDistribution() {
        return insurPredMapper.riskLevelDistribution();
    }

    public List<Map<String, Object>> claimProbabilityHistogram() {
        return insurPredMapper.claimProbabilityHistogram();
    }

    public Map<String, Object> overallStatistics() {
        return insurPredMapper.overallStatistics();
    }

    public Object listModelVersions() {
        String url = fastApiBaseUrl + "/models/versions";
        try (HttpResponse response = HttpRequest.get(url)
                .timeout(fastApiTimeout)
                .execute()) {

            if (response.getStatus() < 200 || response.getStatus() >= 300) {
                throw new CustomException("FastAPI model versions request failed, HTTP status: " + response.getStatus());
            }

            JSONObject responseObj = JSONUtil.parseObj(response.body());
            if (!"200".equals(responseObj.getStr("code"))) {
                throw new CustomException("FastAPI model versions service returned error: " + responseObj.getStr("msg"));
            }

            return normalizeJsonValue(responseObj.get("data"));
        } catch (CustomException e) {
            throw e;
        } catch (Exception e) {
            throw new CustomException("Failed to call FastAPI model versions service: " + e.getMessage());
        }
    }

    private JSONObject callFastApiPredict(MotorInsurance record, String modelVersion) {
        String url = fastApiBaseUrl + "/predict";

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("record", JSONUtil.parseObj(record));
        payload.put("modelVersion", modelVersion);

        try (HttpResponse response = HttpRequest.post(url)
                .timeout(fastApiTimeout)
                .header("Content-Type", "application/json")
                .body(JSONUtil.toJsonStr(payload))
                .execute()) {

            if (response.getStatus() < 200 || response.getStatus() >= 300) {
                throw new CustomException("FastAPI prediction request failed, HTTP status: " + response.getStatus());
            }

            JSONObject responseObj = JSONUtil.parseObj(response.body());
            if (!"200".equals(responseObj.getStr("code"))) {
                throw new CustomException("FastAPI prediction service returned error: " + responseObj.getStr("msg"));
            }

            JSONObject result = responseObj.getJSONObject("data");
            if (result == null || result.isEmpty()) {
                throw new CustomException("FastAPI prediction response is empty");
            }
            return result;
        } catch (CustomException e) {
            throw e;
        } catch (Exception e) {
            throw new CustomException("Failed to call FastAPI prediction service: " + e.getMessage());
        }
    }

    private MotorInsurance buildPredictionRecordById(Integer id, HttpSession session) {
        MotorInsurance motorInsurance = motorInsuranceMapper.selectById(id);
        if (motorInsurance == null) {
            throw new CustomException("未找到对应的保单信息，无法执行预测");
        }
        SessionUserUtil.requireOwnerOrAdmin(motorInsurance.getCreatorEmployeeNo(), session);

        ClaimTypes claimRecord = claimTypesMapper.selectById(id);
        if (claimRecord == null) {
            throw new CustomException("该ID缺少理赔记录信息，无法执行预测");
        }

        VehicleInfo vehicleInfo = vehicleInfoMapper.selectById(id);
        if (vehicleInfo == null) {
            throw new CustomException("该ID缺少车辆信息，无法执行预测");
        }

        MotorInsurance record = new MotorInsurance();
        record.setId(motorInsurance.getId());
        record.setDateStartContract(motorInsurance.getDateStartContract());
        record.setDateLastRenewal(motorInsurance.getDateLastRenewal());
        record.setDateNextRenewal(motorInsurance.getDateNextRenewal());
        record.setDateBirth(motorInsurance.getDateBirth());
        record.setDateDrivingLicence(motorInsurance.getDateDrivingLicence());
        record.setDistributionChannel(motorInsurance.getDistributionChannel());
        record.setSeniority(motorInsurance.getSeniority());
        record.setPoliciesInForce(motorInsurance.getPoliciesInForce());
        record.setMaxPolicies(motorInsurance.getMaxPolicies());
        record.setMaxProducts(motorInsurance.getMaxProducts());
        record.setLapse(motorInsurance.getLapse());
        record.setDateLapse(motorInsurance.getDateLapse());
        record.setPayment(motorInsurance.getPayment());
        record.setPremium(motorInsurance.getPremium());
        record.setNClaimsHistory(claimRecord.getNClaimsHistory());
        record.setRClaimsHistory(claimRecord.getRClaimsHistory());
        record.setTypeRisk(claimRecord.getTypeRisk() != null ? claimRecord.getTypeRisk() : motorInsurance.getTypeRisk());
        record.setArea(claimRecord.getArea() != null ? claimRecord.getArea() : motorInsurance.getArea());
        record.setSecondDriver(motorInsurance.getSecondDriver());
        record.setYearMatriculation(vehicleInfo.getYearMatriculation());
        record.setPower(vehicleInfo.getPower());
        record.setCylinderCapacity(vehicleInfo.getCylinderCapacity());
        record.setValueVehicle(vehicleInfo.getValueVehicle());
        record.setNDoors(vehicleInfo.getNDoors());
        record.setTypeFuel(vehicleInfo.getTypeFuel());
        record.setLength(vehicleInfo.getLength());
        record.setWeight(vehicleInfo.getWeight());
        return record;
    }

    private InsurPred convertToInsurPred(JSONObject item, Integer businessId) {
        InsurPred insurPred = new InsurPred();
        insurPred.setId(businessId == null ? 0 : businessId);
        insurPred.setClaimProbability(toBigDecimal(item.get("claimProbability")));
        insurPred.setClaimFlag(item.getInt("claimFlag", 0));
        insurPred.setRiskLevel(item.getStr("riskLevel"));
        insurPred.setThresholdUsed(toBigDecimal(item.get("thresholdUsed")));
        insurPred.setModelVersion(item.getStr("modelVersion"));
        insurPred.setPredictionTime(normalizeDateTime(item.getStr("generatedAt")));
        insurPred.setExplanationSummary(item.getStr("explanationSummary"));
        List<Map<String, Object>> positiveFactors = toFactorList(item.get("positiveFactors"));
        List<Map<String, Object>> negativeFactors = toFactorList(item.get("negativeFactors"));
        insurPred.setPositiveFactors(positiveFactors);
        insurPred.setNegativeFactors(negativeFactors);
        insurPred.setPositiveFactorsJson(JSONUtil.toJsonStr(positiveFactors));
        insurPred.setNegativeFactorsJson(JSONUtil.toJsonStr(negativeFactors));
        return insurPred;
    }

    private InsurPred hydrateExplanationFields(InsurPred insurPred) {
        if (insurPred == null) {
            return null;
        }
        insurPred.setPositiveFactors(parseFactorJson(insurPred.getPositiveFactorsJson()));
        insurPred.setNegativeFactors(parseFactorJson(insurPred.getNegativeFactorsJson()));
        return insurPred;
    }

    private String normalizeDateTime(String generatedAt) {
        if (generatedAt == null || generatedAt.trim().isEmpty()) {
            return null;
        }
        return generatedAt.replace("T", " ");
    }

    private BigDecimal toBigDecimal(Object value) {
        if (value == null) {
            return BigDecimal.ZERO;
        }
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (Exception e) {
            return BigDecimal.ZERO;
        }
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

    private List<Map<String, Object>> toFactorList(Object value) {
        Object normalized = normalizeJsonValue(value);
        List<Map<String, Object>> factors = new ArrayList<>();
        if (!(normalized instanceof List<?>)) {
            return factors;
        }

        for (Object item : (List<?>) normalized) {
            if (!(item instanceof Map<?, ?>)) {
                continue;
            }
            Map<String, Object> factor = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) item).entrySet()) {
                factor.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            factors.add(factor);
        }
        return factors;
    }

    private List<Map<String, Object>> parseFactorJson(String json) {
        if (json == null || json.trim().isEmpty()) {
            return new ArrayList<>();
        }
        try {
            return toFactorList(JSONUtil.parse(json));
        } catch (Exception e) {
            return new ArrayList<>();
        }
    }
}
