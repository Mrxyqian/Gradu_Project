package com.example.controller;

import com.example.common.Result;
import com.example.entity.User;
import com.example.entity.UserHomeShortcutRequest;
import com.example.service.UserService;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import javax.servlet.http.HttpSession;

@RestController
@RequestMapping("/user")
public class UserController {

    @Resource
    private UserService userService;

    @GetMapping("/selectAll")
    public Result selectAll(HttpSession session) {
        return Result.success(userService.selectAll(session));
    }

    @GetMapping("/homeShortcuts")
    public Result homeShortcuts(HttpSession session) {
        return Result.success(userService.getHomeShortcuts(session));
    }

    @PutMapping("/homeShortcuts")
    public Result updateHomeShortcuts(@RequestBody UserHomeShortcutRequest request, HttpSession session) {
        return Result.success(userService.updateHomeShortcuts(request, session));
    }

    @PostMapping("/add")
    public Result add(@RequestBody User user, HttpSession session) {
        userService.addUser(user, session);
        return Result.success();
    }

    @PutMapping("/update")
    public Result update(@RequestBody User user, HttpSession session) {
        userService.updateUser(user, session);
        return Result.success();
    }

    @DeleteMapping("/delete/{id}")
    public Result delete(@PathVariable Integer id, HttpSession session) {
        userService.deleteUser(id, session);
        return Result.success();
    }
}
