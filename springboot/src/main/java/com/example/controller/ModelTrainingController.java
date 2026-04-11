package com.example.controller;

import com.example.common.Result;
import com.example.service.ModelTrainingService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.ResponseEntity;

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
}
