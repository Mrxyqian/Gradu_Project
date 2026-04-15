package com.example.controller;

import com.example.common.Result;
import com.example.entity.AnalyticsQueryRequest;
import com.example.service.AnalyticsService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.util.Map;

@RestController
@RequestMapping("/analytics")
public class AnalyticsController {

    @Resource
    private AnalyticsService analyticsService;

    @PostMapping("/query")
    public Result query(@RequestBody AnalyticsQueryRequest request, HttpSession session) {
        Map<String, Object> result = analyticsService.query(request, session);
        return Result.success(result);
    }
}
