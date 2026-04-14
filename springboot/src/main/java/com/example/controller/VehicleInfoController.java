package com.example.controller;

import com.example.common.Result;
import com.example.entity.VehicleInfo;
import com.example.service.VehicleInfoService;
import com.github.pagehelper.PageInfo;
import org.springframework.web.bind.annotation.*;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/vehicleInfo")
public class VehicleInfoController {

    @Resource
    private VehicleInfoService vehicleInfoService;

    @PostConstruct
    public void init() {
        System.out.println("VehicleInfoController initialized");
    }

    @PostMapping("/add")
    public Result add(@RequestBody VehicleInfo vehicleInfo, HttpSession session) {
        vehicleInfoService.add(vehicleInfo, session);
        return Result.success();
    }

    @DeleteMapping("/delete/{id}")
    public Result delete(@PathVariable Integer id, HttpSession session) {
        vehicleInfoService.deleteById(id, session);
        return Result.success();
    }

    @PutMapping("/update")
    public Result update(@RequestBody VehicleInfo vehicleInfo, HttpSession session) {
        vehicleInfoService.updateById(vehicleInfo, session);
        return Result.success();
    }

    @GetMapping("/selectById/{id}")
    public Result selectById(@PathVariable Integer id, HttpSession session) {
        VehicleInfo vehicleInfo = vehicleInfoService.selectById(id, session);
        return Result.success(vehicleInfo);
    }

    @GetMapping("/selectPage")
    public Result selectPage(@RequestParam(defaultValue = "1") Integer pageNum,
                             @RequestParam(defaultValue = "10") Integer pageSize,
                             VehicleInfo vehicleInfo,
                             HttpSession session) {
        PageInfo<VehicleInfo> pageInfo = vehicleInfoService.selectPage(pageNum, pageSize, vehicleInfo, session);
        return Result.success(pageInfo);
    }

    @GetMapping("/statisticsByTypeRisk")
    public Result statisticsByTypeRisk(HttpSession session) {
        List<Map<String, Object>> statistics = vehicleInfoService.statisticsByTypeRisk(session);
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByTypeFuel")
    public Result statisticsByTypeFuel(HttpSession session) {
        List<Map<String, Object>> statistics = vehicleInfoService.statisticsByTypeFuel(session);
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByYear")
    public Result statisticsByYear(HttpSession session) {
        List<Map<String, Object>> statistics = vehicleInfoService.statisticsByYear(session);
        return Result.success(statistics);
    }
}
