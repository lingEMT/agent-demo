"""多智能体旅行规划系统 - 使用LangChain/LangGraph"""

import json
from typing import Dict, Any, TypedDict, Annotated, Sequence
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt.chat_agent_executor import create_tool_calling_executor

from ..services.llm_service import get_llm
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, Location
from ..config import get_settings
from ..services.amap_service import create_amap_tools
import operator

# ============ Agent提示词 ============

ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。

**重要提示:**
你必须使用工具来搜索景点!不要自己编造景点信息!

**工具调用:**
使用 search_poi 工具搜索景点。

**注意:**
1. 必须使用工具,不要直接回答
2. 返回真实的景点信息
3. 包括景点名称、地址、位置坐标等
"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。

**重要提示:**
你必须使用工具来查询天气!不要自己编造天气信息!

**工具调用:**
使用 get_weather 工具查询天气。

**注意:**
1. 必须使用工具,不要直接回答
2. 返回准确的天气信息
"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。你的任务是根据城市和景点位置推荐合适的酒店。

**重要提示:**
你必须使用工具来搜索酒店!不要自己编造酒店信息!

**工具调用:**
使用 search_poi 工具搜索酒店,关键词使用"酒店"或"宾馆"。

**注意:**
1. 必须使用工具,不要直接回答
2. 返回真实的酒店信息
"""

PLANNER_AGENT_PROMPT = """你是行程规划专家。你的任务是根据景点信息和天气信息,生成详细的旅行计划。

请严格按照以下JSON格式返回旅行计划:
```json
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}
```

**重要提示:**
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. **必须包含预算信息**
"""


# ============ 状态定义 ============

class TripPlanningState(TypedDict):
    """旅行规划状态"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    request: Dict[str, Any]
    attraction_result: str
    weather_result: str
    hotel_result: str
    final_plan: str


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

            # Agent将在运行时创建
            self.attraction_agent = None
            self.weather_agent = None
            self.hotel_agent = None
            self.planner_agent = None

            # 工作流图
            self.workflow = None

            print(f"[OK] 多智能体系统框架初始化成功")

        except Exception as e:
            print(f"[ERROR] 多智能体系统初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def should_reset(self) -> bool:
        """检查是否需要重置 Agent 实例"""
        # 检查 Agent 是否已初始化
        if self.attraction_agent is None or not self.attraction_agent:
            print("[INFO] 检测到 Agent 未初始化或实例为空，需要重置")
            return True

        # 检查 Agent 的类型是否正确
        from langgraph.graph.state import CompiledStateGraph
        if not isinstance(self.attraction_agent, CompiledStateGraph):
            print("[INFO] 检测到 Agent 类型不正确，需要重置")
            return True

        return False

    async def _init_agents(self):
        """初始化所有Agent"""
        print("  - 创建Agent...")

        # 创建景点搜索Agent
        self.attraction_agent = create_tool_calling_executor(
            model=self.llm,
            tools=self.langchain_tools,
            prompt=ATTRACTION_AGENT_PROMPT
        )

        # 创建天气查询Agent
        self.weather_agent = create_tool_calling_executor(
            model=self.llm,
            tools=self.langchain_tools,
            prompt=WEATHER_AGENT_PROMPT
        )

        # 创建酒店推荐Agent
        self.hotel_agent = create_tool_calling_executor(
            model=self.llm,
            tools=self.langchain_tools,
            prompt=HOTEL_AGENT_PROMPT
        )

        # 创建行程规划Agent (不需要工具)
        self.planner_agent = create_tool_calling_executor(
            model=self.llm,
            tools=[],
            prompt=PLANNER_AGENT_PROMPT
        )

        print("  - Agent创建完成")

    def _build_workflow(self) -> StateGraph:
        """构建工作流图"""
        print("  - 构建工作流...")

        workflow = StateGraph(TripPlanningState)

        # 定义节点
        async def attraction_node(state: TripPlanningState) -> Dict:
            """景点搜索节点"""
            print("    [节点] 搜索景点...")
            try:
                request = state["request"]
                keywords = request.get("preferences", ["景点"])[0] if request.get("preferences") else "景点"
                city = request.get("city", "北京")

                query = f"请搜索{city}的{keywords}相关景点"

                print(f"      查询: {query}")

                result = await self.attraction_agent.ainvoke({
                    "messages": [HumanMessage(content=query)]
                })

                print(f"      Agent响应: {len(result.get('messages', []))} 条消息")

                response = result["messages"][-1].content
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
                request = state["request"]
                city = request.get("city", "北京")

                query = f"请查询{city}的天气信息"

                print(f"      查询: {query}")

                result = await self.weather_agent.ainvoke({
                    "messages": [HumanMessage(content=query)]
                })

                print(f"      Agent响应: {len(result.get('messages', []))} 条消息")

                response = result["messages"][-1].content
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
                request = state["request"]
                city = request.get("city", "北京")
                accommodation = request.get("accommodation", "经济型")

                query = f"请搜索{city}的{accommodation}酒店"

                print(f"      查询: {query}")

                result = await self.hotel_agent.ainvoke({
                    "messages": [HumanMessage(content=query)]
                })

                print(f"      Agent响应: {len(result.get('messages', []))} 条消息")

                response = result["messages"][-1].content
                return {"hotel_result": response}
            except Exception as e:
                print(f"      [ERROR] 酒店搜索失败: {str(e)}")
                import traceback
                traceback.print_exc()
                return {"hotel_result": f"错误: {str(e)}"}

        async def planner_node(state: TripPlanningState) -> Dict:
            """行程规划节点"""
            print("    [节点] 生成行程计划...")
            try:
                request = state["request"]

                query = f"""请根据以下信息生成{request.get('city', '北京')}的{request.get('travel_days', 3)}天旅行计划:

**基本信息:**
- 城市: {request.get('city', '北京')}
- 日期: {request.get('start_date', '')} 至 {request.get('end_date', '')}
- 天数: {request.get('travel_days', 3)}天
- 交通方式: {request.get('transportation', '公共交通')}
- 住宿: {request.get('accommodation', '经济型')}
- 偏好: {', '.join(request.get('preferences', [])) if request.get('preferences') else '无'}

**景点信息:**
{state['attraction_result']}

**天气信息:**
{state['weather_result']}

**酒店信息:**
{state['hotel_result']}

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店
4. 考虑景点之间的距离和交通方式
5. 返回完整的JSON格式数据
"""

                if request.get('free_text_input'):
                    query += f"\n**额外要求:** {request.get('free_text_input')}"

                result = await self.planner_agent.ainvoke({
                    "messages": [HumanMessage(content=query)]
                })

                print(f"      Agent响应: {len(result.get('messages', []))} 条消息")

                response = result["messages"][-1].content
                return {"final_plan": response}
            except Exception as e:
                print(f"      [ERROR] 行程规划失败: {str(e)}")
                import traceback
                traceback.print_exc()
                return {"final_plan": f"错误: {str(e)}"}

        # 添加节点
        workflow.add_node("attraction_search", attraction_node)
        workflow.add_node("weather_query", weather_node)
        workflow.add_node("hotel_search", hotel_node)
        workflow.add_node("planner", planner_node)

        # 设置入口
        workflow.set_entry_point("attraction_search")

        # 添加边 - 顺序执行
        workflow.add_edge("attraction_search", "weather_query")
        workflow.add_edge("weather_query", "hotel_search")
        workflow.add_edge("hotel_search", "planner")
        workflow.add_edge("planner", END)

        print(f"  - 工作流节点: {workflow.nodes}")
        return workflow

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
            print(f"🚀 开始多智能体协作规划旅行 (LangGraph)...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"{'='*60}\n")

            # 初始化Agent
            print("初始化 agents...")
            await self._init_agents()

            # 检查 agents 是否初始化
            if self.attraction_agent is None:
                print("[ERROR] Agent 初始化失败，返回备用计划")
                return self._create_fallback_plan(request)

            print(f"attraction_agent: {type(self.attraction_agent)}")
            print(f"weather_agent: {type(self.weather_agent)}")
            print(f"hotel_agent: {type(self.hotel_agent)}")
            print(f"planner_agent: {type(self.planner_agent)}")

            # 构建工作流
            print("构建工作流...")
            workflow = self._build_workflow()
            print(f"Workflow nodes: {workflow.nodes}")

            app = workflow.compile()

            # 准备初始状态
            initial_state = {
                "messages": [],
                "request": request.model_dump(),
                "attraction_result": "",
                "weather_result": "",
                "hotel_result": "",
                "final_plan": ""
            }

            # 运行工作流
            print("[STEP 1] 搜索景点...")
            print("[STEP 2] 查询天气...")
            print("[STEP 3] 搜索酒店...")
            print("[STEP 4] 生成行程计划...")

            result = await app.ainvoke(initial_state)

            # 解析最终计划
            final_plan = result.get("final_plan", "")
            print(f"\n行程规划结果: {final_plan[:300]}...\n")

            trip_plan = self._parse_response(final_plan, request)

            print(f"{'='*60}")
            print(f"✅ 旅行计划生成完成!")
            print(f"{'='*60}\n")

            return trip_plan

        except Exception as e:
            print(f"[ERROR] 生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)

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
            # 尝试获取当前事件循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步环境中,创建新任务
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.plan_trip_async(request))
                    return future.result()
            else:
                # 如果在同步环境中,直接运行
                return loop.run_until_complete(self.plan_trip_async(request))
        except RuntimeError:
            # 如果没有事件循环,创建新的
            return asyncio.run(self.plan_trip_async(request))

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """
        解析Agent响应

        Args:
            response: Agent响应文本
            request: 原始请求

        Returns:
            旅行计划
        """
        try:
            # 尝试从响应中提取JSON
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

            # 解析JSON
            data = json.loads(json_str)

            # 转换为TripPlan对象
            trip_plan = TripPlan(**data)

            return trip_plan

        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            print(f"   将使用备用方案生成计划")
            return self._create_fallback_plan(request)

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用计划(当Agent失败时)"""
        print("创建备用计划...")

        from datetime import datetime, timedelta

        # 解析日期
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")

        # 创建每日行程
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
        # HTTP客户端由httpx管理，不需要手动清理
        print("HTTP客户端资源已自动管理")


# 全局多智能体系统实例
_multi_agent_planner = None
_multi_agent_lock = None  # 添加锁，确保线程安全


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取多智能体旅行规划系统实例(单例模式)"""
    global _multi_agent_planner, _multi_agent_lock

    if _multi_agent_lock is None:
        _multi_agent_lock = __import__('threading').Lock()

    with _multi_agent_lock:
        if _multi_agent_planner is None:
            _multi_agent_planner = MultiAgentTripPlanner()
        elif _multi_agent_planner.should_reset():
            # 如果 Agent 需要重置，创建新实例
            print("[INFO] 旧 Agent 实例失效，重新创建...")
            _multi_agent_planner = MultiAgentTripPlanner()

        return _multi_agent_planner
