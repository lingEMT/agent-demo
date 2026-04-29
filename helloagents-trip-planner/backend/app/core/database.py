"""
SQLAlchemy 异步数据库引擎和会话管理

提供:
1. init_db(): 启动时调用，创建数据目录、建表、设置WAL模式
2. close_db(): 关闭引擎
3. get_db(): FastAPI 依赖注入用的 async generator
"""

import os
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


# 全局引擎和会话工厂（由 init_db 初始化）
_engine = None
_async_session_factory = None


def get_data_dir() -> Path:
    """获取数据库文件存放目录"""
    settings = get_settings()
    # database_url 格式: sqlite+aiosqlite:///./data/trip_planner.db
    # 提取相对路径部分
    url = settings.database_url
    if "///" in url:
        rel_path = url.split("///")[1]
        data_dir = Path(__file__).parent.parent.parent / os.path.dirname(rel_path)
    else:
        data_dir = Path(__file__).parent.parent.parent / "data"
    return data_dir.resolve()


async def init_db():
    """初始化数据库：创建目录、建表、设置WAL模式"""
    global _engine, _async_session_factory

    settings = get_settings()
    database_url = settings.database_url

    # 确保数据目录存在
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"[DB] 数据库目录: {data_dir}")

    # 创建异步引擎
    _engine = create_async_engine(
        database_url,
        echo=False,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    # 创建会话工厂
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # 建表
    from ..models.database import TripRecord, TokenUsageRecord  # noqa: F401
    async with _engine.begin() as conn:
        # SQLite 启用 WAL 模式，提升并发性能
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        await conn.run_sync(Base.metadata.create_all)

    print(f"[DB] 数据库初始化成功: {database_url}")


async def close_db():
    """关闭数据库引擎"""
    global _engine, _async_session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        print("[DB] 数据库连接已关闭")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入 - 获取数据库会话

    用法:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    if _async_session_factory is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")

    async with _async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def get_session() -> AsyncSession:
    """
    获取一个新的数据库会话（非依赖注入用）

    在 HistoryService 等非路由场景中使用，
    每次操作独立创建和关闭会话。
    """
    if _async_session_factory is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")
    return _async_session_factory()
