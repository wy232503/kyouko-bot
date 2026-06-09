"""
对话历史管理 - 按会话维护上下文
"""
import time
from collections import defaultdict
from typing import Dict, List

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)


class ChatHistory:
    """简单的内存对话历史管理"""

    def __init__(self):
        # session_id -> list of {"role": "user"/"assistant", "content": "..."}
        self._store: Dict[str, List[dict]] = defaultdict(list)
        # session_id -> last_access_time
        self._last_access: Dict[str, float] = {}

    def get(self, session_id: str) -> List[dict]:
        """获取会话历史"""
        self._cleanup_expired()
        self._last_access[session_id] = time.time()
        return self._store.get(session_id, [])

    def add(self, session_id: str, role: str, content: str):
        """添加一条消息"""
        self._store[session_id].append({"role": role, "content": content})
        self._last_access[session_id] = time.time()

        # 裁剪过长历史：保留 system prompt 概念上的最近 N 轮
        # system prompt 不在 history 里，所以这里的轮数 = user+assistant 对
        max_msgs = config.MAX_HISTORY_LENGTH * 2  # user + assistant 各算一条
        if len(self._store[session_id]) > max_msgs:
            self._store[session_id] = self._store[session_id][-max_msgs:]

    def clear(self, session_id: str):
        """清除某个会话"""
        self._store.pop(session_id, None)
        self._last_access.pop(session_id, None)

    def reset(self, session_id: str):
        """重置会话（同 clear）"""
        self.clear(session_id)

    def _cleanup_expired(self):
        """清理过期会话"""
        now = time.time()
        expired = [
            sid for sid, t in self._last_access.items()
            if now - t > config.CHAT_TTL_SECONDS
        ]
        for sid in expired:
            self._store.pop(sid, None)
            self._last_access.pop(sid, None)
            logger.info(f"清理过期会话: {sid[:8]}...")


# 全局单例
chat_history = ChatHistory()
