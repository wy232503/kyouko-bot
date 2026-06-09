"""
微信公众号 (Official Account) 接入模块
处理微信服务器回调：Token 验证 + 消息收发 + 客服消息（主动推送）

使用方式:
  1. 注册微信公众号 (mp.weixin.qq.com) → 个人订阅号
  2. 在「设置与开发 → 基本配置」中配置服务器 URL
  3. 设置 Token（与 .env 中的 WECHAT_OA_TOKEN 一致）

客服消息说明:
  - 认证订阅号/服务号可使用客服消息接口，在 48h 内主动给用户发消息
  - 未认证订阅号不支持客服消息，需升级认证
"""
import time
import hashlib
import httpx
import xml.etree.ElementTree as ET
from utils.logger import get_logger
from config import config

logger = get_logger(__name__)

# 微信 access_token 缓存
_access_token_cache: dict = {"token": "", "expires_at": 0}


# ---------- 签名验证 ----------

def verify_signature(signature: str, timestamp: str, nonce: str, token: str) -> bool:
    """验证微信服务器签名"""
    if not all([signature, timestamp, nonce, token]):
        return False
    tmp_list = sorted([token, timestamp, nonce])
    tmp_str = "".join(tmp_list)
    computed = hashlib.sha1(tmp_str.encode("utf-8")).hexdigest()
    return computed == signature


# ---------- XML 消息解析 ----------

def parse_message(xml_text: str) -> dict:
    """解析微信发来的 XML 消息"""
    try:
        root = ET.fromstring(xml_text)
        msg_type = root.find("MsgType")
        msg_type = msg_type.text if msg_type is not None else "unknown"

        result = {
            "from": _get_xml_text(root, "FromUserName"),
            "to": _get_xml_text(root, "ToUserName"),
            "type": msg_type,
            "msg_id": _get_xml_text(root, "MsgId"),
            "create_time": _get_xml_text(root, "CreateTime"),
        }

        if msg_type == "text":
            result["content"] = _get_xml_text(root, "Content")
        elif msg_type == "event":
            result["event"] = _get_xml_text(root, "Event")
            result["content"] = ""
        else:
            result["content"] = ""

        return result
    except ET.ParseError as e:
        logger.error(f"XML 解析失败: {e}")
        return {"from": "", "to": "", "type": "unknown", "content": ""}


def _get_xml_text(element, tag: str) -> str:
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else ""


# ---------- XML 回复构建 ----------

def build_text_reply(to_user: str, from_user: str, content: str) -> str:
    """构建微信文本回复 XML"""
    xml = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
    return xml


def build_empty_reply() -> str:
    """返回空回复"""
    return "success"


# ---------- Access Token 管理 ----------

async def get_access_token() -> str:
    """
    获取微信公众号 access_token（带缓存，自动刷新）
    需要配置 WECHAT_OA_APP_ID 和 WECHAT_OA_APP_SECRET
    """
    global _access_token_cache

    # 缓存未过期
    if _access_token_cache["token"] and time.time() < _access_token_cache["expires_at"]:
        return _access_token_cache["token"]

    app_id = config.WECHAT_OA_APP_ID
    app_secret = config.WECHAT_OA_APP_SECRET

    if not app_id or not app_secret:
        raise ValueError("未配置 WECHAT_OA_APP_ID / WECHAT_OA_APP_SECRET")

    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            data = resp.json()

            if "access_token" in data:
                _access_token_cache["token"] = data["access_token"]
                # 提前 5 分钟过期
                _access_token_cache["expires_at"] = time.time() + data.get("expires_in", 7200) - 300
                logger.info("Access token 已刷新")
                return _access_token_cache["token"]
            else:
                logger.error(f"获取 access_token 失败: {data}")
                raise ValueError(f"微信返回错误: {data}")
    except Exception as e:
        logger.error(f"获取 access_token 异常: {e}")
        raise


# ---------- 客服消息（主动推送） ----------

async def send_customer_message(content: str, to_user: str = "") -> bool:
    """
    通过微信客服消息接口主动发送消息给用户

    限制:
      - 需要认证订阅号或服务号
      - 用户需在 48 小时内有互动
      - 未认证订阅号调用会失败

    Args:
        content: 消息内容
        to_user: 接收用户的 OpenID（留空则不发，仅记录日志）
    """
    if not config.WECHAT_OA_APP_ID or not config.WECHAT_OA_APP_SECRET:
        logger.debug("公众号未完整配置，跳过客服消息")
        return False

    if not to_user:
        logger.debug("未指定接收用户，跳过客服消息发送")
        return False

    try:
        access_token = await get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"

        body = {
            "touser": to_user,
            "msgtype": "text",
            "text": {"content": content},
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body, timeout=10)
            data = resp.json()

            if data.get("errcode") == 0:
                logger.info(f"客服消息发送成功 → {to_user[:8]}...")
                return True
            else:
                logger.warning(f"客服消息发送失败: {data}")
                return False
    except Exception as e:
        logger.error(f"客服消息发送异常: {e}")
        return False
