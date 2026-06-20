"""
mcp.py — 万能MCP接口 (Model Context Protocol)
动态发现→连接→调用任意MCP Server，不受限
支持18个MCP Server + 未来扩展
"""

import os, json, subprocess, time, threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class MCPStatus(Enum):
    OFFLINE="offline"; CONNECTING="connecting"; ONLINE="online"; ERROR="error"


@dataclass
class MCPServer:
    """MCP服务器定义"""
    name: str
    command: str
    args: List[str]
    description: str = ""
    env: Dict[str, str] = field(default_factory=dict)
    status: MCPStatus = MCPStatus.OFFLINE
    last_call: float = 0.0

@dataclass
class MCPResult:
    """MCP调用结果"""
    ok: bool; server: str; method: str
    data: Any = None; error: str = ""; duration: float = 0.0


class UniversalMCP:
    """万能MCP客户端 — 动态调用任意MCP Server"""

    def __init__(self, config_path: Optional[str] = None):
        self.cfg = config_path or os.path.join(
            os.path.expanduser("~"), ".cline", "mcp-config.json")
        self._s: Dict[str, MCPServer] = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.cfg): return
        try:
            with open(self.cfg, "r", encoding="utf-8") as f:
                c = json.load(f)
            wd = os.getcwd()
            for n, cfg in c.get("mcpServers", {}).items():
                args = [a.replace("${workspaceFolder}", wd) for a in cfg.get("args", [])]
                env = {}
                for k, v in cfg.get("env", {}).items():
                    env[k] = os.getenv(v.removeprefix("${").removesuffix("}"), "") if v.startswith("${") and v.endswith("}") else v
                self._s[n] = MCPServer(name=n, command=cfg["command"],
                    args=args, description=cfg.get("description", ""), env=env)
            print(f"🔌 MCP: {len(self._s)}个服务器")
        except Exception as e:
            print(f"❌ MCP加载失败: {e}")

    def list_servers(self) -> List[str]:
        return list(self._s.keys())

    def search(self, kw: str) -> List[str]:
        k = kw.lower()
        return [n for n, s in self._s.items() if k in n.lower() or k in s.description.lower()]

    def describe(self, name: str = "") -> str:
        if name and name in self._s:
            s = self._s[name]
            return f"{s.name}: {s.description}\n  {s.command} {' '.join(s.args[:2])}"
        return "\n".join(f"- **{s.name}**: {s.description}" for s in self._s.values())

    def call(self, server: str, method: str = "",
             args: str = "", timeout: int = 60) -> MCPResult:
        """万能调用 — 任意MCP Server的任意方法"""
        t0 = time.time()
        srv = self._s.get(server)
        if not srv:
            hits = self.search(server)
            hint = f"，相近: {hits}" if hits else ""
            return MCPResult(ok=False, server=server, method=method,
                error=f"未找到'{server}'{hint}。可用:{self.list_servers()}")
        try:
            full = list(srv.args)
            if method: full.append(method)
            if args: full.extend(args.split())
            parts = [srv.command] + full
            cmd = " ".join(f'"{p}"' if " " in p else p for p in parts)
            print(f"🔌 {server} {' '.join(full[:2])}")
            env = os.environ.copy(); env.update(srv.env)
            r = subprocess.run(parts, shell=False, capture_output=True,
                text=True, timeout=timeout, encoding='utf-8', errors='replace',
                cwd=os.path.expanduser("~/.cline"), env=env)
            out = (r.stdout or "").strip() or (r.stderr or "").strip()
            srv.status = MCPStatus.ONLINE; srv.last_call = time.time()
            ok = r.returncode == 0
            return MCPResult(ok=ok, server=server, method=method,
                data=out[:5000] if ok else out[:1000],
                error="" if ok else f"rc={r.returncode}",
                duration=time.time()-t0)
        except subprocess.TimeoutExpired:
            srv.status = MCPStatus.ERROR
            return MCPResult(ok=False, server=server, method=method,
                error="⏱️超时", duration=time.time()-t0)
        except Exception as e:
            srv.status = MCPStatus.ERROR
            return MCPResult(ok=False, server=server, method=method,
                error=str(e), duration=time.time()-t0)

    def call_all(self, method: str = "", args: str = "",
                 servers: Optional[List[str]] = None) -> Dict[str, MCPResult]:
        """批量调用多个MCP服务器"""
        targets = servers or self.list_servers()
        res = {}
        print(f"\n🔌 批量MCP: {len(targets)}个")
        for n in targets:
            res[n] = self.call(n, method, args)
        ok = sum(1 for r in res.values() if r.ok)
        print(f"  📊 {ok}/{len(targets)}成功")
        return res

    def pipeline(self, steps: List[tuple]) -> List[MCPResult]:
        """管道调用: [(server, method, args), ...]"""
        results = []; ctx = ""
        for sn, m, a in steps:
            fa = f"{a} --context \"{ctx[:500]}\"" if ctx else a
            r = self.call(sn, m, fa); results.append(r)
            if r.ok and r.data: ctx = r.data[:1000]
            else: break
        return results

    def health(self) -> Dict[str, str]:
        """健康检查 — 轻量级连通性测试"""
        h = {}
        for n, s in self._s.items():
            scr = s.args[0] if s.args else ""
            if not os.path.exists(scr):
                h[n] = "⚪"
                continue
            try:
                r = subprocess.run(
                    [s.command] + list(s.args[:1]),
                    capture_output=True, text=True, timeout=3,
                    cwd=os.path.expanduser("~/.cline"),
                    env={**os.environ, **s.env})
                h[n] = "🟢" if r.returncode == 0 else "🟡"
            except subprocess.TimeoutExpired:
                h[n] = "🟡"
            except Exception:
                h[n] = "🔴"
        return h

    def refresh(self):
        self._s.clear(); self._load()


_universal: Optional[UniversalMCP] = None

def get_mcp() -> UniversalMCP:
    global _universal
    if _universal is None: _universal = UniversalMCP()
    return _universal

def call_mcp(server: str, method: str = "", args: str = "", timeout: int = 60) -> MCPResult:
    return get_mcp().call(server, method, args, timeout=timeout)


