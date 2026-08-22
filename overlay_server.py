#!/usr/bin/env python3
"""
overlay_server.py - VEMINS Real-Time Visual Overlay Server & WebGL HUD

Features:
1. Microsecond Server-Sent Events (SSE) streaming of live Dual-Layer ESP draw lists at 60 FPS.
2. Hardware-accelerated transparent Canvas/WebGL in-game overlay:
   - Layer 1: Top-Left Minimap Viewport (Hero dots, heading arrows, minion waves, jungle camps).
   - Layer 2: Main In-Game Screen Combat HUD (Overhead HP/Shield bar, Ult & Skill CD timers, Battle Spell, Distance).
   - Layer 3: Off-Screen Perimeter Edge Radar (Directional chevrons & proximity alerts).
3. Real-time in-game calibration panel with persistent saving to minimap_config.json.
4. 100% Zero-dependency (Python standard library only).
"""

import os
import sys
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, List

from esp_overlay_engine import ESPOverlayEngine
from minimap_projection import MinimapProjector


HTML_OVERLAY_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>VEMINS ESP Overlay</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
  html, body {
    width: 100%; height: 100%;
    overflow: hidden;
    background: transparent !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #fff;
  }
  #overlay-canvas {
    position: absolute;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    pointer-events: none;
    z-index: 10;
  }
  #controls-toggle {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: rgba(18, 24, 38, 0.85);
    border: 2px solid #00e5ff;
    color: #00e5ff;
    font-size: 20px;
    font-weight: bold;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 100;
    box-shadow: 0 4px 15px rgba(0, 229, 255, 0.3);
    transition: all 0.2s;
  }
  #controls-toggle:active { transform: scale(0.92); }
  #calibration-panel {
    position: fixed;
    top: 20px;
    right: 20px;
    width: 320px;
    background: rgba(12, 16, 26, 0.92);
    border: 1px solid rgba(0, 229, 255, 0.3);
    border-radius: 12px;
    padding: 16px;
    z-index: 99;
    backdrop-filter: blur(10px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
    display: none;
    max-height: 85vh;
    overflow-y: auto;
  }
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
  .panel-header h2 { font-size: 15px; color: #00e5ff; font-weight: 700; letter-spacing: 0.5px; }
  .section-title { font-size: 12px; color: #8a99ad; margin: 12px 0 6px 0; text-transform: uppercase; font-weight: 600; }
  .control-group { margin-bottom: 8px; }
  .control-label { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; color: #cbd5e1; }
  .control-slider { width: 100%; accent-color: #00e5ff; height: 6px; border-radius: 3px; }
  .toggle-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 12px; }
  .btn-save {
    width: 100%;
    margin-top: 14px;
    padding: 10px;
    background: linear-gradient(135deg, #00b4d8, #0077b6);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    cursor: pointer;
    font-size: 13px;
  }
  .status-badge {
    position: fixed;
    top: 15px;
    left: 410px;
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
    color: #38bdf8;
    z-index: 20;
    pointer-events: none;
  }
</style>
</head>
<body>

<canvas id="overlay-canvas"></canvas>
<div id="status-badge" class="status-badge">VEMINS ESP: Connecting...</div>

<div id="controls-toggle">⚙</div>

<div id="calibration-panel">
  <div class="panel-header">
    <h2>VEMINS CALIBRATION</h2>
    <span style="font-size: 11px; color: #10b981;">ACTIVE</span>
  </div>

  <div class="section-title">Minimap Viewport</div>
  <div class="control-group">
    <div class="control-label"><span>Position X</span><span id="val-map-x">75</span></div>
    <input type="range" class="control-slider" id="inp-map-x" min="0" max="800" step="1">
  </div>
  <div class="control-group">
    <div class="control-label"><span>Position Y</span><span id="val-map-y">15</span></div>
    <input type="range" class="control-slider" id="inp-map-y" min="0" max="500" step="1">
  </div>
  <div class="control-group">
    <div class="control-label"><span>Dimension (Size)</span><span id="val-map-w">320</span></div>
    <input type="range" class="control-slider" id="inp-map-w" min="150" max="600" step="2">
  </div>

  <div class="section-title">Screen Isometric Camera</div>
  <div class="control-group">
    <div class="control-label"><span>Camera Scale X</span><span id="val-cam-sx">38.0</span></div>
    <input type="range" class="control-slider" id="inp-cam-sx" min="15" max="80" step="0.5">
  </div>
  <div class="control-group">
    <div class="control-label"><span>Camera Scale Y</span><span id="val-cam-sy">27.0</span></div>
    <input type="range" class="control-slider" id="inp-cam-sy" min="10" max="60" step="0.5">
  </div>
  <div class="control-group">
    <div class="control-label"><span>HUD Height Offset</span><span id="val-cam-offy">65</span></div>
    <input type="range" class="control-slider" id="inp-cam-offy" min="20" max="150" step="1">
  </div>

  <div class="section-title">Visual Layers</div>
  <div class="toggle-row"><span>Minimap Enemies</span><input type="checkbox" id="chk-m-enemies"></div>
  <div class="toggle-row"><span>Minimap Minions</span><input type="checkbox" id="chk-m-minions"></div>
  <div class="toggle-row"><span>Minimap Jungle/Boss</span><input type="checkbox" id="chk-m-monsters"></div>
  <div class="toggle-row"><span>Overhead Combat HUD</span><input type="checkbox" id="chk-s-hud"></div>
  <div class="toggle-row"><span>Off-Screen Edge Radar</span><input type="checkbox" id="chk-s-radar"></div>

  <button class="btn-save" id="btn-save-cfg">SAVE CALIBRATION</button>
</div>

<script>
const canvas = document.getElementById('overlay-canvas');
const ctx = canvas.getContext('2d');
const statusBadge = document.getElementById('status-badge');

let currentConfig = null;
let currentFrame = null;

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// Toggle Panel
const toggleBtn = document.getElementById('controls-toggle');
const panel = document.getElementById('calibration-panel');
toggleBtn.addEventListener('click', () => {
  panel.style.display = (panel.style.display === 'block') ? 'none' : 'block';
});

// Load Config
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    currentConfig = await res.json();
    populatePanel(currentConfig);
  } catch (e) {
    console.error("Config load failed", e);
  }
}

function populatePanel(cfg) {
  const m = cfg.minimap || {};
  const c = cfg.camera || {};
  const r = cfg.render_settings || {};

  document.getElementById('inp-map-x').value = m.pos_x || 75;
  document.getElementById('val-map-x').innerText = m.pos_x || 75;

  document.getElementById('inp-map-y').value = m.pos_y || 15;
  document.getElementById('val-map-y').innerText = m.pos_y || 15;

  document.getElementById('inp-map-w').value = m.width || 320;
  document.getElementById('val-map-w').innerText = m.width || 320;

  document.getElementById('inp-cam-sx').value = c.scale_x || 38.0;
  document.getElementById('val-cam-sx').innerText = c.scale_x || 38.0;

  document.getElementById('inp-cam-sy').value = c.scale_y || 27.0;
  document.getElementById('val-cam-sy').innerText = c.scale_y || 27.0;

  document.getElementById('inp-cam-offy').value = c.hud_offset_y || 65;
  document.getElementById('val-cam-offy').innerText = c.hud_offset_y || 65;

  document.getElementById('chk-m-enemies').checked = r.minimap_show_enemies !== false;
  document.getElementById('chk-m-minions').checked = r.minimap_show_minions !== false;
  document.getElementById('chk-m-monsters').checked = r.minimap_show_monsters !== false;
  document.getElementById('chk-s-hud').checked = r.screen_show_overhead_hp !== false;
  document.getElementById('chk-s-radar').checked = r.screen_show_edge_radar !== false;
}

// Live Input Event Listeners
function setupInput(id, valId, callback) {
  const el = document.getElementById(id);
  const valEl = document.getElementById(valId);
  el.addEventListener('input', (e) => {
    valEl.innerText = e.target.value;
    callback(parseFloat(e.target.value));
  });
}

setupInput('inp-map-x', 'val-map-x', v => { if(currentConfig) currentConfig.minimap.pos_x = v; });
setupInput('inp-map-y', 'val-map-y', v => { if(currentConfig) currentConfig.minimap.pos_y = v; });
setupInput('inp-map-w', 'val-map-w', v => { if(currentConfig) { currentConfig.minimap.width = v; currentConfig.minimap.height = v; } });
setupInput('inp-cam-sx', 'val-cam-sx', v => { if(currentConfig) currentConfig.camera.scale_x = v; });
setupInput('inp-cam-sy', 'val-cam-sy', v => { if(currentConfig) currentConfig.camera.scale_y = v; });
setupInput('inp-cam-offy', 'val-cam-offy', v => { if(currentConfig) currentConfig.camera.hud_offset_y = v; });

document.getElementById('btn-save-cfg').addEventListener('click', async () => {
  if (!currentConfig) return;
  currentConfig.render_settings.minimap_show_enemies = document.getElementById('chk-m-enemies').checked;
  currentConfig.render_settings.minimap_show_minions = document.getElementById('chk-m-minions').checked;
  currentConfig.render_settings.minimap_show_monsters = document.getElementById('chk-m-monsters').checked;
  currentConfig.render_settings.screen_show_overhead_hp = document.getElementById('chk-s-hud').checked;
  currentConfig.render_settings.screen_show_edge_radar = document.getElementById('chk-s-radar').checked;

  try {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentConfig)
    });
    alert("Calibration Saved!");
  } catch (e) {
    alert("Save Failed: " + e);
  }
});

// SSE Telemetry Stream
function startStream() {
  const evtSource = new EventSource('/stream');
  evtSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      currentFrame = data;
      statusBadge.innerText = `VEMINS ESP: ${data.in_match ? 'MATCH LIVE' : 'IDLE'} | Enemies: ${data.enemies_count || 0}`;
      statusBadge.style.color = data.in_match ? '#10b981' : '#f59e0b';
    } catch (err) {}
  };
  evtSource.onerror = () => {
    statusBadge.innerText = 'VEMINS ESP: Connecting...';
    statusBadge.style.color = '#ef4444';
  };
}

const heroImages = {};
function getHeroImage(id) {
  if (!id) return null;
  if (!heroImages[id]) {
    const img = new Image();
    img.src = `/assets/heroes/${id}.png`;
    heroImages[id] = img;
  }
  return heroImages[id];
}

// Render Loop (60 FPS)
function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (currentFrame && currentFrame.items) {
    const scaleX = canvas.width / (currentConfig?.screen?.width || 2400);
    const scaleY = canvas.height / (currentConfig?.screen?.height || 1080);

    for (const item of currentFrame.items) {
      const x = item.x * scaleX;
      const y = item.y * scaleY;

      // 1. Minimap Box
      if (item.type === 'minimap_box') {
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(x, y, item.w * scaleX, item.h * scaleY);
      }

      // 2. Minimap Minions
      else if (item.type === 'minimap_minion') {
        ctx.beginPath();
        ctx.arc(x, y, (item.radius || 3.5) * scaleX, 0, Math.PI * 2);
        ctx.fillStyle = item.camp === 1 ? '#38bdf8' : '#f87171';
        ctx.fill();
      }

      // 3. Minimap Monsters
      else if (item.type === 'minimap_monster') {
        ctx.beginPath();
        ctx.arc(x, y, (item.radius || 7.0) * scaleX, 0, Math.PI * 2);
        ctx.fillStyle = '#a855f7';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // 4. Minimap Heroes (Draws Round Avatar Portrait)
      else if (item.type === 'minimap_hero') {
        const rad = (item.radius || 9.0) * scaleX;
        const img = getHeroImage(item.hero_id);

        ctx.save();
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.clip();

        if (img && img.complete && img.naturalWidth > 0) {
          ctx.drawImage(img, x - rad, y - rad, rad * 2, rad * 2);
        } else {
          ctx.fillStyle = item.is_local ? '#22c55e' : (item.is_ally ? '#0284c7' : '#ef4444');
          ctx.fill();
          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 9px sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(item.hero_id || '?', x, y);
        }
        ctx.restore();

        // Outer Ring
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.strokeStyle = item.is_local ? '#22c55e' : (item.is_ally ? '#38bdf8' : '#ef4444');
        ctx.lineWidth = 2.0;
        ctx.stroke();
      }

      // 5. Minimap Direction Arrows
      else if (item.type === 'minimap_arrow') {
        const ex = item.end_x * scaleX;
        const ey = item.end_y * scaleY;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(ex, ey);
        ctx.strokeStyle = item.color === 'self' ? '#22c55e' : '#fca5a5';
        ctx.lineWidth = 2.0;
        ctx.stroke();
      }

      // 6. Overhead Screen Combat HUD (Main Screen)
      else if (item.type === 'screen_overhead_hud') {
        const barW = 100 * scaleX;
        const barH = 8 * scaleY;
        const barX = x - (barW / 2);
        const barY = y - 24 * scaleY;

        // Hero Portrait Badge next to HP
        const avatarRad = 12 * scaleX;
        const avatarX = barX - avatarRad - 6;
        const avatarY = barY + (barH / 2);
        const img = getHeroImage(item.hero_id);

        ctx.save();
        ctx.beginPath();
        ctx.arc(avatarX, avatarY, avatarRad, 0, Math.PI * 2);
        ctx.clip();
        if (img && img.complete && img.naturalWidth > 0) {
          ctx.drawImage(img, avatarX - avatarRad, avatarY - avatarRad, avatarRad * 2, avatarRad * 2);
        } else {
          ctx.fillStyle = '#ef4444';
          ctx.fill();
        }
        ctx.restore();

        ctx.beginPath();
        ctx.arc(avatarX, avatarY, avatarRad, 0, Math.PI * 2);
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Background
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(barX - 2, barY - 2, barW + 4, barH + 4);

        // Fill HP
        const hpPct = Math.max(0, Math.min(1, item.hp_pct || 1.0));
        ctx.fillStyle = hpPct > 0.4 ? '#22c55e' : (hpPct > 0.2 ? '#f59e0b' : '#ef4444');
        ctx.fillRect(barX, barY, barW * hpPct, barH);

        // Ult Badge
        const ultReady = item.ult_ready;
        const ultText = ultReady ? 'ULT: READY' : `ULT: ${item.ult_cd_s}s`;
        ctx.fillStyle = ultReady ? '#10b981' : '#f97316';
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(ultText, x, barY - 6 * scaleY);

        // Distance & Hero Info
        ctx.fillStyle = '#cbd5e1';
        ctx.font = '10px sans-serif';
        ctx.fillText(`Hero ${item.hero_id} [Lv.${item.level}] (${item.distance_m}m)`, x, barY + barH + 12 * scaleY);
      }

      // 7. Off-Screen Edge Radar Chevrons
      else if (item.type === 'screen_edge_indicator') {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate((item.angle_deg || 0) * Math.PI / 180);

        // Draw Chevron
        ctx.beginPath();
        ctx.moveTo(12 * scaleX, 0);
        ctx.lineTo(-8 * scaleX, -8 * scaleY);
        ctx.lineTo(-4 * scaleX, 0);
        ctx.lineTo(-8 * scaleX, 8 * scaleY);
        ctx.closePath();
        ctx.fillStyle = item.ult_ready ? '#ef4444' : '#f59e0b';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.restore();

        // Label
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`${item.hero_id} (${item.distance_m}m)`, x, y + 18 * scaleY);
      }
    }
  }

  requestAnimationFrame(render);
}

loadConfig();
startStream();
render();
</script>
</body>
</html>
"""


class OverlayHTTPHandler(BaseHTTPRequestHandler):
    engine: Optional[ESPOverlayEngine] = None
    lock = threading.Lock()

    def log_message(self, format, *args):
        pass  # Suppress normal HTTP access logs

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html", "/overlay"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML_OVERLAY_PAGE.encode("utf-8"))

        elif parsed.path == "/api/config":
            if self.engine and self.engine.projector:
                data = self.engine.projector.config
            else:
                data = {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif parsed.path.startswith("/assets/"):
            rel_path = parsed.path[len("/assets/"):]
            full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", rel_path)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                self.send_response(200)
                if full_path.endswith(".png"):
                    self.send_header("Content-Type", "image/png")
                elif full_path.endswith(".json"):
                    self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "max-age=86400")
                self.end_headers()
                with open(full_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()

        elif parsed.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            try:
                while True:
                    if self.engine:
                        snap = self.engine.fetch_snapshot()
                        items = [item.to_dict() for item in self.engine.build_draw_list(snap)]
                        payload = {
                            "in_match": snap.in_match,
                            "battle_state": snap.battle_state,
                            "enemies_count": len(snap.enemies),
                            "minions_count": len(snap.soldiers),
                            "monsters_count": len(snap.monsters),
                            "items": items,
                            "enemies": [e.to_dict() for e in snap.enemies],
                            "allies": [a.to_dict() for a in snap.allies],
                            "local_player": snap.local_player.to_dict() if snap.local_player else None,
                            "soldiers": [s.to_dict() for s in snap.soldiers],
                            "monsters": [m.to_dict() for m in snap.monsters]
                        }
                    else:
                        payload = {"in_match": False, "items": [], "enemies": [], "allies": []}

                    msg = f"data: {json.dumps(payload)}\n\n"
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(0.016)  # ~60 FPS
            except Exception:
                pass

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            try:
                new_cfg = json.loads(body.decode("utf-8"))
                if self.engine and self.engine.projector:
                    self.engine.projector.config = new_cfg
                    self.engine.projector._update_cached_transforms()
                    self.engine.projector.save_config()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "msg": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_server(port: int = 8080):
    engine = ESPOverlayEngine()
    engine.connect()
    OverlayHTTPHandler.engine = engine

    server = HTTPServer(("0.0.0.0", port), OverlayHTTPHandler)
    print("=================================================================")
    print(f"      VEMINS ESP - VISUAL OVERLAY SERVER RUNNING                ")
    print("=================================================================")
    print(f"[✓] Overlay URL     : http://127.0.0.1:{port}/overlay")
    print(f"[✓] Calibration API : http://127.0.0.1:{port}/api/config")
    print(f"[✓] 60 FPS Stream   : http://127.0.0.1:{port}/stream")
    print("=================================================================")
    print("Open http://127.0.0.1:8080 in any Android floating browser or overlay!")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down overlay server...")
        server.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
