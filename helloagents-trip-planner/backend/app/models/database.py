"""SQLAlchemy ORM 模型定义"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import TEXT as SQLITE_TEXT

from ..core.database import Base


class TripRecord(Base):
    """旅行计划持久化记录"""

    __tablename__ = "trip_records"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID主键",
    )
    session_id = Column(
        String(36),
        index=True,
        nullable=False,
        comment="前端session_id，用于身份标识",
    )
    title = Column(
        String(200),
        nullable=False,
        comment="旅行计划标题（如：北京3日游）",
    )
    city = Column(
        String(50),
        nullable=False,
        comment="目的地城市",
    )
    request_data = Column(
        SQLITE_TEXT,
        nullable=False,
        comment="旅行请求原始数据（JSON）",
    )
    plan_data = Column(
        SQLITE_TEXT,
        nullable=True,
        comment="旅行计划完整数据（JSON），生成成功后才保存",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        comment="更新时间",
    )

    def __repr__(self):
        return f"<TripRecord(id={self.id}, title={self.title}, city={self.city})>"


class TokenUsageRecord(Base):
    """Token调用量持久化记录（预留）"""

    __tablename__ = "token_usage_records"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    session_id = Column(String(36), index=True, nullable=True, comment="会话ID")
    token_key = Column(String(100), nullable=False, comment="Token key标识")
    request_id = Column(String(100), nullable=True, comment="请求ID")
    input_tokens = Column(Integer, default=0, comment="输入Token数")
    output_tokens = Column(Integer, default=0, comment="输出Token数")
    total_tokens = Column(Integer, default=0, comment="总Token数")
    model = Column(String(50), nullable=True, comment="模型名称")
    cost = Column(Integer, default=0, comment="费用(分)")
    error = Column(String(500), nullable=True, comment="错误信息")
    timestamp = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="记录时间",
    )

    def __repr__(self):
        return f"<TokenUsageRecord(id={self.id}, key={self.token_key})>"
