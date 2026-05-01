# 对话记忆 + 迭代式计划修改 实施记录

## 概述

实现对话记忆和迭代式计划修改功能。用户可以在计划生成后，通过自然语言对话方式提出修改要求（如"第二天改轻松点"、"加一天去故宫"），系统基于原计划进行修改并保存版本历史。

核心思路：**修改时不重新运行完整 LangGraph 工作流（4 个节点），只重新运行 planner 节点**，将原计划作为上下文注入。

## 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/services/conversation_service.py` | 对话记忆服务（单例模式），管理版本链 CRUD |
| `frontend/src/components/ChatPanel.vue` | 右侧对话面板组件，包含版本标签栏、消息列表、输入框 |

## 修改文件

### 后端

| 文件 | 变更要点 |
|------|----------|
| `backend/app/models/database.py` | TripRecord 表新增 4 列：`conversation_id`、`parent_id`、`version_number`、`modification_request` |
| `backend/app/models/schemas.py` | 新增 `ModificationRequest`、`PlanVersionInfo`、`ConversationSummary`、`ConversationListResponse` |
| `backend/app/agents/skills/planner_skill.py` | 新增 `MODIFICATION_SYSTEM_PROMPT` 和 `modify_plan()` 方法 |
| `backend/app/agents/trip_planner_agent.py` | 新增 `modify_plan_stream()` 方法；`plan_trip_stream()` 新增 `session_id` 参数，自动创建对话记录 |
| `backend/app/api/routes/trip.py` | 新增 3 个端点：`POST /plan/modify/{plan_id}/stream`、`GET /conversation/{id}`、`GET /conversations/list`；修改 `POST /plan/stream` 新增 `session_id` 查询参数 |

### 前端

| 文件 | 变更要点 |
|------|----------|
| `frontend/src/types/index.ts` | 新增 `PlanVersion`、`ChatMessage`、`ConversationSummary`、`TripPlanMeta`、`ModificationRequest` 接口 |
| `frontend/src/services/api.ts` | 新增 `modifyTripPlanStream()`、`getConversation()`、`listConversations()`；`generateTripPlanStream()` 新增 `sessionId` 参数 |
| `frontend/src/views/Home.vue` | 传递 `sessionId` 到 SSE stream；存储 `tripPlanMeta`（plan_id, conversation_id, version_number）；清理 `_meta` 再保存旧版历史记录 |
| `frontend/src/views/Result.vue` | 嵌入 ChatPanel 组件，从 2 列变为 3 列布局；新增 `onPlanChanged()` 回调更新主显示和地图 |
| `frontend/src/views/History.vue` | 新增"对话视图"标签页，展示对话卡片列表；支持点击卡片加载最新计划 |

## API 变更

### 新增端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/trip/plan/modify/{plan_id}/stream` | SSE 流式修改计划 |
| GET | `/api/trip/conversation/{conversation_id}` | 获取对话所有版本 |
| GET | `/api/trip/conversations/list` | 列出所有对话 |

### 修改端点

`POST /api/trip/plan/stream` 新增可选查询参数 `session_id`

## 版本链设计

```
TripRecord 表新增 4 列：
- conversation_id: 对话分组 ID（同一棵修改树共享）
- parent_id: 父计划 UUID，根计划为 None
- version_number: 版本号，从 1 开始递增
- modification_request: 导致此版本的修改文本

版本链示例：
v1: parent_id=None, version_number=1  （根计划）
v2: parent_id=<v1_uuid>, version_number=2, modification_request="把第二天改轻松些"
v3: parent_id=<v2_uuid>, version_number=3, modification_request="加一天去故宫"
```

## 状态覆盖

| 组件 | 空状态 | 加载中 | 流式传输中 | 错误态 |
|------|--------|--------|------------|--------|
| ChatPanel | "开始修改您的计划"占位符 | 版本历史加载 spin | 输入框禁用 + 动画 | 内联错误提示 |
| Result | "请先生成计划"空态 | - | - | - |
| History | "没有对话"空态 | spin | - | error result 组件 |

## 边界情况处理

1. 快速连续两次修改 → 前端禁用发送按钮直到流完成
2. 无 plan_data 的记录 → 返回 400
3. conversation 超过 30 版本 → 版本标签折叠到下拉
4. 从历史记录加载 deleted 计划 → 404 处理 + 提示

## 验证方案

1. 生成计划 → 确认自动创建 conversation 并显示 v1 标签
2. 输入"第二天改轻松些" → 确认 SSE stream 正常，新 v2 出现
3. 输入"加一天" → 确认天数 +1，v3 出现
4. 点击 v1 标签 → 确认显示原始计划
5. 刷新页面 → 从历史记录加载 → 确认 ChatPanel 恢复对话
6. 查看 History 页 → 确认显示对话卡片列表
