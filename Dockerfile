# 堀京子 AI Chat - Docker 镜像
# 用于 Railway / 任意支持 Docker 的云平台部署

FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# Railway 通过 PORT 环境变量指定端口
EXPOSE 8000

# 启动命令
CMD ["python", "main.py"]
