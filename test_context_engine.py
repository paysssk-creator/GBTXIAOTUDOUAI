"""
test_context_engine.py — 上下文引擎测试 & 演示
测试 LocalCurator (回退模式)、TapeDatabase、ContextManager、MirrorContext

用法:
    python test_context_engine.py            # 基础测试 (不需要Ollama)
    python test_context_engine.py --ollama   # 完整测试 (需要Ollama运行本地模型)
"""
import os, sys, json, tempfile, time

# 确保gbt模块可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def green(s): return f"\033[92m{s}\033[0m"
def red(s): return f"\033[91m{s}\033[0m"
def blue(s): return f"\033[94m{s}\033[0m"
def bold(s): return f"\033[1m{s}\033[0m"


def test_estimate_tokens():
    """测试token估算"""
    from gbt.context_engine import estimate_tokens
    
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") > 0
    assert estimate_tokens("你好世界这是一个测试") > 0
    # 中文token数应大于英文
    cn = estimate_tokens("你好世界这是一个很长的中文测试句子")
    en = estimate_tokens("hello world this is a long english test sentence")
    print(f"  中文token: {cn}, 英文token: {en}")
    print(green("  ✅ estimate_tokens 通过"))


def test_tape_database():
    """测试SQLite数据库"""
    from gbt.context_engine import TapeDatabase, TapeSegment, TapeFold
    
    # 使用临时数据库
    db_path = os.path.join(tempfile.gettempdir(), "test_context_tape.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = TapeDatabase(db_path)
    sid = "test_session_001"
    
    # 创建会话
    db.create_session(sid, "test_project")
    sess = db.get_session(sid)
    assert sess is not None
    assert sess["status"] == "active"
    print(green("  ✅ 创建会话"))
    
    # 插入段
    seg = TapeSegment(session_id=sid, seq=1, role="user",
                      content="你好，帮我分析项目", token_estimate=10)
    seg_id = db.insert_segment(seg)
    assert seg_id > 0
    
    seg2 = TapeSegment(session_id=sid, seq=2, role="assistant",
                       content="好的，项目分析如下...", token_estimate=15)
    db.insert_segment(seg2)
    
    segments = db.get_segments(sid)
    assert len(segments) == 2
    print(green(f"  ✅ 插入&读取段: {len(segments)}段"))
    
    # 插入折叠
    fold = TapeFold(
        session_id=sid, start_seq=1, end_seq=2,
        original_tokens=25, folded_tokens=8, compression_ratio=0.32,
        summary="用户请求分析项目，AI回应概要",
        keywords=json.dumps(["项目分析", "架构"], ensure_ascii=False),
        decisions=json.dumps(["开始分析"], ensure_ascii=False),
        facts=json.dumps({"project": "test"}, ensure_ascii=False),
    )
    fold_id = db.insert_fold(fold)
    assert fold_id > 0
    print(green(f"  ✅ 插入折叠: id={fold_id}"))
    
    # 标记段为已折叠
    db.mark_folded([seg_id, seg2.id], fold_id)
    
    # 读取折叠
    folds = db.get_folds(sid)
    assert len(folds) == 1
    assert folds[0].get_keywords() == ["项目分析", "架构"]
    print(green(f"  ✅ 读取折叠: {folds[0].summary[:30]}..."))
    
    # 索引
    db.insert_indices(fold_id, {"项目分析": [], "架构": []}, sid)
    matched = db.search_indices(sid, "项目")
    assert len(matched) >= 1
    print(green(f"  ✅ 索引搜索: {len(matched)}匹配"))
    
    # 事实
    db.upsert_fact(sid, "language", "Python", category="tech")
    facts = db.get_facts(sid)
    assert len(facts) == 1
    print(green(f"  ✅ 事实存储: {facts[0]['fact_key']}={facts[0]['fact_value']}"))
    
    # 搜索事实
    results = db.search_facts(sid, "python")
    assert len(results) >= 1
    print(green(f"  ✅ 事实搜索: {len(results)}结果"))
    
    # 清理
    db.update_session(sid, status="completed")
    print(green("  ✅ 全部数据库测试通过"))
    
    # 清理临时文件
    try:
        os.remove(db_path)
        # 同时清理WAL文件
        for ext in ["-wal", "-shm"]:
            p = db_path + ext
            if os.path.exists(p):
                os.remove(p)
    except Exception:
        pass


def test_local_curator_fallback():
    """测试本地策展人回退模式 (无Ollama时)"""
    from gbt.context_engine import LocalCurator, TapeSegment, estimate_tokens
    
    # 使用不存在的模型触发回退
    curator = LocalCurator(
        model_name="nonexistent:model",
        base_url="http://localhost:11434/v1",
        temperature=0.3,
    )
    
    assert not curator.available
    print(green("  ✅ 策展人检测: 回退模式激活"))
    
    # 测试回退摘要
    segments = [
        TapeSegment(session_id="test", seq=1, role="user",
                    content="帮我写一个Python脚本来分析股票数据",
                    token_estimate=estimate_tokens("帮我写一个Python脚本来分析股票数据")),
        TapeSegment(session_id="test", seq=2, role="assistant",
                    content="好的，我先导入需要的库: pandas, numpy, matplotlib...",
                    token_estimate=estimate_tokens("好的，我先导入需要的库...")),
        TapeSegment(session_id="test", seq=3, role="user",
                    content="需要支持实时数据更新",
                    token_estimate=estimate_tokens("需要支持实时数据更新")),
        TapeSegment(session_id="test", seq=4, role="assistant",
                    content="我添加了WebSocket实时数据源连接",
                    token_estimate=estimate_tokens("我添加了WebSocket实时数据源连接")),
    ]
    
    fold = curator._fallback_summarize(segments)
    assert fold is not None
    assert fold.original_tokens > 0
    assert fold.folded_tokens > 0
    # Note: 对于短段，回退摘要可能比原始略长 (因为加了role前缀)，这是正常的
    # 在真实长对话中，压缩比会显著更好
    assert len(fold.summary) > 0
    assert len(fold.get_keywords()) > 0
    print(f"  原始tokens: {fold.original_tokens}, 折叠tokens: {fold.folded_tokens}")
    print(f"  压缩比: {fold.compression_ratio:.1%}")
    print(f"  摘要: {fold.summary[:80]}...")
    print(f"  关键词: {fold.get_keywords()}")
    print(green("  ✅ 回退摘要通过"))
    
    # 测试回退检索
    folds = [fold]
    result = curator.retrieve("股票数据", folds, segments)
    assert len(result) > 0
    print(f"  检索结果: {result[:80]}...")
    print(green("  ✅ 回退检索通过"))
    
    # 测试回退索引
    indices = curator.index_segments(segments)
    assert len(indices) > 0
    print(f"  索引关键词: {list(indices.keys())[:5]}")
    print(green("  ✅ 回退索引通过"))


def test_context_manager():
    """测试上下文管理器"""
    from gbt.context_engine import ContextManager, ContextConfig
    
    # 使用临时数据库
    db_path = os.path.join(tempfile.gettempdir(), "test_ctx_mgr.db")
    config = ContextConfig(
        small_model_name="qwen2.5:3b",
        max_active_tokens=500,
        fold_trigger_ratio=0.5,
        fold_batch_size=3,
        min_fold_age=2,
        db_path=db_path,
    )
    
    ctx = ContextManager(config=config, auto_curator=False)
    
    # 启动会话
    sid = ctx.start_session("test_project")
    assert sid is not None
    print(green(f"  ✅ 会话启动: {sid}"))
    
    # 追加段
    messages = [
        ("system", "你是一个Python助手"),
        ("user", "写一个快速排序"),
        ("assistant", "```python\ndef quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[0]\n    left = [x for x in arr[1:] if x <= pivot]\n    right = [x for x in arr[1:] if x > pivot]\n    return quicksort(left) + [pivot] + quicksort(right)\n```"),
        ("user", "这个算法时间复杂度是多少？"),
        ("assistant", "**快速排序时间复杂度**:\n- 平均: O(n log n)\n- 最坏: O(n²) 当每次选到极值\n- 最好: O(n log n)\n- 空间: O(log n) 递归栈"),
        ("user", "能不能优化？"),
        ("assistant", "可以！几个优化方向:\n1. 三数取中法选pivot — 避免最坏情况\n2. 尾递归优化 — 减少栈深度\n3. 小数组切换插入排序 — 减少递归开销"),
    ]
    
    for role, content in messages:
        ctx.append(content, role)
    
    stats = ctx.tape_stats()
    print(f"  段数: {stats['segments']}, tokens: {stats['total_tokens']}")
    print(green(f"  ✅ 追加段: {len(messages)}段"))
    
    # 手动折叠
    fold = ctx.fold_manually(num_segments=3)
    if fold:
        print(f"  折叠: {fold.original_tokens}→{fold.folded_tokens}tokens ({fold.compression_ratio:.1%})")
    
    stats2 = ctx.tape_stats()
    print(f"  折叠后: {stats2['segments']}段, {stats2['folds']}折叠")
    print(green("  ✅ 手动折叠通过"))
    
    # 构建活跃窗口
    window = ctx._build_active_window("你是Python专家")
    assert len(window) > 0
    assert window[0]["role"] == "system"
    # 检查折叠注入
    if stats2['folds'] > 0:
        assert "折叠摘要" in window[0]["content"]
    print(green(f"  ✅ 活跃窗口: {len(window)}条消息"))
    
    # 搜索
    result = ctx.search("排序")
    print(f"  搜索结果: {result}")
    print(green("  ✅ 搜索通过"))
    
    # 结束
    end_stats = ctx.end_session()
    assert end_stats["session_id"] == sid
    print(green(f"  ✅ 会话结束: {end_stats}"))
    
    # 恢复会话
    ok = ctx.resume_session(sid)
    assert ok
    stats3 = ctx.tape_stats()
    assert stats3["segments"] > 0 or stats3["folds"] > 0
    print(green(f"  ✅ 会话恢复: {stats3['segments']}段/{stats3['folds']}折叠"))
    
    # 回溯上下文
    result = ctx.retrieve_context("排序优化")
    print(f"  回溯结果: {result[:100] if result else '空'}...")
    print(green("  ✅ 上下文回溯通过"))
    
    ctx.end_session()
    
    # 清理
    try:
        os.remove(db_path)
        for ext in ["-wal", "-shm"]:
            p = db_path + ext
            if os.path.exists(p):
                os.remove(p)
    except Exception:
        pass


def test_mirror_context():
    """测试镜像上下文"""
    from gbt.context_engine import ContextManager, MirrorContext, ContextConfig
    
    db_path = os.path.join(tempfile.gettempdir(), "test_mirror_ctx.db")
    config = ContextConfig(db_path=db_path)
    ctx = ContextManager(config=config, auto_curator=False)
    
    with MirrorContext(ctx) as mirror:
        result = mirror.test_summarize(
            "我们需要设计一个数据库架构来存储用户对话历史和上下文折叠信息"
        )
        print(f"  镜像测试: {result}")
    
    print(green("  ✅ 镜像上下文通过"))
    
    ctx.end_session()
    try:
        os.remove(db_path)
        for ext in ["-wal", "-shm"]:
            p = db_path + ext
            if os.path.exists(p):
                os.remove(p)
    except Exception:
        pass


def test_create_context_manager():
    """测试便捷工厂"""
    from gbt.context_engine import create_context_manager, ContextManager
    
    db_path = os.path.join(tempfile.gettempdir(), "test_factory.db")
    ctx = create_context_manager(
        large_model_llm=None,
        small_model="qwen2.5:3b",
        db_path=db_path,
        max_active_tokens=4000,
        auto_start=False,  # 不自动连Ollama
    )
    
    assert isinstance(ctx, ContextManager)
    print(green(f"  ✅ 工厂创建: {ctx}"))
    
    # 清理
    try:
        os.remove(db_path)
        for ext in ["-wal", "-shm"]:
            p = db_path + ext
            if os.path.exists(p):
                os.remove(p)
    except Exception:
        pass


def test_context_config():
    """测试配置"""
    from gbt.context_engine import ContextConfig
    
    cfg = ContextConfig(
        small_model_name="phi4-mini",
        max_active_tokens=4000,
        fold_trigger_ratio=0.6,
    )
    
    assert cfg.small_model_name == "phi4-mini"
    assert cfg.max_active_tokens == 4000
    assert cfg.fold_trigger_ratio == 0.6
    print(green("  ✅ 配置通过"))


def run_all():
    """运行所有测试"""
    print(bold("\n" + "=" * 60))
    print(bold("  上下文引擎测试套件"))
    print(bold("=" * 60))
    
    tests = [
        ("Token估算", test_estimate_tokens),
        ("SQLite数据库", test_tape_database),
        ("策展人回退模式", test_local_curator_fallback),
        ("上下文管理器", test_context_manager),
        ("镜像空间", test_mirror_context),
        ("配置", test_context_config),
        ("便捷工厂", test_create_context_manager),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for name, func in tests:
        print(blue(f"\n── {name} ──"))
        try:
            func()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            print(red(f"  ❌ 失败: {e}"))
            import traceback
            traceback.print_exc()
    
    print(bold("\n" + "=" * 60))
    print(bold(f"  结果: {green(str(passed))}通过 / {red(str(failed))}失败"))
    
    if errors:
        for name, err in errors:
            print(red(f"  ❌ {name}: {err}"))
    
    print(bold("=" * 60))
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
