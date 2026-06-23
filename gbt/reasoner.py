"""
reasoner.py — 深度推理引擎
调用LLM真实算力进行全方位结构化推理:
分析 → 拆解 → 计算 → 评估 → 规划
"""

import time, re, logging
from collections import deque
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

L = logging.getLogger("GBT.Reasoner")


class ReasonMode(Enum):
    CHAIN="chain"             # 链式推理 (A→B→C)
    TREE="tree"               # 树形分解 (根→分支→叶)
    SWOT="swot"               # 态势分析 (优势/劣势/机会/威胁)
    ROOT_CAUSE="root_cause"   # 根因分析 (5-Why)
    DECISION="decision"       # 决策矩阵
    ESTIMATE="estimate"       # 估算推演
    COMPARE="compare"         # 对比分析
    PLAN="plan"               # 行动计划生成


@dataclass
class ReasonNode:
    """推理节点"""
    id: str; depth: int; label: str
    content: str = ""; confidence: float = 0.0
    children: List["ReasonNode"] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

@dataclass
class ReasonResult:
    """推理结果"""
    mode: ReasonMode; question: str
    nodes: List[ReasonNode] = field(default_factory=list)
    conclusion: str = ""; plan: List[str] = field(default_factory=list)
    confidence: float = 0.0; duration: float = 0.0
    raw: str = ""  # LLM原始输出


# ── 结构化推理提示模板 ──

REASON_PROMPTS = {
    ReasonMode.CHAIN: """你是一位深度推理专家。对以下问题进行**链式推理**：

**问题**: {question}
**上下文**: {context}

按以下格式逐步推理：
## 第1步: [初始分析]
对问题的核心要素进行分析。

## 第2步: [深入推导]
基于第1步，进行更深层的推导。

## 第3步: [关键洞察]
识别关键信息和约束条件。

## 第4步: [综合结论]
将所有步骤综合，给出最终答案。

## 最终答案
[清晰明确的结论]

## 置信度
[0-100]%""",

    ReasonMode.TREE: """对问题进行**树形分解推理**：

**问题**: {question}
**上下文**: {context}

按以下格式分解：
## 根节点: [问题核心]
定义问题的本质。

### 分支1: [维度1]
分析与评估。

#### 叶节点1.1: [具体点]
详细说明。

#### 叶节点1.2: [具体点]
详细说明。

### 分支2: [维度2]
分析与评估。

#### 叶节点2.1: [具体点]
详细说明。

## 综合结论
[整合所有分支的结论]

## 置信度
[0-100]%""",

    ReasonMode.SWOT: """对以下问题进行**态势分析(SWOT)**：

**问题**: {question}
**上下文**: {context}

## Strengths (优势)
1. 
2. 
3. 

## Weaknesses (劣势)
1. 
2. 
3. 

## Opportunities (机会)
1. 
2. 
3. 

## Threats (威胁)
1. 
2. 
3. 

## 策略建议
基于SWOT分析，推荐以下策略：
1. 
2. 

## 置信度
[0-100]%""",

    ReasonMode.ROOT_CAUSE: """对问题进行**根因分析(5-Why)**：

**问题**: {question}
**上下文**: {context}

## 问题描述
[清晰描述问题]

## Why 1: [为什么发生？]
[分析第一层原因]

## Why 2: [为什么那个原因存在？]
[深入第二层]

## Why 3: [为什么？]
[继续深入]

## Why 4: [为什么？]
[继续深入]

## Why 5: [为什么？]
[直到找到根本原因]

## 根本原因
[最终确定的根本原因]

## 解决方案
1. 
2. 

## 置信度
[0-100]%""",

    ReasonMode.DECISION: """对以下问题进行**决策矩阵分析**：

**问题**: {question}
**上下文**: {context}

## 可选方案
| 方案 | 可行性 | 成本 | 风险 | 收益 | 总分 |
|------|--------|------|------|------|------|
| 方案A | /10 | /10 | /10 | /10 | /40 |
| 方案B | /10 | /10 | /10 | /10 | /40 |
| 方案C | /10 | /10 | /10 | /10 | /40 |

## 详细分析
### 方案A
- 优点: 
- 缺点: 

### 方案B
- 优点: 
- 缺点: 

## 推荐方案
[选择最佳方案并说明理由]

## 置信度
[0-100]%""",

    ReasonMode.ESTIMATE: """对以下问题进行**估算推演**：

**问题**: {question}
**上下文**: {context}

## 假设条件
1. 
2. 
3. 

## 计算过程
### 步骤1: 
计算公式: 
计算结果: 

### 步骤2: 
计算公式: 
计算结果: 

## 估算范围
- 最乐观: 
- 最可能: 
- 最悲观: 

## 最终估算
[给出数值或范围]

## 置信度
[0-100]%""",

    ReasonMode.COMPARE: """对以下问题进行**对比分析**：

**问题**: {question}
**上下文**: {context}

## 对比维度
| 维度 | 选项A | 选项B | 选项C |
|------|-------|-------|-------|
| 维度1 | | | |
| 维度2 | | | |
| 维度3 | | | |

## 详细分析
### 选项A
- 优势:
- 劣势:

### 选项B
- 优势:
- 劣势:

## 结论
[对比总结与推荐]

## 置信度
[0-100]%""",

    ReasonMode.PLAN: """基于分析结果生成**可执行行动计划**：

**目标**: {question}
**上下文**: {context}

## 阶段1: [准备阶段]
- [ ] 任务1.1: [具体行动] — 预计耗时: 
- [ ] 任务1.2: [具体行动] — 预计耗时: 

## 阶段2: [执行阶段]
- [ ] 任务2.1: [具体行动] — 预计耗时: 
- [ ] 任务2.2: [具体行动] — 预计耗时: 

## 阶段3: [验证阶段]
- [ ] 任务3.1: [验收标准] — 预计耗时: 
- [ ] 任务3.2: [回滚方案] — 条件: 

## 风险点
1. [风险] → 应对: 
2. [风险] → 应对: 

## 总耗时: [估算]

## 置信度
[0-100]%""",
}


class DeepReasoner:
    """深度推理引擎 — 调用LLM真实算力进行全方位结构化推理"""

    def __init__(self, llm, tool_registry=None):
        self.llm = llm  # GBTLLM
        self.tools = tool_registry
        self._history: deque = deque(maxlen=50)  # 最多保留最近50条历史，防止无限增长

    def reason(self, question: str, mode: ReasonMode = ReasonMode.CHAIN,
               context: str = "", tool_hints: List[str] = None,
               **kwargs) -> ReasonResult:
        """全方位深度推理"""
        t0 = time.time()
        print(f"\n[DeepReason] [{mode.value}]: {question[:80]}...")

        # 1. 构建推理提示
        prompt = REASON_PROMPTS[mode].format(
            question=question, context=context or "无额外上下文")

        # 2. 如果有工具，先收集信息
        evidence = []
        if self.tools and tool_hints:
            for hint in tool_hints:
                try:
                    result = self.tools.execute(hint, question[:200])
                    if result and "❌" not in result:
                        evidence.append(result[:500])
                except Exception as e:
                    L.warning(f"证据收集工具执行失败 [{hint}]: {e}")

        if evidence:
            context += "\n\n## 工具收集的证据\n" + "\n".join(evidence)

        # 3. LLM深度推理
        messages = [
            {"role": "system", "content": "你是一位深度推理专家。请使用完整的计算和推理能力分析问题。"},
            {"role": "user", "content": prompt}
        ]
        raw = self.llm.invoke(messages, temperature=0.3, max_tokens=4096, **kwargs)

        # 4. 解析结果
        conclusion, confidence, plan = self._parse(raw, mode)
        nodes = self._build_nodes(raw, mode)

        result = ReasonResult(
            mode=mode, question=question, nodes=nodes,
            conclusion=conclusion, plan=plan,
            confidence=confidence, duration=time.time()-t0, raw=raw
        )

        self._history.append(result)
        print(f"  [OK] reasoning complete | confidence:{confidence:.0%} | {result.duration:.1f}s")
        return result

    def multi_reason(self, question: str,
                     modes: List[ReasonMode] = None,
                     context: str = "", **kwargs) -> List[ReasonResult]:
        """多模式交叉推理 — 从多个角度分析同一问题"""
        if modes is None:
            modes = [ReasonMode.CHAIN, ReasonMode.TREE, ReasonMode.SWOT]
        results = []
        for mode in modes:
            r = self.reason(question, mode, context, **kwargs)
            results.append(r)
        # 取最高置信度作为综合建议（空列表时安全返回 None 而非崩溃）
        if not results:
            print("  [WARN] no reasoning results")
            return results
        best = max(results, key=lambda x: x.confidence)
        print(f"\n  [BEST] best reasoning: {best.mode.value} (confidence {best.confidence:.0%})")
        return results

    def reason_and_plan(self, question: str, context: str = "",
                        **kwargs) -> ReasonResult:
        """推理+规划 — 先分析再生成可执行计划"""
        # 第一步: 链式推理
        r1 = self.reason(question, ReasonMode.CHAIN, context, **kwargs)
        # 第二步: 基于推理结果生成计划
        plan_context = f"{context}\n\n## 推理结论\n{r1.conclusion}"
        return self.reason(question, ReasonMode.PLAN, plan_context, **kwargs)

    def pipeline_reason(self, question: str, context: str = "",
                        **kwargs) -> Tuple[ReasonResult, ReasonResult, ReasonResult]:
        """完整推理管道: 根因分析 → 决策 → 计划"""
        rc = self.reason(question, ReasonMode.ROOT_CAUSE, context, **kwargs)
        ctx2 = f"{context}\n根因: {rc.conclusion}"
        dec = self.reason(question, ReasonMode.DECISION, ctx2, **kwargs)
        ctx3 = f"{ctx2}\n决策: {dec.conclusion}"
        plan = self.reason(question, ReasonMode.PLAN, ctx3, **kwargs)
        return rc, dec, plan

    def _parse(self, raw: str, mode: ReasonMode) -> Tuple[str, float, List[str]]:
        # 提取结论
        conclusion = ""
        for tag in ["## 最终答案", "## 综合结论", "## 根本原因",
                     "## 推荐方案", "## 最终估算", "## 结论"]:
            m = re.search(f"{tag}\\s*\\n(.*?)(?=\\n##|$)", raw, re.DOTALL)
            if m:
                conclusion = m.group(1).strip()
                break
        conclusion = conclusion or raw[-500:]

        # 提取置信度
        conf = 0.5
        m = re.search(r"置信度[：:]\s*(\d+)", raw)
        if m: conf = int(m.group(1)) / 100

        # 提取计划
        plan = []
        for line in raw.split("\n"):
            if re.match(r"^\d+\.\s", line) or line.strip().startswith("- ["):
                plan.append(line.strip())

        return conclusion, conf, plan

    def _build_nodes(self, raw: str, mode: ReasonMode) -> List[ReasonNode]:
        nodes = []
        if mode == ReasonMode.CHAIN:
            steps = re.findall(r"## 第(\d+)步: (.+?)\n(.*?)(?=## 第|\Z)", raw, re.DOTALL)
            for i, (num, label, content) in enumerate(steps):
                nodes.append(ReasonNode(id=f"s{num}", depth=i+1,
                    label=label.strip(), content=content.strip()))
        elif mode == ReasonMode.TREE:
            root_m = re.search(r"## 根节点: (.+?)\n(.+?)(?=###|\Z)", raw, re.DOTALL)
            if root_m:
                root = ReasonNode(id="root", depth=0,
                    label=root_m.group(1).strip(),
                    content=root_m.group(2).strip())
                branches = re.findall(r"### 分支\d+: (.+?)\n(.*?)(?=###|##)", raw, re.DOTALL)
                for i, (bl, bc) in enumerate(branches):
                    br = ReasonNode(id=f"b{i+1}", depth=1,
                        label=bl.strip(), content=bc.strip())
                    root.children.append(br)
                nodes.append(root)
        return nodes

    def get_history(self) -> List[ReasonResult]:
        """返回历史列表副本"""
        return list(self._history)

    def clear_history(self):
        self._history.clear()


# ── 沙盒验证闭环 ──

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("[TEST] reasoner.py sandbox verification")
    print("=" * 60)

    errors: List[str] = []

    # ------------------------------------------------------------------
    # 1. 验证 8 种推理模式 template 都能正常渲染
    # ------------------------------------------------------------------
    print("\n[1] 8 reasoning mode template rendering")
    test_question = "如何优化交易策略？"
    test_context = "市场波动率上升"
    all_modes = list(ReasonMode)
    missing_keys = set()

    for mode in all_modes:
        try:
            tmpl = REASON_PROMPTS.get(mode)
            assert tmpl is not None, f"缺少 {mode} 的模板"
            rendered = tmpl.format(question=test_question, context=test_context)
            assert test_question in rendered, f"{mode.value} 模板未包含 question"
            assert test_context in rendered, f"{mode.value} 模板未包含 context"
            assert len(rendered) > 100, f"{mode.value} 模板渲染结果过短"
            print(f"  [OK] {mode.value:12s} - rendered ({len(rendered)} chars)")
        except KeyError as e:
            missing_keys.add(str(e))
            print(f"  [FAIL] {mode.value:12s} - missing placeholder: {e}")
            errors.append(f"{mode.value}: 模板占位符缺失 {e}")
        except Exception as e:
            print(f"  [FAIL] {mode.value:12s} - exception: {e}")
            errors.append(f"{mode.value}: {e}")

    if missing_keys:
        errors.append(f"模板缺少占位符: {missing_keys}")
    assert len(all_modes) == 8, f"ReasonMode 应为 8 种，实际 {len(all_modes)} 种"
    print(f"  [OK] ReasonMode has {len(all_modes)} modes (CHAIN / TREE / SWOT / "
          f"ROOT_CAUSE / DECISION / ESTIMATE / COMPARE / PLAN）")

    # ------------------------------------------------------------------
    # 2. 验证 _history 截断正常工作（deque maxlen=50）
    # ------------------------------------------------------------------
    print("\n[2] _history truncation (maxlen=50)")

    class _MockLLM:
        def invoke(self, messages, **kw):
            return "## 最终答案\n测试结论。\n\n## 置信度\n85"

    dr = DeepReasoner(_MockLLM())
    # 不依赖真实 LLM：直接构造 ReasonResult 填入 history 测试 deque 截断
    for i in range(60):
        dr._history.append(ReasonResult(
            mode=ReasonMode.CHAIN,
            question=f"Q{i}",
            conclusion=f"结论{i}",
            confidence=0.8,
            duration=0.1,
        ))

    hist = dr.get_history()
    assert len(hist) == 50, f"期望 50，实际 {len(hist)}"
    assert hist[0].question == "Q10", f"最早应为 Q10，实际 {hist[0].question}"
    assert hist[-1].question == "Q59", f"最晚应为 Q59，实际 {hist[-1].question}"
    print(f"  [OK] 60 writes -> keeps latest 50, earliest: {hist[0].question}, latest: {hist[-1].question}")

    dr.clear_history()
    assert len(dr.get_history()) == 0, "clear_history 后应空"
    print("  [OK] clear_history works")

    # ------------------------------------------------------------------
    # 3. 验证空输入安全返回
    # ------------------------------------------------------------------
    print("\n[3] empty input safe return")

    # 空 question
    empty_result = dr.reason("", ReasonMode.CHAIN, "")
    assert empty_result.question == "", "空 question 应保留"
    assert empty_result.mode == ReasonMode.CHAIN
    assert empty_result.duration >= 0
    print("  [OK] reason('') safely returns ReasonResult")

    # 空 context
    r2 = dr.reason("测试", ReasonMode.SWOT, "")
    assert r2.question == "测试"
    print("  [OK] empty context safe")

    # multi_reason 空 modes 列表
    empty_modes: List[ReasonMode] = []
    mr = dr.multi_reason("测试", modes=empty_modes)
    assert mr == [], f"空 modes 应返回空列表，实际: {mr}"
    print("  [OK] multi_reason(modes=[]) returns empty list")

    # ------------------------------------------------------------------
    # 4. 验证 max() 不崩溃
    # ------------------------------------------------------------------
    print("\n[4] max() empty list does not crash")

    # 构造一个空列表直接验证 max 保护逻辑
    test_empty: List[ReasonResult] = []
    try:
        if test_empty:
            _ = max(test_empty, key=lambda x: x.confidence)
            print("  [OK] non-empty list max works")
        else:
            print("  [OK] empty list guarded, max() not called")
    except ValueError as e:
        errors.append(f"max() 空列表崩溃: {e}")
        print(f"  [FAIL] max() crashed: {e}")

    # 通过 multi_reason 空 modes 再次验证
    dr2 = DeepReasoner(_MockLLM())
    result = dr2.multi_reason("测试", modes=[])
    assert result == [], "multi_reason 空 modes 应返回 []"
    print("  [OK] multi_reason empty modes returns [] (max not called)")

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    if errors:
        print(f"[FAIL] verification failed ({len(errors)} items):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("[PASS] All checks passed: 8 templates | _history truncation | empty input safety | max() safe")
        sys.exit(0)
