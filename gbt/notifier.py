"""
notifier.py — 告警通知系统
支持: 控制台/文件日志/Telegram/邮件/微信Server酱
"""
import os, json, time, logging, smtplib
from email.mime.text import MIMEText
from typing import List, Dict, Optional
from dataclasses import dataclass

L = logging.getLogger("gbt.notify")


@dataclass
class Alert:
    level: str  # INFO / WARNING / CRITICAL
    title: str
    body: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")


class Notifier:
    """通知中心 — 多渠道告警"""
    def __init__(self):
        self.channels = []
        self._load_config()

    def _load_config(self):
        env = os.environ
        # Telegram
        if env.get("TG_BOT_TOKEN") and env.get("TG_CHAT_ID"):
            self.channels.append(("telegram", {
                "token": env["TG_BOT_TOKEN"],
                "chat_id": env["TG_CHAT_ID"],
            }))
        # 邮箱
        if env.get("SMTP_HOST"):
            self.channels.append(("email", {
                "host": env.get("SMTP_HOST"),
                "port": int(env.get("SMTP_PORT", 465)),
                "user": env.get("SMTP_USER", ""),
                "password": env.get("SMTP_PASS", ""),
                "to": env.get("ALERT_EMAIL", ""),
            }))
        # 微信Server酱
        if env.get("SC_KEY"):
            self.channels.append(("wechat_sc", {"key": env["SC_KEY"]}))
        # 控制台
        self.channels.append(("console", {}))
        # 文件日志
        self.channels.append(("file", {"path": os.path.join(os.path.dirname(os.path.dirname(__file__)), "alerts.log")}))

    def send(self, alert: Alert):
        """发送告警到所有渠道"""
        for ch_type, cfg in self.channels:
            try:
                if ch_type == "console":
                    prefix = {"CRITICAL": "XXX", "WARNING": "!! ", "INFO": "  > "}.get(alert.level, "  > ")
                    print(f"{prefix}[{alert.timestamp}] {alert.title}: {alert.body[:120]}",
                          flush=True)
                elif ch_type == "telegram":
                    self._send_telegram(cfg, alert)
                elif ch_type == "email":
                    self._send_email(cfg, alert)
                elif ch_type == "wechat_sc":
                    self._send_wechat(cfg, alert)
                elif ch_type == "file":
                    with open(cfg["path"], "a", encoding="utf-8") as f:
                        f.write(f"[{alert.level}] [{alert.timestamp}] {alert.title} | {alert.body}\n")
            except Exception as e:
                L.warning(f"Notify {ch_type} failed: {e}")

    def _send_telegram(self, cfg, alert):
        import requests
        url = f"https://api.telegram.org/bot{cfg['token']}/sendMessage"
        text = f"{'XXX ' if alert.level == 'CRITICAL' else ''}*{alert.title}*\n{alert.body[:500]}"
        requests.post(url, json={"chat_id": cfg["chat_id"], "text": text, "parse_mode": "Markdown"},
                      timeout=10)

    def _send_email(self, cfg, alert):
        msg = MIMEText(alert.body[:2000], "plain", "utf-8")
        msg["Subject"] = f"[GBT-{alert.level}] {alert.title}"
        msg["From"] = cfg["user"]
        msg["To"] = cfg["to"]
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"]) as s:
            s.login(cfg["user"], cfg["password"])
            s.sendmail(cfg["user"], [cfg["to"]], msg.as_string())

    def _send_wechat(self, cfg, alert):
        import requests
        requests.post(f"https://sctapi.ftqq.com/{cfg['key']}.send",
                      json={"title": f"[{alert.level}] {alert.title}", "desp": alert.body[:500]},
                      timeout=10)

    # ── 便捷方法 ──
    def trade_alert(self, side, code, name, price, shares, reasoning=""):
        self.send(Alert("INFO", f"{'买入' if side == 'BUY' else '卖出'}{name}({code})",
                       f"{'买入' if side == 'BUY' else '卖出'}{shares}股 @¥{price} | 理由: {reasoning[:60]}"))

    def stop_alert(self, code, name, pnl_pct, price):
        self.send(Alert("CRITICAL", f"止损触发: {name}({code})",
                       f"盈亏: {pnl_pct:+.1f}% | 价格: ¥{price} | 立即平仓"))

    def profit_alert(self, code, name, pnl_pct, price):
        self.send(Alert("WARNING", f"止盈触发: {name}({code})",
                       f"盈亏: {pnl_pct:+.1f}% | 价格: ¥{price}"))

    def error_alert(self, module, error):
        self.send(Alert("CRITICAL", f"系统错误: {module}", str(error)[:300]))

    def daily_summary(self, pnl, trades, equity):
        self.send(Alert("INFO", f"收盘总结",
                       f"当日盈亏: ¥{pnl:+.2f} | 净值: ¥{equity:,.2f} | 成交: {trades}笔"))


# 全局单例
_notifier = None


def get_notifier() -> Notifier:
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier
