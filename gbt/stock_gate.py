# -*- coding: utf-8 -*-
"""
gbt/stock_gate.py — A股券商入口逻辑

调用者发起操作 → 先弹出券商列表让用户选 → 再打开对应平台
"""
import webbrowser, logging

L = logging.getLogger("GBT.StockGate")

# ── 券商平台注册表 ──
BROKERS = {
    "东方财富": {
        "url": "https://trade.eastmoney.com",
        "type": "web",
        "desc": "东方财富网 — 免费行情 + 模拟交易",
        "keywords": ["东方财富", "eastmoney", "东财"],
        "ui_profile": {
            "window_keywords": ["东方财富", "东财", "财富终端", "炒股"],
            "login_keywords": ["持仓", "我的资产", "可用资金", "买入", "卖出", "委托", "成交", "资金股份"],
            "anchor_keywords": {
                "stock_code": ["证券代码", "股票代码", "代码", "证券"],
                "price": ["委托价格", "买入价格", "卖出价格", "价格", "委托价"],
                "lots": ["委托数量", "买入数量", "卖出数量", "数量", "股数"],
                "buy_btn": ["买入", "立即买入"],
                "sell_btn": ["卖出", "立即卖出"],
                "confirm_btn": ["确认", "确定", "提交", "下单", "委托"],
            },
            "panel_keywords": {
                "entrust": ["委托", "今日委托", "当前委托", "当日委托", "委托查询", "申报", "撤单"],
                "position": ["持仓", "我的持仓", "持仓查询", "资金股份", "股票市值", "可用股份", "持股"],
            },
        },
    },
    "同花顺": {
        "url": "https://www.10jqka.com.cn",
        "type": "web",
        "desc": "同花顺 — 国内最大行情软件",
        "keywords": ["同花顺", "10jqka", "ths"],
        "ui_profile": {
            "window_keywords": ["同花顺", "10jqka", "网上股票交易系统", "委托下单", "GBT全能小土豆CC", "GBT全能小土豆"],
            "login_keywords": ["我的资产", "可用", "资金余额", "买入", "卖出", "撤单", "委托查询", "成交查询"],
            "anchor_keywords": {
                "stock_code": ["证券代码", "股票代码", "代码"],
                "price": ["委托价", "买入价", "卖出价", "价格"],
                "lots": ["委托数量", "数量", "股数"],
                "buy_btn": ["买入", "买入[B]"],
                "sell_btn": ["卖出", "卖出[S]"],
                "confirm_btn": ["确认", "确定", "提交"],
            },
            "panel_keywords": {
                "entrust": ["今日委托", "当前委托", "委托查询", "撤单", "申报编号"],
                "position": ["持仓", "持仓查询", "股份余额", "可卖数量", "参考盈亏"],
            },
        },
    },
    "雪球": {
        "url": "https://xueqiu.com",
        "type": "web",
        "desc": "雪球 — 社交化投资平台",
        "keywords": ["雪球", "xueqiu"],
    },
    "腾讯自选股": {
        "url": "https://gu.qq.com",
        "type": "web",
        "desc": "腾讯自选股 — 腾讯系免费行情",
        "keywords": ["腾讯", "自选股", "qq股票", "腾讯股票"],
    },
    "新浪财经": {
        "url": "https://finance.sina.com.cn/stock",
        "type": "web",
        "desc": "新浪财经 — A股实时行情",
        "keywords": ["新浪", "sina", "新浪财经"],
    },
    "通达信": {
        "url": "https://pc.tdx.com.cn",
        "type": "web",
        "desc": "通达信 — 专业交易终端 (需客户端)",
        "keywords": ["通达信", "tdx"],
        "ui_profile": {
            "window_keywords": ["通达信", "网上交易", "通达信金融终端"],
            "login_keywords": ["资金股份", "委托", "成交", "持仓", "买入", "卖出"],
            "anchor_keywords": {
                "stock_code": ["证券代码", "代码"],
                "price": ["委托价格", "价格", "买入价格", "卖出价格"],
                "lots": ["委托数量", "数量", "股数"],
                "buy_btn": ["买入", "买入委托"],
                "sell_btn": ["卖出", "卖出委托"],
                "confirm_btn": ["确认", "提交", "委托"],
            },
            "panel_keywords": {
                "entrust": ["委托查询", "今日委托", "当前委托", "申报"],
                "position": ["持仓查询", "股票余额", "可用余额", "参考盈亏"],
            },
        },
    },
    "大智慧": {
        "url": "https://www.gw.com.cn",
        "type": "web",
        "desc": "大智慧 — 老牌股票软件",
        "keywords": ["大智慧", "dzh"],
    },
    "中信证券": {
        "url": "https://www.cs.ecitic.com",
        "type": "web",
        "desc": "中信证券 — 头部券商 (需账户)",
        "keywords": ["中信", "中信证券", "citic"],
        "ui_profile": {
            "window_keywords": ["中信证券", "信e投", "中信建投", "交易客户端"],
            "login_keywords": ["资产总值", "总资产", "可用资金", "买入", "卖出", "委托", "成交", "持仓"],
            "anchor_keywords": {
                "stock_code": ["证券代码", "股票代码", "代码"],
                "price": ["委托价格", "价格", "委托价"],
                "lots": ["委托数量", "数量", "股数"],
                "buy_btn": ["买入", "普通买入"],
                "sell_btn": ["卖出", "普通卖出"],
                "confirm_btn": ["确认", "确定", "提交", "下单"],
            },
            "panel_keywords": {
                "entrust": ["委托", "当日委托", "当前委托", "撤单"],
                "position": ["持仓", "我的持仓", "股票市值", "可卖数量", "参考市值"],
            },
        },
    },
}


def list_brokers() -> str:
    """列出所有可选券商平台 (格式化)"""
    lines = ["📊 请选择券商/行情平台:"]
    for i, (name, info) in enumerate(BROKERS.items(), 1):
        lines.append(f"  {i}. {name} — {info['desc']}")
    lines.append(f"\n  输入平台名称或序号即可 (例如: 东方财富 或 1)")
    return "\n".join(lines)


def find_broker(keyword: str) -> dict | None:
    """根据关键词找到匹配的券商"""
    kw = keyword.strip().lower()
    
    # 按序号匹配
    for i, (name, info) in enumerate(BROKERS.items(), 1):
        if kw == str(i):
            return {"name": name, **info}
    
    # 按名称/别名匹配
    for name, info in BROKERS.items():
        if kw == name.lower() or kw in [k.lower() for k in info.get("keywords", [])]:
            return {"name": name, **info}
    
    # 模糊匹配
    for name, info in BROKERS.items():
        if kw in name.lower():
            return {"name": name, **info}
    
    # 默认: 东方财富
    return {"name": "东方财富", **BROKERS["东方财富"]}


def open_broker(keyword: str = "") -> dict:
    """
    打开券商平台
    如果 keyword 为空 → 返回列表让用户选
    如果 keyword 有值 → 直接打开
    """
    if not keyword or keyword.strip() == "":
        return {"ok": True, "need_choice": True, "list": list_brokers()}
    
    broker = find_broker(keyword)
    if not broker:
        return {"ok": False, "error": f"未找到券商: {keyword}", "list": list_brokers()}
    
    url = broker["url"]
    name = broker["name"]
    
    try:
        webbrowser.open(url)
        L.info(f"已打开券商: {name} → {url}")
        return {
            "ok": True,
            "name": name,
            "url": url,
            "desc": broker["desc"],
            "message": f"已在浏览器打开 {name} ({broker['desc']})",
        }
    except Exception as e:
        return {"ok": False, "error": f"打开失败: {e}"}


def get_login_url(broker_name: str = "东方财富") -> str:
    """获取特定券商的登录URL"""
    broker = find_broker(broker_name)
    if not broker:
        return ""
    url = broker["url"]
    # 部分平台有专门的登录页
    name = broker["name"]
    if name == "东方财富":
        url = "https://trade.eastmoney.com"
    elif name == "同花顺":
        url = "https://upass.10jqka.com.cn/login"
    elif name == "雪球":
        url = "https://xueqiu.com"
    return url


def get_broker_ui_profile(broker_name: str = "") -> dict:
    broker = find_broker(broker_name or "东方财富")
    if not broker:
        broker = {"name": "东方财富", **BROKERS["东方财富"]}
    profile = dict((broker.get("ui_profile") or {}))
    profile["name"] = broker.get("name")
    profile["keywords"] = list(broker.get("keywords") or [])
    return profile
