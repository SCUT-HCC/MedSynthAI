# medsynthai/core/registrar.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # 确保导入 CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from medsynthai.core.middleware import BandwidthMonitorMiddleware
from medsynthai.database_model import (
    AudioDatabase,
    DialogueDatabase,
)

# 导入路由
from medsynthai.app import upload_router, download_router, diagnosis_router, report_router
from medsynthai.app.dialogue.api import respond_router

# 创建数据库连接并初始化应用程序状态
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database and store connection in app state
    app.state.dialogue_db = DialogueDatabase()
    app.state.audio_db = AudioDatabase()
    app.state.medical_workflows = {}
    app.state.medical_workflows_lock = asyncio.Lock()
    # Initialize workflows
    app.state.diagnosis_workflows = {}
    app.state.diagnosis_workflows_lock = asyncio.Lock()
    logging.info("Database connections established")
    yield
    # 在应用关闭时关闭数据库连接（如果 close 方法存在）
    # 注意：原始代码没有关闭所有数据库连接，这里补充一下（假设它们有 close 方法）
    if hasattr(app.state.dialogue_db, 'close'):
        app.state.dialogue_db.close()
    if hasattr(app.state.audio_db, 'close'):
        app.state.audio_db.close()
    logging.info("Database connections closed")


def register_app() -> FastAPI:
    """
    创建并配置FastAPI应用程序
    """
    app = FastAPI(lifespan=lifespan)

    # 添加带宽监控中间件
    # 注意：FastAPI 添加中间件的推荐方式是 app.add_middleware(MiddlewareClass, **options)
    # 而不是 app.middleware("http")(MiddlewareInstance)。后者是 Starlette 的旧方式，虽然可能仍有效。
    # 如果遇到问题，可以尝试改为： app.add_middleware(BandwidthMonitorMiddleware)
    app.middleware("http")(BandwidthMonitorMiddleware())

    # --- 修改 CORS 配置 ---
    # 定义允许访问的源列表
    origins = [
        "http://localhost:3000",        # 保留用于本地开发（如果需要）
        "http://100.82.33.121:8081",    # 添加您通过 Tailscale IP 访问的前端地址
        # 如果有其他需要允许的源，也一并添加
    ]

    # 添加 CORS 中间件配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,          # 使用上面定义的列表
        allow_credentials=True,         # 允许携带凭证（如 cookies）
        allow_methods=["*"],            # 允许所有标准 HTTP 方法
        allow_headers=["*"],            # 允许所有 HTTP 请求头
    )
    # --- CORS 配置结束 ---

    # 注册路由
    register_routes(app)

    return app

def register_routes(app: FastAPI):
    """
    注册所有API路由
    """
    # 包含所有路由
    app.include_router(upload_router)
    app.include_router(download_router)
    app.include_router(diagnosis_router)
    app.include_router(respond_router,prefix="/dialogue", tags=["dialogue"])
    app.include_router(report_router)