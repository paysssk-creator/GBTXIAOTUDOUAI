# syntax=docker/dockerfile:1
# 开发者: 自由的风
# GBT Pro · 一键安装容器镜像 · 多阶段构建
# 严格遵守"密钥不打包"铁律：runtime 镜像绝不包含 .env，通过环境变量注入

# ---------- 阶段 1：build ----------
ARG APP_VERSION=v1.1.17
ARG RELEASE_TAG=v1.1.17-desktop-runtime

FROM python:3.14.5-slim AS builder

WORKDIR /build

# 1) 装编译期依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2) 按 requirements.txt 装到独立 prefix（避开系统 site-packages）
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 3) 复制源码（已被 .dockerignore 过滤 .env / .git / data/audit）
COPY . .

# ---------- 阶段 2：runtime ----------
FROM python:3.14.5-slim

ARG APP_VERSION
ARG RELEASE_TAG

LABEL maintainer="自由的风" \
    app="GBT Pro" \
    version="${APP_VERSION}" \
    release_tag="${RELEASE_TAG}" \
    description="AI 驱动 A 股自主交易终端 · 多源降级行情 · Futurapay 支付集成"

WORKDIR /app

# 1) 复制编译好的依赖
COPY --from=builder /install /usr/local

# 2) 复制源码（仅应用代码，不含 .env / .git）
COPY --from=builder /build /app

# 3) 创建非 root 用户（最小权限原则）
RUN useradd -m -u 1000 gbt && \
    mkdir -p /app/data/pay /app/data/audit /app/data/release /app/data/preview && \
    chown -R gbt:gbt /app

USER gbt

# 4) 健康检查端点
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/status', timeout=3)" || exit 1

# 5) 暴露端口
EXPOSE 8765

# 6) 启动（生产用 waitress，非 dev server）
#    容器启动时需 -e FUTURAPAY_SITE_ID=... -e FUTURAPAY_API_KEY=... -e FUTURAPAY_MERCHANT_KEY=... 注入密钥
#    或挂载 /app/.env 到外部安全卷
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GBT_ROLE=prod \
    PORT=8765

CMD ["python", "-c", "from waitress import serve; from desktop_app import app; serve(app, host='0.0.0.0', port=8765, threads=4)"]

# ---------- 使用示例 ----------
# 构建：docker build --build-arg APP_VERSION=${APP_VERSION} --build-arg RELEASE_TAG=${RELEASE_TAG} -t gbt-pro:${APP_VERSION} .
# 启动：docker run -d \
#         -p 8765:8765 \
#         -e FUTURAPAY_SITE_ID=131052833 \
#         -e FUTURAPAY_API_KEY=<你的真实密钥，从 Key Vault 注入，绝不入镜像> \
#         -e FUTURAPAY_MERCHANT_KEY=<你的真实密钥> \
#         --name gbt-pro \
#         gbt-pro:${APP_VERSION}
