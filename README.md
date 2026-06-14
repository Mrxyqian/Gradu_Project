# 车险理赔预测系统 (Vehicle Insurance Claim Prediction System)

基于机器学习的车险理赔预测与管理系统，采用前后端分离的三层架构，集成 PyTorch 深度学习模型实现理赔概率预测与可解释性分析。

## 系统架构

```
浏览器 (Vue 3 + Element Plus + ECharts)        :5173
    │
    ▼
Spring Boot (API 网关)                          :9090  ←→  MySQL (gra_data)
    │
    ▼ HTTP 代理
FastAPI (ML 推理服务)                            :8000  →  PyTorch MLP 模型
```

- **前端**：Vue 3 + Element Plus + ECharts，负责数据展示与交互
- **后端**：Spring Boot 作为 API 网关，处理所有业务 CRUD 并代理 ML 请求
- **ML 服务**：FastAPI 运行残差式 MLP 神经网络，提供预测、训练与可解释性分析

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Vue 3 + Vue Router 4 | ^3.3.4 |
| UI 组件库 | Element Plus | ^2.4.2 |
| 图表库 | ECharts | ^6.0.0 |
| 构建工具 | Vite | ^4.4.11 |
| 后端框架 | Spring Boot | 2.5.9 |
| Java 版本 | JDK | 1.8 |
| ORM | MyBatis + PageHelper | 2.2.1 / 1.4.6 |
| 工具库 | Hutool | 5.8.18 |
| ML 框架 | PyTorch | >=2.0 |
| ML 服务 | FastAPI + Uvicorn | >=0.100 |
| 数据库 | MySQL | 8.x |

## 项目结构

```
Vehic_Insur_Claim/
├── vue/                          # 前端 (Vue 3)
│   └── src/
│       ├── views/                # 页面组件
│       │   ├── Login.vue        # 登录页
│       │   ├── MainLayout.vue   # 管理后台主布局
│       │   └── manager/         # 业务模块页面
│       │       ├── Home.vue              # 首页仪表盘
│       │       ├── MotorInsurance.vue    # 车险保单管理
│       │       ├── ClaimTypes.vue        # 理赔类型管理
│       │       ├── VehicleInfo.vue       # 车辆信息管理
│       │       ├── PredictionManage.vue  # 预测管理
│       │       ├── PredictionStatistics.vue  # 预测统计
│       │       ├── BusinessAnalytics.vue # 业务分析 (保单/理赔统计复用)
│       │       ├── ModelTraining.vue     # 模型训练 (仅管理员)
│       │       ├── ModelTrainingResult.vue  # 训练结果详情
│       │       └── UserManage.vue        # 用户管理 (仅管理员)
│       ├── router/index.js       # 路由定义 (含权限守卫)
│       └── utils/
│           ├── request.js        # Axios 封装 (401 自动跳转登录)
│           └── auth.js           # sessionStorage 用户状态管理
│
├── springboot/                   # 后端 (Spring Boot)
│   └── src/main/java/com/example/
│       ├── controller/          # REST 控制器 (9个)
│       │   ├── AuthController          # 认证登录
│       │   ├── MotorInsuranceController # 车险保单 CRUD
│       │   ├── ClaimTypesController     # 理赔类型 CRUD
│       │   ├── VehicleInfoController    # 车辆信息 CRUD
│       │   ├── InsurPredController      # 理赔预测
│       │   ├── ModelTrainingController  # 模型训练管理
│       │   ├── AnalyticsController      # 数据分析
│       │   ├── UserController           # 用户管理
│       │   └── FileController           # 文件上传/下载
│       ├── service/              # 业务逻辑层
│       ├── mapper/               # MyBatis 接口 + XML 映射
│       ├── entity/               # 领域实体与 DTO
│       ├── common/               # 统一响应、角色枚举、Session 工具、跨域配置
│       └── exception/            # 全局异常处理
│
├── MLP/                          # ML 服务 (FastAPI + PyTorch)
│   ├── FastAPIApp.py             # FastAPI 应用入口 (9个 API 端点)
│   ├── Model.py                  # InsuranceMLP 残差式神经网络
│   ├── InferenceService.py      # 推理服务 (预测 + 可解释性 + 多版本管理)
│   ├── DataLoader.py             # 数据加载与特征工程
│   ├── TrainModel.py             # 模型训练流程
│   ├── TrainingManager.py        # 异步训练任务管理
│   ├── TrainConfig.py            # 训练超参数配置
│   ├── DataSet/                  # 数据集 (CSV)
│   ├── ablation/                 # 消融实验 (组件/不平衡/结构)
│   ├── benchmark/                # 基准测试 (MLP vs FT-Transformer)
│   └── outputs/                  # 模型权重与训练产物
│
├── sql/                          # 数据库迁移脚本 (按日期命名)
├── docs/diagrams/                # 系统架构图、E-R 图、流程图
└── start_vehic_insur_claim.bat   # 一键启动脚本 (Windows)
```

## 快速开始

### 环境要求

- JDK 1.8+
- Node.js 16+
- Python 3.9+ (推荐使用 Conda)
- MySQL 8.x

### 数据库配置

创建数据库并导入表结构：

```sql
CREATE DATABASE gra_data DEFAULT CHARSET utf8mb4;
```

数据库连接配置位于 `springboot/src/main/resources/application.yml`，默认账号 `root/123`，端口 `3306`。SQL 迁移脚本位于 `sql/` 目录，按日期顺序执行。

### 一键启动 (Windows)

```bat
start_vehic_insur_claim.bat
```

### 手动启动

**1. 启动后端 (Spring Boot, 端口 9090)**

```bash
cd springboot
mvn spring-boot:run
```

**2. 启动 ML 服务 (FastAPI, 端口 8000)**

```bash
conda activate gra
cd MLP
pip install -r requirements-fastapi.txt
python FastAPIApp.py
```

**3. 启动前端 (Vue 3, 端口 5173)**

```bash
cd vue
npm install
npm run dev
```

启动后访问 `http://localhost:5173` 即可进入系统。

## 核心功能

### 业务管理

- **保单管理**：车险保单的增删改查、分页查询、数据导出
- **理赔类型管理**：理赔类型字典维护
- **车辆信息管理**：车辆基本信息的录入与管理
- **业务分析**：保单与理赔的多维统计分析（ECharts 可视化）
- **用户权限**：基于 Session 的角色认证，支持管理员 (`ADMIN`) 和普通用户 (`STUDENT`) 两种角色

### 机器学习

- **理赔预测**：输入保单特征，输出理赔概率与风险等级 (LOW / MEDIUM / HIGH)
- **可解释性分析**：基于逐特征消融的局部解释，返回风险提升因素与缓释因素，生成中文自然语言摘要
- **模型训练**：管理员可在线发起训练任务，配置超参数（层数、宽度、学习率、优化器等），实时查看训练曲线（Loss / AUC）
- **多版本管理**：训练产物按版本保存，支持版本切换与回滚

### ML 模型详情

**模型架构**：残差式 MLP (InsuranceMLP)

```
Input (26 features)
  → InputDropout(0.05)
  → LinearProjection + LayerNorm + GELU
  → ResidualBlock(256→512) × 4   [LayerNorm + GELU + Dropout(0.25)]
  → ClassificationHead(64)        [LayerNorm + GELU + Dropout(0.15)]
  → Logit (蒙特卡罗 Dropout ×10 取均值)
```

- **损失函数**：BCEWithLogits + 正样本加权 (pos_weight=3.10) + 标签平滑 (0.05)
- **优化器**：AdamW (lr=1e-4, weight_decay=8e-3)
- **调度器**：Cosine Annealing with Warmup (5 epochs)
- **自动阈值**：基于 F1-beta (beta=1.3) 最优化，约束召回率 >= 0.83
- **特征工程**：以最近续保日期为锚点，将原始日期转换为年龄/经验/时长等语义特征

### API 端点 (FastAPI)

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/predict` | 单条保单理赔预测 (含可解释性) |
| GET | `/models/versions` | 查询可用模型版本 |
| POST | `/training/start` | 启动训练任务 |
| GET | `/training/jobs/latest` | 获取最新训练任务状态 |
| GET | `/training/jobs/{job_id}` | 获取指定训练任务详情 |
| POST | `/training/jobs/{job_id}/save-weights` | 保存训练权重 |
| GET | `/training/jobs/{job_id}/figures/{key}` | 获取训练曲线图 |

## 关键设计约定

- **统一响应格式**：所有 API 返回 `Result` 包装 (`code`, `msg`, `data`)
- **认证机制**：Session 会话管理，前端 Axios 拦截 `code === '401'` 自动跳转登录页
- **权限控制**：后端通过 `SessionUserUtil.requireAdmin()` 校验，前端通过路由 `meta.adminOnly` 守卫
- **组件复用**：`BusinessAnalytics.vue` 通过 `meta.analyticsSubject` 路由元信息区分保单统计与理赔统计
- **训练数据同步**：Spring Boot `ModelTrainingService` 将 `train_data` 表导出为 CSV，FastAPI 读取进行训练
- **模型训练图片**：训练曲线 (Loss/AUC) 由 FastAPI 生成，Spring Boot 以 `ResponseEntity<byte[]>` 代理转发

## 实验与评估

- **消融实验** (`MLP/ablation/`)：组件消融、不平衡处理策略、网络结构敏感性分析
- **基准测试** (`MLP/benchmark/`)：残差 MLP vs FT-Transformer (Gorishniy et al., NeurIPS 2021) 对比
- **评估指标**：AUC、PR-AUC、F1、Precision、Recall、Accuracy、Balanced Accuracy
