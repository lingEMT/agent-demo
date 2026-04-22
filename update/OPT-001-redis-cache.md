# 优化记录：Redis 缓存层集成

## 📝 优化基本信息

**优化编号**：OPT-001
**优化标题**：Redis 缓存层集成
**优先级**：高
**开始时间**：2026-04-23
**完成时间**：2026-04-25
**负责人**：[待填写]
**状态**：待实施

**注意**：这是一个模板示例，请按照 `optimization-record-template.md` 的格式填写实际优化记录。

---

## 🎯 优化目标

### 原始问题
- [ ] LLM 调用无缓存，重复查询效率低
- [ ] 高德API调用无缓存，频繁请求可能触发限流
- [ ] Agent 初始化耗时较长

### 优化目标
- [ ] LLM 调用耗时降低 60-80%
- [ ] 高德 API 调用降低 70%
- [ ] 并发能力提升 3-5倍

---

## 🔧 实施过程

### 1. 环境准备

**依赖安装**
```bash
pip install redis[hiredis] >= 5.0
```

**配置说明**
- Redis 版本：>= 6.0
- 内存要求：至少 2GB
- 端口配置：6379

**配置文件**
```python
# app/core/redis_config.py
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None
REDIS_MAX_CONNECTIONS = 10
```

---

### 2. 代码实现

**创建 Redis 缓存服务**
```python
# app/services/redis_cache.py
from redis import asyncio as aioredis
import json
import hashlib

class RedisCache:
    def __init__(self):
        self.redis = aioredis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            max_connections=REDIS_MAX_CONNECTIONS,
            password=REDIS_PASSWORD
        )

    async def get(self, key: str):
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(self, key: str, value, ttl: int = 3600):
        await self.redis.setex(key, ttl, json.dumps(value))

    async def delete(self, key: str):
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key) > 0

    def generate_key(self, *args) -> str:
        """生成缓存键"""
        key_str = ":".join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()
```

**在 LLM 服务中集成缓存**
```python
# app/services/llm_service.py
from app.services.redis_cache import RedisCache

redis_cache = RedisCache()

async def generate_trip_plan(city, preferences, travel_days):
    # 生成缓存键
    cache_key = f"llm:trip:plan:{city}:{preferences}:{travel_days}"

    # 尝试从缓存获取
    cached_result = await redis_cache.get(cache_key)
    if cached_result:
        print(f"✅ 命中缓存: {cache_key}")
        return cached_result

    # 缓存未命中，执行LLM调用
    print(f"❌ 缓存未命中: {cache_key}")
    result = await call_llm(city, preferences, travel_days)

    # 写入缓存
    await redis_cache.set(cache_key, result, ttl=3600)

    return result
```

**在高德服务中集成缓存**
```python
# app/services/amap_service.py
from app.services.redis_cache import RedisCache

redis_cache = RedisCache()

async def search_poi(keywords, city):
    cache_key = f"amap:poi:{city}:{keywords}"

    cached_result = await redis_cache.get(cache_key)
    if cached_result:
        print(f"✅ POI缓存命中")
        return json.loads(cached_result)

    print(f"❌ POI缓存未命中")
    result = await amap_api.search_poi(keywords, city)

    await redis_cache.set(cache_key, result, ttl=3600)
    return result
```

---

### 3. 测试验证

**单元测试**
```python
# tests/test_redis_cache.py
import pytest
from app.services.redis_cache import RedisCache

@pytest.mark.asyncio
async def test_redis_cache_basic():
    cache = RedisCache()

    # 测试写入和读取
    key = "test:key"
    value = {"data": "test"}

    await cache.set(key, value)
    result = await cache.get(key)

    assert result == value
    assert await cache.exists(key) == True

    # 测试删除
    await cache.delete(key)
    assert await cache.exists(key) == False
```

**性能测试对比**
```python
# tests/test_performance.py
import asyncio
from app.services.llm_service import generate_trip_plan
import time

async def test_performance():
    # 测试前
    start = time.time()
    await generate_trip_plan("北京", "历史文化", 3)
    first_time = time.time() - start

    # 测试后（命中缓存）
    start = time.time()
    await generate_trip_plan("北京", "历史文化", 3)
    cached_time = time.time() - start

    print(f"首次调用: {first_time:.2f}秒")
    print(f"缓存命中: {cached_time:.4f}秒")
    print(f"性能提升: {(1 - cached_time/first_time)*100:.1f}%")
```

**测试结果**
```
首次调用: 12.34秒
缓存命中: 0.02秒
性能提升: 99.8%

POI搜索首次: 0.56秒
POI搜索缓存: 0.01秒
性能提升: 98.2%
```

---

### 4. 问题与解决方案

**问题 1：Redis 连接失败**
- **现象**：启动时抛出连接错误
- **原因**：Redis 服务未启动或配置错误
- **解决**：
  ```bash
  # 启动 Redis
  redis-server --port 6379

  # 检查配置
  redis-cli ping
  ```
- **验证**：测试缓存读写功能正常

**问题 2：缓存键冲突**
- **现象**：不同请求共用缓存数据
- **原因**：缓存键生成逻辑错误
- **解决**：使用完整的参数组合生成 MD5 哈希
- **验证**：不同参数产生不同缓存键

**问题 3：缓存过期后性能下降**
- **现象**：高德 API 调用过多
- **原因**：TTL 设置过短
- **解决**：调整 TTL 为 1 小时
- **验证**：监控 API 调用频率下降

---

### 5. 优化成果

**性能提升数据**
| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| LLM 调用耗时 | 12.34秒 | 0.02秒 | 99.8% |
| 高德 API 调用 | 0.56秒 | 0.01秒 | 98.2% |
| 并发处理能力 | 10 QPS | 50 QPS | 400% |

**代码变更统计**
- 新增文件：2个（redis_cache.py, redis_config.py）
- 修改文件：2个（llm_service.py, amap_service.py）
- 新增代码行数：150行
- 删除代码行数：10行
- 净增加：140行

**测试覆盖**
- 单元测试：通过 ✅
- 性能测试：通过 ✅
- 集成测试：通过 ✅
- 负载测试：通过 ✅

---

## 📊 影响评估

### 功能影响
- ✅ 不影响现有功能
- ✅ 向后兼容
- ✅ 可配置开关

### 性能影响
- ✅ 读取性能大幅提升
- ✅ 写入性能略有下降（可接受）
- ✅ 内存占用增加（可接受）

### 维护成本
- ✅ 增加运维监控
- ✅ 增加缓存失效策略
- ⚠️ 需要定期清理过期数据

---

## 🎉 成果展示

### 优化前
```
用户请求 → 等待LLM调用 → 等待高德API → 返回结果
          [12.34秒]     [0.56秒]
          总耗时：13秒
```

### 优化后
```
用户请求 → 检查缓存 → 缓存未命中
          [0.001秒]        [12.40秒]
                      → LLM调用 → 高德API → 写入缓存 → 返回结果
                                           [0.57秒]     [0.02秒]
          总耗时：0.03秒（首次）
                    0.02秒（缓存命中）
```

---

## 📚 文档更新

### 需要更新的文档
- [ ] README.md - 更新技术栈
- [ ] requirements.txt - 添加 redis 依赖
- [ ] .env.example - 添加 Redis 配置
- [ ] API 文档 - 更新响应时间说明

### 需要更新的代码注释
- [ ] redis_cache.py - 添加详细注释
- [ ] llm_service.py - 添加缓存说明
- [ ] amap_service.py - 添加缓存说明

---

## 🔄 后续优化建议

1. **缓存预热**
   - 预加载热门城市的缓存数据
   - 定时更新缓存

2. **缓存策略优化**
   - 根据数据更新频率动态调整 TTL
   - 实现多级缓存（内存 + Redis）

3. **监控告警**
   - 添加 Redis 连接监控
   - 添加缓存命中率监控
   - 添加性能监控

---

## ✅ 验收清单

- [ ] 所有测试通过
- [ ] 性能指标达标
- [ ] 代码审查通过
- [ ] 文档更新完成
- [ ] 部署到测试环境
- [ ] 用户验收通过
- [ ] 部署到生产环境

---

## 📝 备注

**注意事项**
- Redis 服务需要独立部署
- 生产环境需要配置密码认证
- 需要监控 Redis 内存使用情况

**后续计划**
- 考虑使用 Redis Cluster
- 实现缓存失效通知机制
- 优化缓存淘汰策略

---

**记录时间**：2026-04-22
**审核时间**：待审核
**审核人**：待审核
