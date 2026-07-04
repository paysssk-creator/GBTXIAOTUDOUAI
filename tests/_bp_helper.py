"""tests/_bp_helper.py · T-003 蓝图测试公共助手
──────────────────────────────────────────────
所有 test_api_*.py 都通过这个模块访问运行中的桌面主实例。
默认地址：http://127.0.0.1:8765  （由 GBT_MAIN_URL 环境变量覆盖）
"""
import os
import json
import time
import urllib.request
import urllib.error

BASE = os.environ.get("GBT_MAIN_URL", "http://127.0.0.1:8765")
TIMEOUT = int(os.environ.get("GBT_TEST_TIMEOUT", "10"))


def get(path, timeout=None):
    """GET 请求，返回 (status, body_bytes)"""
    url = BASE + path
    t = timeout or TIMEOUT
    try:
        r = urllib.request.urlopen(url, timeout=t)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.fp else b""
    except Exception as e:
        return 0, str(e).encode("utf-8")


def post(path, body, timeout=None):
    """POST JSON 请求，返回 (status, body_bytes)"""
    url = BASE + path
    t = timeout or TIMEOUT
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=t)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.fp else b""
    except Exception as e:
        return 0, str(e).encode("utf-8")


def must_status(path, expected, timeout=None):
    """断言 GET 返回的状态码"""
    code, _ = get(path, timeout=timeout)
    assert code == expected, f"{path}: status {code} != expected {expected}"
    return code


def must_field(path, field, timeout=None):
    """断言 GET 返回 JSON 含 field 字段"""
    code, body = get(path, timeout=timeout)
    assert code == 200, f"{path}: status {code}, body={body[:100]!r}"
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert field in j, f"{path}: 响应 JSON 缺少字段 {field}，实际 {list(j.keys())[:8]}"
    return j


def soft_status(path, allowed=(200, 204), timeout=None):
    """软断言：允许 200/204/401 等合理响应（用于认证端点）"""
    code, _ = get(path, timeout=timeout)
    assert code in allowed, f"{path}: status {code} not in {allowed}"
    return code


def is_main_alive():
    """主实例可用性预检（pytest 启动时调用）"""
    code, _ = get("/api/status")
    return code == 200