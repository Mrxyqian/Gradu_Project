# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

车险理赔预测系统 (Vehicle Insurance Claim Prediction System) — a graduation project with a three-tier architecture for managing motor insurance policies, claim records, vehicle info, and ML-based claim probability prediction.

## Running the Project

One-click startup (Windows):
```bat
start_vehic_insur_claim.bat
```

Manual startup:

```bash
# Backend (Spring Boot) — port 9090
cd springboot
mvn spring-boot:run

# Python ML service (FastAPI) — port 8000, requires conda env "gra"
conda activate gra && cd MLP && python FastAPIApp.py

# Frontend (Vue 3 + Vite) — port 5173
cd vue && npm run dev
```

MySQL database: `gra_data` on `localhost:3306` (root/123 per application.yml).

## Architecture

Three-tier architecture, all three tiers must be running:

```
Browser (Vue 3 + Element Plus + ECharts)
    │  :5173
    ▼
Spring Boot (port 9090)  ←→  MySQL (gra_data)
    │  HTTP proxy for ML endpoints
    ▼
FastAPI (port 8000)  →  PyTorch MLP model
```

**Spring Boot** is the API gateway. It handles all CRUD for business entities (via MyBatis + PageHelper) and proxies ML prediction/training requests to FastAPI using hutool HTTP client. Session-based auth with two roles: `ADMIN` and `STUDENT` (regular user). Admin-only pages: model training, user management. The `RoleEnum.java` uses "STUDENT" as the label but the actual regular users are operators in this system.

**FastAPI** runs the MLP neural network (in `MLP/`). It exposes `/predict` (single-record inference with explainability), `/training/start` (async training job management), and `/models/versions`. The Spring Boot `ModelTrainingService` syncs a `train_data` table → CSV export → FastAPI reads it for training. Trained weights are saved to `saved_weights/`.

Key Spring Boot packages:
- `controller/` — REST controllers (Auth, MotorInsurance, ClaimTypes, VehicleInfo, InsurPred, ModelTraining, Analytics, User, File)
- `service/` — business logic; `InsurPredService` calls FastAPI for predictions, `ModelTrainingService` proxies to FastAPI
- `mapper/` — MyBatis interfaces, paired with XML in `resources/mapper/`
- `entity/` — domain objects
- `common/` — `Result` wrapper, `RoleEnum`, `SessionUserUtil`, `CorsConfig`, `DateUtil`

Frontend (`vue/src/`):
- `views/manager/` — page components per business module
- `utils/request.js` — Axios instance with 401 redirect
- `utils/auth.js` — sessionStorage-based user state
- `router/index.js` — routes with admin-only guard via `meta.adminOnly`

## Important Conventions

- All API responses use `Result` wrapper (`code`, `msg`, `data`). Controllers return `Result.success(data)`.
- Frontend Axios response interceptor checks `res.code === '401'` to redirect to login on session expiry.
- Admin-only routes use `SessionUserUtil.requireAdmin(session)` in backend and `meta.adminOnly` in frontend router.
- The `BusinessAnalytics.vue` component is reused for both policy analytics and claim analytics, differentiated by `meta.analyticsSubject` route meta field.
- Model training images (loss/AUC curves) are fetched as binary from FastAPI and proxied through Spring Boot as `ResponseEntity<byte[]>`.
- The `train_data` table in MySQL must exist before training — `ModelTrainingService.ensureTrainDataTableInitialized()` creates it from a backup table if missing.
