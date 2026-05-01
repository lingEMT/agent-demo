"""
Redis缓存服务核心

提供：
1. CacheService - 单例模式，redis.asyncio连接池，优雅降级
2. @cached 装饰器 - 透明集成，无需修改业务逻辑
3. 命名空间前缀 trip_planner: 避免key冲突
4. 内置缓存统计（命中/未命中/错误）
"""
import functools
import hashlib
import json
import time
from enum import Enum
from typing import Any, Callable, Optional

import redis.asyncio as aioredis

from ..config import get_settings


class CacheNamespace(str, Enum):
    """缓存命名空间"""

    POI_SEARCH = "amap:poi_search"
    WEATHER = "amap:weather"
    ROUTE = "amap:route"
    POI_DETAIL = "amap:poi_detail"
    GEOCODE = "amap:geocode"
    LLM_RESPONSE = "llm:response"


# 缓存TTL配置（单位：秒）
CACHE_TTL = {
    CacheNamespace.POI_SEARCH: 86400,       # 24小时
    CacheNamespace.WEATHER: 1800,           # 30分钟
    CacheNamespace.ROUTE: 1800,             # 30分钟（步行默认）
    CacheNamespace.POI_DETAIL: 86400,       # 24小时
    CacheNamespace.GEOCODE: 604800,         # 7天
    CacheNamespace.LLM_RESPONSE: 3600,      # 1小时
}

# 不同路线类型的不同TTL
ROUTE_TTL_OVERRIDES = {
    "walking": 1800,    # 30分钟
    "driving": 600,     # 10分钟
    "transit": 1200,    # 20分钟
}


class CacheService:
    """
    Redis缓存服务（单例模式）

    特性：
    - 连接池复用
    - 优雅降级（Redis不可用时自动跳过）
    - 缓存统计（命中/未命中/错误数）
    - 按命名空间管理
    """

    _instance = None
    _pool = None
    _client: Optional[aioredis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._stats = {
                "hits": 0,
                "misses": 0,
                "errors": 0,
                "last_error": None,
            }
        return cls._instance

    async def init(self):
        """初始化Redis连接池"""
        settings = get_settings()

        if not settings.redis_enabled:
            print("[CACHE] Redis缓存未启用 (redis_enabled=False)")
            self._enabled = False
            return

        try:
            self._pool = aioredis.ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                retry_on_timeout=False,
                health_check_interval=30,
            )
            self._client = aioredis.Redis(connection_pool=self._pool)

            # 测试连接
            await self._client.ping()
            self._enabled = True
            print(f"[CACHE] Redis缓存已连接: {settings.redis_host}:{settings.redis_port}/{settings.redis_db}")

        except Exception as e:
            self._enabled = False
            print(f"[CACHE] Redis连接失败，缓存将优雅降级: {e}")
            if self._pool:
                await self._pool.disconnect()
                self._pool = None
            self._client = None

    async def close(self):
        """关闭Redis连接"""
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None
        if self._pool:
            try:
                await self._pool.disconnect()
            except Exception:
                pass
            self._pool = None
        self._enabled = False
        print("[CACHE] Redis连接已关闭")

    @property
    def enabled(self) -> bool:
        """缓存是否可用"""
        return self._enabled

    @staticmethod
    def _make_key(namespace: CacheNamespace, key: str) -> str:
        """生成完整的缓存key（带命名空间前缀）"""
        prefix = get_settings().redis_prefix
        return f"{prefix}:{namespace.value}:{key}"

    @staticmethod
    def _md5(text: str) -> str:
        """计算MD5哈希"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    async def get(self, namespace: CacheNamespace, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            namespace: 缓存命名空间
            key: 缓存键

        Returns:
            缓存的数据(已反序列化)，未命中返回None
        """
        if not self._enabled or not self._client:
            return None

        full_key = self._make_key(namespace, key)
        try:
            data = await self._client.get(full_key)
            if data is not None:
                self._stats["hits"] += 1
                return json.loads(data)
            self._stats["misses"] += 1
            return None
        except Exception as e:
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            return None

    async def set(
        self,
        namespace: CacheNamespace,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存

        Args:
            namespace: 缓存命名空间
            key: 缓存键
            value: 要缓存的数据（必须是JSON可序列化的）
            ttl: 过期时间(秒)。为None时使用命名空间默认TTL

        Returns:
            是否成功
        """
        if not self._enabled or not self._client:
            return False

        full_key = self._make_key(namespace, key)
        effective_ttl = ttl if ttl is not None else CACHE_TTL.get(namespace, 300)

        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            await self._client.setex(full_key, effective_ttl, serialized)
            return True
        except Exception as e:
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            return False

    async def delete(self, namespace: CacheNamespace, key: str) -> bool:
        """删除单个缓存"""
        if not self._enabled or not self._client:
            return False

        full_key = self._make_key(namespace, key)
        try:
            deleted = await self._client.delete(full_key)
            return deleted > 0
        except Exception:
            return False

    async def clear_namespace(self, namespace: CacheNamespace) -> int:
        """
        清除指定命名空间下的所有缓存

        Args:
            namespace: 要清除的命名空间

        Returns:
            删除的key数量
        """
        if not self._enabled or not self._client:
            return 0

        prefix = get_settings().redis_prefix
        pattern = f"{prefix}:{namespace.value}:*"
        try:
            cursor = 0
            deleted_count = 0
            while True:
                cursor, keys = await self._client.scan(
                    cursor=cursor, match=pattern, count=100
                )
                if keys:
                    deleted_count += await self._client.delete(*keys)
                if cursor == 0:
                    break
            return deleted_count
        except Exception as e:
            print(f"[CACHE] 清除命名空间 {namespace.value} 失败: {e}")
            return 0

    async def clear_all(self) -> int:
        """
        清除所有缓存（仅限本应用前缀的key）

        Returns:
            删除的key数量
        """
        if not self._enabled or not self._client:
            return 0

        prefix = get_settings().redis_prefix
        pattern = f"{prefix}:*"
        try:
            cursor = 0
            total_deleted = 0
            while True:
                cursor, keys = await self._client.scan(
                    cursor=cursor, match=pattern, count=200
                )
                if keys:
                    total_deleted += await self._client.delete(*keys)
                if cursor == 0:
                    break
            return total_deleted
        except Exception as e:
            print(f"[CACHE] 清除所有缓存失败: {e}")
            return 0

    async def health_check(self) -> dict:
        """
        缓存健康检查

        Returns:
            健康状态信息
        """
        status = "disconnected"
        latency_ms = None

        if self._enabled and self._client:
            try:
                start = time.time()
                await self._client.ping()
                latency_ms = round((time.time() - start) * 1000, 2)
                status = "connected"
            except Exception as e:
                status = f"error: {e}"

        return {
            "status": status,
            "enabled": self._enabled,
            "latency_ms": latency_ms,
            "stats": dict(self._stats),
        }

    async def get_stats(self) -> dict:
        """
        获取缓存统计信息

        Returns:
            {
                "hits": int,
                "misses": int,
                "hit_rate": float,
                "errors": int,
                "last_error": Optional[str],
                "total_requests": int,
            }
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = round(self._stats["hits"] / total, 4) if total > 0 else 0.0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "errors": self._stats["errors"],
            "last_error": self._stats["last_error"],
            "total_requests": total,
        }

    async def reset_stats(self):
        """重置缓存统计"""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "last_error": None,
        }


# ============ 全局单例访问器 ============

_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取缓存服务实例（单例）"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# ============ @cached 装饰器 ============

def cached(
    namespace: CacheNamespace,
    key_builder: Optional[Callable[..., str]] = None,
    ttl: Optional[int] = None,
):
    """
    缓存装饰器 - 透明地为异步函数添加缓存

    用法:
        @cached(namespace=CacheNamespace.POI_SEARCH)
        async def search_poi(keywords: str, city: str) -> List[POIInfo]:
            ...

    原理:
        1. 首次调用: 执行原函数 -> 序列化结果 -> 写入Redis
        2. 后续调用: 读取Redis缓存 -> 反序列化 -> 直接返回
        3. Redis不可用时: 自动降级，始终执行原函数，不影响业务

    Args:
        namespace: 缓存命名空间
        key_builder: 自定义key生成函数，接收原函数的所有参数，返回字符串key
                     为None时自动使用参数JSON的MD5作为key
        ttl: 缓存过期时间(秒)，为None时使用命名空间默认TTL

    Returns:
        装饰后的异步函数
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            cache = get_cache_service()

            # 缓存未启用时直接执行原函数
            if not cache.enabled:
                return await func(*args, **kwargs)

            # 生成缓存key
            if key_builder is not None:
                cache_key = key_builder(*args, **kwargs)
            else:
                raw = json.dumps({"args": str(args), "kwargs": kwargs}, sort_keys=True)
                cache_key = CacheService._md5(raw)

            # 尝试从缓存读取
            cached_value = await cache.get(namespace, cache_key)
            if cached_value is not None:
                return cached_value

            # 缓存未命中，执行原函数
            result = await func(*args, **kwargs)

            # 写入缓存（仅当结果不为None时）
            if result is not None:
                effective_ttl = ttl
                if effective_ttl is None and namespace == CacheNamespace.ROUTE:
                    route_type = kwargs.get("route_type", "walking")
                    effective_ttl = ROUTE_TTL_OVERRIDES.get(route_type, CACHE_TTL[namespace])
                await cache.set(namespace, cache_key, result, ttl=effective_ttl)

            return result

        return wrapper

    return decorator
