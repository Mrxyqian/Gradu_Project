package com.example.service;

import cn.hutool.crypto.SecureUtil;
import com.example.entity.User;
import com.example.exception.CustomException;
import com.example.mapper.UserMapper;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

@Service
public class UserService {

    private static final String REGISTER_CODE = "add123";
    private static final String DEFAULT_ADMIN_EMPLOYEE_NO = "000001";
    private static final String DEFAULT_ADMIN_PASSWORD = "admin123";
    private static final DateTimeFormatter TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Resource
    private UserMapper userMapper;

    @PostConstruct
    public void init() {
        userMapper.createTableIfNotExists();
        User admin = new User();
        admin.setEmployeeNo(DEFAULT_ADMIN_EMPLOYEE_NO);
        admin.setName("管理员");
        admin.setPassword(encodePassword(DEFAULT_ADMIN_PASSWORD));
        admin.setRole("ADMIN");
        admin.setCreateTime(now());
        userMapper.initAdmin(admin);
    }

    public Map<String, Object> register(User user) {
        validateEmployeeNo(user.getEmployeeNo());
        validateName(user.getName());
        validatePassword(user.getPassword());

        if (!REGISTER_CODE.equals(user.getRegisterCode())) {
            throw new CustomException("注册密码不正确");
        }
        if (userMapper.selectByEmployeeNo(user.getEmployeeNo()) != null) {
            throw new CustomException("该工号已注册");
        }

        User newUser = new User();
        newUser.setEmployeeNo(user.getEmployeeNo());
        newUser.setName(user.getName());
        newUser.setPassword(encodePassword(user.getPassword()));
        newUser.setRole("USER");
        newUser.setCreateTime(now());
        userMapper.insert(newUser);

        return login(user);
    }

    public Map<String, Object> login(User user) {
        validateEmployeeNo(user.getEmployeeNo());
        validatePassword(user.getPassword());

        User dbUser = userMapper.selectByEmployeeNo(user.getEmployeeNo());
        if (dbUser == null) {
            throw new CustomException("工号或密码错误");
        }
        if (!encodePassword(user.getPassword()).equals(dbUser.getPassword())) {
            throw new CustomException("工号或密码错误");
        }

        String previousLoginTime = dbUser.getLastLoginTime();
        dbUser.setLastLoginTime(now());
        userMapper.updateLastLoginTime(dbUser);

        Map<String, Object> result = new HashMap<>();
        result.put("user", buildSafeUser(dbUser));
        result.put("loginMessage", previousLoginTime == null || previousLoginTime.trim().isEmpty()
                ? "欢迎首次登录"
                : "您上次登录时间为：" + previousLoginTime);
        return result;
    }

    private User buildSafeUser(User user) {
        User safeUser = new User();
        safeUser.setId(user.getId());
        safeUser.setEmployeeNo(user.getEmployeeNo());
        safeUser.setName(user.getName());
        safeUser.setRole(user.getRole());
        safeUser.setLastLoginTime(user.getLastLoginTime());
        safeUser.setCreateTime(user.getCreateTime());
        return safeUser;
    }

    private void validateEmployeeNo(String employeeNo) {
        if (employeeNo == null || !employeeNo.matches("\\d{6}")) {
            throw new CustomException("请输入6位数字工号");
        }
    }

    private void validateName(String name) {
        if (name == null || name.trim().isEmpty()) {
            throw new CustomException("姓名不能为空");
        }
    }

    private void validatePassword(String password) {
        if (password == null || password.trim().isEmpty()) {
            throw new CustomException("密码不能为空");
        }
    }

    private String encodePassword(String password) {
        return SecureUtil.md5(password);
    }

    private String now() {
        return LocalDateTime.now().format(TIME_FORMATTER);
    }
}
