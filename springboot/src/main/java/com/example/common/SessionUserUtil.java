package com.example.common;

import com.example.entity.User;
import com.example.exception.CustomException;

import javax.servlet.http.HttpSession;

public class SessionUserUtil {

    private static final String CURRENT_USER = "currentUser";
    private static final String ROLE_ADMIN = "ADMIN";

    private SessionUserUtil() {
    }

    public static User requireLogin(HttpSession session) {
        Object currentUserObj = session.getAttribute(CURRENT_USER);
        if (!(currentUserObj instanceof User)) {
            throw new CustomException("请先登录");
        }
        return (User) currentUserObj;
    }

    public static User requireAdmin(HttpSession session) {
        User currentUser = requireLogin(session);
        if (!isAdmin(currentUser)) {
            throw new CustomException("无权限执行该操作");
        }
        return currentUser;
    }

    public static boolean isAdmin(User user) {
        return user != null && ROLE_ADMIN.equals(user.getRole());
    }

    public static String resolveDataScopeEmployeeNo(HttpSession session) {
        User currentUser = requireLogin(session);
        return isAdmin(currentUser) ? null : currentUser.getEmployeeNo();
    }

    public static User requireOwnerOrAdmin(String creatorEmployeeNo, HttpSession session) {
        User currentUser = requireLogin(session);
        if (isAdmin(currentUser)) {
            return currentUser;
        }
        if (creatorEmployeeNo == null || !creatorEmployeeNo.equals(currentUser.getEmployeeNo())) {
            throw new CustomException("无权限查看或操作该数据");
        }
        return currentUser;
    }
}
