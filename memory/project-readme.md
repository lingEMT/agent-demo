# 智能旅行助手项目说明

## 项目概述

**项目名称**: 智能旅行助手
**项目定位**: 基于AI Agent的个性化旅行规划系统
**项目定位**: 基于AI Agent的个性化旅行规划系统
**项目路径**: D:\python_file\python_project\agent\helloagents-trip-planner

这是一个基于 LangChain 和 LangGraph 框架构建的智能旅行规划助手，集成高德地图MCP服务，提供个性化的旅行计划生成。

## 技术架构

### 后端技术栈
- **框架**: FastAPI + LangChain + LangGraph
- **LLM**: 支持多种LLM提供商（OpenAI, DeepSeek等） - 使用LangChain集成
- **多智能体框架**: LangGraph 状态图编排
- **地图服务**: 高德地图 Web API
- **图片服务**: Unsplash API
- **HTTP客户端**: httpx

### 前端技术栈
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI组件库**: Ant Design Vue
- **路由**: Vue Router
- **HTTP客户端**: Axios

## 项目结构

```
helloagents-trip-planner/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── agents/            # Agent实现
│   │   │   └── trip_planner_agent.py
│   │   ├── api/               # FastAPI路由
│   │   │   ├── main.py
│   │   │   └── routes/
│   │   │       ├── trip.py
│   │   │       ├── poi.py
│   │   │       └── map.py
│   │   ├── services/          # 服务层
│   │   │   ├── amap_service.py  # 高德地图服务
│   │   │   ├── llm_service.py   # LLM服务
│   │   │   └── unsplash_service.py  # Unsplash图片服务
│   │   ├── models/            # 数据模型
│   │   │   └── schemas.py
│   │   └── config.py          # 配置管理
│   ├── requirements.txt
│   ├── .env
│   └── run.py
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue       # 首页表单
│   │   │   └── Result.vue     # 结果展示页
│   │   ├── services/
│   │   │   └── api.ts         # API客户端
│   │   ├── types/
│   │   │   └── index.ts       # TypeScript类型
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 核心功能

### 1. 智能旅行规划（基于LangGraph）
- 用户输入目的地、日期、偏好等信息
- 多智能体协作系统自动生成详细的多日行程
- 包含每日景点、餐饮、住宿推荐

### 2. 高德地图集成
- **POI搜索**: 搜索景点、酒店、餐厅等
- **天气查询**: 获取目的地天气信息
- **路线规划**: 支持步行、驾车、公共交通
- **地理编码**: 地址转坐标

### 3. AI驱动（基于LangChain/LangGraph）
- 使用 LangGraph 构建多智能体协作系统
- Agent 使用 LLM 生成合理的行程建议
- Agent 自动调用地图工具获取实时信息
- 整合天气、景点、交通等多维度数据

### 4. 图片展示
- 通过 Unsplash API 获取景点图片
- 增强用户体验

## 关键组件说明

### backend/app/services/amap_service.py
- 封装高德地图 Web API
- 提供 LangChain StructuredTool 格式的工具函数：
  - `search_poi()` - 搜索POI
  - `get_weather()` - 查询天气
  - `plan_route()` - 规划路线
- 包含模拟数据降级方案

### backend/app/api/routes/poi.py
- `/api/poi/search` - 搜索POI
- `/api/poi/detail/{poi_id}` - 获取POI详情
- `/api/poi/photo` - 获取景点图片

### backend/app/models/schemas.py
- 定义了完整的数据模型
- 包括 TripRequest, TripPlan, Attraction, Meal, Hotel 等

### frontend/src/views/Home.vue
- 旅行规划表单页面
- 收集用户输入的信息

### frontend/src/views/Result.vue
- 展示生成的旅行计划
- 包含地图、天气、预算等详细信息

## 配置说明

### 环境变量 (.env)
```bash
# 高德地图API
AMAP_APP_CODE=你的高德App Code
AMAP_API_KEY=（可选）高德WebJS密钥

# Unsplash API
UNSPLASH_ACCESS_KEY=你的Unsplash访问密钥

# LLM配置（从环境变量读取）
LLM_API_KEY=你的LLM API密钥
LLM_BASE_URL=API基础URL
LLM_MODEL_ID=模型ID
```

### API端点
- `GET /` - 根路径
- `GET /health` - 健康检查
- `GET /docs` - API文档（Swagger）
- `POST /api/trip/plan` - 生成旅行计划（使用LangGraph多智能体）
- `GET /api/poi/search` - 搜索POI
- `GET /api/poi/detail/{poi_id}` - POI详情
- `GET /api/map/weather` - 天气查询
- `POST /api/map/route` - 路线规划

## 启动方式

### 后端
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python run.py
```
服务运行在 `http://localhost:8000`

### 前端
```bash
cd frontend
npm install
npm run dev
```
应用运行在 `http://localhost:5173`

## 项目特点

1. **LangGraph多智能体系统**: 基于LangGraph构建的多智能体协作，智能规划
2. **模块化架构**: 后端前后端分离，服务层清晰
3. **容错机制**: API失败时自动降级到模拟数据
4. **类型安全**: 前后端都使用TypeScript/Pydantic
5. **文档完善**: README包含详细的说明文档
6. **CORS配置**: 支持跨域请求

## 当前项目状态

从文件结构看，这是一个**已完成并运行**的项目：
- 后端有 `.env` 配置文件
- 前端有 `node_modules`，说明已安装依赖
- 有 `.pyc` 编译文件，说明后端已运行过

项目已完成以下主要功能：
✅ 基于LangGraph的多智能体旅行规划系统
✅ 高德地图API集成
✅ 前后端分离架构
✅ 完整的数据模型
✅ API文档

## 技术要点

### 数据模型 (schemas.py)
- `TripRequest`: 旅行规划请求
- `TripPlan`: 旅行计划响应
- `Attraction`: 景点信息
- `Meal`: 餐饮信息
- `Hotel`: 酒店信息
- `DayPlan`: 单日行程
- `WeatherInfo`: 天气信息
- `Budget`: 预算信息

### Agent功能
- 旅行规划助手Agent
- 自动调用高德地图工具
- 生成详细的多日行程
- 整合天气和景点信息

### API设计
- RESTful API设计
- 完整的错误处理
- 模拟数据降级机制
- 详细的API文档

### LangChain/LangGraph集成
- **LangGraph多智能体系统**: 使用状态图(State Graph)构建多智能体协作
- **工具调用**: 通过LangChain的StructuredTool集成高德地图API
- **LLM服务**: 使用langchain-openai与OpenAI/DeepSeek等模型对接
- **多智能体规划**: 智能体之间协作规划完整的旅行行程

## 依赖说明

### 后端依赖
- FastAPI
- Uvicorn
- Pydantic-settings
- python-dotenv
- httpx
- langchain-core
- langchain-openai
- langgraph
- dotenv

### 前端依赖
- Vue 3
- TypeScript
- Vite
- Ant Design Vue
- Vue Router
- Axios

## 注意事项

1. 高德地图API需要先在开放平台注册获取密钥
2. LLM API需要配置相应的密钥（支持OpenAI和DeepSeek等）
3. 确保前后端服务都能正常访问
4. 前端需要配置CORS支持
5. LangGraph多智能体系统需要配置好LLM服务，确保能正常调用

---

**项目文档生成时间**: 2026-04-13
