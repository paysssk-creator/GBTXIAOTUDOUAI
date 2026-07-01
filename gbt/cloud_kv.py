"""
cloud_kv.py - 天帝宝库云端密钥存取
CockroachDB双节点: US-West + AP-Southeast
密码通过环境变量 CLOUDKV_DSN_US / CLOUDKV_DSN_AP 注入，不硬编码
"""
import os, time, logging
L = logging.getLogger("GBT.CloudKV")

def _build_nodes():
    """从环境变量构建节点列表，不硬编码密码"""
    nodes = []
    for key in ["CLOUDKV_DSN_US", "CLOUDKV_DSN_AP"]:
        dsn = os.getenv(key, "")
        if dsn:
            node_name = key.replace("CLOUDKV_DSN_", "").replace("_","-")
            nodes.append({"name": f"宝库-{node_name}", "dsn": dsn})
    return nodes

CLOUD_NODES = _build_nodes()

class CloudKV:
    TABLE = "gbt_keys"
    def __init__(self):
        self._conn = None; self._node = None; self._fail_until = 0

    def connect(self, idx=0):
        if time.time() < self._fail_until: return False
        if idx >= len(CLOUD_NODES): self._fail_until = time.time() + 120; return False
        if not CLOUD_NODES:
            L.error("No CloudKV DSN configured — set CLOUDKV_DSN_US and/or CLOUDKV_DSN_AP")
            return False
        cfg = CLOUD_NODES[idx]
        try:
            import psycopg2
            self._conn = psycopg2.connect(cfg["dsn"])
            self._node = cfg["name"]
            L.info(f"connected to {cfg['name']}")
            return True
        except Exception as e:
            L.warning(f"{cfg['name']} failed: {e}")
            return self.connect(idx + 1)

    def _ensure(self):
        if self._conn and not self._conn.closed: return True
        return self.connect()

    def put(self, pid: str, key: str, free: bool, note: str = ""):
        if not self._ensure(): return False
        try:
            cur = self._conn.cursor()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    pid TEXT PRIMARY KEY, key TEXT, free BOOL, note TEXT,
                    updated TIMESTAMPTZ DEFAULT now()
                )""")
            cur.execute(f"UPSERT INTO {self.TABLE} (pid,key,free,note,updated) VALUES (%s,%s,%s,%s,now())",
                       (pid, key, free, note))
            self._conn.commit()
            return True
        except Exception as e:
            L.error(f"put failed: {e}")
            try: self._conn.rollback()
            except Exception: L.debug("rollback skipped")
            return False

    def get(self, pid: str):
        if not self._ensure(): return None
        try:
            cur = self._conn.cursor()
            cur.execute(f"SELECT key FROM {self.TABLE} WHERE pid=%s", (pid,))
            row = cur.fetchone()
            return row[0] if row else None
        except Exception as e:
            L.error(f"get failed: {e}")
            return None

    def sync_from_local(self, local_db):
        """从本地 KeyDB 同步到云端"""
        if not self._ensure(): return False
        rows = local_db.all_info()
        for pid, enc, free, note in rows:
            try: self.put(pid, local_db._dec(enc), bool(free), note or "")
            except Exception as e: L.warning(f"sync {pid} failed: {e}")
        L.info("sync complete")
        return True

    def close(self):
        if self._conn:
            try: self._conn.close()
            except Exception: L.debug("close skipped")
