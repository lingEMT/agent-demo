"""行程规划技能 - 基于景点、天气、酒店信息生成完整的旅行计划"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt.chat_agent_executor import create_tool_calling_executor

from ...models.schemas import TripPlan
from ...services.cache_service import get_cache_service, CacheNamespace
import json

# ============ 提示词 ============

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


MODIFICATION_SYSTEM_PROMPT = """你是行程优化专家。你会收到一份现有的旅行计划以及用户的修改请求。
你的任务是根据修改请求对行程进行调整。

**要求:**
1. 保持与原始计划相同的城市、日期范围和天数，除非修改明确要求改变
2. 修改后的计划仍然需要包含完整的 TripPlan JSON 结构
3. 保持合理的行程安排，考虑景点之间的距离关系
4. 保持天气信息不变（天气不因行程修改而改变）
5. 输出格式必须与原始计划完全一致，使用相同的 JSON 结构
"""


class PlannerSkill:
    """行程规划技能 - 使用结构化输出生成完整的旅行计划"""

    def __init__(self, llm):
        self.llm = llm
        self._fallback_agent = None

    @property
    def fallback_agent(self):
        """延迟初始化的回退 agent executor"""
        if self._fallback_agent is None:
            self._fallback_agent = create_tool_calling_executor(
                model=self.llm,
                tools=[],
                prompt=PLANNER_AGENT_PROMPT
            )
        return self._fallback_agent

    def _build_cache_key(self, request: dict) -> str:
        """构建LLM响应缓存key"""
        parts = [
            request.get('city', ''),
            str(request.get('travel_days', 3)),
            str(request.get('start_date', '')),
            str(request.get('end_date', '')),
            request.get('transportation', ''),
            request.get('accommodation', ''),
            str(request.get('preferences', [])),
        ]
        return ":".join(parts)

    def _build_query(self, request: dict, state: dict) -> str:
        """构建LLM查询文本"""
        query = f"""请根据以下信息生成{request.get('city', '北京')}的{request.get('travel_days', 3)}天旅行计划:

**基本信息:**
- 城市: {request.get('city', '北京')}
- 日期: {request.get('start_date', '')} 至 {request.get('end_date', '')}
- 天数: {request.get('travel_days', 3)}天
- 交通方式: {request.get('transportation', '公共交通')}
- 住宿: {request.get('accommodation', '经济型')}
- 偏好: {', '.join(request.get('preferences', [])) if request.get('preferences') else '无'}

**景点信息:**
{state.get('attraction_result', '')}

**天气信息:**
{state.get('weather_result', '')}

**酒店信息:**
{state.get('hotel_result', '')}

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店
4. 考虑景点之间的距离和交通方式
5. 返回完整的JSON格式数据
"""
        if request.get('free_text_input'):
            query += f"\n**额外要求:** {request.get('free_text_input')}"
        return query

    async def execute_structured(self, request: dict, state: dict) -> dict:
        """
        使用结构化输出生成旅行计划（主要路径）

        Args:
            request: 旅行请求字典
            state: 当前工作流状态（包含景点/天气/酒店结果）

        Returns:
            TripPlan 字典（可直接用于构造 TripPlan 对象）
        """
        cache_key = self._build_cache_key(request)

        # 检查缓存
        cache = get_cache_service()
        cached_result = await cache.get(CacheNamespace.LLM_RESPONSE, cache_key)
        if cached_result is not None:
            print("      [CACHE] LLM响应缓存命中")
            return cached_result

        # 调用LLM
        query = self._build_query(request, state)
        structured_llm = self.llm.with_structured_output(TripPlan, method="json_mode")
        messages = [
            SystemMessage(content=PLANNER_AGENT_PROMPT),
            HumanMessage(content=query)
        ]
        trip_plan: TripPlan = await structured_llm.ainvoke(messages)
        print(f"      结构化输出成功: {trip_plan.city} {len(trip_plan.days)}天")

        # 序列化并缓存
        plan_dict = trip_plan.model_dump()
        await cache.set(CacheNamespace.LLM_RESPONSE, cache_key, plan_dict, ttl=3600)

        return plan_dict

    async def modify_plan(self, original_plan: dict, modification_text: str, request: dict) -> dict:
        """
        基于原计划 + 修改文本，生成新计划。跳过 cache（每次修改唯一）。

        Args:
            original_plan: 原始旅行计划 dict
            modification_text: 用户修改请求文本
            request: 原始旅行请求数据

        Returns:
            修改后的 TripPlan 字典
        """
        original_plan_json = json.dumps(original_plan, ensure_ascii=False, indent=2)

        query = f"""以下是用户当前的旅行计划：

{original_plan_json}

**原始请求信息:**
- 城市: {request.get('city', '')}
- 日期: {request.get('start_date', '')} 至 {request.get('end_date', '')}
- 天数: {request.get('travel_days', 3)}天
- 交通方式: {request.get('transportation', '公共交通')}
- 住宿: {request.get('accommodation', '经济型')}
- 偏好: {', '.join(request.get('preferences', [])) if request.get('preferences') else '无'}

**用户的修改请求:**
{modification_text}

请根据修改请求对上述旅行计划进行调整，返回完整的修改后计划 JSON。"""
        if request.get('free_text_input'):
            query += f"\n\n**额外要求（来自原始请求）:** {request.get('free_text_input')}"

        structured_llm = self.llm.with_structured_output(TripPlan, method="json_mode")
        messages = [
            SystemMessage(content=MODIFICATION_SYSTEM_PROMPT),
            HumanMessage(content=query)
        ]
        print(f"      [修改] 调用LLM进行计划修改: {modification_text[:50]}...")
        trip_plan: TripPlan = await structured_llm.ainvoke(messages)
        print(f"      [修改] 修改成功: {trip_plan.city} {len(trip_plan.days)}天")

        return trip_plan.model_dump()

    async def execute_fallback(self, request: dict, state: dict) -> str:
        """
        使用传统 agent executor 生成旅行计划（回退路径）

        Args:
            request: 旅行请求字典
            state: 当前工作流状态

        Returns:
            LLM响应文本（需要后续解析）
        """
        query = self._build_query(request, state)
        agent = self.fallback_agent
        result = await agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        return result["messages"][-1].content
