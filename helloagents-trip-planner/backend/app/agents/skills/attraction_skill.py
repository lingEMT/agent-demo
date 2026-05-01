"""景点搜索技能 - 搜索指定城市的景点信息"""

from langchain_core.messages import HumanMessage
from langgraph.prebuilt.chat_agent_executor import create_tool_calling_executor

# ============ 提示词 ============

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


class AttractionSkill:
    """景点搜索技能"""

    def __init__(self, llm, tools):
        self.agent = create_tool_calling_executor(
            model=llm,
            tools=tools,
            prompt=ATTRACTION_AGENT_PROMPT
        )

    async def execute(self, request: dict) -> str:
        """
        执行景点搜索

        Args:
            request: 旅行请求字典

        Returns:
            景点搜索结果文本
        """
        keywords = request.get("preferences", ["景点"])[0] if request.get("preferences") else "景点"
        city = request.get("city", "北京")
        query = f"请搜索{city}的{keywords}相关景点"
        print(f"      [景点搜索] 查询: {query}")

        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        print(f"      [景点搜索] Agent响应: {len(result.get('messages', []))} 条消息")

        return result["messages"][-1].content
