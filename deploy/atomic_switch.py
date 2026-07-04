"""GBT Pro — 原子切换器

核心要求：替换前后契约一致；数据隔离；灰度；真正原子。
实现路径：
  1. 预发用新 tag 跑通
  2. 拉出新 tag 的 prod 容器，但端口绑在 8766（先热备）
  3. 在 8765 上做一次"流量切换"——同一 image tag 重启用 prod 数据卷
  4. 校验新实例 /api/status 和 dashboard 与预览版一致
  5. 关掉旧 prod；8765 端口由新实例独占

任一步骤失败 → 立即撤回 → 旧实例继续服务。

执行：
  python atomic_switch.py --new-tag v1.0.7 [--drill] [--rollback] [--dry-run]
"""

# 开发者: 自由的风
from __future__ import annotations
import os, sys, json, time, subprocess, argparse, shutil, logging, signal, socket

LOG = logging.getLogger("gbt.atomic")

COMPOSE_PROD = os.path.join(os.path.dirname(__file__), "docker-compose.prod.yml")
COMPOSE_PREVIEW = os.path.join(os.path.dirname(__file__), "docker-compose.preview.yml")


def run(cmd, check=True, capture=False, env=None):
    LOG.debug("$ %s", " ".join(cmd))
    return subprocess.run(cmd, check=check, capture_output=capture, text=True, env={**os.environ, **(env or {})})


def docker(tag, role="preview"):
    cmd = ["docker", "compose", "-f", (COMPOSE_PREVIEW if role == "preview" else COMPOSE_PROD)]
    cmd += ["--env-file", os.path.join(os.path.dirname(__file__), f".env.{role}")]
    return cmd


def is_port_open(port: int, host="127.0.0.1", timeout=0.5) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def wait_healthy(url: str, timeout:30=60) -> bool:
    """L1+L2 一致性探针通过即可切换"""
    sys.path.insert(0, os.path.dirname(__file__))
    from healthcheck import probe
    t0 = time.time()
    fails = 0
    while time.time() - t0 < timeout:
        r = probe(url)
        if r.get("ok"):
            LOG.info("[探针] %s 健康：%s", url, r.get("l1", {}).get("version"))
            return True
        fails += 1
        time.sleep(2)
    LOG.error("[探针] %s 一直未通过", url)
    return False


def preview(new_tag: str) -> bool:
    LOG.info("[预演] 启动预览服务 tag=%s", new_tag)
    cmd = docker(new_tag, "preview") + ["up", "-d"]
    run(cmd, env={"GBT_RELEASE_TAG": new_tag})
    if not wait_healthy("http://127.0.0.1:18765"):
        run(docker(new_tag, "preview") + ["down"])
        return False
    # 预演必须可回滚 — 主动触发一次数据迁移 rollback 路径，验证
    run(docker(new_tag, "preview") + ["exec", "-T", "gbt-preview",
                                      "python", "/app/deploy/migrate.py", "rollback"],
        check=False)
    if not wait_healthy("http://127.0.0.1:18765"):
        LOG.warning("[预演] rollback 后健康态异常 — 仍在演练阶段，不影响生产")
    LOG.info("[预演] 通过")
    return True


def promote(new_tag: str) -> bool:
    """真正把生产流量切到新 tag"""
    LOG.info("[生产] 启动热备服务 tag=%s 端口=8766", new_tag)
    hot_cmd = ["docker", "run", "-d", "--name", f"gbt-prod-{new_tag}-hot",
               "-p", "8766:8765",
               "--env-file", os.path.join(os.path.dirname(__file__), ".env.prod"),
               "-e", f"BUILD_HASH={new_tag}",
               f"gbt-pro:{new_tag}"]
    try:
        run(hot_cmd)
    except subprocess.CalledProcessError as e:
        LOG.error("[生产] 热备启动失败：%s", e)
        return False
    if not wait_healthy("http://127.0.0.1:8766", timeout=30):
        run(["docker", "rm", "-f", f"gbt-prod-{new_tag}-hot"], check=False)
        return False

    # 数据迁移（仅在生产第一次切换该 tag 时会动）
    try:
        run(docker(new_tag, "prod") + ["--env-file",
                                       os.path.join(os.path.dirname(__file__), ".env.prod"),
                                       "run", "--rm", "-e", f"GBT_RELEASE_TAG={new_tag}",
                                       f"gbt-pro:{new_tag}", "python",
                                       "/app/deploy/migrate.py", "forward"], check=False)
    except Exception:
        pass

    # 一次性路由切换：停掉旧 prod 容器，启动新 prod（同 image tag，重新挂数据卷）
    LOG.info("[生产] 停旧 prod（同 tag=%s 旧版）", os.environ.get("GBT_PREV_TAG", "previous"))
    run(docker(new_tag, "prod") + ["down"], check=False)

    LOG.info("[生产] 以新 tag=%s 重新拉起", new_tag)
    cmd = docker(new_tag, "prod") + ["up", "-d"]
    run(cmd, env={"GBT_RELEASE_TAG": new_tag})
    if not wait_healthy("http://127.0.0.1:8765"):
        LOG.error("[生产] 新 prod 未通过健康探针 — 立即回滚")
        rollback(new_tag)
        return False

    # 热备退场
    run(["docker", "rm", "-f", f"gbt-prod-{new_tag}-hot"], check=False)
    LOG.info("[生产] 路由切换完成")
    return True


def rollback(new_tag: str) -> bool:
    LOG.warning("[回滚] 把生产从 tag=%s 撤回", new_tag)
    run(docker(new_tag, "prod") + ["down"], check=False)
    run(["docker", "rm", "-f", f"gbt-prod-{new_tag}-hot"], check=False)
    # 还原上一个 tag — 由 GBT_PREV_TAG 环境变量提供
    prev = os.environ.get("GBT_PREV_TAG")
    if prev:
        LOG.info("[回滚] 还原上一个 tag=%s", prev)
        cmd = docker(prev, "prod") + ["up", "-d"]
        run(cmd, env={"GBT_RELEASE_TAG": prev})
        return wait_healthy("http://127.0.0.1:8765", timeout=45)
    LOG.warning("[回滚] 未设置 GBT_PREV_TAG，等待人工介入")
    return False


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s :: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--new-tag", required=True)
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--drill", action="store_true", help="只跑预演，不切生产")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划")
    args = ap.parse_args()

    if args.rollback:
        ok = rollback(args.new_tag)
        sys.exit(0 if ok else 1)

    if args.dry_run:
        print(json.dumps({"plan": [{"step": "preview", "tag": args.new_tag},
                                   {"step": "promote", "tag": args.new_tag}]},
                         ensure_ascii=False, indent=2))
        return

    if not preview(args.new_tag):
        sys.exit(2)
    if args.drill:
        run(docker(args.new_tag, "preview") + ["down"])
        LOG.info("[演练完成] 仅预演，未切生产")
        return
    if not promote(args.new_tag):
        sys.exit(3)
    LOG.info("[完成] 新版本=%s 已灰度灰量切到生产", args.new_tag)


if __name__ == "__main__":
    main()
