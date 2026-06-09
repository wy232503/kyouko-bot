"""
定时主动消息调度器

功能:
  - 早安消息: 每天 7:00-9:00 之间随机时间发送
  - 晚安消息: 每天 21:00-23:00 之间随机时间发送
  - 日常分享: 每天 2-4 次随机分享生活碎片
  - 去重: 同一天同类型只发一次，用户先发了则不重复

消息投递通道（双通道）:
  - Web Push: 推送到网页聊天客户端（SSE 队列）
  - 微信客服消息: 通过微信公众号客服 API 推送（需已认证）
"""

import asyncio
import random
import json
import os
import hashlib
import time as time_module
from datetime import datetime, timedelta
from typing import Optional, Dict, Set
from dataclasses import dataclass, field

from utils.logger import get_logger
from config import config

logger = get_logger(__name__)

# ---------- 推送消息队列 ----------
# Web 客户端通过 SSE 从此队列获取主动推送的消息
web_push_queue: asyncio.Queue = asyncio.Queue(maxsize=100)


# ---------- 当天已发送记录 ----------

@dataclass
class DailyRecord:
    """当天发送记录"""
    date: str = ""  # YYYY-MM-DD
    morning_sent: bool = False
    evening_sent: bool = False
    daily_share_count: int = 0
    last_user_message_time: Optional[float] = None  # 用户最后一次发消息的时间戳
    morning_target_time: Optional[str] = None  # 今天早安的目标时间
    evening_target_time: Optional[str] = None  # 今天晚安的目标时间
    share_times: list = field(default_factory=list)  # 今天日常分享的目标时间列表


class SendTracker:
    """发送追踪器，管理每天的发信状态"""

    def __init__(self, state_file: str = "send_state.json"):
        self.state_file = state_file
        self.record = DailyRecord()
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.record = DailyRecord(**data)
        except Exception:
            pass

    def _save(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.record.__dict__, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存发送状态失败: {e}")

    def new_day(self):
        """新的一天，重新规划"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.record.date != today:
            # 随机选择今天的早安时间 (7:00-8:59)
            morning_hour = random.randint(7, 8)
            morning_min = random.randint(0, 59)
            # 随机选择今天的晚安时间 (21:00-22:59)
            evening_hour = random.randint(21, 22)
            evening_min = random.randint(0, 59)
            # 随机选择今天日常分享的时间（2-4次，在9:00-23:00之间）
            share_count = random.randint(2, 4)
            share_times = []
            used_hours = set()
            for _ in range(share_count):
                while True:
                    h = random.randint(9, 22)
                    if h not in used_hours:
                        used_hours.add(h)
                        break
                m = random.randint(0, 59)
                share_times.append(f"{h:02d}:{m:02d}")
            share_times.sort()

            self.record = DailyRecord(
                date=today,
                morning_sent=False,
                evening_sent=False,
                daily_share_count=0,
                last_user_message_time=None,
                morning_target_time=f"{morning_hour:02d}:{morning_min:02d}",
                evening_target_time=f"{evening_hour:02d}:{evening_min:02d}",
                share_times=share_times,
            )
            logger.info(f"📅 新的一天！早安 {self.record.morning_target_time} | "
                        f"晚安 {self.record.evening_target_time} | "
                        f"日常分享 {len(share_times)} 次: {share_times}")
            self._save()

    def user_messaged(self):
        """记录用户发消息的时间"""
        self.record.last_user_message_time = time_module.time()
        self._save()

    def mark_morning_sent(self):
        self.record.morning_sent = True
        self._save()

    def mark_evening_sent(self):
        self.record.evening_sent = True
        self._save()

    def mark_share_sent(self):
        self.record.daily_share_count += 1
        self._save()

    def should_send_morning(self, now: datetime) -> bool:
        """是否应该发送早安"""
        if self.record.morning_sent:
            return False
        target = self.record.morning_target_time
        if not target:
            return False
        current = now.strftime("%H:%M")
        # 到了目标时间，且用户还没发过消息
        if current >= target:
            # 如果用户在目标时间之前已经发了消息，就不发了
            if self._user_already_beat_to_it(target):
                self.mark_morning_sent()  # 标记已处理
                logger.info("☀️ 用户已经先发消息了，跳过早安")
                return False
            return True
        return False

    def should_send_evening(self, now: datetime) -> bool:
        """是否应该发送晚安"""
        if self.record.evening_sent:
            return False
        target = self.record.evening_target_time
        if not target:
            return False
        current = now.strftime("%H:%M")
        if current >= target:
            if self._user_already_beat_to_it(target):
                self.mark_evening_sent()
                logger.info("🌙 用户已经先发消息了，跳过晚安")
                return False
            return True
        return False

    def should_send_share(self, now: datetime) -> bool:
        """是否应该发送日常分享"""
        pending = [t for t in self.record.share_times
                   if t <= now.strftime("%H:%M")]
        already_sent = self.record.daily_share_count
        return len(pending) > already_sent

    def _user_already_beat_to_it(self, target_time: str) -> bool:
        """检查用户是否在目标时间之前已经发了消息"""
        if not self.record.last_user_message_time:
            return False
        # 解析目标时间
        try:
            h, m = map(int, target_time.split(":"))
            now = datetime.now()
            target_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            user_msg_dt = datetime.fromtimestamp(self.record.last_user_message_time)
            # 用户消息时间在目标时间之后 → 用户先发了
            return user_msg_dt >= target_dt
        except Exception:
            return False


# ---------- 消息生成 ----------

DAILY_SHARE_PROMPTS = [
    "你现在想和男朋友分享一件生活中的小事。内容要自然随意，像真的情侣聊天一样。话题可以是：今天吃了什么、路上看到的有趣的事、咖啡店打工遇到的客人、课上发生的事、和朋友聊了什么、买了什么、天气、心情变化等等。用1-3句话分享，带一点情绪。不要用'今天我想分享...'这种格式，直接说内容。",
    "你现在突然想到男朋友，想撒娇或者说句甜甜的话。自然一点，不要肉麻过度。",
    "你现在想关心一下男朋友——问他吃饭了没、在干嘛、今天过得怎么样。",
    "你现在心情有点小变化（可能是开心、累、烦、想他），想自然地跟男朋友说。",
    "你在做一件日常的事（比如做饭、逛超市、看书、收拾房间），想顺口跟男朋友提一下。",
]


async def generate_proactive_message(prompt_type: str) -> str:
    """
    调用 DeepSeek 生成主动消息

    Args:
        prompt_type: "morning" | "evening" | "daily_share"
    """
    from character.hori_prompt import GIRLFRIEND_SYSTEM_PROMPT, GIRLFRIEND_COMPACT_PROMPT
    from character.time_context import get_time_context
    from character.emotion import emotion_engine
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_BASE_URL,
    )

    # 构建 prompt
    if prompt_type == "morning":
        user_prompt = "现在是早上，你刚刚醒来/正在准备出门。给你男朋友发一条早安消息。要自然可爱，像真的女朋友早上发微信那样。1-3句话。不要用'早安！今天也要加油哦'这种刻板句式，要有你自己的风格。"
    elif prompt_type == "evening":
        user_prompt = "现在是晚上，你准备睡了/刚洗完澡/在沙发上休息。给你男朋友发一条晚安消息。要温柔自然，1-3句话。可以是催他睡觉、或者说今天很开心、或者说梦里见之类的。不要刻板。"
    else:  # daily_share
        user_prompt = random.choice(DAILY_SHARE_PROMPTS)

    system_prompt = GIRLFRIEND_SYSTEM_PROMPT + "\n" + get_time_context() + "\n" + emotion_engine.get_context()

    try:
        response = await client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.95,  # 高一点让消息更多样
            max_tokens=300,
        )
        reply = response.choices[0].message.content or ""
        return reply.strip()
    except Exception as e:
        logger.error(f"生成主动消息失败: {e}")
        # fallback 消息
        if prompt_type == "morning":
            return "早安呀亲爱的~ 今天天气不错呢☀️ 起床了吗？"
        elif prompt_type == "evening":
            return "晚安宝贝~ 今天辛苦了，早点休息哦💤 明天见！"
        else:
            return "突然好想你呀~ 你在干嘛呢？💕"


# ---------- 消息投递 ----------

async def deliver_message(message: str):
    """将消息投递到所有可用通道"""
    logger.info(f"📤 投递主动消息: {message[:60]}...")

    # 通道1: Web Push（网页聊天客户端）
    try:
        await web_push_queue.put({
            "type": "proactive",
            "content": message,
            "time": datetime.now().isoformat(),
        })
        logger.info("  → Web Push 已入队")
    except asyncio.QueueFull:
        logger.warning("  → Web Push 队列已满，丢弃")

    # 通道2: 微信客服消息（如果配置了公众号）
    if config.WECHAT_OA_APP_ID and config.WECHAT_OA_APP_SECRET:
        try:
            from wechat.official_account import send_customer_message
            # 注意：微信客服消息需要用户在48小时内有互动
            # 这里只做 best-effort 尝试
            await send_customer_message(message)
            logger.info("  → 微信客服消息已发送")
        except Exception as e:
            logger.warning(f"  → 微信客服消息发送失败: {e}")


# ---------- 主调度循环 ----------

tracker = SendTracker(state_file=os.path.join(os.path.dirname(__file__), "send_state.json"))


async def scheduler_loop():
    """
    主调度循环 - 每分钟检查一次
    """
    logger.info("⏰ 主动消息调度器已启动")
    logger.info("   ☀️  早安窗口: 7:00-8:59 (随机)")
    logger.info("   🌙  晚安窗口: 21:00-22:59 (随机)")
    logger.info("   💬  日常分享: 每天2-4次随机")

    while True:
        try:
            now = datetime.now()
            tracker.new_day()

            # 检查早安
            if tracker.should_send_morning(now):
                logger.info(f"☀️ 触发早安消息 (目标: {tracker.record.morning_target_time})")
                msg = await generate_proactive_message("morning")
                if msg:
                    await deliver_message(msg)
                tracker.mark_morning_sent()

            # 检查晚安
            elif tracker.should_send_evening(now):
                logger.info(f"🌙 触发晚安消息 (目标: {tracker.record.evening_target_time})")
                msg = await generate_proactive_message("evening")
                if msg:
                    await deliver_message(msg)
                tracker.mark_evening_sent()

            # 检查日常分享
            elif tracker.should_send_share(now):
                logger.info(f"💬 触发日常分享 (第{tracker.record.daily_share_count + 1}次)")
                msg = await generate_proactive_message("daily_share")
                if msg:
                    await deliver_message(msg)
                tracker.mark_share_sent()

            await asyncio.sleep(60)  # 每分钟检查一次

        except Exception as e:
            logger.error(f"调度器异常: {e}")
            await asyncio.sleep(60)


def record_user_message():
    """记录用户发消息（供外部调用）"""
    tracker.user_messaged()
