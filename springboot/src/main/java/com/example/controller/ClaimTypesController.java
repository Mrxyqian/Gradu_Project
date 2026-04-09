package com.example.controller;

import com.example.common.Result;
import com.example.entity.ClaimTypes;
import com.example.service.ClaimTypesService;
import com.github.pagehelper.PageInfo;
import org.springframework.web.bind.annotation.*;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/claimTypes")
public class ClaimTypesController {

    @Resource
    private ClaimTypesService claimTypesService;

    @PostConstruct
    public void init() {
        System.out.println("✅ ClaimTypesController 初始化成功");
    }

    @PostMapping("/add")
    public Result add(@RequestBody ClaimTypes claimTypes) {
        claimTypesService.add(claimTypes);
        return Result.success();
    }

    @DeleteMapping("/delete/{id}")
    public Result delete(@PathVariable Integer id, HttpSession session) {
        claimTypesService.deleteById(id, session);
        return Result.success();
    }

    @PutMapping("/update")
    public Result update(@RequestBody ClaimTypes claimTypes) {
        claimTypesService.updateById(claimTypes);
        return Result.success();
    }

    @GetMapping("/selectById/{id}")
    public Result selectById(@PathVariable Integer id) {
        ClaimTypes claimTypes = claimTypesService.selectById(id);
        return Result.success(claimTypes);
    }

    @GetMapping("/selectPage")
    public Result selectPage(@RequestParam(defaultValue = "1") Integer pageNum,
                            @RequestParam(defaultValue = "10") Integer pageSize,
                            ClaimTypes claimTypes) {
        PageInfo<ClaimTypes> pageInfo = claimTypesService.selectPage(pageNum, pageSize, claimTypes);
        return Result.success(pageInfo);
    }

    @GetMapping("/statisticsByClaimType")
    public Result statisticsByClaimType() {
        List<Map<String, Object>> statistics = claimTypesService.statisticsByClaimType();
        return Result.success(statistics);
    }

    @GetMapping("/overallClaimsStatistics")
    public Result overallClaimsStatistics() {
        Map<String, Object> statistics = claimTypesService.overallClaimsStatistics();
        return Result.success(statistics);
    }

    @GetMapping("/claimsCostPercentage")
    public Result claimsCostPercentage() {
        List<Map<String, Object>> statistics = claimTypesService.claimsCostPercentage();
        return Result.success(statistics);
    }

    @GetMapping("/selectByClaimsType")
    public Result selectByClaimsType(@RequestParam String claimsType) {
        List<ClaimTypes> claimTypesList = claimTypesService.selectByClaimsType(claimsType);
        return Result.success(claimTypesList);
    }

    @GetMapping("/selectByMinCost")
    public Result selectByMinCost(@RequestParam BigDecimal minCost) {
        List<ClaimTypes> claimTypesList = claimTypesService.selectByMinCost(minCost);
        return Result.success(claimTypesList);
    }
}
