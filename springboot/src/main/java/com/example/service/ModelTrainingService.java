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
import org.springframework.stereotype.Service;

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

    public Object startTraining(Map<String, Object> payload, HttpSession session) {
        SessionUserUtil.requireAdmin(session);
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
