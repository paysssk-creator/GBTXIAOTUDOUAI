# -*- coding: utf-8 -*-
"""
镜像多维度空间 — 专属桌面APP v1.0
═══════════════════════════════════════════════════
Flask + 内嵌 Dashboard (自包含)
打包: pyinstaller mirror_dimension.spec → dist/GBT_MirrorDimension.exe
"""
import os, sys, threading, time, webbrowser, socket

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if getattr(sys, "frozen", False):
    ROOT = os.path.dirname(sys.executable)
    if hasattr(sys, "_MEIPASS"):
        sys.path.insert(0, sys._MEIPASS)
else:
    ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from flask import Flask, render_template_string, jsonify, request

# ══════════════════════════════════════════════════════════
DASHBOARD_HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>镜像多维度空间</title>
<style>
:root{--bg0:#05080f;--bg1:#0c101a;--bg2:#131a28;--fg0:#e8ecf4;--fg1:#8899bb;--fg2:#4a5568;--accent:#a855f7;--accent2:#c084fc;--green:#22c55e;--red:#ef4444;--amber:#f59e0b;--blue:#3b82f6;--cyan:#06b6d4;--pink:#ec4899;--border:#1a2440}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI','PingFang SC',sans-serif;background:var(--bg0);color:var(--fg0);min-height:100vh;overflow-x:hidden}
#starfield{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none}
.scanline{position:fixed;top:0;left:0;width:100%;height:100%;z-index:1;pointer-events:none;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(168,85,247,.008) 2px,rgba(168,85,247,.008) 4px)}
.hdr{background:rgba(12,16,26,.92);backdrop-filter:blur(20px);padding:14px 28px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10;box-shadow:0 4px 30px rgba(168,85,247,.08)}
.hdr .brand{display:flex;align-items:center;gap:12px}
.hdr .logo{font-size:30px;filter:drop-shadow(0 0 12px rgba(168,85,247,.6));animation:logoFloat 3s ease-in-out infinite}
@keyframes logoFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
.hdr h1{font-size:20px;font-weight:800;background:linear-gradient(135deg,var(--accent2),var(--cyan),var(--accent2));background-size:200% 200%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:titleShimmer 3s ease infinite;letter-spacing:1px}
@keyframes titleShimmer{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.hdr .ver{font-size:10px;color:var(--fg2);margin-left:4px;padding:2px 8px;border:1px solid var(--border);border-radius:4px;letter-spacing:1px}
.hdr .status{font-size:11px;color:var(--fg1);display:flex;align-items:center;gap:8px}
.hdr .dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 12px var(--green),0 0 24px rgba(34,197,94,.4);animation:dotPulse 2s infinite}
@keyframes dotPulse{0%,100%{box-shadow:0 0 12px var(--green),0 0 24px rgba(34,197,94,.4)}50%{box-shadow:0 0 4px var(--green),0 0 8px rgba(34,197,94,.2)}}
.main{display:flex;height:calc(100vh - 58px);position:relative;z-index:2}
.nav{width:210px;background:rgba(12,16,26,.85);backdrop-filter:blur(12px);border-right:1px solid var(--border);padding:16px 0;flex-shrink:0}
.nav .ni{padding:12px 18px;cursor:pointer;font-size:12.5px;color:var(--fg1);border-left:3px solid transparent;transition:all .25s;display:flex;align-items:center;gap:10px;position:relative}
.nav .ni::before{content:'';position:absolute;left:0;top:0;height:100%;width:0;background:linear-gradient(90deg,rgba(168,85,247,.15),transparent);transition:width .3s}
.nav .ni:hover{color:var(--fg0);background:rgba(168,85,247,.05)}
.nav .ni:hover::before{width:100%}
.nav .ni.sel{color:var(--fg0);border-left-color:var(--accent);background:rgba(168,85,247,.1)}
.nav .ni .ico{font-size:17px;width:24px;text-align:center;transition:transform .3s}
.nav .ni:hover .ico{transform:scale(1.15)}
.nav .sep{border-top:1px solid var(--border);margin:10px 0}
.content{flex:1;overflow-y:auto;padding:24px 32px}
.content::-webkit-scrollbar{width:6px}
.content::-webkit-scrollbar-track{background:transparent}
.content::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.path-bar{display:flex;gap:12px;margin-bottom:28px;align-items:center}
.path-bar input{flex:1;background:rgba(19,26,40,.8);border:1px solid var(--border);color:var(--fg0);padding:11px 16px;border-radius:10px;font-size:13px;font-family:'Cascadia Code',monospace;outline:none;transition:all .3s}
.path-bar input:focus{border-color:var(--accent);box-shadow:0 0 20px rgba(168,85,247,.15)}
.path-bar input::placeholder{color:var(--fg2)}
.btn{padding:10px 20px;border:none;border-radius:10px;font-size:12px;font-weight:600;cursor:pointer;transition:all .25s;display:flex;align-items:center;gap:7px;position:relative;overflow:hidden}
.btn::after{content:'';position:absolute;top:50%;left:50%;width:0;height:0;border-radius:50%;background:rgba(255,255,255,.15);transform:translate(-50%,-50%);transition:width .6s,height .6s}
.btn:active::after{width:300px;height:300px}
.btn-primary{background:linear-gradient(135deg,var(--accent),#7c3aed);color:#fff;box-shadow:0 4px 20px rgba(168,85,247,.3)}
.btn-primary:hover{box-shadow:0 6px 30px rgba(168,85,247,.5);transform:translateY(-1px)}
.btn-outline{background:rgba(19,26,40,.6);border:1px solid var(--border);color:var(--fg0)}
.btn-outline:hover{border-color:var(--accent);box-shadow:0 0 15px rgba(168,85,247,.1)}
.btn:disabled{opacity:.4;cursor:not-allowed;transform:none!important;box-shadow:none!important}
.pipeline-wrap{position:relative;margin-bottom:28px}
.pipeline{display:flex;gap:0;background:rgba(12,16,26,.7);border:1px solid var(--border);border-radius:14px;overflow:hidden;position:relative}
.pipeline::before{content:'';position:absolute;top:0;left:0;width:100%;height:1px;background:linear-gradient(90deg,transparent,var(--accent),transparent);animation:scanLine 3s linear infinite}
@keyframes scanLine{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}
.pipe-step{flex:1;padding:18px 8px;text-align:center;position:relative;transition:all .4s;z-index:1}
.pipe-step:not(:last-child)::after{content:'';position:absolute;right:-10px;top:50%;width:20px;height:2px;background:var(--border);z-index:0;transition:all .5s}
.pipe-step .step-num{font-size:9px;color:var(--fg2);margin-bottom:6px;letter-spacing:2px;font-weight:700}
.pipe-step .step-icon{font-size:26px;margin-bottom:6px;opacity:.25;transition:all .5s;filter:grayscale(1)}
.pipe-step .step-name{font-size:10.5px;color:var(--fg2);transition:all .3s}
.pipe-step.active{background:rgba(168,85,247,.1)}
.pipe-step.active .step-icon{opacity:1;filter:grayscale(0);animation:iconBounce .6s ease}
.pipe-step.active .step-name{color:var(--accent2)}
.pipe-step.active:not(:last-child)::after{background:linear-gradient(90deg,var(--accent),var(--border))}
.pipe-step.done{background:rgba(34,197,94,.06)}
.pipe-step.done .step-icon{opacity:1;filter:grayscale(0)}
.pipe-step.done .step-name{color:var(--green)}
.pipe-step.done:not(:last-child)::after{background:var(--green)}
.pipe-step.fail{background:rgba(239,68,68,.06)}
.pipe-step.fail .step-icon{opacity:1;filter:grayscale(0);animation:iconShake .5s ease}
.pipe-step.fail .step-name{color:var(--red)}
@keyframes iconBounce{0%,100%{transform:scale(1)}40%{transform:scale(1.3)}60%{transform:scale(.9)}}
@keyframes iconShake{0%,100%{transform:translateX(0)}25%{transform:translateX(-4px)}75%{transform:translateX(4px)}}
.particle-stream{position:absolute;top:50%;height:2px;background:linear-gradient(90deg,transparent,var(--accent2),transparent);border-radius:2px;pointer-events:none;animation:streamFlow 2s ease infinite;opacity:.6}
@keyframes streamFlow{0%{left:-10%;width:20%}100%{left:100%;width:20%}}
.g2{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
.card{background:rgba(12,16,26,.6);border:1px solid var(--border);border-radius:12px;padding:18px;transition:all .35s;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;width:100%;height:100%;background:radial-gradient(circle at 30% 20%,rgba(168,85,247,.04),transparent 70%);pointer-events:none}
.card:hover{border-color:#2a3450;transform:translateY(-2px);box-shadow:0 8px 30px rgba(0,0,0,.3)}
.card .c-label{font-size:10px;color:var(--fg2);text-transform:uppercase;letter-spacing:2px;font-weight:600}
.card .c-value{font-size:32px;font-weight:800;margin:6px 0;transition:all .3s;background:linear-gradient(180deg,var(--fg0),var(--fg1));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.card .c-sub{font-size:10.5px;color:var(--fg2)}
.card.ok{border-left:3px solid var(--green);box-shadow:0 0 20px rgba(34,197,94,.08)}
.card.warn{border-left:3px solid var(--amber);box-shadow:0 0 20px rgba(245,158,11,.08)}
.card.err{border-left:3px solid var(--red);box-shadow:0 0 20px rgba(239,68,68,.08)}
.dim-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
.dim-card{background:rgba(12,16,26,.6);border:1px solid var(--border);border-radius:12px;padding:20px;transition:all .4s;position:relative;overflow:hidden}
.dim-card::after{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:conic-gradient(from 0deg,transparent,rgba(168,85,247,.03),transparent,rgba(6,182,212,.03),transparent);animation:dimRotate 8s linear infinite;pointer-events:none}
@keyframes dimRotate{to{transform:rotate(360deg)}}
.dim-card:hover{transform:perspective(500px) rotateY(2deg) scale(1.02);box-shadow:0 12px 40px rgba(0,0,0,.4)}
.dim-card .dim-title{font-size:13px;font-weight:700;margin-bottom:4px}
.dim-card .dim-score{font-size:42px;font-weight:900;margin:6px 0;transition:all .5s}
.dim-card .dim-bar{height:5px;border-radius:3px;margin-top:12px;background:rgba(255,255,255,.05);overflow:hidden}
.dim-card .dim-bar-fill{height:100%;border-radius:3px;transition:width .8s cubic-bezier(.4,0,.2,1);box-shadow:0 0 10px currentColor}
.results{background:rgba(12,16,26,.6);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:22px}
.results .res-hdr{padding:13px 20px;background:rgba(19,26,40,.6);font-size:12px;font-weight:700;display:flex;justify-content:space-between;align-items:center;letter-spacing:.5px}
.results .res-body{padding:0;max-height:520px;overflow-y:auto}
.results .res-item{padding:9px 20px;font-size:11.5px;border-bottom:1px solid rgba(26,36,64,.5);display:flex;align-items:flex-start;gap:10px;font-family:'Cascadia Code',monospace;transition:background .2s}
.results .res-item:hover{background:rgba(168,85,247,.04)}
.results .res-tag{font-size:9px;padding:3px 8px;border-radius:5px;white-space:nowrap;font-weight:700;letter-spacing:.5px}
.results .res-text{color:var(--fg1);word-break:break-all;line-height:1.5}
.tag-d{background:rgba(239,68,68,.15);color:var(--red);border:1px solid rgba(239,68,68,.25)}
.tag-f{background:rgba(245,158,11,.15);color:var(--amber);border:1px solid rgba(245,158,11,.25)}
.tag-s{background:rgba(59,130,246,.15);color:var(--blue);border:1px solid rgba(59,130,246,.25)}
.tag-ok{background:rgba(34,197,94,.15);color:var(--green);border:1px solid rgba(34,197,94,.25)}
.history{background:rgba(12,16,26,.6);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.history .h-item{padding:12px 20px;border-bottom:1px solid rgba(26,36,64,.5);font-size:12px;display:flex;justify-content:space-between;cursor:pointer;transition:all .2s}
.history .h-item:hover{background:rgba(168,85,247,.05)}
.toast{position:fixed;bottom:28px;right:28px;background:rgba(12,16,26,.92);border:1px solid var(--accent);border-radius:10px;padding:14px 22px;font-size:13px;z-index:100;opacity:0;transition:.4s;pointer-events:none;box-shadow:0 8px 30px rgba(168,85,247,.2)}
.toast.show{opacity:1;animation:toastIn .4s ease}
@keyframes toastIn{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}
.firework{position:fixed;pointer-events:none;z-index:99}
.firework .particle{position:absolute;width:4px;height:4px;border-radius:50%;animation:fwBurst .8s ease-out forwards}
@keyframes fwBurst{0%{transform:translate(0,0) scale(1);opacity:1}100%{transform:translate(var(--dx),var(--dy)) scale(0);opacity:0}}
.mindmap-toggle{position:fixed;right:20px;bottom:20px;width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,var(--accent),#7c3aed);color:#fff;font-size:22px;border:none;cursor:pointer;z-index:50;box-shadow:0 4px 20px rgba(168,85,247,.4);transition:all .3s;display:flex;align-items:center;justify-content:center}
.mindmap-toggle:hover{transform:scale(1.1);box-shadow:0 6px 30px rgba(168,85,247,.6)}
.mindmap-panel{position:fixed;top:0;right:-420px;width:400px;height:100%;background:rgba(12,16,26,.95);backdrop-filter:blur(20px);border-left:1px solid var(--border);z-index:49;transition:right .4s cubic-bezier(.4,0,.2,1);padding:24px;overflow-y:auto;box-shadow:-8px 0 40px rgba(0,0,0,.5)}
.mindmap-panel.open{right:0}
.mindmap-panel h2{font-size:15px;margin-bottom:16px;background:linear-gradient(135deg,var(--accent2),var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.mindmap-panel .mm-principle{font-size:11px;color:var(--fg1);line-height:1.7;background:rgba(19,26,40,.6);border-radius:8px;padding:12px;margin-bottom:16px;white-space:pre-wrap}
.mindmap-panel .mm-list{list-style:none}
.mindmap-panel .mm-list li{font-size:11.5px;padding:8px 0;border-bottom:1px solid rgba(26,36,64,.5);color:var(--fg1);display:flex;align-items:flex-start;gap:8px}
.mindmap-panel .mm-source{font-size:10px;color:var(--fg2);margin-top:16px;font-style:italic}
.mm-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.4);z-index:48;display:none}
.mm-overlay.show{display:block}
</style>
</head>
<body>
<canvas id="starfield"></canvas>
<div class="scanline"></div>
<div class="hdr">
  <div class="brand"><span class="logo">🪞</span><h1>镜像多维度空间</h1><span class="ver">V1.0</span></div>
  <div class="status" id="statusBar"><span class="dot"></span><span id="statusText">就绪</span></div>
</div>
<div class="main">
  <div class="nav">
    <div class="ni sel" data-panel="full" onclick="switchPanel('full')"><span class="ico">🚀</span>完整管道</div>
    <div class="sep"></div>
    <div class="ni" data-panel="scan" onclick="switchPanel('scan')"><span class="ico">🔍</span>全量扫描</div>
    <div class="ni" data-panel="audit" onclick="switchPanel('audit')"><span class="ico">🔐</span>深度审计</div>
    <div class="ni" data-panel="fix" onclick="switchPanel('fix')"><span class="ico">🔧</span>沙盒修复</div>
    <div class="ni" data-panel="dimensions" onclick="switchPanel('dimensions')"><span class="ico">🎯</span>四维度测试</div>
    <div class="sep"></div>
    <div class="ni" data-panel="history" onclick="switchPanel('history')"><span class="ico">📋</span>运行记录</div>
  </div>
  <div class="content" id="mainContent">
    <div class="path-bar">
      <input type="text" id="projectPath" placeholder="输入项目路径..." value="">
      <button class="btn btn-outline" onclick="browse()">📂</button>
      <button class="btn btn-primary" id="btnRun" onclick="runCurrentPanel()">🚀 启动完整管道</button>
    </div>
    <div class="pipeline-wrap" id="pipelineWrap">
      <div class="pipeline" id="pipelineBar">
        <div class="pipe-step" id="ps0"><div class="step-num">STAGE 1</div><div class="step-icon">🔍</div><div class="step-name">全量扫描</div></div>
        <div class="pipe-step" id="ps1"><div class="step-num">STAGE 2</div><div class="step-icon">📊</div><div class="step-name">分类统计</div></div>
        <div class="pipe-step" id="ps2"><div class="step-num">STAGE 3</div><div class="step-icon">🔐</div><div class="step-name">深度审计</div></div>
        <div class="pipe-step" id="ps3"><div class="step-num">STAGE 4</div><div class="step-icon">🔧</div><div class="step-name">沙盒修复</div></div>
        <div class="pipe-step" id="ps4"><div class="step-num">STAGE 5</div><div class="step-icon">✅</div><div class="step-name">语法验证</div></div>
        <div class="pipe-step" id="ps5"><div class="step-num">STAGE 6</div><div class="step-icon">🎯</div><div class="step-name">四维度测试</div></div>
        <div class="pipe-step" id="ps6"><div class="step-num">STAGE 7</div><div class="step-icon">📦</div><div class="step-name">原子部署</div></div>
      </div>
    </div>
    <div class="g2" id="metricCards">
      <div class="card"><div class="c-label">扫描文件</div><div class="c-value" id="mFiles">—</div><div class="c-sub">总文件数</div></div>
      <div class="card"><div class="c-label">安全隐患</div><div class="c-value" id="mDangers" style="color:var(--red)">—</div><div class="c-sub">危险模式</div></div>
      <div class="card"><div class="c-label">虚假代码</div><div class="c-value" id="mFakes" style="color:var(--amber)">—</div><div class="c-sub">占位/假数据</div></div>
      <div class="card"><div class="c-label">耗时</div><div class="c-value" id="mTime">—</div><div class="c-sub">秒</div></div>
    </div>
    <div class="dim-grid" id="dimCards" style="display:none">
      <div class="dim-card"><div class="dim-title">👤 用户视角</div><div class="dim-score" id="dimUser" style="color:var(--blue)">—</div><div class="dim-bar"><div class="dim-bar-fill" id="dimBarUser" style="width:0%;background:var(--blue)"></div></div></div>
      <div class="dim-card"><div class="dim-title">💻 开发者视角</div><div class="dim-score" id="dimDev" style="color:var(--accent2)">—</div><div class="dim-bar"><div class="dim-bar-fill" id="dimBarDev" style="width:0%;background:var(--accent2)"></div></div></div>
      <div class="dim-card"><div class="dim-title">⚙️ 运维视角</div><div class="dim-score" id="dimOps" style="color:var(--green)">—</div><div class="dim-bar"><div class="dim-bar-fill" id="dimBarOps" style="width:0%;background:var(--green)"></div></div></div>
      <div class="dim-card"><div class="dim-title">🛡️ 安全视角</div><div class="dim-score" id="dimSec" style="color:var(--red)">—</div><div class="dim-bar"><div class="dim-bar-fill" id="dimBarSec" style="width:0%;background:var(--red)"></div></div></div>
    </div>
    <div class="results" id="resultsBlock" style="display:none">
      <div class="res-hdr"><span id="resTitle">扫描结果</span><span id="resCount">0 项</span></div>
      <div class="res-body" id="resBody"></div>
    </div>
    <div class="history" id="historyBlock" style="display:none"></div>
  </div>
</div>
<div class="toast" id="toast"></div>
<button class="mindmap-toggle" id="mmToggle" onclick="toggleMindmap()" title="思维导图">🧠</button>
<div class="mm-overlay" id="mmOverlay" onclick="toggleMindmap()"></div>
<div class="mindmap-panel" id="mmPanel">
  <h2>🧠 思维导图 — 精细链路指引</h2>
  <div class="mm-principle" id="mmPrinciple">选择模式后自动展示...</div>
  <ul class="mm-list" id="mmList"></ul>
  <div class="mm-source" id="mmSource"></div>
</div>
<script>
const canvas=document.getElementById('starfield'),ctx=canvas.getContext('2d');
let stars=[];
function rs(){canvas.width=window.innerWidth;canvas.height=window.innerHeight}
rs();window.addEventListener('resize',rs);
for(let i=0;i<120;i++)stars.push({x:Math.random()*2e3,y:Math.random()*2e3,r:Math.random()*1.8+.2,dx:(Math.random()-.5)*.3,dy:(Math.random()-.5)*.3,a:Math.random()*.6+.2,p:Math.random()*Math.PI*2,s:Math.random()*.02+.005});
(function draw(t){ctx.clearRect(0,0,canvas.width,canvas.height);stars.forEach(s=>{s.x+=s.dx;s.y+=s.dy;if(s.x<0)s.x=canvas.width;if(s.x>canvas.width)s.x=0;if(s.y<0)s.y=canvas.height;if(s.y>canvas.height)s.y=0;let f=Math.sin(s.p+t*s.s)*.3+.7;ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,Math.PI*2);ctx.fillStyle='rgba(168,180,220,'+s.a*f+')';ctx.fill()});requestAnimationFrame(draw)})();
function fw(x,y){let c=document.createElement('div');c.className='firework';c.style.left=x+'px';c.style.top=y+'px';let cols=['#a855f7','#c084fc','#22c55e','#06b6d4','#f59e0b','#ec4899'];for(let i=0;i<30;i++){let p=document.createElement('div');p.className='particle';let a=Math.PI*2*i/30,d=30+Math.random()*50;p.style.setProperty('--dx',Math.cos(a)*d+'px');p.style.setProperty('--dy',Math.sin(a)*d+'px');p.style.background=cols[Math.floor(Math.random()*cols.length)];p.style.boxShadow='0 0 6px '+p.style.background;c.appendChild(p)}document.body.appendChild(c);setTimeout(()=>c.remove(),900)}
function spf(){let w=document.getElementById('pipelineWrap');w.querySelectorAll('.particle-stream').forEach(e=>e.remove());for(let i=0;i<3;i++){let s=document.createElement('div');s.className='particle-stream';s.style.top=(20+Math.random()*60)+'%';s.style.animationDuration=(1.5+Math.random()*2)+'s';s.style.animationDelay=(i*.4)+'s';w.appendChild(s)}}
let cp='full',ir=false,rh=JSON.parse(localStorage.getItem('mirror_history')||'[]'),pc='';
function sP(n){cp=n;document.querySelectorAll('.nav .ni').forEach(e=>e.classList.remove('sel'));document.querySelector('.nav .ni[data-panel="'+n+'"]').classList.add('sel');document.getElementById('btnRun').textContent=n==='full'?'🚀 启动完整管道':n==='scan'?'🔍 开始扫描':n==='audit'?'🔐 开始审计':n==='fix'?'🔧 沙盒修复':n==='dimensions'?'🎯 四维度测试':'▶ 运行';rU();if(n==='history')lH()}
function rU(){document.querySelectorAll('.pipe-step').forEach(e=>e.className='pipe-step');['mFiles','mDangers','mFakes','mTime'].forEach(id=>document.getElementById(id).textContent='—');document.getElementById('dimCards').style.display='none';document.getElementById('resultsBlock').style.display='none';document.getElementById('historyBlock').style.display='none';document.getElementById('metricCards').style.display='grid';['dimUser','dimDev','dimOps','dimSec'].forEach(id=>document.getElementById(id).textContent='—');document.getElementById('statusText').textContent='就绪'}
async function rCP(){if(ir)return;let p=document.getElementById('projectPath').value.trim();if(!p){t('请输入项目路径');return}pc=p;ir=true;document.getElementById('btnRun').disabled=true;document.getElementById('statusText').textContent='初始化管道...';document.getElementById('resultsBlock').style.display='block';document.getElementById('dimCards').style.display='none';spf();try{let r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p,mode:cp})});if(!r.ok){t('启动失败');ir=false;document.getElementById('btnRun').disabled=false;return}await pR()}catch(e){t('连接失败: '+e.message)}finally{ir=false;document.getElementById('btnRun').disabled=false}}
async function pR(){let d=false;while(!d){try{let r=await fetch('/api/status'),data=await r.json();uPL(data.pipeline||[]);uM(data.metrics||{});if(data.dimensions)uD(data.dimensions);if(data.results&&data.results.length>0)uRS(data.results);d=data.done;document.getElementById('statusText').textContent=data.status_text||'运行中...'}catch(e){d=true}if(!d)await new Promise(r=>setTimeout(r,800))}try{let r=await fetch('/api/result'),f=await r.json();uPL(f.pipeline||[]);uM(f.metrics||{});if(f.dimensions)uD(f.dimensions);if(f.results)uRS(f.results);document.getElementById('statusText').textContent=f.verdict||'完成';if(f.verdict==='通过'){let w=window.innerWidth,h=window.innerHeight;fw(w*.3,h*.3);setTimeout(()=>fw(w*.7,h*.25),300);setTimeout(()=>fw(w*.5,h*.35),600)}sH(f)}catch(e){}}
function uPL(st){st.forEach((s,i)=>{let el=document.getElementById('ps'+i);if(!el)return;el.className='pipe-step '+(s.status||'')})}
function uM(m){document.getElementById('mFiles').textContent=m.files??'—';document.getElementById('mDangers').textContent=m.dangers??'—';document.getElementById('mFakes').textContent=m.fakes??'—';document.getElementById('mTime').textContent=m.duration??'—'}
function uD(d){document.getElementById('dimCards').style.display='grid';[{id:'User',k:'user',c:'var(--blue)'},{id:'Dev',k:'developer',c:'var(--accent2)'},{id:'Ops',k:'ops',c:'var(--green)'},{id:'Sec',k:'security',c:'var(--red)'}].forEach(item=>{let v=d[item.k]?.score??0,el=document.getElementById('dim'+item.id);el.textContent=v+'/20';el.style.color=v>=15?'var(--green)':v>=10?'var(--amber)':'var(--red)';el.style.textShadow='0 0 '+(v>=15?20:8)+'px '+el.style.color;document.getElementById('dimBar'+item.id).style.width=(v/20*100)+'%';document.getElementById('dimBar'+item.id).style.background=item.c})}
function uRS(items){document.getElementById('resCount').textContent=items.length+' 项';let body=document.getElementById('resBody');body.innerHTML=items.slice(0,200).map(item=>{let tc=item.type&&(item.type.startsWith('HARDCODE')||item.type.startsWith('DANGER')||item.type==='SYNTAX_ERROR')?'tag-d':item.type&&(item.type.startsWith('FAKE')||item.type.startsWith('TODO')||item.type.startsWith('STUB')||item.type.startsWith('FIXME')||item.type.startsWith('HACK'))?'tag-f':item.type==='FIXED'?'tag-ok':'tag-s';return`<div class="res-item"><span class="res-tag ${tc}">${item.type||''}</span><span class="res-text">${item.file||''}${item.line?':'+item.line:''} — ${(item.snippet||'').slice(0,150)}</span></div>`}).join('')}
function sH(data){let e={time:new Date().toISOString(),path:pc,mode:cp,verdict:data.verdict||'完成',files:data.metrics?.files||0,dangers:data.metrics?.dangers||0,duration:data.metrics?.duration||0};rh.unshift(e);if(rh.length>50)rh=rh.slice(0,50);localStorage.setItem('mirror_history',JSON.stringify(rh))}
function lH(){document.getElementById('resultsBlock').style.display='none';document.getElementById('dimCards').style.display='none';document.getElementById('metricCards').style.display='none';let hb=document.getElementById('historyBlock');hb.style.display='block';rh=JSON.parse(localStorage.getItem('mirror_history')||'[]');hb.innerHTML=rh.length===0?'<div style="padding:30px;text-align:center;color:var(--fg2)">暂无运行记录</div>':rh.map(h=>`<div class="h-item"><span>${new Date(h.time).toLocaleString()} — ${(h.path||'').split('/').pop()||(h.path||'').split('\\').pop()}</span><span style="color:var(--fg2)">${h.files}文件 | ${h.dangers}问题 | ${h.duration}s</span><span style="font-weight:700;color:${h.verdict==='通过'?'var(--green)':'var(--amber)'}">${h.verdict}</span></div>`).join('')}
function browse(){t('手动输入项目路径即可');document.getElementById('projectPath').focus()}
function t(msg){let el=document.getElementById('toast');el.textContent=msg;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),2500)}
document.addEventListener('DOMContentLoaded',()=>{document.getElementById('projectPath').value='';document.getElementById('resultsBlock').style.display='none';document.getElementById('historyBlock').style.display='none';document.getElementById('dimCards').style.display='none';document.getElementById('mFiles').textContent='🪞'});
let mmOpen=false;
async function toggleMindmap(){mmOpen=!mmOpen;document.getElementById('mmPanel').classList.toggle('open',mmOpen);document.getElementById('mmOverlay').classList.toggle('show',mmOpen);if(mmOpen&&cp){try{let r=await fetch('/api/mindmap/'+cp),d=await r.json(),g=d.guide;document.getElementById('mmPrinciple').textContent=g.principle;document.getElementById('mmList').innerHTML=(g.checklist||[]).map(c=>'<li>'+c+'</li>').join('');document.getElementById('mmSource').textContent='参照: '+g.source}catch(e){}}}
async function showMindmapFor(mode){cp=mode;if(mmOpen){try{let r=await fetch('/api/mindmap/'+mode),d=await r.json(),g=d.guide;document.getElementById('mmPrinciple').textContent=g.principle;document.getElementById('mmList').innerHTML=(g.checklist||[]).map(c=>'<li>'+c+'</li>').join('');document.getElementById('mmSource').textContent='参照: '+g.source}catch(e){}}}
let _origSP=sP;sP=function(n){_origSP(n);showMindmapFor(n)}
</script>
</body>
</html>'''


# ══════════════════════════════════════════════════════════
#  引擎导入
# ══════════════════════════════════════════════════════════

from mirror_dimension.scanner import ProjectScanner
from mirror_dimension.auditor import ProjectAuditor
from mirror_dimension.fixer import SandboxFixer
from mirror_dimension.dimensions import DimensionTester
from mirror_dimension.mindmap_guide import get_prompt_prefix, MIRROR_DIMENSION_MERMAID, \
    AGENT_LOOP_MERMAID, DUAL_WHEEL_MERMAID, get_guide

# ══════════════════════════════════════════════════════════
#  Flask App
# ══════════════════════════════════════════════════════════

app = Flask(__name__)

_run_state = {
    "running": False, "done": False,
    "pipeline": [{"name": s, "status": ""} for s in
                 ["全量扫描","分类统计","深度审计","沙盒修复","语法验证","四维度测试","原子部署"]],
    "metrics": {"files": 0, "dangers": 0, "fakes": 0, "duration": 0},
    "dimensions": None, "results": [], "status_text": "就绪", "verdict": "",
    "mindmap": None,
}


@app.route("/")
@app.route("/dashboard")
def dashboard():
    resp = app.make_response(render_template_string(DASHBOARD_HTML))
    resp.headers["Cache-Control"] = "no-cache,no-store,must-revalidate"
    return resp


@app.route("/api/status")
def api_status():
    return jsonify(_run_state)


@app.route("/api/result")
def api_result():
    return jsonify(_run_state)


@app.route("/api/run", methods=["POST"])
def api_run():
    global _run_state
    if _run_state["running"]:
        return jsonify({"error": "已有任务在运行"}), 409
    data = request.get_json() or {}
    path = data.get("path", "")
    mode = data.get("mode", "full")
    if not path or not os.path.isdir(path):
        return jsonify({"error": "无效的项目路径"}), 400

    _run_state = {
        "running": True, "done": False,
        "pipeline": [{"name": s, "status": ""} for s in
                     ["全量扫描","分类统计","深度审计","沙盒修复","语法验证","四维度测试","原子部署"]],
        "metrics": {"files": 0, "dangers": 0, "fakes": 0, "duration": 0},
        "dimensions": None, "results": [], "status_text": "启动中...", "verdict": "",
    }

    def _runner():
        global _run_state
        t0 = time.time()
        try:
            stages = _run_state["pipeline"]
            # Scan
            stages[0]["status"] = "active"
            _run_state["status_text"] = "Stage 1/7: 维度展开中..."
            scan = ProjectScanner(path).scan()
            _run_state["metrics"] = {
                "files": scan["total_files"],
                "dangers": scan["dangers"],
                "fakes": scan["fakes"],
                "duration": round(time.time()-t0, 1),
            }
            _run_state["results"] = (
                scan["danger_items"][:50] + scan["fake_items"][:50] + scan["syntax_items"][:20]
            )
            stages[0]["status"] = "done" if scan["clean"] else "fail"
            stages[1]["status"] = "done"
            if mode == "scan":
                _run_state.update(done=True, status_text="维度收束完成",
                    verdict="通过" if scan["clean"] else f"发现{scan['dangers']}个异常", running=False)
                return

            # Audit
            stages[2]["status"] = "active"
            _run_state["status_text"] = "Stage 3/7: 镜像折射中..."
            audit = ProjectAuditor(path).audit()
            if audit.get("sensitive_files"):
                _run_state["results"].extend(
                    {"file": f, "type": "SENSITIVE_FILE", "line": 0, "snippet": f}
                    for f in audit["sensitive_files"]
                )
            if audit.get("gitignore_gaps"):
                _run_state["results"].extend(
                    {"file": ".gitignore", "type": "GITIGNORE_GAP", "line": 0, "snippet": g}
                    for g in audit["gitignore_gaps"]
                )
            stages[2]["status"] = "done" if audit["clean"] else "fail"
            if mode == "audit":
                _run_state.update(done=True, status_text="折射完成",
                    verdict="通过" if audit["clean"] else "发现裂痕", running=False)
                return

            # Fix
            stages[3]["status"] = "active"
            _run_state["status_text"] = "Stage 4/7: 沙盒重塑中..."
            fix = SandboxFixer(path).run()
            _run_state["results"].extend(
                {"file": f, "type": "FIXED", "line": 0, "snippet": "已修复"}
                for f in fix.get("files_fixed", [])
            )
            stages[3]["status"] = "done"
            stages[4]["status"] = "done" if fix["clean"] else "fail"
            if mode == "fix":
                _run_state.update(done=True, status_text="重塑完成",
                    verdict=f"修复{fix.get('fixes_applied',0)}处", running=False)
                return

            # Dimensions
            stages[5]["status"] = "active"
            _run_state["status_text"] = "Stage 6/7: 四维度坍缩中..."
            dims = DimensionTester(path).test()
            _run_state["dimensions"] = dims
            stages[5]["status"] = "done" if dims.get("average_score", 0) >= 50 else "fail"
            if mode == "dimensions":
                _run_state.update(done=True, status_text="坍缩完成",
                    verdict=f"平均{dims.get('average_score',0):.0f}/80", running=False)
                return

            # Done
            stages[6]["status"] = "done"
            total_issues = scan["dangers"] + (fix.get("syntax_errors") and len(fix["syntax_errors"]) or 0)
            _run_state.update(done=True, status_text="多维空间稳定",
                verdict="通过" if total_issues == 0 else f"发现{total_issues}个异常维度",
                running=False)
            _run_state["metrics"]["duration"] = round(time.time()-t0, 1)
        except Exception as e:
            _run_state.update(done=True, running=False,
                status_text=f"维度震荡: {e}", verdict="管道崩塌")

    threading.Thread(target=_runner, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/mindmap/<mode>")
def api_mindmap(mode):
    guide = get_guide(mode)
    return jsonify({
        "mode": mode,
        "guide": guide,
        "mermaid": MIRROR_DIMENSION_MERMAID if mode == "full" else "",
    })


def main():
    port = 8766
    for p in range(8766, 8780):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", p))
            s.close()
            port = p
            break
        except Exception:
            continue
    url = f"http://127.0.0.1:{port}"
    print(f"\n{'=' * 50}")
    print(f"  🪞  镜像多维度空间 v1.0")
    print(f"  🌐 {url}")
    print(f"{'=' * 50}\n")
    webbrowser.open(url)
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()