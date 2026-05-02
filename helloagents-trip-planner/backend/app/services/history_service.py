"""
历史记录服务

提供旅行计划的持久化 CRUD 操作。
每次方法调用独立创建和关闭 DB session，不跨请求持有连接。
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, desc, select, update, func

from ..core.database import get_session
from ..models.database import TripRecord


def _serialize(data: Any) -> str:
    """将数据序列化为 JSON 字符串"""
    return json.dumps(data, ensure_ascii=False, default=str)


def _deserialize(data: Any) -> Any:
    """将 JSON 字符串反序列化为 Python 对象"""
    if isinstance(data, str):
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data
    return data


class HistoryService:
    """
    历史记录服务（单例模式）

    方法列表:
        save_trip()       - 保存旅行计划
        get_trip()        - 获取单个计划详情
        list_trips()      - 获取计划列表（分页）
        delete_trip()     - 删除计划
        update_trip()     - 更新计划
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def save_trip(
        self,
        session_id: str,
        title: str,
        request_data: Dict[str, Any],
        plan_data: Optional[Dict[str, Any]] = None,
    ) -> TripRecord:
        """
        保存旅行计划

        Args:
            session_id: 前端身份标识
            title: 计划标题（如：北京3日游）
            request_data: 旅行请求数据
            plan_data: 旅行计划数据（可选，生成成功后才提供）

        Returns:
            创建的 TripRecord 实例
        """
        async with get_session() as session:
            record = TripRecord(
                session_id=session_id,
                title=title,
                city=request_data.get("city", ""),
                request_data=_serialize(request_data),
                plan_data=_serialize(plan_data) if plan_data else None,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)

            # 清理旧记录：同 session 最多保留 5 条（不含对话版本链记录）
            MAX_RECORDS = 5
            count_result = await session.execute(
                select(func.count())
                .select_from(TripRecord)
                .where(
                    TripRecord.session_id == session_id,
                    TripRecord.conversation_id.is_(None),
                )
            )
            total = count_result.scalar() or 0
            if total > MAX_RECORDS:
                # 找出需要删除的旧记录
                excess = total - MAX_RECORDS
                old_result = await session.execute(
                    select(TripRecord.id)
                    .where(
                        TripRecord.session_id == session_id,
                        TripRecord.conversation_id.is_(None),
                    )
                    .order_by(TripRecord.created_at.asc())
                    .limit(excess)
                )
                old_ids = [row[0] for row in old_result.fetchall()]
                if old_ids:
                    await session.execute(
                        delete(TripRecord).where(TripRecord.id.in_(old_ids))
                    )
                    await session.commit()
                    print(f"[HISTORY] 已清理 {len(old_ids)} 条旧记录，session {session_id[:8]}... 保留 {MAX_RECORDS} 条")

            return record

    async def get_trip(self, record_id: str) -> Optional[TripRecord]:
        """
        根据 ID 获取旅行计划详情

        Args:
            record_id: 记录 UUID

        Returns:
            TripRecord 实例（含已反序列化的JSON字段），不存在返回 None
        """
        async with get_session() as session:
            result = await session.execute(
                select(TripRecord).where(TripRecord.id == record_id)
            )
            return result.scalar_one_or_none()

    async def list_trips(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[TripRecord], int]:
        """
        获取旅行计划列表（分页，按创建时间倒序）

        Args:
            session_id: 前端身份标识
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            (记录列表, 总数)
        """
        async with get_session() as session:
            # 查询总数
            count_result = await session.execute(
                select(TripRecord).where(TripRecord.session_id == session_id)
            )
            total = len(count_result.scalars().all())

            # 分页查询
            offset = (page - 1) * page_size
            result = await session.execute(
                select(TripRecord)
                .where(TripRecord.session_id == session_id)
                .order_by(desc(TripRecord.created_at))
                .offset(offset)
                .limit(page_size)
            )
            records = list(result.scalars().all())
            return records, total

    async def delete_trip(self, record_id: str) -> bool:
        """
        删除旅行计划

        Args:
            record_id: 记录 UUID

        Returns:
            是否成功删除
        """
        async with get_session() as session:
            result = await session.execute(
                delete(TripRecord).where(TripRecord.id == record_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def update_trip(
        self,
        record_id: str,
        plan_data: Dict[str, Any],
    ) -> Optional[TripRecord]:
        """
        更新旅行计划数据（用于生成成功后回填 plan_data）

        Args:
            record_id: 记录 UUID
            plan_data: 旅行计划数据

        Returns:
            更新后的 TripRecord 实例，不存在返回 None
        """
        async with get_session() as session:
            result = await session.execute(
                update(TripRecord)
                .where(TripRecord.id == record_id)
                .values(
                    plan_data=_serialize(plan_data),
                    updated_at=datetime.utcnow(),
                )
            )
            if result.rowcount == 0:
                return None
            await session.commit()
            # 重新查询返回完整记录
            return await self.get_trip(record_id)


# ============ 全局单例访问器 ============

_history_service: Optional[HistoryService] = None


def get_history_service() -> HistoryService:
    """获取历史记录服务实例（单例）"""
    global _history_service
    if _history_service is None:
        _history_service = HistoryService()
    return _history_service
