import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')


# 读取原始文件，指定分隔符为分号
df_motor = pd.read_csv('./DataSet/Motor vehicle insurance data.csv', sep=';')
df_sample = pd.read_csv('./DataSet/sample type claim.csv', sep=';')

# 保存为标准 CSV（逗号分隔）
df_motor.to_csv('./DataSet/Motor vehicle insurance data.csv', index=False)
df_sample.to_csv('./DataSet/sample type claim.csv', index=False)

print("转换完成！")

def inspect_dataset(df, name, target_col=None):
    """对一个数据集进行基础检测，返回检测结果字典"""
    print(f"\n{'=' * 50}\n数据集：{name}\n{'=' * 50}")

    # 1. 基本信息
    print(f"形状: {df.shape}")
    print(f"列名: {list(df.columns)}")
    print("\n数据类型:\n", df.dtypes)

    # 2. 缺失值检测
    missing = df.isnull().sum()
    missing_pct = (missing / len(df)) * 100
    missing_report = missing[missing > 0].sort_values(ascending=False)
    if len(missing_report) > 0:
        print(f"\n⚠️ 发现缺失值 (共 {len(missing_report)} 列):")
        for col, cnt in missing_report.items():
            print(f"   {col}: {cnt} ({missing_pct[col]:.2f}%)")
    else:
        print("\n✅ 无缺失值")

    # 3. 重复行检测
    dup_rows = df.duplicated().sum()
    if dup_rows > 0:
        print(f"\n⚠️ 发现重复行: {dup_rows} 条 ({dup_rows / len(df) * 100:.2f}%)")
    else:
        print(f"\n✅ 无重复行")

    # 4. 数值型列统计与异常值检测（基于IQR或标准差）
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        print(f"\n数值型列 ({len(numeric_cols)} 列): {numeric_cols}")
        for col in numeric_cols:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
            if len(outliers) > 0:
                print(f"   ⚠️ {col}: 发现 {len(outliers)} 个异常值 ({len(outliers) / len(df) * 100:.2f}%)")
            else:
                print(f"   ✅ {col}: 无异常值（基于IQR）")
    else:
        print("\n无数值型列")

    # 5. 类别型列（object 或 category）
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    if cat_cols:
        print(f"\n类别型列 ({len(cat_cols)} 列): {cat_cols}")
        for col in cat_cols:
            unique_vals = df[col].nunique()
            print(f"   {col}: 唯一值数 {unique_vals}")
            # 低频类别（出现次数少于总样本的 1% 或少于 10 次，可根据数据规模调整）
            freq = df[col].value_counts()
            low_freq = freq[freq < max(10, len(df) * 0.01)]
            if len(low_freq) > 0:
                print(f"       ⚠️ 低频类别: {len(low_freq)} 个（占比 <1% 或少于 10 次）")
    else:
        print("\n无类别型列")

    # 6. 目标变量分析（如果提供）
    if target_col and target_col in df.columns:
        print(f"\n🎯 目标列 '{target_col}' 分析:")
        if df[target_col].dtype in ['object', 'category']:
            print("   分布:")
            print(df[target_col].value_counts(normalize=True))
        else:
            print("   统计描述:")
            print(df[target_col].describe())

    # 收集一些关键信息供后续比较
    result = {
        'shape': df.shape,
        'missing_cols': missing[missing > 0].index.tolist(),
        'dup_rows': dup_rows,
        'numeric_cols': numeric_cols,
        'cat_cols': cat_cols
    }
    return result


def compare_train_test(train, test, target_col=None):
    """比较训练集与测试集在特征上的一致性"""
    print(f"\n{'=' * 50}\n训练集 vs 测试集 一致性检查\n{'=' * 50}")

    # 1. 列对齐
    train_cols = set(train.columns)
    test_cols = set(test.columns)
    if train_cols != test_cols:
        only_train = train_cols - test_cols
        only_test = test_cols - train_cols
        if only_train:
            print(f"⚠️ 仅在训练集中出现的列: {only_train}")
        if only_test:
            print(f"⚠️ 仅在测试集中出现的列: {only_test}")
    else:
        print("✅ 列名完全一致")

    # 2. 数值型特征分布比较（使用均值和标准差）
    common_numeric = set(train.select_dtypes(include=[np.number]).columns) & set(
        test.select_dtypes(include=[np.number]).columns)
    if common_numeric:
        print("\n数值特征分布差异（训练 vs 测试）:")
        for col in common_numeric:
            train_mean = train[col].mean()
            train_std = train[col].std()
            test_mean = test[col].mean()
            test_std = test[col].std()
            mean_diff = abs(train_mean - test_mean) / (train_std + 1e-8)  # 相对差异
            std_diff = abs(train_std - test_std) / (train_std + 1e-8)
            if mean_diff > 0.2 or std_diff > 0.2:  # 阈值可调整
                print(f"   ⚠️ {col}: 均值差异 {mean_diff:.3f}, 标准差差异 {std_diff:.3f}")
            else:
                print(f"   ✅ {col}: 分布相近")

    # 3. 类别型特征类别对齐
    common_cat = set(train.select_dtypes(include=['object', 'category']).columns) & set(
        test.select_dtypes(include=['object', 'category']).columns)
    if common_cat:
        print("\n类别特征类别对齐:")
        for col in common_cat:
            train_uniq = set(train[col].dropna().unique())
            test_uniq = set(test[col].dropna().unique())
            only_train = train_uniq - test_uniq
            only_test = test_uniq - train_uniq
            if only_train:
                print(f"   ⚠️ {col}: 训练集独有类别: {only_train}")
            if only_test:
                print(f"   ⚠️ {col}: 测试集独有类别: {only_test}")
            if not only_train and not only_test:
                print(f"   ✅ {col}: 类别完全一致")

    # 4. 目标变量在训练集中的分布（如果有）
    if target_col and target_col in train.columns:
        print(f"\n🎯 训练集目标变量 '{target_col}' 分布:")
        if train[target_col].dtype in ['object', 'category']:
            print(train[target_col].value_counts(normalize=True))
        else:
            print(train[target_col].describe())


# ----------------- 主程序 -----------------
# 请将 train.csv 和 test.csv 放在当前目录，或修改文件路径
train_df = pd.read_csv('./DataSet/Motor vehicle insurance data.csv')
test_df = pd.read_csv('./DataSet/sample type claim.csv')



# 如果有目标变量列名，请在这里指定（例如 'label', 'target' 等）
TARGET_COL = 'target'  # 修改为实际目标列名，如 'target'


# 检测训练集
train_info = inspect_dataset(train_df, 'Motor', target_col=TARGET_COL)

# 检测测试集
test_info = inspect_dataset(test_df, 'sample', target_col=TARGET_COL)

# 比较两个数据集
compare_train_test(train_df, test_df, target_col=TARGET_COL)

print("\n✅ 检测完成！请根据上述报告决定清洗与预处理策略。")

#我发现两个CSV数据文件似乎没有按照正确的csv中以逗号和回车来构成文件，而是以分号和回车来分割数据，这将会在后续机器学习中发生错误，请帮我用Python来纠正这两个文件
