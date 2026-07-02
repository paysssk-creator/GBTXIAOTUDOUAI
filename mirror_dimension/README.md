# 镜像多维度空间 v1.0

> AI 项目安全验证 & 沙盒修复工具 — 一键管道：扫描 → 审计 → 修复 → 四维度测试

## 安装

```bash
pip install -e .
# 或
pip install gbt-mirror-dimension
```

依赖：Python >= 3.10, Flask

## 快速开始

### 桌面 APP（推荐）

```bash
python mirror_dimension_app.py
# → 浏览器自动打开 Dashboard (http://127.0.0.1:8766)
```

或双击打包好的 `GBT_MirrorDimension.exe`

### CLI 模式

```bash
python mirror_dimension_cli.py scan /path/to/project
python mirror_dimension_cli.py audit /path/to/project
python mirror_dimension_cli.py fix /path/to/project --dry-run
python mirror_dimension_cli.py full /path/to/project -o report.json
```

### Python SDK

```python
from mirror_dimension import scan_project, audit_project, fix_project
from mirror_dimension import MirrorPipeline

# 全量扫描
result = scan_project("/path/to/project")
print(f"文件: {result['total_files']}, 隐患: {result['dangers']}")

# 完整管道
pipeline = MirrorPipeline("/path/to/project", dry_run=True)
report = pipeline.run()
print(f"判定: {report['verdict']}")
```

## 五种模式

| 模式 | 说明 | 检测内容 |
|------|------|---------|
| `scan` | 全量扫描 | 10种危险模式 + 11种虚假代码 + Python语法 |
| `audit` | 深度审计 | 敏感文件 + .gitignore缺口 + 未跟踪风险 |
| `fix` | 沙盒修复 | 裸except/shell=True自动修复 + 语法验证 + 原子部署 |
| `dimensions` | 四维度测试 | 用户/开发者/运维/安全 四视角评分 |
| `full` | 完整管道 | scan→audit→fix→dimensions 一键全跑 |

## 危险模式 (10种)

API_KEY硬编码 · password明文 · token泄露 · secret泄露 · OpenAI Key泄露
eval() · exec() · os.system() · shell=True · 裸except

## 虚假代码 (11种)

TODO占位 · FIXME占位 · HACK标记 · NotImplementedError · 空返回
test假数据 · placeholder假数据 · mock假数据 · dummy假数据 · fake假数据 · xxx假数据

## 思维导图

Dashboard 右下角 🧠 按钮 — 每个阶段都有对应的思维导图展示核心原则和操作清单。

## 构建

```bash
# 单文件 EXE
pip install pyinstaller
pyinstaller mirror_dimension.spec
# → dist/GBT_MirrorDimension.exe (~15MB, 独立可运行)

# 运行测试
pip install pytest
pytest tests/ -v
```

## 项目结构

```
mirror_dimension/
├── __init__.py       # SDK 入口
├── scanner.py        # 全量扫描引擎
├── auditor.py        # 深度审计引擎
├── fixer.py          # 沙盒修复引擎
├── dimensions.py     # 四维度测试引擎
├── pipeline.py       # 管道编排器
└── mindmap_guide.py  # AI 链路指引

mirror_dimension_app.py   # Flask Dashboard (专属APP)
mirror_dimension_cli.py   # CLI 入口
mirror_dimension.spec     # PyInstaller 构建配置
tests/                    # 测试
docs/superpowers/mindmap/ # 思维导图资源
```
