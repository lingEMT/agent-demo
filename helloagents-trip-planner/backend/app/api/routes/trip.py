"""旅行规划API路由 - 异步版本"""

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from ...models.schemas import (
    TripRequest,
    TripPlan,
    TripPlanResponse,
    ModificationRequest,
    ConversationSummary,
    ConversationListResponse,
    PlanVersionInfo,
)
from ...agents.trip_planner_agent import get_trip_planner_agent
from ...services.conversation_service import get_conversation_service
from ...services.history_service import get_history_service

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
async def plan_trip_stream(
    request: TripRequest,
    session_id: Optional[str] = Query(default="", description="前端会话ID"),
):
    """
    流式生成旅行计划 (SSE)

    Args:
        request: 旅行请求参数
        session_id: 前端会话ID（可选，用于对话记忆）

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
                async for event_data in agent.plan_trip_stream(request, session_id=session_id):
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


@router.post(
    "/plan/modify/{plan_id}/stream",
    summary="流式修改旅行计划",
    description="基于已有计划，通过自然语言对话方式修改旅行计划，SSE流式返回"
)
async def modify_plan_stream(plan_id: str, request: ModificationRequest):
    """
    流式修改旅行计划 (SSE)

    只重新运行 planner 节点，将原计划作为上下文注入。
    速度快 3-4 倍，token 成本降低 3-4 倍。

    Args:
        plan_id: 要修改的计划ID
        request: 修改请求（包含 modification_text 和 session_id）

    Returns:
        SSE流式响应
    """
    try:
        print(f"\n{'='*60}")
        print(f"[INFO] 收到计划修改请求:")
        print(f"   plan_id: {plan_id}")
        print(f"   修改: {request.modification_text[:100]}")
        print(f"{'='*60}\n")

        agent = get_trip_planner_agent()

        async def event_generator():
            """生成SSE事件流"""
            try:
                async for event_data in agent.modify_plan_stream(
                    plan_id=plan_id,
                    modification_text=request.modification_text,
                    session_id=request.session_id,
                ):
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
            detail=f"流式修改旅行计划失败: {str(e)}"
        )


@router.get(
    "/conversation/{conversation_id}",
    summary="获取对话所有版本",
    description="获取指定对话的完整版本链"
)
async def get_conversation(conversation_id: str):
    """
    获取对话所有版本（按版本号升序）

    Args:
        conversation_id: 对话ID

    Returns:
        版本列表
    """
    try:
        conv_service = get_conversation_service()
        history_service = get_history_service()

        # 获取完整版本链
        records = await conv_service.get_conversation(conversation_id)
        if not records:
            raise HTTPException(status_code=404, detail="对话不存在")

        # 获取最新的版本ID
        latest_record = await conv_service.get_latest_plan(conversation_id)
        latest_id = latest_record.id if latest_record else ""

        versions = []
        for record in records:
            plan_data = None
            if record.plan_data:
                try:
                    plan_data = json.loads(record.plan_data) if isinstance(record.plan_data, str) else record.plan_data
                except (json.JSONDecodeError, TypeError):
                    pass

            # 如果没有 plan_data，加载全部数据（从 history 加载使用）
            if not plan_data and record.plan_data:
                full = await history_service.get_trip(record.id)
                if full and full.plan_data:
                    try:
                        plan_data = json.loads(full.plan_data) if isinstance(full.plan_data, str) else full.plan_data
                    except (json.JSONDecodeError, TypeError):
                        pass

            versions.append({
                "id": record.id,
                "version_number": record.version_number or 1,
                "is_current": record.id == latest_id,
                "modification_request": record.modification_request,
                "created_at": record.created_at.isoformat() if record.created_at else "",
                "plan_data": plan_data,
            })

        return {
            "success": True,
            "conversation_id": conversation_id,
            "versions": versions,
            "total_versions": len(versions),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 获取对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取对话失败: {str(e)}")


@router.get(
    "/conversations/list",
    summary="列出所有对话",
    description="按对话分组展示计划列表"
)
async def list_conversations(
    session_id: str = Query(..., description="会话ID"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
):
    """
    列出所有对话（每个对话只返回最新版本摘要）

    Args:
        session_id: 会话ID
        page: 页码
        page_size: 每页数量

    Returns:
        对话列表
    """
    try:
        conv_service = get_conversation_service()
        summaries, total = await conv_service.list_conversations(
            session_id=session_id,
            page=page,
            page_size=page_size,
        )

        return {
            "success": True,
            "data": summaries,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    except Exception as e:
        print(f"[ERROR] 列出对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出对话失败: {str(e)}")


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
            "tools_initialized": agent.langchain_tools is not None,
            "skills_initialized": agent.attraction_skill is not None
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )
