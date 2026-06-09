"""
微信适配层 - 封装 wxauto，提供统一的微信消息收发接口

依赖：Windows + 微信PC客户端 + wxauto
启动前需要：
  1. 打开微信PC客户端并登录
  2. 运行本程序，wxauto 会自动附着到微信窗口
"""
import time
import threading
from typing import Callable, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

# wxauto 是可选依赖，允许在没有微信的环境下只运行 Web 服务
try:
    from wxauto import WeChat
    WXAUTO_AVAILABLE = True
except ImportError:
    WXAUTO_AVAILABLE = False
    WeChat = None
    logger.warning("wxauto 未安装，微信功能不可用。安装：pip install wxauto")


class WeChatAdapter:
    """
    微信适配器 - 监听消息并通过回调处理
    """

    def __init__(self):
        self._wx: Optional[WeChat] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._message_handler: Optional[Callable] = None
        self._last_processed: dict = {}  # 去重用

    # ---------- 公开 API ----------

    @property
    def available(self) -> bool:
        """微信功能是否可用"""
        return WXAUTO_AVAILABLE

    def start(self, message_handler: Callable):
        """
        启动微信监听（非阻塞，在后台线程运行）

        Args:
            message_handler: async def handler(msg: dict) -> str | None
              消息格式: {"type": "private"|"group", "sender": str, "content": str, "group_name": str|None}
              返回 None 表示不回复，返回 str 表示回复内容
        """
        if not WXAUTO_AVAILABLE:
            logger.error("wxauto 不可用，无法启动微信机器人")
            return

        if self._running:
            logger.warning("微信机器人已在运行中")
            return

        self._message_handler = message_handler
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("🤖 微信机器人已启动，监听新消息中...")

    def stop(self):
        """停止微信监听"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("微信机器人已停止")

    def send_text(self, to: str, content: str):
        """
        发送文本消息

        Args:
            to: 接收者微信名（备注名或昵称）
            content: 消息内容
        """
        if not self._wx:
            logger.error("微信未连接")
            return
        try:
            self._wx.SendMsg(content, to)
            logger.info(f"发送消息 → {to}: {content[:30]}...")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    # ---------- 内部实现 ----------

    def _listen_loop(self):
        """主消息监听循环"""
        try:
            self._wx = WeChat()
            logger.info("✅ 微信连接成功！等待新消息...")
        except Exception as e:
            logger.error(f"微信连接失败: {e}")
            logger.error("请确保：1) 微信PC客户端已登录  2) 微信窗口可见")
            self._running = False
            return

        last_check_time = time.time()

        while self._running:
            try:
                # 获取新消息
                msgs = self._wx.GetAllNewMessage()
                if msgs:
                    # 处理每条新消息
                    for msg in msgs:
                        self._process_single_message(msg)

                # 每 30 秒输出心跳（调试用）
                now = time.time()
                if now - last_check_time > 30:
                    logger.debug("微信监听心跳 OK")
                    last_check_time = now

                time.sleep(1)  # 1秒轮询间隔

            except Exception as e:
                logger.error(f"微信监听异常: {e}")
                time.sleep(5)

    def _process_single_message(self, msg):
        """处理单条微信消息"""
        try:
            # 消息去重（wxauto 可能返回重复消息）
            msg_id = str(msg.get('id', ''))
            if msg_id and msg_id in self._last_processed:
                return
            if msg_id:
                self._last_processed[msg_id] = time.time()

            # 清理过期去重记录
            self._last_processed = {
                k: v for k, v in self._last_processed.items()
                if time.time() - v < 60
            }

            msg_type = msg.get('type', '')
            sender = msg.get('sender', '') or msg.get('sender_name', '')
            content = msg.get('content', '') or msg.get('text', '')
            group_name = msg.get('group_name', '')

            if not content or not sender:
                return

            # 构建标准化消息
            normalized = {
                "type": "group" if "群" in msg_type or group_name else "private",
                "sender": sender,
                "content": content.strip(),
                "group_name": group_name or None,
            }

            logger.info(f"📩 [{normalized['type']}] {sender}: {content[:50]}...")

            # 调用处理器
            if self._message_handler:
                reply = self._message_handler(normalized)
                if reply:
                    # 群聊回复格式：@发送者 + 回复内容
                    if normalized['type'] == 'group' and group_name:
                        # 群聊消息：通过群聊发送
                        self._wx.SendMsg(f"@{sender} {reply}", group_name)
                        logger.info(f"群聊回复 → {group_name}: @{sender} {reply[:30]}...")
                    else:
                        # 私聊消息
                        self._wx.SendMsg(reply, sender)
                        logger.info(f"私聊回复 → {sender}: {reply[:30]}...")

        except Exception as e:
            logger.error(f"处理消息异常: {e}")


# 全局单例
wechat_adapter = WeChatAdapter()
