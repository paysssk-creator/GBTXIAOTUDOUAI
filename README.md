# ⚕ GBT小土豆全能开发者 — AI原生Agent框架

[![Version](https://img.shields.io/badge/version-1.5.1-blue)](https://github.com/paysssk-creator/GBT)
[![Python](https://img.shields.io/badge/python-3.10%2B-green)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-Windows-blue)](https://github.com/paysssk-creator/GBT)

> 一个AI原生的全能开发Agent框架，集成13大模型、18个MCP Server、8种深度推理模式、16类Windows原生操控能力。

## 🏗️ 架构

```
agent-framework/
├── gbt/                    核心引擎 (14模块, ~3500行)
│   ├── providers.py        13大模型配置 + 自主密钥发现
│   ├── llm.py              LLM统一抽象层 (OpenAI兼容)
│   ├── message.py          消息/历史/配置
│   ├── tool.py             工具注册表
│   ├── agent.py            SimpleAgent基类
│   ├── react.py            ReAct推理循环
│   ├── memory.py           记忆系统 (工作/情景/持久)
│   ├── evolve.py           6步自进化闭环引擎
│   ├── guard.py            行动前强制全扫描守卫
│   ├── mirror.py           镜像空间 (沙盒→验证→部署)
│   ├── mcp.py              万能MCP客户端 (18 Server)
│   ├── reasoner.py         深度推理引擎 (8模式)
│   ├── winctl.py           Windows原生操控 (16类)
│   └── ocr.py              图片转文字 (3引擎)
├── agents/gbt_agent.py     GBT全能开发者Agent
├── tools/mcp_tools.py      万能MCP工具注册
├── desktop/app.py          桌面APP (GUI + Web双模式)
└── main.py                 CLI入口
```

## 🚀 快速开始

```bash
# 安装
pip install -e .

# 配置密钥
cp .env.example .env
# 编辑.env填入任意模型API密钥

# CLI模式
python main.py

# 桌面APP (GUI)
python desktop/app.py

# Web API模式
python desktop/app.py --web
# → http://localhost:8765
```

## 🧠 13大模型

| 模型 | provider | 特点 |
|------|----------|------|
| 智谱 GLM-5.1 | zhipu | 国产最强 |
| OpenAI GPT-4o | openai | 全能 |
| DeepSeek V3 | deepseek | 推理强 |
| Claude 3.5 | anthropic | 安全 |
| Ollama本地 | ollama | 隐私 |
| 文心一言 | baidu | 中文 |
| 通义千问 | qwen | 阿里 |
| 月之暗面 | moonshot | 长文本 |
| 零一万物 | lingyi | 多模态 |
| 百川 | baichuan | 中文 |
| 讯飞星火 | xinghuo | 语音 |
| MiniMax | minimax | 对话 |
| 硅基流动 | siliconflow | 流式 |

## 🔧 核心能力

```python
from agents.gbt_agent import GBTAgent

agent = GBTAgent(provider="auto")

# 对话
agent.chat("分析这个项目")

# 深度推理 (8模式)
agent.deep_reason("如何优化？", mode="decision")

# 6步自进化闭环
agent.evolve("性能优化")

# 行动前守卫
agent.guard_scan()

# 镜像空间部署
agent.mirror_deploy()

# 万能MCP
agent.call_mcp("scanner")

# Windows操控
agent.winctl("screen", "capture")
agent.winctl("voice", "listen")

# OCR图片转文字
agent.winctl("ocr", "screen")
```

## 🛡️ 6步自进化闭环

1. **Step1 自查** → 行动前守卫全项目扫描 (零跳过)
2. **Step2 发现** → scanner.js安全扫描
3. **Step3 备份** → git自动备份
4. **Step4 修复** → auto-fix修复
5. **Step5 审查** → audit.js审查 (FAIL自动回滚)
6. **Step6 进化** → memory记录 + git提交

## 📦 依赖

- Python >= 3.10
- Ollama (可选, 本地模型)
- Tesseract (可选, OCR增强)
- Node.js (MCP Server)
- Git (版本控制)

## 📄 License

MIT © GBTxiaotudou
