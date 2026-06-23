"""
GBT 数据库引擎 v1 — SQLite 持久化层
替代内存 deque + JSON，支持账户/交易/信号/会话/策略/日统计全量持久化
"""
import os
import sqlite3
import threading
import logging
import json
from datetime import datetime
from contextlib import contextmanager

L = logging.getLogger("GBT.Database")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "gbt.db")

# ── Schema ──
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT 'default',
    initial_cash REAL NOT NULL DEFAULT 100000,
    cash REAL NOT NULL DEFAULT 100000,
    total_pnl REAL NOT NULL DEFAULT 0,
    daily_pnl REAL NOT NULL DEFAULT 0,
    total_trades INTEGER NOT NULL DEFAULT 0,
    win_trades INTEGER NOT NULL DEFAULT 0,
    loss_trades INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL DEFAULT 1,
    code TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    shares INTEGER NOT NULL DEFAULT 0,
    avg_cost REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, code),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL DEFAULT 1,
    time TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('buy','sell')),
    code TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    shares INTEGER NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    pnl REAL DEFAULT 0,
    cash_after REAL DEFAULT 0,
    commission REAL DEFAULT 0,
    stamp_tax REAL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'filled',
    session_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL CHECK(action IN ('buy','sell','hold')),
    price REAL NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0,
    reason TEXT DEFAULT '',
    strategy TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'init',
    start_time TEXT NOT NULL,
    executed INTEGER NOT NULL DEFAULT 0,
    signal_json TEXT DEFAULT '{}',
    steps_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    total_trades INTEGER NOT NULL DEFAULT 0,
    buy_trades INTEGER NOT NULL DEFAULT 0,
    sell_trades INTEGER NOT NULL DEFAULT 0,
    daily_pnl REAL NOT NULL DEFAULT 0,
    total_pnl REAL NOT NULL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    best_trade REAL DEFAULT 0,
    worst_trade REAL DEFAULT 0,
    sharpe_ratio REAL DEFAULT 0,
    decisions_count INTEGER NOT NULL DEFAULT 0,
    signals_count INTEGER NOT NULL DEFAULT 0,
    risk_blocks INTEGER NOT NULL DEFAULT 0,
    mcp_downtime_seconds INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL DEFAULT '',
    value_type TEXT NOT NULL DEFAULT 'str',
    description TEXT DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL DEFAULT '',
    value_type TEXT NOT NULL DEFAULT 'str',
    description TEXT DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kline_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    scale INTEGER NOT NULL DEFAULT 240,
    day TEXT NOT NULL,
    open REAL NOT NULL DEFAULT 0,
    high REAL NOT NULL DEFAULT 0,
    low REAL NOT NULL DEFAULT 0,
    close REAL NOT NULL DEFAULT 0,
    volume REAL NOT NULL DEFAULT 0,
    amount REAL DEFAULT 0,
    fetched_at TEXT NOT NULL,
    UNIQUE(code, scale, day)
);

CREATE TABLE IF NOT EXISTS blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    reason TEXT DEFAULT '',
    added_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_code ON trades(code);
CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(time);
CREATE INDEX IF NOT EXISTS idx_trades_action ON trades(action);
CREATE INDEX IF NOT EXISTS idx_signals_code ON signals(code);
CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(time);
CREATE INDEX IF NOT EXISTS idx_signals_action ON signals(action);
CREATE INDEX IF NOT EXISTS idx_sessions_code ON sessions(code);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_kline_cache_code_scale ON kline_cache(code, scale);
CREATE INDEX IF NOT EXISTS idx_kline_cache_day ON kline_cache(day);
"""


class Database:
    """SQLite 数据库管理器 — 线程安全"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._local = threading.local()
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        # 确保默认账户存在
        self._ensure_default_account()
        # 加载配置到内存缓存
        self._config_cache = {}
        self._load_configs()
        L.info(f"🗄️ 数据库已初始化: {self.db_path}")

    def _get_conn(self):
        """获取线程本地连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn.execute("PRAGMA busy_timeout=3000")
        return self._local.conn

    @contextmanager
    def conn(self):
        """连接上下文管理器"""
        c = self._get_conn()
        try:
            yield c
        except Exception:
            c.rollback()
            raise

    # ═══════════════════════════════════════════════
    # 账户操作
    # ═══════════════════════════════════════════════
    def _ensure_default_account(self):
        with self.conn() as c:
            r = c.execute("SELECT id FROM accounts WHERE name='default'").fetchone()
            if not r:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute(
                    "INSERT INTO accounts (name, initial_cash, cash, created_at, updated_at) VALUES (?,?,?,?,?)",
                    ("default", 100000, 100000, now, now)
                )
                c.commit()
                L.info("💰 默认账户已创建: ¥100,000")

    def get_account(self, name="default"):
        with self.conn() as c:
            r = c.execute("SELECT * FROM accounts WHERE name=?", (name,)).fetchone()
            return dict(r) if r else None

    def update_account(self, name="default", **kwargs):
        kwargs["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [name]
        with self.conn() as c:
            c.execute(f"UPDATE accounts SET {sets} WHERE name=?", vals)
            c.commit()
        return self.get_account(name)

    def reset_daily_account(self, name="default"):
        with self.conn() as c:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("UPDATE accounts SET daily_pnl=0, daily_trades=0, updated_at=? WHERE name=?", (now, name))
            c.commit()

    # ═══════════════════════════════════════════════
    # 持仓操作
    # ═══════════════════════════════════════════════
    def get_positions(self, account_id=1):
        with self.conn() as c:
            rows = c.execute("SELECT * FROM positions WHERE account_id=? AND shares > 0", (account_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_position(self, code, account_id=1):
        with self.conn() as c:
            r = c.execute("SELECT * FROM positions WHERE account_id=? AND code=?", (account_id, code)).fetchone()
            return dict(r) if r else None

    def upsert_position(self, code, name, shares, avg_cost, account_id=1):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn() as c:
            existing = c.execute(
                "SELECT id, shares, avg_cost FROM positions WHERE account_id=? AND code=?",
                (account_id, code)
            ).fetchone()
            if existing and shares > 0:
                # 加仓：重新计算均价
                total_shares = existing["shares"] + shares
                total_cost = existing["avg_cost"] * existing["shares"] + avg_cost * shares
                new_avg = round(total_cost / max(total_shares, 1), 2)
                c.execute(
                    "UPDATE positions SET name=?, shares=?, avg_cost=?, updated_at=? WHERE id=?",
                    (name, total_shares, new_avg, now, existing["id"])
                )
            elif shares > 0:
                c.execute(
                    "INSERT INTO positions (account_id, code, name, shares, avg_cost, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                    (account_id, code, name, shares, avg_cost, now, now)
                )
            else:
                c.execute("DELETE FROM positions WHERE account_id=? AND code=?", (account_id, code))
            c.commit()

    def delete_position(self, code, account_id=1):
        with self.conn() as c:
            c.execute("DELETE FROM positions WHERE account_id=? AND code=?", (account_id, code))
            c.commit()

    # ═══════════════════════════════════════════════
    # 交易记录
    # ═══════════════════════════════════════════════
    def add_trade(self, time, action, code, name, shares, price, amount,
                  pnl=0, cash_after=0, commission=0, stamp_tax=0,
                  status="filled", session_id=None, account_id=1):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn() as c:
            c.execute(
                """INSERT INTO trades
                (account_id, time, action, code, name, shares, price, amount, pnl, cash_after, commission, stamp_tax, status, session_id, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (account_id, time, action, code, name, shares, price, amount, pnl, cash_after, commission, stamp_tax, status, session_id, now)
            )
            c.commit()
            return c.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_trades(self, limit=100, code=None, action=None, date=None):
        with self.conn() as c:
            sql = "SELECT * FROM trades WHERE 1=1"
            params = []
            if code: sql += " AND code=?"; params.append(code)
            if action: sql += " AND action=?"; params.append(action)
            if date: sql += " AND date(time)=?"; params.append(date)
            sql += " ORDER BY id DESC LIMIT ?"; params.append(limit)
            return [dict(r) for r in c.execute(sql, params).fetchall()]

    def get_trade_stats(self, date=None):
        """某日交易统计"""
        with self.conn() as c:
            if date:
                params = (date,)
                where = "WHERE date(time)=?"
            else:
                params = ()
                where = ""
            return {
                "total": c.execute(f"SELECT COUNT(*) FROM trades {where}", params).fetchone()[0],
                "buys": c.execute(f"SELECT COUNT(*) FROM trades {where} AND action='buy'", params).fetchone()[0],
                "sells": c.execute(f"SELECT COUNT(*) FROM trades {where} AND action='sell'", params).fetchone()[0],
                "total_pnl": c.execute(f"SELECT COALESCE(SUM(pnl),0) FROM trades {where}", params).fetchone()[0],
            }

    # ═══════════════════════════════════════════════
    # 信号记录
    # ═══════════════════════════════════════════════
    def add_signal(self, time, code, name, action, price, confidence, reason="", strategy=""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn() as c:
            c.execute(
                "INSERT INTO signals (time, code, name, action, price, confidence, reason, strategy, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (time, code, name, action, price, confidence, reason, strategy, now)
            )
            c.commit()

    def get_signals(self, limit=100, code=None):
        with self.conn() as c:
            if code:
                rows = c.execute("SELECT * FROM signals WHERE code=? ORDER BY id DESC LIMIT ?", (code, limit)).fetchall()
            else:
                rows = c.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_signals_count(self, date=None):
        with self.conn() as c:
            if date:
                return c.execute("SELECT COUNT(*) FROM signals WHERE date(created_at)=?", (date,)).fetchone()[0]
            return c.execute("SELECT COUNT(*) FROM signals").fetchone()[0]

    # ═══════════════════════════════════════════════
    # 会话记录
    # ═══════════════════════════════════════════════
    def save_session(self, session_id, code, name, status, start_time, executed=False, signal=None, steps=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        signal_json = json.dumps(signal, ensure_ascii=False) if signal else "{}"
        steps_json = json.dumps(steps, ensure_ascii=False) if steps else "[]"
        with self.conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO sessions (session_id, code, name, status, start_time, executed, signal_json, steps_json, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (session_id, code, name, status, start_time, 1 if executed else 0, signal_json, steps_json, now)
            )
            c.commit()

    def get_sessions(self, limit=20, status=None):
        with self.conn() as c:
            if status:
                rows = c.execute("SELECT * FROM sessions WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)).fetchall()
            else:
                rows = c.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                try: d["signal"] = json.loads(d.pop("signal_json", "{}"))
                except: d["signal"] = {}
                try: d["steps"] = json.loads(d.pop("steps_json", "[]"))
                except: d["steps"] = []
                result.append(d)
            return result

    # ═══════════════════════════════════════════════
    # 日统计
    # ═══════════════════════════════════════════════
    def save_daily_stats(self, date, **kwargs):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn() as c:
            existing = c.execute("SELECT id FROM daily_stats WHERE date=?", (date,)).fetchone()
            if existing:
                sets = ", ".join(f"{k}=?" for k in kwargs)
                vals = list(kwargs.values()) + [now, date]
                c.execute(f"UPDATE daily_stats SET {sets}, created_at=? WHERE date=?", vals)
            else:
                kwargs["date"] = date
                kwargs["created_at"] = now
                cols = ", ".join(kwargs.keys())
                placeholders = ", ".join("?" * len(kwargs))
                c.execute(f"INSERT INTO daily_stats ({cols}) VALUES ({placeholders})", list(kwargs.values()))
            c.commit()

    def get_daily_stats(self, date=None, limit=30):
        with self.conn() as c:
            if date:
                r = c.execute("SELECT * FROM daily_stats WHERE date=?", (date,)).fetchone()
                return dict(r) if r else None
            rows = c.execute("SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════
    # 策略配置持久化
    # ═══════════════════════════════════════════════
    def _load_configs(self):
        """启动时加载配置缓存"""
        with self.conn() as c:
            for table in ("strategy_config", "risk_config"):
                rows = c.execute("SELECT key, value, value_type FROM " + table).fetchall()
                for r in rows:
                    prefix = "strategy." if table == "strategy_config" else "risk."
                    self._config_cache[prefix + r["key"]] = self._parse_value(r["value"], r["value_type"])

    def _parse_value(self, value, vtype):
        if vtype == "int": return int(value)
        if vtype == "float": return float(value)
        if vtype == "bool": return value.lower() in ("true", "1", "yes")
        if vtype == "json": return json.loads(value)
        return str(value)

    def get_config(self, key, default=None, table="strategy_config"):
        cache_key = f"{'strategy' if table=='strategy_config' else 'risk'}.{key}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        with self.conn() as c:
            r = c.execute(f"SELECT value, value_type FROM {table} WHERE key=?", (key,)).fetchone()
            if r:
                val = self._parse_value(r["value"], r["value_type"])
                with self._lock:
                    self._config_cache[cache_key] = val
                return val
        return default

    def set_config(self, key, value, table="strategy_config", description=""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, bool): vtype, sval = "bool", str(value).lower()
        elif isinstance(value, int): vtype, sval = "int", str(value)
        elif isinstance(value, float): vtype, sval = "float", str(value)
        elif isinstance(value, (list, dict)): vtype, sval = "json", json.dumps(value, ensure_ascii=False)
        else: vtype, sval = "str", str(value)

        with self.conn() as c:
            c.execute(
                f"""INSERT INTO {table} (key, value, value_type, description, updated_at)
                VALUES (?,?,?,?,?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, value_type=excluded.value_type, description=excluded.description, updated_at=excluded.updated_at""",
                (key, sval, vtype, description, now)
            )
            c.commit()
        cache_key = f"{'strategy' if table=='strategy_config' else 'risk'}.{key}"
        with self._lock:
            self._config_cache[cache_key] = value

    def get_all_configs(self, table="strategy_config"):
        with self.conn() as c:
            rows = c.execute(f"SELECT * FROM {table} ORDER BY key").fetchall()
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════
    # K线缓存
    # ═══════════════════════════════════════════════
    def cache_klines(self, code, scale, klines):
        """批量缓存K线 [{'day':..., 'open':..., 'high':..., 'low':..., 'close':..., 'volume':..., 'amount':...}]"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn() as c:
            for k in klines:
                c.execute(
                    """INSERT OR REPLACE INTO kline_cache (code, scale, day, open, high, low, close, volume, amount, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (code, scale, k["day"],
                     float(k.get("open", 0)), float(k.get("high", 0)),
                     float(k.get("low", 0)), float(k.get("close", 0)),
                     float(k.get("volume", 0)), float(k.get("amount", 0)) if k.get("amount") else 0,
                     now)
                )
            c.commit()

    def get_klines(self, code, scale=240, limit=200, order="ASC"):
        with self.conn() as c:
            rows = c.execute(
                f"SELECT * FROM kline_cache WHERE code=? AND scale=? ORDER BY day {order} LIMIT ?",
                (code, scale, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_kline_arrays(self, code, scale=240, limit=200):
        """返回 [closes, highs, lows, volumes] 数组格式"""
        klines = self.get_klines(code, scale, limit, order="ASC")
        return {
            "ok": True, "code": code, "count": len(klines),
            "closes": [k["close"] for k in klines],
            "highs": [k["high"] for k in klines],
            "lows": [k["low"] for k in klines],
            "volumes": [k["volume"] for k in klines],
            "raw": [{"day": k["day"], "open": k["open"], "close": k["close"],
                     "high": k["high"], "low": k["low"], "volume": k["volume"]} for k in klines]
        }

    def kline_needs_refresh(self, code, scale=240):
        """检查是否需要刷新：最后一条K线日期 vs 今日"""
        today = datetime.now().strftime("%Y-%m-%d")
        with self.conn() as c:
            r = c.execute(
                "SELECT day FROM kline_cache WHERE code=? AND scale=? ORDER BY day DESC LIMIT 1",
                (code, scale)
            ).fetchone()
            if not r: return True  # 无缓存
            return r["day"] < today  # 需要更新到今天

    # ═══════════════════════════════════════════════
    # 黑名单
    # ═══════════════════════════════════════════════
    def add_blacklist(self, code, name="", reason="", duration_days=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expires = None
        if duration_days:
            from datetime import timedelta
            expires = (datetime.now() + timedelta(days=duration_days)).strftime("%Y-%m-%d %H:%M:%S")
        with self.conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO blacklist (code, name, reason, added_at, expires_at) VALUES (?,?,?,?,?)",
                (code, name, reason, now, expires)
            )
            c.commit()

    def is_blacklisted(self, code):
        with self.conn() as c:
            r = c.execute(
                "SELECT id FROM blacklist WHERE code=? AND (expires_at IS NULL OR expires_at > datetime('now','localtime'))",
                (code,)
            ).fetchone()
            return r is not None

    def remove_blacklist(self, code):
        with self.conn() as c:
            c.execute("DELETE FROM blacklist WHERE code=?", (code,))
            c.commit()

    def get_blacklist(self):
        with self.conn() as c:
            rows = c.execute("SELECT * FROM blacklist ORDER BY added_at DESC").fetchall()
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════
    # 迁移工具 — 从内存 deque/JSON 迁入 SQLite
    # ═══════════════════════════════════════════════
    def migrate_account(self, acct):
        """从内存 Account 对象迁入"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn() as c:
            c.execute(
                """UPDATE accounts SET cash=?, initial_cash=?, total_pnl=?, daily_pnl=?,
                total_trades=?, win_trades=?, loss_trades=?, updated_at=?
                WHERE name='default'""",
                (acct.cash, acct.initial_cash, acct.total_pnl, acct.daily_pnl,
                 acct.total_trades, acct.win_trades, acct.loss_trades, now)
            )
            c.commit()

        # 迁入持仓
        for code, pos in acct.positions.items():
            self.upsert_position(code, pos.get("name", code), pos["shares"], pos["avg_cost"])

        # 迁入交易日志
        for entry in reversed(list(acct.trade_log)):
            self.add_trade(
                time=entry.get("time", now),
                action=entry.get("action", "buy"),
                code=entry.get("code", ""),
                name=entry.get("name", ""),
                shares=entry.get("shares", 0),
                price=entry.get("price", 0),
                amount=entry.get("amount", 0),
                pnl=entry.get("pnl", 0),
                cash_after=entry.get("cash_after", 0),
            )
        L.info(f"📦 账户迁入完成: ¥{acct.cash:.0f} + {len(acct.positions)}持仓 + {len(acct.trade_log)}笔交易")

    def migrate_trader(self, trader):
        """从内存 Trader 对象迁入"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 迁入信号
        for sig in reversed(list(trader.signals)):
            self.add_signal(
                time=getattr(sig, 'time', now),
                code=getattr(sig, 'code', ''),
                name=getattr(sig, 'name', ''),
                action=getattr(sig, 'action', 'hold'),
                price=getattr(sig, 'price', 0),
                confidence=getattr(sig, 'confidence', 0),
                reason=getattr(sig, 'reason', ''),
                strategy=getattr(sig, 'strategy', ''),
            )

        # 迁入会话
        for sess in reversed(list(trader.sessions)):
            d = sess.to_dict() if hasattr(sess, 'to_dict') else sess
            self.save_session(
                session_id=d.get("id", ""),
                code=d.get("code", ""),
                name=d.get("name", ""),
                status=d.get("status", "init"),
                start_time=d.get("start_time", now),
                executed=d.get("executed", False),
                signal={"action": d.get("signal", {}).get("action", "")} if d.get("signal") else None,
                steps=d.get("steps", [])
            )

        # 迁入交易日志
        for entry in reversed(list(trader.trade_log)):
            self.add_trade(
                time=entry.get("time", now),
                action=entry.get("action", "buy"),
                code=entry.get("code", ""),
                name=entry.get("name", ""),
                shares=entry.get("shares", 0),
                price=entry.get("price", 0),
                amount=entry.get("amount", 0),
                status=entry.get("status", "filled"),
            )

        # 保存策略配置
        configs = {
            "auto_trade": trader.auto_trade,
            "confidence_threshold": trader.confidence_threshold,
            "scan_interval": trader.scan_interval,
            "max_position_pct": trader.max_position_pct,
        }
        for k, v in configs.items():
            self.set_config(k, v, "strategy_config", f"Trader.{k}")

        L.info(f"📦 交易引擎迁入完成: {len(trader.signals)}信号 + {len(trader.sessions)}会话")

    def migrate_risk(self, risk_mgr):
        """迁入风控配置"""
        configs = {
            "total_capital": risk_mgr.total_capital,
            "max_single_pct": risk_mgr.max_single_pct,
            "max_total_pct": risk_mgr.max_total_pct,
            "stop_loss_pct": risk_mgr.stop_loss_pct,
            "stop_profit_pct": risk_mgr.stop_profit_pct,
            "trailing_stop_pct": risk_mgr.trailing_stop_pct,
            "max_daily_trades": risk_mgr.max_daily_trades,
            "max_daily_loss_pct": risk_mgr.max_daily_loss_pct,
        }
        for k, v in configs.items():
            self.set_config(k, v, "risk_config", f"RiskManager.{k}")
        L.info(f"📦 风控配置迁入完成: {len(configs)}项")

    # ═══════════════════════════════════════════════
    # 数据库统计
    # ═══════════════════════════════════════════════
    def get_db_stats(self):
        with self.conn() as c:
            tables = ["accounts", "positions", "trades", "signals", "sessions", "daily_stats", "kline_cache", "blacklist"]
            stats = {}
            for t in tables:
                count = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                stats[t] = count
            stats["db_size_mb"] = round(os.path.getsize(self.db_path) / 1024 / 1024, 2) if os.path.exists(self.db_path) else 0
            return stats

    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ── 全局数据库实例 ──
db = Database()