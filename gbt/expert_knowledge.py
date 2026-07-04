# -*- coding: utf-8 -*-
"""
gbt/knowledge.py — GBT 专业知识库 v1.0

两大知识域:
  1. 电脑操控知识   — 系统快捷键, 进程管理, 窗口操控, 网络诊断, 文件管理
  2. A股操盘知识    — 交易规则, 技术指标, 风控参数, 券商操作流程

用途: 为 LLM 决策提供上下文知识和操作指南
"""

import os, json, logging
from typing import Dict, List, Optional

L = logging.getLogger("GBT.Knowledge")

# ═══════════════════════════════════════════════════════
# 电脑操控知识库
# ═══════════════════════════════════════════════════════

COMPUTER_KNOWLEDGE = {
    "shortcuts": {
        "title": "Windows 常用快捷键",
        "items": {
            "复制": "Ctrl+C",
            "粘贴": "Ctrl+V",
            "剪切": "Ctrl+X",
            "撤销": "Ctrl+Z",
            "全选": "Ctrl+A",
            "保存": "Ctrl+S",
            "查找": "Ctrl+F",
            "刷新": "F5 / Ctrl+R",
            "切换窗口": "Alt+Tab",
            "关闭窗口": "Alt+F4",
            "显示桌面": "Win+D",
            "运行": "Win+R",
            "设置": "Win+I",
            "截图": "Win+Shift+S",
            "任务管理器": "Ctrl+Shift+Esc",
            "文件资源管理器": "Win+E",
            "锁屏": "Win+L",
            "投影": "Win+P",
            "通知中心": "Win+A",
            "剪贴板历史": "Win+V",
        },
    },
    "process": {
        "title": "进程与任务管理",
        "commands": [
            {"cmd": "tasklist", "desc": "列出所有进程"},
            {"cmd": "taskkill /F /IM 进程名.exe", "desc": "强制结束进程"},
            {"cmd": "netstat -ano", "desc": "查看网络连接和端口占用"},
            {"cmd": "wmic process list brief", "desc": "进程详细信息"},
            {"cmd": "Get-Process | Sort-Object CPU -Descending", "desc": "按CPU排序 (PowerShell)"},
        ],
        "best_practices": [
            "结束进程前先确认是否为系统关键进程",
            "使用 Ctrl+Shift+Esc 快速打开任务管理器",
            "CPU > 80% 持续 1 分钟是异常信号",
        ],
    },
    "window": {
        "title": "窗口操控指南",
        "methods": [
            {"method": "win+r 输入 app", "desc": "启动应用 (输入 calc/notepad/mstsc)"},
            {"method": "pyautogui.getActiveWindow()", "desc": "获取当前活动窗口"},
            {"method": "pyautogui.click(x,y)", "desc": "点击窗口指定位置"},
            {"method": "win+左右箭头", "desc": "分屏到左/右半屏"},
            {"method": "win+上箭头", "desc": "最大化当前窗口"},
        ],
    },
    "file_ops": {
        "title": "文件操作指南",
        "commands": [
            {"cmd": "dir /s *.py", "desc": "递归搜索 Python 文件"},
            {"cmd": "type 文件.txt", "desc": "查看文件内容"},
            {"cmd": "where 程序名", "desc": "查找程序路径"},
            {"cmd": "tree /F", "desc": "目录树"},
            {"cmd": "Get-ChildItem -Recurse -Filter *.log", "desc": "PowerShell 搜索日志"},
        ],
    },
    "network": {
        "title": "网络诊断知识",
        "checks": [
            {"check": "ping 8.8.8.8", "desc": "测试外网连通性"},
            {"check": "ipconfig /all", "desc": "查看 IP 配置"},
            {"check": "nslookup 域名", "desc": "DNS 解析检查"},
            {"check": "tracert 域名", "desc": "路由追踪"},
            {"check": "curl -I URL", "desc": "HTTP 头检查"},
        ],
    },
    "browser": {
        "title": "浏览器操控",
        "operations": [
            {"op": "os.startfile(URL)", "desc": "Python 打开默认浏览器"},
            {"op": "F11", "desc": "全屏模式"},
            {"op": "Ctrl+T", "desc": "新标签"},
            {"op": "Ctrl+W", "desc": "关闭标签"},
            {"op": "Ctrl+Shift+T", "desc": "恢复关闭的标签"},
            {"op": "F12", "desc": "开发者工具"},
        ],
    },
}


# ═══════════════════════════════════════════════════════
# A股操盘专业知识库
# ═══════════════════════════════════════════════════════

TRADING_KNOWLEDGE = {
    "rules": {
        "title": "A股交易规则",
        "items": {
            "交易时间": "9:30-11:30, 13:00-15:00 (集合竞价: 9:15-9:25)",
            "T+1交割": "当日买入次日方可卖出",
            "涨跌停限制": "主板 ±10%, 科创/创业板 ±20%, ST股 ±5%",
            "最小交易单位": "100股 (1手), 以手为单位递增",
            "交易费用": "佣金万分之2.5 + 印花税千分之1 (卖出) + 过户费万分之0.2",
            "停牌规则": "连续涨停/跌停会触发临时停牌核查",
            "大宗交易门槛": "A股 30万股 或 200万元",
        },
    },
    "indicators": {
        "title": "常用技术指标参数",
        "items": {
            "MA均线": "5日(周线) / 10日(半月) / 20日(月线) / 60日(季线) / 120日(半年) / 250日(年线)",
            "RSI": "14日周期, >70超买 <30超卖",
            "MACD": "12/26/9 默认参数, DIF上穿DEA为金叉, 下穿为死叉",
            "布林带": "20日周期 2倍标准差, 价格触及上轨=超买, 触及下轨=超卖",
            "KDJ": "9/3/3 默认, K>80超买 D<20超卖",
            "成交量": "量价配合: 放量上涨=强势, 缩量上涨=谨慎, 放量下跌=恐慌",
            "OBV能量潮": "量在价先, OBV创新高但价未跟上=顶背离",
        },
    },
    "patterns": {
        "title": "经典K线形态",
        "items": {
            "早晨之星": "下跌末端的反转信号, 长阴+十字星+长阳",
            "黄昏之星": "上涨末端的反转信号, 长阳+十字星+长阴",
            "三只乌鸦": "连续三根阴线, 强烈的下跌信号",
            "红三兵": "连续三根阳线, 强烈的上涨信号",
            "锤子线": "长下影线, 底部反转信号",
            "吊颈线": "长下影线出现在顶部, 见顶信号",
            "吞没形态": "第二根K线完全涵盖第一根, 强烈反转",
            "十字星": "开盘价=收盘价, 变盘信号",
        },
    },
    "risk_mgmt": {
        "title": "风控参数建议",
        "items": {
            "单票最大仓位": "总资金 20%",
            "总仓位上限": "牛市 80%, 震荡 50%, 熊市 30%",
            "止损线": "价格回撤 5-8% 或 破 MA20",
            "止盈线": "盈利 15% 或 破 MA5",
            "最大回撤": "单日净值回撤 > 3% 暂停交易",
            "连续止损": "连续 3 笔止损后暂停当日交易",
            "黑天鹅防护": "五一/国庆/春节长假前减仓至 30%",
        },
    },
    "broker_ops": {
        "title": "券商操作流程",
        "steps": [
            {"phase": "登录", "actions": ["打开券商网站/APP", "输入账号密码/验证码", "确认登录成功"]},
            {"phase": "查行情", "actions": ["输入 6 位股票代码", "查看实时价格和五档盘口", "检查涨跌幅/换手率"]},
            {"phase": "下单", "actions": ["点击买入/卖出", "输入价格(限价单)", "输入数量(手)", "点击确认"]},
            {"phase": "确认", "actions": ["检查委托信息", "确认提交", "查看成交回报"]},
            {"phase": "撤单", "actions": ["查看委托列表", "找到未成交单", "点击撤单", "确认撤单"]},
        ],
    },
    "watch_behavior": {
        "title": "操盘盯盘要点",
        "items": [
            "集合竞价阶段(9:15-9:25)观察量比和竞价方向",
            "开盘前5分钟(9:30-9:35)是最活跃时段，不宜追涨杀跌",
            "10:00 和 14:00 是盘中波动较大的两个时间点",
            "尾盘(14:45-15:00)容易出现主力拉升或打压",
            "龙虎榜和北向资金流向是重要的撑盘/砸盘力量",
            "涨停板封单量: 封单 > 流通市值 1% 说明封板坚决",
        ],
    },
}


# ═══════════════════════════════════════════════════════
# 知识检索引擎
# ═══════════════════════════════════════════════════════

class KnowledgeBase:
    """GBT 专业知识库检索"""

    def __init__(self):
        self._index: Dict[str, any] = {}
        self._build_index()

    def _build_index(self):
        """构建扁平化知识索引"""
        for category, content in COMPUTER_KNOWLEDGE.items():
            self._index[f"电脑:{category}"] = content
        for category, content in TRADING_KNOWLEDGE.items():
            self._index[f"交易:{category}"] = content

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """关键词搜索知识库"""
        query_lower = query.lower()
        results = []

        for key, content in self._index.items():
            score = 0
            # 标题匹配
            title = content.get("title", "")
            if any(kw in title.lower() for kw in query_lower.split()):
                score += 3
            if any(kw in key.lower() for kw in query_lower.split()):
                score += 2

            # 内容匹配
            items = content.get("items", {})
            if isinstance(items, dict):
                for item_key, item_val in items.items():
                    if any(kw in item_key.lower() for kw in query_lower.split()):
                        score += 1
                    if any(kw in str(item_val).lower() for kw in query_lower.split()):
                        score += 1
            elif isinstance(items, list):
                for item in items:
                    item_str = str(item)
                    if any(kw in item_str.lower() for kw in query_lower.split()):
                        score += 1

            if score > 0:
                results.append({"key": key, "content": content, "score": score})

        results.sort(key=lambda r: -r["score"])
        return results[:top_k]

    def get(self, key: str) -> Optional[Dict]:
        """精确获取知识条目"""
        return self._index.get(key)

    def answer(self, question: str) -> str:
        """回答知识问题"""
        results = self.search(question, top_k=3)
        if not results:
            return self._default_answer()

        lines = []
        for r in results:
            content = r["content"]
            title = content.get("title", r["key"])
            lines.append(f"\n📚 {title}:")
            items = content.get("items", {})
            if isinstance(items, dict):
                for k, v in list(items.items())[:5]:
                    lines.append(f"  • {k}: {v}")
            elif isinstance(items, list):
                for item in items[:5]:
                    if isinstance(item, dict):
                        lines.append(f"  • {item.get('name', item.get('phase', item.get('cmd', '')))}: {item.get('desc', item.get('value', ''))}")
                    else:
                        lines.append(f"  • {item}")

        return "\n".join(lines)

    def _default_answer(self) -> str:
        return (
            "\n📚 GBT 知识库覆盖以下领域:\n"
            "  电脑操控: 快捷键/进程管理/窗口操控/文件操作/网络诊断/浏览器操控\n"
            "  A股操盘: 交易规则/技术指标/K线形态/风控参数/券商操作/盯盘要点\n"
            "  请用自然语言提问，例如:\n"
            "  • \"怎么截图？\"\n"
            "  • \"RSI 参数是什么？\"\n"
            "  • \"A股交易时间？\"\n"
            "  • \"怎么结束进程？\""
        )

    def list_topics(self) -> List[str]:
        return list(self._index.keys())

    def context_for_llm(self) -> str:
        """生成 LLM 上下文知识摘要"""
        parts = []
        parts.append("=== GBT 电脑操控知识 ===")
        for k, v in COMPUTER_KNOWLEDGE.items():
            parts.append(f"[{v['title']}]")
            items = v.get("items", {})
            if isinstance(items, dict):
                for ik, iv in list(items.items())[:3]:
                    parts.append(f"  {ik}: {iv}")
        parts.append("\n=== GBT A股操盘知识 ===")
        for k, v in TRADING_KNOWLEDGE.items():
            parts.append(f"[{v['title']}]")
            items = v.get("items", {})
            if isinstance(items, dict):
                for ik, iv in list(items.items())[:3]:
                    parts.append(f"  {ik}: {iv}")
        return "\n".join(parts)


# ── 全局单例 ──
_kb: KnowledgeBase = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


L.info("GBT KnowledgeBase v1.0 已加载: 电脑操控 + A股操盘")
