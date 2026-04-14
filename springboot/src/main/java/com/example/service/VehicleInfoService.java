package com.example.service;

import com.example.common.SessionUserUtil;
import com.example.entity.MotorInsurance;
import com.example.entity.VehicleInfo;
import com.example.exception.CustomException;
import com.example.mapper.MotorInsuranceMapper;
import com.example.mapper.VehicleInfoMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.util.List;
import java.util.Map;

@Service
public class VehicleInfoService {

    @Resource
    private VehicleInfoMapper vehicleInfoMapper;

    @Resource
    private MotorInsuranceMapper motorInsuranceMapper;

    private VehicleInfo requireAccessibleVehicleInfo(Integer id, HttpSession session) {
        VehicleInfo vehicleInfo = vehicleInfoMapper.selectById(id);
        if (vehicleInfo == null) {
            throw new CustomException("车辆信息不存在");
        }
        SessionUserUtil.requireOwnerOrAdmin(vehicleInfo.getCreatorEmployeeNo(), session);
        return vehicleInfo;
    }

    public void add(VehicleInfo vehicleInfo, HttpSession session) {
        SessionUserUtil.requireLogin(session);
        if (vehicleInfo.getId() == null) {
            throw new CustomException("保单编号不能为空");
        }
        MotorInsurance motorInsurance = motorInsuranceMapper.selectById(vehicleInfo.getId());
        if (motorInsurance == null) {
            throw new CustomException("该保单编号在保单信息中不存在，请先新增对应保单记录");
        }
        SessionUserUtil.requireOwnerOrAdmin(motorInsurance.getCreatorEmployeeNo(), session);
        if (vehicleInfoMapper.selectById(vehicleInfo.getId()) != null) {
            throw new CustomException("该保单编号的车辆信息已存在");
        }
        vehicleInfo.setTypeRisk(motorInsurance.getTypeRisk());
        vehicleInfo.setCreatorEmployeeNo(motorInsurance.getCreatorEmployeeNo());
        vehicleInfoMapper.insert(vehicleInfo);
    }

    public void deleteById(Integer id, HttpSession session) {
        requireAccessibleVehicleInfo(id, session);
        vehicleInfoMapper.deleteById(id);
    }

    public void updateById(VehicleInfo vehicleInfo, HttpSession session) {
        VehicleInfo existing = requireAccessibleVehicleInfo(vehicleInfo.getId(), session);
        vehicleInfo.setCreatorEmployeeNo(existing.getCreatorEmployeeNo());
        vehicleInfoMapper.updateById(vehicleInfo);
    }

    public VehicleInfo selectById(Integer id, HttpSession session) {
        return requireAccessibleVehicleInfo(id, session);
    }

    public PageInfo<VehicleInfo> selectPage(Integer pageNum, Integer pageSize, VehicleInfo vehicleInfo, HttpSession session) {
        SessionUserUtil.requireLogin(session);
        if (vehicleInfo == null) {
            vehicleInfo = new VehicleInfo();
        }
        String scopedEmployeeNo = SessionUserUtil.resolveDataScopeEmployeeNo(session);
        if (scopedEmployeeNo != null) {
            vehicleInfo.setCreatorEmployeeNo(scopedEmployeeNo);
        }
        PageHelper.startPage(pageNum, pageSize);
        List<VehicleInfo> vehicleInfoList = vehicleInfoMapper.selectAll(vehicleInfo);
        return PageInfo.of(vehicleInfoList);
    }

    public List<Map<String, Object>> statisticsByTypeRisk(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return vehicleInfoMapper.statisticsByTypeRisk(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }

    public List<Map<String, Object>> statisticsByTypeFuel(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return vehicleInfoMapper.statisticsByTypeFuel(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }

    public List<Map<String, Object>> statisticsByYear(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return vehicleInfoMapper.statisticsByYear(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }
}