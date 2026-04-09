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
        if (!ROLE_ADMIN.equals(currentUser.getRole())) {
            throw new CustomException("普通用户不能删除数据");
        }
        return currentUser;
    }
}
