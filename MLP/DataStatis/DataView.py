import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. 读取数据
file_path = "../DataSet/Motor vehicle insurance data.csv"
df = pd.read_csv(file_path)

if "Cost_claims_year" not in df.columns:
    raise KeyError("数据集中不存在字段 Cost_claims_year")

# 2. 清理数据，只保留数值型且大于 0 的样本
s = pd.to_numeric(df["Cost_claims_year"], errors="coerce").dropna()
s = s[s > 0]

if s.empty:
    raise ValueError("Cost_claims_year 中没有大于 0 的有效样本")

# 3. 分箱：200 元步长，>2000 合并
bins = list(range(0, 2001, 200)) + [np.inf]
labels = [f"{i}-{i+200}" for i in range(0, 2000, 200)] + [">2000"]

freq = pd.cut(
    s,
    bins=bins,
    labels=labels,
    right=True,
    include_lowest=True
).value_counts().sort_index()

# 4. 统计指标
stats = {
    "Sample size": s.shape[0],
    "Minimum": s.min(),
    "Maximum": s.max(),
    "Mean": s.mean(),
    "Median": s.median(),
    "Variance": s.var(ddof=1),
    "Standard deviation": s.std(ddof=1),
    "Coefficient of variation": s.std(ddof=1) / s.mean() if s.mean() != 0 else np.nan,
    "Skewness": s.skew(),
    "Q1 (25%)": s.quantile(0.25),
    "Q3 (75%)": s.quantile(0.75),
    "IQR": s.quantile(0.75) - s.quantile(0.25),
}

# 5. 打印频数分布
print("=== Frequency distribution of Cost_claims_year ===")
print(freq.to_string())

# 6. 打印统计指标，统一保留三位小数
print("\n=== Distribution-related statistics ===")
stats_df = pd.DataFrame(
    [(k, f"{v:.3f}" if pd.notna(v) else "NaN") for k, v in stats.items()],
    columns=["Metric", "Value"]
)
print(stats_df.to_string(index=False))

# 7. 绘制直方图（柱状图）并标注频数（字体放大 + Y轴留空）
plt.figure(figsize=(14, 6))

# 全局字体大小设置
plt.rcParams['font.size'] = 14
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12

bars = plt.bar(freq.index.astype(str), freq.values, edgecolor="black")

max_height = freq.values.max()
# 扩展 Y 轴上限，为数字标签留出空间
plt.ylim(0, max_height * 1.15)   # 顶部留出 5% 空白

# 添加数字标签
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2.,
             height + max_height * 0.01,   # 标签位置在柱子上方一点
             f'{int(height)}',
             ha='center', va='bottom',
             fontsize=16)

plt.title("Distribution of the claim amount")
plt.xlabel("Amount range")
plt.ylabel("Quantity")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()