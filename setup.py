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
        "openai>=1.0",
        "requests>=2.31",
        "python-dotenv>=1.0",
        "ollama>=0.4",
        "Pillow>=10.0",
        "pyautogui>=0.9",
        "pyttsx3>=2.90",
        "SpeechRecognition>=3.10",
        "pyperclip>=1.8",
        "psutil>=5.9",
    ],
    extras_require={
        "full": [
            "flask>=3.0",
            "tesserocr>=2.6",
            "easyocr>=1.7",
            "opencv-python>=4.8",
            "screeninfo>=0.8",
            "pycaw>=20230407",
            "bleak>=0.21",
            "win10toast>=0.9",
        ],
        "desktop": [
            "flask>=3.0",
            "screeninfo>=0.8",
            "pycaw>=20230407",
            "win10toast>=0.9",
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
