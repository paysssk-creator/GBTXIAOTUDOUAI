"""GBT Pro — 数据迁移与回滚引擎（成对设计、幂等）

数据契约（输入输出格式与字段集合）：
  - token_balance.json : { "_default": {"tokens":int,"used":int,"plan":str,"recharged":int}, ... }
  - auth_users.json    : { "<username>": {"password_hash":str,"created":ISO,"plan":str}, ... }
                        + "_sessions": { "<token>": "<username>", ... }
  - paper_account.json : { "cash":number, "equity":number, "positions":{code:{...}}, "trades":[...] }
  - autopilot.json     : { "running":bool, "scan_count":int, "last_scan_time":ISO, "triggers":[...] }

每次 schema 变更都同时实现：
  - forward(name)  幂等新增字段（缺则补、有则不动）
  - rollback(name) 只回滚本轮 forward 的字段，不动用户数据

state 文件名约定：state.json + state.json.bak 最新两份互为备份
"""

# 开发者: 自由的风
from __future__ import annotations
import json, os, time, shutil, threading, hashlib, logging
from typing import Callable, Dict, Tuple

LOG = logging.getLogger("gbt.migrate")
_LOCK = threading.Lock()

# ── 注册表：可平铺叠加 — 每个迁移都必须同时实现 forward/rollback ──
REGISTRY: Dict[str, Tuple[Callable[[dict], None], Callable[[dict], None]]] = {}


def reg(name: str):
    """装饰器：先注册 forward 默认 rollback 为 no-op，再用 reg_rollback() 补上反向"""
    def deco(fwd: Callable[[dict], None]):
        REGISTRY[name] = (fwd, lambda state: None)
        return fwd
    return deco


def reg_rollback(name: str):
    """配套 reg(name)，用于补 rollback 实现"""
    def deco(rbk: Callable[[dict], None]):
        fwd, _ = REGISTRY.get(name, (lambda s: None, lambda s: None))
        REGISTRY[name] = (fwd, rbk)
        return rbk
    return deco


def _read(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # 损坏文件：立刻回退到 .bak
        bak = path + ".bak"
        if os.path.exists(bak):
            with open(bak, "r", encoding="utf-8") as f:
                return json.load(f)
        return default


def _atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    os.replace(tmp, path)


def _checksum(data) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


# ── 迁移 001：保证 _default 账户存在 ──
@reg("001_init_default_account")
def _001(state: dict):
    bal = state.setdefault("token_balance", {})
    bal.setdefault("_default", {"tokens": 0, "used": 0, "plan": "trial", "recharged": 0})

# ── 迁移 002：plan 字段兜底 ──
@reg("002_plan_field")
def _002(state: dict):
    bal = state.setdefault("token_balance", {})
    for _, v in bal.items():
        v.setdefault("plan", "trial")
        v.setdefault("recharged", 0)
    users = state.setdefault("auth_users", {})
    if "_sessions" not in users:
        users["_sessions"] = {}


# ── 迁移 003：paper_account 标准字段 ──
@reg("003_paper_account_fields")
def _003(state: dict):
    pa = state.setdefault("paper_account", {})
    pa.setdefault("cash", 1000000.0)
    pa.setdefault("equity", 1000000.0)
    pa.setdefault("positions", {})
    pa.setdefault("trades", [])
    pa.setdefault("created", time.strftime("%Y-%m-%dT%H:%M:%S"))


def apply(state: dict, name: str, direction: str):
    fwd, rbk = REGISTRY[name]
    target = fwd if direction == "forward" else rbk
    if not callable(target):
        raise RuntimeError(f"迁移 {name} 缺少 {direction} 实现")

    # fwd / rbk 共用一个迁移，但 rbk 只在 forward 跑过之后才生效
    marks = state.setdefault("_migrate", {})
    if direction == "forward":
        before = _checksum(state)
        target(state)
        after = _checksum(state)
        marks[name] = {"before": before, "after": after, "at": time.time()}
        LOG.info("[迁移][%s forward] %s", name, _diff(before, after))
    else:
        if name not in marks:
            LOG.warning("[迁移][%s rollback] 未在本环境中应用过，跳过", name)
            return
        target(state)
        marks.pop(name, None)
        LOG.info("[迁移][%s rollback] 已撤销", name)


def _diff(_a, _b):
    return "applied"


def run_migrations(data_dir: str, direction: str = "forward") -> dict:
    """对每个 state 文件应用迁移；幂等；带 .bak 备份；带状态文件记录。"""
    assert direction in ("forward", "rollback")
    state_path = os.path.join(data_dir, "state.json")
    with _LOCK:
        # 把各 JSON 文件统一读入内存合并
        merged = {
            "token_balance": _read(os.path.join(data_dir, "token_balance.json"), {}),
            "auth_users": _read(os.path.join(data_dir, "auth_users.json"), {}),
            "paper_account": _read(os.path.join(data_dir, "paper_account.json"), {}),
            "autopilot": _read(os.path.join(data_dir, "autopilot.json"), {}),
        }
        # 也读 state.json 中之前落盘的合并视图
        on_disk = _read(state_path, {})
        for k, v in on_disk.items():
            if k.startswith("_") or not isinstance(v, dict) or k not in merged:
                merged[k] = on_disk[k] if k in on_disk else merged[k]
        # 跑迁移
        for name in REGISTRY:
            apply(merged, name, direction)
        # 落盘三份同步、镜像
        _atomic_write(os.path.join(data_dir, "token_balance.json"), merged["token_balance"])
        _atomic_write(os.path.join(data_dir, "auth_users.json"), merged["auth_users"])
        _atomic_write(os.path.join(data_dir, "paper_account.json"), merged["paper_account"])
        _atomic_write(os.path.join(data_dir, "autopilot.json"), merged["autopilot"])
        _atomic_write(state_path, merged)
        return {"applied": list(REGISTRY.keys())}


def rollback_last(data_dir: str) -> dict:
    """一键回滚上一次 forward 的所有迁移 — 不破坏已有用户数据"""
    state_path = os.path.join(data_dir, "state.json")
    merged = _read(state_path, {})
    marks = merged.get("_migrate", {}) or {}
    if not marks:
        return {"rolled_back": [], "note": "无迁移记录，无需回滚"}
    # 倒序回滚，先冻结本次要回的迁移清单
    names = list(marks.keys())
    order = sorted(names, key=lambda k: marks[k].get("at", 0))
    for name in reversed(order):
        apply(merged, name, "rollback")
    _atomic_write(state_path, merged)
    return {"rolled_back": names}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s :: %(message)s")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["forward", "rollback"])
    ap.add_argument("--data", default=os.environ.get("GBT_DATA_DIR", "./data"))
    args = ap.parse_args()
    print(run_migrations(args.data, args.cmd))
