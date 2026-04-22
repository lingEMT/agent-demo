# HelloAgents 迁移至 LangChain 重构计划

## Context

将智能旅行规划助手项目的基础架构从 HelloAgents 框架迁移到 LangChain 生态系统，保持核心功能不变。

**迁移原因**: LangChain 是更成熟的 AI 应用框架，拥有更丰富的工具生态、更好的文档支持和更活跃的社区。

**核心功能保留**:
- 4个专业Agent（景点搜索、天气查询、酒店推荐、行程规划）
- MCP工具集成（高德地图服务）
- 多Agent顺序协作流程
- FastAPI接口（/api/trip/plan 等）
- 数据模型和响应格式
- 单例模式管理

---

## 技术方案

### 1. 依赖变更

**移除**: `hello-agents[protocols]>=0.2.4,<=0.2.9`

**新增**:
```
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-core>=0.3.0
langgraph>=0.2.0
langchain-mcp-adapters>=0.1.0
```

### 2. LLM服务迁移

**文件**: `backend/app/services/llm_service.py`

| HelloAgents | LangChain |
|-------------|-----------|
| `HelloAgentsLLM()` | `ChatOpenAI(api_key, base_url, model)` |
| 自动读取环境变量 | 手动读取环境变量配置 |

### 3. MCP工具迁移

**文件**: `backend/app/services/amap_service.py`

| HelloAgents | LangChain |
|-------------|-----------|
| `MCPTool(name, server_command, env, auto_expand)` | `MultiServerMCPClient(config)` |
| 同步初始化 | 异步初始化 (需在 FastAPI lifespan 中调用) |
| `tool.ainvoke()` | `tool.ainvoke()` (返回 StructuredTool 列表) |

### 4. Agent系统迁移

**文件**: `backend/app/agents/trip_planner_agent.py`

| HelloAgents | LangChain/LangGraph |
|-------------|---------------------|
| `SimpleAgent(name, llm, system_prompt)` | `create_tool_calling_executor(llm, tools, prompt)` |
| `agent.add_tool(tool)` | 在 `create_tool_calling_executor` 中传入 tools |
| `agent.run(query)` | `agent.ainvoke({"messages": [...]})` |
| 顺序调用多个Agent | `StateGraph` 定义工作流节点和边 |

**注意**:
- LangChain v1.0+ 使用 `create_tool_calling_executor` 从 `langgraph.prebuilt.chat_agent_executor`
- 这是创建智能体的推荐方式，替代了旧的 `create_react_agent`

### 5. API层适配

**文件**: `backend/app/api/main.py`

添加 `lifespan` 异步上下文管理器，在启动时初始化 MCP 客户端。

**文件**: `backend/app/api/routes/trip.py`

将 `plan_trip` 改为 `async def`，使用 `await` 调用 Agent。

---

## 需要修改的文件清单

| 文件路径 | 修改类型 | 说明 |
|---------|---------|------|
| `backend/requirements.txt` | 修改 | 替换依赖 |
| `backend/app/services/llm_service.py` | 重写 | 使用 LangChain ChatOpenAI |
| `backend/app/services/amap_service.py` | 重写 | 使用 langchain-mcp-adapters |
| `backend/app/agents/trip_planner_agent.py` | 重写 | 使用 LangGraph StateGraph |
| `backend/app/api/main.py` | 修改 | 添加异步初始化 |
| `backend/app/api/routes/trip.py` | 修改 | 改为异步调用 |
| `backend/app/api/routes/map.py` | 修改 | 适配异步服务 |

---

## 实施步骤

### Step 1: 更新依赖
修改 `requirements.txt`，运行 `pip install -r requirements.txt`

### Step 2: 重写 LLM 服务
修改 `llm_service.py`，使用 `langchain_openai.ChatOpenAI`

### Step 3: 重写 MCP 服务
修改 `amap_service.py`，使用 `langchain_mcp_adapters.MultiServerMCPClient`

### Step 4: 重写 Agent 系统
修改 `trip_planner_agent.py`:
- 定义 `TripPlanningState` 状态类型
- 创建4个 `create_tool_calling_executor` 实例
- 构建 `StateGraph` 工作流
- 实现 `plan_trip` 异步方法

**注意**:
- 使用 `create_tool_calling_executor` 从 `langgraph.prebuilt.chat_agent_executor`
- 参数使用 `model`、`tools`、`prompt` 而不是 `llm`、`state_modifier`

### Step 5: 适配 API 层
- 修改 `main.py` 添加 lifespan 初始化
- 修改路由文件使用异步调用

### Step 6: 测试验证
- 启动服务测试 `/api/trip/plan` 接口
- 验证响应格式一致性
- 测试 MCP 工具调用

---

## 关键代码路径

```
backend/
├── app/
│   ├── agents/
│   │   └── trip_planner_agent.py  # 核心：多Agent协作逻辑
│   ├── services/
│   │   ├── llm_service.py         # LLM封装
│   │   └── amap_service.py        # MCP工具管理
│   ├── api/
│   │   ├── main.py                # FastAPI应用入口
│   │   └── routes/
│   │       ├── trip.py            # 旅行规划API
│   │       ├── map.py             # 地图服务API
│   │       └── poi.py             # POI服务API
│   └── models/
│       └── schemas.py             # 数据模型(不变)
```

---

## 验证方式

1. 启动后端服务: `cd backend && python run.py`
2. 访问 API 文档: `http://localhost:8000/docs`
3. 测试旅行规划接口:
```bash
curl -X POST "http://localhost:8000/api/trip/plan" \
  -H "Content-Type: application/json" \
  -d '{"city":"北京","start_date":"2026-04-10","end_date":"2026-04-12","travel_days":3,"preferences":["历史文化"],"transportation":"地铁","accommodation":"经济型"}'
```
4. 验证返回的 JSON 格式和内容是否正确

---

## 风险提示

| 风险 | 缓解措施 |
|-----|---------|
| MCP工具名称可能不同 | 打印工具列表，建立名称映射 |
| 异步兼容性问题 | 确保所有调用使用 async/await |
| LLM响应格式差异 | 增强JSON解析容错 |
