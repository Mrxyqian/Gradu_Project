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
        System.out.println("✅ MotorInsuranceController 初始化成功");
    }

    @PostMapping("/add")
    public Result add(@RequestBody MotorInsurance motorInsurance) {
        motorInsuranceService.add(motorInsurance);
        return Result.success();
    }

    @DeleteMapping("/delete/{id}")
    public Result delete(@PathVariable Integer id, HttpSession session) {
        motorInsuranceService.deleteById(id, session);
        return Result.success();
    }

    @PutMapping("/update")
    public Result update(@RequestBody MotorInsurance motorInsurance) {
        motorInsuranceService.updateById(motorInsurance);
        return Result.success();
    }

    @GetMapping("/selectById/{id}")
    public Result selectById(@PathVariable Integer id) {
        MotorInsurance motorInsurance = motorInsuranceService.selectById(id);
        return Result.success(motorInsurance);
    }

    @GetMapping("/selectPage")
    public Result selectPage(@RequestParam(defaultValue = "1") Integer pageNum,
                             @RequestParam(defaultValue = "10") Integer pageSize,
                             MotorInsurance motorInsurance) {
        PageInfo<MotorInsurance> pageInfo = motorInsuranceService.selectPage(pageNum, pageSize, motorInsurance);
        return Result.success(pageInfo);
    }

    @GetMapping("/statisticsByRiskType")
    public Result statisticsByRiskType() {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByRiskType();
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByArea")
    public Result statisticsByArea() {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByArea();
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByPayment")
    public Result statisticsByPayment() {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByPayment();
        return Result.success(statistics);
    }

    @GetMapping("/overallStatistics")
    public Result overallStatistics() {
        Map<String, Object> statistics = motorInsuranceService.overallStatistics();
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByFuelType")
    public Result statisticsByFuelType() {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByFuelType();
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByMatriculationYear")
    public Result statisticsByMatriculationYear() {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByMatriculationYear();
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByDistributionChannel")
    public Result statisticsByDistributionChannel() {
        List<Map<String, Object>> statistics = motorInsuranceService.statisticsByDistributionChannel();
        return Result.success(statistics);
    }
}
