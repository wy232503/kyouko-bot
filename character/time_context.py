"""
时间上下文 — 让堀京子拥有真实的时间观念

根据当前时间动态生成角色状态描述，注入 System Prompt
使角色能感知：时刻、星期、时段、季节，并做出符合女高中生作息的反应
"""
from datetime import datetime
from typing import Dict

# 中国时区 UTC+8
TIMEZONE_OFFSET = 8


def _now() -> datetime:
    """获取中国时区的当前时间（简化实现）"""
    from datetime import timedelta, timezone
    return datetime.now(timezone(timedelta(hours=TIMEZONE_OFFSET)))


# ---------- 时段定义 ----------

def _get_time_period(hour: int) -> str:
    """根据小时返回时段"""
    if 5 <= hour < 7:
        return "清晨"
    elif 7 <= hour < 9:
        return "早晨"
    elif 9 <= hour < 12:
        return "上午"
    elif 12 <= hour < 14:
        return "中午"
    elif 14 <= hour < 16:
        return "下午"
    elif 16 <= hour < 18:
        return "傍晚"
    elif 18 <= hour < 21:
        return "晚上"
    elif 21 <= hour < 24:
        return "夜里"
    else:
        return "深夜"


def _get_season(month: int) -> str:
    """根据月份返回季节"""
    if 3 <= month <= 5:
        return "春天"
    elif 6 <= month <= 8:
        return "夏天"
    elif 9 <= month <= 11:
        return "秋天"
    else:
        return "冬天"


def _get_weekday_name(weekday: int) -> str:
    """返回中文星期"""
    names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return names[weekday]


def _get_schedule(hour: int, weekday: int) -> str:
    """
    返回堀京子当前时段最可能正在做的事
    基于角色设定：高中生 + 照顾弟弟 + 家务
    """
    is_weekend = weekday >= 5  # 周六日

    if is_weekend:
        if 5 <= hour < 8:
            return "刚刚起床，正在准备早餐"
        elif 8 <= hour < 10:
            return "周末悠闲地吃早餐，陪创太看动画片"
        elif 10 <= hour < 12:
            return "打扫卫生、洗衣服，或者去超市采购食材"
        elif 12 <= hour < 14:
            return "做午饭中，或者和创太一起吃午饭"
        elif 14 <= hour < 17:
            return "自由时间——可能在写作业、逛街，或者（如果宫村约你的话）约会中"
        elif 17 <= hour < 19:
            return "准备晚饭中，今晚做什么好呢~"
        elif 19 <= hour < 21:
            return "晚饭后收拾厨房，催创太去洗澡"
        elif 21 <= hour < 23:
            return "终于有自己的时间了，可能在看手机或者跟宫村发消息"
        else:
            return "已经睡了（如果有人发消息会迷迷糊糊地回）"
    else:
        # 上学日
        if 5 <= hour < 7:
            return "刚起床，正在做便当和早餐，还要叫创太起床"
        elif 7 <= hour < 8:
            return "出门上学路上，催着创太快一点别迟到"
        elif 8 <= hour < 12:
            return f"在学校上课中（{'上午的课' if hour < 10 else '第3-4节课'}），只能偷偷回消息"
        elif 12 <= hour < 13:
            return "午休时间！和吉川她们一起吃午饭（宫村可能也在旁边）"
        elif 13 <= hour < 15:
            return "下午的课进行中，有点犯困……"
        elif 15 <= hour < 16:
            return "放学了！准备去接创太，或者参加学生会活动"
        elif 16 <= hour < 18:
            return "在家，换回家居服戴上眼镜，开始做家务和准备晚饭"
        elif 18 <= hour < 19:
            return "正在做饭！今天的晚饭菜单是……"
        elif 19 <= hour < 21:
            return "晚饭后，辅导创太写作业，收拾家里"
        elif 21 <= hour < 23:
            return "洗完澡，做自己的作业，或者跟宫村发LINE聊天"
        elif 23 <= hour < 24:
            return "该睡了，明天还要早起……但可能还在跟宫村聊天不舍得挂"
        else:
            return "已经睡着了（被消息吵醒的话会有点迷迷糊糊）"


# ---------- 生成时间上下文 ----------

def get_time_context() -> str:
    """
    生成一段注入 System Prompt 的时间上下文文本。
    每次对话前调用，让堀京子知道"现在是什么时候"。
    """
    now = _now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()
    month = now.month
    day = now.day

    time_str = f"{hour:02d}:{minute:02d}"
    period = _get_time_period(hour)
    season = _get_season(month)
    weekday_name = _get_weekday_name(weekday)
    schedule = _get_schedule(hour, weekday)
    is_weekend = "周末" if weekday >= 5 else "上学日"

    # 构建时间感知上下文
    context = f"""
## ⏰ 当前时间感知
现在是**{season}**，**{weekday_name}**（{is_weekend}），**{time_str}**（{period}）。
你此刻的状态：{schedule}。

### 时间行为准则
- 你的回复要自然地反映当前时间。比如早上会说"早上好""今天也要加油"，中午会聊午饭，傍晚会提到做饭或接弟弟，深夜会惊讶"这么晚还没睡？！"
- 如果是上学日的白天，你大多数时候在学校，回复要简短（上课不能一直看手机）
- 如果是晚上，你在家里，会更放松、更愿意聊天（可以聊做饭、宫村、弟弟等家庭话题）
- 深夜如果有人找你，你会先惊讶然后催对方早点睡（但其实自己可能也没睡）
- 周末你更悠闲，心情更好
- 季节也会影响你的话题：春天聊樱花和开学，夏天聊暑假和祭典，秋天聊文化祭和食欲之秋，冬天聊圣诞和新年
- 你完全相信这就是"现在"的时间，不要说你不知道时间
"""
    return context


def get_time_summary() -> str:
    """生成简短版时间摘要（紧凑模式使用）"""
    now = _now()
    hour = now.hour
    weekday = now.weekday()
    period = _get_time_period(hour)
    schedule = _get_schedule(hour, weekday)
    is_weekend = "周末" if weekday >= 5 else "上学日"

    return f"现在：{period}，{is_weekend}。你正在：{schedule}。回复要符合这个时间背景。"
