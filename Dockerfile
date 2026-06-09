# 京子 AI 女友 - Docker 镜像
# 用于 Zeabur / Railway 等云平台

FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 端口（Zeabur 通过 PORT 环境变量指定，默认 8000）
EXPOSE 8000

# 启动
CMD ["python", "main.py"]
