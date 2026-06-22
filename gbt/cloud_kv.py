"""
cloud_kv.py - 天帝宝库云端密钥存取
CockroachDB双节点: US-West + AP-Southeast
"""
import os, time, logging
L = logging.getLogger("GBT.CloudKV")

CLOUD_NODES = [
    {"name": "宝库1-US","dsn": "postgresql://xiaotudou:YxKqxCxppSR3vS47DtiMUg@punchy-tiandi-baoku-25490.j77.aws-us-west-2.cockroachlabs.cloud:26257/defaultdb?sslmode=require"},
    {"name": "宝库2-AP","dsn": "postgresql://xiaotudou:IYz4hP01M7uuFnCdGQP_rw@taut-katydid-26069.j77.aws-ap-southeast-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"},
]

class CloudKV:
    TABLE = "gbt_keys"
    def __init__(self):
        self._conn = None; self._node = None; self._fail_until = 0

    def connect(self, idx=0):
        if time.time() < self._fail_until: return False
        if idx >= len(CLOUD_NODES): self._fail_until = time.time() + 120; return False
        n = CLOUD_NODES[idx]
        try:
            import psycopg2
            self._conn = psycopg2.connect(n["dsn"], connect_timeout=8)
            self._conn.autocommit = True; self._node = n
            cur = self._conn.cursor()
            cur.execute(f"CREATE TABLE IF NOT EXISTS {self.TABLE}(pid TEXT PRIMARY KEY,key TEXT,ts TIMESTAMPTZ DEFAULT now(),cnt INT DEFAULT 0,free BOOL DEFAULT false,note TEXT DEFAULT '')")
            cur.close()
            return True
        except Exception as e:
            L.warning(f"{n['name']}: {e}")
            return self.connect(idx+1)

    def put(self, pid, key, free=False, note=""):
        if not self._conn and not self.connect(): return False
        try:
            cur = self._conn.cursor()
            cur.execute(f"UPSERT INTO {self.TABLE}(pid,key,ts,free,note) VALUES(%s,%s,now(),%s,%s)",(pid,key,free,note))
            cur.close(); print(f"  ☁️ {pid} -> {self._node['name']}"); return True
        except Exception as e:
            L.error(f"put {pid}: {e}"); self._conn = None
            return self.connect() and self.put(pid,key,free,note)

    def get(self, pid):
        if not self._conn and not self.connect(): return None
        try:
            cur = self._conn.cursor()
            cur.execute(f"SELECT key FROM {self.TABLE} WHERE pid=%s",(pid,)); r = cur.fetchone()
            if r: cur.execute(f"UPDATE {self.TABLE} SET cnt=cnt+1,ts=now() WHERE pid=%s",(pid,))
            cur.close(); return r[0] if r else None
        except Exception as e:
            L.error(f"get {pid}: {e}"); self._conn = None
            return self.connect() and self.get(pid)

    def all(self):
        if not self._conn and not self.connect(): return {}
        try:
            cur = self._conn.cursor()
            cur.execute(f"SELECT pid,key,free,note FROM {self.TABLE} ORDER BY ts DESC")
            rows = cur.fetchall(); cur.close()
            return {r[0]:{"key":r[1],"free":r[2],"note":r[3]} for r in rows}
        except: return {}

    def rm(self, pid):
        if not self._conn and not self.connect(): return False
        try:
            cur = self._conn.cursor(); cur.execute(f"DELETE FROM {self.TABLE} WHERE pid=%s",(pid,))
            cur.close(); return True
        except: return False

    def status(self):
        return f"☁️ {self._node['name']}" if self._node else "未连接"


def sync_up():
    """本地→云端"""
    from gbt.keydb import KeyDB
    local, cloud = KeyDB(), CloudKV()
    if not cloud.connect(): return print("❌ 连接失败")
    rows = local.conn.execute("SELECT pid,key,free,note FROM k").fetchall()
    for pid,enc,free,note in rows:
        try: cloud.put(pid, local._dec(enc), bool(free), note or "")
        except: pass
    print("✅ 同步完成")

def sync_down():
    """云端→本地"""
    from gbt.keydb import KeyDB
    cloud, local = CloudKV(), KeyDB()
    if not cloud.connect(): return print("❌ 连接失败")
    for pid,info in cloud.all().items():
        if info["key"] and not local.get(pid):
            local.save(pid, info["key"], info.get("free",False), info.get("note",""))
    print("✅ 下载完成")

def status():
    cloud = CloudKV()
    if cloud.connect():
        print(f"☁️ {cloud._node['name']}"); all_k = cloud.all()
        print(f"   密钥: {len(all_k)}"); [print(f"   {p}") for p in all_k]
    else: print("❌ 云端不可达")
