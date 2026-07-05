"""
CodeWhale 上下文管家 v3 — 省费引擎
核心原则：能用 SQLite 查的不用 LLM，能本地摘要的不用云端大模型

省费策略：
  1. 查历史 → 纯 SQL 搜（免费），不走 LLM（$$/token）
  2. 存关键 → 一次写入，永不再重复推理
  3. 上下文接力 → 新会话自动注入历史摘要，省去重新读取文件
  4. 本地压缩 → 旧对话用 qwen2.5-coder:7b 折叠（免费），不占云端窗口
"""
import sys, json, re, sqlite3, time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gbt.context_engine import (
    ContextManager, ContextConfig, TapeDatabase, LocalCurator,
    estimate_tokens,
)

DB_PATH = str(ROOT / "data" / "context_tape.db")
SESSION_ID = "codewhale_main"

_ctx: ContextManager | None = None
_saved_tokens: int = 0   # 累计节省的 token 数
_query_count: int = 0    # 查询次数


def _get_ctx() -> ContextManager:
    global _ctx
    if _ctx is None:
        config = ContextConfig(
            small_model_name="qwen2.5-coder:7b",
            db_path=DB_PATH,
            max_active_tokens=16000,
        )
        curator = LocalCurator(
            model_name="qwen2.5-coder:7b",
            base_url="http://localhost:11434/v1",
            temperature=0.3,
            timeout=30,
        )
        db = TapeDatabase(config.db_path)
        _ctx = ContextManager(
            config=config,
            curator=curator,
            database=db,
            auto_curator=False,
        )
        if not _ctx.resume_session(SESSION_ID):
            _ctx.start_session(SESSION_ID, "CodeWhale")
    return _ctx


# ── 纯 SQL 搜索（免费，不走 LLM）─────────────────────────

def _sql_search(query: str, limit: int = 8) -> list[dict]:
    ctx = _get_ctx()
    sid = ctx.session_id or SESSION_ID
    conn = ctx._db._get_conn()

    qwords = re.findall(r'[\u4e00-\u9fff]{2,5}', query)
    if not qwords:
        qwords = [query]

    results = []

    # 搜事实（权重最高，结构化数据最可靠）
    facts = conn.execute(
        "SELECT fact_key, fact_value, category FROM context_facts WHERE session_id=?",
        (sid,)
    ).fetchall()
    for row in facts:
        combined = f"{row['fact_key']} {row['fact_value']} {row['category']}".lower()
        if any(qw.lower() in combined for qw in qwords):
            results.append({
                "source": "fact",
                "role": row['category'],
                "content": f"{row['fact_key']}: {row['fact_value']}",
                "_score": 10,  # 事实权重最高
            })

    # 搜原文段（活跃窗口，最新上下文）
    segments = conn.execute(
        "SELECT role, content, seq FROM tape_segments WHERE session_id=? AND is_folded=0 ORDER BY seq DESC LIMIT 300",
        (sid,)
    ).fetchall()
    for row in segments:
        content_lower = row['content'].lower()
        matched = sum(1 for qw in qwords if qw.lower() in content_lower)
        if matched > 0:
            preview = row['content'][:250].replace('\n', ' ')
            if len(row['content']) > 250:
                preview += "..."
            results.append({
                "source": "segment",
                "role": row['role'],
                "content": preview,
                "_score": matched * 5,
            })

    # 搜折叠摘要（历史精华）
    folds = conn.execute(
        "SELECT summary, keywords FROM tape_folds WHERE session_id=? ORDER BY id DESC LIMIT 20",
        (sid,)
    ).fetchall()
    for row in folds:
        combined = f"{row['summary']} {row['keywords']}".lower()
        matched = sum(1 for qw in qwords if qw.lower() in combined)
        if matched > 0:
            results.append({
                "source": "fold",
                "role": "summary",
                "content": row['summary'][:250],
                "_score": matched * 3,
            })

    results.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return results[:limit]


def search(query: str) -> str:
    """
    搜索历史上下文（纯 SQL，免费）
    返回匹配结果，统计节省的 token 估算
    """
    global _query_count, _saved_tokens
    _query_count += 1

    matches = _sql_search(query)

    if not matches:
        return f"[管家] 未找到与 '{query}' 相关的历史上下文"

    # 估算节省的 token：如果不走管家，就需要重读文件/重推理
    estimated_read_tokens = 2000  # 假设每次不用管家就要读 2000 token 的文件
    _saved_tokens += estimated_read_tokens

    lines = [f"[管家] 找到 {len(matches)} 条匹配 (已累计节省 ~{_saved_tokens}tokens):"]
    for i, m in enumerate(matches, 1):
        lines.append(f"  {i}. [{m['source']}] {m['content'][:200]}")
    return "\n".join(lines)


# ── 核心操作 ────────────────────────────────────────────

def save(role: str, content: str):
    """保存一段上下文到数据库（几乎免费，仅 SQLite 写入开销）"""
    _get_ctx().append(content, role=role)


def remember(key: str, value: str):
    """记录一个结构化事实 — 后续检索命中率最高，省费效果最好"""
    ctx = _get_ctx()
    ctx._db.upsert_fact(ctx.session_id or SESSION_ID, key, value)


def facts() -> list[dict]:
    """列出所有结构化事实"""
    ctx = _get_ctx()
    return ctx._db.get_facts(ctx.session_id or SESSION_ID)


def stats() -> dict:
    s = _get_ctx().tape_stats()
    s["butler_queries"] = _query_count
    s["butler_tokens_saved"] = _saved_tokens
    return s


# ── 🆕 省费关键能力 ─────────────────────────────────────

def archive_turn(summary: str, decisions: list[str] | None = None,
                 discoveries: list[str] | None = None):
    """
    归档当前轮对话 — 一次写入，永不再重复推理
    save free SQLite writes instead of cloud LLM re-inference

    用法（每轮对话结束时调用）:
        archive_turn(
            "讨论了策略回测架构，决定用策略+工厂模式",
            decisions=["架构：策略+工厂模式"],
            discoveries=["gbt/strategies.py 有 4 种策略基类"]
        )
    """
    save("summary", summary)
    for d in (decisions or []):
        save("decision", d)
    for d in (discoveries or []):
        save("discovery", d)
    return f"[管家] 已归档: {1 + len(decisions or []) + len(discoveries or [])} 条"


def load_context(hints: list[str] | None = None) -> str:
    """
    会话开始时调用 — 自动搜索相关历史，生成上下文摘要注入到新对话
    省去 LLM 重读项目文件、重推理的开销

    用法:
        load_context(["架构", "策略", "回测"])
    """
    ctx = _get_ctx()
    s = stats()

    if s['segments'] == 0 and not facts():
        return ""

    lines = ["[管家] 历史上下文摘要:"]

    # 列出所有事实（最有价值的信息）
    all_facts = facts()
    if all_facts:
        lines.append("  已记录的事实:")
        for f in all_facts:
            lines.append(f"    - {f['fact_key']}: {f['fact_value']}")

    # 最近决策
    conn = ctx._db._get_conn()
    recent_decisions = conn.execute(
        "SELECT content FROM tape_segments WHERE session_id=? AND role='decision' ORDER BY seq DESC LIMIT 5",
        (SESSION_ID,)
    ).fetchall()
    if recent_decisions:
        lines.append("  最近的决策:")
        for r in recent_decisions:
            lines.append(f"    - {r['content'][:150]}")

    # 如有关键词，精细搜索
    if hints:
        lines.append(f"  关键词检索 ({', '.join(hints)}):")
        for hint in hints:
            matches = _sql_search(hint, limit=2)
            for m in matches:
                lines.append(f"    [{m['source']}] {m['content'][:150]}")

    global _saved_tokens
    # 估算：不用管家的话，至少要读 5 个文件 × 2000 tokens = 10000
    _saved_tokens += 10000

    return "\n".join(lines)


def fold_now() -> dict | None:
    """
    手动触发折叠 — 用本地免费小模型压缩旧对话
    云端大模型看到的窗口更干净，token 开销更低
    """
    fold = _get_ctx().fold_manually()
    if fold:
        return {
            "summary": fold.summary[:200],
            "keywords": fold.get_keywords(),
            "compression": f"{fold.compression_ratio:.1%}",
            "saved_tokens": fold.original_tokens - fold.folded_tokens,
        }
    return None


def forget(key: str | None = None):
    """删除事实或清空会话"""
    ctx = _get_ctx()
    db = ctx._db
    sid = ctx.session_id or SESSION_ID
    if key:
        db._execute("DELETE FROM context_facts WHERE session_id=? AND fact_key=?", (sid, key))
        return f"已删除事实: {key}"
    else:
        for tbl in ["tape_segments", "tape_folds", "tape_indices", "context_facts"]:
            db._execute(f"DELETE FROM {tbl} WHERE session_id = ?", (sid,))
        ctx.end_session()
        global _ctx, _saved_tokens, _query_count
        _ctx = None
        _saved_tokens = 0
        _query_count = 0
        return f"已清空会话 {sid}"


def savings() -> str:
    """查看省费报告"""
    s = stats()
    return (
        f"[管家省费报告]\n"
        f"  查询次数: {_query_count}\n"
        f"  累计节省: ~{_saved_tokens} tokens\n"
        f"  折合费用: ~${_saved_tokens / 1_000_000 * 0.43:.4f} (按 DeepSeek V4 Pro $0.43/M)\n"
        f"  数据库: {s['segments']}段 / {s['folds']}折叠 / {s['total_tokens']}tokens\n"
        f"  事实数: {len(facts())}"
    )


# ── 启动诊断 ──────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  CodeWhale 上下文管家 v3 — 省费引擎")
    print("=" * 55)
    ctx = _get_ctx()
    s = stats()
    print(f"  会话: {s['session_id']}")
    print(f"  策展人: {'LLM (免费)' if s['curator_available'] else 'fallback'}")
    print(f"  数据: {s['segments']}段 / {s['folds']}折叠 / {s['total_tokens']}tokens")
    print(f"  事实: {len(facts())} 条")
    print(f"  数据库: {DB_PATH}")
    print()
    print(savings())
    print("=" * 55)
