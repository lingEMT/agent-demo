"""LLM监控服务 - 拦截并记录token使用"""

import time
import uuid
import os
from typing import Dict, Any, Optional, List
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler
from ..config import get_settings
from ..services.token_usage_tracker import get_token_usage_tracker


class TokenUsageCallback(BaseCallbackHandler):
    """Token使用量回调处理器"""

    def __init__(self, token_key: str, request_id: Optional[str] = None):
        super().__init__()
        self.token_key = token_key
        self.request_id = request_id or str(uuid.uuid4())
        self.input_tokens = 0
        self.output_tokens = 0
        self.model = "unknown"
        self.cost = 0.0
        self.error = None

    async def on_llm_start(
        self,
        serialized: Optional[Dict[str, Any]],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """LLM开始调用时"""
        self._start_time = time.time()

    async def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """LLM调用成功结束"""
        try:
            if hasattr(response, 'llm_output'):
                llm_output = response.llm_output or {}
                self.input_tokens = llm_output.get('token_usage', {}).get('prompt_tokens', 0)
                self.output_tokens = llm_output.get('token_usage', {}).get('completion_tokens', 0)
                self.model = llm_output.get('model', 'unknown')

                # 计算成本（基于GPT-4.0的价格）
                # input: $0.03/1K tokens, output: $0.06/1K tokens
                if self.model.startswith('gpt-4'):
                    self.cost = (self.input_tokens / 1000 * 0.03) + (self.output_tokens / 1000 * 0.06)
                elif self.model.startswith('gpt-3.5'):
                    self.cost = (self.input_tokens / 1000 * 0.002) + (self.output_tokens / 1000 * 0.002)

            # 记录到追踪器
            tracker = get_token_usage_tracker()
            await tracker.record_usage(
                token_key=self.token_key,
                request_id=self.request_id,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
                model=self.model,
                cost=self.cost
            )

            self._end_time = time.time()
            print(f"[OK] Token监控 - {self.token_key} - "
                  f"请求: {self.input_tokens}+{self.output_tokens} tokens - "
                  f"成本: ¥{self.cost:.4f}")

        except Exception as e:
            self.error = str(e)
            print(f"[ERROR] Token监控失败: {e}")

    async def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """LLM调用失败"""
        self.error = str(error)
        tracker = get_token_usage_tracker()
        await tracker.record_usage(
            token_key=self.token_key,
            request_id=self.request_id,
            input_tokens=0,
            output_tokens=0,
            model="unknown",
            cost=0.0,
            error=error
        )


class MonitorableChatOpenAI(ChatOpenAI):
    """可监控的ChatOpenAI包装器"""

    def __init__(self, token_key: str, **kwargs):
        super().__init__(**kwargs)
        # 使用实例变量而不是属性，避免Pydantic错误
        self._token_key = token_key
        self._callbacks = kwargs.get('callbacks', [])

        # 添加token使用监控回调
        if not any(isinstance(cb, TokenUsageCallback) for cb in self._callbacks):
            self._callbacks.append(TokenUsageCallback(token_key))

    def __call__(self, messages, **kwargs):
        """调用时使用回调"""
        response = super().__call__(messages, **kwargs)

        # 触发回调
        for callback in self._callbacks:
            import asyncio
            if isinstance(callback, TokenUsageCallback):
                asyncio.create_task(callback.on_llm_end(response))

        return response

    def bind_tools(self, tools, **kwargs):
        """绑定工具时使用回调"""
        new_instance = super().bind_tools(tools, **kwargs)
        if isinstance(new_instance, MonitorableChatOpenAI):
            new_instance._token_key = self._token_key
            new_instance._callbacks = self._callbacks
        return new_instance

    @property
    def token_key(self) -> str:
        """获取token_key"""
        return self._token_key

    @token_key.setter
    def token_key(self, value: str):
        """设置token_key"""
        self._token_key = value


class LLMMonitor:
    """LLM监控工具"""

    @staticmethod
    def _create_llm_instance() -> ChatOpenAI:
        """
        创建LLM实例（复用llm_service的逻辑）

        Returns:
            ChatOpenAI实例
        """
        settings = get_settings()

        # 从环境变量读取配置
        api_key = os.getenv("LLM_API_KEY") or settings.llm_api_key
        api_key_secret = SecretStr(api_key)
        base_url = os.getenv("LLM_BASE_URL") or settings.llm_base_url
        model = os.getenv("LLM_MODEL_ID") or settings.llm_model

        if not api_key:
            raise ValueError("LLM API Key未配置,请设置环境变量 LLM_API_KEY")

        return ChatOpenAI(
            api_key=api_key_secret,
            base_url=base_url,
            model=model,
            temperature=0.7
        )

    @staticmethod
    def get_monitored_llm(token_key: str) -> ChatOpenAI:
        """
        获取可监控的LLM实例

        Args:
            token_key: 调用者标识（如用户ID、API端点等）

        Returns:
            可监控的ChatOpenAI实例
        """
        llm = LLMMonitor._create_llm_instance()

        # 检查是否已经是可监控的实例
        if isinstance(llm, MonitorableChatOpenAI):
            llm.token_key = token_key
            return llm

        # 创建可监控实例
        return MonitorableChatOpenAI(token_key=token_key)

    @staticmethod
    def get_default_token_key() -> str:
        """获取默认的token_key"""
        # 尝试从环境变量获取
        import os
        token_key = os.getenv("TOKEN_KEY", "default")

        # 如果有用户认证，使用用户ID
        # 这里简化处理，返回default
        return token_key
