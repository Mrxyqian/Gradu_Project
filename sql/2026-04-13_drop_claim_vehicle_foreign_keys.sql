ALTER TABLE claim_record
    DROP FOREIGN KEY fk_claim_record_motor_insurance;

ALTER TABLE vehicle_info
    DROP FOREIGN KEY fk_vehicle_info_motor_insurance;
