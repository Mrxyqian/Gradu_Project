# 当前项目系统模型配置导出

导出日期：2026-04-20

本文档汇总当前项目系统中与车辆保险理赔二分类模型相关的主要配置，包括训练超参数、网络层结构、特征工程、阈值策略与当前已发布模型的实际配置。

## 1. 配置来源

| 来源 | 说明 |
| --- | --- |
| `MLP/TrainConfig.py` | 训练配置类的代码默认值 |
| `MLP/TrainingManager.py` | 系统启动训练时对配置的覆盖逻辑 |
| `MLP/Model.py` | MLP 网络结构、残差块、分类头与损失函数定义 |
| `MLP/DataLoader.py` | 数据读取、预处理、特征工程与目标变量定义 |
| `MLP/FastAPIApp.py` | 后端训练接口请求参数默认值 |
| `vue/src/views/manager/ModelTraining.vue` | 前端训练页面表单默认值 |
| `MLP/outputs/saved_weights/claim-training-20260420132754-*.json` | 当前最近一次完成并发布的模型训练元数据 |

## 2. 当前已发布模型实际配置

当前系统中最近一次完成并发布的训练作业为：

| 项目 | 值 |
| --- | --- |
| 训练作业 ID | `20260420132754-6a846b` |
| 模型名称 | `claim-training-20260420132754-lunwen.pth` |
| 训练开始时间 | `2026-04-20T13:27:54` |
| 训练完成时间 | `2026-04-20T13:45:30` |
| 配置轮数 | `100` |
| 实际完成轮数 | `58` |
| 是否早停 | `true` |
| 早停监控指标 | `auc` |
| 最佳监控值 | `0.960419` |
| 当前分类阈值 | `0.624372` |
| 训练数据路径 | `D:\Gradua_pro_code-spring\Vehic_Insur_Claim\MLP\DataSet\train_data.csv` |

当前模型实际训练时使用的核心超参数如下：

| 配置项 | 当前已发布模型实际值 |
| --- | --- |
| `num_epochs` | `100` |
| `batch_size` | `512` |
| `optimizer` | `adamw` |
| `learning_rate` | `0.0002` |
| `weight_decay` | `0.008` |
| `beta1` | `0.9` |
| `beta2` | `0.999` |
| `eps` | `1e-8` |
| `scheduler` | `cosine_warmup` |
| `warmup_epochs` | `5` |
| `min_lr` | `1e-6` |
| `early_stop` | `true` |
| `patience` | `5` |
| `min_delta` | `5e-5` |
| `use_amp` | `true` |
| `grad_clip` | `1.0` |
| `auto_threshold` | `true` |
| `threshold_metric` | `precision` |
| `threshold_beta` | `1.3` |
| `threshold_min_recall` | `0.83` |
| `pos_weight` | `3.1` |
| `label_smoothing` | `0.05` |

## 3. 当前已发布模型网络层配置

当前已发布模型的输入维度为特征工程后的 `29` 个特征，网络主体为残差式 MLP。

| 网络部分 | 配置 |
| --- | --- |
| 模型类 | `InsuranceMLP` |
| 输入维度 | `29` |
| `hidden_dims` | `[128, 256, 256, 128, 128]` |
| `head_hidden_dim` | `32` |
| `input_dropout` | `0.05` |
| `backbone_dropout` | `0.25` |
| `head_dropout` | `0.15` |
| `head_samples` | `10` |
| 输出维度 | `1` 个 logit |
| 参数量 | `389,761` 个可训练参数 |

网络结构展开如下：

| 顺序 | 层/模块 | 结构 |
| --- | --- | --- |
| 1 | 输入 Dropout | `Dropout(0.05)` |
| 2 | 输入投影层 | `Linear(29 -> 128) + LayerNorm(128) + GELU + Dropout(0.25)` |
| 3 | 残差块 1 | `ResidualBlock(128 -> 256)` |
| 4 | 残差块 2 | `ResidualBlock(256 -> 256)` |
| 5 | 残差块 3 | `ResidualBlock(256 -> 128)` |
| 6 | 残差块 4 | `ResidualBlock(128 -> 128)` |
| 7 | 分类头 | `Linear(128 -> 32) + LayerNorm(32) + GELU + Dropout(0.15) + Linear(32 -> 1)` |
| 8 | 概率转换 | `sigmoid(logit)` |
| 9 | 标签判定 | `probability >= 0.624372` 判定为理赔 |

`ResidualBlock(in_dim -> hidden_dim)` 的内部结构为：

```text
主分支: Linear(in_dim -> hidden_dim)
      + LayerNorm(hidden_dim)
      + GELU
      + Dropout
      + Linear(hidden_dim -> hidden_dim)
      + LayerNorm(hidden_dim)

捷径分支: 如果 in_dim != hidden_dim，则使用 Linear(in_dim -> hidden_dim, bias=False)
        否则使用 Identity

输出: GELU(主分支输出 + 捷径分支输出)
```

`head_samples=10` 表示同一个分类头重复前向计算 10 次并平均 logits。它不是 10 个独立分类头，因此不会让参数量乘以 10；训练时由于 Dropout 存在，会带来类似采样平均的效果。

## 4. 代码默认训练配置

`MLP/TrainConfig.py` 中的默认配置如下。注意：系统通过页面或接口启动训练时，会在这些默认值基础上覆盖部分参数。

### 4.1 路径配置

| 配置项 | 默认值 |
| --- | --- |
| `train_table` | `D:\Gradua_pro_code-spring\Vehic_Insur_Claim\MLP\DataSet\train_data.csv` |
| `output_dir` | `D:\Gradua_pro_code-spring\Vehic_Insur_Claim\MLP\outputs` |
| `scaler_path` | `D:\Gradua_pro_code-spring\Vehic_Insur_Claim\MLP\outputs\scaler.pkl` |
| `reference_path` | `D:\Gradua_pro_code-spring\Vehic_Insur_Claim\MLP\outputs\preprocess_reference.pkl` |
| `best_model_path` | `D:\Gradua_pro_code-spring\Vehic_Insur_Claim\MLP\outputs\best_model.pth` |
| `last_model_path` | `D:\Gradua_pro_code-spring\Vehic_Insur_Claim\MLP\outputs\last_model.pth` |
| `log_dir` | `D:\Gradua_pro_code-spring\Vehic_Insur_Claim\MLP\outputs\runs` |

### 4.2 数据配置

| 配置项 | 默认值 |
| --- | --- |
| `val_ratio` | `0.15` |
| `test_ratio` | `0.10` |
| `random_seed` | `42` |
| `batch_size` | `128` |
| `num_workers` | `0` |
| `balanced_sampling` | `false` |
| `sampler_alpha` | `0.75` |

### 4.3 模型配置

| 配置项 | 默认值 |
| --- | --- |
| `input_dim` | `-1`，训练时由实际特征数覆盖 |
| `hidden_dims` | `[256, 512, 512, 256, 256]` |
| `head_hidden_dim` | `64` |
| `input_dropout` | `0.05` |
| `backbone_dropout` | `0.25` |
| `head_dropout` | `0.15` |
| `head_samples` | `10` |

### 4.4 损失函数配置

| 配置项 | 默认值 |
| --- | --- |
| 损失函数 | `BCEWithLogitsLoss` |
| `pos_weight` | `3.10` |
| `label_smoothing` | `0.05` |

标签平滑逻辑：

```text
smoothed_target = target * (1 - label_smoothing) + 0.5 * label_smoothing
```

### 4.5 优化器配置

| 配置项 | 默认值 |
| --- | --- |
| `optimizer` | `adamw` |
| `lr` | `1e-4` |
| `weight_decay` | `8e-3` |
| `beta1` | `0.9` |
| `beta2` | `0.999` |
| `eps` | `1e-8` |
| `momentum` | `0.9` |
| `nesterov` | `true` |

### 4.6 学习率调度配置

| 配置项 | 默认值 |
| --- | --- |
| `scheduler` | `cosine_warmup` |
| `warmup_epochs` | `5` |
| `min_lr` | `1e-6` |
| `plateau_factor` | `0.5` |
| `plateau_patience` | `5` |
| `plateau_min_lr` | `1e-6` |
| `step_size` | `10` |
| `gamma` | `0.5` |

### 4.7 训练过程配置

| 配置项 | 默认值 |
| --- | --- |
| `num_epochs` | `100` |
| `early_stop` | `true` |
| `patience` | `5` |
| `min_delta` | `5e-5` |
| `early_stop_metric` | `auc` |
| `use_amp` | `true` |
| `grad_clip` | `1.0` |
| `resume_from` | 空字符串 |
| `log_interval` | `100` |
| `save_every_epoch` | `false` |
| `clf_threshold` | `0.5` |
| `auto_threshold` | `true` |
| `threshold_metric` | `f1` |
| `threshold_beta` | `1.3` |
| `threshold_min_recall` | `0.830` |

## 5. 前端/API 启动训练时的默认值

系统页面或接口启动训练时，不一定完全使用 `TrainConfig.py` 的默认值。当前主要入口默认值如下：

| 配置项 | 前端训练页面默认值 | FastAPI 请求模型默认值 |
| --- | --- | --- |
| `numEpochs` | `80` | `80` |
| `batchSize` | `256` | `128` |
| `optimizer` | `adamw` | `adamw` |
| `learningRate` | `0.0002` | `0.0002` |
| `earlyStopMetric` | `auc` | `auc` |
| `thresholdMetric` | `precision` | `f1` |
| `thresholdMinRecall` | 前端会随请求传入，当前模型使用 `0.83` | `0.83` |
| `hiddenDims` | `[128, 256, 256, 128, 128]` | `[128, 256, 256, 128, 128]` |
| `headHiddenDim` | `32` | `32` |

训练管理器会先创建 `TrainConfig.Config()`，再用前端/API 请求参数覆盖配置。因此，真正训练出来的模型应以训练作业元数据中的 resolved config 为准。

## 6. 数据读取与特征工程配置

### 6.1 数据源

当前默认训练数据源为本地 CSV：

```text
D:\Gradua_pro_code-spring\Vehic_Insur_Claim\MLP\DataSet\train_data.csv
```

如果 `train_table` 是 `.csv` 文件路径或本地路径，系统会读取本地 CSV；只有当传入的是数据库表名时，才会通过 MySQL 查询读取数据。

### 6.2 目标变量

| 配置项 | 值 |
| --- | --- |
| 原始目标列 | `N_claims_year` |
| 二分类标签 | `N_claims_year > 0` 为正类，即发生理赔 |

### 6.3 日期特征工程

当前特征工程版本：

| 配置项 | 值 |
| --- | --- |
| `FEATURE_ENGINEERING_VERSION` | `2` |
| `FEATURE_ENGINEERING_STRATEGY` | `date_last_renewal_anchor` |
| 观察时点锚点列 | `Date_last_renewal` |

当前日期相关特征如下：

| 特征 | 含义 |
| --- | --- |
| `Date_start_contract_days` | 合同开始日期相对 `Date_last_renewal` 的天数差 |
| `Date_next_renewal_days` | 下次续保日期相对 `Date_last_renewal` 的天数差 |
| `Date_birth_days` | 出生日期相对 `Date_last_renewal` 的天数差 |
| `Date_driving_licence_days` | 驾照日期相对 `Date_last_renewal` 的天数差 |
| `driving_experience_years` | 驾龄，基于 `Date_last_renewal` 与 `Date_driving_licence` 计算 |
| `insured_age_years` | 被保险人年龄，基于 `Date_last_renewal` 与 `Date_birth` 计算 |
| `contract_duration_years` | 合同持续年限，基于 `Date_last_renewal` 与 `Date_start_contract` 计算 |
| `vehicle_age_years` | 车辆年龄，基于 `Date_last_renewal` 与 `Year_matriculation` 计算 |

`Date_last_renewal` 只作为每条样本自己的观察时点锚点使用，不作为最终模型输入特征直接保留。

### 6.4 当前模型输入特征列表

当前已发布模型使用 `29` 个输入特征：

| 序号 | 特征名 |
| --- | --- |
| 1 | `Distribution_channel` |
| 2 | `Seniority` |
| 3 | `Policies_in_force` |
| 4 | `Max_policies` |
| 5 | `Max_products` |
| 6 | `Lapse` |
| 7 | `Payment` |
| 8 | `Premium` |
| 9 | `N_claims_history` |
| 10 | `R_Claims_history` |
| 11 | `Type_risk` |
| 12 | `Area` |
| 13 | `Second_driver` |
| 14 | `Year_matriculation` |
| 15 | `Power` |
| 16 | `Cylinder_capacity` |
| 17 | `Value_vehicle` |
| 18 | `N_doors` |
| 19 | `Type_fuel` |
| 20 | `Length` |
| 21 | `Weight` |
| 22 | `Date_start_contract_days` |
| 23 | `Date_next_renewal_days` |
| 24 | `Date_birth_days` |
| 25 | `Date_driving_licence_days` |
| 26 | `driving_experience_years` |
| 27 | `insured_age_years` |
| 28 | `contract_duration_years` |
| 29 | `vehicle_age_years` |

### 6.5 数值裁剪与标准化

以下数值列在预处理阶段会按训练数据的 `0.999` 分位数进行上界裁剪：

```text
Premium
Value_vehicle
Power
Cylinder_capacity
Weight
Length
```

模型输入特征之后会使用 `StandardScaler` 标准化，相关对象保存在：

```text
MLP/outputs/scaler.pkl
MLP/outputs/preprocess_reference.pkl
```

## 7. 阈值搜索与推理判定

当前系统支持带 recall 下限的自动阈值搜索。当前已发布模型配置为：

| 配置项 | 值 |
| --- | --- |
| `auto_threshold` | `true` |
| `threshold_metric` | `precision` |
| `threshold_min_recall` | `0.83` |
| 最终分类阈值 | `0.624372` |

推理时不是固定使用 `0.5` 判断理赔，而是使用当前模型加载出的 `classificationThreshold`：

```text
probability >= classificationThreshold => 判定为理赔
probability < classificationThreshold  => 判定为未理赔
```

当前已发布模型中：

```text
classificationThreshold = 0.624372
```

## 8. 当前已发布模型评估指标

| 指标 | 值 |
| --- | --- |
| `loss` | `0.508877` |
| `auc` | `0.961897` |
| `prAuc` | `0.866705` |
| `accuracy` | `0.909823` |
| `balancedAccuracy` | `0.879245` |
| `f1` | `0.774194` |
| `precision` | `0.725011` |
| `recall` | `0.830534` |

混淆矩阵：

| 实际/预测 | 预测未理赔 | 预测理赔 |
| --- | ---: | ---: |
| 实际未理赔 | `7973` | `619` |
| 实际理赔 | `333` | `1632` |

## 9. 重要说明

1. `TrainConfig.py` 中的 `input_dim=-1` 是占位值，真正训练时会由数据加载后的特征数量覆盖。当前已发布模型实际输入维度是 `29`。
2. 当前训练默认数据源是本地 CSV `MLP/DataSet/train_data.csv`，不是 MySQL 中的 `train_data` 表；除非启动训练时显式传入数据库表名。
3. 前端、FastAPI 和 `TrainConfig.py` 的默认值并不完全相同。若要确认某一次训练实际使用的参数，应优先查看对应训练作业元数据。
4. 当前已发布模型使用 `threshold_metric=precision` 且 `threshold_min_recall=0.83`，因此阈值搜索目标是在 recall 不低于 0.83 的候选阈值中尽量提高 precision。
5. `head_samples=10` 会增加训练/推理中的前向计算次数，但不会增加模型参数量。
