"""旅行规划API路由 - 异步版本"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ...models.schemas import TripRequest, TripPlan, TripPlanResponse
from ...agents.trip_planner_agent import get_trip_planner_agent

router = APIRouter(prefix="/trip", tags=["旅行规划"])


@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划",
    description="根据用户输入的旅行需求,生成详细的旅行计划"
)
async def plan_trip(request: TripRequest) -> TripPlanResponse:
    """
    生成旅行计划

    Args:
        request: 旅行请求参数

    Returns:
        旅行计划响应
    """
    try:
        print(f"\n{'='*60}")
        print(f"[INFO] 收到旅行规划请求:")
        print(f"   城市: {request.city}")
        print(f"   日期: {request.start_date} - {request.end_date}")
        print(f"   天数: {request.travel_days}")
        print(f"   偏好: {request.preferences}")
        print(f"{'='*60}\n")

        # 获取Agent实例
        print("[INFO] 获取多智能体系统实例...")
        agent = get_trip_planner_agent()

        # 生成旅行计划 (异步调用)
        print("[INFO] 开始生成旅行计划...")
        trip_plan: TripPlan = await agent.plan_trip_async(request)

        print("[OK] 旅行计划生成成功,准备返回响应\n")

        return TripPlanResponse(
            success=True,
            message="旅行计划生成成功",
            data=trip_plan
        )

    except Exception as e:
        print(f"[ERROR] 生成旅行计划失败: {str(e)}")
        import traceback
        import io
        import sys
        tb_output = io.StringIO()
        traceback.print_exc(file=tb_output)
        print(f"[ERROR] 详细堆栈:\n{tb_output.getvalue()}")
        raise HTTPException(
            status_code=500,
            detail=f"生成旅行计划失败: {str(e)}"
        )


@router.post(
    "/plan/stream",
    summary="流式生成旅行计划",
    description="根据用户输入的旅行需求,通过SSE流式返回每个节点的执行进度和最终计划"
)
async def plan_trip_stream(request: TripRequest):
    """
    流式生成旅行计划 (SSE)

    Args:
        request: 旅行请求参数

    Returns:
        SSE流式响应，包含进度事件和最终结果
    """
    try:
        print(f"\n{'='*60}")
        print(f"[INFO] 收到流式旅行规划请求:")
        print(f"   城市: {request.city}")
        print(f"   日期: {request.start_date} - {request.end_date}")
        print(f"   天数: {request.travel_days}")
        print(f"   偏好: {request.preferences}")
        print(f"{'='*60}\n")

        agent = get_trip_planner_agent()

        async def event_generator():
            """生成SSE事件流"""
            try:
                async for event_data in agent.plan_trip_stream(request):
                    event_type = event_data["event"]
                    data_json = json.dumps(event_data["data"], ensure_ascii=False)
                    yield f"event: {event_type}\ndata: {data_json}\n\n"
            except Exception as e:
                print(f"[ERROR] SSE流生成异常: {str(e)}")
                error_data = json.dumps({"error": str(e), "code": "STREAM_ERROR"}, ensure_ascii=False)
                yield f"event: error\ndata: {error_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except Exception as e:
        print(f"[ERROR] 创建流式响应失败: {str(e)}")
        import traceback
        import io
        import sys
        tb_output = io.StringIO()
        traceback.print_exc(file=tb_output)
        print(f"[ERROR] 详细堆栈:\n{tb_output.getvalue()}")
        raise HTTPException(
            status_code=500,
            detail=f"流式生成旅行计划失败: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康检查",
    description="检查旅行规划服务是否正常"
)
async def health_check():
    """健康检查"""
    try:
        # 检查Agent是否可用
        agent = get_trip_planner_agent()

        return {
            "status": "healthy",
            "service": "trip-planner",
            "framework": "LangChain/LangGraph",
            "mcp_tools_initialized": agent.mcp_tools is not None
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )
