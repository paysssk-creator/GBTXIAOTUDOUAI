# GBT 多功能思维导图索引
## MindMap Index — 镜像多维度空间

> 收集自 paysssk-creator 开源仓库，集成多维度思维导图 + 架构蓝图 + 设计文档
> 开发者：自由的风 | 集成日期：2026-07-01

---

## 📊 思维导图全景

```
                        ┌─────────────────────────┐
                        │    GBT 小土豆 AI 大脑     │
                        │    (GBT-brain)           │
                        │    mindmap_extender.py   │
                        └───────────┬─────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  设计大脑        │     │  镜像多维度空间   │     │  原生引擎        │
│  Design Brain   │     │  Mirror Space    │     │  Native Engine  │
│                 │     │                 │     │                 │
│ 蓝图 + 票据     │     │ 门禁 + 纯度检查  │     │ 蓝图架构         │
│ 门禁体系        │     │ Canary + 回滚    │     │ (Blueprint)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Agent Loop      │  │  Spider 架构      │  │  能力地图         │
│  (Mermaid)       │  │  Scrapling        │  │  Capability Map  │
│  agent-loop.mmd  │  │  spider_arch.png  │  │  32KB 能力矩阵    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 🗂️ 文件清单

### 🔵 思维导图引擎 (2 个)
| 文件 | 类型 | 来源 | 大小 |
|------|------|------|:--:|
| `mindmap_extender.py` | Python 思维导图扩展器 | GBT-brain | 6.4KB |
| `mindmap_engine.ts` | TypeScript 思维导图引擎 | GBTxiaotudouchuangzaozhushou | 5.0KB |

### 🟢 架构设计文档 (4 个)
| 文件 | 内容 | 来源 | 大小 |
|------|------|------|:--:|
| `APP_FRAMEWORK_DESIGN.md` | 应用框架设计 | GBTxiaotudouchuangzaozhushou | 6.4KB |
| `DESIGN_REFACTOR.md` | 设计重构方案 | GBTxiaotudouchuangzaozhushou | 5.7KB |
| `ARCHITECTURE_COMPARISON.md` | 架构方案对比 | xiaotudou-benyuan | 11.0KB |
| `NATIVE_ARCHITECTURE_SUMMARY.md` | 原生架构完成摘要 | xiaotudou-benyuan | 13.5KB |

### 🟠 蓝图 & 路线图 (4 个)
| 文件 | 内容 | 来源 | 大小 |
|------|------|------|:--:|
| `NATIVE_ENGINE_BLUEPRINT.md` | 原生引擎蓝图 | xiaotudou-benyuan | 14.2KB |
| `IMPLEMENTATION_ROADMAP.md` | 实施路线图 | xiaotudou-benyuan | 12.7KB |
| `Scrapling_ROADMAP.md` | Scrapling 路线图 | Scrapling | 1.1KB |
| `spider_architecture.png` | Spider 架构图 | Scrapling | 126.7KB |

### 🟣 能力 & 流程 (2 个)
| 文件 | 内容 | 来源 | 大小 |
|------|------|------|:--:|
| `XIAOTUDOU_CAPABILITY_MAP.md` | 小土豆能力全景地图 | xiaotudou-benyuan | 32.1KB |
| `agent-loop.mmd` | Agent 循环流程图 (Mermaid) | claude-code | 1.2KB |

---

## 🔗 与镜像多维度空间的关系

```
设计规格 (specs/2026-06-30-镜像多维度空间-...)
    │
    ├── §5 Design Brain  ←── mindmap_extender.py（思维导图扩展器）
    ├── §6 Pipeline      ←── agent-loop.mmd（Agent 循环流程）
    ├── §7 Contract Gate  ←── ARCHITECTURE_COMPARISON.md
    ├── §11 交付物        ←── NATIVE_ENGINE_BLUEPRINT.md
    └── §1 铁律           ←── APP_FRAMEWORK_DESIGN.md
```

---

## 🚀 如何使用

1. **思维导图扩展**: `python mindmap/mindmap_extender.py` — 自动从代码生成思维导图节点
2. **TypeScript 引擎**: `npx ts-node mindmap/mindmap_engine.ts` — 可视化思维导图渲染
3. **Mermaid 流程图**: 在支持 Mermaid 的 Markdown 查看器中打开 `mindmap/agent-loop.mmd`
4. **能力地图**: 查看 `XIAOTUDOU_CAPABILITY_MAP.md` 了解全部能力矩阵
5. **架构图**: 直接打开 `spider_architecture.png`

---

## 📁 目录结构

```
GBTXIAOTUDOUAI/docs/superpowers/
├── specs/
│   └── 2026-06-30-镜像多维度空间-必经之路-门禁计费-设计大脑-设计规格.md
├── mindmap/
│   ├── INDEX.md                              ← 本文件
│   ├── mindmap_extender.py                   ← Python 扩展器
│   ├── mindmap_engine.ts                     ← TypeScript 引擎
│   ├── APP_FRAMEWORK_DESIGN.md
│   ├── DESIGN_REFACTOR.md
│   ├── ARCHITECTURE_COMPARISON.md
│   ├── NATIVE_ARCHITECTURE_SUMMARY.md
│   ├── NATIVE_ENGINE_BLUEPRINT.md
│   ├── IMPLEMENTATION_ROADMAP.md
│   ├── Scrapling_ROADMAP.md
│   ├── XIAOTUDOU_CAPABILITY_MAP.md
│   ├── spider_architecture.png
│   └── agent-loop.mmd
├── ARCHITECTURE_AUDIT_DUAL_WHEEL.md          ← 🆕 双轮驱动架构审计
└── (未来可扩展: blueprint.html, design.spec.json, design.ticket, deploy.ticket)
```
