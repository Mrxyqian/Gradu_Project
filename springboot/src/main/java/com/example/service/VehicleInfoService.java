package com.example.service;

import com.example.common.SessionUserUtil;
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

    public void add(VehicleInfo vehicleInfo) {
        if (vehicleInfo.getId() == null) {
            throw new CustomException("ID不能为空");
        }
        if (motorInsuranceMapper.selectById(vehicleInfo.getId()) == null) {
            throw new CustomException("该ID在保单信息中不存在，请先新增对应保单记录");
        }
        if (vehicleInfoMapper.selectById(vehicleInfo.getId()) != null) {
            throw new CustomException("该ID的车辆信息已存在");
        }
        vehicleInfoMapper.insert(vehicleInfo);
    }

    public void deleteById(Integer id, HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        vehicleInfoMapper.deleteById(id);
    }

    public void updateById(VehicleInfo vehicleInfo) {
        vehicleInfoMapper.updateById(vehicleInfo);
    }

    public VehicleInfo selectById(Integer id) {
        return vehicleInfoMapper.selectById(id);
    }

    public PageInfo<VehicleInfo> selectPage(Integer pageNum, Integer pageSize, VehicleInfo vehicleInfo) {
        PageHelper.startPage(pageNum, pageSize);
        List<VehicleInfo> vehicleInfoList = vehicleInfoMapper.selectAll(vehicleInfo);
        return PageInfo.of(vehicleInfoList);
    }

    public List<Map<String, Object>> statisticsByTypeRisk() {
        return vehicleInfoMapper.statisticsByTypeRisk();
    }

    public List<Map<String, Object>> statisticsByTypeFuel() {
        return vehicleInfoMapper.statisticsByTypeFuel();
    }

    public List<Map<String, Object>> statisticsByYear() {
        return vehicleInfoMapper.statisticsByYear();
    }
}
