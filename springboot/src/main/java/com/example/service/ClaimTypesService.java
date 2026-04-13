package com.example.service;

import com.example.common.SessionUserUtil;
import com.example.entity.ClaimTypes;
import com.example.entity.MotorInsurance;
import com.example.exception.CustomException;
import com.example.mapper.ClaimTypesMapper;
import com.example.mapper.MotorInsuranceMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.util.List;
import java.util.Map;

@Service
public class ClaimTypesService {

    @Resource
    private ClaimTypesMapper claimTypesMapper;

    @Resource
    private MotorInsuranceMapper motorInsuranceMapper;

    public void add(ClaimTypes claimTypes) {
        if (claimTypes.getId() == null) {
            throw new CustomException("ID不能为空");
        }
        MotorInsurance motorInsurance = motorInsuranceMapper.selectById(claimTypes.getId());
        if (motorInsurance == null) {
            throw new CustomException("该ID在保单信息中不存在，请先新增对应保单记录");
        }
        if (claimTypesMapper.selectById(claimTypes.getId()) != null) {
            throw new CustomException("该ID的理赔记录已存在");
        }
        claimTypes.setTypeRisk(motorInsurance.getTypeRisk());
        claimTypes.setArea(motorInsurance.getArea());
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

    public List<Map<String, Object>> statisticsByRiskType() {
        return claimTypesMapper.statisticsByRiskType();
    }

    public List<Map<String, Object>> statisticsByArea() {
        return claimTypesMapper.statisticsByArea();
    }
}