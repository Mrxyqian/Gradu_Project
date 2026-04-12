"""
回滚脚本：将 test_func.csv 中的 25 条记录追加回原 CSV，
并重新插入 MySQL 表 motor_insurance，恢复删除前的状态。

前提：test_func.csv 和原 CSV 文件均存在且未被修改。
"""

import pandas as pd
from sqlalchemy import create_engine

# ─────────────────────────────────────────────
# 0. 配置区 —— 与 extract_and_sync_delete.py 保持一致
# ─────────────────────────────────────────────
SOURCE_CSV  = "./Motor vehicle insurance data.csv"
BACKUP_CSV  = "./test_func.csv"
TABLE_NAME  = "motor_insurance"

DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "root",          # ← 改成你的用户名
    "password": "123", # ← 改成你的密码
    "database": "gra_data",  # ← 改成你的数据库名
    "charset":  "utf8mb4",
}

# ─────────────────────────────────────────────
# 1. 读取两个 CSV
# ─────────────────────────────────────────────
print(f"[1/4] 读取文件 ...")
df_main   = pd.read_csv(SOURCE_CSV)
df_backup = pd.read_csv(BACKUP_CSV)
print(f"      原 CSV：{len(df_main)} 条")
print(f"      待恢复：{len(df_backup)} 条")

# ─────────────────────────────────────────────
# 2. 追加回原 CSV（保持列顺序一致）
# ─────────────────────────────────────────────
print(f"[2/4] 追加记录到 {SOURCE_CSV} ...")
df_restored = pd.concat([df_main, df_backup], ignore_index=True)
df_restored.to_csv(SOURCE_CSV, index=False)
print(f"      恢复后共 {len(df_restored)} 条，已覆盖保存。")

# ─────────────────────────────────────────────
# 3. 重新插入 MySQL
# ─────────────────────────────────────────────
print(f"[3/4] 连接 MySQL，重新插入 {len(df_backup)} 条记录 ...")

url = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    f"?charset={DB_CONFIG['charset']}"
)
engine = create_engine(url)

# if_exists='append' 只追加，不删除现有数据，不修改表结构
df_backup.to_sql(
    name      = TABLE_NAME,
    con       = engine,
    if_exists = "append",
    index     = False,
)
print(f"      MySQL [{TABLE_NAME}] 已插入 {len(df_backup)} 条。")

# ─────────────────────────────────────────────
# 4. 汇总
# ─────────────────────────────────────────────
print("\n[4/4] 回滚完成")
print(f"  ✅ {SOURCE_CSV}：已恢复至 {len(df_restored)} 条")
print(f"  ✅ MySQL [{TABLE_NAME}]：已补回 {len(df_backup)} 条")
print(f"\n  提示：如确认数据已完整恢复，可手动删除 {BACKUP_CSV}。")
