package com.example.controller;

import com.example.common.Result;
import com.example.entity.VehicleInfo;
import com.example.service.VehicleInfoService;
import com.github.pagehelper.PageInfo;
import org.springframework.web.bind.annotation.*;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/vehicleInfo")
public class VehicleInfoController {

    @Resource
    private VehicleInfoService vehicleInfoService;

    @PostConstruct
    public void init() {
        System.out.println("✅ VehicleInfoController 初始化成功");
    }

    @GetMapping("/selectById/{id}")
    public Result selectById(@PathVariable Integer id) {
        VehicleInfo vehicleInfo = vehicleInfoService.selectById(id);
        return Result.success(vehicleInfo);
    }

    @GetMapping("/selectPage")
    public Result selectPage(@RequestParam(defaultValue = "1") Integer pageNum,
                             @RequestParam(defaultValue = "10") Integer pageSize,
                             VehicleInfo vehicleInfo) {
        PageInfo<VehicleInfo> pageInfo = vehicleInfoService.selectPage(pageNum, pageSize, vehicleInfo);
        return Result.success(pageInfo);
    }

    @GetMapping("/statisticsByTypeRisk")
    public Result statisticsByTypeRisk() {
        List<Map<String, Object>> statistics = vehicleInfoService.statisticsByTypeRisk();
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByTypeFuel")
    public Result statisticsByTypeFuel() {
        List<Map<String, Object>> statistics = vehicleInfoService.statisticsByTypeFuel();
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByYear")
    public Result statisticsByYear() {
        List<Map<String, Object>> statistics = vehicleInfoService.statisticsByYear();
        return Result.success(statistics);
    }
}
