package com.example.controller;

import com.example.common.Result;
import com.example.entity.ClaimTypes;
import com.example.service.ClaimTypesService;
import com.github.pagehelper.PageInfo;
import org.springframework.web.bind.annotation.*;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/claimTypes")
public class ClaimTypesController {

    @Resource
    private ClaimTypesService claimTypesService;

    @PostConstruct
    public void init() {
        System.out.println("ClaimTypesController initialized");
    }

    @PostMapping("/add")
    public Result add(@RequestBody ClaimTypes claimTypes, HttpSession session) {
        claimTypesService.add(claimTypes, session);
        return Result.success();
    }

    @DeleteMapping("/delete/{id}")
    public Result delete(@PathVariable Integer id, HttpSession session) {
        claimTypesService.deleteById(id, session);
        return Result.success();
    }

    @PutMapping("/update")
    public Result update(@RequestBody ClaimTypes claimTypes, HttpSession session) {
        claimTypesService.updateById(claimTypes, session);
        return Result.success();
    }

    @GetMapping("/selectById/{id}")
    public Result selectById(@PathVariable Integer id, HttpSession session) {
        ClaimTypes claimTypes = claimTypesService.selectById(id, session);
        return Result.success(claimTypes);
    }

    @GetMapping("/selectPage")
    public Result selectPage(@RequestParam(defaultValue = "1") Integer pageNum,
                             @RequestParam(defaultValue = "10") Integer pageSize,
                             ClaimTypes claimTypes,
                             HttpSession session) {
        PageInfo<ClaimTypes> pageInfo = claimTypesService.selectPage(pageNum, pageSize, claimTypes, session);
        return Result.success(pageInfo);
    }

    @GetMapping("/statisticsByRiskType")
    public Result statisticsByRiskType(HttpSession session) {
        List<Map<String, Object>> statistics = claimTypesService.statisticsByRiskType(session);
        return Result.success(statistics);
    }

    @GetMapping("/statisticsByArea")
    public Result statisticsByArea(HttpSession session) {
        List<Map<String, Object>> statistics = claimTypesService.statisticsByArea(session);
        return Result.success(statistics);
    }
}
