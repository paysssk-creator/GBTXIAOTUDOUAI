"""
keydb.py - GBT内置密钥数据库, 自动存储/读取免费API密钥
免费: Gemini | Groq | Mistral | Kimi | StepFun | Doubao | Cohere | DeepSeek | Together
"""
import os, sys, base64, sqlite3, time, threading
from typing import Optional, Dict, List, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".gbt_keys.db")

FREE_TIER = {
    "gemini":  {"name":"Google Gemini","env":"GEMINI_API_KEY","url":"https://aistudio.google.com/apikey","free":"每天1500次,视觉免费","pri":1},
    "groq":    {"name":"Groq","env":"GROQ_API_KEY","url":"https://console.groq.com/keys","free":"超高并发,支持llama","pri":2},
    "mistral": {"name":"Mistral AI","env":"MISTRAL_API_KEY","url":"https://console.mistral.ai/api-keys","free":"免费套餐,codestral","pri":3},
    "kimi":    {"name":"Kimi(Moonshot)","env":"MOONSHOT_API_KEY","url":"https://platform.moonshot.cn/console/api-keys","free":"送15元,128K上下文","pri":4},
    "stepfun": {"name":"Step-2(阶跃)","env":"STEPFUN_API_KEY","url":"https://platform.stepfun.com","free":"免费额度","pri":5},
    "doubao":  {"name":"豆包(火山)","env":"DOUBAO_API_KEY","url":"https://console.volcengine.com/ark","free":"免费50万tokens","pri":6},
    "cohere":  {"name":"Cohere","env":"COHERE_API_KEY","url":"https://dashboard.cohere.com/api-keys","free":"试用额度","pri":7},
    "deepseek":{"name":"DeepSeek","env":"DEEPSEEK_API_KEY","url":"https://platform.deepseek.com/api_keys","free":"送500万tokens","pri":8},
    "zhipu":   {"name":"智谱GLM","env":"GLM_API_KEY","url":"https://open.bigmodel.cn/usercenter/apikeys","free":"送2000万tokens","pri":9},
    "together":{"name":"Together AI","env":"TOGETHER_API_KEY","url":"https://api.together.xyz/settings/api-keys","free":"送$5信用额","pri":10},
}

class KeyDB:
    _inst = None
    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
            cls._inst._init()
        return cls._inst
    def _init(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.execute("CREATE TABLE IF NOT EXISTS k(pid TEXT PRIMARY KEY,key TEXT,ts REAL,used REAL,cnt INT DEFAULT 0,free INT DEFAULT 0,note TEXT DEFAULT '')")
        self.conn.commit()
    def _enc(self, s): return base64.b64encode(bytes([b^83 for b in s.encode()])).decode()
    def _dec(self, s): return bytes([b^83 for b in base64.b64decode(s)]).decode()
    def save(self, pid, key, free=False, note=""):
        self.conn.execute("INSERT OR REPLACE INTO k VALUES(?,?,?,?,?,?,?)",(pid,self._enc(key),time.time(),time.time(),0,int(free),note))
        self.conn.commit()
    def get(self, pid):
        info = FREE_TIER.get(pid, {})
        ek = info.get("env","")
        if ek:
            v = os.getenv(ek)
            if v: return v
            for p in [os.path.join(os.path.dirname(DB_PATH),".env")]:
                if os.path.exists(p):
                    try:
                        for l in open(p,"r",encoding="utf-8"):
                            l=l.strip()
                            if l.startswith(f"{ek}="): return l.split("=",1)[1].strip().strip('"').strip("'")
                    except: pass
        r = self.conn.execute("SELECT key FROM k WHERE pid=? ORDER BY used DESC LIMIT 1",(pid,)).fetchone()
        if r:
            try: return self._dec(r[0])
            except: pass
        # cloud fallback
        try:
            from gbt.cloud_kv import CloudKV
            cv = CloudKV()
            if cv.connect():
                v = cv.get(pid)
                if v:
                    self.save(pid, v, free=True, note="cloud")
                    return v
        except: pass
        return None


    def all_info(self):
        rows = self.conn.execute("SELECT pid,ts,used,cnt,free,note FROM k").fetchall()
        res = {}
        for r in rows:
            info = FREE_TIER.get(r[0], {"name": r[0]})
            res[r[0]] = {"name": info.get("name", r[0]), "has_key": True,
                "added": time.strftime("%Y-%m-%d", time.localtime(r[1])),
                "used": time.strftime("%m-%d %H:%M", time.localtime(r[2])),
                "calls": r[3], "free": bool(r[4]), "note": r[5],
                "url": info.get("url", ""), "free_tier": info.get("free", "")}
        return res

    def available(self):
        av = []
        for pid in FREE_TIER:
            k = self.get(pid)
            if k: av.append((pid, FREE_TIER[pid]["name"], True))
        return sorted(av, key=lambda x: FREE_TIER[x[0]]["pri"])

    def mark(self, pid):
        self.conn.execute("UPDATE k SET used=?,cnt=cnt+1 WHERE pid=?", (time.time(), pid))
        self.conn.commit()

    def remove(self, pid):
        self.conn.execute("DELETE FROM k WHERE pid=?", (pid,))
        self.conn.commit()

    def table(self):
        lines = ["Provider       | Key? | Free Tier"]
        lines.append("-" * 52)
        for pid, info in sorted(FREE_TIER.items(), key=lambda x: x[1]["pri"]):
            lines.append(f"{pid:<15}| {'YES' if self.get(pid) else 'NO ':<3} | {info['free'][:30]}")
        return chr(10).join(lines)


def get_keydb(): return KeyDB()

def auto_import():
    db = KeyDB()
    for pid, info in FREE_TIER.items():
        v = os.getenv(info["env"])
        if v and not db.get(pid):
            db.save(pid, v, free=True)
            print(f"  + {pid}")
    return db
