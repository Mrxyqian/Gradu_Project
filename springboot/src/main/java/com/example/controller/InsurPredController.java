package com.example.controller;

import com.example.common.Result;
import com.example.entity.InsurPred;
import com.example.entity.PredictionBatchRequest;
import com.example.service.InsurPredService;
import com.github.pagehelper.PageInfo;
import org.springframework.web.bind.annotation.*;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/insurPred")
public class InsurPredController {

    @Resource
    private InsurPredService insurPredService;

    @PostConstruct
    public void init() {
        System.out.println("✅ InsurPredController 初始化成功");
    }

    @PostMapping("/predict")
    public Result predict(@RequestBody PredictionBatchRequest request) {
        List<InsurPred> resultList = insurPredService.predictAndSave(request.getIds(), request.getModelVersion());
        return Result.success(resultList);
    }

    @GetMapping("/modelVersions")
    public Result modelVersions() {
        return Result.success(insurPredService.listModelVersions());
    }

    @DeleteMapping("/delete/{predId}")
    public Result delete(@PathVariable Integer predId) {
        insurPredService.deleteByPredId(predId);
        return Result.success();
    }

    @GetMapping("/selectByPredId/{predId}")
    public Result selectByPredId(@PathVariable Integer predId) {
        InsurPred insurPred = insurPredService.selectByPredId(predId);
        return Result.success(insurPred);
    }

    @GetMapping("/selectPage")
    public Result selectPage(@RequestParam(defaultValue = "1") Integer pageNum,
                             @RequestParam(defaultValue = "10") Integer pageSize,
                             InsurPred insurPred) {
        PageInfo<InsurPred> pageInfo = insurPredService.selectPage(pageNum, pageSize, insurPred);
        return Result.success(pageInfo);
    }

    @GetMapping("/riskLevelDistribution")
    public Result riskLevelDistribution() {
        List<Map<String, Object>> statistics = insurPredService.riskLevelDistribution();
        return Result.success(statistics);
    }

    @GetMapping("/claimProbabilityHistogram")
    public Result claimProbabilityHistogram() {
        List<Map<String, Object>> statistics = insurPredService.claimProbabilityHistogram();
        return Result.success(statistics);
    }

    @GetMapping("/overallStatistics")
    public Result overallStatistics() {
        Map<String, Object> statistics = insurPredService.overallStatistics();
        return Result.success(statistics);
    }

    @PostMapping("/countByBusinessIds")
    public Result countByBusinessIds(@RequestBody PredictionBatchRequest request) {
        List<Map<String, Object>> statistics = insurPredService.countByBusinessIds(request.getIds());
        return Result.success(statistics);
    }
}
