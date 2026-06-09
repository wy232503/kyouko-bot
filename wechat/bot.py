"""
微信消息处理器 - 将微信消息转发给 DeepSeek，返回堀京子的回复
"""
import asyncio
import uuid
from utils.logger import get_logger
from llm.deepseek_client import chat
from config import config

logger = get_logger(__name__)


def create_wechat_handler():
    """
    创建微信消息处理回调函数

    返回的 handler 在 wxauto 的线程中被同步调用，
    内部通过 asyncio 桥接到异步 DeepSeek 客户端
    """

    def handle_message(msg: dict) -> str | None:
        """
        处理微信消息，返回要回复的内容（None 表示不回复）

        msg 格式:
          {"type": "private"|"group", "sender": str,
           "content": str, "group_name": str|None}
        """
        msg_type = msg.get('type', 'private')
        sender = msg.get('sender', '未知')
        content = msg.get('content', '')

        # 群聊：只回复被 @堀 或 @京子 的消息
        if msg_type == 'group':
            if not _is_mentioned(content):
                return None

        # 为每个微信用户创建独立会话
        session_id = f"wechat_{sender}"

        try:
            # 在同步上下文中调用异步 DeepSeek
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                reply = loop.run_until_complete(chat(session_id, content))
            finally:
                loop.close()
            return reply
        except Exception as e:
            logger.error(f"DeepSeek 调用失败: {e}")
            return "啊，抱歉，我这边有点忙……等一下再聊吧！"

    return handle_message


def _is_mentioned(content: str) -> bool:
    """检查消息是否 @了机器人（@堀 / @京子 / @hori 等）"""
    mention_keywords = ['@堀', '@京子', '@hori', '@Hori', '@ほり', '@ホリ']
    # 微信 @ 消息通常格式为 @xxx 或 @xxx​ （带零宽字符）
    return any(kw.lower() in content.lower() for kw in mention_keywords)


# ---------- 备用：同步版本（如果需要更简单的实现）----------

def handle_wechat_message_sync(msg: dict) -> str | None:
    """
    同步版本的消息处理器（用于无 asyncio 环境测试）
    注意：这个版本不支持真正的异步，仅用于测试
    """
    handler = create_wechat_handler()
    return handler(msg)
