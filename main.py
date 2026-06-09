"""
京子 AI 女友 - 主入口

本地启动:
  python main.py
  → 网页聊天: http://localhost:8000
  → 主动消息推送: 自动在 7-9点早安 / 21-23点晚安 / 随机日常分享

云端部署 (Zeabur):
  GitHub 推送 → Zeabur 自动构建
  → 网页聊天: https://你的域名
  → 微信公众号: https://你的域名/wechat
  → 主动消息通过 Web Push + 微信客服消息双通道投递
"""

import os
import sys
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import config
from web.routes import router as web_router
from utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="京子 AI Girlfriend",
        description="以堀京子为原型的 AI 女友，拥有自己的情绪和日常生活",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(web_router)

    return app


def print_banner():
    """打印启动横幅"""
    is_cloud = bool(os.getenv("ZEABUR") or os.getenv("RAILWAY_SERVICE_ID") or os.getenv("RENDER"))
    env_name = "☁️  云端模式" if is_cloud else "💻 本地模式"

    banner = rf"""
╔══════════════════════════════════════════════╗
║       💕  京 子  AI  女 友  💕             ║
║       Kyouko v2.0                          ║
║                                             ║
║  「えっと……我是你的女朋友京子，              ║
║     请多指教哦~ (〃ω〃)」                   ║
║                                             ║
║  🌐 Web:    http://0.0.0.0:{config.PORT:<5}                ║
║  📱 公众号:  {'已配置' if config.WECHAT_OA_TOKEN else '待配置' if is_cloud else '云端可用'}                 ║
║  ⏰ 主动消息: {'✅ 已启用' if config.SCHEDULER_ENABLED else '❌ 未启用'}                  ║
║  🖥️  状态:    {env_name}                    ║
╚══════════════════════════════════════════════╝
"""
    print(banner)


def start_wechat_pc():
    """启动微信 PC 客户端桥接（仅 Windows 本地）"""
    if not config.WECHAT_ENABLED:
        return

    try:
        from wechat.wechat_adapter import wechat_adapter
        from wechat.bot import create_wechat_handler

        if not wechat_adapter.available:
            logger.warning("wxauto 未安装，跳过微信 PC 桥接")
            return

        handler = create_wechat_handler()
        wechat_adapter.start(handler)
        logger.info("微信 PC 桥接启动成功！")
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"微信 PC 桥接失败: {e}")


def start_scheduler():
    """启动主动消息调度器（后台 asyncio 任务）"""
    if not config.SCHEDULER_ENABLED:
        logger.info("主动消息调度器未启用（SCHEDULER_ENABLED=false）")
        return

    try:
        from scheduler import scheduler_loop
        from character.emotion import emotion_engine

        # 加载情绪状态
        emotion_engine.load()

        # 在事件循环中创建后台任务
        loop = asyncio.get_event_loop()
        loop.create_task(scheduler_loop())
        logger.info("⏰ 主动消息调度器已加入后台任务")
    except Exception as e:
        logger.error(f"调度器启动失败: {e}")


def check_config():
    """检查配置"""
    if "sk-your" in config.DEEPSEEK_API_KEY:
        logger.warning("请在 .env 中设置 DEEPSEEK_API_KEY！")

    if config.WECHAT_OA_TOKEN:
        logger.info("微信公众号已配置")
    else:
        is_cloud = bool(os.getenv("ZEABUR") or os.getenv("RAILWAY_SERVICE_ID"))
        if is_cloud:
            logger.info("提示: 设置 WECHAT_OA_TOKEN 以启用微信公众号")


def main():
    """主函数"""
    print_banner()
    check_config()

    app = create_app()

    # 微信 PC 桥接（仅本地 Windows）
    start_wechat_pc()

    # 启动主动消息调度器
    start_scheduler()

    # 启动服务
    port = int(os.getenv("PORT", config.PORT))
    logger.info(f"服务启动 → http://0.0.0.0:{port}")
    logger.info(f"健康检查 → http://0.0.0.0:{port}/health")
    logger.info(f"主动推送 → http://0.0.0.0:{port}/api/push")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
