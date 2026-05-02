# HelloAgents 智能旅行规划助手

> 基于 **FastAPI + LangChain/LangGraph + Vue 3** 的多智能体 AI 旅行规划系统。

## 项目概述

HelloAgents 智能旅行规划助手是一个由 **4 个专业 AI Agent 协作**驱动的旅行规划系统。用户只需输入目的地、日期和偏好，系统即可自动生成包含景点推荐、天气信息、酒店建议和每日行程的完整旅行计划，并支持后续的**自然语言对话修改**和**版本对比**功能。

### 核心能力

| 能力 | 说明 |
|------|------|
| 一键生成 | 输入城市、日期和偏好，AI 自动生成完整旅行计划 |
| 多智能体协作 | 4 个专业 Agent 并行工作，覆盖景点、天气、酒店、规划 |
| 对话修改 | 用自然语言修改计划（如"第二天轻松些"），无需手动编辑 |
| 版本管理 | 每次修改自动保存为新版本，支持任意版本切换和差异对比 |
| 流式生成 | SSE 实时推送生成进度，前端实时反馈，无需等待 |
| 预算管理 | 自动估算景点门票、住宿、餐饮、交通费用 |
| 地图集成 | 基于高德地图 API 的 POI 搜索、路线规划和天气查询 |
| Token 统计 | 完整的 LLM 调用量监控和费用统计面板 |
| 数据持久化 | Redis 缓存加速 + SQLite 历史记录存储 |

## 技术栈

### 前端

| 技术 | 用途 |
|------|------|
| **Vue 3** (Composition API + `<script setup>`) | 前端框架 |
| **TypeScript** | 类型安全 |
| **Ant Design Vue 4.x** | UI 组件库 |
| **Vite 6** | 构建工具 |
| **Axios** | HTTP 客户端 |
| **ECharts 5** | Token 监控图表 |
| **高德地图 JS API** | 地图展示 |
| **html2canvas + jsPDF** | 导出图片/PDF |

### 后端

| 技术 | 用途 |
|------|------|
| **FastAPI** | Web 框架 |
| **LangChain** | LLM 工具调用框架 |
| **LangGraph** | 多智能体工作流编排 |
| **SQLAlchemy 2.0** (async) | ORM 数据库操作 |
| **SQLite** (aiosqlite) | 持久化存储 |
| **Redis** | 缓存层 |
| **SSE** (Server-Sent Events) | 流式数据传输 |
| **Pydantic v2** | 数据验证 |

### 外部 API

| API | 用途 |
|-----|------|
| **OpenAI / DeepSeek / DashScope** | LLM 模型 |
| **高德地图 Web 服务 API** | POI 搜索、天气预报、路线规划 |
| **高德地图 JS API** | 前端地图展示 |
| **Unsplash API** | 景点图片 (可选) |

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Frontend (Vue 3)                           │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Home.vue │  │Result.vue│  │History.vue│  │ TokenMonitor.vue │   │
│  │ 规划表单  │  │ 计划展示  │  │ 历史记录  │  │  Token 监控      │   │
│  └────┬─────┘  └───┬──┬───┘  └────┬─────┘  └──────────────────┘   │
│       │            │  │           │                                │
│       │     ┌──────┘  └──────┐    │                                │
│       │     │  ChatPanel.vue  │    │                                │
│       │     │  (对话修改/版本)  │    │                                │
│       │     └──────┬─────────┘    │                                │
│       │            │              │                                │
│       │     ┌──────┴─────────┐    │                                │
│       │     │VersionDiff.vue │    │                                │
│       │     │  (版本差异对比)  │    │                                │
│       │     └────────────────┘    │                                │
│  ┌────┴──────────────────────────────┐                              │
│  │         api.ts (Axios + SSE)      │                              │
│  └───────────────────────────────────┘                              │
├────────────────────┬────────────────────────────────────────────────┤
│                    │  HTTP / SSE                                     │
├────────────────────┴────────────────────────────────────────────────┤
│                          Backend (FastAPI)                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    API Routes (/api/*)                        │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────┐ ┌──────────────┐ ┌─────┐ │  │
│  │  │ trip/*  │ │ history/*│ │map/* │ │token-monitor/*│ │cache/*│ │  │
│  │  │ 旅行规划  │ │ 历史记录  │ │ 高德  │ │ Token 监控   │ │缓存管│ │  │
│  │  └────┬────┘ └──────────┘ └──────┘ └──────────────┘ └─────┘ │  │
│  └───────┼──────────────────────────────────────────────────────┘  │
│          │                                                         │
│  ┌───────┴──────────────────────────────────────────────────────┐  │
│  │          MultiAgentTripPlanner (LangGraph StateGraph)         │  │
│  │                                                               │  │
│  │                    ┌──────────────────┐                       │  │
│  │                    │ AttractionSkill  │                       │  │
│  │                    │  (景点搜索/POI)   │                       │  │
│  │                    └────────┬─────────┘                       │  │
│  │                             │                                 │  │
│  │              ┌──────────────┼──────────────┐                  │  │
│  │              ▼              ▼              ▼                  │  │
│  │  ┌──────────────────┐ ┌──────────┐ ┌──────────────┐          │  │
│  │  │  WeatherSkill    │ │ 并行执行  │ │  HotelSkill  │          │  │
│  │  │  (天气查询)       │ │          │ │  (酒店推荐)   │          │  │
│  │  └────────┬─────────┘ │          │ └──────┬───────┘          │  │
│  │           └────────────┼──────────┼────────┘                  │  │
│  │                        ▼          ▼                           │  │
│  │                  ┌──────────────────┐                         │  │
│  │                  │   PlannerSkill   │                         │  │
│  │                  │  (行程规划/JSON)  │                         │  │
│  │                  └──────────────────┘                         │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      服务层                                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │  │
│  │  │AmapService│ │LlService │ │CacheSvc │ │ConvService     │  │  │
│  │  │ 高德地图   │ │ LLM      │ │ Redis   │ │ 对话版本管理   │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────┬────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │           │  │
│  │  │HistSvc   │ │TokenTrack│ │Unsplash  │        ▼           │  │
│  │  │ SQLite   │ │ Token统计 │ │ 图片搜索 │  ┌──────────┐      │  │
│  │  └──────────┘ └──────────┘ └──────────┘  │ SQLAlchemy│      │  │
│  │                                          └──────────┘      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 工作流说明

1. **用户输入** → 在 Home 页面填写城市、日期、偏好等信息
2. **景点搜索** → AttractionSkill 调用高德 POI 搜索 API，查找目标景点
3. **并行查询** → WeatherSkill 查天气 + HotelSkill 查酒店（同时进行）
4. **行程规划** → PlannerSkill 整合所有信息，LLM 生成结构化 JSON 计划
5. **流式返回** → SSE 实时推送每个阶段的进度和结果到前端
6. **展示修改** → Result 页面展示计划，ChatPanel 支持对话修改生成新版本

## 功能详解

### 1. 旅行计划生成

在首页填写旅行需求表单：

- **目的地 & 日期**：选择城市、出发/结束日期，自动计算旅行天数
- **交通 & 住宿偏好**：选择交通方式和住宿类型
- **兴趣偏好**：选择自然风光、人文历史、美食探索等多种偏好标签
- **自由输入**：额外的特殊要求（如 "带老人出行，节奏要慢"）

支持**同步**和**SSE 流式**两种生成方式，流式模式实时展示各 Agent 的工作进度。

### 2. 对话式修改

在 Result 页面的 ChatPanel 中，通过自然语言与 AI 对话修改计划：

- **输入示例**："第二天轻松些，少安排两个景点"
- **输入示例**："帮我换一个离故宫近的酒店"
- **输入示例**："增加一天的预算到 3000"
- 每次修改自动生成新版本，保留完整修改历史

### 3. 版本管理与对比

- 所有版本在 ChatPanel 顶部以标签形式展示（v1, v2, v3...）
- 点击标签即**切换显示**该版本的完整计划
- 点击"比较版本"按钮，在**模态框**中以 diff 视图对比两个版本的差异：
  - **概览对比**：天数、日期、城市变化 + 预算分类对比（带差额）
  - **每日对比**：各天景点增减、餐饮变化、住宿交通变更
  - **颜色编码**：绿色=新增、红色=移除、蓝色=修改

### 4. Token 调用监控

在 TokenMonitor 页面可查看完整的 LLM 使用统计：

- 总请求数、总 Token 数、总费用
- 7 日趋势折线图
- 各模型用量排行
- 错误统计
- Token 消耗排名

### 5. 历史记录

在 History 页面：

- **记录模式**：展示已保存的旅行计划列表
- **对话模式**：按对话分组，展示每个对话的版本链
- 支持加载历史计划到 Result 页面继续修改

### 6. 导出功能

- 将旅行计划导出为**图片** (html2canvas)
- 将旅行计划导出为 **PDF** (jsPDF)

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- Redis（可选，用于缓存加速）
- 高德地图 Web 服务 API Key（**必需**）
- LLM API Key（OpenAI / DeepSeek / DashScope 等兼容接口）

### 1. 克隆项目

```bash
git clone <repository-url>
cd helloagents-trip-planner
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

编辑 `backend/.env` 配置文件：

```ini
# === 高德地图配置（必需）===
AMAP_APP_CODE=your_amap_web_service_key

# === LLM 配置（必需）===
LLM_API_KEY=your_llm_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus

# === 服务器配置 ===
HOST=0.0.0.0
PORT=8000

# === Redis 配置（可选）===
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_ENABLED=true

# === 数据库配置 ===
TRIP_DB_URL=sqlite+aiosqlite:///./data/trip_planner.db
```

### 3. 启动后端

```bash
cd backend
python run.py
```

后端服务启动在 `http://localhost:8000`。API 文档地址：`http://localhost:8000/docs`

### 4. 前端配置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端开发服务器启动在 `http://localhost:5173`，自动代理 `/api` 请求到后端。

### 5. 访问应用

打开浏览器访问 `http://localhost:5173`，即可使用。

## 项目结构

```
helloagents-trip-planner/
├── CLAUDE.md                        # 项目开发规范
├── README.md                        # 本文件
│
├── backend/                         # 后端 (FastAPI)
│   ├── .env                         # 环境变量配置
│   ├── run.py                       # 启动入口
│   ├── requirements.txt             # Python 依赖
│   │
│   ├── app/
│   │   ├── config.py                # 配置管理 (Pydantic Settings)
│   │   │
│   │   ├── api/                     # API 路由层
│   │   │   ├── main.py              # FastAPI 应用入口
│   │   │   └── routes/
│   │   │       ├── trip.py          # 旅行规划 API
│   │   │       ├── history.py       # 历史记录 API
│   │   │       ├── map.py           # 高德地图代理 API
│   │   │       ├── poi.py           # POI 详情/图片 API
│   │   │       ├── token_monitor.py # Token 监控 API
│   │   │       └── cache_admin.py   # 缓存管理 API
│   │   │
│   │   ├── agents/                  # AI Agent 层
│   │   │   ├── trip_planner_agent.py # 多智能体编排 (LangGraph)
│   │   │   └── skills/
│   │   │       ├── attraction_skill.py  # 景点搜索 Agent
│   │   │       ├── weather_skill.py     # 天气查询 Agent
│   │   │       ├── hotel_skill.py       # 酒店推荐 Agent
│   │   │       └── planner_skill.py     # 行程规划 Agent
│   │   │
│   │   ├── services/                # 服务层
│   │   │   ├── amap_service.py      # 高德地图 API 封装
│   │   │   ├── llm_service.py       # LLM 初始化与配置
│   │   │   ├── llm_monitor.py       # LLM Token 监控回调
│   │   │   ├── token_usage_tracker.py # Token 用量追踪
│   │   │   ├── cache_service.py     # Redis 缓存服务
│   │   │   ├── conversation_service.py # 对话版本管理
│   │   │   ├── history_service.py   # 历史记录持久化
│   │   │   └── unsplash_service.py  # Unsplash 图片搜索
│   │   │
│   │   ├── models/                  # 数据模型
│   │   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   │   └── database.py          # SQLAlchemy ORM 模型
│   │   │
│   │   └── core/
│   │       └── database.py          # 数据库引擎与会话管理
│   │
│   ├── alembic/                     # 数据库迁移
│   └── data/                        # SQLite 数据文件
│
├── frontend/                        # 前端 (Vue 3)
│   ├── .env                         # 环境变量
│   ├── index.html                   # HTML 入口
│   ├── package.json                 # 依赖配置
│   ├── tsconfig.json                # TypeScript 配置
│   ├── vite.config.ts               # Vite 构建配置
│   │
│   └── src/
│       ├── main.ts                  # Vue 应用入口 + 路由
│       ├── App.vue                  # 根组件 (导航布局)
│       │
│       ├── types/
│       │   └── index.ts             # TypeScript 类型定义
│       │
│       ├── services/
│       │   └── api.ts               # Axios HTTP + SSE 流式请求
│       │
│       ├── views/
│       │   ├── Home.vue             # 首页 - 旅行规划表单
│       │   ├── Result.vue           # 结果页 - 计划展示/修改/导出
│       │   ├── History.vue          # 历史记录页
│       │   └── TokenMonitor.vue     # Token 监控仪表盘
│       │
│       └── components/
│           ├── ChatPanel.vue        # 对话修改面板 + 版本管理
│           └── VersionDiff.vue      # 版本差异对比组件
│
└── update/                          # 更新记录
    └── ...
```

## API 文档

### 旅行规划 API (Trip Planning)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/trip/plan` | 生成旅行计划（同步返回） |
| POST | `/api/trip/plan/stream` | 流式生成旅行计划（SSE） |
| POST | `/api/trip/plan/modify/{plan_id}/stream` | 对话修改计划（SSE） |
| GET | `/api/trip/conversation/{conversation_id}` | 获取对话所有版本 |
| GET | `/api/trip/conversations/list` | 列出所有对话 |
| GET | `/api/trip/health` | 服务健康检查 |

### 历史记录 API (History)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/history/save` | 保存旅行记录 |
| GET | `/api/history/list` | 分页列出记录 |
| GET | `/api/history/{record_id}` | 获取记录详情 |
| DELETE | `/api/history/{record_id}` | 删除记录 |

### 高德地图 API (Map)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/map/poi` | 搜索 POI |
| GET | `/api/map/weather` | 查询天气 |
| POST | `/api/map/route` | 规划路线 |
| GET | `/api/map/health` | 地图服务健康检查 |

### Token 监控 API (Token Monitor)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/token-monitor/summary` | 用量汇总 |
| GET | `/api/token-monitor/stats` | 按时间范围统计 |
| GET | `/api/token-monitor/daily` | 每日统计 |
| GET | `/api/token-monitor/models` | 各模型统计 |
| GET | `/api/token-monitor/errors` | 错误统计 |
| GET | `/api/token-monitor/breakdown` | 用量明细 |
| GET | `/api/token-monitor/top-tokens` | Token 消耗排行 |
| DELETE | `/api/token-monitor/cleanup` | 清理旧数据 |

### 缓存管理 API (Cache)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/cache/health` | 缓存健康检查 |
| GET | `/api/cache/stats` | 缓存统计 |
| POST | `/api/cache/clear` | 清空所有缓存 |
| POST | `/api/cache/clear/{namespace}` | 清空指定命名空间 |

启动后端后，完整的 Swagger 文档可访问 `http://localhost:8000/docs`。

## 配置参考

### 核心配置项 (backend/.env)

| 环境变量 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `AMAP_APP_CODE` | 是 | - | 高德地图 Web 服务 API Key |
| `AMAP_API_KEY` | 否 | - | 高德地图 JS API Key（前端地图用） |
| `LLM_API_KEY` | 是 | - | LLM API Key |
| `LLM_BASE_URL` | 否 | - | LLM API 基础 URL |
| `LLM_MODEL` | 否 | - | LLM 模型名称 |
| `HOST` | 否 | 0.0.0.0 | 服务器监听地址 |
| `PORT` | 否 | 8000 | 服务器端口 |
| `CORS_ORIGINS` | 否 | localhost:5173,... | 允许的 CORS 域名 |
| `REDIS_HOST` | 否 | localhost | Redis 地址（空=禁用） |
| `REDIS_PORT` | 否 | 6379 | Redis 端口 |
| `REDIS_ENABLED` | 否 | true | 缓存总开关 |
| `TRIP_DB_URL` | 否 | sqlite+aiosqlite:///./data/trip_planner.db | 数据库连接 URL |
| `LOG_LEVEL` | 否 | INFO | 日志级别 |

> **提示：** 也支持通过系统环境变量设置。环境变量名与配置项名相同（大写、下划线分隔）。

### 缓存命名空间与 TTL

| 命名空间 | 默认 TTL | 用途 |
|----------|---------|------|
| `poi_search` | 24 小时 | POI 搜索结果 |
| `weather` | 30 分钟 | 天气预报 |
| `route` | 10-30 分钟 | 路线规划 |
| `poi_detail` | 24 小时 | POI 详情 |
| `geocode` | 7 天 | 地理编码 |
| `llm_response` | 1 小时 | LLM 响应缓存 |

## 开发指南

### 开发环境

推荐使用以下工具：

- **Python**：使用 venv 虚拟环境管理依赖
- **Node.js**：使用 npm 管理前端依赖
- **Git**：遵循语义化提交信息

### 本地开发

```bash
# 终端 1：启动后端
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python run.py

# 终端 2：启动前端
cd frontend
npm run dev
```

后端热重载已启用（`reload=True`），前端 Vite 自带 HMR。

### 构建生产版本

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist/` 目录，可部署到任意静态文件服务器。

### 添加新 Agent

1. 在 `backend/app/agents/skills/` 下创建新的 Skill 文件
2. 在 `trip_planner_agent.py` 中的 `StateGraph` 添加新节点
3. 定义新节点与前/后节点的连接边
4. 在 SSE 流中添加新节点的事件类型

### 添加新 API 路由

1. 在 `backend/app/api/routes/` 下创建新的路由文件
2. 在 `backend/app/api/main.py` 中注册路由
3. 在 `frontend/src/services/api.ts` 中添加对应的 HTTP 请求函数

## 常见问题

### 1. 启动后端时报 "AMAP_APP_CODE未配置"

在 `backend/.env` 中配置正确的高德地图 Web 服务 API Key。如果没有，可前往 [高德开放平台](https://lbs.amap.com/) 申请。

### 2. 前端请求后端报跨域错误

检查 `backend/.env` 中的 `CORS_ORIGINS` 是否包含前端地址。默认已包含 `localhost:5173`。

### 3. Redis 连接失败

如果未安装 Redis，将 `REDIS_ENABLED` 设为 `false` 即可禁用缓存，系统会自动降级。

### 4. LLM 调用失败

检查 `LLM_API_KEY` 和 `LLM_BASE_URL` 是否正确。支持任何兼容 OpenAI SDK 格式的 API。

## 更新记录

详见 [update/](./update/) 目录下的记录文件。

## 许可证

本项目仅供学习和参考使用。
