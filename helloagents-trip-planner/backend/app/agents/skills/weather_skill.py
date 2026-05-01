"""天气查询技能 - 查询指定城市的天气信息"""

from langchain_core.messages import HumanMessage
from langgraph.prebuilt.chat_agent_executor import create_tool_calling_executor

# ============ 提示词 ============

WEATHER_AGENT_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。

**重要提示:**
你必须使用工具来查询天气!不要自己编造天气信息!

**工具调用:**
使用 get_weather 工具查询天气。

**注意:**
1. 必须使用工具,不要直接回答
2. 返回准确的天气信息
"""


class WeatherSkill:
    """天气查询技能"""

    def __init__(self, llm, tools):
        self.agent = create_tool_calling_executor(
            model=llm,
            tools=tools,
            prompt=WEATHER_AGENT_PROMPT
        )

    async def execute(self, request: dict) -> str:
        """
        执行天气查询

        Args:
            request: 旅行请求字典

        Returns:
            天气查询结果文本
        """
        city = request.get("city", "北京")
        query = f"请查询{city}的天气信息"
        print(f"      [天气查询] 查询: {query}")

        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        print(f"      [天气查询] Agent响应: {len(result.get('messages', []))} 条消息")

        return result["messages"][-1].content
