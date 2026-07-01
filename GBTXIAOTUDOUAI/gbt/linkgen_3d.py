"""GBT LinkGen 3D — 3D地球连接可视化 v1.0
Flask + Three.js 3D Globe — 全球可访问
展示短链接在全球的访问节点
"""
import os, json, logging, threading, time, socket

L = logging.getLogger("GBT.LinkGen3D")

# ── 全局状态 ──────────────────────────────────────
_links: list = []       # [{url, short, service, lat, lng, time}]
_server_thread = None
_server_port = 8769
_server_running = False

# ── 主要城市坐标 (lat, lng) ───────────────────────
CITIES = {
    "Beijing": (39.9, 116.4), "Shanghai": (31.2, 121.5),
    "Tokyo": (35.7, 139.7), "Seoul": (37.6, 127.0),
    "Singapore": (1.3, 103.8), "Mumbai": (19.1, 72.9),
    "Dubai": (25.2, 55.3), "Moscow": (55.8, 37.6),
    "London": (51.5, -0.1), "Paris": (48.9, 2.3),
    "Berlin": (52.5, 13.4), "New York": (40.7, -74.0),
    "San Francisco": (37.8, -122.4), "Los Angeles": (34.1, -118.2),
    "Sydney": (-33.9, 151.2), "Sao Paulo": (-23.5, -46.6),
    "Cape Town": (-33.9, 18.4), "Lagos": (6.5, 3.4),
    "Toronto": (43.7, -79.4), "Mexico City": (19.4, -99.1),
    "Jakarta": (-6.2, 106.8), "Bangkok": (13.8, 100.5),
    "Istanbul": (41.0, 29.0), "Cairo": (30.0, 31.2),
    "Amsterdam": (52.4, 4.9), "Stockholm": (59.3, 18.1),
}

# ── Three.js 3D Globe HTML 模板 ────────────────────
GLOBE_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GBT LinkGen 3D Globe</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e14;overflow:hidden;font-family:"Cascadia Code","Consolas",monospace}
#info{position:absolute;top:20px;left:50%;transform:translateX(-50%);
  color:#58a6ff;font-size:14px;text-align:center;pointer-events:none;
  text-shadow:0 0 20px rgba(88,166,255,0.5);z-index:10}
#stats{position:absolute;bottom:30px;left:50%;transform:translateX(-50%);
  color:#8b949e;font-size:11px;text-align:center;pointer-events:none;z-index:10}
.node-label{position:absolute;color:#e6e8ec;font-size:10px;
  pointer-events:none;text-shadow:0 0 8px rgba(57,211,83,0.8);
  transform:translate(-50%,-50%);z-index:5}
#panel{position:absolute;top:20px;right:20px;background:rgba(19,24,32,0.95);
  border:1px solid #1c2433;border-radius:8px;padding:16px;color:#e6e8ec;
  font-size:12px;max-width:260px;z-index:20}
#panel h3{color:#39d353;margin-bottom:8px;font-size:13px}
#panel .link-item{padding:6px 0;border-bottom:1px solid #1c2433;cursor:pointer}
#panel .link-item:hover{color:#58a6ff}
#panel .link-item .service{color:#8b949e;font-size:10px}
#panel .link-item .url{color:#58a6ff;font-size:10px;word-break:break-all}
#panel .empty{color:#8b949e;font-size:11px;text-align:center;padding:10px 0}
.loading{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  color:#58a6ff;font-size:18px;z-index:100}
</style>
</head>
<body>
<div class="loading" id="loading">🌍 Loading Globe...</div>
<div id="info">GBT LinkGen — 全球连接节点</div>
<div id="stats">Nodes: 0 | Links: 0</div>
<div id="panel">
  <h3>🔗 Generated Links</h3>
  <div id="link-list"><div class="empty">No links yet — generate one!</div></div>
</div>

<script type="importmap">
{"imports":{"three":"https://unpkg.com/three@0.160.0/build/three.module.js",
"three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}
</script>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

// ── Scene Setup ──────────────────────────────────
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0e14);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth/window.innerHeight, 0.5, 1000);
camera.position.set(0, 0, 4.5);

const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));
document.body.appendChild(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(window.innerWidth, window.innerHeight);
labelRenderer.domElement.style.position = 'absolute';
labelRenderer.domElement.style.top = '0px';
labelRenderer.domElement.style.pointerEvents = 'none';
document.body.appendChild(labelRenderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 1.8;
controls.maxDistance = 10;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.3;

// ── Stars ────────────────────────────────────────
const starsGeo = new THREE.BufferGeometry();
const starsCount = 2000;
const starsPos = new Float32Array(starsCount * 3);
for(let i=0;i<starsCount*3;i++) starsPos[i] = (Math.random()-0.5)*30;
starsGeo.setAttribute('position', new THREE.BufferAttribute(starsPos,3));
const stars = new THREE.Points(starsGeo, new THREE.PointsMaterial({color:0xffffff,size:0.015}));
scene.add(stars);

// ── Earth ────────────────────────────────────────
const earthGeo = new THREE.SphereGeometry(1.2, 64, 64);
const earthTex = new THREE.TextureLoader().load(
  'https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg'
);
const earthMat = new THREE.MeshPhongMaterial({map:earthTex, specular:0x333333, shininess:15});
const earth = new THREE.Mesh(earthGeo, earthMat);
scene.add(earth);

// ── Atmosphere ───────────────────────────────────
const atmosGeo = new THREE.SphereGeometry(1.23, 64, 64);
const atmosMat = new THREE.MeshPhongMaterial({
  color:0x58a6ff, transparent:true, opacity:0.08, side:THREE.FrontSide
});
const atmosphere = new THREE.Mesh(atmosGeo, atmosMat);
scene.add(atmosphere);

// ── Grid lines ───────────────────────────────────
const gridHelper = new THREE.PolarGridHelper(2, 36, 24, 64, 0x1c2433, 0x1c2433);
scene.add(gridHelper);

// ── Lights ───────────────────────────────────────
const ambient = new THREE.AmbientLight(0x404060);
scene.add(ambient);
const sun = new THREE.DirectionalLight(0xffffff, 1.8);
sun.position.set(5, 3, 5);
scene.add(sun);

// ── Node system ──────────────────────────────────
const nodes = [];
const arcs = [];
const NODE_COLORS = [0x39d353, 0x58a6ff, 0xf0883e, 0xe55388, 0xf0c040];

function latLngToVec3(lat, lng, radius=1.25) {
  const phi = (90 - lat) * Math.PI / 180;
  const theta = lng * Math.PI / 180;
  return new THREE.Vector3(
    radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

function addNode(lat, lng, label, colorIdx=0) {
  const pos = latLngToVec3(lat, lng);
  const color = NODE_COLORS[colorIdx % NODE_COLORS.length];

  // Glow ring
  const ringGeo = new THREE.TorusGeometry(0.025, 0.006, 16, 16);
  const ringMat = new THREE.MeshBasicMaterial({color, transparent:true, opacity:0.9});
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.position.copy(pos);
  ring.lookAt(new THREE.Vector3(0,0,0));
  scene.add(ring);

  // Dot
  const dotGeo = new THREE.SphereGeometry(0.018, 16, 16);
  const dotMat = new THREE.MeshBasicMaterial({color:0xffffff});
  const dot = new THREE.Mesh(dotGeo, dotMat);
  dot.position.copy(pos);
  scene.add(dot);

  // Label
  const div = document.createElement('div');
  div.className = 'node-label';
  div.textContent = label;
  const labelObj = new CSS2DObject(div);
  labelObj.position.copy(latLngToVec3(lat, lng, 1.4));
  scene.add(labelObj);

  nodes.push({pos, ring, dot, label: labelObj, color, lat, lng});
  return nodes.length - 1;
}

function addArc(fromIdx, toIdx, colorIdx=0) {
  if(fromIdx >= nodes.length || toIdx >= nodes.length) return;
  const from = nodes[fromIdx];
  const to = nodes[toIdx];
  const color = NODE_COLORS[colorIdx % NODE_COLORS.length];

  const mid = from.pos.clone().add(to.pos).normalize().multiplyScalar(1.6);
  const curve = new THREE.QuadraticBezierCurve3(from.pos.clone(), mid, to.pos.clone());
  const points = curve.getPoints(50);
  const arcGeo = new THREE.BufferGeometry().setFromPoints(points);
  const arcMat = new THREE.LineBasicMaterial({color, transparent:true, opacity:0.5});
  const arcLine = new THREE.Line(arcGeo, arcMat);
  scene.add(arcLine);

  // Pulse dot
  const pulseGeo = new THREE.SphereGeometry(0.01, 8, 8);
  const pulseMat = new THREE.MeshBasicMaterial({color});
  const pulse = new THREE.Mesh(pulseGeo, pulseMat);
  pulse.position.copy(from.pos);
  scene.add(pulse);

  const arcData = {line:arcLine, pulse, curve, from:from.pos, to:to.pos, progress:0};
  arcs.push(arcData);
  return arcData;
}

// ── Load data from API ───────────────────────────
async function loadLinks() {
  try {
    const resp = await fetch('/api/links');
    const data = await resp.json();
    document.getElementById('loading').style.display = 'none';

    if(!data.links || data.links.length === 0) return;

    const listEl = document.getElementById('link-list');
    listEl.innerHTML = '';

    const cityNames = Object.keys(data.cities || {});
    const usedCities = {};
    data.links.forEach((link, i) => {
      // Pick a city for the destination
      const cityIdx = i % cityNames.length;
      const city = cityNames[cityIdx];
      const [lat, lng] = data.cities[city];
      const key = `${lat},${lng}`;

      if(!usedCities[key]) {
        usedCities[key] = {lat, lng, label: city, count: 0};
      }
      const nodeIdx = addNode(lat, lng, city, i);

      // Add to panel
      const item = document.createElement('div');
      item.className = 'link-item';
      item.innerHTML = `<div>🔗 ${link.short || link.url}</div>
        <div class="service">${link.service||'direct'} · ${link.time||''}</div>`;
      item.onclick = () => {
        if(link.short) navigator.clipboard.writeText(link.short);
      };
      listEl.appendChild(item);
    });

    // Add origin node (Shanghai as default origin)
    const originIdx = addNode(31.2, 121.5, 'GBT', 0);

    // Connect origin to all destinations
    for(let i = 0; i < nodes.length - 1; i++) {
      addArc(originIdx, originIdx + 1 + i, i);
    }

    document.getElementById('stats').textContent =
      `Nodes: ${nodes.length} | Links: ${data.links.length} | GBT LinkGen 3D`;
  } catch(e) {
    document.getElementById('loading').textContent = '⚠ Server offline — start linkgen_3d';
    console.error(e);
  }
}

// ── Animation Loop ───────────────────────────────
let clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  controls.update();

  const dt = Math.min(clock.getDelta(), 0.1);

  // Pulse arcs
  arcs.forEach(arc => {
    arc.progress = (arc.progress + dt * 0.5) % 1;
    const pt = arc.curve.getPoint(arc.progress);
    arc.pulse.position.copy(pt);
    arc.pulse.material.opacity = 0.5 + 0.5 * Math.sin(arc.progress * Math.PI);
  });

  // Pulse rings
  const t = Date.now() * 0.001;
  nodes.forEach((n, i) => {
    const s = 0.85 + 0.15 * Math.sin(t * 3 + i);
    n.ring.scale.setScalar(s);
  });

  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}

// ── Start ────────────────────────────────────────
loadLinks().then(() => animate());

// ── Resize ───────────────────────────────────────
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  labelRenderer.setSize(window.innerWidth, window.innerHeight);
});
</script>
</body>
</html>"""


def _find_free_port(start: int = 8769) -> int:
    """找可用端口"""
    for port in range(start, start + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start


def start_server(port: int = None, links: list = None) -> dict:
    """启动3D地球可视化Flask服务"""
    global _server_thread, _server_port, _server_running, _links

    if _server_running:
        return {"ok": True, "port": _server_port, "url": f"http://localhost:{_server_port}", "status": "already_running"}

    if links is not None:
        _links = list(links)
    if port is None:
        port = _find_free_port()
    _server_port = port

    try:
        from flask import Flask, jsonify, send_from_directory
        import flask

        app = Flask(__name__)

        # 自动追加 gbt 目录到路径
        gbt_dir = os.path.dirname(__file__)

        @app.route("/")
        def index():
            return GLOBE_HTML

        @app.route("/api/links")
        def api_links():
            return jsonify({
                "links": _links,
                "cities": CITIES,
                "server": "GBT LinkGen 3D",
                "version": "1.0",
            })

        @app.route("/api/health")
        def health():
            return jsonify({"ok": True, "port": _server_port})

        def _run():
            global _server_running
            try:
                app.run(host="127.0.0.1", port=_server_port, debug=False, use_reloader=False)
            except Exception as e:
                L.error(f"3D server crashed: {e}")
            finally:
                _server_running = False

        _server_thread = threading.Thread(target=_run, daemon=True, name="LinkGen3D")
        _server_thread.start()
        time.sleep(0.5)
        _server_running = True

        return {
            "ok": True,
            "port": _server_port,
            "url": f"http://localhost:{_server_port}",
            "status": "started",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stop_server() -> dict:
    """停止3D服务"""
    global _server_running
    _server_running = False
    return {"ok": True, "status": "stopped"}


def status() -> dict:
    """获取服务状态"""
    return {
        "ok": _server_running,
        "port": _server_port,
        "url": f"http://localhost:{_server_port}" if _server_running else None,
        "links_count": len(_links),
    }


def add_link(url: str, short: str = "", service: str = "") -> dict:
    """添加一个链接节点到3D地球"""
    global _links
    entry = {
        "url": url,
        "short": short or url,
        "service": service,
        "time": __import__("time").strftime("%H:%M:%S"),
    }
    _links.append(entry)
    if len(_links) > 20:
        _links = _links[-20:]
    return {"ok": True, "added": entry, "total": len(_links)}
