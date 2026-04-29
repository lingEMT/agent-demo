"""
历史记录 API 路由

提供旅行计划的持久化 CRUD 接口。
遵循 trip.py 的错误处理模式（try/except + HTTPException）。
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ...services.history_service import get_history_service

router = APIRouter(prefix="/history", tags=["历史记录"])


def _record_to_summary(record) -> dict:
    """将 TripRecord 转换为列表摘要"""
    return {
        "id": record.id,
        "title": record.title,
        "city": record.city,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _record_to_detail(record) -> dict:
    """将 TripRecord 转换为完整详情（含 JSON 数据）"""
    result = _record_to_summary(record)
    # request_data 和 plan_data 是 JSON 字符串，需要反序列化
    result["request_data"] = json.loads(record.request_data) if isinstance(record.request_data, str) else record.request_data
    result["plan_data"] = json.loads(record.plan_data) if isinstance(record.plan_data, str) else record.plan_data
    return result


@router.post(
    "/save",
    summary="保存旅行计划",
    description="将生成的旅行计划持久化存储",
)
async def save_trip(
    session_id: str = Query(..., description="前端身份标识"),
    title: str = Query(..., description="计划标题"),
    request_data: str = Query(..., description="旅行请求数据（JSON字符串）"),
    plan_data: Optional[str] = Query(None, description="旅行计划数据（JSON字符串，可选）"),
):
    """
    保存旅行计划

    Args:
        session_id: 前端 localStorage 生成的 UUID
        title: 计划标题
        request_data: 旅行请求 JSON 字符串
        plan_data: 旅行计划 JSON 字符串（可选）

    Returns:
        保存的记录摘要
    """
    try:
        # 解析 JSON 字符串
        request_dict = json.loads(request_data)
        plan_dict = json.loads(plan_data) if plan_data else None

        service = get_history_service()
        record = await service.save_trip(
            session_id=session_id,
            title=title,
            request_data=request_dict,
            plan_data=plan_dict,
        )
        return {"success": True, "data": _record_to_summary(record)}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {str(e)}")
    except Exception as e:
        print(f"[ERROR] 保存历史记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.get(
    "/list",
    summary="获取历史记录列表",
    description="获取当前用户的历史旅行计划列表（分页）",
)
async def list_trips(
    session_id: str = Query(..., description="前端身份标识"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    获取历史旅行计划列表

    Args:
        session_id: 前端 localStorage 生成的 UUID
        page: 页码
        page_size: 每页数量

    Returns:
        分页的记录列表
    """
    try:
        service = get_history_service()
        records, total = await service.list_trips(
            session_id=session_id,
            page=page,
            page_size=page_size,
        )
        return {
            "success": True,
            "data": [_record_to_summary(r) for r in records],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        print(f"[ERROR] 获取历史记录列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.get(
    "/{record_id}",
    summary="获取旅行计划详情",
    description="根据记录ID获取完整的旅行计划数据",
)
async def get_trip(record_id: str):
    """
    获取单个旅行计划详情

    Args:
        record_id: 记录 UUID

    Returns:
        包含 request_data 和 plan_data 的完整记录
    """
    try:
        service = get_history_service()
        record = await service.get_trip(record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="记录不存在")
        return {"success": True, "data": _record_to_detail(record)}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 获取历史记录详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")


@router.delete(
    "/{record_id}",
    summary="删除旅行计划",
    description="删除指定的历史旅行计划记录",
)
async def delete_trip(record_id: str):
    """
    删除旅行计划

    Args:
        record_id: 记录 UUID

    Returns:
        删除结果
    """
    try:
        service = get_history_service()
        deleted = await service.delete_trip(record_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="记录不存在")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 删除历史记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
