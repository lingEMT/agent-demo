"""
对话记忆服务

管理旅行计划的版本链。每条计划记录通过 conversation_id + parent_id + version_number
形成链表，支持对话式迭代修改。

使用方式：
    service = get_conversation_service()
    root = await service.create_conversation(session_id, title, request_data, plan_data)
    v2 = await service.add_version(root.id, session_id, "改轻松些", request_data, plan_data)
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, select

from ..core.database import get_session
from ..models.database import TripRecord


def _serialize(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _deserialize(data: Any) -> Any:
    if isinstance(data, str):
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data
    return data


class ConversationService:
    """
    对话记忆服务（单例模式）

    方法列表:
        create_conversation()   - 创建根计划，自动生成 conversation_id
        add_version()           - 追加修改版本
        get_conversation()      - 获取完整版本链
        get_latest_plan()       - 获取最新版本
        get_plan()              - 获取指定版本
        list_conversations()    - 按对话分组展示（每个对话只返回最新版本摘要）
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def create_conversation(
        self,
        session_id: str,
        title: str,
        request_data: Dict[str, Any],
        plan_data: Optional[Dict[str, Any]] = None,
    ) -> TripRecord:
        """
        创建根计划，自动生成 conversation_id，version_number=1

        Args:
            session_id: 前端身份标识
            title: 计划标题
            request_data: 旅行请求数据
            plan_data: 旅行计划数据（可选）

        Returns:
            创建的 TripRecord 实例
        """
        conversation_id = str(uuid.uuid4())
        async with get_session() as session:
            record = TripRecord(
                session_id=session_id,
                title=title,
                city=request_data.get("city", ""),
                request_data=_serialize(request_data),
                plan_data=_serialize(plan_data) if plan_data else None,
                conversation_id=conversation_id,
                parent_id=None,
                version_number=1,
                modification_request=None,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def add_version(
        self,
        parent_plan_id: str,
        session_id: str,
        modification_text: str,
        request_data: Dict[str, Any],
        plan_data: Dict[str, Any],
    ) -> Optional[TripRecord]:
        """
        追加修改版本，继承 conversation_id，version_number 递增

        Args:
            parent_plan_id: 父计划 ID
            session_id: 前端身份标识
            modification_text: 修改描述
            request_data: 旅行请求数据
            plan_data: 旅行计划数据

        Returns:
            创建的 TripRecord 实例，父记录不存在返回 None
        """
        # 先查询父记录以获取 conversation_id 和版本号
        async with get_session() as session:
            parent_result = await session.execute(
                select(TripRecord).where(TripRecord.id == parent_plan_id)
            )
            parent = parent_result.scalar_one_or_none()
            if not parent:
                return None

            conversation_id = parent.conversation_id
            # 没有 conversation_id 说明是旧数据，新建一个
            if not conversation_id:
                conversation_id = str(uuid.uuid4())

            new_version_number = (parent.version_number or 1) + 1

            record = TripRecord(
                session_id=session_id,
                title=parent.title,
                city=parent.city,
                request_data=_serialize(request_data),
                plan_data=_serialize(plan_data),
                conversation_id=conversation_id,
                parent_id=parent_plan_id,
                version_number=new_version_number,
                modification_request=modification_text,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def get_conversation(
        self, conversation_id: str
    ) -> List[TripRecord]:
        """
        获取完整版本链（按 version_number 升序）

        Args:
            conversation_id: 对话 ID

        Returns:
            TripRecord 列表，按版本号升序
        """
        async with get_session() as session:
            result = await session.execute(
                select(TripRecord)
                .where(TripRecord.conversation_id == conversation_id)
                .order_by(TripRecord.version_number.asc())
            )
            records = list(result.scalars().all())
            return records

    async def get_latest_plan(
        self, conversation_id: str
    ) -> Optional[TripRecord]:
        """
        获取最新版本

        Args:
            conversation_id: 对话 ID

        Returns:
            最新的 TripRecord 实例
        """
        async with get_session() as session:
            result = await session.execute(
                select(TripRecord)
                .where(TripRecord.conversation_id == conversation_id)
                .order_by(desc(TripRecord.version_number))
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_plan(self, plan_id: str) -> Optional[TripRecord]:
        """
        获取指定 ID 的计划

        Args:
            plan_id: 记录 ID

        Returns:
            TripRecord 实例
        """
        async with get_session() as session:
            result = await session.execute(
                select(TripRecord).where(TripRecord.id == plan_id)
            )
            return result.scalar_one_or_none()

    async def list_conversations(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        按对话分组展示（每个对话只返回最新版本摘要）

        Args:
            session_id: 前端身份标识
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            (摘要列表, 总数)
        """
        async with get_session() as session:
            # 查询有 conversation_id 的记录，按 conversation_id 分组取最新版本
            # 使用子查询方式
            # 先找到所有有 conversation_id 的记录
            all_result = await session.execute(
                select(TripRecord)
                .where(
                    TripRecord.session_id == session_id,
                    TripRecord.conversation_id.isnot(None),
                )
                .order_by(
                    TripRecord.conversation_id,
                    desc(TripRecord.version_number),
                )
            )
            all_records = list(all_result.scalars().all())

            # 按 conversation_id 分组，取每个组的第一个（最新版本）
            seen = set()
            latest_per_conversation = []
            for record in all_records:
                cid = record.conversation_id
                if cid and cid not in seen:
                    seen.add(cid)
                    latest_per_conversation.append(record)

            # 按 updated_at 倒序排列
            latest_per_conversation.sort(
                key=lambda r: r.updated_at or datetime.min, reverse=True
            )

            total = len(latest_per_conversation)

            # 分页
            offset = (page - 1) * page_size
            page_records = latest_per_conversation[offset: offset + page_size]

            # 统计每个对话的版本数
            from collections import Counter
            version_counts = Counter(r.conversation_id for r in all_records)

            result = []
            for record in page_records:
                cid = record.conversation_id or ""
                result.append({
                    "conversation_id": cid,
                    "title": record.title,
                    "latest_version": record.version_number or 1,
                    "total_versions": version_counts.get(cid, 1),
                    "city": record.city,
                    "created_at": (
                        record.created_at.isoformat() if record.created_at else ""
                    ),
                    "updated_at": (
                        record.updated_at.isoformat() if record.updated_at else ""
                    ),
                    "latest_plan_id": record.id,
                })

            return result, total


# ============ 全局单例访问器 ============

_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """获取对话记忆服务实例（单例）"""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
