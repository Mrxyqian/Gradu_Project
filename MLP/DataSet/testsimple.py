import pandas as pd
from sqlalchemy import create_engine, text

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "123",
    "database": "gra_data",
    "charset": "utf8mb4",
}

url = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    f"?charset={DB_CONFIG['charset']}"
)
engine = create_engine(url)

business_columns = [
    "ID",
    "creator_employee_no",
    "Date_start_contract",
    "Date_last_renewal",
    "Date_next_renewal",
    "Date_birth",
    "Date_driving_licence",
    "Distribution_channel",
    "Seniority",
    "Policies_in_force",
    "Max_policies",
    "Max_products",
    "Lapse",
    "Date_lapse",
    "Payment",
    "Premium",
    "Type_risk",
    "Area",
    "Second_driver",
]

query = "SELECT " + ", ".join(f"`{column}`" for column in business_columns) + " FROM motor_insurance"
df = pd.read_sql(query, engine)
print(f"去重前：{len(df)} 条")

duplicates = df[df.duplicated(keep=False)]
if duplicates.empty:
    print("无重复数据，无需处理。")
else:
    print(f"发现 {len(duplicates)} 条重复记录（含所有副本）")

    columns = list(df.columns)
    where_clause = " AND ".join([f"`{col}` <=> :{col}" for col in columns])
    delete_sql = text(f"DELETE FROM `motor_insurance` WHERE {where_clause}")

    dup_unique = duplicates.drop_duplicates(keep="first")

    with engine.begin() as conn:
        for _, row in dup_unique.iterrows():
            params = {col: (None if pd.isna(row[col]) else row[col]) for col in columns}
            conn.execute(delete_sql, params)

        dup_unique.to_sql(
            name="motor_insurance",
            con=conn,
            if_exists="append",
            index=False,
        )

    deleted_count = len(duplicates) - len(dup_unique)
    print(f"MySQL 已删除 {deleted_count} 条多余重复记录，保留 {len(dup_unique)} 条。")

    df_deduped = df.drop_duplicates(keep="first")
    df_deduped.to_csv("Motor vehicle insurance data.csv", index=False)
    print(f"CSV 已同步去重：{len(df)} -> {len(df_deduped)} 条")