"""
缓存管理API路由

提供缓存的健康检查、统计和清理功能。
"""
from fastapi import APIRouter, HTTPException

from ...services.cache_service import CacheNamespace, get_cache_service

router = APIRouter(prefix="/cache", tags=["缓存管理"])

# 命名空间信息（用于展示）
NAMESPACE_INFO = {
    "poi_search": {
        "name": "POI搜索",
        "ttl_seconds": 86400,
        "ttl_display": "24小时",
        "hit_rate": "极高",
    },
    "weather": {
        "name": "天气查询",
        "ttl_seconds": 1800,
        "ttl_display": "30分钟",
        "hit_rate": "高",
    },
    "route": {
        "name": "路线规划",
        "ttl_seconds": 1800,
        "ttl_display": "30分钟(步行) / 10分钟(驾车)",
        "hit_rate": "中",
    },
    "poi_detail": {
        "name": "POI详情",
        "ttl_seconds": 86400,
        "ttl_display": "24小时",
        "hit_rate": "中",
    },
    "geocode": {
        "name": "地理编码",
        "ttl_seconds": 604800,
        "ttl_display": "7天",
        "hit_rate": "低",
    },
}


@router.get("/health")
async def cache_health():
    """缓存健康检查"""
    cache = get_cache_service()
    health = await cache.health_check()
    return {"success": True, "data": health}


@router.get("/stats")
async def cache_stats():
    """获取缓存统计信息"""
    cache = get_cache_service()
    stats = await cache.get_stats()

    namespaces = [
        {
            "key": ns.value.split(":")[-1],
            "full_key": ns.value,
            "info": NAMESPACE_INFO.get(ns.value.split(":")[-1], {}),
        }
        for ns in CacheNamespace
    ]

    return {
        "success": True,
        "data": {
            "stats": stats,
            "enabled": cache.enabled,
            "namespaces": namespaces,
        },
    }


@router.post("/clear")
async def clear_all_cache():
    """清除所有缓存"""
    cache = get_cache_service()
    if not cache.enabled:
        raise HTTPException(status_code=503, detail="缓存服务未启用")

    deleted = await cache.clear_all()
    await cache.reset_stats()

    return {
        "success": True,
        "message": f"已清除 {deleted} 个缓存",
        "data": {"deleted_count": deleted},
    }


@router.post("/clear/{namespace}")
async def clear_namespace(namespace: str):
    """清除指定命名空间的缓存"""
    ns_map = {}
    for ns in CacheNamespace:
        short_name = ns.value.split(":")[-1]
        ns_map[short_name] = ns
        ns_map[ns.value] = ns

    if namespace not in ns_map:
        valid = sorted(NAMESPACE_INFO.keys())
        raise HTTPException(
            status_code=400,
            detail=f"无效的命名空间: {namespace}。有效值: {', '.join(valid)}",
        )

    cache = get_cache_service()
    if not cache.enabled:
        raise HTTPException(status_code=503, detail="缓存服务未启用")

    selected_ns = ns_map[namespace]
    deleted = await cache.clear_namespace(selected_ns)

    return {
        "success": True,
        "message": f"已清除命名空间 {selected_ns.value} 的 {deleted} 个缓存",
        "data": {"namespace": selected_ns.value, "deleted_count": deleted},
    }


@router.post("/stats/reset")
async def reset_cache_stats():
    """重置缓存统计信息"""
    cache = get_cache_service()
    await cache.reset_stats()
    return {"success": True, "message": "缓存统计已重置"}
