package com.example.service;

import cn.hutool.crypto.SecureUtil;
import com.example.entity.User;
import com.example.exception.CustomException;
import com.example.mapper.UserMapper;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class UserService {

    public static final String CURRENT_USER = "currentUser";
    private static final String REGISTER_CODE = "add123";
    private static final String DEFAULT_ADMIN_EMPLOYEE_NO = "000001";
    private static final String DEFAULT_ADMIN_PASSWORD = "admin123";
    private static final String ROLE_ADMIN = "ADMIN";
    private static final String ROLE_USER = "USER";
    private static final DateTimeFormatter TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Resource
    private UserMapper userMapper;

    @PostConstruct
    public void init() {
        userMapper.createTableIfNotExists();
        User admin = new User();
        admin.setEmployeeNo(DEFAULT_ADMIN_EMPLOYEE_NO);
        admin.setName("管理员");
        admin.setName("管理员");
        admin.setPassword(encodePassword(DEFAULT_ADMIN_PASSWORD));
        admin.setRole(ROLE_ADMIN);
        admin.setCreateTime(now());
        userMapper.initAdmin(admin);
    }

    public Map<String, Object> register(User user, HttpSession session) {
        validateEmployeeNo(user.getEmployeeNo());
        validateName(user.getName());
        validatePassword(user.getPassword());
        validateRole(user.getRole());

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
        newUser.setRole(user.getRole());
        newUser.setCreateTime(now());
        userMapper.insert(newUser);

        return login(user, session);
    }

    public Map<String, Object> login(User user, HttpSession session) {
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
        User safeUser = buildSafeUser(dbUser);
        session.setAttribute(CURRENT_USER, safeUser);
        result.put("user", safeUser);
        result.put("loginMessage", previousLoginTime == null || previousLoginTime.trim().isEmpty()
                ? "欢迎首次登录"
                : "您上次登录时间为：" + previousLoginTime);
        return result;
    }

    public void logout(HttpSession session) {
        session.invalidate();
    }

    public List<User> selectAll(HttpSession session) {
        requireAdmin(session);
        return userMapper.selectAll().stream().map(this::buildSafeUser).collect(Collectors.toList());
    }

    public void addUser(User user, HttpSession session) {
        requireAdmin(session);
        validateEmployeeNo(user.getEmployeeNo());
        validateName(user.getName());
        validatePassword(user.getPassword());
        validateRole(user.getRole());

        if (userMapper.selectByEmployeeNo(user.getEmployeeNo()) != null) {
            throw new CustomException("该工号已存在");
        }

        User newUser = new User();
        newUser.setEmployeeNo(user.getEmployeeNo());
        newUser.setName(user.getName());
        newUser.setPassword(encodePassword(user.getPassword()));
        newUser.setRole(user.getRole());
        newUser.setCreateTime(now());
        userMapper.insert(newUser);
    }

    public void updateUser(User user, HttpSession session) {
        requireAdmin(session);
        User dbUser = userMapper.selectById(user.getId());
        if (dbUser == null) {
            throw new CustomException("用户不存在");
        }
        if (ROLE_ADMIN.equals(dbUser.getRole())) {
            throw new CustomException("不能修改管理员账号");
        }

        validateName(user.getName());
        validateRole(user.getRole());

        User updateUser = new User();
        updateUser.setId(dbUser.getId());
        updateUser.setName(user.getName());
        updateUser.setRole(user.getRole());
        updateUser.setPassword((user.getPassword() == null || user.getPassword().trim().isEmpty())
                ? dbUser.getPassword()
                : encodePassword(user.getPassword()));
        userMapper.updateById(updateUser);
    }

    public void deleteUser(Integer id, HttpSession session) {
        User currentUser = requireAdmin(session);
        User dbUser = userMapper.selectById(id);
        if (dbUser == null) {
            throw new CustomException("用户不存在");
        }
        if (currentUser.getId().equals(id)) {
            throw new CustomException("不允许删除当前登录用户");
        }
        if (ROLE_ADMIN.equals(dbUser.getRole())) {
            Integer adminCount = userMapper.countByRole(ROLE_ADMIN);
            if (adminCount != null && adminCount <= 1) {
                throw new CustomException("系统中至少需要保留一个管理员");
            }
            throw new CustomException("不能删除管理员账号");
        }
        userMapper.deleteById(id);
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

    private void validateRole(String role) {
        if (!ROLE_ADMIN.equals(role) && !ROLE_USER.equals(role)) {
            throw new CustomException("角色参数不正确");
        }
    }

    private User requireAdmin(HttpSession session) {
        Object currentUserObj = session.getAttribute(CURRENT_USER);
        if (!(currentUserObj instanceof User)) {
            throw new CustomException("请先登录");
        }
        User currentUser = (User) currentUserObj;
        if (!ROLE_ADMIN.equals(currentUser.getRole())) {
            throw new CustomException("无权限操作该功能");
        }
        return currentUser;
    }

    private String encodePassword(String password) {
        return SecureUtil.md5(password);
    }

    private String now() {
        return LocalDateTime.now().format(TIME_FORMATTER);
    }
}
