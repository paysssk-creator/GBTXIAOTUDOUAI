"""
keydb.py - 本地密钥存储 (SQLite)
AES加密存储 + .env自动发现
"""
import os, sqlite3, base64, time
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),".gbt_keys.db")

class KeyDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.execute("CREATE TABLE IF NOT EXISTS k (pid TEXT PRIMARY KEY, key TEXT, free INT, note TEXT, used REAL)")
        self.conn.commit()

    def _enc(self, v):
        """简单混淆 (生产环境请用真正的AES)"""
        return base64.b64encode(v.encode()).decode()

    def _dec(self, v):
        return base64.b64decode(v).decode()

    def get(self, pid):
        """获取密钥: .env > 数据库"""
        ek = pid.upper() + "_API_KEY"
        # 1) 从 .env 发现
        for p in [os.path.join(os.path.dirname(DB_PATH),".env")]:
            if os.path.exists(p):
                try:
                    for l in open(p,"r",encoding="utf-8"):
                        l=l.strip()
                        if l.startswith(f"{ek}="): return l.split("=",1)[1].strip().strip('"').strip("'")
                except Exception: pass  # .env 读取失败时回退到数据库
        r = self.conn.execute("SELECT key FROM k WHERE pid=? ORDER BY used DESC LIMIT 1",(pid,)).fetchone()
        if r:
            try: return self._dec(r[0])
            except Exception: pass  # 解密失败
        return None
    def all_info(self):
        return self.conn.execute("SELECT pid,key,free,note FROM k ORDER BY pid").fetchall()
    def available(self):
        rows = self.conn.execute("SELECT pid,key,free FROM k ORDER BY pid").fetchall()
        return [(pid, pid.upper(), bool(key)) for pid,key,free in rows]
    def put(self, pid, key, free, note=""):
        self.conn.execute("INSERT OR REPLACE INTO k VALUES (?,?,?,?,?)",
                         (pid, self._enc(key), 1 if free else 0, note, time.time()))
        self.conn.commit()
    def delete(self, pid):
        self.conn.execute("DELETE FROM k WHERE pid=?",(pid,))
        self.conn.commit()
    def close(self):
        self.conn.close()
