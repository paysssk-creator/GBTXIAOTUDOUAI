# 🧠 GBT AI Workstation v4 — 全能型 AI 智能体桌面应用

[![Version](https://img.shields.io/badge/version-v4.0.4-blue)](https://github.com/paysssk-creator/GBTXIAOTUDOUAI)
[![Python](https://img.shields.io/badge/python-3.12-green)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20Docker-blue)](https://github.com/paysssk-creator/GBTXIAOTUDOUAI)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)

> 以 **Nanobrowser** 为浏览器框架、**Cradle** 为电脑自主操控核心，融合 GBT 原有全部能力，打造的端对端全能 AI 智能体工作站。

## 🏗️ 架构

```
GBTXIAOTUDOUAI/
├── gbt/                    核心引擎 (40+ 模块)
│   ├── web_api.py          Web API / 现代仪表盘
│   ├── skills/             模块化能力目录 (借鉴 open-strix)
│   ├── dashboard.html      新版 Web 控制面板
│   ├── ai_operator.py      AI 设备操控总入口
│   ├── desktop_ctl.py      Windows 原生操控
│   ├── vision.py           AI 视觉 (截图 + OCR + 多模态)
│   ├── screen_ai.py        屏幕文字识别
│   ├── router.py           自然语言能力路由
│   ├── capabilities.py     19 项能力注册表
│   ├── providers.py        13 大模型配置
│   ├── trader.py           A 股交易引擎
│   ├── brain.py            自主 AI 大脑
│   ├── watcher.py          7×24 守夜人安全监控
│   ├── guard.py            行动前强制扫描
│   ├── mirror.py           镜像空间沙盒
│   ├── evolve.py           6 步自进化闭环
│   ├── mcp.py              万能 MCP 客户端
│   └── ...
├── agents/                 Agent 封装
├── tools/                  工具链
├── desktop/app.py          桌面启动器（旧 GUI + Web 双模式）
├── entry.py                v4 统一入口（自动打开 Web 面板）
├── Dockerfile              生产级多阶段 Docker 打包
├── docker-compose.yml      一键云端/本地部署
└── README.md               本文件
```

## 🚀 快速开始

### 1. 本地开发

```bash
# 克隆
git clone https://github.com/paysssk-creator/GBTXIAOTUDOUAI.git
cd GBTXIAOTUDOUAI

# 安装
pip install -e .

# 配置密钥
cp .env.example .env
# 编辑 .env 填入任意模型 API 密钥

# 启动 Web 工作台（自动打开浏览器面板）
python entry.py
```

### 2. Docker 部署

```bash
cp .env.example .env
# 编辑 .env
docker compose up -d
# → http://localhost:8765
```

### 3. 打包桌面 EXE

```bash
pip install pyinstaller
python build_exe.py
# 输出 dist/GBTWorkstation.exe
```

## 🌐 Web 控制面板

启动后访问 http://127.0.0.1:8765，新面板包含：

- **Command Center** — 自然语言输入，调用任意能力
- **AI Vision** — 一键截图 + OCR / 截图 + GLM-4V 多模态理解
- **Capabilities** — 19 项能力实时展示
- **System** — 服务状态、版本、一键重载

## 🧩 19 项核心能力

| 能力 | 说明 |
|------|------|
| 文件系统 | 读/写/搜索/压缩 |
| 浏览器控制 | 导航、点击、输入、提取 |
| 代码执行 | Python / Shell 沙盒执行 |
| 数据库 | SQLite / JSON 查询 |
| HTTP API | 任意 REST 调用 |
| 进程管理 | 启动、监控、结束 |
| Windows 操控 | 鼠标、键盘、窗口、热键 |
| AI 视觉 | 截图、OCR、多模态理解 |
| 语音交互 | TTS / 语音识别 |
| A 股交易 | 行情、分析、下单流程 |
| 数据分析 | Pandas / 图表 |
| 黑客工具集 | 扫描、枚举、信息收集 |
| MCP 客户端 | 18+ Server 即插即用 |
| 自进化 | 6 步闭环持续改进 |
| 镜像空间 | 沙盒 → 验证 → 部署 |
| 守夜人 | 7×24 安全监控 |
| 守卫 | 行动前全扫描 |
| 记忆系统 | 工作 / 情景 / 持久记忆 |
| 深度推理 | 8 模式推理引擎 |

## 📡 API 速查

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 控制面板 |
| `/api/health` | GET | 健康检查 |
| `/api/capabilities` | GET | 能力列表 |
| `/api/chat` | POST | 自然语言执行 |
| `/api/desk/observe` | POST | 截图+OCR |
| `/api/desk/act` | POST | 执行设备动作 |
| `/api/desk/run_task` | POST | 自主任务流 |
| `/api/hacker/exec` | POST | 黑客工具调用 |
| `/api/trade/analyze` | POST | 股票分析 |
| `/api/trade/execute` | POST | 股票执行 |

## 🧪 测试

```bash
# 端对端测试
python tests/e2e_smoke.py

# 压力测试
python tests/stress_test.py
```

## 📦 发布

```bash
# 构建 Docker 镜像
docker build -t ghcr.io/paysssk-creator/gbt-ai-workstation:v4.0.4 .

# 推送到 GitHub Container Registry
docker push ghcr.io/paysssk-creator/gbt-ai-workstation:v4.0.4
```

## 🙏 致谢

- [nanobrowser](https://github.com/paysssk-creator/nanobrowser) — 浏览器框架
- [Cradle](https://github.com/paysssk-creator/Cradle) — 电脑自主操控核心
- [openhuman](https://github.com/paysssk-creator/openhuman) — 打包与发布参考

## 📄 License

MIT © 2026 自由的风 (paysssk-creator)
