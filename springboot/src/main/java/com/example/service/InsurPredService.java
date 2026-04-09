package com.example.service;

import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONNull;
import cn.hutool.json.JSONUtil;
import com.example.entity.InsurPred;
import com.example.entity.MotorInsurance;
import com.example.exception.CustomException;
import com.example.mapper.InsurPredMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class InsurPredService {

    @Resource
    private InsurPredMapper insurPredMapper;

    @Resource
    private MotorInsuranceService motorInsuranceService;

    @Value("${fastapi.base-url:http://localhost:8000}")
    private String fastApiBaseUrl;

    @Value("${fastapi.timeout:30000}")
    private Integer fastApiTimeout;

    public List<InsurPred> predictAndSave(List<Integer> ids, String modelVersion) {
        validatePredictIds(ids);

        List<Integer> distinctIds = ids.stream().distinct().collect(Collectors.toList());
        List<MotorInsurance> motorInsuranceList = motorInsuranceService.selectByIds(distinctIds);
        validatePoliciesFound(distinctIds, motorInsuranceList);

        JSONArray resultArray = callFastApiBatchPredict(motorInsuranceList, modelVersion);
        List<InsurPred> savedList = new ArrayList<>();
        for (int i = 0; i < resultArray.size(); i++) {
            JSONObject item = resultArray.getJSONObject(i);
            InsurPred insurPred = convertToInsurPred(item);
            insurPredMapper.insert(insurPred);
            savedList.add(insurPredMapper.selectByPredId(insurPred.getPredId()));
        }
        return savedList;
    }

    public void deleteByPredId(Integer predId) {
        insurPredMapper.deleteByPredId(predId);
    }

    public InsurPred selectByPredId(Integer predId) {
        return insurPredMapper.selectByPredId(predId);
    }

    public PageInfo<InsurPred> selectPage(Integer pageNum, Integer pageSize, InsurPred insurPred) {
        PageHelper.startPage(pageNum, pageSize);
        List<InsurPred> insurPredList = insurPredMapper.selectAll(insurPred);
        return PageInfo.of(insurPredList);
    }

    public List<Map<String, Object>> riskLevelDistribution() {
        return insurPredMapper.riskLevelDistribution();
    }

    public List<Map<String, Object>> claimAmountHistogram() {
        return insurPredMapper.claimAmountHistogram();
    }

    public Map<String, Object> overallStatistics() {
        return insurPredMapper.overallStatistics();
    }

    public List<Map<String, Object>> countByBusinessIds(List<Integer> ids) {
        validatePredictIds(ids);
        return insurPredMapper.countByBusinessIds(ids.stream().distinct().collect(Collectors.toList()));
    }

    public Object listModelVersions() {
        String url = fastApiBaseUrl + "/models/versions";
        try (HttpResponse response = HttpRequest.get(url)
                .timeout(fastApiTimeout)
                .execute()) {

            if (response.getStatus() < 200 || response.getStatus() >= 300) {
                throw new CustomException("FastAPI 模型版本服务调用失败，HTTP 状态码: " + response.getStatus());
            }

            JSONObject responseObj = JSONUtil.parseObj(response.body());
            if (!"200".equals(responseObj.getStr("code"))) {
                throw new CustomException("FastAPI 模型版本服务返回异常: " + responseObj.getStr("msg"));
            }

            return normalizeJsonValue(responseObj.get("data"));
        } catch (CustomException e) {
            throw e;
        } catch (Exception e) {
            throw new CustomException("调用 FastAPI 模型版本服务异常: " + e.getMessage());
        }
    }

    private void validatePredictIds(List<Integer> ids) {
        if (ids == null || ids.isEmpty()) {
            throw new CustomException("请至少传入 1 条保单 ID");
        }
        if (ids.size() > 10) {
            throw new CustomException("单次最多支持 10 条保单预测");
        }
        for (Integer id : ids) {
            if (id == null) {
                throw new CustomException("保单 ID 不能为空");
            }
        }
    }

    private void validatePoliciesFound(List<Integer> requestedIds, List<MotorInsurance> motorInsuranceList) {
        Set<Integer> foundIds = new HashSet<>();
        for (MotorInsurance motorInsurance : motorInsuranceList) {
            foundIds.add(motorInsurance.getId());
        }

        List<Integer> missingIds = new ArrayList<>();
        for (Integer requestedId : requestedIds) {
            if (!foundIds.contains(requestedId)) {
                missingIds.add(requestedId);
            }
        }

        if (!missingIds.isEmpty()) {
            throw new CustomException("以下保单 ID 不存在，无法预测: " + missingIds);
        }
    }

    private JSONArray callFastApiBatchPredict(List<MotorInsurance> motorInsuranceList, String modelVersion) {
        String url = fastApiBaseUrl + "/predict/batch";

        List<Object> recordList = new ArrayList<>();
        for (MotorInsurance motorInsurance : motorInsuranceList) {
            JSONObject recordMap = JSONUtil.parseObj(motorInsurance);
            recordList.add(recordMap);
        }

        Map<String, Object> payload = new HashMap<>();
        payload.put("records", recordList);
        payload.put("modelVersion", modelVersion);

        try (HttpResponse response = HttpRequest.post(url)
                .timeout(fastApiTimeout)
                .header("Content-Type", "application/json")
                .body(JSONUtil.toJsonStr(payload))
                .execute()) {

            if (response.getStatus() < 200 || response.getStatus() >= 300) {
                throw new CustomException("FastAPI 预测服务调用失败，HTTP 状态码: " + response.getStatus());
            }

            JSONObject responseObj = JSONUtil.parseObj(response.body());
            if (!"200".equals(responseObj.getStr("code"))) {
                throw new CustomException("FastAPI 预测服务返回异常: " + responseObj.getStr("msg"));
            }

            JSONObject dataObj = responseObj.getJSONObject("data");
            if (dataObj == null) {
                throw new CustomException("FastAPI 预测服务未返回 data 数据");
            }

            JSONArray results = dataObj.getJSONArray("results");
            if (results == null || results.isEmpty()) {
                throw new CustomException("FastAPI 预测服务未返回有效预测结果");
            }

            return results;
        } catch (CustomException e) {
            throw e;
        } catch (Exception e) {
            throw new CustomException("调用 FastAPI 预测服务异常: " + e.getMessage());
        }
    }

    private InsurPred convertToInsurPred(JSONObject item) {
        InsurPred insurPred = new InsurPred();
        insurPred.setId(item.getInt("sourceId"));
        insurPred.setClaimProbability(toBigDecimal(item.get("claimProbability")));
        insurPred.setClaimFlag(item.getInt("claimFlag", 0));
        insurPred.setRiskLevel(item.getStr("riskLevel"));
        insurPred.setExpectedClaimAmount(toBigDecimal(item.get("expectedClaimAmount")));
        insurPred.setThresholdUsed(toBigDecimal(item.get("thresholdUsed")));
        insurPred.setModelVersion(item.getStr("modelVersion"));
        insurPred.setPredictionTime(normalizeDateTime(item.getStr("generatedAt")));
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
}
