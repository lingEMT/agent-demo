"""LLM服务模块 - 使用LangChain"""

import os
from typing import Optional

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from ..config import get_settings
from .llm_monitor import LLMMonitor

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

        # 从配置实例读取配置
        api_key = settings.llm_api_key
        # api_key_secret = SecretStr(api_key)
        base_url = settings.llm_base_url
        model = settings.llm_model

        if not api_key:
            raise ValueError("LLM API Key未配置,请设置环境变量 LLM_API_KEY")

        # 创建可监控的ChatOpenAI实例
        _llm_instance = LLMMonitor.get_monitored_llm(token_key or "default")

        print(f"[OK] LLM服务初始化成功 (LangChain)")
        print(f"   Base URL: {base_url}")
        print(f"   模型: {model}")
        print(f"   Token Key: {token_key or 'default'}")

    return _llm_instance


def reset_llm():
    """重置LLM实例(用于测试或重新配置)"""
    global _llm_instance
    _llm_instance = None
