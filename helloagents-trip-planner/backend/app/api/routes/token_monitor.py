"""Token使用量监控路由"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from ..services.token_usage_tracker import get_token_usage_tracker

router = APIRouter(prefix="/token-monitor", tags=["Token监控"])


@router.get("/summary")
async def get_token_summary():
    """
    获取token使用摘要

    Returns:
        Token使用摘要信息
    """
    tracker = get_token_usage_tracker()
    summary = await tracker.get_summary()

    return {
        "success": True,
        "data": summary
    }


@router.get("/stats")
async def get_token_stats(
    hours: int = Query(24, ge=1, le=720, description="统计时间范围（小时）"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="返回记录数量限制")
):
    """
    获取token使用统计

    Args:
        hours: 统计时间范围（小时）
        limit: 返回记录数量限制

    Returns:
        Token使用统计信息
    """
    tracker = get_token_usage_tracker()
    stats = await tracker.get_usage_stats(hours=hours, limit=limit)

    return {
        "success": True,
        "data": stats
    }


@router.get("/daily")
async def get_daily_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数")
):
    """
    获取每日token使用统计

    Args:
        days: 统计天数

    Returns:
        每日统计信息
    """
    tracker = get_token_usage_tracker()
    daily_stats = await tracker.get_daily_stats(days=days)

    return {
        "success": True,
        "data": {
            "days": days,
            "stats": daily_stats
        }
    }


@router.get("/models")
async def get_model_stats():
    """
    获取各模型使用统计

    Returns:
        模型使用统计信息
    """
    tracker = get_token_usage_tracker()
    model_stats = await tracker.get_model_stats()

    return {
        "success": True,
        "data": model_stats
    }


@router.get("/errors")
async def get_error_stats():
    """
    获取错误统计

    Returns:
        错误统计信息
    """
    tracker = get_token_usage_tracker()
    error_stats = await tracker.get_error_stats()

    return {
        "success": True,
        "data": {
            "total_errors": sum(stats["count"] for stats in error_stats),
            "errors": error_stats
        }
    }


@router.get("/breakdown")
async def get_usage_breakdown(
    hours: int = Query(24, ge=1, le=720, description="统计时间范围（小时）"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="返回记录数量限制")
):
    """
    获取使用情况分解

    Args:
        hours: 统计时间范围（小时）
        limit: 返回记录数量限制

    Returns:
        使用情况分解信息
    """
    tracker = get_token_usage_tracker()
    stats = await tracker.get_usage_stats(hours=hours, limit=limit)

    return {
        "success": True,
        "data": stats
    }


@router.get("/history")
async def get_token_history(
    token_key: Optional[str] = Query(None, description="token_key筛选"),
    hours: int = Query(24, ge=1, le=720, description="统计时间范围（小时）"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数量")
):
    """
    获取token使用历史记录

    Args:
        token_key: token_key筛选（None表示获取所有）
        hours: 统计时间范围（小时）
        limit: 返回记录数量

    Returns:
        Token使用历史记录
    """
    tracker = get_token_usage_tracker()
    stats = await tracker.get_usage_stats(token_key=token_key, hours=hours, limit=limit)

    # 格式化历史记录
    history = []
    for record in stats.get("requests", []):
        history.append({
            "timestamp": record["timestamp"],
            "request_id": record["request_id"],
            "input_tokens": record["input_tokens"],
            "output_tokens": record["output_tokens"],
            "total_tokens": record["total_tokens"],
            "model": record["model"],
            "cost": record["cost"],
            "error": record.get("error")
        })

    return {
        "success": True,
        "data": {
            "token_key": stats.get("token_key"),
            "total_requests": stats.get("total_requests"),
            "total_tokens": stats.get("total_tokens"),
            "total_cost": stats.get("total_cost"),
            "input_tokens": stats.get("input_tokens"),
            "output_tokens": stats.get("output_tokens"),
            "requests": history
        }
    }


@router.get("/top-tokens")
async def get_top_tokens(
    hours: int = Query(24, ge=1, le=720, description="统计时间范围（小时）"),
    limit: int = Query(10, ge=1, le=100, description="返回数量")
):
    """
    获取token使用量排行

    Args:
        hours: 统计时间范围（小时）
        limit: 返回数量

    Returns:
        Token使用量排行
    """
    tracker = get_token_usage_tracker()
    stats = await tracker.get_usage_stats(hours=hours, limit=limit)

    # 获取top tokens
    top_tokens = stats.get("usage_breakdown", [])[:limit]

    return {
        "success": True,
        "data": {
            "time_range_hours": hours,
            "top_tokens": top_tokens
        }
    }


@router.delete("/cleanup")
async def cleanup_old_data(days: int = Query(30, ge=7, le=365, description="清理天数") ):
    """
    清理旧数据

    Args:
        days: 清理的天数

    Returns:
        清理结果
    """
    tracker = get_token_usage_tracker()
    cleaned = await tracker.cleanup_old_data(days=days)

    return {
        "success": True,
        "message": f"已清理 {cleaned} 条旧数据",
        "data": {
            "cleaned_count": cleaned,
            "days_to_keep": days
        }
    }
