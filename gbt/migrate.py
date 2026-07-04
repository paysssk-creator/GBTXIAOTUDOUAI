# -*- coding: utf-8 -*-
"""
gbt/migrate.py — 数据库迁移引擎 v1.0

强制合规:
  - 每个迁移有对应回滚脚本 (forward/rollback pair)
  - 迁移脚本必须幂等 (IF NOT EXISTS / 安全检查)
  - 执行前自动创建数据备份
  - 版本追踪在迁移版本表中
"""
import os, sys, sqlite3, json, time, shutil, logging
from datetime import datetime
from contextlib import contextmanager

L = logging.getLogger("GBT.Migrate")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
DB_PATH = os.path.join(DB_DIR, "gbt.db")


def _ensure_migration_table(conn: sqlite3.Connection):
    """幂等创建迁移版本表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'ok'
        )
    """)
    conn.commit()


def _get_applied_versions(conn: sqlite3.Connection) -> set:
    """已应用的迁移版本"""
    try:
        rows = conn.execute(
            "SELECT version FROM _migrations WHERE status='ok' ORDER BY version"
        ).fetchall()
        return {r[0] for r in rows}
    except sqlite3.OperationalError:
        _ensure_migration_table(conn)
        return set()


def _backup_db(db_path: str) -> str:
    """创建备份快照"""
    os.makedirs(DB_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(DB_DIR, f"gbt_backup_{ts}.db")
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        L.info(f"备份已创建: {backup_path}")
    return backup_path


@contextmanager
def _get_conn(db_path: str = None):
    """获取独立连接（非线程本地）"""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def run_migration(version: str, db_path: str = None) -> dict:
    """
    执行单个迁移
    - 查找 migrations/{version}_up.sql
    - 执行前备份
    - 记录版本
    """
    path = db_path or DB_PATH
    up_file = os.path.join(MIGRATIONS_DIR, f"{version}_up.sql")
    down_file = os.path.join(MIGRATIONS_DIR, f"{version}_down.sql")

    if not os.path.exists(up_file):
        return {"ok": False, "error": f"迁移文件不存在: {up_file}"}
    if not os.path.exists(down_file):
        return {"ok": False, "error": f"缺少回滚对: {down_file} 不存在"}

    with _get_conn(path) as conn:
        _ensure_migration_table(conn)
        applied = _get_applied_versions(conn)

        if version in applied:
            L.info(f"迁移 {version} 已应用，跳过")
            return {"ok": True, "version": version, "status": "already_applied"}

        # 备份
        backup = _backup_db(path)

        # 执行
        sql = open(up_file, encoding='utf-8').read()
        t0 = time.time()
        try:
            conn.executescript(sql)
            conn.commit()
            elapsed = int((time.time() - t0) * 1000)

            conn.execute(
                "INSERT INTO _migrations (version, applied_at, duration_ms, status) VALUES (?,?,?,?)",
                (version, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), elapsed, "ok")
            )
            conn.commit()

            L.info(f"迁移 {version} 完成 ({elapsed}ms)")
            return {
                "ok": True, "version": version, "status": "applied",
                "duration_ms": elapsed, "backup": backup,
            }
        except Exception as e:
            L.error(f"迁移 {version} 失败: {e}")
            return {"ok": False, "error": str(e)[:200], "backup": backup}


def rollback_migration(version: str, db_path: str = None) -> dict:
    """
    回滚单个迁移
    - 查找 migrations/{version}_down.sql
    - 删除版本记录
    """
    path = db_path or DB_PATH
    down_file = os.path.join(MIGRATIONS_DIR, f"{version}_down.sql")

    if not os.path.exists(down_file):
        return {"ok": False, "error": f"回滚文件不存在: {down_file}"}

    with _get_conn(path) as conn:
        _ensure_migration_table(conn)
        applied = _get_applied_versions(conn)

        if version not in applied:
            return {"ok": True, "version": version, "status": "not_applied"}

        # 备份
        backup = _backup_db(path)

        # 执行回滚
        sql = open(down_file, encoding='utf-8').read()
        t0 = time.time()
        try:
            conn.executescript(sql)
            conn.commit()
            elapsed = int((time.time() - t0) * 1000)

            conn.execute(
                "DELETE FROM _migrations WHERE version=?", (version,)
            )
            conn.commit()

            L.info(f"回滚 {version} 完成 ({elapsed}ms)")
            return {
                "ok": True, "version": version, "status": "rolled_back",
                "duration_ms": elapsed, "backup": backup,
            }
        except Exception as e:
            L.error(f"回滚 {version} 失败: {e}")
            return {"ok": False, "error": str(e)[:200], "backup": backup}


def migrate_all(db_path: str = None) -> dict:
    """
    执行所有待应用迁移 (按版本号排序)
    """
    path = db_path or DB_PATH
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(MIGRATIONS_DIR, exist_ok=True)

    # 扫描迁移文件
    pending = []
    for fname in sorted(os.listdir(MIGRATIONS_DIR)):
        if fname.endswith("_up.sql"):
            ver = fname.replace("_up.sql", "")
            down = os.path.join(MIGRATIONS_DIR, f"{ver}_down.sql")
            if not os.path.exists(down):
                return {"ok": False, "error": f"迁移 {ver} 缺少回滚配对流"}
            pending.append(ver)

    if not pending:
        return {"ok": True, "applied": [], "status": "no_migrations"}

    with _get_conn(path) as conn:
        _ensure_migration_table(conn)
        applied_set = _get_applied_versions(conn)

    results = []
    for ver in pending:
        if ver in applied_set:
            continue
        r = run_migration(ver, path)
        results.append(r)
        if not r["ok"]:
            return {"ok": False, "error": f"迁移 {ver} 失败", "results": results}

    return {"ok": True, "applied": [r["version"] for r in results], "results": results}


def status(db_path: str = None) -> dict:
    """查看迁移状态"""
    path = db_path or DB_PATH
    os.makedirs(MIGRATIONS_DIR, exist_ok=True)

    pending_files = sorted([
        f.replace("_up.sql", "") for f in os.listdir(MIGRATIONS_DIR)
        if f.endswith("_up.sql")
    ])

    if not os.path.exists(path):
        return {"ok": True, "db_exists": False, "pending": pending_files}

    with _get_conn(path) as conn:
        try:
            _ensure_migration_table(conn)
            applied = sorted(_get_applied_versions(conn))
        except Exception as e:
            return {"ok": False, "error": str(e)[:120]}

    return {
        "ok": True,
        "db_exists": True,
        "db_size_mb": round(os.path.getsize(path) / 1024 / 1024, 2),
        "applied": applied,
        "pending": [p for p in pending_files if p not in applied],
        "all": pending_files,
    }


# ═══ CLI ═══
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("action", nargs="?", default="status",
                    choices=["status", "migrate", "rollback"])
    ap.add_argument("--version", "-v", help="版本号或 'last'")
    args = ap.parse_args()

    if args.action == "status":
        s = status()
        print(json.dumps(s, ensure_ascii=False, indent=2))

    elif args.action == "migrate":
        if args.version:
            r = run_migration(args.version)
        else:
            r = migrate_all()
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif args.action == "rollback":
        if not args.version:
            print("需要 --version")
            sys.exit(1)
        if args.version == "last":
            s = status()
            if s.get("applied"):
                args.version = s["applied"][-1]
            else:
                print("无已应用迁移")
                sys.exit(0)
        r = rollback_migration(args.version)
        print(json.dumps(r, ensure_ascii=False, indent=2))
