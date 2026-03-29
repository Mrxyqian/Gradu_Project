package com.example.service;

import com.example.entity.VehicleInfo;
import com.example.mapper.VehicleInfoMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.List;
import java.util.Map;

@Service
public class VehicleInfoService {

    @Resource
    private VehicleInfoMapper vehicleInfoMapper;

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
