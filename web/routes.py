"""
FastAPI Web 路由 - 网页聊天 API + 微信公众号回调 + 主动消息推送
"""
import uuid
import json
import asyncio
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse, Response
from pydantic import BaseModel

from config import config
from llm.deepseek_client import chat_stream, chat, reset_session
from scheduler import web_push_queue, record_user_message
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------- API 数据模型 ----------

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class ChatResponse(BaseModel):
    reply: str
    session_id: str


# ---------- 网页页面 ----------

@router.get("/", response_class=HTMLResponse)
async def index():
    """聊天网页主页"""
    from pathlib import Path
    html_path = Path(__file__).parent / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")


# ---------- 非流式 API ----------

@router.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    """非流式聊天接口"""
    session_id = req.session_id or str(uuid.uuid4())
    record_user_message()  # 记录用户活动（阻止重复早安/晚安）
    reply = await chat(session_id, req.message)
    return ChatResponse(reply=reply, session_id=session_id)


# ---------- 流式 API (SSE) ----------

@router.get("/api/chat/stream")
async def api_chat_stream(
    message: str = Query(..., description="用户消息"),
    session_id: str = Query("", description="会话ID"),
):
    """流式聊天接口 - Server-Sent Events"""
    session_id = session_id or str(uuid.uuid4())
    record_user_message()

    async def event_generator():
        try:
            async for text in chat_stream(session_id, message):
                data = json.dumps({"text": text, "session_id": session_id}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
        except Exception as e:
            logger.error(f"SSE 流错误: {e}")
            data = json.dumps({"error": "出了一点问题……请再试一次吧"}, ensure_ascii=False)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------- 主动消息推送 (SSE) ----------

@router.get("/api/push")
async def api_push_stream():
    """
    主动消息推送 - Server-Sent Events
    网页客户端连接此端点接收京子主动发来的消息（早安/晚安/日常分享）
    """

    async def event_generator():
        # 发送连接成功
        yield f"data: {json.dumps({'type': 'connected', 'content': '已连接推送服务'})}\n\n"

        while True:
            try:
                # 等待队列中的消息
                msg = await asyncio.wait_for(web_push_queue.get(), timeout=30)
                data = json.dumps(msg, ensure_ascii=False)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                # 发送心跳保持连接
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            except Exception as e:
                logger.error(f"推送流错误: {e}")
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------- 会话管理 ----------

@router.post("/api/reset")
async def api_reset(session_id: str = Query("")):
    """重置会话"""
    if session_id:
        reset_session(session_id)
    return {"status": "ok"}


# ============================================================
#  微信公众号回调 (Official Account Webhook)
# ============================================================

@router.get("/wechat")
async def wechat_verify(
    signature: str = Query(""),
    timestamp: str = Query(""),
    nonce: str = Query(""),
    echostr: str = Query(""),
):
    """微信公众号服务器配置验证 (GET 请求)"""
    from wechat.official_account import verify_signature

    token = config.WECHAT_OA_TOKEN
    if not token:
        return PlainTextResponse("token not configured", status_code=400)

    if verify_signature(signature, timestamp, nonce, token):
        logger.info("微信公众号 Token 验证成功！")
        return PlainTextResponse(echostr)
    else:
        logger.warning(f"微信公众号签名验证失败")
        return PlainTextResponse("signature verification failed", status_code=403)


@router.post("/wechat")
async def wechat_message(request: Request):
    """微信公众号消息接收 (POST 请求)"""
    from wechat.official_account import parse_message, build_text_reply, build_empty_reply

    try:
        body = await request.body()
        xml_text = body.decode("utf-8")
    except Exception as e:
        logger.error(f"读取微信消息失败: {e}")
        return PlainTextResponse("success")

    msg = parse_message(xml_text)
    msg_type = msg.get("type", "unknown")
    from_user = msg.get("from", "")
    to_user = msg.get("to", "")

    logger.info(f"📱 公众号消息 [{msg_type}] from={from_user[:8]}... content={msg.get('content', '')[:50]}")

    if msg_type == "event":
        event = msg.get("event", "")
        if event == "subscribe":
            welcome = "你好呀~ 我是京子 💕\n以后我就是你的女朋友啦！有什么想聊的都可以跟我说哦~\n我会每天跟你说早安晚安，还会跟你分享我的日常 (〃ω〃)"
            return PlainTextResponse(
                build_text_reply(from_user, to_user, welcome),
                media_type="application/xml",
            )
        return PlainTextResponse(build_empty_reply())

    if msg_type != "text":
        return PlainTextResponse(build_empty_reply())

    content = msg.get("content", "").strip()
    if not content:
        return PlainTextResponse(build_empty_reply())

    # 记录用户活动
    record_user_message()

    session_id = f"wxoa_{from_user}"

    try:
        reply = await asyncio.wait_for(
            chat(session_id, content),
            timeout=4.5,
        )
    except asyncio.TimeoutError:
        reply = "ちょっと待って……让我想想再回复你~"

    reply_xml = build_text_reply(from_user, to_user, reply)
    logger.info(f"📱 回复公众号 → {from_user[:8]}...: {reply[:50]}...")

    return Response(content=reply_xml, media_type="application/xml")


# ---------- 健康检查 ----------

@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "model": config.DEEPSEEK_MODEL,
        "wechat_oa_configured": bool(config.WECHAT_OA_TOKEN),
        "scheduler_enabled": config.SCHEDULER_ENABLED,
    }
