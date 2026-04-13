-- 1) 备份原表，方便回滚
DROP TABLE IF EXISTS motor_insurance_backup_20260413_idfix;
CREATE TABLE motor_insurance_backup_20260413_idfix AS
SELECT * FROM motor_insurance;

-- 2) 为每一行补一个临时唯一行号，便于精确更新重复 ID
ALTER TABLE motor_insurance
    ADD COLUMN migration_row_id BIGINT NOT NULL AUTO_INCREMENT,
    ADD UNIQUE KEY uk_motor_insurance_migration_row_id (migration_row_id);

-- 3) 将重复 ID 中除第一条外的记录，顺延到当前最大 ID 之后
SET @next_id := (SELECT MAX(ID) FROM motor_insurance);

UPDATE motor_insurance mi
JOIN (
    SELECT ordered.migration_row_id,
           CASE
               WHEN ordered.rn = 1 THEN ordered.old_id
               ELSE (@next_id := @next_id + 1)
           END AS new_id
    FROM (
        SELECT migration_row_id,
               ID AS old_id,
               ROW_NUMBER() OVER (PARTITION BY ID ORDER BY migration_row_id) AS rn
        FROM motor_insurance
    ) ordered
    ORDER BY ordered.old_id, ordered.rn, ordered.migration_row_id
) fixed_ids ON fixed_ids.migration_row_id = mi.migration_row_id
SET mi.ID = fixed_ids.new_id
WHERE mi.ID <> fixed_ids.new_id;

-- 4) 清理临时列并把 ID 设为主键
ALTER TABLE motor_insurance
    DROP COLUMN migration_row_id;

ALTER TABLE motor_insurance
    ADD PRIMARY KEY (ID);

-- 5) 验证
SELECT COUNT(*) AS total_rows FROM motor_insurance;
SELECT COUNT(*) AS duplicate_groups
FROM (
    SELECT ID
    FROM motor_insurance
    GROUP BY ID
    HAVING COUNT(*) > 1
) t;
