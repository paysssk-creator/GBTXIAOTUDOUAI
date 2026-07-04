"""GBT Pro — 不可变启动入口
由生产镜像 ENTRYPOINT 固定调用，启动只做三件事：
 1) 等前置迁移（idempotent）
 2) 校验配置 + 健康探针能起
 3) 把 waitress / Flask 拉起

任何环境差异都在容器启动时被剔除。
"""

# 开发者: 自由的风
import os, sys, json, time, signal, logging, traceback

# ── 数据 / 日志 / 配置 路径强制可控（防止"看起来一样，实则不同"） ──
DATA_DIR = os.environ.get("GBT_DATA_DIR", "/app/data")
LOG_DIR = os.environ.get("GBT_LOG_DIR", "/app/logs")
ROLE = os.environ.get("GBT_ROLE", "prod")
BUILD_HASH = os.environ.get("BUILD_HASH", "unknown")

for d in (DATA_DIR, LOG_DIR):
    os.makedirs(d, exist_ok=True)

logging.basicConfig(
    level=os.environ.get("GBT_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "gbt.launcher.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("gbt.launcher")

# ── 1) 强制环境变量已注入 ──
REQUIRED = ["GBT_PORT", "GBT_BIND"]
missing = [k for k in REQUIRED if not os.environ.get(k)]
if missing:
    log.error("缺少必须环境变量: %s", missing)
    sys.exit(2)


def _shutdown(signum, _):
    log.warning("收到信号 %s，开始优雅退出", signum)
    sys.exit(0)


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

# ── 2) 跑迁移（永远幂等） ──
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from migrate import run_migrations
    res = run_migrations(DATA_DIR, direction="forward")
    log.info("[迁移] forward %s", res)
except Exception as e:
    log.error("[迁移失败] %s\n%s", e, traceback.format_exc())
    # 迁移失败 → 直接拒绝启动，符合"回滚优于硬上"
    sys.exit(3)

# ── 3) 拉起应用 ──
PORT = int(os.environ["GBT_PORT"])
BIND = os.environ["GBT_BIND"]

# desktop_app.py 用的是内置 Flask 开发服务器 — 生产用 waitress
from waitress import serve  # type: ignore

# 动态导入，避免提前副作用
sys.path.insert(0, "/app")
import desktop_app  # noqa: E402
app = desktop_app.app

log.info("=" * 60)
log.info("GBT Pro 启动  ROLE=%s VERSION=%s BIND=%s:%s", ROLE, BUILD_HASH, BIND, PORT)
log.info("数据目录=%s  日志目录=%s", DATA_DIR, LOG_DIR)
log.info("=" * 60)


def _health_app(_environ, start_response):
    payload = json.dumps({"ok": True, "role": ROLE, "version": BUILD_HASH}).encode()
    start_response("200 OK", [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(payload))),
    ])
    return [payload]


serve(app, host=BIND, port=PORT, threads=8, ident=f"gbt-pro/{BUILD_HASH}")
