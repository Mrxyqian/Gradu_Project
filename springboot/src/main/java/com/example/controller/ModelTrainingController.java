package com.example.controller;

import com.example.common.Result;
import com.example.entity.TrainDataImportRequest;
import com.example.service.ModelTrainingService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.util.Map;

@RestController
@RequestMapping("/modelTraining")
public class ModelTrainingController {

    @Resource
    private ModelTrainingService modelTrainingService;

    @PostMapping("/start")
    public Result start(@RequestBody Map<String, Object> payload, HttpSession session) {
        return Result.success(modelTrainingService.startTraining(payload, session));
    }

    @GetMapping("/jobs/latest")
    public Result latest(HttpSession session) {
        return Result.success(modelTrainingService.getLatestJob(session));
    }

    @GetMapping("/jobs/{jobId}")
    public Result detail(@PathVariable String jobId, HttpSession session) {
        return Result.success(modelTrainingService.getJob(jobId, session));
    }

    @PostMapping("/jobs/{jobId}/save-weights")
    public Result saveWeights(@PathVariable String jobId,
                              @RequestBody Map<String, Object> payload,
                              HttpSession session) {
        return Result.success(modelTrainingService.saveWeights(jobId, payload, session));
    }

    @PostMapping("/jobs/{jobId}/discard")
    public Result discard(@PathVariable String jobId, HttpSession session) {
        return Result.success(modelTrainingService.discardJob(jobId, session));
    }

    @GetMapping("/jobs/{jobId}/figures/{figureKey}")
    public ResponseEntity<byte[]> figure(@PathVariable String jobId,
                                         @PathVariable String figureKey,
                                         HttpSession session) {
        return modelTrainingService.getFigure(jobId, figureKey, session);
    }

    @GetMapping("/trainData/overview")
    public Result trainDataOverview(HttpSession session) {
        return Result.success(modelTrainingService.getTrainDataOverview(session));
    }

    @PostMapping("/trainData/import")
    public Result importTrainData(@RequestBody(required = false) TrainDataImportRequest request,
                                  HttpSession session) {
        Integer contractYear = request == null ? null : request.getContractYear();
        return Result.success(modelTrainingService.importTrainData(contractYear, session));
    }
}