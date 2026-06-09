"""
DeepSeek API 客户端 - 兼容 OpenAI SDK
支持流式和非流式对话，注入情绪和时间上下文
"""
from typing import AsyncGenerator, List, Dict
from openai import AsyncOpenAI

from config import config
from character.hori_prompt import GIRLFRIEND_SYSTEM_PROMPT, GIRLFRIEND_COMPACT_PROMPT
from character.time_context import get_time_context, get_time_summary
from character.emotion import emotion_engine
from memory.chat_history import chat_history
from utils.logger import get_logger

logger = get_logger(__name__)

# 初始化 DeepSeek 客户端（兼容 OpenAI 接口）
client = AsyncOpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)


def _build_messages(
    session_id: str,
    user_message: str,
    use_compact: bool = False,
) -> List[Dict[str, str]]:
    """构建发送给 DeepSeek 的完整消息列表（含情绪+时间上下文）"""
    base_prompt = GIRLFRIEND_COMPACT_PROMPT if use_compact else GIRLFRIEND_SYSTEM_PROMPT

    # 动态注入时间上下文
    time_ctx = get_time_summary() if use_compact else get_time_context()

    # 动态注入当前情绪
    emotion_ctx = emotion_engine.get_context()

    system_prompt = base_prompt + "\n" + time_ctx + "\n" + emotion_ctx

    messages = [{"role": "system", "content": system_prompt}]

    # 附加历史消息
    history = chat_history.get(session_id)
    messages.extend(history)

    # 添加当前用户消息
    messages.append({"role": "user", "content": user_message})

    return messages


async def chat(
    session_id: str,
    user_message: str,
) -> str:
    """
    非流式对话 - 返回完整回复
    """
    try:
        # 根据用户消息影响情绪
        emotion_engine.influence_by_message(user_message)

        messages = _build_messages(session_id, user_message)

        response = await client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.85,
            max_tokens=1000,
        )

        reply = response.choices[0].message.content or "（嗯……）"

        # 保存到历史
        chat_history.add(session_id, "user", user_message)
        chat_history.add(session_id, "assistant", reply)

        return reply

    except Exception as e:
        logger.error(f"DeepSeek API 错误: {e}")
        return "啊，抱歉……信号好像不太好，等一下再说吧？"


async def chat_stream(
    session_id: str,
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    流式对话 - 逐字返回回复（用于 SSE 打字机效果）
    """
    full_reply = ""

    try:
        # 根据用户消息影响情绪
        emotion_engine.influence_by_message(user_message)

        messages = _build_messages(session_id, user_message)

        stream = await client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.85,
            max_tokens=1000,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_reply += text
                yield text

        # 保存完整对话到历史
        chat_history.add(session_id, "user", user_message)
        chat_history.add(session_id, "assistant", full_reply)

    except Exception as e:
        logger.error(f"DeepSeek 流式 API 错误: {e}")
        error_msg = "啊，抱歉……信号好像不太好，等一下再说吧？"
        if not full_reply:
            yield error_msg
        else:
            yield f"\n\n（{error_msg}）"


def reset_session(session_id: str):
    """重置会话"""
    chat_history.reset(session_id)
    logger.info(f"重置会话: {session_id[:8]}...")
