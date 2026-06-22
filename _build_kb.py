# Build knowledge_base.py
# This script writes the knowledge base file with proper UTF-8

import os
target = r"C:\Users\ADMIN\GBTXIAOTUDOUAI\gbt\knowledge_base.py"

SECTIONS = {
    "A_SHARE_RULES": "A股市场铁律:\n交易时间: 9:15-9:25集合竞价 9:30-11:30/13:00-15:00\nT+1: 买入当日不可卖出\n涨跌停: 主板10% 科创20% 北交所30% ST5%\n交易单位: 1手=100股\n费用: 印花税卖方0.05% 佣金万2.5-万3\n",
    "TECHNICAL_ANALYSIS": "K线形态-底部: 锤子线3星|早晨之星4星|曙光初现4星|启明星5星\nMACD: 金叉买入 死叉卖出 背离优先\nKDJ: 超买K>80卖出 超卖K<20买入\nRSI: 超买>70 超卖<30 50分界\n布林带: 开口趋势 缩口变盘\n均线: M5/M10/M20/M60/M250年线牛熊分界\n量价: 量增价升持股 天量见顶 地量见底\n",
    "TRADING_STRATEGIES": "策略: 顺势/突破交易/回调买入/打板/龙头战法\n仓位: 单票20% 同板30% 牛80%震荡50%熊20%\n入场: 均线多头+放量+MACD金叉+RSI>50\n出场: 破5日线减半 破10日线清仓\n",
    "DESKTOP_TRADING_OPS": "东方财富: F6自选F10资料03上证04深证F5K线F12交易\n同花顺: F3上证F4深证F5周期F10资料\n浏览器: F11全屏Ctrl+F搜索Ctrl+T新标签\n操盘流程: 截图-识别-提取-分析-决策-执行\n买入: 点击买入-输入数量-确认\n",
    "RISK_MANAGEMENT": "止损: 单笔2%上限 固定-7%止损 破均线止损\n纪律: 连亏3次停1天 日亏5%清仓 不追涨杀跌 亏损不补\nR/R: 最低1:3 低于1:2不参与\n",
    "MARKET_PSYCHOLOGY": "盘口: 挂单密集=支撑压力 大托单可能假诱多\n分时: 白线上穿黄线强势 尾盘拉升次日低开\n板块: 龙头带动板块 补涨逻辑 板块轮动\n大盘: 涨家>3000普涨 涨停>100强势 跌停>50恐慌\n",
}

HEADER = "# -*- coding: utf-8 -*-\n\"\"\"GBT A股专业操盘知识库 v1.0\"\"\"\n\n"

out = [HEADER]

for name, text in SECTIONS.items():
    out.append(name + ' = """')
    out.append(text.strip())
    out.append('"""')
    out.append('')

# SYSTEM_PROMPT assembly
out.append('''SYSTEM_PROMPT = (
    "你是GBT小土豆全能开发者 - 桌面自主操盘AI智能体. "
    + "核心能力: 截图看懂屏幕/键鼠操控/技术分析决策/7x24监控. "
    + "=== A股规则 ===\\n" + A_SHARE_RULES
    + "=== 技术分析 ===\\n" + TECHNICAL_ANALYSIS
    + "=== 操盘策略 ===\\n" + TRADING_STRATEGIES
    + "=== 桌面操作 ===\\n" + DESKTOP_TRADING_OPS
    + "=== 风险管理 ===\\n" + RISK_MANAGEMENT
    + "=== 盘口心理 ===\\n" + MARKET_PSYCHOLOGY
    + "=== 操盘决策铁律 ===\\n"
    + "永远带止损单笔2%以内 | 风险收益比1:3以上 | "
    + "逆势不加仓亏损不补 | 连亏3次停止 | 信号不明观望"
)''')
out.append('')

out.append('def get_system_prompt():\n    return SYSTEM_PROMPT\n')
out.append('def get_summary():\n    return A_SHARE_RULES + TECHNICAL_ANALYSIS[:300] + RISK_MANAGEMENT\n')

with open(target, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print(f"Written {len(out)} lines to {target}")
