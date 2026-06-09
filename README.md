# 🎀 堀京子 AI Chat

以《堀与宫村》(Horimiya) 女主角 **堀京子 (Hori Kyoko)** 为原型的 AI 聊天机器人。

## 功能

- 🌐 **网页聊天** — 浏览器打开即可和堀聊天，支持流式打字机效果
- 📱 **微信公众号** — 接入公众号后，在微信里像聊天一样和堀对话（**24/7 在线，手机随时聊**）
- 💻 **微信 PC 桥接** — 本地 Windows 使用 wxauto 登录个人微信
- ⏰ **时间感知** — 堀拥有真实的时间观念，会根据时刻、星期、季节做出符合高中生作息的反应

---

## 🚀 快速开始（二选一）

### 方案 A：本地运行（网页聊天）

```bash
cd D:\kujingzi
pip install -r requirements.txt
python main.py
```
浏览器打开 http://localhost:8000 即可聊天。

### 方案 B：云端部署 + 微信公众号（推荐！手机随时聊）

不想让电脑一直开着？部署到 Railway（免费额度够用），然后接入微信公众号。

#### Step 1: 部署到 Railway

1. 把项目上传到 GitHub
2. 打开 [railway.app](https://railway.app) 用 GitHub 登录
3. 点 **New Project → Deploy from GitHub repo**
4. 选择你的仓库 → Railway 自动用 Dockerfile 构建
5. 在 Railway Dashboard → Variables 中添加环境变量：

```
DEEPSEEK_API_KEY=sk-b12ded90dc24451ebff8caebc4db9320
WECHAT_OA_TOKEN=你自编的Token（3-32位，比如 hori2024kyoko）
```

6. Railway 会分配一个域名，比如 `hori-bot.up.railway.app`

#### Step 2: 注册微信公众号

1. 去 [mp.weixin.qq.com](https://mp.weixin.qq.com) 注册 **个人订阅号**（免费，1-2天审核）
2. 审核通过后，进入「设置与开发 → 基本配置」
3. 在「服务器配置」中填写：
   - **URL**: `https://hori-bot.up.railway.app/wechat`
   - **Token**: 你在 Railway 环境变量中设的 `WECHAT_OA_TOKEN` 值
   - **EncodingAESKey**: 点随机生成
   - 消息加解密方式：选 **明文模式**
4. 点提交，微信会验证服务器 → 验证通过后启用

#### Step 3: 开始聊天！

手机打开微信 → 通讯录 → 公众号 → 找到你的公众号 → 发消息，堀就会回复你！

---

## 项目结构

```
kujingzi/
├── main.py                    # 启动入口
├── config.py                  # 配置
├── .env                       # 环境变量
├── Dockerfile                 # Docker 镜像 (Railway 部署用)
├── railway.json               # Railway 部署配置
├── requirements.txt
├── character/
│   ├── hori_prompt.py         # 堀京子角色 Prompt（核心！）
│   └── time_context.py        # 时间感知模块
├── llm/
│   └── deepseek_client.py     # DeepSeek API 客户端
├── memory/
│   └── chat_history.py        # 对话历史管理
├── web/
│   ├── routes.py              # 路由（Web + 公众号回调）
│   └── static/index.html      # 网页聊天 UI
├── wechat/
│   ├── bot.py                 # 微信 PC 桥接消息处理
│   ├── wechat_adapter.py      # 微信 PC 桥接适配层
│   └── official_account.py    # 微信公众号接入（NEW!）
└── utils/
    └── logger.py
```

---

## 环境变量参考

| 变量 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API Key |
| `WECHAT_OA_TOKEN` | 公众号必填 | 微信公众号 Token |
| `WECHAT_OA_APP_ID` | 可选 | 公众号 AppID |
| `WECHAT_OA_APP_SECRET` | 可选 | 公众号 AppSecret |
| `WECHAT_ENABLED` | 可选 | 启用微信 PC 桥接（仅 Windows） |
| `PORT` | 可选 | 服务端口（Railway 自动设置） |

---

## 常见问题

**Q: 部署到 Railway 后网页打不开？**
- Railway 免费版首次访问会冷启动（~30 秒），等一会就好

**Q: 微信公众号验证失败？**
- 确认 URL 是 `https://` 开头（不是 `http://`）
- 确认 Token 两边一致
- 确认选的是「明文模式」

**Q: 微信公众号回复很慢？**
- DeepSeek API 通常 2-3 秒回复，微信要求 5 秒内。偶尔超时会提示稍等
- Railway 免费版冷启动会慢一些

**Q: 可以用其他模型吗？**
- 可以！DeepSeek 兼容 OpenAI 格式，修改 `.env` 中的 `DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL` 即可
