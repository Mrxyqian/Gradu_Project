package com.example.mapper;

import com.example.entity.User;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

public interface UserMapper {

    @Update("CREATE TABLE IF NOT EXISTS sys_user (" +
            "id INT PRIMARY KEY AUTO_INCREMENT," +
            "employee_no VARCHAR(6) NOT NULL UNIQUE," +
            "name VARCHAR(30) NOT NULL," +
            "password VARCHAR(64) NOT NULL," +
            "role VARCHAR(20) NOT NULL," +
            "last_login_time VARCHAR(19) DEFAULT NULL," +
            "create_time VARCHAR(19) NOT NULL" +
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    void createTableIfNotExists();

    @Insert("INSERT INTO sys_user (employee_no, name, password, role, last_login_time, create_time) " +
            "VALUES (#{employeeNo}, #{name}, #{password}, #{role}, #{lastLoginTime}, #{createTime})")
    void insert(User user);

    @Select("SELECT id, employee_no AS employeeNo, name, password, role, last_login_time AS lastLoginTime, " +
            "create_time AS createTime FROM sys_user WHERE employee_no = #{employeeNo} LIMIT 1")
    User selectByEmployeeNo(String employeeNo);

    @Select("SELECT id, employee_no AS employeeNo, name, password, role, last_login_time AS lastLoginTime, " +
            "create_time AS createTime FROM sys_user WHERE id = #{id} LIMIT 1")
    User selectById(Integer id);

    @Select("SELECT id, employee_no AS employeeNo, name, password, role, last_login_time AS lastLoginTime, " +
            "create_time AS createTime FROM sys_user ORDER BY CASE WHEN role = 'ADMIN' THEN 0 ELSE 1 END, employee_no ASC")
    List<User> selectAll();

    @Update("UPDATE sys_user SET last_login_time = #{lastLoginTime} WHERE id = #{id}")
    void updateLastLoginTime(User user);

    @Update("UPDATE sys_user SET name = #{name}, password = #{password}, role = #{role} WHERE id = #{id}")
    void updateById(User user);

    @Delete("DELETE FROM sys_user WHERE id = #{id}")
    void deleteById(Integer id);

    @Select("SELECT COUNT(*) FROM sys_user WHERE role = #{role}")
    Integer countByRole(String role);

    @Insert("INSERT INTO sys_user (employee_no, name, password, role, create_time) " +
            "SELECT #{employeeNo}, #{name}, #{password}, #{role}, #{createTime} FROM DUAL " +
            "WHERE NOT EXISTS (SELECT 1 FROM sys_user WHERE employee_no = #{employeeNo})")
    void initAdmin(User user);
}
