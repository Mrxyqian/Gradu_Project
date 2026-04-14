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

    private ClaimTypes requireAccessibleClaimRecord(Integer id, HttpSession session) {
        ClaimTypes claimTypes = claimTypesMapper.selectById(id);
        if (claimTypes == null) {
            throw new CustomException("理赔记录不存在");
        }
        SessionUserUtil.requireOwnerOrAdmin(claimTypes.getCreatorEmployeeNo(), session);
        return claimTypes;
    }

    public void add(ClaimTypes claimTypes, HttpSession session) {
        SessionUserUtil.requireLogin(session);
        if (claimTypes.getId() == null) {
            throw new CustomException("保单编号不能为空");
        }
        MotorInsurance motorInsurance = motorInsuranceMapper.selectById(claimTypes.getId());
        if (motorInsurance == null) {
            throw new CustomException("该保单编号在保单信息中不存在，请先新增对应保单记录");
        }
        SessionUserUtil.requireOwnerOrAdmin(motorInsurance.getCreatorEmployeeNo(), session);
        if (claimTypesMapper.selectById(claimTypes.getId()) != null) {
            throw new CustomException("该保单编号的理赔记录已存在");
        }
        claimTypes.setTypeRisk(motorInsurance.getTypeRisk());
        claimTypes.setArea(motorInsurance.getArea());
        claimTypes.setCreatorEmployeeNo(motorInsurance.getCreatorEmployeeNo());
        claimTypesMapper.insert(claimTypes);
    }

    public void deleteById(Integer id, HttpSession session) {
        requireAccessibleClaimRecord(id, session);
        claimTypesMapper.deleteById(id);
    }

    public void updateById(ClaimTypes claimTypes, HttpSession session) {
        ClaimTypes existing = requireAccessibleClaimRecord(claimTypes.getId(), session);
        claimTypes.setCreatorEmployeeNo(existing.getCreatorEmployeeNo());
        claimTypesMapper.updateById(claimTypes);
    }

    public ClaimTypes selectById(Integer id, HttpSession session) {
        return requireAccessibleClaimRecord(id, session);
    }

    public PageInfo<ClaimTypes> selectPage(Integer pageNum, Integer pageSize, ClaimTypes claimTypes, HttpSession session) {
        SessionUserUtil.requireLogin(session);
        if (claimTypes == null) {
            claimTypes = new ClaimTypes();
        }
        String scopedEmployeeNo = SessionUserUtil.resolveDataScopeEmployeeNo(session);
        if (scopedEmployeeNo != null) {
            claimTypes.setCreatorEmployeeNo(scopedEmployeeNo);
        }
        PageHelper.startPage(pageNum, pageSize);
        List<ClaimTypes> claimTypesList = claimTypesMapper.selectAll(claimTypes);
        return PageInfo.of(claimTypesList);
    }

    public List<Map<String, Object>> statisticsByRiskType(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return claimTypesMapper.statisticsByRiskType(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }

    public List<Map<String, Object>> statisticsByArea(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return claimTypesMapper.statisticsByArea(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }
}