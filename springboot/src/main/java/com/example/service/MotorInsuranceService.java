package com.example.service;

import com.example.entity.MotorInsurance;
import com.example.mapper.MotorInsuranceMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.List;
import java.util.Map;

@Service
public class MotorInsuranceService {

    @Resource
    private MotorInsuranceMapper motorInsuranceMapper;

    public void add(MotorInsurance motorInsurance) {
        motorInsuranceMapper.insert(motorInsurance);
    }

    public void deleteById(Integer id) {
        motorInsuranceMapper.deleteById(id);
    }

    public void updateById(MotorInsurance motorInsurance) {
        motorInsuranceMapper.updateById(motorInsurance);
    }

    public MotorInsurance selectById(Integer id) {
        return motorInsuranceMapper.selectById(id);
    }

    public PageInfo<MotorInsurance> selectPage(Integer pageNum, Integer pageSize, MotorInsurance motorInsurance) {
        PageHelper.startPage(pageNum, pageSize);
        List<MotorInsurance> motorInsuranceList = motorInsuranceMapper.selectAll(motorInsurance);
        return PageInfo.of(motorInsuranceList);
    }

    public List<Map<String, Object>> statisticsByRiskType() {
        return motorInsuranceMapper.statisticsByRiskType();
    }

    public List<Map<String, Object>> statisticsByArea() {
        return motorInsuranceMapper.statisticsByArea();
    }

    public List<Map<String, Object>> statisticsByPayment() {
        return motorInsuranceMapper.statisticsByPayment();
    }

    public Map<String, Object> overallStatistics() {
        return motorInsuranceMapper.overallStatistics();
    }

    public List<Map<String, Object>> statisticsByFuelType() {
        return motorInsuranceMapper.statisticsByFuelType();
    }

    public List<Map<String, Object>> statisticsByMatriculationYear() {
        return motorInsuranceMapper.statisticsByMatriculationYear();
    }

    public List<Map<String, Object>> statisticsByDistributionChannel() {
        return motorInsuranceMapper.statisticsByDistributionChannel();
    }
}
