package com.example.service;

import com.example.common.DateUtil;
import com.example.common.SessionUserUtil;
import com.example.entity.MotorInsurance;
import com.example.mapper.MotorInsuranceMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.util.List;
import java.util.Map;

@Service
public class MotorInsuranceService {

    @Resource
    private MotorInsuranceMapper motorInsuranceMapper;

    private void convertDatesToDBFormat(MotorInsurance motorInsurance) {
        if (motorInsurance.getDateStartContract() != null) {
            motorInsurance.setDateStartContract(DateUtil.convertYYYYMMDDToDDMMYYYY(motorInsurance.getDateStartContract()));
        }
        if (motorInsurance.getDateLastRenewal() != null) {
            motorInsurance.setDateLastRenewal(DateUtil.convertYYYYMMDDToDDMMYYYY(motorInsurance.getDateLastRenewal()));
        }
        if (motorInsurance.getDateNextRenewal() != null) {
            motorInsurance.setDateNextRenewal(DateUtil.convertYYYYMMDDToDDMMYYYY(motorInsurance.getDateNextRenewal()));
        }
        if (motorInsurance.getDateBirth() != null) {
            motorInsurance.setDateBirth(DateUtil.convertYYYYMMDDToDDMMYYYY(motorInsurance.getDateBirth()));
        }
        if (motorInsurance.getDateDrivingLicence() != null) {
            motorInsurance.setDateDrivingLicence(DateUtil.convertYYYYMMDDToDDMMYYYY(motorInsurance.getDateDrivingLicence()));
        }
        if (motorInsurance.getDateLapse() != null) {
            motorInsurance.setDateLapse(DateUtil.convertYYYYMMDDToDDMMYYYY(motorInsurance.getDateLapse()));
        }
    }

    private void convertDatesToDisplayFormat(MotorInsurance motorInsurance) {
        if (motorInsurance.getDateStartContract() != null) {
            motorInsurance.setDateStartContract(DateUtil.convertDDMMYYYYToYYYYMMDD(motorInsurance.getDateStartContract()));
        }
        if (motorInsurance.getDateLastRenewal() != null) {
            motorInsurance.setDateLastRenewal(DateUtil.convertDDMMYYYYToYYYYMMDD(motorInsurance.getDateLastRenewal()));
        }
        if (motorInsurance.getDateNextRenewal() != null) {
            motorInsurance.setDateNextRenewal(DateUtil.convertDDMMYYYYToYYYYMMDD(motorInsurance.getDateNextRenewal()));
        }
        if (motorInsurance.getDateBirth() != null) {
            motorInsurance.setDateBirth(DateUtil.convertDDMMYYYYToYYYYMMDD(motorInsurance.getDateBirth()));
        }
        if (motorInsurance.getDateDrivingLicence() != null) {
            motorInsurance.setDateDrivingLicence(DateUtil.convertDDMMYYYYToYYYYMMDD(motorInsurance.getDateDrivingLicence()));
        }
        if (motorInsurance.getDateLapse() != null) {
            motorInsurance.setDateLapse(DateUtil.convertDDMMYYYYToYYYYMMDD(motorInsurance.getDateLapse()));
        }
    }

    public void add(MotorInsurance motorInsurance) {
        convertDatesToDBFormat(motorInsurance);
        motorInsuranceMapper.insert(motorInsurance);
    }

    public void deleteById(Integer id, HttpSession session) {
        SessionUserUtil.requireAdmin(session);
        motorInsuranceMapper.deleteById(id);
    }

    public void updateById(MotorInsurance motorInsurance) {
        convertDatesToDBFormat(motorInsurance);
        motorInsuranceMapper.updateById(motorInsurance);
    }

    public MotorInsurance selectById(Integer id) {
        MotorInsurance motorInsurance = motorInsuranceMapper.selectById(id);
        if (motorInsurance != null) {
            convertDatesToDisplayFormat(motorInsurance);
        }
        return motorInsurance;
    }

    public List<MotorInsurance> selectByIds(List<Integer> ids) {
        List<MotorInsurance> motorInsuranceList = motorInsuranceMapper.selectByIds(ids);
        for (MotorInsurance motorInsurance : motorInsuranceList) {
            convertDatesToDisplayFormat(motorInsurance);
        }
        return motorInsuranceList;
    }

    public PageInfo<MotorInsurance> selectPage(Integer pageNum, Integer pageSize, MotorInsurance motorInsurance) {
        PageHelper.startPage(pageNum, pageSize);
        List<MotorInsurance> motorInsuranceList = motorInsuranceMapper.selectAll(motorInsurance);
        for (MotorInsurance mi : motorInsuranceList) {
            convertDatesToDisplayFormat(mi);
        }
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
