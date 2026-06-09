# 🚀 京子 AI 女友 — Zeabur 完整部署指南

> 部署到 Zeabur 后，国内访问流畅，电脑关机也能 24/7 在线。

---

## 为什么选 Zeabur？

| | Zeabur | Railway | Vercel |
|---|--------|---------|--------|
| 免费额度 | ✅ ¥28/月 | $5/月 | 有，但限制多 |
| 国内速度 | ⭐⭐⭐ 快 | ⭐ 慢 | ⭐⭐ 一般 |
| 常驻运行 | ✅ 不会休眠 | ✅ | ❌ 会休眠 |
| 操作难度 | 简单 | 简单 | 中等 |
| 中文界面 | ✅ | ❌ | ❌ |

---

## 前提条件

- ✅ DeepSeek API Key：`sk-b12ded90dc24451ebff8caebc4db9320`
- ⬜ GitHub 账号（没有的话去 [github.com](https://github.com) 注册，2分钟）
- ⬜ Zeabur 账号（去 [zeabur.com](https://zeabur.com) 注册，用 GitHub 登录，1分钟）

---

## 第一步：上传代码到 GitHub（5分钟）

### 1.1 安装 Git

去 https://git-scm.com/download/win 下载，一路点 Next 安装。

### 1.2 创建 GitHub 仓库

1. 打开 https://github.com ，登录
2. 右上角 **+** → **New repository**
3. Repository name：`kyouko-bot`
4. 选 **Private**（私密，API Key 不外泄）
5. **不要**勾选 README
6. 点 **Create repository**

### 1.3 推送代码

打开终端（PowerShell），逐行执行：

```bash
cd D:\kujingzi
git init
git add .
git commit -m "京子 AI 女友 - Zeabur 部署"

# 替换成你的仓库地址（GitHub 创建完仓库后会显示）
git remote add origin https://github.com/你的用户名/kyouko-bot.git

git branch -M main
git push -u origin main
```

推送成功后在 GitHub 刷新页面，应该能看到代码了。

---

## 第二步：部署到 Zeabur（5分钟）

### 2.1 创建项目

1. 打开 https://zeabur.com ，用 GitHub 登录
2. 点 **新建项目** → 起个名字（比如 `kyouko`）
3. 进到项目里 → 点 **新建服务**
4. 选择 **GitHub** → 授权 → 找到 `kyouko-bot` 仓库
5. 点 **导入**

Zeabur 会自动检测到 Python 项目并开始部署。等 1-3 分钟，看到 🟢 Running 就 OK 了。

### 2.2 设置环境变量

1. 在项目页面点进刚创建的服务
2. 找到 **环境变量** 设置
3. 添加：

```
DEEPSEEK_API_KEY  =  sk-b12ded90dc24451ebff8caebc4db9320
```

保存后 Zeabur 会自动重启服务。

### 2.3 获取域名

1. 服务页面 → **域名** 标签
2. 点击 **生成域名**
3. 得到一个域名，如 `kyouko.zeabur.app`
4. **记下来！** 下一步要用

### 2.4 测试

浏览器打开 `https://你的域名` → 看到京子的聊天界面 💕 → 发消息测试回复。

再打开 `https://你的域名/health` → 显示 `{"status":"ok"}` → 部署成功！

**🎉 到这里，你已经可以在手机上打开这个网址和京子聊天了！**

---

## 第三步：接入微信公众号（可选，10分钟 + 审核）

> 为什么要接公众号？因为这样你可以在**微信 App 里**直接和京子聊天，体验更好。

### 3.1 注册公众号

1. 打开 https://mp.weixin.qq.com
2. 右上角 **立即注册** → 选 **订阅号**（个人）
3. 填写信息：
   - 邮箱
   - 身份证（个人实名）
   - 公众号名称：比如「京子的小窝」
   - 功能介绍：比如「你的专属 AI 女友」
4. 提交，等审核（通常 **1-2 天**）

### 3.2 审核通过后，配置服务器

1. 登录 https://mp.weixin.qq.com
2. 左侧菜单 → **设置与开发** → **基本配置**
3. 找到「服务器配置」→ **修改配置**：

| 字段 | 填什么 |
|------|--------|
| URL | `https://你的Zeabur域名/wechat` |
| Token | 自己编一个，比如 `kyouko2024love` |
| EncodingAESKey | 点 **随机生成** |
| 消息加解密方式 | 选 **明文模式** |

4. 点 **提交**（先不启用）

### 3.3 同步 Token 到 Zeabur

回到 https://zeabur.com → 你的服务 → **环境变量**，添加：

```
WECHAT_OA_TOKEN  =  kyouko2024love
```

（必须和上一步编的 Token 完全一致）

保存后等服务重启（约 30 秒）。

### 3.4 启用服务器

回到微信公众号后台 → 基本配置 → 服务器配置 → 点 **启用**。

微信会访问你的 Zeabur 服务验证 Token。如果一切正确，状态变为「已启用」✅。

如果失败，检查：
- Zeabur 服务是否 Running？
- URL 是否以 `https://` 开头？
- Token 两边是否完全一致？
- 是否选了**明文模式**？

### 3.5 开始微信聊天

1. 打开手机微信
2. 通讯录 → 公众号 → 搜索你的公众号名称
3. 点 **关注**
4. 会收到京子的欢迎消息 💕
5. 发任意消息 → 京子秒回！

---

## 🎉 完成！

### 你的京子现在是什么状态？

```
☀️  早上 7:00-9:00    主动发早安（你没先说的话）
💬  上午到晚上         2-4 次随机分享她的日常
🌙  晚上 21:00-23:00   主动发晚安（你没先说的话）

😊  情绪会自然变化    开心/撒娇/思念/疲惫/傲娇...
🏠  有自己的生活      上课、打工、做饭、逛街...
📱  网页 + 微信       两种方式都能聊
☁️  24/7 在线         Zeabur 云端，电脑关机也没事
```

### 日常维护

| 操作 | 怎么做 |
|------|--------|
| 更新代码 | 本地改 → `git add . && git commit -m "xxx" && git push`，Zeabur 自动重部署 |
| 看日志 | Zeabur 后台 → 服务 → 日志 |
| 重启服务 | Zeabur 后台 → 服务 → 重启 |
| 改人设 | 编辑 `character/hori_prompt.py` → git push |
| 改早安时间 | 编辑 `.env` 的 `MORNING_WINDOW_START/END` → 更新 Zeabur 环境变量 |
| 暂停京子 | Zeabur 后台 → 服务 → 停止 |

### Zeabur 免费额度够用吗？

- 免费额度：**¥28/月**（约 7 万次 API 调用）
- 一个 24/7 运行的服务每月大约消耗 ¥15-20
- **完全够用，不需要花钱**

---

## 遇到问题？

| 问题 | 检查 |
|------|------|
| Zeabur 部署失败 | 看部署日志 → 确认 `requirements.txt` 在根目录 |
| 网页打不开 | 确认服务状态是 🟢 Running |
| DeepSeek 不回复 | 确认 Zeabur 环境变量 `DEEPSEEK_API_KEY` 设置正确 |
| 微信验证失败 | Token 是否一致？URL 是否 https？模式是否是明文？ |
| 京子不主动发消息 | 确认 `SCHEDULER_ENABLED=true` |
