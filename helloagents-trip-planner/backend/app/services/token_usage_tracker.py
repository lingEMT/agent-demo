"""Token使用量追踪服务"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, Counter
import threading


class TokenUsageTracker:
    """Token使用量追踪器"""

    def __init__(self):
        self._token_usage: Dict[str, List[Dict]] = defaultdict(list)  # key: token_key, value: list of usage records
        self._locks = defaultdict(threading.Lock)  # 每个token_key一个锁
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # 每小时清理一次旧数据

        # 初始化统计数据
        self._total_requests = 0
        self._total_tokens = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    async def record_usage(
        self,
        token_key: str,
        request_id: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
        cost: float,
        error: Optional[str] = None
    ):
        """
        记录token使用情况

        Args:
            token_key: 调用者标识（如用户ID、API端点等）
            request_id: 请求ID
            input_tokens: 输入token数
            output_tokens: 输出token数
            model: 模型名称
            cost: 成本（元）
            error: 错误信息（如果有）
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": model,
            "cost": cost,
            "error": error
        }

        with self._locks[token_key]:
            self._token_usage[token_key].append(record)
            self._total_requests += 1
            self._total_tokens += input_tokens + output_tokens
            self._total_input_tokens += input_tokens
            self._total_output_tokens += output_tokens

    async def get_usage_stats(
        self,
        token_key: Optional[str] = None,
        hours: int = 24,
        limit: Optional[int] = None
    ) -> Dict:
        """
        获取token使用统计

        Args:
            token_key: 调用者标识（None表示获取全局统计）
            hours: 时间范围（小时）
            limit: 限制返回的记录数量

        Returns:
            统计数据字典
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        if token_key:
            # 单个token_key的统计
            with self._locks[token_key]:
                records = [r for r in self._token_usage[token_key] if
                          datetime.fromisoformat(r["timestamp"]) >= cutoff_time]

                if limit:
                    records = records[-limit:]

                return {
                    "token_key": token_key,
                    "total_requests": len(records),
                    "total_tokens": sum(r["total_tokens"] for r in records),
                    "input_tokens": sum(r["input_tokens"] for r in records),
                    "output_tokens": sum(r["output_tokens"] for r in records),
                    "total_cost": sum(r["cost"] for r in records),
                    "requests": records
                }
        else:
            # 全局统计
            return {
                "token_key": "global",
                "total_requests": self._total_requests,
                "total_tokens": self._total_tokens,
                "input_tokens": self._total_input_tokens,
                "output_tokens": self._total_output_tokens,
                "total_cost": sum(r["cost"] for key in self._token_usage.values()
                                for r in key),
                "usage_breakdown": self._get_usage_breakdown(cutoff_time),
                "top_tokens": self._get_top_tokens(cutoff_time, limit)
            }

    async def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """获取每日统计"""
        cutoff_time = datetime.now() - timedelta(days=days)
        daily_stats = defaultdict(lambda: {
            "total_requests": 0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost": 0
        })

        for key in self._token_usage:
            for record in self._token_usage[key]:
                record_time = datetime.fromisoformat(record["timestamp"])
                if record_time >= cutoff_time:
                    day = record_time.date().isoformat()
                    daily_stats[day]["total_requests"] += 1
                    daily_stats[day]["total_tokens"] += record["total_tokens"]
                    daily_stats[day]["input_tokens"] += record["input_tokens"]
                    daily_stats[day]["output_tokens"] += record["output_tokens"]
                    daily_stats[day]["total_cost"] += record["cost"]

        return [
            {
                "date": day,
                **stats
            }
            for day, stats in sorted(daily_stats.items())
        ]

    async def get_model_stats(self) -> List[Dict]:
        """获取各模型使用统计"""
        model_stats = defaultdict(lambda: {
            "total_requests": 0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost": 0
        })

        for key in self._token_usage:
            for record in self._token_usage[key]:
                model = record["model"]
                model_stats[model]["total_requests"] += 1
                model_stats[model]["total_tokens"] += record["total_tokens"]
                model_stats[model]["input_tokens"] += record["input_tokens"]
                model_stats[model]["output_tokens"] += record["output_tokens"]
                model_stats[model]["total_cost"] += record["cost"]

        return [
            {
                "model": model,
                **stats
            }
            for model, stats in sorted(model_stats.items(),
                                      key=lambda x: x[1]["total_tokens"], reverse=True)
        ]

    async def get_error_stats(self) -> List[Dict]:
        """获取错误统计"""
        error_stats = Counter()
        for key in self._token_usage:
            for record in self._token_usage[key]:
                if record.get("error"):
                    error_stats[record["error"]] += 1

        return [
            {
                "error": error,
                "count": count
            }
            for error, count in error_stats.most_common()
        ]

    def _get_usage_breakdown(self, cutoff_time: datetime) -> List[Dict]:
        """获取使用情况分解"""
        breakdown = {}

        for key in self._token_usage:
            for record in self._token_usage[key]:
                record_time = datetime.fromisoformat(record["timestamp"])
                if record_time >= cutoff_time:
                    key_name = key.split(":")[-1] if ":" in key else key
                    if key_name not in breakdown:
                        breakdown[key_name] = {
                            "total_requests": 0,
                            "total_tokens": 0
                        }
                    breakdown[key_name]["total_requests"] += 1
                    breakdown[key_name]["total_tokens"] += record["total_tokens"]

        return [
            {
                "key": k,
                "total_requests": v["total_requests"],
                "total_tokens": v["total_tokens"]
            }
            for k, v in sorted(breakdown.items(), key=lambda x: x[1]["total_tokens"], reverse=True)
        ]

    def _get_top_tokens(self, cutoff_time: datetime, limit: Optional[int] = None) -> List[Dict]:
        """获取token使用量排行"""
        top_tokens = []

        for key in self._token_usage:
            with self._locks[key]:
                token_count = 0
                for record in self._token_usage[key]:
                    record_time = datetime.fromisoformat(record["timestamp"])
                    if record_time >= cutoff_time:
                        token_count += record["total_tokens"]

                if token_count > 0:
                    token_name = key.split(":")[-1] if ":" in key else key
                    top_tokens.append({
                        "token_key": token_name,
                        "total_tokens": token_count
                    })

        top_tokens.sort(key=lambda x: x["total_tokens"], reverse=True)

        if limit:
            top_tokens = top_tokens[:limit]

        return top_tokens

    async def get_summary(self) -> Dict:
        """获取摘要信息"""
        global_stats = await self.get_usage_stats(hours=24)

        return {
            "last_24h": global_stats,
            "daily_stats": await self.get_daily_stats(days=7),
            "model_stats": await self.get_model_stats(),
            "error_stats": await self.get_error_stats()
        }

    async def cleanup_old_data(self, days: int = 30):
        """清理旧数据"""
        cutoff_time = datetime.now() - timedelta(days=days)
        cleaned = 0

        for key in list(self._token_usage.keys()):
            with self._locks[key]:
                before_count = len(self._token_usage[key])
                self._token_usage[key] = [
                    r for r in self._token_usage[key]
                    if datetime.fromisoformat(r["timestamp"]) >= cutoff_time
                ]
                cleaned += before_count - len(self._token_usage[key])

        self._last_cleanup = time.time()
        return cleaned


# 全局单例
_token_usage_tracker = TokenUsageTracker()


def get_token_usage_tracker() -> TokenUsageTracker:
    """获取token使用量追踪器实例"""
    return _token_usage_tracker
