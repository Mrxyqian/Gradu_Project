START TRANSACTION;

INSERT INTO claim_record (
    ID,
    Cost_claims_year,
    N_claims_year,
    N_claims_history,
    R_Claims_history,
    Type_risk,
    Area
)
SELECT
    ID,
    Cost_claims_year,
    N_claims_year,
    N_claims_history,
    R_Claims_history,
    Type_risk,
    Area
FROM motor_insurance
ON DUPLICATE KEY UPDATE
    Cost_claims_year = VALUES(Cost_claims_year),
    N_claims_year = VALUES(N_claims_year),
    N_claims_history = VALUES(N_claims_history),
    R_Claims_history = VALUES(R_Claims_history),
    Type_risk = VALUES(Type_risk),
    Area = VALUES(Area);

INSERT INTO vehicle_info (
    ID,
    Type_risk,
    Year_matriculation,
    Power,
    Cylinder_capacity,
    Value_vehicle,
    N_doors,
    Type_fuel,
    Length,
    Weight
)
SELECT
    ID,
    Type_risk,
    Year_matriculation,
    Power,
    Cylinder_capacity,
    Value_vehicle,
    N_doors,
    Type_fuel,
    Length,
    Weight
FROM motor_insurance
ON DUPLICATE KEY UPDATE
    Type_risk = VALUES(Type_risk),
    Year_matriculation = VALUES(Year_matriculation),
    Power = VALUES(Power),
    Cylinder_capacity = VALUES(Cylinder_capacity),
    Value_vehicle = VALUES(Value_vehicle),
    N_doors = VALUES(N_doors),
    Type_fuel = VALUES(Type_fuel),
    Length = VALUES(Length),
    Weight = VALUES(Weight);

COMMIT;

SELECT COUNT(*) AS motor_rows FROM motor_insurance;
SELECT COUNT(*) AS claim_rows FROM claim_record;
SELECT COUNT(*) AS vehicle_rows FROM vehicle_info;
