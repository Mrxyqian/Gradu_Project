"""
从 Motor vehicle insurance data.csv 中抽取 25 条记录到 test_func.csv，
同时在原 CSV 和 MySQL 表 motor_insurance 中同步删除这 25 条记录。

抽取规则：
  - 20 条：N_claims_year == 0
  -  5 条：N_claims_year  > 0

使用前请确认：
  1. pip install pandas sqlalchemy pymysql
  2. 修改下方 DB_CONFIG 中的数据库连接信息
"""

import pandas as pd
from sqlalchemy import create_engine, text

# ─────────────────────────────────────────────
# 0. 配置区 —— 请按实际情况修改
# ─────────────────────────────────────────────
SOURCE_CSV  = "./Motor vehicle insurance data.csv"   # 原始 CSV 路径
OUTPUT_CSV  = "test_func.csv"                       # 抽取结果存放路径
TARGET_COL  = "N_claims_year"                       # 筛选字段
TABLE_NAME  = "motor_insurance"                     # MySQL 表名
N_ZERO      = 20                                    # N_claims_year == 0 的条数
N_NONZERO   = 5                                     # N_claims_year  > 0 的条数

DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "root",          # ← 改成你的用户名
    "password": "123", # ← 改成你的密码
    "database": "gra_data",  # ← 改成你的数据库名
    "charset":  "utf8mb4",
}

# ─────────────────────────────────────────────
# 1. 读取 CSV
# ─────────────────────────────────────────────
print(f"[1/5] 读取 {SOURCE_CSV} ...")
df = pd.read_csv(SOURCE_CSV)
print(f"      共 {len(df)} 条记录，列：{list(df.columns)}")

if TARGET_COL not in df.columns:
    raise ValueError(f"字段 '{TARGET_COL}' 不存在，请检查列名。")

# ─────────────────────────────────────────────
# 2. 随机抽样
# ─────────────────────────────────────────────
print(f"[2/5] 随机抽取 {N_ZERO} 条 {TARGET_COL}==0 + {N_NONZERO} 条 {TARGET_COL}>0 ...")

zero_pool    = df[df[TARGET_COL] == 0]
nonzero_pool = df[df[TARGET_COL] >  0]

if len(zero_pool) < N_ZERO:
    raise ValueError(f"{TARGET_COL}==0 的记录仅 {len(zero_pool)} 条，不足 {N_ZERO} 条。")
if len(nonzero_pool) < N_NONZERO:
    raise ValueError(f"{TARGET_COL}>0 的记录仅 {len(nonzero_pool)} 条，不足 {N_NONZERO} 条。")

sampled = pd.concat([
    zero_pool.sample(n=N_ZERO,    random_state=42),
    nonzero_pool.sample(n=N_NONZERO, random_state=42),
])
sampled_idx = set(sampled.index)   # 原 DataFrame 的行索引
print(f"      抽取完成，共 {len(sampled)} 条。")

# ─────────────────────────────────────────────
# 3. 写出 test_func.csv，更新原 CSV
# ─────────────────────────────────────────────
print(f"[3/5] 写出 {OUTPUT_CSV} ...")
sampled.to_csv(OUTPUT_CSV, index=False)

df_remaining = df.drop(index=sampled_idx)
df_remaining.to_csv(SOURCE_CSV, index=False)
print(f"      原 CSV 剩余 {len(df_remaining)} 条，已覆盖保存。")

# ─────────────────────────────────────────────
# 4. 连接 MySQL，同步删除
# ─────────────────────────────────────────────
print(f"[4/5] 连接 MySQL，同步删除 {len(sampled)} 条记录 ...")

url = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    f"?charset={DB_CONFIG['charset']}"
)
engine = create_engine(url)

# 由于表无主键，使用所有列做精确匹配，每次只删 1 行（LIMIT 1），
# 防止偶发重复行被多删。
columns = list(sampled.columns)
where_clause = " AND ".join(
    [f"`{col}` <=> :{col}" for col in columns]   # <=> 可安全比较 NULL
)
delete_sql = text(
    f"DELETE FROM `{TABLE_NAME}` WHERE {where_clause} LIMIT 1"
)

deleted_count = 0
with engine.begin() as conn:
    for _, row in sampled.iterrows():
        params = {col: (None if pd.isna(row[col]) else row[col]) for col in columns}
        result = conn.execute(delete_sql, params)
        deleted_count += result.rowcount

print(f"      MySQL 实际删除 {deleted_count} 条（预期 {len(sampled)} 条）。")

if deleted_count != len(sampled):
    print("  ⚠️  警告：删除数量与预期不符，请手动核查数据库。")

# ─────────────────────────────────────────────
# 5. 汇总
# ─────────────────────────────────────────────
print("\n[5/5] 完成汇总")
print(f"  ✅ {OUTPUT_CSV}：已写入 {len(sampled)} 条")
print(f"  ✅ {SOURCE_CSV}：剩余 {len(df_remaining)} 条")
print(f"  ✅ MySQL [{TABLE_NAME}]：已删除 {deleted_count} 条")