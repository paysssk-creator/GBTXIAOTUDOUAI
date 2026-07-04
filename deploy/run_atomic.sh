#!/usr/bin/env bash
# GBT Pro — 完整原子部署流程（在主机上执行）
# 调用顺序: preview → drill → promote；任一失败自动触发 rollback

set -euo pipefail

ROOT="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$ROOT"

echo "═══════════════════════════════════════════════════"
echo " GBT Pro · 部署面板 · 多维度空间 → 预演 → 灰度 → 生产"
echo "═══════════════════════════════════════════════════"

if [ -z "${1:-}" ]; then
  echo "用法: deploy/run_atomic.sh <release-tag> [--drill]"
  echo "示例: deploy/run_atomic.sh v1.0.7"
  echo "      deploy/run_atomic.sh v1.0.7 --drill   # 仅演练"
  exit 1
fi

TAG="$1"; shift
DRILL=""
if [ "${1:-}" = "--drill" ]; then DRILL="--drill"; fi

# ── 0) 配置来源检查（密钥管理一致性） ──
if [ ! -f deploy/.env.preview ]; then cp deploy/.env.example deploy/.env.preview; fi
if [ ! -f deploy/.env.prod    ]; then cp deploy/.env.example deploy/.env.prod;    fi
for v in DEEPSEEK_API_KEY; do
  if grep -q "^${v}=$" deploy/.env.prod; then echo "[FATAL] 生产 .env 缺少 ${v}"; exit 4; fi
done

# ── 1) 构建不可变镜像 ──
echo ""
echo "▶ [1] 构建不可变镜像 (tag=$TAG)"
docker build --pull -t "gbt-pro:$TAG" -f Dockerfile .

# ── 2) 预演（同一镜像 + 预发栈） ──
echo ""
echo "▶ [2] 启动预发 / 跑预演"
GBT_PREV_TAG="$(docker inspect --format '{{ index .Config.Labels "org.opencontainers.image.version"}}' gbt-pro:latest 2>/dev/null || echo previous)" \
GBT_RELEASE_TAG="$TAG" \
  python deploy/atomic_switch.py --new-tag "$TAG" --drill $DRILL

# ── 3) 灰度切换到生产 ──
echo ""
echo "▶ [3] 灰度切换到生产"
GBT_PREV_TAG="${GBT_PREV_TAG:-previous}" \
GBT_RELEASE_TAG="$TAG" \
  python deploy/atomic_switch.py --new-tag "$TAG" $DRILL || {
    echo ""
    echo "[FATAL] 生产切换失败 — 已在脚本内回滚"
    exit 5
  }

echo ""
echo "═══════════════════════════════════════════════════"
echo " 部署完成 tag=$TAG"
echo "═══════════════════════════════════════════════════"
