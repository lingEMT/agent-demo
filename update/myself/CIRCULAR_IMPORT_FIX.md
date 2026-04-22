# 循环导入错误修复总结

## 🔧 问题描述

**错误信息**：
```
ImportError: cannot import name 'get_monitored_llm' from 'app.services.llm_monitor'
```

**根本原因**：
- `llm_service.py` 导入 `get_monitored_llm` 从 `llm_monitor.py`
- `llm_monitor.py` 导入 `get_llm` 从 `llm_service.py`
- 形成循环依赖

---

## ✅ 解决方案

### 1. 移除循环依赖

**修改 `llm_monitor.py`**：
```python
# ❌ 删除这行
from ..services.llm_service import get_llm

# ✅ 添加自己的LLM创建逻辑
class LLMMonitor:
    @staticmethod
    def _create_llm_instance() -> ChatOpenAI:
        settings = get_settings()
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or settings.openai_api_key
        api_key_secret = SecretStr(api_key)
        base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or settings.openai_base_url
        model = os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or settings.openai_model

        return ChatOpenAI(
            api_key=api_key_secret,
            base_url=base_url,
            model=model,
            temperature=0.7
        )
```

**修改 `llm_service.py`**：
```python
# ❌ 删除这行
from .llm_monitor import get_monitored_llm

# ✅ 修改为
from .llm_monitor import LLMMonitor

# ❌ 修改这行
_llm_instance = get_monitored_llm(token_key or "default")

# ✅ 改为
_llm_instance = LLMMonitor.get_monitored_llm(token_key or "default")
```

---

### 2. 修复 Pydantic 属性设置错误

**问题**：LangChain 的 `ChatOpenAI` 类不支持直接设置自定义属性

**解决方案**：使用实例变量而不是属性
```python
class MonitorableChatOpenAI(ChatOpenAI):
    def __init__(self, token_key: str, **kwargs):
        super().__init__(**kwargs)
        # ✅ 使用实例变量
        self._token_key = token_key
        self._callbacks = kwargs.get('callbacks', [])

        # 添加token使用监控回调
        if not any(isinstance(cb, TokenUsageCallback) for cb in self._callbacks):
            self._callbacks.append(TokenUsageCallback(token_key))

    # ✅ 添加属性访问器
    @property
    def token_key(self) -> str:
        return self._token_key

    @token_key.setter
    def token_key(self, value: str):
        self._token_key = value
```

---

## ✅ 验证结果

### 1. 导入测试
```bash
python -c "from app.services.llm_service import get_llm; print('导入成功')"
# 输出: LLM服务导入成功
```

### 2. 服务启动测试
```bash
python -c "from app.services.llm_service import get_llm; llm = get_llm(); print('LLM实例创建成功')"
# 输出: LLM服务导入成功
# 输出: LLM实例创建成功: MonitorableChatOpenAI
```

### 3. Token追踪器测试
```bash
python -c "from app.services.token_usage_tracker import get_token_usage_tracker; print('Token追踪器初始化成功')"
# 输出: Token追踪器初始化成功: TokenUsageTracker
```

---

## 📝 修改文件

- `backend/app/services/llm_monitor.py`
  - 移除对 `get_llm` 的导入
  - 添加 `_create_llm_instance()` 方法
  - 修复 `MonitorableChatOpenAI` 类的属性设置

- `backend/app/services/llm_service.py`
  - 导入 `LLMMonitor` 而不是 `get_monitored_llm`
  - 调用 `LLMMonitor.get_monitored_llm()` 而不是 `get_monitored_llm()`

---

## 🚀 后续注意事项

1. **避免循环依赖**：
   - 模块A导入模块B，模块B不要导入模块A
   - 尽量使用依赖注入而不是直接导入

2. **延迟导入**：
   - 在函数内部导入而不是模块级别导入
   - 减少启动时的循环检查

3. **抽象层**：
   - 创建接口或抽象类来解耦依赖
   - 使用依赖注入模式

---

**修复时间**：2026-04-23
**验证状态**：✅ 通过
**状态**：已解决
