package com.example.controller;

import com.example.common.Result;
import com.example.entity.MotorInsurance;
import com.example.service.MotorInsuranceService;
import com.github.pagehelper.PageInfo;
import org.springframework.web.bind.annotation.*;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/motorInsurance")
public class MotorInsuranceController {

    @Resource
    private MotorInsuranceService motorInsuranceService;

    @PostConstruct
    public void init() {
        System.out.println("MotorInsuranceController initialized");
    }

    @PostMapping("/add")
    public Result add(@RequestBody MotorInsurance motorInsurance, HttpSession session) {
        MotorInsurance created = motorInsuranceService.add(motorInsurance, session);
        return Result.success(created);
    }

    @DeleteMapping("/delete/{id}")
    public Result delete(@PathVariable Integer id, HttpSession session) {
        motorInsuranceService.deleteById(id, session);
        return Result.success();
    }

    @PutMapping("/update")
    public Result update(@RequestBody MotorInsurance motorInsurance, HttpSession session) {
        motorInsuranceService.updateById(motorInsurance, session);
        return Result.success();
    }

    @GetMapping("/selectById/{id}")
    public Result selectById(@PathVariable Integer id, HttpSession session) {
        MotorInsurance motorInsurance = motorInsuranceService.selectById(id, session);
        return Result.success(motorInsurance);
    }

    @GetMapping("/selectPage")
    public Result selectPage(@RequestParam(defaultValue = "1") Integer pageNum,
                             @RequestParam(defaultValue = "10") Integer pageSize,
                             MotorInsurance motorInsurance,
                             HttpSession session) {
        PageInfo<MotorInsurance> pageInfo = motorInsuranceService.selectPage(pageNum, pageSize, motorInsurance, session);
        return Result.success(pageInfo);
    }

    @GetMapping("/statisticsByRiskType")
    public Result statisticsByRiskType(HttpSession session) {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByRiskType(session);
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByArea")
    public Result statisticsByArea(HttpSession session) {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByArea(session);
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByPayment")
    public Result statisticsByPayment(HttpSession session) {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByPayment(session);
        return Result.success(statistics);
    }

    @GetMapping("/overallStatistics")
    public Result overallStatistics(HttpSession session) {
        Map<String, Object> statistics = motorInsuranceService.overallStatistics(session);
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByFuelType")
    public Result statisticsByFuelType(HttpSession session) {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByFuelType(session);
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByMatriculationYear")
    public Result statisticsByMatriculationYear(HttpSession session) {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByMatriculationYear(session);
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByDistributionChannel")
    public Result statisticsByDistributionChannel(HttpSession session) {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByDistributionChannel(session);
        return Result.success(statistics);
    }
}
