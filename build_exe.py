"""
GBT — 专业级 PyInstaller 打包脚本
生成: GBT.exe (桌面原生应用, 带原生窗口 / --browser Web模式)
"""
import os, sys, shutil, subprocess

PROJECT = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(PROJECT, "dist", "GBT")

# ── 清理旧构建 ──
for d in ["build", "dist"]:
    p = os.path.join(PROJECT, d)
    if os.path.exists(p):
        shutil.rmtree(p)
        print(f"Clean: {p}")

# ── PyInstaller 命令 ──
pyinstaller_args = [
    "pyinstaller",
    "--name=GBT",
    "--onedir",                     # 目录打包 (体积小, 启动快, 更可靠)
    "--console",                    # 控制台模式 (窗口+日志, --browser 终端输出)
    "--icon=desktop/GBT.ico",        # GBT专业图标
    "--distpath=" + os.path.join(PROJECT, "dist"),
    "--workpath=" + os.path.join(PROJECT, "build"),
    "--specpath=" + PROJECT,
    # 隐藏系统导入避免打包体积膨胀
    "--exclude-module=tkinter",
    "--exclude-module=matplotlib",
    "--exclude-module=numpy",
    "--exclude-module=pandas",
    "--exclude-module=scipy",
    "--exclude-module=sounddevice", # 排除可能导致内存问题的音频模块
    "--exclude-module=dotenv",       # 已手动解析 .env，排除避免库内自动调用
    "--exclude-module=python_dotenv",
    # 显式包含所需模块 (自动检测之外的保证)
    "--hidden-import=flask",
    "--hidden-import=webview",
    "--hidden-import=dotenv",
    "--hidden-import=openai",
    "--hidden-import=ollama",
    "--hidden-import=psutil",
    "--hidden-import=pyautogui",
    # 添加数据文件 — templates 和图标
    "--add-data=desktop/templates;desktop/templates",
    "--add-data=desktop/GBT.ico;.",
    # 路径注入 - 确保代码能找到同级 .env 和模块
    "--collect-all=gbt",
    "--collect-all=agents",
    "--collect-all=tools",
    # 资源
    "--add-data=README.md;.",
    # 入口
    os.path.join(PROJECT, "desktop", "app.py"),
]

print("=" * 60)
print("  GBT v2.0 — 专业桌面客户端打包")
print("=" * 60)
print(f"  源目录: {PROJECT}")
print(f"  输出: {OUTPUT}.exe")
print("=" * 60)

result = subprocess.run(pyinstaller_args, cwd=PROJECT)
if result.returncode != 0:
    print(f"\nFAIL (code={result.returncode})")
    sys.exit(1)

print(f"\nBUILD OK!")
print(f"   输出: {os.path.join(PROJECT, 'dist', 'GBT', 'GBT.exe')}")
print(f"   大小: {os.path.getsize(os.path.join(PROJECT, 'dist', 'GBT', 'GBT.exe')) / 1024 / 1024:.1f} MB")
