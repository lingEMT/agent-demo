# 持久化数据方案 - 保存过往旅行记录

## 概述

为项目引入 SQLite + SQLAlchemy 数据库持久化层，保存用户的旅行历史记录，支持查看、加载、删除过往计划。

## 新增文件（6个）

| 文件 | 用途 |
|------|------|
| `backend/app/core/__init__.py` | 核心模块初始化 |
| `backend/app/core/database.py` | SQLAlchemy 异步引擎、会话管理、生命周期 |
| `backend/app/models/database.py` | SQLAlchemy ORM 模型定义（TripRecord + TokenUsageRecord） |
| `backend/app/services/history_service.py` | 历史记录 CRUD 业务逻辑（单例模式） |
| `backend/app/api/routes/history.py` | 历史记录 API 路由（4个端点） |
| `frontend/src/views/History.vue` | 历史记录页面（表格展示、加载、删除） |

## 修改文件（9个）

| 文件 | 变更要点 |
|------|----------|
| `backend/requirements.txt` | 添加 `sqlalchemy[asyncio]>=2.0.0`, `aiosqlite>=0.20.0` |
| `backend/app/config.py` | 添加 `database_url`, `database_auto_create` 配置项 |
| `backend/app/models/__init__.py` | 导出 `TripRecord`, `TokenUsageRecord` |
| `backend/app/api/main.py` | lifespan 注册 `init_db()` / `close_db()`；注册 history 路由 |
| `frontend/src/types/index.ts` | 新增 `TripRecordSummary`, `TripRecordDetail` 等接口 |
| `frontend/src/services/api.ts` | 新增 `saveTripRecord()`, `listTripRecords()` 等4个函数 |
| `frontend/src/views/Home.vue` | `onMounted` 生成 session_id；`onFinalResult` fire-and-forget 保存 |
| `frontend/src/main.ts` | 添加 `/history` 路由 → `History.vue` |
| `frontend/src/App.vue` | 导航栏添加 "历史记录" 菜单项 |

## 核心设计

### 数据库
- **引擎**: SQLite + SQLAlchemy async + aiosqlite
- **存储**: JSON Blob 单表（TripRecord），避免多表关联和 Schema 迁移
- **位置**: `backend/data/trip_planner.db`（已加入 .gitignore）

### 身份标识
- 前端 `localStorage` 生成 UUID v4 作为 `session_id`
- 无需用户系统即可区分不同用户

### 数据流
1. 用户生成计划 → SSE 流返回 → `onFinalResult`:
   - `sessionStorage.set('tripPlan', plan)` → 导航到 `/result`（保持现有逻辑）
   - `POST /api/history/save` fire-and-forget → `.catch()` 静默处理
2. 用户查看历史 → `GET /api/history/list?session_id=xxx` → 展示列表
3. 用户加载历史 → `GET /api/history/{id}` → `sessionStorage.set` → 导航到 `/result`

### API 端点
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/history/save` | 保存计划（Query 参数） |
| GET | `/api/history/list` | 列表（分页） |
| GET | `/api/history/{record_id}` | 详情 |
| DELETE | `/api/history/{record_id}` | 删除 |

## 依赖变更

### 新增依赖
- `sqlalchemy[asyncio]>=2.0.0`
- `aiosqlite>=0.20.0`

## 配置说明

在 `.env` 中添加（可选，有默认值）：
```env
# 数据库（默认使用 SQLite）
TRIP_DB_URL=sqlite+aiosqlite:///./data/trip_planner.db
DATABASE_AUTO_CREATE=True
```

## 验证方法

1. 启动后端 → 日志显示数据库初始化成功，`backend/data/trip_planner.db` 文件创建
2. 生成旅行计划 → 控制台无 save 相关错误
3. 访问 `/history` → 能看到刚生成的计划记录
4. 点击加载 → 成功导航到 `/result` 并显示完整计划
5. 删除记录 → 记录消失
6. 重启后端 → 数据依然存在
