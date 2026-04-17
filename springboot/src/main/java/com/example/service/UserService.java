package com.example.service;

import cn.hutool.crypto.SecureUtil;
import com.example.entity.User;
import com.example.entity.UserHomeShortcutRequest;
import com.example.exception.CustomException;
import com.example.mapper.UserMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import javax.servlet.http.HttpSession;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class UserService {

    public static final String CURRENT_USER = "currentUser";
    private static final String ADMIN_REGISTER_CODE = "add123";
    private static final String USER_REGISTER_CODE = "add";
    private static final String DEFAULT_ADMIN_EMPLOYEE_NO = "000001";
    private static final String DEFAULT_ADMIN_PASSWORD = "admin123";
    private static final String ROLE_ADMIN = "ADMIN";
    private static final String ROLE_USER = "USER";
    private static final int MAX_HOME_SHORTCUTS = 4;
    private static final DateTimeFormatter TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final List<String> USER_ALLOWED_SHORTCUTS = Arrays.asList(
            "/motorInsurance",
            "/motorInsuranceStatistics",
            "/claimTypes",
            "/claimStatistics",
            "/vehicleInfo",
            "/predictionManage",
            "/predictionStatistics"
    );
    private static final List<String> ADMIN_ONLY_SHORTCUTS = Arrays.asList(
            "/modelTraining",
            "/userManage"
    );

    @Resource
    private UserMapper userMapper;

    @Resource
    private JdbcTemplate jdbcTemplate;

    @PostConstruct
    public void init() {
        userMapper.createTableIfNotExists();
        Integer shortcutColumnCount = userMapper.countHomeShortcutsColumn();
        if (shortcutColumnCount == null || shortcutColumnCount == 0) {
            userMapper.addHomeShortcutsColumn();
        }
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

        validateRegisterCode(user.getRole(), user.getRegisterCode());
        if (userMapper.selectByEmployeeNo(user.getEmployeeNo()) != null) {
            throw new CustomException("\u8be5\u7528\u6237\u5df2\u5b58\u5728");
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
        updateUser.setHomeShortcuts(joinShortcutPaths(sanitizeShortcutPaths(user.getRole(), parseShortcutPaths(dbUser.getHomeShortcuts()))));
        updateUser.setPassword((user.getPassword() == null || user.getPassword().trim().isEmpty())
                ? dbUser.getPassword()
                : encodePassword(user.getPassword()));
        userMapper.updateById(updateUser);
    }

    public Map<String, Object> getHomeShortcuts(HttpSession session) {
        User currentUser = requireLogin(session);
        User dbUser = userMapper.selectById(currentUser.getId());
        if (dbUser == null) {
            throw new CustomException("用户不存在");
        }

        List<String> selectedPaths = sanitizeShortcutPaths(dbUser.getRole(), parseShortcutPaths(dbUser.getHomeShortcuts()));
        String normalizedValue = joinShortcutPaths(selectedPaths);
        if (!normalizedValue.equals(dbUser.getHomeShortcuts() == null ? "" : dbUser.getHomeShortcuts())) {
            dbUser.setHomeShortcuts(normalizedValue);
            userMapper.updateHomeShortcuts(dbUser);
        }

        User safeUser = buildSafeUser(dbUser);
        session.setAttribute(CURRENT_USER, safeUser);

        Map<String, Object> result = new HashMap<>();
        result.put("selectedPaths", selectedPaths);
        result.put("user", safeUser);
        return result;
    }

    public Map<String, Object> getHomeTodos(HttpSession session) {
        User currentUser = requireLogin(session);
        Map<String, Object> result = new HashMap<>();
        if (ROLE_ADMIN.equals(currentUser.getRole())) {
            result.put("items", new ArrayList<>());
            result.put("totalCount", 0);
            result.put("missingClaimCount", 0);
            result.put("missingVehicleCount", 0);
            return result;
        }

        String sql = "SELECT m.ID AS policyId, " +
                "CASE WHEN c.ID IS NULL THEN 1 ELSE 0 END AS missingClaimRecord, " +
                "CASE WHEN v.ID IS NULL THEN 1 ELSE 0 END AS missingVehicleInfo " +
                "FROM motor_insurance m " +
                "LEFT JOIN claim_record c ON c.ID = m.ID " +
                "LEFT JOIN vehicle_info v ON v.ID = m.ID " +
                "WHERE m.creator_employee_no = ? AND (c.ID IS NULL OR v.ID IS NULL) " +
                "ORDER BY m.ID DESC";

        List<Map<String, Object>> items = jdbcTemplate.query(sql, (rs, rowNum) -> {
            List<String> missingItems = new ArrayList<>();
            boolean missingClaimRecord = rs.getInt("missingClaimRecord") == 1;
            boolean missingVehicleInfo = rs.getInt("missingVehicleInfo") == 1;
            if (missingClaimRecord) {
                missingItems.add("缺理赔记录");
            }
            if (missingVehicleInfo) {
                missingItems.add("缺车辆信息");
            }

            Map<String, Object> item = new LinkedHashMap<>();
            item.put("policyId", rs.getInt("policyId"));
            item.put("missingClaimRecord", missingClaimRecord);
            item.put("missingVehicleInfo", missingVehicleInfo);
            item.put("missingItems", missingItems);
            item.put("missingSummary", String.join("、", missingItems));
            return item;
        }, currentUser.getEmployeeNo());

        int missingClaimCount = 0;
        int missingVehicleCount = 0;
        for (Map<String, Object> item : items) {
            if (Boolean.TRUE.equals(item.get("missingClaimRecord"))) {
                missingClaimCount++;
            }
            if (Boolean.TRUE.equals(item.get("missingVehicleInfo"))) {
                missingVehicleCount++;
            }
        }

        result.put("items", items);
        result.put("totalCount", items.size());
        result.put("missingClaimCount", missingClaimCount);
        result.put("missingVehicleCount", missingVehicleCount);
        return result;
    }

    public Map<String, Object> updateHomeShortcuts(UserHomeShortcutRequest request, HttpSession session) {
        User currentUser = requireLogin(session);
        User dbUser = userMapper.selectById(currentUser.getId());
        if (dbUser == null) {
            throw new CustomException("用户不存在");
        }

        List<String> selectedPaths = sanitizeShortcutPaths(dbUser.getRole(), request == null ? null : request.getSelectedPaths());
        if (selectedPaths.size() > MAX_HOME_SHORTCUTS) {
            throw new CustomException("快捷入口最多只能保存 4 个");
        }

        User updateUser = new User();
        updateUser.setId(dbUser.getId());
        updateUser.setHomeShortcuts(joinShortcutPaths(selectedPaths));
        userMapper.updateHomeShortcuts(updateUser);

        dbUser.setHomeShortcuts(updateUser.getHomeShortcuts());
        User safeUser = buildSafeUser(dbUser);
        session.setAttribute(CURRENT_USER, safeUser);

        Map<String, Object> result = new HashMap<>();
        result.put("selectedPaths", selectedPaths);
        result.put("user", safeUser);
        return result;
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
        safeUser.setHomeShortcuts(joinShortcutPaths(sanitizeShortcutPaths(user.getRole(), parseShortcutPaths(user.getHomeShortcuts()))));
        return safeUser;
    }

    private void validateEmployeeNo(String employeeNo) {
        if (employeeNo == null || !employeeNo.matches("\\d{6}")) {
            throw new CustomException("\u8bf7\u8f93\u51656\u4f4d\u6570\u5b57\u5de5\u53f7");
        }
    }

    private void validateName(String name) {
        if (name == null || name.trim().isEmpty()) {
            throw new CustomException("\u59d3\u540d\u4e0d\u80fd\u4e3a\u7a7a");
        }
    }

    private void validatePassword(String password) {
        if (password == null || password.trim().isEmpty()) {
            throw new CustomException("\u5bc6\u7801\u4e0d\u80fd\u4e3a\u7a7a");
        }
    }

    private void validateRole(String role) {
        if (!ROLE_ADMIN.equals(role) && !ROLE_USER.equals(role)) {
            throw new CustomException("\u89d2\u8272\u53c2\u6570\u4e0d\u6b63\u786e");
        }
    }

    private void validateRegisterCode(String role, String registerCode) {
        String expectedCode = ROLE_ADMIN.equals(role) ? ADMIN_REGISTER_CODE : USER_REGISTER_CODE;
        if (registerCode == null || !expectedCode.equals(registerCode.trim())) {
            throw new CustomException("\u6ce8\u518c\u53e3\u4ee4\u9519\u8bef");
        }
    }

    private User requireAdmin(HttpSession session) {
        User currentUser = requireLogin(session);
        if (!ROLE_ADMIN.equals(currentUser.getRole())) {
            throw new CustomException("无权限操作该功能");
        }
        return currentUser;
    }

    private User requireLogin(HttpSession session) {
        Object currentUserObj = session.getAttribute(CURRENT_USER);
        if (!(currentUserObj instanceof User)) {
            throw new CustomException("请先登录");
        }
        return (User) currentUserObj;
    }

    private List<String> sanitizeShortcutPaths(String role, List<String> shortcutPaths) {
        List<String> rawPaths = shortcutPaths == null ? new ArrayList<>() : shortcutPaths;
        Set<String> allowedPaths = new LinkedHashSet<>(USER_ALLOWED_SHORTCUTS);
        if (ROLE_ADMIN.equals(role)) {
            allowedPaths.addAll(ADMIN_ONLY_SHORTCUTS);
        }

        LinkedHashSet<String> normalized = new LinkedHashSet<>();
        for (String path : rawPaths) {
            String trimmedPath = path == null ? "" : path.trim();
            if (trimmedPath.isEmpty()) {
                continue;
            }
            if (!allowedPaths.contains(trimmedPath)) {
                continue;
            }
            normalized.add(trimmedPath);
            if (normalized.size() == MAX_HOME_SHORTCUTS) {
                break;
            }
        }
        return new ArrayList<>(normalized);
    }

    private List<String> parseShortcutPaths(String homeShortcuts) {
        if (homeShortcuts == null || homeShortcuts.trim().isEmpty()) {
            return new ArrayList<>();
        }
        return Arrays.stream(homeShortcuts.split(","))
                .map(String::trim)
                .filter(item -> !item.isEmpty())
                .collect(Collectors.toList());
    }

    private String joinShortcutPaths(List<String> shortcutPaths) {
        if (shortcutPaths == null || shortcutPaths.isEmpty()) {
            return "";
        }
        return String.join(",", shortcutPaths);
    }

    private String encodePassword(String password) {
        return SecureUtil.md5(password);
    }

    private String now() {
        return LocalDateTime.now().format(TIME_FORMATTER);
    }
}
