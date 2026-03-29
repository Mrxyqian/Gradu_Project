package com.example.mapper;

import com.example.entity.VehicleInfo;
import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

public interface VehicleInfoMapper {

    @Select("SELECT * FROM motor_insurance WHERE ID = #{id}")
    VehicleInfo selectById(Integer id);

    List<VehicleInfo> selectAll(VehicleInfo vehicleInfo);

    @Select("SELECT Type_risk as typeRisk, COUNT(*) as count, AVG(Power) as avgPower, " +
            "AVG(Cylinder_capacity) as avgCylinderCapacity, AVG(Value_vehicle) as avgVehicleValue " +
            "FROM motor_insurance GROUP BY Type_risk")
    List<Map<String, Object>> statisticsByTypeRisk();

    @Select("SELECT Type_fuel as typeFuel, COUNT(*) as count, AVG(Power) as avgPower " +
            "FROM motor_insurance GROUP BY Type_fuel")
    List<Map<String, Object>> statisticsByTypeFuel();

    @Select("SELECT Year_matriculation as yearMatriculation, COUNT(*) as count " +
            "FROM motor_insurance GROUP BY Year_matriculation ORDER BY Year_matriculation")
    List<Map<String, Object>> statisticsByYear();
}
