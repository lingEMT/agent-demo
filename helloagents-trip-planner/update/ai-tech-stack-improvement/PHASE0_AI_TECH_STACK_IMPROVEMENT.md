# AI技术栈集成改进 (Phase 0)

## 概述

按照 AI 技术栈集成分析报告的建议，实施了 Phase 0 的三项改进：

1. **LLM 响应缓存** — 新增 `CacheNamespace.LLM_RESPONSE`，为 LLM 响应添加 Redis 缓存支持（1小时 TTL）
2. **结构化输出** — 用 `with_structured_output(TripPlan)` 替代手写 `_parse_response()`，消除最脆弱的代码路径
3. **Agent 模块拆分** — 将 4 个 Agent 提示词和执行逻辑提取到独立的 Skill 模块，提高可测试性和可维护性

## 新增文件

| 文件 | 说明 |
|------|------|
| `app/agents/skills/__init__.py` | 技能模块包初始化，导出全部 Skill 类 |
| `app/agents/skills/attraction_skill.py` | 景点搜索技能（提示词 + 执行逻辑） |
| `app/agents/skills/weather_skill.py` | 天气查询技能（提示词 + 执行逻辑） |
| `app/agents/skills/hotel_skill.py` | 酒店推荐技能（提示词 + 执行逻辑） |
| `app/agents/skills/planner_skill.py` | 行程规划技能（结构化输出 + LLM 缓存 + 回退逻辑） |

## 修改文件

### `app/services/cache_service.py`
- 新增 `CacheNamespace.LLM_RESPONSE = "llm:response"`
- 新增 TTL 配置：`CacheNamespace.LLM_RESPONSE: 3600`（1小时）

### `app/agents/trip_planner_agent.py`
- **移除**：4 个提示词常量（`ATTRACTION_AGENT_PROMPT` 等）→ 移至 Skill 模块
- **移除**：`_init_agents()` 方法 → 替换为 `_ensure_skills()`
- **移除**：`_build_workflow()` 方法 → 替换为 `_get_compiled_workflow()`（缓存编译结果）
- **新增**：从 `.skills` 导入 4 个 Skill 类
- **重构**：`__init__` 初始化 Skill 实例为 `None`（延迟初始化）
- **重构**：`should_reset()` 简化为检查 `attraction_skill`
- **重构**：`plan_trip_async()` 和 `plan_trip_stream()` 使用 `_ensure_skills()` + `_get_compiled_workflow()`
- **保留**：`_parse_response()` 作为回退路径
- **保留**：`_create_fallback_plan()` 作为最终兜底

### `app/api/routes/trip.py`
- 修复健康检查中的 `agent.mcp_tools` → `agent.langchain_tools`（非 MCP 协议）

## 架构变化

### 重构前
```
trip_planner_agent.py (711 行)
├── 4 个提示词常量
├── _init_agents()     ← 创建 4 个 agent executor
├── _build_workflow()  ← 4 个内嵌节点函数
└── _parse_response()  ← 脆弱的手写 JSON 解析
```

### 重构后
```
trip_planner_agent.py (~270 行，精简 60%)
├── 导入 4 个 Skill 类
├── _ensure_skills()   ← 延迟初始化技能实例
├── _get_compiled_workflow()  ← 缓存编译结果
└── _parse_response()  ← 仅作为回退保留

skills/                      ← 新增模块，可独立测试
├── attraction_skill.py       ← 景点搜索 (74 行)
├── weather_skill.py          ← 天气查询 (65 行)
├── hotel_skill.py            ← 酒店推荐 (67 行)
└── planner_skill.py          ← 行程规划 (178 行，含结构化输出 + 缓存)
```

## 关键技术决策

### 结构化输出
- 使用 `llm.with_structured_output(TripPlan, method="json_mode")` 替代 `create_tool_calling_executor`
- **主要路径**：结构化输出 → `TripPlan` 对象 → 序列化为 dict → 缓存
- **回退路径**：传统 agent executor → 文本 → `_parse_response()` 解析
- 使用 `SystemMessage` + `HumanMessage` 替代 agent executor 的 prompt 注入

### LLM 响应缓存
- 基于请求参数（城市、天数、日期、偏好等）构建缓存 key
- 使用 `CacheNamespace.LLM_RESPONSE`（1小时 TTL）
- 仅在缓存未命中时调用 LLM，降低 API 费用和延迟

### 工作流编译缓存
- `_get_compiled_workflow()` 编译一次后缓存，后续调用直接返回
- 避免每次请求都重新编译 LangGraph 工作流，提升性能

## 验证

- `plan_trip_async()` 和 `plan_trip_stream()` 保持相同的输入/输出接口
- 健康检查端点 `/trip/health` 返回 `tools_initialized` 和 `skills_initialized` 状态
- 所有错误路径保留三层兜底：结构化输出 → 文本解析 → 备用计划
