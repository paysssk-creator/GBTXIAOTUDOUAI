# -*- coding: utf-8 -*-
"""
镜像多维度空间 — AI 思维导图链路指引
从开源仓库思维导图中提取精细化操作指引, 注入 pipeline 各阶段
"""
import os

MINDMAP_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "docs", "superpowers", "mindmap")

# ══════════════════════════════════════════════════════════
#  Pipeline 阶段 → 思维导图映射
# ══════════════════════════════════════════════════════════

PIPELINE_GUIDES = {
    "scan": {
        "title": "🔍 全量扫描 — 纯度检查思维导图",
        "principle": """
纯度检查原则:
1. 每一个文件都是生产代码 — 拒绝 TODO/FIXME/占位符
2. 硬编码密钥 = 致命漏洞 — 零容忍
3. eval/exec/os.system = 高危操作 — 必须有合理理由
4. 裸 except = 隐藏 bug — 必须明确异常类型
5. 语法错误 = 不可部署 — 编译必须通过
        """,
        "checklist": [
            "🚨 硬编码密钥: API_KEY / password / token / secret 明文",
            "⚠️ 危险函数: eval() / exec() / os.system() / shell=True",
            "📌 占位符: TODO / FIXME / HACK / NotImplementedError",
            "🎭 假数据: test / placeholder / mock / dummy / fake / xxx",
            "🐍 语法错误: py_compile 全量编译检查",
            "🕳️ 空实现: pass 函数体 / return None 占位",
        ],
        "source": "gbt/mirror.py + gbt/guard.py",
    },

    "audit": {
        "title": "🔐 深度审计 — 架构审计思维导图",
        "principle": """
双轮驱动审计框架 (ARCHITECTURE_AUDIT_DUAL_WHEEL):
- 正向飞轮 L1→L5: 数据→模型→工程→应用→商业化 五层覆盖
- 逆向降维 L5→L1: 商业价值→应用体验→工程质量→模型选型→数据质量

审计关注点:
1. 敏感文件泄露 (.env/.key/.pem 不应在仓库中)
2. .gitignore 规则完整性 (确保敏感文件不会被提交)
3. 未跟踪的敏感文件 (git ls-files --others)
4. 配置文件完整性 (.env.example/pyproject.toml/requirements.txt)
        """,
        "checklist": [
            "🔑 敏感文件扫描: .env / .pem / .key / credentials / .db / .sqlite",
            "📋 .gitignore 规则: 检查 8 条必要规则是否完备",
            "🕵️ 未跟踪文件: git ls-files --others 检查泄露",
            "📦 配置文件: .env.example / pyproject.toml / requirements.txt",
        ],
        "source": "ARCHITECTURE_AUDIT_DUAL_WHEEL.md",
    },

    "fix": {
        "title": "🔧 沙盒修复 — 镜像空间修复思维导图",
        "principle": """
沙盒修复原则 (MirrorSpace):
1. 克隆 → 修复 → 验证 → 部署, 绝不直接修改源文件
2. 语法验证通过才部署, 不通过自动回滚
3. 裸 except → except Exception as e (可自动修复)
4. shell=True → shell=False (可自动修复)
5. 仅修复确定安全的模式, 危险模式只报告

Agent 循环 (agent-loop.mmd):
  Context管理 → Pre-hook → LLM推理 → tool_use决策
  → 权限检查 → 工具执行 → Post-hook → Token预算检查
  → 继续或完成
        """,
        "checklist": [
            "🪞 创建镜像: shutil.copytree → 临时目录",
            "🔧 自动修复: bare except / shell=True 模式替换",
            "✅ 语法验证: compile() 全量编译检查",
            "🚀 原子部署: shutil.copy2 逐文件回写",
            "🧹 清理镜像: shutil.rmtree 删除临时文件",
        ],
        "source": "gbt/mirror.py + mindmap/agent-loop.mmd",
    },

    "dimensions": {
        "title": "🎯 四维度测试 — 能力全景思维导图",
        "principle": """
四维度评估框架 (XIAOTUDOU_CAPABILITY_MAP):
- 👤 用户视角: 入口可用性 + 文档完整性 + CLI 可用性
- 💻 开发者视角: 代码质量 + docstring 覆盖率 + 模块解耦
- ⚙️ 运维视角: Docker 支持 + 日志系统 + 健康检查
- 🛡️ 安全视角: eval/exec 使用 + 密钥管理 + 依赖安全

铁律 (Iron Laws):
1. 指令 = 行动。收到指令 → 解析 → 执行 → 交结果。
2. 80% 确定就出手。等 100% 确定，机会早没了。
3. 执行时入定：关闭情绪，全神贯注，一击必中。
4. 闭环跑通才是真功夫：想到→尝试→跑通→验证→闭环。
        """,
        "checklist": [
            "👤 用户: 入口文件存在 / README 文档 / CLI 参数完整",
            "💻 开发者: docstring 覆盖率 / 代码一致性 / 循环依赖",
            "⚙️ 运维: Dockerfile / docker-compose / logging 模块",
            "🛡️ 安全: eval/exec 使用 / 密钥硬编码 / 依赖漏洞",
        ],
        "source": "XIAOTUDOU_CAPABILITY_MAP.md + docs/superpowers",
    },

    "full": {
        "title": "🚀 完整管道 — 镜像多维度空间全景思维导图",
        "principle": """
镜像多维度空间全景:
                    Purity Gate → Design Brain → Pipeline
                         ↓              ↓            ↓
                    纯度检查         设计蓝图      一条龙部署
                         ↓              ↓            ↓
                      Ticket  ────  Billing  ────  Audit
                     票据验签        计费          审计

六子系统联动:
1. Purity Gate: 代码纯度检查, 拒绝虚假代码
2. Design Brain: 思维导图扩展器, AI 生成设计方案
3. Pipeline: Agent 循环执行, 工具调用 + 权限检查
4. Ticket: 票据验签, 确保操作授权
5. Billing: 计费模块, $1/次
6. Audit: 审计跟踪, 所有操作可追溯
        """,
        "checklist": [
            "Stage 1 全量扫描: 纯度检查, 10种危险模式 + 11种虚假代码",
            "Stage 2 分类统计: 按类型归类, 生成优先级清单",
            "Stage 3 深度审计: 敏感文件 + .gitignore + 未跟踪风险",
            "Stage 4 沙盒修复: 镜像→扫描→修复→验证→部署",
            "Stage 5 语法验证: compile() 全量编译检查",
            "Stage 6 四维度测试: 用户/开发者/运维/安全评分",
            "Stage 7 原子部署: 通过验证后一键部署回源",
        ],
        "source": "mirror_dimension + ARCHITECTURE_AUDIT_DUAL_WHEEL + XIAOTUDOU_CAPABILITY_MAP",
    },
}


def get_guide(mode: str) -> dict:
    """获取指定模式的思维导图指引"""
    return PIPELINE_GUIDES.get(mode, PIPELINE_GUIDES["full"])


def get_prompt_prefix(mode: str) -> str:
    """生成 AI prompt 前缀 — 注入思维导图作为精细链路指引"""
    guide = get_guide(mode)
    lines = [
        f"## {guide['title']}",
        "",
        "### 核心原则",
        guide["principle"].strip(),
        "",
        "### 操作清单",
    ]
    for i, item in enumerate(guide["checklist"], 1):
        lines.append(f"{i}. {item}")
    lines.append("")
    lines.append(f"--- 参照: {guide['source']}")
    return "\n".join(lines)


def get_all_guides() -> dict:
    """获取所有阶段的思维导图指引"""
    return PIPELINE_GUIDES


# ══════════════════════════════════════════════════════════
#  Mermaid 流程图 (可在支持的 Markdown 查看器中渲染)
# ══════════════════════════════════════════════════════════

MIRROR_DIMENSION_MERMAID = """flowchart TB
    subgraph INPUT["输入"]
        A[项目路径]
    end

    subgraph SCAN["Stage 1-2: 纯度检查"]
        B1[全量扫描]
        B2[分类统计]
        B1 --> B2
    end

    subgraph AUDIT["Stage 3: 架构审计"]
        C1[敏感文件扫描]
        C2[.gitignore 检查]
        C3[未跟踪文件]
        C1 --> C2 --> C3
    end

    subgraph FIX["Stage 4-5: 沙盒修复"]
        D1[创建镜像]
        D2[自动修复]
        D3[语法验证]
        D1 --> D2 --> D3
        D3 -->|失败| D4[回滚]
        D3 -->|通过| D5[原子部署]
    end

    subgraph DIMS["Stage 6: 四维度测试"]
        E1[用户视角]
        E2[开发者视角]
        E3[运维视角]
        E4[安全视角]
    end

    subgraph DEPLOY["Stage 7: 交付"]
        F1[综合判定]
        F2[报告生成]
        F1 --> F2
    end

    A --> SCAN
    SCAN --> AUDIT
    AUDIT --> FIX
    FIX --> DIMS
    DIMS --> DEPLOY

    classDef scan fill:#eef,stroke:#66c,color:#224
    classDef audit fill:#fee,stroke:#c66,color:#422
    classDef fix fill:#efe,stroke:#6a6,color:#242
    classDef dims fill:#eff,stroke:#6cc,color:#244
    classDef deploy fill:#ffe,stroke:#cc6,color:#442

    class B1,B2 scan
    class C1,C2,C3 audit
    class D1,D2,D3,D4,D5 fix
    class E1,E2,E3,E4 dims
    class F1,F2 deploy
"""

AGENT_LOOP_MERMAID = """flowchart TB
    START((输入)) --> CTX["Context 管理"]
    CTX --> PRE["Pre-sampling Hook"]
    PRE --> LLM["LLM 流式输出"]
    LLM --> TC{tool_use?}
    TC -->|是| PERM{需权限?}
    PERM -->|是| USER["👤 用户审批"]
    USER -->|allow| TOOL_PRE["Pre-tool Hook"]
    USER -->|deny| DENIED["拒绝"]
    PERM -->|否| TOOL_PRE
    TOOL_PRE --> EXEC["并发执行工具"]
    EXEC --> TOOL_POST["Post-tool Hook"]
    TOOL_POST --> CTX
    DENIED --> CTX
    TC -->|否| POST["Post-sampling Hook"]
    POST --> STOP{"Stop Hook"}
    STOP -->|不通过| CTX
    STOP -->|通过| BUDGET{"Token Budget"}
    BUDGET -->|继续| CTX
    BUDGET -->|完成| DONE((完成))
"""

DUAL_WHEEL_MERMAID = """flowchart LR
    subgraph FW["正向飞轮 L1→L5"]
        L1[L1 数据] --> L2[L2 模型]
        L2 --> L3[L3 工程]
        L3 --> L4[L4 应用]
        L4 --> L5[L5 商业化]
    end
    subgraph BW["逆向降维 L5→L1"]
        R5[L5 价值] --> R4[L4 体验]
        R4 --> R3[L3 质量]
        R3 --> R2[L2 选型]
        R2 --> R1[L1 质量]
    end
    FW -.->|审计| BW
"""
