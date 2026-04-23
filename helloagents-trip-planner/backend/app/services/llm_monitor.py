"""LLM监控服务 - 拦截并记录token使用"""

import time
import uuid
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler
from ..config import get_settings
from ..services.token_usage_tracker import get_token_usage_tracker


class TokenUsageCallback(BaseCallbackHandler):
    """Token使用量回调处理器"""

    def __init__(self, token_key: Optional[str] = None, request_id: Optional[str] = None):
        super().__init__()
        self.token_key = token_key or "default"
        self.request_id = request_id or str(uuid.uuid4())
        self.input_tokens = 0
        self.output_tokens = 0
        self.model = "unknown"
        self.cost = 0.0
        self.error = None

    async def on_llm_start(
        self,
        serialized: Optional[dict],
        prompts: list,
        **kwargs
    ) -> None:
        """LLM开始调用时"""
        self._start_time = time.time()

    async def on_llm_end(self, response, **kwargs) -> None:
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

    async def on_llm_error(self, error: Exception, **kwargs) -> None:
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


def create_llm_with_monitoring(
    llm: ChatOpenAI,
    token_key: Optional[str] = None,
    request_id: Optional[str] = None
) -> ChatOpenAI:
    """
    为现有的LLM实例添加监控回调

    Args:
        llm: 基础 LLM 实例
        token_key: 调用者标识
        request_id: 请求ID（可选）

    Returns:
        带监控的 LLM 实例（同一个对象，但添加了回调）
    """
    # 检查是否已经有回调
    if not llm.callbacks:
        llm.callbacks = []

    # 创建回调实例
    callback = TokenUsageCallback(token_key=token_key, request_id=request_id)
    llm.callbacks.append(callback)

    return llm
