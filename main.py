"""
京子 AI 女友 - 主入口

本地启动:
  python main.py

云端部署 (Zeabur):
  Zeabur 自动检测 FastAPI → uvicorn main:app
  或通过 zeabur.json 指定: python main.py
"""
import os
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import config
from web.routes import router as web_router
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------- 后台任务启动 ----------

def _start_scheduler():
    """启动主动消息调度器（后台 asyncio 任务）"""
    if not config.SCHEDULER_ENABLED:
        logger.info("主动消息调度器未启用（SCHEDULER_ENABLED=false）")
        return

    try:
        from scheduler import scheduler_loop
        from character.emotion import emotion_engine

        emotion_engine.load()
        loop = asyncio.get_event_loop()
        loop.create_task(scheduler_loop())
        logger.info("主动消息调度器已启动")
    except Exception as e:
        logger.error(f"调度器启动失败: {e}")


# ---------- FastAPI 应用 ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时加载调度器，关闭时清理"""
    _start_scheduler()
    yield


app = FastAPI(
    title="京子 AI Girlfriend",
    description="以堀京子为原型的 AI 女友，拥有自己的情绪和日常生活",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_router)


# ---------- 本地启动 ----------

def main():
    """本地开发启动"""
    if config.WECHAT_ENABLED:
        try:
            from wechat.wechat_adapter import wechat_adapter
            from wechat.bot import create_wechat_handler
            if wechat_adapter.available:
                wechat_adapter.start(create_wechat_handler())
                logger.info("微信 PC 桥接已启动")
        except Exception:
            pass

    port = int(os.getenv("PORT", config.PORT))
    logger.info(f"京子启动 → http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
