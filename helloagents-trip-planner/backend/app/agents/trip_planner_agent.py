"""多智能体旅行规划系统 - 使用LangChain/LangGraph"""

import json
from typing import Dict, Any, AsyncGenerator, TypedDict, Annotated, Sequence

from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.graph import StateGraph, END

from ..services.llm_service import get_llm
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, Location
from ..config import get_settings
from ..services.amap_service import create_amap_tools
from ..services.conversation_service import get_conversation_service
from ..services.history_service import get_history_service
from .skills import AttractionSkill, WeatherSkill, HotelSkill, PlannerSkill
import operator


# ============ 状态定义 ============

class TripPlanningState(TypedDict):
    """旅行规划状态"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    request: Dict[str, Any]
    attraction_result: str
    weather_result: str
    hotel_result: str
    final_plan: Any  # TripPlan dict (structured) or str (fallback)


# ============ 多智能体系统 ============

class MultiAgentTripPlanner:
    """多智能体旅行规划系统 - 使用LangGraph"""

    def __init__(self):
        """初始化多智能体系统"""
        print("[INFO] 开始初始化多智能体旅行规划系统 (LangGraph)...")

        try:
            settings = get_settings()
            self.llm = get_llm()
            self.settings = settings

            # 创建HTTP工具
            self.langchain_tools = create_amap_tools()
            print(f"[OK] 创建了 {len(self.langchain_tools)} 个工具")

            # 技能实例（延迟初始化）
            self.attraction_skill = None
            self.weather_skill = None
            self.hotel_skill = None
            self.planner_skill = None

            # 已编译的工作流（缓存避免重复编译）
            self._compiled_workflow = None

            print(f"[OK] 多智能体系统框架初始化成功")

        except Exception as e:
            print(f"[ERROR] 多智能体系统初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def should_reset(self) -> bool:
        """检查是否需要重置（技能实例是否已初始化）"""
        return self.attraction_skill is None

    async def _ensure_skills(self):
        """确保所有技能实例已初始化"""
        if self.attraction_skill is not None:
            return
        print("  - 初始化技能实例...")
        self.attraction_skill = AttractionSkill(self.llm, self.langchain_tools)
        self.weather_skill = WeatherSkill(self.llm, self.langchain_tools)
        self.hotel_skill = HotelSkill(self.llm, self.langchain_tools)
        self.planner_skill = PlannerSkill(self.llm)
        print("  - 技能实例初始化完成")

    def _get_compiled_workflow(self):
        """构建并编译工作流图（缓存编译结果，避免重复编译）"""
        if self._compiled_workflow is not None:
            return self._compiled_workflow

        print("  - 构建工作流（并行模式）...")

        workflow = StateGraph(TripPlanningState)

        # ========== 定义工作流节点 ==========

        async def attraction_node(state: TripPlanningState) -> Dict:
            """景点搜索节点"""
            print("    [节点] 搜索景点...")
            try:
                response = await self.attraction_skill.execute(state["request"])
                return {"attraction_result": response}
            except Exception as e:
                print(f"      [ERROR] 景点搜索失败: {str(e)}")
                import traceback
                traceback.print_exc()
                return {"attraction_result": f"错误: {str(e)}"}

        async def weather_node(state: TripPlanningState) -> Dict:
            """天气查询节点"""
            print("    [节点] 查询天气...")
            try:
                response = await self.weather_skill.execute(state["request"])
                return {"weather_result": response}
            except Exception as e:
                print(f"      [ERROR] 天气查询失败: {str(e)}")
                import traceback
                traceback.print_exc()
                return {"weather_result": f"错误: {str(e)}"}

        async def hotel_node(state: TripPlanningState) -> Dict:
            """酒店推荐节点"""
            print("    [节点] 搜索酒店...")
            try:
                response = await self.hotel_skill.execute(state["request"])
                return {"hotel_result": response}
            except Exception as e:
                print(f"      [ERROR] 酒店搜索失败: {str(e)}")
                import traceback
                traceback.print_exc()
                return {"hotel_result": f"错误: {str(e)}"}

        async def planner_node(state: TripPlanningState) -> Dict:
            """行程规划节点 - 使用结构化输出"""
            print("    [节点] 生成行程计划（结构化输出）...")
            try:
                plan_dict = await self.planner_skill.execute_structured(state["request"], state)
                return {"final_plan": plan_dict}
            except Exception as e:
                print(f"      [WARN] 结构化输出失败，回退到文本解析: {str(e)}")
                import traceback
                traceback.print_exc()
                try:
                    response = await self.planner_skill.execute_fallback(state["request"], state)
                    return {"final_plan": response}
                except Exception as fallback_err:
                    print(f"      [ERROR] 回退规划也失败: {str(fallback_err)}")
                    return {"final_plan": f"错误: {str(fallback_err)}"}

        # 添加节点
        workflow.add_node("attraction_search", attraction_node)
        workflow.add_node("weather_query", weather_node)
        workflow.add_node("hotel_search", hotel_node)
        workflow.add_node("planner", planner_node)

        # 设置入口
        workflow.set_entry_point("attraction_search")

        # 扇出结构：attraction_search 完成后同时启动天气和酒店查询
        workflow.add_edge("attraction_search", "weather_query")
        workflow.add_edge("attraction_search", "hotel_search")

        # 扇入结构：天气和酒店都完成后才进入规划节点
        workflow.add_edge("weather_query", "planner")
        workflow.add_edge("hotel_search", "planner")

        workflow.add_edge("planner", END)

        print(f"  - 工作流节点: {workflow.nodes}")
        print(f"  - 执行模式: 并行（天气+酒店与景点并行）")

        self._compiled_workflow = workflow.compile()
        return self._compiled_workflow

    async def plan_trip_async(self, request: TripRequest) -> TripPlan:
        """
        使用多智能体协作生成旅行计划 (异步版本)

        Args:
            request: 旅行请求

        Returns:
            旅行计划
        """
        try:
            print(f"\n{'='*60}")
            print(f"[开始] 多智能体协作规划旅行 (LangGraph)")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"{'='*60}\n")

            # 确保技能已初始化
            await self._ensure_skills()

            # 获取已编译的工作流
            app = self._get_compiled_workflow()

            # 准备初始状态
            initial_state = {
                "messages": [],
                "request": request.model_dump(),
                "attraction_result": "",
                "weather_result": "",
                "hotel_result": "",
                "final_plan": ""
            }

            print("[STEP 1] 搜索景点...")
            print("[STEP 2] 查询天气...")
            print("[STEP 3] 搜索酒店...")
            print("[STEP 4] 生成行程计划...")

            result = await app.ainvoke(initial_state)

            # 解析最终计划
            raw_plan = result.get("final_plan", "")
            if isinstance(raw_plan, dict):
                # 结构化输出路径：直接从 dict 构造 TripPlan
                trip_plan = TripPlan(**raw_plan)
                print(f"\n[OK] 结构化输出成功: {trip_plan.city} {len(trip_plan.days)}天\n")
            elif isinstance(raw_plan, str) and raw_plan and not raw_plan.startswith("错误"):
                # 传统文本解析路径（回退）
                trip_plan = self._parse_response(raw_plan, request)
            else:
                print(f"\n[WARN] 最终计划无效，使用备用方案\n")
                trip_plan = self._create_fallback_plan(request)

            print(f"{'='*60}")
            print(f"[完成] 旅行计划生成成功!")
            print(f"{'='*60}\n")

            return trip_plan

        except Exception as e:
            print(f"[ERROR] 生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)

    async def plan_trip_stream(self, request: TripRequest, session_id: str = "") -> AsyncGenerator[Dict[str, Any], None]:
        """
        使用多智能体协作流式生成旅行计划，逐个节点产生SSE事件

        Args:
            request: 旅行请求
            session_id: 前端会话ID（用于对话记忆）

        Yields:
            事件字典: {"event": event_type, "data": data_dict}
        """
        plan_id = ""
        conversation_id = ""
        try:
            print(f"\n{'='*60}")
            print(f"[开始] 多智能体协作流式规划旅行 (LangGraph)")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"{'='*60}\n")

            # 初始化技能
            yield {"event": "progress", "data": {"stage": "init", "progress": 5, "message": "正在初始化系统..."}}
            await self._ensure_skills()

            # 获取已编译的工作流
            yield {"event": "progress", "data": {"stage": "build_workflow", "progress": 10, "message": "正在构建工作流..."}}
            app = self._get_compiled_workflow()

            # 准备初始状态
            initial_state = {
                "messages": [],
                "request": request.model_dump(),
                "attraction_result": "",
                "weather_result": "",
                "hotel_result": "",
                "final_plan": ""
            }

            # 发送进度：开始景点搜索
            yield {"event": "progress", "data": {"stage": "attraction_search", "progress": 20, "message": "正在搜索景点..."}}
            print("[STEP 1] 搜索景点...")

            final_state = {}

            # 使用astream流式执行，stream_mode="updates"产生每节点完成事件
            async for event in app.astream(initial_state, stream_mode="updates"):
                for node_name, state_update in event.items():
                    final_state.update(state_update)

                    if node_name == "attraction_search":
                        content = state_update.get("attraction_result", "")
                        yield {"event": "partial_result", "data": {"type": "attractions", "content": content}}
                        yield {"event": "progress", "data": {"stage": "weather_query", "progress": 40, "message": "正在查询天气..."}}
                        yield {"event": "progress", "data": {"stage": "hotel_search", "progress": 50, "message": "正在搜索酒店..."}}

                    elif node_name == "weather_query":
                        content = state_update.get("weather_result", "")
                        yield {"event": "partial_result", "data": {"type": "weather", "content": content}}
                        yield {"event": "progress", "data": {"stage": "weather_done", "progress": 60, "message": "天气查询完成"}}

                    elif node_name == "hotel_search":
                        content = state_update.get("hotel_result", "")
                        yield {"event": "partial_result", "data": {"type": "hotels", "content": content}}
                        yield {"event": "progress", "data": {"stage": "hotel_done", "progress": 70, "message": "酒店搜索完成"}}

                    elif node_name == "planner":
                        yield {"event": "progress", "data": {"stage": "planning", "progress": 85, "message": "正在生成行程计划..."}}
                        print("[STEP 4] 生成行程计划...")

            # 所有节点完成，解析最终计划
            yield {"event": "progress", "data": {"stage": "parsing", "progress": 95, "message": "正在解析结果..."}}

            raw_plan = final_state.get("final_plan", "")
            trip_plan = None

            if isinstance(raw_plan, dict):
                try:
                    trip_plan = TripPlan(**raw_plan)
                    print(f"[OK] 结构化输出解析成功")
                except Exception as e:
                    print(f"[WARN] 结构化输出转 TripPlan 失败: {e}")

            if trip_plan is None:
                final_plan_str = raw_plan if isinstance(raw_plan, str) else ""
                if final_plan_str and final_plan_str != f"错误:" and not final_plan_str.startswith("错误"):
                    trip_plan = self._parse_response(final_plan_str, request)

            if trip_plan is None:
                print(f"[WARN] 最终计划无效，使用备用方案")
                trip_plan = self._create_fallback_plan(request)

            # 创建对话记录
            if session_id and trip_plan:
                try:
                    request_dict = request.model_dump()
                    plan_dict = trip_plan.model_dump()
                    title = f"{request.city}{request.travel_days}日游"
                    conv_service = get_conversation_service()
                    record = await conv_service.create_conversation(
                        session_id=session_id,
                        title=title,
                        request_data=request_dict,
                        plan_data=plan_dict,
                    )
                    plan_id = record.id
                    conversation_id = record.conversation_id or ""
                    print(f"[OK] 对话记录已创建: conversation_id={conversation_id}, plan_id={plan_id}")
                except Exception as conv_err:
                    print(f"[WARN] 创建对话记录失败: {conv_err}")
                    import traceback
                    traceback.print_exc()

            yield {"event": "progress", "data": {"stage": "complete", "progress": 100, "message": "完成!"}}
            result_data = trip_plan.model_dump()
            result_data["_meta"] = {
                "plan_id": plan_id,
                "conversation_id": conversation_id,
                "version_number": 1,
            } if plan_id else {}
            yield {"event": "final_result", "data": {"success": True, "message": "旅行计划生成成功", "data": result_data}}
            print(f"\n{'='*60}")
            print(f"[完成] 旅行计划流式生成成功!")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"[ERROR] 流式生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            yield {"event": "error", "data": {"error": f"生成旅行计划失败: {str(e)}", "code": "SYSTEM_ERROR"}}
            try:
                fallback_plan = self._create_fallback_plan(request)
                yield {"event": "final_result", "data": {"success": True, "message": "已生成备用旅行计划", "data": fallback_plan.model_dump()}}
            except:
                pass

    async def modify_plan_stream(
        self,
        plan_id: str,
        modification_text: str,
        session_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        基于已有计划进行流式修改（只运行 planner 节点）

        Args:
            plan_id: 原计划 ID
            modification_text: 用户修改请求
            session_id: 会话ID

        Yields:
            SSE 事件字典
        """
        try:
            yield {"event": "progress", "data": {"stage": "loading", "progress": 10, "message": "正在加载原计划..."}}

            # 1. 加载原计划
            history_service = get_history_service()
            record = await history_service.get_trip(plan_id)
            if not record:
                yield {"event": "error", "data": {"error": "原计划记录不存在", "code": "PLAN_NOT_FOUND"}}
                return

            plan_data_str = record.plan_data
            if not plan_data_str:
                yield {"event": "error", "data": {"error": "原计划数据为空", "code": "PLAN_DATA_EMPTY"}}
                return

            import json
            original_plan = json.loads(plan_data_str) if isinstance(plan_data_str, str) else plan_data_str
            request_data = json.loads(record.request_data) if isinstance(record.request_data, str) else (record.request_data or {})

            # 2. 准备修改上下文（使用原 request，但保留原始请求数据）
            yield {"event": "progress", "data": {"stage": "modifying", "progress": 30, "message": "正在根据请求修改计划..."}}

            # 3. 确保技能已初始化
            await self._ensure_skills()

            # 4. 调用 planner_skill.modify_plan()
            yield {"event": "progress", "data": {"stage": "planning", "progress": 50, "message": "正在生成修改后的计划..."}}
            new_plan = await self.planner_skill.modify_plan(
                original_plan=original_plan,
                modification_text=modification_text,
                request=request_data,
            )

            # 5. 验证生成结果
            yield {"event": "progress", "data": {"stage": "saving", "progress": 80, "message": "正在保存新版本..."}}
            trip_plan = TripPlan(**new_plan)

            # 6. 通过 ConversationService 保存新版本
            conv_service = get_conversation_service()
            new_record = await conv_service.add_version(
                parent_plan_id=plan_id,
                session_id=session_id,
                modification_text=modification_text,
                request_data=request_data,
                plan_data=new_plan,
            )

            new_plan_id = ""
            new_conversation_id = ""
            new_version_number = 1

            if new_record:
                new_plan_id = new_record.id
                new_conversation_id = new_record.conversation_id or ""
                new_version_number = new_record.version_number or 1
                print(f"[OK] 新版本已保存: {new_plan_id} (v{new_version_number})")

            yield {"event": "progress", "data": {"stage": "complete", "progress": 100, "message": "修改完成!"}}

            # 7. 返回结果
            result_data = trip_plan.model_dump()
            result_data["_meta"] = {
                "plan_id": new_plan_id,
                "conversation_id": new_conversation_id,
                "version_number": new_version_number,
                "modification_text": modification_text,
            }
            yield {"event": "final_result", "data": {"success": True, "message": "计划修改成功", "data": result_data}}

        except Exception as e:
            print(f"[ERROR] 修改计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            yield {"event": "error", "data": {"error": f"修改计划失败: {str(e)}", "code": "MODIFY_ERROR"}}

    def plan_trip(self, request: TripRequest) -> TripPlan:
        """
        使用多智能体协作生成旅行计划 (同步版本)

        Args:
            request: 旅行请求

        Returns:
            旅行计划
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.plan_trip_async(request))
                    return future.result()
            else:
                return loop.run_until_complete(self.plan_trip_async(request))
        except RuntimeError:
            return asyncio.run(self.plan_trip_async(request))

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """
        解析Agent响应（回退路径：从 LLM 文本输出中提取 JSON）

        Args:
            response: Agent响应文本
            request: 原始请求

        Returns:
            旅行计划
        """
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                raise ValueError("响应中未找到JSON数据")

            data = json.loads(json_str)
            trip_plan = TripPlan(**data)
            return trip_plan

        except Exception as e:
            print(f"[WARN] 解析响应失败: {str(e)}")
            return self._create_fallback_plan(request)

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用计划(当Agent失败时)"""
        print("创建备用计划...")

        from datetime import datetime, timedelta

        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")

        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)

            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天行程",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    Attraction(
                        name=f"{request.city}景点{j+1}",
                        address=f"{request.city}市",
                        location=Location(longitude=116.4 + i*0.01 + j*0.005, latitude=39.9 + i*0.01 + j*0.005),
                        visit_duration=120,
                        description=f"这是{request.city}的著名景点",
                        category="景点"
                    )
                    for j in range(2)
                ],
                meals=[
                    Meal(type="breakfast", name=f"第{i+1}天早餐", description="当地特色早餐"),
                    Meal(type="lunch", name=f"第{i+1}天午餐", description="午餐推荐"),
                    Meal(type="dinner", name=f"第{i+1}天晚餐", description="晚餐推荐")
                ]
            )
            days.append(day_plan)

        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间。"
        )

    async def cleanup(self):
        """清理资源"""
        self._compiled_workflow = None
        print("Agent资源已清理")


# ============ 全局单例 ============

_multi_agent_planner = None
_multi_agent_lock = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取多智能体旅行规划系统实例(单例模式)"""
    global _multi_agent_planner, _multi_agent_lock

    if _multi_agent_lock is None:
        _multi_agent_lock = __import__('threading').Lock()

    with _multi_agent_lock:
        if _multi_agent_planner is None:
            _multi_agent_planner = MultiAgentTripPlanner()
        elif _multi_agent_planner.should_reset():
            print("[INFO] 旧 Agent 实例失效，重新创建...")
            _multi_agent_planner = MultiAgentTripPlanner()

        return _multi_agent_planner
