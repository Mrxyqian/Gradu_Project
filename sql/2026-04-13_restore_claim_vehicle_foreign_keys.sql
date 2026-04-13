ALTER TABLE claim_record
    ADD CONSTRAINT fk_claim_record_motor_insurance
        FOREIGN KEY (ID) REFERENCES motor_insurance(ID)
        ON UPDATE CASCADE
        ON DELETE CASCADE;

ALTER TABLE vehicle_info
    ADD CONSTRAINT fk_vehicle_info_motor_insurance
        FOREIGN KEY (ID) REFERENCES motor_insurance(ID)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
