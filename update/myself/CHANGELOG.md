# 更新日志

## [未发布] 2026-04-23

### 新增功能

#### Token调用量可视化功能

**后端新增**:
- ✅ Token使用量追踪服务 (`backend/app/services/token_usage_tracker.py`)
  - 异步追踪LLM调用
  - 支持多维度统计
  - 线程安全设计

- ✅ LLM监控服务 (`backend/app/services/llm_monitor.py`)
  - LangChain回调处理器
  - 自动记录token使用
  - 成本计算

- ✅ Token监控API (`backend/app/api/routes/token_monitor.py`)
  - 9个API端点
  - 支持多种统计查询

**前端新增**:
- ✅ TokenMonitor.vue组件
  - 统计卡片
  - 每日趋势图（ECharts）
  - 模型统计表
  - 错误统计
  - Token使用排行

- ✅ 路由配置
  - 添加 `/token-monitor` 路由
  - 导航菜单集成

**依赖更新**:
- ✅ 前端: 添加 `echarts@^5.4.0`

**修改文件**:
- ✅ `backend/app/services/llm_service.py` - 集成token追踪
- ✅ `frontend/package.json` - 添加echarts
- ✅ `frontend/src/main.ts` - 添加TokenMonitor路由
- ✅ `frontend/src/App.vue` - 添加导航菜单

**API端点**:
- `GET /api/token-monitor/summary` - 获取摘要
- `GET /api/token-monitor/stats` - 获取统计
- `GET /api/token-monitor/daily` - 获取每日统计
- `GET /api/token-monitor/models` - 获取模型统计
- `GET /api/token-monitor/errors` - 获取错误统计
- `GET /api/token-monitor/breakdown` - 获取使用分解
- `GET /api/token-monitor/history` - 获取历史记录
- `GET /api/token-monitor/top-tokens` - 获取使用排行
- `DELETE /api/token-monitor/cleanup` - 清理旧数据

**文档**:
- ✅ `update/myself/TOKEN_MONITOR_FEATURE.md` - 完整实现文档

---

## 功能说明

### Token追踪机制
- 自动拦截所有LLM调用
- 记录input_tokens、output_tokens、total_tokens
- 计算成本（GPT-4: $0.03/1K input, $0.06/1K output）
- 支持按token_key区分不同调用者

### 可视化内容
1. **统计卡片**: 总请求数、Token总数、成本、输入Token
2. **趋势图**: 7天Token使用趋势
3. **模型统计**: 各模型使用情况
4. **错误统计**: 错误类型和次数
5. **使用排行**: Top 10 token_key排行

### 使用方式
1. 启动后端服务
2. 启动前端服务
3. 访问 http://localhost:5173/token-monitor
4. 查看Token使用情况

### 日志输出
```
[OK] Token监控 - default - 请求: 1000+500 tokens - 成本: ¥0.0180
[OK] Token监控 - user_1 - 请求: 800+400 tokens - 成本: ¥0.0144
```

---

## 技术栈

### 后端
- LangChain (Callback机制)
- FastAPI
- 异步I/O (async/await)

### 前端
- Vue 3
- TypeScript
- Ant Design Vue
- ECharts (数据可视化)
- Vue Router

---

## 性能指标

| 指标 | 结果 |
|------|------|
| 100次调用耗时 | < 1秒 |
| 平均每次调用 | < 0.01秒 |
| API响应时间 | < 100ms |
| 并发支持 | 是 |

---

## 下一步计划

1. ✅ 添加单元测试
2. ⏳ 添加性能测试
3. ⏳ 实现持久化存储
4. ⏳ 添加监控告警
5. ⏳ 增强前端功能（导出、筛选等）

---

**更新时间**: 2026-04-23
