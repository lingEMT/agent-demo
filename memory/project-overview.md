# HelloAgents 智能旅行助手项目

## 项目概述
基于HelloAgents框架构建的智能旅行规划助手，集成高德地图MCP服务，提供个性化的旅行计划生成。

## 技术栈

### 后端
- **框架**: HelloAgents (基于SimpleAgent)
- **API**: FastAPI
- **MCP工具**: amap-mcp-server (高德地图)
- **LLM**: 支持OpenAI、DeepSeek等

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI组件库**: Ant Design Vue
- **地图服务**: 高德地图 JavaScript API

## 项目结构

```
helloagents-trip-planner/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── agents/            # Agent实现
│   │   │   └── trip_planner_agent.py  # 多智能体旅行规划系统
│   │   ├── api/               # FastAPI路由
│   │   │   ├── main.py
│   │   │   └── routes/
│   │   │       ├── trip.py
│   │   │       └── map.py
│   │   ├── services/          # 服务层
│   │   │   ├── llm_service.py
│   │   │   └── amap_service.py
│   │   ├── models/            # 数据模型
│   │   │   └── schemas.py
│   │   └── config.py          # 配置管理
│   └── requirements.txt
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── services/          # API服务
│   │   │   └── api.ts
│   │   ├── views/             # 页面视图
│   │   │   ├── Home.vue
│   │   │   └── Result.vue
│   │   └── App.vue
│   └── package.json
└── README.md
```

## 核心组件

### 1. 多智能体系统
位于 `backend/app/agents/trip_planner_agent.py`

**Agent组成**:
- **景点搜索专家**: 使用MCP工具搜索景点POI
- **天气查询专家**: 查询城市天气信息
- **酒店推荐专家**: 搜索推荐酒店
- **行程规划专家**: 整合信息生成详细旅行计划

**工具调用**:
- `maps_text_search`: 搜索景点POI
- `maps_weather`: 查询天气
- `maps_direction_walking_by_address`: 步行路线
- `maps_direction_driving_by_address`: 驾车路线
- `maps_direction_transit_integrated_by_address`: 公共交通路线

### 2. MCP集成
使用 `MCPTool` 从 `hello_agents.tools` 导入，通过 `uvx amap-mcp-server` 启动MCP服务器。

### 3. 数据模型
- `TripRequest`: 旅行请求参数
- `TripPlan`: 旅行计划结果
- `DayPlan`: 每日行程
- `Attraction`: 景点信息
- `Meal`: 餐饮推荐
- `WeatherInfo`: 天气信息
- `Hotel`: 酒店信息

## 配置要求
- Python 3.10+
- Node.js 16+
- 高德地图API Key (Web服务API和Web端JS API)
- LLM API Key (OpenAI/DeepSeek等)

## 主要API端点
- `POST /api/trip/plan` - 生成旅行计划
- `GET /api/map/poi` - 搜索POI
- `GET /api/map/weather` - 查询天气
- `POST /api/map/route` - 规划路线
- `GET /docs` - API文档
