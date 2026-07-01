"""
context_engine.py — 双层上下文引擎 (本地小模型 + 大模型 循环系统)

┌──────────────────────────────────────────────────────┐
│  胶带卷 (Tape Roll) 隐喻:                             │
│  · 新内容追加到胶带末端                                │
│  · 旧内容不丢失 — 由本地小模型折叠成摘要                │
│  · 折叠点带索引，需要时本地小模型召回原文重新总结        │
│  · 大模型始终看到: 活跃窗口 + 折叠摘要注入              │
│                                                       │
│  架构:                                                │
│  ☁️  大模型 (推理/决策) ← 活跃窗口注入折叠摘要          │
│  🏠  本地小模型 3B-4B (摘要/索引/回溯)                 │
│  🗄️  SQLite 持久化 (所有原始数据 + 折叠 + 索引)        │
│  🪞  MirrorContext (沙盒安全)                         │
└──────────────────────────────────────────────────────┘

用法:
    from gbt.context_engine import ContextManager, ContextConfig

    ctx = ContextManager(
        large_model_llm=my_cloud_llm,   # GBTLLM 实例
        small_model_name="qwen2.5:3b",  # Ollama 本地模型
    )

    # 启动会话
    ctx.start_session("my_project_session")

    # 每次对话往返
    response = ctx.send("帮我分析这个项目结构")

    # 大模型主动请求历史上下文时
    historical_summary = ctx.retrieve_context("三小时前讨论过的数据库设计")

    # 查看胶带卷状态
    print(ctx.tape_stats())

    # 结束会话 — 所有数据持久化
    ctx.end_session()
"""

import os, re, json, time, hashlib, sqlite3, threading
from typing import Dict, List, Optional, Tuple, Any, Iterator, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager

# ── 可选依赖 ────────────────────────────────────────────────
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ── 常量 ────────────────────────────────────────────────────

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_DB_PATH = os.path.join(DB_DIR, "context_tape.db")

# 默认本地小模型 (推荐 3B-4B)
SMALL_MODEL_CANDIDATES = [
    "qwen2.5:3b",       # 阿里通义千问3B — 中文最佳
    "phi4-mini:3.8b",    # 微软Phi-4-mini
    "llama3.2:3b",       # Meta Llama 3.2 3B
    "gemma2:2b",         # Google Gemma 2 2B
]

# 本地小模型的默认系统提示
CURATOR_SYSTEM_PROMPT = """你是上下文策展人，负责整理、摘要和索引对话历史。

## 能力
1. **摘要**: 将长对话折叠为简洁的结构化摘要
2. **索引**: 提取关键词、主题、决策要点
3. **回溯**: 根据查询从原始对话中提取相关信息重新总结

## 摘要格式
```json
{
  "summary": "核心内容摘要(100-200字)",
  "keywords": ["关键词1", "关键词2", ...],
  "decisions": ["决策1", "决策2", ...],
  "facts": {"key": "value", ...},
  "sentiment": "positive|neutral|negative",
  "priority": 1-5
}
```

## 规则
- 保持简洁，不要遗漏关键决策和事实
- 优先保留与当前任务相关的信息
- JSON格式严格输出"""


# ── 数据结构 ────────────────────────────────────────────────

class SegmentRole(str, Enum):
    """胶带段角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SUMMARY = "summary"    # 折叠后的摘要注入


@dataclass
class TapeSegment:
    """胶带上的一个段 — 单条消息或一组消息的折叠"""
    id: Optional[int] = None
    session_id: str = ""
    seq: int = 0                    # 序列号
    role: str = "user"
    content: str = ""
    token_estimate: int = 0         # 估算token数
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id, "session_id": self.session_id,
            "seq": self.seq, "role": self.role, "content": self.content,
            "token_estimate": self.token_estimate, "timestamp": self.timestamp
        }


@dataclass
class TapeFold:
    """胶带折叠 — 将多个连续段折叠为一个摘要"""
    id: Optional[int] = None
    session_id: str = ""
    start_seq: int = 0              # 折叠起始段序号
    end_seq: int = 0                # 折叠结束段序号
    original_tokens: int = 0        # 原始token数
    folded_tokens: int = 0          # 折叠后token数
    compression_ratio: float = 0.0  # 压缩比
    summary: str = ""               # 折叠摘要
    keywords: str = ""              # JSON格式关键词列表
    decisions: str = ""             # JSON格式决策列表
    facts: str = ""                 # JSON格式事实字典
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_keywords(self) -> List[str]:
        try:
            return json.loads(self.keywords) if self.keywords else []
        except Exception:
            return []
    
    def get_decisions(self) -> List[str]:
        try:
            return json.loads(self.decisions) if self.decisions else []
        except Exception:
            return []
    
    def get_facts(self) -> dict:
        try:
            return json.loads(self.facts) if self.facts else {}
        except Exception:
            return {}


@dataclass
class ContextConfig:
    """上下文引擎配置"""
    # 本地小模型配置
    small_model_name: str = "qwen2.5:3b"
    small_model_base_url: str = "http://localhost:11434/v1"
    small_model_temperature: float = 0.3
    small_model_max_tokens: int = 1024
    
    # 折叠策略
    max_active_tokens: int = 8000          # 活跃窗口最大token数
    fold_trigger_ratio: float = 0.75       # 触发折叠的token占比
    fold_batch_size: int = 6               # 每次折叠的段数
    min_fold_age: int = 4                  # 至少保留最近N段不折叠
    
    # 索引策略
    auto_index: bool = True                # 自动建索引
    index_keyword_count: int = 10          # 每次提取关键词数
    
    # 数据库
    db_path: str = DEFAULT_DB_PATH
    
    # 镜像空间
    use_mirror: bool = True                # 是否使用镜像空间沙盒


# ── SQLite Schema ──────────────────────────────────────────

CTX_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tape_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    project_name TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    total_segments INTEGER NOT NULL DEFAULT 0,
    total_folds INTEGER NOT NULL DEFAULT 0,
    total_tokens_estimate INTEGER NOT NULL DEFAULT 0,
    active_window_tokens INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tape_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    token_estimate INTEGER NOT NULL DEFAULT 0,
    is_folded INTEGER NOT NULL DEFAULT 0,
    fold_id INTEGER,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(fold_id) REFERENCES tape_folds(id)
);

CREATE TABLE IF NOT EXISTS tape_folds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    start_seq INTEGER NOT NULL,
    end_seq INTEGER NOT NULL,
    original_tokens INTEGER NOT NULL DEFAULT 0,
    folded_tokens INTEGER NOT NULL DEFAULT 0,
    compression_ratio REAL NOT NULL DEFAULT 0,
    summary TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '[]',
    decisions TEXT NOT NULL DEFAULT '[]',
    facts TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tape_indices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    fold_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(fold_id) REFERENCES tape_folds(id)
);

CREATE TABLE IF NOT EXISTS context_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    fact_key TEXT NOT NULL,
    fact_value TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'general',
    confidence REAL NOT NULL DEFAULT 1.0,
    source_seq INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(session_id, fact_key)
);

CREATE INDEX IF NOT EXISTS idx_segments_session ON tape_segments(session_id, seq);
CREATE INDEX IF NOT EXISTS idx_segments_folded ON tape_segments(session_id, is_folded);
CREATE INDEX IF NOT EXISTS idx_folds_session ON tape_folds(session_id, start_seq);
CREATE INDEX IF NOT EXISTS idx_indices_fold ON tape_indices(fold_id);
CREATE INDEX IF NOT EXISTS idx_indices_keyword ON tape_indices(keyword);
CREATE INDEX IF NOT EXISTS idx_facts_session ON context_facts(session_id);
"""


# ── Token 估算辅助 ──────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """粗略token估算: 中文 ~1.5字/token, 英文 ~4字/token"""
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return max(1, int(chinese_chars / 1.5 + other_chars / 4))


def estimate_messages_tokens(messages: List[dict]) -> int:
    """估算消息列表的token数"""
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.get("content", ""))
    return total + len(messages) * 4  # 每条消息的结构开销


# ── 本地小模型客户端 ────────────────────────────────────────

class LocalCurator:
    """本地小模型策展人 — 负责摘要、索引、回溯
    
    使用Ollama运行3B-4B小模型，作为上下文管家：
    - summarize(): 把长对话折叠成结构化摘要
    - index(): 为折叠段建立关键词索引
    - retrieve(): 根据查询召回相关历史，重新总结
    - extract_facts(): 从对话中提取结构化事实
    """
    
    def __init__(
        self,
        model_name: str = "qwen2.5:3b",
        base_url: str = "http://localhost:11434/v1",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: int = 60,
    ):
        if not HAS_OPENAI:
            raise ImportError("LocalCurator需要 openai 库: pip install openai")
        
        self.model = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = OpenAI(base_url=base_url, api_key="ollama", timeout=timeout)
        self._lock = threading.Lock()
        
        # 自检
        self._available = self._health_check()
        if self._available:
            print(f"✅ LocalCurator: {model_name} 就绪")
        else:
            print(f"⚠️ LocalCurator: {model_name} 不可用，将使用本地回退")
    
    @property
    def available(self) -> bool:
        return self._available
    
    def _health_check(self) -> bool:
        """检查本地模型是否可用"""
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=4,
                temperature=0,
            )
            return bool(resp.choices and resp.choices[0].message.content)
        except Exception as e:
            print(f"  ⚠️ LocalCurator 健康检查失败: {e}")
            return False
    
    def _call(self, prompt: str, system: str = "") -> str:
        """调用本地小模型"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        try:
            with self._lock:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            return (resp.choices[0].message.content or "") if resp.choices else ""
        except Exception as e:
            print(f"  ❌ LocalCurator 调用失败: {e}")
            return ""
    
    def summarize(self, segments: List[TapeSegment]) -> Optional[TapeFold]:
        """折叠一段对话为摘要"""
        if not segments:
            return None
        
        content = "\n\n".join(
            f"[{s.role.upper()}] {s.content[:500]}"
            for s in segments
        )
        
        prompt = f"请将以下对话折叠为结构化摘要，用JSON格式输出:\n\n{content}"
        
        response = self._call(prompt, system=CURATOR_SYSTEM_PROMPT)
        if not response:
            return self._fallback_summarize(segments)
        
        # 解析JSON
        parsed = self._parse_json_response(response)
        
        original_tokens = sum(s.token_estimate for s in segments)
        summary = parsed.get("summary", response[:300])
        folded_tokens = estimate_tokens(summary)
        
        return TapeFold(
            session_id=segments[0].session_id if segments else "",
            start_seq=segments[0].seq if segments else 0,
            end_seq=segments[-1].seq if segments else 0,
            original_tokens=original_tokens,
            folded_tokens=folded_tokens,
            compression_ratio=folded_tokens / max(original_tokens, 1),
            summary=summary,
            keywords=json.dumps(parsed.get("keywords", []), ensure_ascii=False),
            decisions=json.dumps(parsed.get("decisions", []), ensure_ascii=False),
            facts=json.dumps(parsed.get("facts", {}), ensure_ascii=False),
        )
    
    @staticmethod
    def _fallback_summarize(segments: List[TapeSegment]) -> "TapeFold":
        """无小模型时的回退摘要 — 取每段前80字拼接"""
        parts = []
        keywords = set()
        for s in segments:
            snippet = s.content[:80].replace("\n", " ")
            parts.append(f"[{s.role}] {snippet}")
            # 简单提取中文关键词 (2-4字词组)
            words = re.findall(r'[\u4e00-\u9fff]{2,4}', s.content)
            for w in words[:3]:
                keywords.add(w)
        
        summary = " | ".join(parts[:6])
        if len(parts) > 6:
            summary += f" ... (共{len(parts)}段)"
        
        original_tokens = sum(s.token_estimate for s in segments)
        folded_tokens = estimate_tokens(summary)
        
        return TapeFold(
            session_id=segments[0].session_id if segments else "",
            start_seq=segments[0].seq if segments else 0,
            end_seq=segments[-1].seq if segments else 0,
            original_tokens=original_tokens,
            folded_tokens=folded_tokens,
            compression_ratio=folded_tokens / max(original_tokens, 1),
            summary=summary,
            keywords=json.dumps(list(keywords)[:10], ensure_ascii=False),
            decisions=json.dumps([], ensure_ascii=False),
            facts=json.dumps({}, ensure_ascii=False),
        )
    
    def retrieve(
        self,
        query: str,
        folds: List[TapeFold],
        segments: List[TapeSegment],
        top_k: int = 3,
    ) -> str:
        """回溯 — 根据查询从折叠和原始段中召回相关信息
        
        Args:
            query: 回溯查询
            folds: 所有折叠的摘要
            segments: 原始段 (可以按fold范围加载)
            top_k: 返回最相关的K个折叠
            
        Returns:
            重新总结后的上下文
        """
        if not folds and not segments:
            return ""
        
        # Step 1: 用关键词匹配初步筛选
        query_words = set(re.findall(r'[\u4e00-\u9fff]{2,6}', query.lower()))
        scored_folds = []
        
        for fold in folds:
            score = 0.0
            # 关键词匹配
            for kw in fold.get_keywords():
                if any(qw in kw for qw in query_words):
                    score += 2.0
                if any(kw in qw for qw in query_words):
                    score += 1.0
            # 摘要内容匹配
            summary_lower = fold.summary.lower()
            for qw in query_words:
                if qw in summary_lower:
                    score += 1.0
            if score > 0:
                scored_folds.append((score, fold))
        
        # 按分数排序取top_k
        scored_folds.sort(key=lambda x: x[0], reverse=True)
        top_folds = [f for _, f in scored_folds[:top_k]]
        
        if not top_folds:
            # 没有匹配 — 尝试用最近折叠
            if folds:
                top_folds = [folds[-1]]
            else:
                return ""
        
        # Step 2: 如果小模型可用，让它重新总结
        if self._available:
            context_parts = []
            for fold in top_folds:
                context_parts.append(f"[折叠 {fold.start_seq}-{fold.end_seq}] {fold.summary}")
            
            combined = "\n\n".join(context_parts)
            prompt = (
                f"用户查询: {query}\n\n"
                f"以下是从历史对话中找到的相关上下文:\n{combined}\n\n"
                f"请提取与查询最相关的信息并重新总结 (100-200字):"
            )
            
            response = self._call(prompt, CURATOR_SYSTEM_PROMPT)
            if response:
                return response
        
        # Step 3: 回退 — 直接拼接摘要
        return "\n---\n".join(
            f"[历史 {f.start_seq}-{f.end_seq}]: {f.summary[:200]}"
            for f in top_folds
        )
    
    def index_segments(self, segments: List[TapeSegment]) -> Dict[str, List[str]]:
        """为段建立关键词索引"""
        indices: Dict[str, List[str]] = {}
        content = " ".join(s.content[:200] for s in segments)
        
        if self._available:
            prompt = f"从以下内容提取10个关键词，用JSON数组格式返回:\n{content[:800]}"
            response = self._call(prompt)
            parsed = self._parse_json_response(response)
            keywords = parsed.get("keywords", []) if isinstance(parsed, dict) else []
            if keywords:
                for kw in keywords[:10]:
                    indices[kw] = indices.get(kw, [])
                return indices
        
        # 回退: 简单提取中文词组
        words = re.findall(r'[\u4e00-\u9fff]{2,4}', content)
        from collections import Counter
        top_words = [w for w, _ in Counter(words).most_common(10)]
        for w in top_words:
            indices[w] = indices.get(w, [])
        return indices
    
    def extract_facts(self, segments: List[TapeSegment]) -> Dict[str, str]:
        """从对话中提取结构化事实"""
        content = " ".join(s.content[:300] for s in segments)
        
        if self._available:
            prompt = (
                f"从对话中提取关键事实，以JSON字典格式返回 (key=事实名称, value=事实值):\n"
                f"{content[:1000]}"
            )
            response = self._call(prompt)
            parsed = self._parse_json_response(response)
            if isinstance(parsed, dict) and parsed:
                facts = {}
                for k, v in parsed.items():
                    if k not in ("keywords", "summary", "decisions"):
                        facts[str(k)] = str(v)
                return facts
        
        return {}
    
    def _parse_json_response(self, text: str) -> dict:
        """从模型输出中提取JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 ```json ... ``` 代码块
        m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试提取 { ... }
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        
        return {"summary": text[:300]}


# ── 胶带卷数据库 ────────────────────────────────────────────

class TapeDatabase:
    """胶带卷SQLite持久化层 — 线程安全"""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript(CTX_SCHEMA_SQL)
            conn.commit()
    
    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=3000")
        return self._local.conn
    
    @contextmanager
    def conn(self):
        c = self._get_conn()
        try:
            yield c
        finally:
            pass
    
    # ── Session ──
    
    def create_session(self, session_id: str, project_name: str = "") -> int:
        now = datetime.now().isoformat()
        with self.conn() as c:
            cur = c.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO tape_sessions "
                "(session_id, project_name, status, created_at, updated_at) "
                "VALUES (?, ?, 'active', ?, ?)",
                (session_id, project_name, now, now)
            )
            c.commit()
            return cur.lastrowid
    
    def update_session(self, session_id: str, **kwargs):
        fields = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [session_id, datetime.now().isoformat()]
        with self.conn() as c:
            c.execute(
                f"UPDATE tape_sessions SET {fields}, updated_at=? WHERE session_id=?",
                values
            )
            c.commit()
    
    def get_session(self, session_id: str) -> Optional[dict]:
        with self.conn() as c:
            row = c.execute(
                "SELECT * FROM tape_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
            return dict(row) if row else None
    
    # ── Segments ──
    
    def insert_segment(self, segment: TapeSegment) -> int:
        with self.conn() as c:
            cur = c.cursor()
            cur.execute(
                "INSERT INTO tape_segments "
                "(session_id, seq, role, content, token_estimate, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (segment.session_id, segment.seq, segment.role,
                 segment.content, segment.token_estimate, segment.timestamp)
            )
            c.commit()
            return cur.lastrowid
    
    def get_segments(self, session_id: str, start_seq: int = 0,
                     end_seq: Optional[int] = None,
                     exclude_folded: bool = False) -> List[TapeSegment]:
        query = "SELECT * FROM tape_segments WHERE session_id=? AND seq>=?"
        params: list = [session_id, start_seq]
        
        if end_seq is not None:
            query += " AND seq<=?"
            params.append(end_seq)
        if exclude_folded:
            query += " AND is_folded=0"
        
        query += " ORDER BY seq ASC"
        
        with self.conn() as c:
            rows = c.execute(query, params).fetchall()
        
        return [
            TapeSegment(
                id=row["id"], session_id=row["session_id"],
                seq=row["seq"], role=row["role"],
                content=row["content"], token_estimate=row["token_estimate"],
                timestamp=row["timestamp"]
            )
            for row in rows
        ]
    
    def mark_folded(self, segment_ids: List[int], fold_id: int):
        with self.conn() as c:
            for sid in segment_ids:
                c.execute(
                    "UPDATE tape_segments SET is_folded=1, fold_id=? WHERE id=?",
                    (fold_id, sid)
                )
            c.commit()
    
    def get_segment_count(self, session_id: str) -> int:
        with self.conn() as c:
            row = c.execute(
                "SELECT COUNT(*) as cnt FROM tape_segments WHERE session_id=?",
                (session_id,)
            ).fetchone()
            return row["cnt"] if row else 0
    
    # ── Folds ──
    
    def insert_fold(self, fold: TapeFold) -> int:
        with self.conn() as c:
            cur = c.cursor()
            cur.execute(
                "INSERT INTO tape_folds "
                "(session_id, start_seq, end_seq, original_tokens, "
                "folded_tokens, compression_ratio, summary, keywords, "
                "decisions, facts, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (fold.session_id, fold.start_seq, fold.end_seq,
                 fold.original_tokens, fold.folded_tokens,
                 fold.compression_ratio, fold.summary, fold.keywords,
                 fold.decisions, fold.facts, fold.created_at)
            )
            c.commit()
            return cur.lastrowid
    
    def get_folds(self, session_id: str, limit: int = 20) -> List[TapeFold]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT * FROM tape_folds WHERE session_id=? "
                "ORDER BY start_seq DESC LIMIT ?",
                (session_id, limit)
            ).fetchall()
        
        return [
            TapeFold(
                id=row["id"], session_id=row["session_id"],
                start_seq=row["start_seq"], end_seq=row["end_seq"],
                original_tokens=row["original_tokens"],
                folded_tokens=row["folded_tokens"],
                compression_ratio=row["compression_ratio"],
                summary=row["summary"], keywords=row["keywords"],
                decisions=row["decisions"], facts=row["facts"],
                created_at=row["created_at"]
            )
            for row in rows
        ]
    
    # ── Indices ──
    
    def insert_indices(self, fold_id: int, keywords: Dict[str, List[str]],
                       session_id: str):
        now = datetime.now().isoformat()
        with self.conn() as c:
            for kw in keywords:
                c.execute(
                    "INSERT INTO tape_indices "
                    "(session_id, fold_id, keyword, weight, created_at) "
                    "VALUES (?, ?, ?, 1.0, ?)",
                    (session_id, fold_id, kw, now)
                )
            c.commit()
    
    def search_indices(self, session_id: str, query: str,
                       limit: int = 10) -> List[int]:
        """搜索关键词索引，返回fold_id列表"""
        with self.conn() as c:
            # 用LIKE做简单搜索
            rows = c.execute(
                "SELECT DISTINCT fold_id FROM tape_indices "
                "WHERE session_id=? AND keyword LIKE ? "
                "LIMIT ?",
                (session_id, f"%{query}%", limit)
            ).fetchall()
            return [row["fold_id"] for row in rows]
    
    # ── Facts ──
    
    def upsert_fact(self, session_id: str, key: str, value: str,
                    category: str = "general", confidence: float = 1.0,
                    source_seq: int = 0):
        now = datetime.now().isoformat()
        with self.conn() as c:
            c.execute(
                "INSERT INTO context_facts "
                "(session_id, fact_key, fact_value, category, confidence, "
                "source_seq, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id, fact_key) DO UPDATE SET "
                "fact_value=excluded.fact_value, "
                "confidence=excluded.confidence, "
                "updated_at=excluded.updated_at",
                (session_id, key, value, category, confidence,
                 source_seq, now, now)
            )
            c.commit()
    
    def get_facts(self, session_id: str, category: Optional[str] = None) -> List[dict]:
        query = "SELECT * FROM context_facts WHERE session_id=?"
        params: list = [session_id]
        if category:
            query += " AND category=?"
            params.append(category)
        
        with self.conn() as c:
            rows = c.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    
    def search_facts(self, session_id: str, query: str, limit: int = 10) -> List[dict]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT * FROM context_facts WHERE session_id=? "
                "AND (fact_key LIKE ? OR fact_value LIKE ?) LIMIT ?",
                (session_id, f"%{query}%", f"%{query}%", limit)
            ).fetchall()
        return [dict(row) for row in rows]
    
    def __del__(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            try:
                self._local.conn.close()
            except Exception:
                pass


# ── 上下文管理器 ────────────────────────────────────────────

class ContextManager:
    """双层上下文管理器 — 胶带卷循环系统
    
    核心工作流:
    1. 用户消息追加到胶带 (append_segment)
    2. 检查token计数 → 超阈值时触发折叠 (fold)
    3. 折叠: 本地小模型摘要 → 存储到DB → 标记原段为已折叠
    4. 构建活跃窗口: 最近N段 + 折叠摘要注入
    5. 大模型请求历史时: retrieve_context() 召回+重摘要
    
    Usage:
        from gbt.llm import GBTLLM
        from gbt.context_engine import ContextManager
        
        cloud_llm = GBTLLM(provider="deepseek")
        ctx = ContextManager(large_model_llm=cloud_llm, auto_curator=True)
        
        ctx.start_session("my_project")
        response = ctx.send("帮我分析这个项目")
        ctx.end_session()
    """
    
    def __init__(
        self,
        large_model_llm: Any = None,     # GBTLLM 实例
        config: Optional[ContextConfig] = None,
        small_model_name: str = "qwen2.5:3b",
        curator: Optional[LocalCurator] = None,
        database: Optional[TapeDatabase] = None,
        auto_curator: bool = True,
    ):
        self.config = config or ContextConfig(small_model_name=small_model_name)
        self.large_llm = large_model_llm
        self._db = database or TapeDatabase(self.config.db_path)
        self._curator = curator
        
        # 自动初始化策展人
        if auto_curator and self._curator is None:
            try:
                self._curator = LocalCurator(
                    model_name=self.config.small_model_name,
                    base_url=self.config.small_model_base_url,
                    temperature=self.config.small_model_temperature,
                    max_tokens=self.config.small_model_max_tokens,
                )
            except Exception as e:
                print(f"⚠️ LocalCurator 初始化失败: {e}")
                self._curator = None
        
        # 运行时状态
        self._session_id: Optional[str] = None
        self._segments: List[TapeSegment] = []      # 活跃段 (内存)
        self._folds: List[TapeFold] = []            # 折叠缓存
        self._seq_counter: int = 0
        self._total_tokens: int = 0
        
        print(f"📼 ContextManager 就绪 | "
              f"小模型={'✅' if self._curator and self._curator.available else '⚠️ 回退'} | "
              f"激活窗口={self.config.max_active_tokens}tokens")
    
    @property
    def session_id(self) -> Optional[str]:
        return self._session_id
    
    # ── Session 生命周期 ──
    
    def start_session(self, session_id: Optional[str] = None,
                      project_name: str = "") -> str:
        """启动新会话"""
        if self._session_id:
            self.end_session()
        
        self._session_id = session_id or self._generate_session_id()
        self._segments = []
        self._folds = []
        self._seq_counter = 0
        self._total_tokens = 0
        
        self._db.create_session(self._session_id, project_name)
        print(f"📼 会话启动: {self._session_id}")
        return self._session_id
    
    def end_session(self) -> dict:
        """结束当前会话并返回统计"""
        if not self._session_id:
            return {}
        
        stats = self.tape_stats()
        self._db.update_session(
            self._session_id,
            status="completed",
            total_segments=stats["segments"],
            total_folds=stats["folds"],
            total_tokens_estimate=stats["total_tokens"],
            active_window_tokens=stats["active_tokens"],
        )
        
        print(f"📼 会话结束: {self._session_id} | {stats['segments']}段/{stats['folds']}折叠")
        
        sid = self._session_id
        self._session_id = None
        self._segments = []
        self._folds = []
        self._seq_counter = 0
        self._total_tokens = 0
        
        return {"session_id": sid, **stats}
    
    def resume_session(self, session_id: str) -> bool:
        """恢复已有会话"""
        sess = self._db.get_session(session_id)
        if not sess:
            print(f"❌ 会话不存在: {session_id}")
            return False
        
        self._session_id = session_id
        
        # 加载最近的未折叠段
        self._segments = self._db.get_segments(session_id, exclude_folded=True)
        self._seq_counter = max((s.seq for s in self._segments), default=0)
        self._total_tokens = sum(s.token_estimate for s in self._segments)
        
        # 加载折叠
        self._folds = self._db.get_folds(session_id)
        
        print(f"📼 恢复会话: {session_id} | "
              f"{len(self._segments)}活跃段/{len(self._folds)}折叠 | "
              f"{self._total_tokens}tokens")
        return True
    
    # ── 核心操作 ──
    
    def append(self, content: str, role: str = "user") -> TapeSegment:
        """追加一段内容到胶带"""
        assert self._session_id, "请先调用 start_session()"
        
        self._seq_counter += 1
        segment = TapeSegment(
            session_id=self._session_id,
            seq=self._seq_counter,
            role=role,
            content=content,
            token_estimate=estimate_tokens(content),
        )
        
        # 持久化
        segment.id = self._db.insert_segment(segment)
        
        # 加入内存
        self._segments.append(segment)
        self._total_tokens += segment.token_estimate
        
        # 自动折叠检查
        self._auto_fold()
        
        return segment
    
    def send(self, user_message: str, system_prompt: str = "",
             **llm_kwargs) -> str:
        """发送用户消息到大模型，自动管理上下文
        
        完整流程:
        1. 追加用户消息
        2. 构建活跃窗口 (最近N段 + 折叠摘要)
        3. 调用大模型
        4. 追加助手回复
        5. 返回响应
        """
        # 1. 追加用户消息
        self.append(user_message, role="user")
        
        # 2. 构建消息
        messages = self._build_active_window(system_prompt)
        
        # 3. 调用大模型
        if self.large_llm:
            try:
                response = self.large_llm.invoke(messages, **llm_kwargs)
            except Exception as e:
                response = f"[大模型调用失败: {e}]"
        else:
            response = "[未配置大模型]"
        
        # 4. 追加助手回复
        self.append(response, role="assistant")
        
        return response
    
    def retrieve_context(self, query: str) -> str:
        """回溯历史上下文 — 大模型主动请求时调用
        
        流程:
        1. 搜索关键词索引
        2. 本地小模型召回相关折叠
        3. 加载原始段 → 重新总结
        4. 返回精炼上下文
        """
        assert self._session_id, "请先调用 start_session()"
        
        if not self._curator or not self._curator.available:
            # 回退: 直接搜索事实库
            facts = self._db.search_facts(self._session_id, query, limit=5)
            if facts:
                return "\n".join(f"[{f['fact_key']}] {f['fact_value']}" for f in facts)
            return ""
        
        # 获取所有折叠
        all_folds = self._folds + self._db.get_folds(self._session_id)
        # 加载可召回段的概要
        recall_segments = self._db.get_segments(
            self._session_id,
            start_seq=max(0, self._seq_counter - 20),
            exclude_folded=False,
        )[:20]
        
        result = self._curator.retrieve(query, all_folds, recall_segments)
        return result or f"[未找到相关上下文: {query}]"
    
    def fetch_context_for_large_model(self, system_prompt: str = "") -> List[dict]:
        """构建给大模型的完整上下文消息列表
        
        包括:
        - System prompt
        - 最近的折叠摘要注入
        - 最近的活跃段
        """
        return self._build_active_window(system_prompt)
    
    # ── 折叠机制 ──
    
    def _auto_fold(self):
        """自动折叠检查 — 超token阈值时触发"""
        if self._total_tokens < self.config.max_active_tokens * self.config.fold_trigger_ratio:
            return
        
        # 确定折叠范围: 最老的段 (保留最近min_fold_age段)
        fold_cutoff = len(self._segments) - self.config.min_fold_age
        if fold_cutoff <= 0:
            return
        
        batch_size = min(self.config.fold_batch_size, fold_cutoff)
        segments_to_fold = self._segments[:batch_size]
        
        if not segments_to_fold:
            return
        
        print(f"📼 触发折叠: {len(segments_to_fold)}段 → 摘要")
        self._fold_segments(segments_to_fold)
    
    def _fold_segments(self, segments: List[TapeSegment]) -> Optional[TapeFold]:
        """执行折叠"""
        if not self._curator or not self._curator.available:
            fold = LocalCurator._fallback_summarize(segments)
        else:
            fold = self._curator.summarize(segments)
        
        if not fold:
            return None
        
        fold.session_id = self._session_id or ""
        
        # 持久化折叠
        fold.id = self._db.insert_fold(fold)
        
        # 标记原段为已折叠
        self._db.mark_folded(
            [s.id for s in segments if s.id is not None],
            fold.id
        )
        
        # 建索引
        if self._curator:
            indices = self._curator.index_segments(segments)
            self._db.insert_indices(fold.id, indices, self._session_id or "")
        
        # 提取事实
        if self._curator and self._curator.available:
            facts = self._curator.extract_facts(segments)
            for k, v in facts.items():
                self._db.upsert_fact(
                    self._session_id or "", k, v,
                    source_seq=segments[0].seq if segments else 0
                )
        
        # 更新内存状态
        self._folds.append(fold)
        
        # 移除已折叠段
        folded_ids = {id(s) for s in segments}
        self._segments = [s for s in self._segments if id(s) not in folded_ids]
        self._total_tokens = sum(s.token_estimate for s in self._segments)
        
        # 添加折叠摘要作为占位段
        if fold.summary:
            summary_seg = TapeSegment(
                session_id=self._session_id or "",
                seq=-fold.start_seq,  # 负序号表示折叠摘要
                role="summary",
                content=f"[📼 折叠摘要 {fold.start_seq}-{fold.end_seq}]: {fold.summary}",
                token_estimate=fold.folded_tokens,
            )
            # 不持久化摘要段，只注入到上下文
            self._segments.insert(0, summary_seg)
        
        print(f"  ✅ 折叠完成: {fold.original_tokens}→{fold.folded_tokens}tokens "
              f"({fold.compression_ratio:.1%})")
        return fold
    
    def fold_manually(self, num_segments: Optional[int] = None) -> Optional[TapeFold]:
        """手动触发折叠"""
        if not self._segments:
            return None
        
        n = num_segments or min(self.config.fold_batch_size, len(self._segments) - 2)
        n = max(1, min(n, len(self._segments)))
        
        segments_to_fold = self._segments[:n]
        return self._fold_segments(segments_to_fold)
    
    # ── 活跃窗口构建 ──
    
    def _build_active_window(self, system_prompt: str = "") -> List[dict]:
        """构建活跃上下文窗口"""
        messages = []
        
        # System prompt
        full_system = system_prompt or "你是一个有用的AI助手。"
        
        # 注入折叠摘要
        fold_injections = self._get_fold_injections()
        if fold_injections:
            full_system += "\n\n## 历史上下文 (折叠摘要)\n" + fold_injections
        
        messages.append({"role": "system", "content": full_system})
        
        # 活跃段
        for seg in self._segments:
            if seg.role != SegmentRole.SUMMARY.value:
                # 跳过已折叠的summary类型占位段
                if seg.seq > 0:
                    messages.append({"role": seg.role, "content": seg.content})
        
        return messages
    
    def _get_fold_injections(self) -> str:
        """获取折叠摘要注入文本"""
        if not self._folds:
            return ""
        
        parts = []
        for fold in self._folds[-5:]:  # 最近5个折叠
            kws = fold.get_keywords()
            kw_str = ", ".join(kws[:5]) if kws else "无"
            parts.append(
                f"- **[{fold.start_seq}-{fold.end_seq}]** {fold.summary[:150]}"
                f" (关键词: {kw_str})"
            )
        
        return "\n".join(parts)
    
    # ── 统计 & 诊断 ──
    
    def tape_stats(self) -> dict:
        """胶带卷统计"""
        return {
            "session_id": self._session_id,
            "segments": len(self._segments),
            "folds": len(self._folds),
            "total_tokens": self._total_tokens,
            "active_tokens": sum(s.token_estimate for s in self._segments),
            "compression_saved": sum(
                f.original_tokens - f.folded_tokens for f in self._folds
            ),
            "curator_available": self._curator is not None and self._curator.available,
            "small_model": self.config.small_model_name if self._curator else None,
        }
    
    def get_segments(self, limit: int = 20) -> List[dict]:
        """获取最近的段 (用于UI展示)"""
        segments = self._segments[-limit:]
        return [s.to_dict() for s in segments]
    
    def get_folds(self, limit: int = 10) -> List[dict]:
        """获取最近的折叠"""
        folds = self._folds[-limit:]
        return [
            {
                "id": f.id, "start_seq": f.start_seq, "end_seq": f.end_seq,
                "original_tokens": f.original_tokens,
                "folded_tokens": f.folded_tokens,
                "compression_ratio": f.compression_ratio,
                "summary": f.summary[:200],
                "keywords": f.get_keywords(),
                "decisions": f.get_decisions(),
            }
            for f in folds
        ]
    
    def search(self, query: str) -> dict:
        """综合搜索 — 搜索折叠索引和事实库"""
        assert self._session_id, "请先调用 start_session()"
        
        fold_ids = self._db.search_indices(self._session_id, query)
        facts = self._db.search_facts(self._session_id, query)
        
        return {
            "query": query,
            "matched_folds": len(fold_ids),
            "matched_facts": len(facts),
            "facts": facts,
        }
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(str(time.time_ns()).encode()).hexdigest()[:6]
        return f"ctx_{ts}_{h}"
    
    def __repr__(self) -> str:
        s = f"ContextManager(session={self._session_id or 'none'}"
        s += f", segments={len(self._segments)}, folds={len(self._folds)}"
        s += f", curator={'✅' if self._curator and self._curator.available else '⚠️'}"
        s += ")"
        return s


# ── 镜像空间集成 ────────────────────────────────────────────

class MirrorContext:
    """镜像上下文 — 所有上下文操作在沙盒中验证后再持久化
    
    继承 MirrorSpace 的安全隔离理念:
    1. 上下文操作先在镜像DB中进行
    2. 验证通过 → 合并到真实DB
    3. 验证失败 → 丢弃镜像，不影响真实数据
    """
    
    def __init__(self, context_manager: ContextManager):
        self._ctx = context_manager
        self._mirror_db: Optional[TapeDatabase] = None
        self._mirror_session: Optional[str] = None
        self._active = False
    
    def __enter__(self):
        """进入镜像上下文空间"""
        import tempfile
        mirror_path = os.path.join(
            tempfile.gettempdir(),
            f"gbt_mirror_ctx_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"
        )
        self._mirror_db = TapeDatabase(mirror_path)
        self._mirror_session = f"mirror_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self._mirror_db.create_session(self._mirror_session, "mirror")
        self._active = True
        print(f"🪞 进入镜像上下文空间: {self._mirror_session}")
        return self
    
    def __exit__(self, *args):
        if self._active:
            # 清理镜像
            if self._mirror_db:
                try:
                    os.remove(self._mirror_db.db_path)
                except Exception:
                    pass
            self._active = False
            print("🧹 镜像上下文已清理")
    
    def test_summarize(self, content: str) -> dict:
        """在镜像中测试摘要效果"""
        if not self._ctx._curator:
            return {"error": "无可用策展人"}
        
        segments = [
            TapeSegment(
                session_id=self._mirror_session or "",
                seq=i + 1,
                role="user" if i % 2 == 0 else "assistant",
                content=content[i:i + 500] if isinstance(content, list) else content,
                token_estimate=estimate_tokens(content if isinstance(content, str) else content[i:i + 500]),
            )
            for i in range(min(3, len(content) if isinstance(content, list) else 1))
        ]
        
        fold = self._ctx._curator.summarize(segments)
        
        return {
            "original_tokens": sum(s.token_estimate for s in segments),
            "folded_tokens": fold.folded_tokens if fold else 0,
            "compression_ratio": f"{fold.compression_ratio:.1%}" if fold else "N/A",
            "summary": fold.summary if fold else "",
            "keywords": fold.get_keywords() if fold else [],
        }


# ── 工具函数 ────────────────────────────────────────────────

def discover_local_models(base_url: str = "http://localhost:11434/v1") -> List[str]:
    """发现可用的本地Ollama模型"""
    if not HAS_OPENAI:
        return []
    try:
        client = OpenAI(base_url=base_url, api_key="ollama", timeout=5)
        # Ollama list models via /api/tags
        import urllib.request, json as _json
        req = urllib.request.Request("http://localhost:11434/api/tags")
        resp = urllib.request.urlopen(req, timeout=5)
        data = _json.loads(resp.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def pick_best_local_model(models: List[str]) -> Optional[str]:
    """从可用模型中选择最合适的本地小模型 (3B-4B范围)"""
    # 优先级排序
    priority = [
        "qwen2.5:3b", "qwen2:7b",
        "phi4-mini", "phi4-mini:3.8b",
        "llama3.2:3b", "llama3.1:8b",
        "gemma2:2b", "gemma2:9b",
    ]
    available = set(m.split(":")[0].lower() if ":" in m else m.lower() for m in models)
    
    for p in priority:
        p_key = p.split(":")[0].lower() if ":" in p else p.lower()
        if p_key in available:
            # 返回精确名称
            for m in models:
                if p_key in m.lower():
                    return m
    return models[0] if models else None


# ── 便捷工厂 ────────────────────────────────────────────────

def create_context_manager(
    large_model_llm: Any = None,
    small_model: Optional[str] = None,
    db_path: Optional[str] = None,
    max_active_tokens: int = 8000,
    auto_start: bool = True,
) -> ContextManager:
    """创建上下文管理器 (自动发现最佳本地模型)
    
    Args:
        large_model_llm: GBTLLM 实例 (大模型)
        small_model: 本地小模型名 (默认自动发现)
        db_path: 数据库路径
        max_active_tokens: 活跃窗口最大token
        auto_start: 是否尝试自动连接本地小模型
    
    Returns:
        ContextManager 实例
    """
    # 自动发现
    if small_model is None and auto_start:
        available = discover_local_models()
        if available:
            small_model = pick_best_local_model(available)
            print(f"🔍 发现本地模型: {available}")
            print(f"✅ 选择: {small_model}")
    
    config = ContextConfig(
        small_model_name=small_model or "qwen2.5:3b",
        max_active_tokens=max_active_tokens,
        db_path=db_path or DEFAULT_DB_PATH,
    )
    
    return ContextManager(
        large_model_llm=large_model_llm,
        config=config,
        auto_curator=auto_start,
    )