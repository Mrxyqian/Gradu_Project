package com.example.controller;

import com.example.common.Result;
import com.example.entity.User;
import com.example.service.UserService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import java.util.Map;

@RestController
@RequestMapping("/auth")
public class AuthController {

    @Resource
    private UserService userService;

    @PostMapping("/register")
    public Result register(@RequestBody User user) {
        Map<String, Object> data = userService.register(user);
        return Result.success(data);
    }

    @PostMapping("/login")
    public Result login(@RequestBody User user) {
        Map<String, Object> data = userService.login(user);
        return Result.success(data);
    }
}
