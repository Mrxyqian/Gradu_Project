package com.example.service;

import com.example.common.DateUtil;
import com.example.common.SessionUserUtil;
import com.example.entity.MotorInsurance;
import com.example.entity.User;
import com.example.exception.CustomException;
import com.example.mapper.MotorInsuranceMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.List;
import java.util.Map;

@Service
public class MotorInsuranceService {

    @Resource
    private MotorInsuranceMapper motorInsuranceMapper;

    @Resource
    private JdbcTemplate jdbcTemplate;

    private void validateRequiredFields(MotorInsurance motorInsurance, boolean requirePolicyId) {
        if (requirePolicyId && motorInsurance.getId() == null) {
            throw new CustomException("保单编号不能为空");
        }
        if (isBlank(motorInsurance.getDateStartContract())) {
            throw new CustomException("合同开始日期不能为空");
        }
        if (isBlank(motorInsurance.getDateLastRenewal())) {
            throw new CustomException("最后续保日期不能为空");
        }
        if (isBlank(motorInsurance.getDateNextRenewal())) {
            throw new CustomException("下次续保日期不能为空");
        }
        if (isBlank(motorInsurance.getDateBirth())) {
            throw new CustomException("被保人出生日期不能为空");
        }
        if (isBlank(motorInsurance.getDateDrivingLicence())) {
            throw new CustomException("驾照签发日期不能为空");
        }
        if (motorInsurance.getDistributionChannel() == null) {
            throw new CustomException("分销渠道不能为空");
        }
        if (motorInsurance.getSeniority() == null) {
            throw new CustomException("合作年数不能为空");
        }
        if (motorInsurance.getPoliciesInForce() == null) {
            throw new CustomException("有效保单数不能为空");
        }
        if (motorInsurance.getMaxPolicies() == null) {
            throw new CustomException("历史最高保单数不能为空");
        }
        if (motorInsurance.getMaxProducts() == null) {
            throw new CustomException("历史最高产品数不能为空");
        }
        if (motorInsurance.getLapse() == null) {
            throw new CustomException("失效保单数不能为空");
        }
        if (motorInsurance.getPayment() == null) {
            throw new CustomException("缴费方式不能为空");
        }
        if (motorInsurance.getPremium() == null) {
            throw new CustomException("净保费不能为空");
        }
        if (motorInsurance.getTypeRisk() == null) {
            throw new CustomException("风险类型不能为空");
        }
        if (motorInsurance.getArea() == null) {
            throw new CustomException("地区不能为空");
        }
        if (motorInsurance.getSecondDriver() == null) {
            throw new CustomException("第二驾驶员不能为空");
        }
    }

    private void normalizeOptionalFields(MotorInsurance motorInsurance) {
        if (isBlank(motorInsurance.getDateLapse())) {
            motorInsurance.setDateLapse(null);
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

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

    private void convertQueryDatesToDBFormat(MotorInsurance motorInsurance) {
        if (motorInsurance == null) {
            return;
        }
        try {
            if (!isBlank(motorInsurance.getDateStartContract())) {
                motorInsurance.setDateStartContract(DateUtil.convertYYYYMMDDToDDMMYYYYQueryPattern(motorInsurance.getDateStartContract()));
            }
            if (!isBlank(motorInsurance.getDateLastRenewal())) {
                motorInsurance.setDateLastRenewal(DateUtil.convertYYYYMMDDToDDMMYYYYQueryPattern(motorInsurance.getDateLastRenewal()));
            }
            if (!isBlank(motorInsurance.getDateNextRenewal())) {
                motorInsurance.setDateNextRenewal(DateUtil.convertYYYYMMDDToDDMMYYYYQueryPattern(motorInsurance.getDateNextRenewal()));
            }
            if (!isBlank(motorInsurance.getDateBirth())) {
                motorInsurance.setDateBirth(DateUtil.convertYYYYMMDDToDDMMYYYYQueryPattern(motorInsurance.getDateBirth()));
            }
            if (!isBlank(motorInsurance.getDateDrivingLicence())) {
                motorInsurance.setDateDrivingLicence(DateUtil.convertYYYYMMDDToDDMMYYYYQueryPattern(motorInsurance.getDateDrivingLicence()));
            }
            if (!isBlank(motorInsurance.getDateLapse())) {
                motorInsurance.setDateLapse(DateUtil.convertYYYYMMDDToDDMMYYYYQueryPattern(motorInsurance.getDateLapse()));
            }
        } catch (IllegalArgumentException e) {
            throw new CustomException(e.getMessage());
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

    private Integer allocateNextPolicyId() {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(connection -> {
            PreparedStatement preparedStatement = connection.prepareStatement(
                    "INSERT INTO motor_insurance_id_sequence VALUES ()",
                    Statement.RETURN_GENERATED_KEYS
            );
            return preparedStatement;
        }, keyHolder);
        Number generatedKey = keyHolder.getKey();
        if (generatedKey == null) {
            throw new CustomException("系统分配保单编号失败，请稍后重试");
        }
        return generatedKey.intValue();
    }

    private MotorInsurance requireAccessibleMotorInsurance(Integer id, HttpSession session) {
        MotorInsurance motorInsurance = motorInsuranceMapper.selectById(id);
        if (motorInsurance == null) {
            throw new CustomException("保单信息不存在");
        }
        SessionUserUtil.requireOwnerOrAdmin(motorInsurance.getCreatorEmployeeNo(), session);
        return motorInsurance;
    }

    @Transactional
    public MotorInsurance add(MotorInsurance motorInsurance, HttpSession session) {
        validateRequiredFields(motorInsurance, false);
        User currentUser = SessionUserUtil.requireLogin(session);
        Integer nextPolicyId = allocateNextPolicyId();
        normalizeOptionalFields(motorInsurance);
        convertDatesToDBFormat(motorInsurance);
        motorInsurance.setId(nextPolicyId);
        motorInsurance.setCreatorEmployeeNo(currentUser.getEmployeeNo());
        motorInsuranceMapper.insert(motorInsurance);
        return selectById(nextPolicyId, session);
    }

    public void deleteById(Integer id, HttpSession session) {
        requireAccessibleMotorInsurance(id, session);
        motorInsuranceMapper.deleteById(id);
    }

    public void updateById(MotorInsurance motorInsurance, HttpSession session) {
        validateRequiredFields(motorInsurance, true);
        MotorInsurance existing = requireAccessibleMotorInsurance(motorInsurance.getId(), session);
        normalizeOptionalFields(motorInsurance);
        convertDatesToDBFormat(motorInsurance);
        motorInsurance.setCreatorEmployeeNo(existing.getCreatorEmployeeNo());
        motorInsuranceMapper.updateById(motorInsurance);
    }

    public MotorInsurance selectById(Integer id, HttpSession session) {
        MotorInsurance motorInsurance = requireAccessibleMotorInsurance(id, session);
        convertDatesToDisplayFormat(motorInsurance);
        return motorInsurance;
    }

    public List<MotorInsurance> selectByIds(List<Integer> ids) {
        List<MotorInsurance> motorInsuranceList = motorInsuranceMapper.selectByIds(ids);
        for (MotorInsurance motorInsurance : motorInsuranceList) {
            convertDatesToDisplayFormat(motorInsurance);
        }
        return motorInsuranceList;
    }

    public PageInfo<MotorInsurance> selectPage(Integer pageNum, Integer pageSize, MotorInsurance motorInsurance, HttpSession session) {
        SessionUserUtil.requireLogin(session);
        if (motorInsurance == null) {
            motorInsurance = new MotorInsurance();
        }
        convertQueryDatesToDBFormat(motorInsurance);
        String scopedEmployeeNo = SessionUserUtil.resolveDataScopeEmployeeNo(session);
        if (scopedEmployeeNo != null) {
            motorInsurance.setCreatorEmployeeNo(scopedEmployeeNo);
        }
        PageHelper.startPage(pageNum, pageSize);
        List<MotorInsurance> motorInsuranceList = motorInsuranceMapper.selectAll(motorInsurance);
        for (MotorInsurance mi : motorInsuranceList) {
            convertDatesToDisplayFormat(mi);
        }
        return PageInfo.of(motorInsuranceList);
    }

    public List<Map<String, Object>> statisticsByRiskType(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return motorInsuranceMapper.statisticsByRiskType(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }

    public List<Map<String, Object>> statisticsByArea(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return motorInsuranceMapper.statisticsByArea(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }

    public List<Map<String, Object>> statisticsByPayment(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return motorInsuranceMapper.statisticsByPayment(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }

    public Map<String, Object> overallStatistics(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return motorInsuranceMapper.overallStatistics(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }

    public List<Map<String, Object>> statisticsByFuelType(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return motorInsuranceMapper.statisticsByFuelType(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }

    public List<Map<String, Object>> statisticsByMatriculationYear(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return motorInsuranceMapper.statisticsByMatriculationYear(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }

    public List<Map<String, Object>> statisticsByDistributionChannel(HttpSession session) {
        SessionUserUtil.requireLogin(session);
        return motorInsuranceMapper.statisticsByDistributionChannel(SessionUserUtil.resolveDataScopeEmployeeNo(session));
    }
}
