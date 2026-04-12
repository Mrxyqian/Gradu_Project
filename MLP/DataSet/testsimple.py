import pandas as pd
from sqlalchemy import create_engine, text

DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "root",          # ← 改成你的用户名
    "password": "123", # ← 改成你的密码
    "database": "gra_data",  # ← 改成你的数据库名
    "charset":  "utf8mb4",
}

url = (f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
       f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
       f"?charset={DB_CONFIG['charset']}")
engine = create_engine(url)

# ── 1. 读取整张表 ──────────────────────────────────────────
df = pd.read_sql("SELECT * FROM motor_insurance", engine)
print(f"去重前：{len(df)} 条")

# ── 2. 检测重复行 ──────────────────────────────────────────
duplicates = df[df.duplicated(keep=False)]
if duplicates.empty:
    print("✅ 无重复数据，无需处理。")
else:
    print(f"⚠️  发现 {len(duplicates)} 条重复记录（含所有副本）")

    # ── 3. 删除 MySQL 中的重复行，每组只保留一条 ──────────────
    # 策略：对每组重复记录，先全部删除，再插回一条
    columns = list(df.columns)
    where_clause = " AND ".join([f"`{col}` <=> :{col}" for col in columns])
    delete_sql = text(f"DELETE FROM `motor_insurance` WHERE {where_clause}")

    # 取每组重复记录的唯一值（即去重后的版本）
    dup_unique = duplicates.drop_duplicates(keep="first")

    with engine.begin() as conn:
        for _, row in dup_unique.iterrows():
            params = {col: (None if pd.isna(row[col]) else row[col]) for col in columns}
            # 先把这组重复的全部删掉（不加 LIMIT，删除所有副本）
            conn.execute(delete_sql, params)

        # 再把每组的唯一记录插回去
        dup_unique.to_sql(
            name      = "motor_insurance",
            con       = conn,
            if_exists = "append",
            index     = False,
        )

    deleted_count = len(duplicates) - len(dup_unique)
    print(f"✅ MySQL 已删除 {deleted_count} 条多余重复记录，保留 {len(dup_unique)} 条。")

    # ── 4. 同步更新 CSV ────────────────────────────────────
    df_deduped = df.drop_duplicates(keep="first")
    df_deduped.to_csv("Motor vehicle insurance data.csv", index=False)
    print(f"✅ CSV 已同步去重：{len(df)} → {len(df_deduped)} 条")