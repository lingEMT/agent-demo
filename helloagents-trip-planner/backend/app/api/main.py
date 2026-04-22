"""FastAPI主应用"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings, validate_config, print_config
from .routes import trip, poi, map as map_routes, token_monitor
from ..agents.trip_planner_agent import get_trip_planner_agent

# 获取配置
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("\n" + "=" * 60)
    print(f"[START] {settings.app_name} v{settings.app_version}")
    print("=" * 60)

    # 打印配置信息
    print_config()

    # 验证配置
    try:
        validate_config()
        print("\n[OK] 配置验证通过")
    except ValueError as e:
        print(f"\n[ERROR] 配置验证失败:\n{e}")
        print("\n请检查.env文件并确保所有必要的配置项都已设置")
        raise

    # 预初始化Agent系统
    print("\n[INFO] 预初始化Agent系统...")
    try:
        agent = get_trip_planner_agent()
        print("[OK] Agent系统预初始化成功")
    except Exception as e:
        print(f"[WARNING] Agent系统预初始化失败: {str(e)}")

    print("\n" + "=" * 60)
    print("[DOCS] API文档: http://localhost:8000/docs")
    print("[REDOC] ReDoc文档: http://localhost:8000/redoc")
    print("=" * 60 + "\n")

    yield

    # 清理资源
    print("\n" + "=" * 60)
    print("[INFO] 正在清理资源...")

    # 清理Agent系统
    try:
        from ..agents.trip_planner_agent import _multi_agent_planner
        if _multi_agent_planner is not None:
            await _multi_agent_planner.cleanup()
    except Exception as e:
        print(f"[WARNING] 清理Agent资源时出错: {str(e)}")

    print("[EXIT] 应用正在关闭...")
    print("=" * 60 + "\n")

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于LangChain框架的智能旅行规划助手API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(trip.router, prefix="/api")
app.include_router(poi.router, prefix="/api")
app.include_router(map_routes.router, prefix="/api")
app.include_router(token_monitor.router, prefix="/api")

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "framework": "LangChain/LangGraph",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "framework": "LangChain/LangGraph"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
