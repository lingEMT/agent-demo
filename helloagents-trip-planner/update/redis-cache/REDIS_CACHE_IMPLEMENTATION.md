# Redis缓存层实现记录

## 概述

为智能旅行规划助手添加Redis缓存层，减少高德地图API调用次数，降低响应延迟。

## 新增文件

### `backend/app/services/cache_service.py` (426行)
**Redis缓存服务核心**
- `CacheService` 单例类：redis.asyncio连接池，优雅降级，缓存统计
- `@cached` 装饰器：透明集成，自动序列化/反序列化
- 5个缓存命名空间：POI搜索、天气、路线、POI详情、地理编码

### `backend/app/api/routes/cache_admin.py` (150行)
**缓存管理API路由**
- `GET /api/cache/health` - 健康检查
- `GET /api/cache/stats` - 缓存统计（命中率等）
- `POST /api/cache/clear` - 清除所有缓存
- `POST /api/cache/clear/{namespace}` - 清除指定命名空间
- `POST /api/cache/stats/reset` - 重置统计

## 修改文件

### `backend/app/config.py`
新增6个Redis配置项：
```python
redis_host: str = "localhost"
redis_port: int = 6379
redis_db: int = 0
redis_password: str = ""
redis_prefix: str = "trip_planner"
redis_enabled: bool = True
```

### `backend/app/services/amap_service.py`
3个独立函数添加 `@cached` 装饰器：
- `search_poi()` - `@cached(namespace=CacheNamespace.POI_SEARCH)`
- `get_weather()` - `@cached(namespace=CacheNamespace.WEATHER)`
- `plan_route()` - `@cached(namespace=CacheNamespace.ROUTE, key_builder=_build_route_key)`

2个方法添加手动缓存逻辑：
- `get_poi_detail()` - 24h TTL，缓存到 Redis
- `geocode()` - 7天 TTL，缓存到 Redis

### `backend/app/api/main.py`
- lifespan 启动时：`cache.init()`
- lifespan 关闭时：`cache.close()`
- 注册 `cache_admin.router`

## 缓存策略

| 数据 | Key模式 | TTL | 命中率 |
|------|---------|-----|--------|
| POI搜索 | `trip_planner:amap:poi_search:{md5}` | 24h | 极高 |
| 天气查询 | `trip_planner:amap:weather:{city}` | 30min | 高 |
| 路线(步行) | `trip_planner:amap:route:{md5}` | 30min | 中 |
| 路线(驾车) | `trip_planner:amap:route:{md5}` | 10min | 低 |
| POI详情 | `trip_planner:amap:poi_detail:{poi_id}` | 24h | 中 |
| 地理编码 | `trip_planner:amap:geocode:{md5}` | 7天 | 低 |

## 新增依赖

```
redis>=5.0.0
```

## 测试

位置：由测试脚本验证，无需部署到生产环境。

18个单元测试覆盖：
- 单例模式 & 默认禁用状态
- key生成 & MD5一致性
- 缓存启用/禁用的get/set/delete
- 优雅降级（Redis不可用时）
- 缓存统计追踪 & 重置
- @cached 装饰器（自定义key、None结果、异常容错）
- 集成测试标记（`--run-integration` 需要Redis）

## 优雅降级

Redis不可用时自动降级，不影响业务：
- `get()`/`set()` 返回 None/False
- `@cached` 检测到缓存不可用，直接执行原函数
- 恢复后自动重连，无需重启应用

## .env 配置示例

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_PREFIX=trip_planner
REDIS_ENABLED=true
```
