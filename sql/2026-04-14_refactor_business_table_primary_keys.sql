CREATE TABLE IF NOT EXISTS motor_insurance_backup_20260414_tabid_refactor LIKE motor_insurance;
INSERT INTO motor_insurance_backup_20260414_tabid_refactor SELECT * FROM motor_insurance;

CREATE TABLE IF NOT EXISTS claim_record_backup_20260414_tabid_refactor LIKE claim_record;
INSERT INTO claim_record_backup_20260414_tabid_refactor SELECT * FROM claim_record;

CREATE TABLE IF NOT EXISTS vehicle_info_backup_20260414_tabid_refactor LIKE vehicle_info;
INSERT INTO vehicle_info_backup_20260414_tabid_refactor SELECT * FROM vehicle_info;

ALTER TABLE claim_record DROP FOREIGN KEY fk_claim_record_motor_insurance;
ALTER TABLE vehicle_info DROP FOREIGN KEY fk_vehicle_info_motor_insurance;

ALTER TABLE motor_insurance
    ADD COLUMN tab_id INT NOT NULL AUTO_INCREMENT COMMENT '表内主键，无业务含义' AFTER ID,
    ADD UNIQUE KEY uk_motor_insurance_tab_id (tab_id);

ALTER TABLE claim_record
    ADD COLUMN tab_id INT NOT NULL AUTO_INCREMENT COMMENT '表内主键，无业务含义' AFTER ID,
    ADD UNIQUE KEY uk_claim_record_tab_id (tab_id);

ALTER TABLE vehicle_info
    ADD COLUMN tab_id INT NOT NULL AUTO_INCREMENT COMMENT '表内主键，无业务含义' AFTER ID,
    ADD UNIQUE KEY uk_vehicle_info_tab_id (tab_id);

ALTER TABLE motor_insurance
    DROP PRIMARY KEY,
    ADD PRIMARY KEY (tab_id),
    ADD UNIQUE KEY uk_motor_insurance_id (ID);

ALTER TABLE claim_record
    DROP PRIMARY KEY,
    ADD PRIMARY KEY (tab_id),
    ADD UNIQUE KEY uk_claim_record_id (ID);

ALTER TABLE vehicle_info
    DROP PRIMARY KEY,
    ADD PRIMARY KEY (tab_id),
    ADD UNIQUE KEY uk_vehicle_info_id (ID);

ALTER TABLE claim_record
    ADD CONSTRAINT fk_claim_record_motor_insurance
        FOREIGN KEY (ID) REFERENCES motor_insurance (ID)
        ON DELETE CASCADE
        ON UPDATE CASCADE;

ALTER TABLE vehicle_info
    ADD CONSTRAINT fk_vehicle_info_motor_insurance
        FOREIGN KEY (ID) REFERENCES motor_insurance (ID)
        ON DELETE CASCADE
        ON UPDATE CASCADE;

CREATE TABLE IF NOT EXISTS motor_insurance_id_sequence (
    seq_id INT NOT NULL AUTO_INCREMENT COMMENT '系统分配的保单编号序列值',
    PRIMARY KEY (seq_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='motor_insurance 业务保单编号序列表';

SET @next_policy_id = (SELECT COALESCE(MAX(ID), 0) + 1 FROM motor_insurance);
SET @alter_sequence_sql = CONCAT('ALTER TABLE motor_insurance_id_sequence AUTO_INCREMENT = ', @next_policy_id);
PREPARE stmt FROM @alter_sequence_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
