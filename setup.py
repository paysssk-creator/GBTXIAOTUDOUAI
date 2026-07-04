"""GBT Agent Framework — AI原生全能开发框架"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="gbt-agent-framework",
    version="1.5.1",
    author="GBTxiaotudou",
    description="GBT全能开发者 — AI原生Agent框架",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/paysssk-creator/GBT",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        # === synced with requirements.txt v1.6 ===
        "openai>=1.0.0,<3.0.0",
        "python-dotenv>=1.0.0,<2.0.0",
        "requests>=2.31,<3.0.0",
        "flask>=3.0,<4.0.0",
        "aiohttp>=3.9",
        "psutil>=5.9,<7.0.0",
        "pyautogui>=0.9,<1.0.0",
        "pyperclip>=1.8,<2.0.0",
        "keyboard>=0.13",
        "Pillow>=10.0,<12.0.0",
        "edge-tts>=6.1",
        "SpeechRecognition>=3.10,<5.0.0",
        "pycaw>=20240210",
        "pyttsx3>=2.90,<3.0.0",
        "bleak>=0.21",
        "comtypes>=1.4",
        "pywin32>=306",
        "numpy>=1.26",
        "pandas>=2.2",
        "lxml>=5.2",
        "beautifulsoup4>=4.12",
    ],
    extras_require={
        "ocr": [
            "opencv-python>=4.8",
            "easyocr>=1.7",
            "pytesseract>=0.3",
        ],
        "browser": [
            "playwright>=1.45",
        ],
        "build": [
            "pyinstaller>=6.0",
            "build>=1.0",
            "twine>=5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "gbt=gbt.cli:main",
            "gbt-desktop=desktop.app:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
    ],
)
