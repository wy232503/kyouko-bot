"""
AI 女友 京子 - 配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # DeepSeek API
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-your-deepseek-api-key-here")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # 服务
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

    # 微信 PC 客户端桥接 (wxauto - 仅 Windows)
    WECHAT_ENABLED = os.getenv("WECHAT_ENABLED", "false").lower() == "true"
    WECHAT_GROUP_AT_ONLY = os.getenv("WECHAT_GROUP_AT_ONLY", "true").lower() == "true"

    # 微信公众号 (Official Account - 云端 24/7)
    WECHAT_OA_TOKEN = os.getenv("WECHAT_OA_TOKEN", "")
    WECHAT_OA_APP_ID = os.getenv("WECHAT_OA_APP_ID", "")
    WECHAT_OA_APP_SECRET = os.getenv("WECHAT_OA_APP_SECRET", "")
    WECHAT_OA_ENCODING_AES_KEY = os.getenv("WECHAT_OA_ENCODING_AES_KEY", "")

    # 主动消息调度
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    MORNING_WINDOW_START = int(os.getenv("MORNING_WINDOW_START", "7"))
    MORNING_WINDOW_END = int(os.getenv("MORNING_WINDOW_END", "9"))
    EVENING_WINDOW_START = int(os.getenv("EVENING_WINDOW_START", "21"))
    EVENING_WINDOW_END = int(os.getenv("EVENING_WINDOW_END", "23"))

    # 对话
    MAX_HISTORY_LENGTH = int(os.getenv("MAX_HISTORY_LENGTH", "20"))
    CHAT_TTL_SECONDS = int(os.getenv("CHAT_TTL_SECONDS", "3600"))


config = Config()
