package com.example.exception;

import cn.hutool.log.Log;
import cn.hutool.log.LogFactory;
import com.example.common.Result;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;

import javax.servlet.http.HttpServletRequest;

@ControllerAdvice(basePackages="com.example.controller")
public class GlobalExceptionHandler {

    private static final Log log = LogFactory.get();

    @ExceptionHandler(CustomException.class)
    @ResponseBody
    public Result customError(HttpServletRequest request, CustomException e) {
        return Result.error(e.getMsg());
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    @ResponseBody
    public Result dataIntegrityError(HttpServletRequest request, DataIntegrityViolationException e) {
        log.error("Data integrity violation", e);
        return Result.error("\u63d0\u4ea4\u7684\u6570\u636e\u4e0d\u5b8c\u6574\u6216\u683c\u5f0f\u4e0d\u6b63\u786e\uff0c\u8bf7\u68c0\u67e5\u5fc5\u586b\u9879");
    }

    @ExceptionHandler(Exception.class)
    @ResponseBody
    public Result error(HttpServletRequest request, Exception e) {
        log.error("Unexpected exception", e);
        return Result.error();
    }
}
