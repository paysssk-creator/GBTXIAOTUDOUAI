#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gbt/voice_web.py — 网页麦克风桥接
在 PC 上启动一个 HTTP 服务，iPhone 浏览器打开页面即可:
  - 手机麦克风采集音频
  - WebSocket 实时传输到 PC
  - PC 端接收后转文字 → 路由 → TTS 语音回复
"""
import sys, os, json, time, asyncio, base64, threading, queue, logging

L = logging.getLogger("GBT.VoiceWeb")

# 语音数据队列 (手机 → PC)
_audio_queue = queue.Queue(maxsize=50)
_text_result_queue = queue.Queue(maxsize=10)

# HTML 页面 - 手机端麦克风采集
WEB_CLIENT_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>GBT Voice</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, system-ui, sans-serif; background: #0d1117; color: #c9d1d9; display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:100vh; padding:20px; }
h1 { font-size:24px; margin-bottom:8px; color:#58a6ff; }
.status { font-size:14px; color:#8b949e; margin-bottom:24px; }
.btn { width:120px; height:120px; border-radius:50%; border:3px solid #30363d; background:#161b22; color:#c9d1d9; font-size:16px; cursor:pointer; transition:all .2s; display:flex; align-items:center; justify-content:center; margin-bottom:20px; user-select:none; -webkit-tap-highlight-color:transparent; }
.btn.listening { border-color:#3fb950; background:#0d3320; color:#3fb950; animation:pulse 1.5s infinite; }
.btn.error { border-color:#f85149; color:#f85149; }
@keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.05)} }
#text { width:100%; max-width:320px; min-height:80px; padding:12px; border-radius:8px; border:1px solid #30363d; background:#0d1117; color:#c9d1d9; font-size:14px; resize:vertical; }
#reply { width:100%; max-width:320px; margin-top:12px; padding:12px; border-radius:8px; background:#161b22; border:1px solid #30363d; font-size:14px; min-height:40px; }
#log { width:100%; max-width:320px; margin-top:8px; font-size:12px; color:#8b949e; text-align:center; }
#wsStatus { font-size:11px; color:#58a6ff; margin-bottom:4px; }
</style>
</head>
<body>
<h1>GBT Voice</h1>
<div id="wsStatus">连接中...</div>
<div class="status" id="status">点击按钮开始说话</div>
<button class="btn" id="btn" onclick="toggleRecord()">🎤</button>
<div id="log"></div>
<textarea id="text" placeholder="或直接打字..."></textarea>
<button onclick="sendText()" style="margin:10px 0;padding:8px 24px;border-radius:6px;border:1px solid #30363d;background:#161b22;color:#c9d1d9;cursor:pointer;">发送文字</button>
<div id="reply"></div>

<script>
let ws = null;
let mediaRecorder = null;
let stream = null;
let isRecording = false;
let reconnectTimer = null;

function connect() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = proto + '//' + location.host + '/voice/ws';
    document.getElementById('wsStatus').textContent = '连接中...';
    
    ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';
    
    ws.onopen = () => {
        document.getElementById('wsStatus').textContent = '已连接';
        document.getElementById('wsStatus').style.color = '#3fb950';
        log('WebSocket 已连接');
        if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    };
    
    ws.onmessage = (e) => {
        try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'reply') {
                document.getElementById('reply').textContent = '回复: ' + msg.text;
                log('回复: ' + msg.text.substring(0,40));
            } else if (msg.type === 'status') {
                document.getElementById('status').textContent = msg.text;
            } else if (msg.type === 'transcript') {
                document.getElementById('status').textContent = '听到: ' + msg.text;
            }
        } catch(err) {}
    };
    
    ws.onclose = () => {
        document.getElementById('wsStatus').textContent = '断开';
        document.getElementById('wsStatus').style.color = '#f85149';
        log('连接断开, 3秒后重连...');
        reconnectTimer = setTimeout(connect, 3000);
    };
    
    ws.onerror = () => {
        document.getElementById('wsStatus').textContent = '错误';
        document.getElementById('wsStatus').style.color = '#f85149';
    };
}

function log(msg) {
    document.getElementById('log').textContent = msg;
}

async function toggleRecord() {
    const btn = document.getElementById('btn');
    
    if (isRecording) {
        stopRecord();
        return;
    }
    
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true } });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
        
        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                ws.send(e.data);
            }
        };
        
        mediaRecorder.start(250);
        isRecording = true;
        btn.classList.add('listening');
        btn.textContent = '⏹';
        document.getElementById('status').textContent = '正在听...';
        log('录音中...');
    } catch(e) {
        log('错误: ' + e.message);
        btn.classList.add('error');
        document.getElementById('status').textContent = '麦克风权限被拒绝';
    }
}

function stopRecord() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    if (stream) {
        stream.getTracks().forEach(t => t.stop());
        stream = null;
    }
    isRecording = false;
    const btn = document.getElementById('btn');
    btn.classList.remove('listening','error');
    btn.textContent = '🎤';
    document.getElementById('status').textContent = '已停止';
    log('录音已停止');
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({type:'stop'}));
    }
}

function sendText() {
    const text = document.getElementById('text').value.trim();
    if (!text) return;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({type:'text', text: text}));
        document.getElementById('text').value = '';
        document.getElementById('status').textContent = '已发送';
    }
}

// Auto-start
connect();

// Handle page visibility
document.addEventListener('visibilitychange', () => {
    if (document.hidden && isRecording) stopRecord();
});
</script>
</body>
</html>
"""

# STT: 音频转文字 (使用 Google Web Speech - 免费)
async def _transcribe_webm(audio_bytes: bytes) -> str:
    """将 webm/opus 音频转为文字"""
    import tempfile, subprocess
    # 先用 ffmpeg 转成 wav (16kHz mono)
    try:
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
            f.write(audio_bytes)
            webm_path = f.name
        wav_path = webm_path.replace('.webm', '.wav')
        
        # ffmpeg convert
        subprocess.run([
            'ffmpeg', '-y', '-i', webm_path, '-ar', '16000', '-ac', '1', '-f', 'wav', wav_path
        ], capture_output=True, timeout=10)
        
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 100:
            # Use speech_recognition with Google
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.AudioFile(wav_path) as source:
                    audio = r.record(source)
                text = r.recognize_google(audio, language='zh-CN')
                return text
            except ImportError:
                pass
    except Exception as e:
        L.warning(f"STT error: {e}")
    finally:
        for p in [webm_path, wav_path]:
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except Exception:
                pass


class VoiceWebBridge:
    """Web 语音桥 - PC 端服务 + 手机端页面"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8766):
        self.host = host
        self.port = port
        self._server = None
        self._running = False
        self._audio_buffer = bytearray()
        self._clients = set()
        self._pending_texts = queue.Queue()
        self._reply_queue = queue.Queue()
        
    def start(self):
        """启动 Web 语音桥服务器"""
        import threading
        t = threading.Thread(target=self._run_server, daemon=True)
        t.start()
        # Wait for server to start
        time.sleep(1)
        return self
        
    def _run_server(self):
        """运行 aiohttp/asyncio 服务"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_run())
        except Exception as e:
            L.error(f"Web voice server error: {e}")
            
    async def _async_run(self):
        """异步 HTTP + WebSocket 服务"""
        import aiohttp
        from aiohttp import web
        
        async def handle_index(request):
            return web.Response(text=WEB_CLIENT_HTML, content_type='text/html; charset=utf-8')
        
        async def handle_ws(request):
            ws = web.WebSocketResponse(max_msg_size=10*1024*1024)
            await ws.prepare(request)
            self._clients.add(ws)
            L.info("Voice client connected")
            
            await ws.send_json({"type": "status", "text": "GBT Voice 已就绪"})
            
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    self._audio_buffer.extend(msg.data)
                    if len(self._audio_buffer) > 16000:  # ~1 second of audio
                        self._audio_queue.put(bytes(self._audio_buffer))
                        self._audio_buffer = bytearray()
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if data.get('type') == 'stop' and len(self._audio_buffer) > 400:
                            self._audio_queue.put(bytes(self._audio_buffer))
                            self._audio_buffer = bytearray()
                        elif data.get('type') == 'text':
                            self._pending_texts.put(data.get('text', ''))
                    except:
                        pass
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    L.warning(f"WS error: {ws.exception()}")
                    
            self._clients.discard(ws)
            L.info("Voice client disconnected")
            return ws
        
        app = web.Application()
        app.router.add_get('/', handle_index)
        app.router.add_get('/voice/ws', handle_ws)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        local_ip = self._get_local_ip()
        print(f"\n{'='*50}")
        print(f"  GBT Voice Web Bridge")
        print(f"  PC: http://{self.host}:{self.port}")
        print(f"  Phone: http://{local_ip}:{self.port}")
        print(f"{'='*50}\n")
        
        self._running = True
        
        # Also start the reply sender + GBT reasoning processor
        asyncio.create_task(self._send_replies())
        asyncio.create_task(self._process_inputs())
        
        # Keep running
        while self._running:
            await asyncio.sleep(1)
            
    async def _process_inputs(self):
        """处理手机端输入 → GBT推理 → TTS回复 → 发送回手机"""
        import aiohttp as ah
        
        while self._running:
            text = None
            mode = "text"
            
            # 先检查文字输入
            try:
                text = self._pending_texts.get_nowait()
                mode = "text"
            except queue.Empty:
                pass
            
            # 再检查语音输入
            if not text:
                try:
                    audio = _audio_queue.get(timeout=0.5)
                    if audio and len(audio) > 400:
                        text = await asyncio.to_thread(_transcribe_webm, audio)
                        mode = "voice"
                except queue.Empty:
                    pass
            
            if not text:
                await asyncio.sleep(0.5)
                continue
            
            print(f"\n[VOICE] {mode}: {text}")
            
            # 发送状态到手机
            for client in list(self._clients):
                try:
                    await client.send_json({"type": "transcript", "text": text})
                except Exception:
                    pass
            
            # Step 1: 调用 GBT 推理
            conclusion = ""
            capability = ""
            try:
                async with ah.ClientSession() as session:
                    async with session.post(
                        "http://127.0.0.1:8765/api/reason",
                        json={"text": text, "mode": "chain"},
                        timeout=ah.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            conclusion = data.get("conclusion", "")[:500]
                            capability = data.get("capability", "")
                            print(f"[VOICE] route={capability} reply={conclusion[:80]}...")
            except Exception as e:
                conclusion = f"抱歉，推理服务出错了: {e}"
            
            # Step 2: TTS 语音回复
            if conclusion:
                try:
                    from gbt.voice_tts import GBTVoice
                    v = GBTVoice()
                    voice_text = conclusion[:400]
                    await asyncio.to_thread(v.speak, voice_text)
                except Exception as e:
                    print(f"[VOICE] TTS error: {e}")
            
            # Step 3: 发送回复到手机
            for client in list(self._clients):
                try:
                    await client.send_json({
                        "type": "reply",
                        "text": conclusion[:500],
                        "capability": capability
                    })
                except Exception:
                    pass
            
    async def _send_replies(self):
        """定期检查并发送回复"""
        while self._running:
            try:
                reply = self._reply_queue.get_nowait()
                for client in list(self._clients):
                    try:
                        await client.send_json({"type": "reply", "text": reply})
                    except Exception:
                        pass
            except queue.Empty:
                pass
            await asyncio.sleep(0.5)
    
    def _get_local_ip(self) -> str:
        """获取本机局域网 IP"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def get_audio(self, timeout: float = 8.0) -> bytes:
        """获取一段语音数据 (阻塞)"""
        try:
            return _audio_queue.get(timeout=timeout)
        except queue.Empty:
            return b''
    
    def get_text(self, timeout: float = 1.0) -> str:
        """获取文字输入"""
        try:
            return self._pending_texts.get(timeout=timeout)
        except queue.Empty:
            return ''
    
    def send_reply(self, text: str):
        """发送回复到手机"""
        self._reply_queue.put(text)
    
    def listen_and_reply(self, timeout: float = 8.0, think_fn=None) -> dict:
        """
        听 → 识别 → 思考 → 回复
        think_fn: 可选的推理函数
        """
        # 先检查文字输入
        text = self.get_text(timeout=0.1)
        
        if not text:
            # 等待语音
            audio = self.get_audio(timeout=timeout)
            if audio:
                text = _transcribe_webm(audio)
        
        if not text:
            return {"ok": False, "error": "未收到输入"}
        
        result = {"ok": True, "text": text, "mode": "voice" if not text else "text"}
        
        # 回复
        if think_fn:
            reply = think_fn(text)
        else:
            reply = f"收到: {text}"
        
        self.send_reply(reply)
        result["reply"] = reply
        return result
    
    def stop(self):
        self._running = False


# 全局单例
_bridge = None

def get_voice_bridge() -> VoiceWebBridge:
    global _bridge
    if _bridge is None:
        _bridge = VoiceWebBridge()
    return _bridge


# ═══ 独立运行 ═══
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bridge = VoiceWebBridge()
    bridge.start()
    
    print("\n在 iPhone 浏览器打开上面的 Phone 地址")
    print("点击麦克风按钮开始说话\n")
    
    try:
        while True:
            audio = bridge.get_audio(timeout=60)
            if audio:
                text = _transcribe_webm(audio)
                if text:
                    print(f"听到: {text}")
                    bridge.send_reply(f"收到你的语音: {text}")
    except KeyboardInterrupt:
        print("\n停止")
        bridge.stop()
