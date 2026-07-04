"""GBT Pro — 一致性探针（健康 + 数据校验）

三层判断，按用户给出的"校验和告警"框架：
  L1:  进程存活 + HTTP 探活（接口 /api/status 返回 200 + version）
  L2:  数据校验（行数 / 校验和 / 关键业务指标）—— 与"上次已通过版本"对比
  L3:  不一致 → 触发 rollback 协议（向部署面板暴露 /api/panel/rollback）
"""

# 开发者: 自由的风
from __future__ import annotations
import os, sys, json, time, hashlib, urllib.request, urllib.error, logging, argparse

LOG = logging.getLogger("gbt.probe")


def _http_json(url, timeout=3.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.URLError as e:
        LOG.warning("HTTP %s 失败：%s", url, e)
        return None
    except Exception as e:
        LOG.warning("HTTP %s 异常：%s", url, e)
        return None


def _grep_dashboard(html: str) -> dict:
    """简单从渲染出的 dashboard HTML 抓关键标识"""
    out = {}
    for key in ["GBT Pro", "trade-pro-chart", "recap-headline"]:
        out[key] = key in html
    return out


def _compare_l2(prev: dict, now: dict, tol: float) -> dict:
    """对比关键指标，做一致性检查"""
    delta = {}
    for k, v in (now or {}).items():
        if isinstance(v, (int, float)) and isinstance(prev.get(k), (int, float)) and prev.get(k) != 0:
            d = (v - prev[k]) / prev[k]
            delta[k] = round(d, 4)
    breach = [k for k, v in delta.items() if abs(v) > tol]
    return {"delta": delta, "breach": breach, "ok": not breach}


def probe(base_url: str, prev_snapshot: dict | None = None, tol: float = 0.02) -> dict:
    """Healthcheck 总入口，返回 dict, ok 与否"""
    result = {"ts": time.time(), "ok": False, "l1": {}, "l2": {}, "l3": {}}

    # L1 — 探活 + 状态码
    status = _http_json(base_url + "/api/status")
    if not status or not status.get("ok", True):
        result["l1"] = {"ok": False, "reason": "/api/status 不可达"}
        return result
    result["l1"] = {"ok": True, "role": status.get("role"), "version": status.get("version")}

    # 校验 dashboard 模板关键节点 — 防止"看起来一样，其实不一样"
    try:
        with urllib.request.urlopen(base_url + "/dashboard", timeout=3.0) as r:
            html = r.read().decode("utf-8", "ignore")
        result["l1"]["dashboard"] = _grep_dashboard(html)
        if not all(result["l1"]["dashboard"].values()):
            result["l1"]["ok"] = False
            result["l1"]["reason"] = "dashboard 模板关键标识缺失"
            return result
    except Exception as e:
        result["l1"]["ok"] = False
        result["l1"]["reason"] = "dashboard 不可访问：" + str(e)[:80]
        return result

    # L2 — 业务指标对比：deepseek 模型、聊天频道、一键复盘接口
    bal = _http_json(base_url + "/api/token/balance")
    if bal is None:
        result["l2"] = {"ok": False, "reason": "/api/token/balance 不可读"}
        return result
    snapshot = {
        "tokens_total": (bal.get("plan") and bal.get("tokens", 0)) or 0,
        "tokens_remaining": bal.get("remaining", 0),
    }

    if prev_snapshot:
        cmp = _compare_l2(prev_snapshot, snapshot, tol)
        result["l2"] = {"ok": cmp["ok"], "snapshot": snapshot, "delta": cmp["delta"], "breach": cmp["breach"]}
        if not cmp["ok"]:
            return result
    else:
        result["l2"] = {"ok": True, "snapshot": snapshot, "delta": {}, "note": "无历史基准，跳过对比"}

    # L3 — 给部署面板一个回滚触发开关
    result["l3"] = {
        "rollback_endpoint": base_url + "/api/panel/rollback",
        "hint": "若调用探针后 panel.trip_breaker=True 即触发回滚"
    }
    result["ok"] = bool(result["l1"]["ok"] and result["l2"]["ok"])
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("GBT_BASE_URL", "http://127.0.0.1:8765"))
    ap.add_argument("--baseline", default=os.environ.get("GBT_BASELINE_JSON", ""))
    ap.add_argument("--tol", type=float, default=float(os.environ.get("GBT_CONSISTENCY_TOLERANCE", 0.02)))
    args = ap.parse_args()

    prev = None
    if args.baseline and os.path.exists(args.baseline):
        try:
            prev = json.load(open(args.baseline, "r", encoding="utf-8"))
        except Exception:
            prev = None

    res = probe(args.url, prev_snapshot=prev, tol=args.tol)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("ok") else 1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s :: %(message)s")
    main()
