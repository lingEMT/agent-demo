"""LLM服务模块 - 使用LangChain"""

import os
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from ..config import get_settings
from .llm_monitor import get_monitored_llm

# 全局LLM实例
_llm_instance = None


def get_llm(token_key: Optional[str] = None) -> ChatOpenAI:
    """
    获取LLM实例(单例模式)

    Args:
        token_key: 调用者标识，用于token追踪

    Returns:
        ChatOpenAI实例
    """
    global _llm_instance

    if _llm_instance is None:
        settings = get_settings()

        # 从环境变量读取配置
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or settings.openai_api_key
        api_key_secret = SecretStr(api_key)
        base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or settings.openai_base_url
        model = os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or settings.openai_model

        if not api_key:
            raise ValueError("LLM API Key未配置,请设置环境变量 LLM_API_KEY 或 OPENAI_API_KEY")

        # 创建可监控的ChatOpenAI实例
        _llm_instance = get_monitored_llm(token_key or "default")

        print(f"[OK] LLM服务初始化成功 (LangChain)")
        print(f"   Base URL: {base_url}")
        print(f"   模型: {model}")

    return _llm_instance


def reset_llm():
    """重置LLM实例(用于测试或重新配置)"""
    global _llm_instance
    _llm_instance = None
