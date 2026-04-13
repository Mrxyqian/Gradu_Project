package com.example.mapper;

import com.example.entity.VehicleInfo;
import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

public interface VehicleInfoMapper {

    @Insert("INSERT INTO vehicle_info (ID, Type_risk, Year_matriculation, Power, Cylinder_capacity, " +
            "Value_vehicle, N_doors, Type_fuel, Length, Weight) VALUES (#{id}, #{typeRisk}, " +
            "#{yearMatriculation}, #{power}, #{cylinderCapacity}, #{valueVehicle}, #{nDoors}, " +
            "#{typeFuel}, #{length}, #{weight})")
    void insert(VehicleInfo vehicleInfo);

    @Delete("DELETE FROM vehicle_info WHERE ID = #{id}")
    void deleteById(Integer id);

    @Update("UPDATE vehicle_info SET Type_risk = #{typeRisk}, Year_matriculation = #{yearMatriculation}, " +
            "Power = #{power}, Cylinder_capacity = #{cylinderCapacity}, Value_vehicle = #{valueVehicle}, " +
            "N_doors = #{nDoors}, Type_fuel = #{typeFuel}, Length = #{length}, Weight = #{weight} WHERE ID = #{id}")
    void updateById(VehicleInfo vehicleInfo);

    @Select("SELECT ID as id, Type_risk as typeRisk, Year_matriculation as yearMatriculation, " +
            "Power as power, Cylinder_capacity as cylinderCapacity, Value_vehicle as valueVehicle, " +
            "N_doors as nDoors, Type_fuel as typeFuel, Length as length, Weight as weight " +
            "FROM vehicle_info WHERE ID = #{id}")
    VehicleInfo selectById(Integer id);

    List<VehicleInfo> selectAll(VehicleInfo vehicleInfo);

    @Select("SELECT Type_risk as typeRisk, COUNT(*) as count, AVG(Power) as avgPower, " +
            "AVG(Cylinder_capacity) as avgCylinderCapacity, AVG(Value_vehicle) as avgVehicleValue " +
            "FROM vehicle_info GROUP BY Type_risk")
    List<Map<String, Object>> statisticsByTypeRisk();

    @Select("SELECT Type_fuel as typeFuel, COUNT(*) as count, AVG(Power) as avgPower " +
            "FROM vehicle_info GROUP BY Type_fuel")
    List<Map<String, Object>> statisticsByTypeFuel();

    @Select("SELECT Year_matriculation as yearMatriculation, COUNT(*) as count " +
            "FROM vehicle_info GROUP BY Year_matriculation ORDER BY Year_matriculation")
    List<Map<String, Object>> statisticsByYear();
}
