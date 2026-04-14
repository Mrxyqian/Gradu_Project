-- Add creator ownership columns for claim_record, motor_insurance, and vehicle_info.
-- Existing rows are assigned so the first half belongs to 000123 and the second half belongs to 000124.
-- claim_record and vehicle_info inherit ownership from motor_insurance when the same policy ID exists.

SET @schema_name = DATABASE();

SET @sql = IF(
    EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = @schema_name
          AND TABLE_NAME = 'motor_insurance'
          AND COLUMN_NAME = 'creator_employee_no'
    ),
    'SELECT ''motor_insurance.creator_employee_no already exists''',
    'ALTER TABLE motor_insurance ADD COLUMN creator_employee_no VARCHAR(6) NULL COMMENT ''creator employee no'' AFTER ID'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
    EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = @schema_name
          AND TABLE_NAME = 'claim_record'
          AND COLUMN_NAME = 'creator_employee_no'
    ),
    'SELECT ''claim_record.creator_employee_no already exists''',
    'ALTER TABLE claim_record ADD COLUMN creator_employee_no VARCHAR(6) NULL COMMENT ''creator employee no'' AFTER ID'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
    EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = @schema_name
          AND TABLE_NAME = 'vehicle_info'
          AND COLUMN_NAME = 'creator_employee_no'
    ),
    'SELECT ''vehicle_info.creator_employee_no already exists''',
    'ALTER TABLE vehicle_info ADD COLUMN creator_employee_no VARCHAR(6) NULL COMMENT ''creator employee no'' AFTER ID'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @motor_total = (SELECT COUNT(*) FROM motor_insurance);

UPDATE motor_insurance mi
JOIN (
    SELECT ranked.ID,
           CASE
               WHEN ranked.row_num <= FLOOR(@motor_total / 2) THEN '000123'
               ELSE '000124'
           END AS creator_employee_no
    FROM (
        SELECT ordered.ID, (@motor_row_num := @motor_row_num + 1) AS row_num
        FROM (
            SELECT ID
            FROM motor_insurance
            ORDER BY ID
        ) ordered
        CROSS JOIN (SELECT @motor_row_num := 0) vars
    ) ranked
) assigned ON assigned.ID = mi.ID
SET mi.creator_employee_no = assigned.creator_employee_no;

UPDATE claim_record cr
JOIN motor_insurance mi ON mi.ID = cr.ID
SET cr.creator_employee_no = mi.creator_employee_no
WHERE cr.creator_employee_no IS NULL OR cr.creator_employee_no = '';

SET @claim_missing_total = (
    SELECT COUNT(*)
    FROM claim_record
    WHERE creator_employee_no IS NULL OR creator_employee_no = ''
);

UPDATE claim_record cr
JOIN (
    SELECT ranked.ID,
           CASE
               WHEN ranked.row_num <= FLOOR(@claim_missing_total / 2) THEN '000123'
               ELSE '000124'
           END AS creator_employee_no
    FROM (
        SELECT ordered.ID, (@claim_row_num := @claim_row_num + 1) AS row_num
        FROM (
            SELECT ID
            FROM claim_record
            WHERE creator_employee_no IS NULL OR creator_employee_no = ''
            ORDER BY ID
        ) ordered
        CROSS JOIN (SELECT @claim_row_num := 0) vars
    ) ranked
) assigned ON assigned.ID = cr.ID
SET cr.creator_employee_no = assigned.creator_employee_no
WHERE cr.creator_employee_no IS NULL OR cr.creator_employee_no = '';

UPDATE vehicle_info vi
JOIN motor_insurance mi ON mi.ID = vi.ID
SET vi.creator_employee_no = mi.creator_employee_no
WHERE vi.creator_employee_no IS NULL OR vi.creator_employee_no = '';

SET @vehicle_missing_total = (
    SELECT COUNT(*)
    FROM vehicle_info
    WHERE creator_employee_no IS NULL OR creator_employee_no = ''
);

UPDATE vehicle_info vi
JOIN (
    SELECT ranked.ID,
           CASE
               WHEN ranked.row_num <= FLOOR(@vehicle_missing_total / 2) THEN '000123'
               ELSE '000124'
           END AS creator_employee_no
    FROM (
        SELECT ordered.ID, (@vehicle_row_num := @vehicle_row_num + 1) AS row_num
        FROM (
            SELECT ID
            FROM vehicle_info
            WHERE creator_employee_no IS NULL OR creator_employee_no = ''
            ORDER BY ID
        ) ordered
        CROSS JOIN (SELECT @vehicle_row_num := 0) vars
    ) ranked
) assigned ON assigned.ID = vi.ID
SET vi.creator_employee_no = assigned.creator_employee_no
WHERE vi.creator_employee_no IS NULL OR vi.creator_employee_no = '';

ALTER TABLE motor_insurance
    MODIFY COLUMN creator_employee_no VARCHAR(6) NOT NULL COMMENT 'creator employee no';

ALTER TABLE claim_record
    MODIFY COLUMN creator_employee_no VARCHAR(6) NOT NULL COMMENT 'creator employee no';

ALTER TABLE vehicle_info
    MODIFY COLUMN creator_employee_no VARCHAR(6) NOT NULL COMMENT 'creator employee no';

SET @sql = IF(
    EXISTS (
        SELECT 1
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = @schema_name
          AND TABLE_NAME = 'motor_insurance'
          AND INDEX_NAME = 'idx_motor_insurance_creator_employee_no'
    ),
    'SELECT ''idx_motor_insurance_creator_employee_no already exists''',
    'CREATE INDEX idx_motor_insurance_creator_employee_no ON motor_insurance (creator_employee_no)'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
    EXISTS (
        SELECT 1
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = @schema_name
          AND TABLE_NAME = 'claim_record'
          AND INDEX_NAME = 'idx_claim_record_creator_employee_no'
    ),
    'SELECT ''idx_claim_record_creator_employee_no already exists''',
    'CREATE INDEX idx_claim_record_creator_employee_no ON claim_record (creator_employee_no)'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
    EXISTS (
        SELECT 1
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = @schema_name
          AND TABLE_NAME = 'vehicle_info'
          AND INDEX_NAME = 'idx_vehicle_info_creator_employee_no'
    ),
    'SELECT ''idx_vehicle_info_creator_employee_no already exists''',
    'CREATE INDEX idx_vehicle_info_creator_employee_no ON vehicle_info (creator_employee_no)'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
