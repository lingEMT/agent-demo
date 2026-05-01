"""酒店推荐技能 - 搜索指定城市的酒店信息"""

from langchain_core.messages import HumanMessage
from langgraph.prebuilt.chat_agent_executor import create_tool_calling_executor

# ============ 提示词 ============

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。你的任务是根据城市和景点位置推荐合适的酒店。

**重要提示:**
你必须使用工具来搜索酒店!不要自己编造酒店信息!

**工具调用:**
使用 search_poi 工具搜索酒店,关键词使用"酒店"或"宾馆"。

**注意:**
1. 必须使用工具,不要直接回答
2. 返回真实的酒店信息
"""


class HotelSkill:
    """酒店推荐技能"""

    def __init__(self, llm, tools):
        self.agent = create_tool_calling_executor(
            model=llm,
            tools=tools,
            prompt=HOTEL_AGENT_PROMPT
        )

    async def execute(self, request: dict) -> str:
        """
        执行酒店搜索

        Args:
            request: 旅行请求字典

        Returns:
            酒店搜索结果文本
        """
        city = request.get("city", "北京")
        accommodation = request.get("accommodation", "经济型")
        query = f"请搜索{city}的{accommodation}酒店"
        print(f"      [酒店搜索] 查询: {query}")

        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        print(f"      [酒店搜索] Agent响应: {len(result.get('messages', []))} 条消息")

        return result["messages"][-1].content
