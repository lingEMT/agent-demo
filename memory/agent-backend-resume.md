# 项目经验 - Agent开发与后端服务

## 1. 基于LangGraph构建多智能体协作系统

使用LangGraph状态图模型，设计并实现多智能体旅行规划系统。通过状态节点、条件边、循环边等机制，编排智能体间的协作流程。采用图编排模式管理复杂任务状态转换，实现行程规划、信息检索、方案优化的自动化编排。

## 2. LangChain工具集成与动态工具调用

基于LangChain的StructuredTool机制，封装高德地图API为标准工具函数。实现智能体的动态工具调用能力，Agent可根据用户需求自动选择POI搜索、天气查询、路线规划等工具。工具函数采用异步设计，支持高并发请求处理。

## 3. LLM服务封装与多模型适配

封装langchain-openai接口，支持OpenAI、DeepSeek等多种LLM模型。实现统一的LLM调用服务，支持流式响应和非流式响应。配置temperature、top_p等生成参数，实现不同风格的回复控制。

## 4. 多智能体状态管理与信息流转

设计多智能体状态机，实现智能体间的信息传递与协作。构建旅行规划复杂状态图，包含信息收集、方案生成、方案优化等状态节点。使用LangGraph的检查点机制保存对话历史，支持中途打断与恢复。

## 5. Agent系统容错与降级机制

实现Agent系统的容错架构，在API调用失败时自动降级到模拟数据。设计工具调用的重试机制和异常捕获处理。通过分层架构隔离底层服务异常，确保主流程稳定性。

---

## 技术栈总结

- **框架**: LangChain, LangGraph, FastAPI
- **LLM**: OpenAI API, DeepSeek API
- **工具**: LangChain StructuredTool, LangChain OpenAI
- **地图**: 高德地图 Web API
- **HTTP**: httpx (异步客户端)
- **数据模型**: Pydantic
- **状态管理**: LangGraph State Graph

**核心技术点**:
1. LangGraph状态图编排
2. LangChain工具链集成
3. 多模型LLM适配
4. 复杂状态管理
5. 容错降级机制
