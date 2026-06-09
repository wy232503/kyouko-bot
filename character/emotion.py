"""
情绪系统 — 让 AI 女友拥有自己的情绪状态

情绪会影响：
  - 回复的语气和内容
  - 主动分享的频率和话题
  - 早安/晚安的风格
"""
import random
import json
import os
from datetime import datetime
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)

# 情绪定义
EMOTIONS = {
    "开心": {"emoji": "😊", "weight": 20, "tone": "活泼可爱，话多，爱用~和颜文字"},
    "平静": {"emoji": "😌", "weight": 25, "tone": "温柔自然，像日常聊天"},
    "思念": {"emoji": "💕", "weight": 15, "tone": "撒娇，会说想你、问你在干嘛、想见面"},
    "撒娇": {"emoji": "🥺", "weight": 10, "tone": "软软的，想要被关心被哄"},
    "疲惫": {"emoji": "😴", "weight": 8, "tone": "话少，会抱怨累，想被你安慰"},
    "难过": {"emoji": "😢", "weight": 6, "tone": "低落，说话慢，需要你的关心"},
    "生气": {"emoji": "😤", "weight": 5, "tone": "傲娇模式全开！会哼哼、不理你（但其实等你哄）"},
    "兴奋": {"emoji": "🤩", "weight": 6, "tone": "超开心！话超多，分享欲爆棚"},
    "傲娇": {"emoji": "😒", "weight": 8, "tone": "嘴上嫌弃但心里甜的经典堀模式"},
    "担心": {"emoji": "😟", "weight": 5, "tone": "担心你、关心你的状态、会反复确认"},
}

# 时段情绪倾向：某些时段更容易出现某些情绪
TIME_EMOTION_BIAS = {
    # 早上 (5-9): 容易困、平静
    5: {"疲惫": +10, "平静": +5},
    6: {"疲惫": +8, "平静": +5},
    7: {"开心": +5, "平静": +5},
    8: {"开心": +8, "兴奋": +3},
    # 上午 (9-12): 正常
    # 下午 (12-17): 容易累、思念
    13: {"疲惫": +5},
    14: {"思念": +5, "疲惫": +5},
    15: {"思念": +5},
    16: {"思念": +8, "撒娇": +5},
    17: {"思念": +5, "撒娇": +3},
    # 晚上 (18-23): 放松、撒娇
    18: {"开心": +5, "平静": +5},
    19: {"开心": +8, "撒娇": +5},
    20: {"撒娇": +8, "思念": +8},
    21: {"撒娇": +10, "思念": +10},
    22: {"思念": +12, "撒娇": +8, "疲惫": +5},
    23: {"疲惫": +10, "思念": +8},
    # 深夜 (0-4): 困
    0: {"疲惫": +15, "思念": +5},
    1: {"疲惫": +20},
    2: {"疲惫": +25},
    3: {"疲惫": +25},
    4: {"疲惫": +20},
}


class EmotionEngine:
    """情绪引擎"""

    def __init__(self, state_file: str = "emotion_state.json"):
        self.state_file = state_file
        self.current_emotion = "平静"
        self.last_change = datetime.now()
        self.emotion_history: list = []  # 最近的情绪变化记录

    def load(self):
        """从文件加载情绪状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_emotion = data.get("emotion", "平静")
                    self.last_change = datetime.fromisoformat(data.get("last_change", datetime.now().isoformat()))
                    self.emotion_history = data.get("history", [])
                    logger.info(f"情绪状态已加载: {self.current_emotion}")
        except Exception as e:
            logger.warning(f"加载情绪状态失败: {e}，使用默认")

    def save(self):
        """保存情绪状态到文件"""
        try:
            data = {
                "emotion": self.current_emotion,
                "last_change": self.last_change.isoformat(),
                "history": self.emotion_history[-20:],  # 只保留最近 20 条
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存情绪状态失败: {e}")

    def get_emotion(self) -> str:
        """获取当前情绪"""
        self._maybe_change()
        return self.current_emotion

    def get_emoji(self) -> str:
        """获取当前情绪的表情"""
        return EMOTIONS.get(self.current_emotion, {}).get("emoji", "😊")

    def get_tone(self) -> str:
        """获取当前情绪的语调描述"""
        return EMOTIONS.get(self.current_emotion, {}).get("tone", "温柔自然")

    def get_context(self) -> str:
        """生成情绪上下文，注入到 System Prompt"""
        return f"你现在的情绪是「{self.current_emotion}」{self.get_emoji()}。说话风格：{self.get_tone()}。"

    def set_emotion(self, emotion: str, reason: str = ""):
        """手动设置情绪"""
        if emotion in EMOTIONS:
            old = self.current_emotion
            self.current_emotion = emotion
            self.last_change = datetime.now()
            entry = {
                "time": datetime.now().isoformat(),
                "from": old,
                "to": emotion,
                "reason": reason,
            }
            self.emotion_history.append(entry)
            logger.info(f"情绪变化: {old} → {emotion} ({reason})")
            self.save()

    def influence_by_message(self, message: str):
        """
        根据用户消息内容影响情绪
        """
        msg_lower = message.lower()

        # 正面词汇 → 变开心
        positive = ["爱你", "喜欢你", "想你", "宝贝", "亲爱的", "好可爱", "真棒", "厉害", "抱抱", "亲亲", "好美", "好漂亮"]
        if any(w in msg_lower for w in positive):
            if random.random() < 0.4:
                self.set_emotion("开心", "被你夸了/甜到了")
                return
            if random.random() < 0.3:
                self.set_emotion("撒娇", "被你甜到了想撒娇")
                return

        # 负面 → 可能难过
        negative = ["好累", "烦躁", "不开心", "郁闷", "压力", "加班", "生病"]
        if any(w in msg_lower for w in negative):
            if random.random() < 0.5:
                self.set_emotion("担心", "听说你不舒服/不开心")
                return

        # 争吵/批评 → 生气
        angry = ["滚", "烦死了", "别烦我", "你很烦", "不想理"]
        if any(w in msg_lower for w in angry):
            if random.random() < 0.6:
                self.set_emotion("生气", "你说的话让我不开心了")
                return
            if random.random() < 0.3:
                self.set_emotion("难过", "你说的话让我有点难过")
                return

    def _maybe_change(self):
        """随机检查是否需要改变情绪（约 15% 概率）"""
        # 情绪自然波动：约 15% 概率，但限制最小间隔 10 分钟
        minutes_since_change = (datetime.now() - self.last_change).total_seconds() / 60
        if minutes_since_change < 10:
            return

        if random.random() < 0.15:
            self._natural_shift()

    def _natural_shift(self):
        """自然情绪转变"""
        now = datetime.now()

        # 构建加权选择
        choices = []
        weights = []
        for name, info in EMOTIONS.items():
            if name == self.current_emotion:
                continue
            w = info["weight"]
            # 加上时段偏向
            bias = TIME_EMOTION_BIAS.get(now.hour, {}).get(name, 0)
            w = max(1, w + bias)
            choices.append(name)
            weights.append(w)

        if choices:
            new_emotion = random.choices(choices, weights=weights, k=1)[0]
            self.set_emotion(new_emotion, "情绪自然变化")


# 全局单例
emotion_engine = EmotionEngine(state_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), "emotion_state.json"))
