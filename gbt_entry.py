"""GBT 打包入口 — 顶层显式 import，PyInstaller 追踪依赖链"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 标准库
import json, time, threading, logging, re, base64, hashlib
import sqlite3, asyncio, subprocess, urllib, ssl, webbrowser
import tempfile, shutil, platform, pathlib, ctypes
import socket, email, xml, uuid, struct, math, random
import csv, io, textwrap, string, copy, inspect, traceback
import functools, itertools, collections, dataclasses, enum, abc
import typing, contextlib, concurrent, queue, selectors, http
import statistics, weakref, pprint, binascii, shlex
import datetime, contextvars, multiprocessing

# 第三方库
import openai
import ollama
import tiktoken
import httpx
import pydantic
import PIL
import pyautogui
import pyperclip
import psutil
import pyttsx3
import speech_recognition
import flask
import requests
import dotenv
import numpy
import cv2

# GBT 全家桶
import gbt
import gbt.llm
import gbt.providers
import gbt.router
import gbt.reasoner
import gbt.guard
import gbt.evolve
import gbt.mirror
import gbt.mcp
import gbt.winctl
import gbt.desktop_ctl
import gbt.trader
import gbt.strategies
import gbt.tech_analysis
import gbt.scraper
import gbt.backtest
import gbt.risk_ctrl
import gbt.screen_ai
import gbt.agent
import gbt.agents
import gbt.react
import gbt.autopilot
import gbt.memory
import gbt.knowledge_base
import gbt.database
import gbt.protocol
import gbt.watcher
import gbt.watcher_agent
import gbt.account
import gbt.capabilities
import gbt.tool
import gbt.message
import gbt.cloud_kv
import gbt.keydb
import gbt.llm_metrics
import gbt.ocr
import gbt.paper_account
import gbt.setup_glm4v

print("GBT 全家桶 v1.5.1 — ALL MODULES OK")
sys.exit(0)
