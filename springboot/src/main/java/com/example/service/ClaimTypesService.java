package com.example.service;

import com.example.common.SessionUserUtil;
import com.example.entity.ClaimTypes;
import com.example.mapper.ClaimTypesMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Service
public class ClaimTypesService {

    @Resource
    private ClaimTypesMapper claimTypesMapper;

    public void add(ClaimTypes claimTypes) {
        claimTypesMapper.insert(claimTypes);
    }

    public void deleteById(Integer id, HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        claimTypesMapper.deleteById(id);
    }

    public void updateById(ClaimTypes claimTypes) {
        claimTypesMapper.updateById(claimTypes);
    }

    public ClaimTypes selectById(Integer id) {
        return claimTypesMapper.selectById(id);
    }

    public PageInfo<ClaimTypes> selectPage(Integer pageNum, Integer pageSize, ClaimTypes claimTypes) {
        PageHelper.startPage(pageNum, pageSize);
        List<ClaimTypes> claimTypesList = claimTypesMapper.selectAll(claimTypes);
        return PageInfo.of(claimTypesList);
    }

    public List<Map<String, Object>> statisticsByClaimType() {
        return claimTypesMapper.statisticsByClaimType();
    }

    public Map<String, Object> overallClaimsStatistics() {
        return claimTypesMapper.overallClaimsStatistics();
    }

    public List<Map<String, Object>> claimsCostPercentage() {
        return claimTypesMapper.claimsCostPercentage();
    }

    public List<ClaimTypes> selectByClaimsType(String claimsType) {
        return claimTypesMapper.selectByClaimsType(claimsType);
    }

    public List<ClaimTypes> selectByMinCost(BigDecimal minCost) {
        return claimTypesMapper.selectByMinCost(minCost);
    }
}
