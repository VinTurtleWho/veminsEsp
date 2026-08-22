# VEMINS // ESP (v1.2.0-PROD)

<div align="center">
  <img src="vemins_overlay_app/app/src/main/res/drawable/ic_bubble.xml" width="96" height="96" alt="Vemins ESP Logo" />
  <h3>High-Precision Read-Only Memory Telemetry & Transparent Tactical Overlay</h3>
  <p><b>Obsidian & Stark White Industrial Design • Zero-Injection Security • 60/120 FPS DMA Direct Surface</b></p>

  [![Python Tests](https://img.shields.io/badge/Tests-113%2F113%20Passing-30D158?style=flat-square)](tests/)
  [![Platform](https://img.shields.io/badge/Platform-Android%20ARM64-FFFFFF?style=flat-square&logo=android)](vemins_overlay_app/)
  [![Architecture](https://img.shields.io/badge/Architecture-Bionic%20Native%20%2B%20Kotlin-FFFFFF?style=flat-square)](ARCHITECTURE.md)
  [![License](https://img.shields.io/badge/License-MIT-FFFFFF?style=flat-square)](LICENSE)
</div>

---

## Overview

**VeminsESP** is a low-latency, read-only memory telemetry daemon and floating tactical HUD suite engineered for Mobile Legends: Bang Bang (ARM64).

Operating completely outside the game process via direct `/proc/$PID/mem` kernel reads, VeminsESP requires **zero in-game memory modification, zero function hooking (no Frida / Substrate / ptrace injection), and zero asset manipulation**. All overlays render onto an independent, hardware-accelerated transparent surface view.

```
  [ MLBB Target Process (Untouched) ]
                 │
                 ▼  (Read-Only pread() from /proc/$PID/mem)
  [ vemins_daemon (Native C Bionic Core) ]
     ├── Dynamic Self-Growing Heap Buffer (json_buffer_t, 0% Truncation)
     ├── Strict isfinite() Sanitization (NaN / Inf immune)
     └── Zero-Syscall ELF Header & PID Latching
                 │
                 ▼  (TCP Stream @ 127.0.0.1:9999)
  [ VeminsESP Android App (Kotlin 2.0 / SurfaceView) ]
     ├── 500ms Self-Healing Supervisor Watchdog
     ├── Double-Buffered Canvas Locking Fallback
     ├── Persistent Camera Tracking & Respawn Continuity
     └── In-Game Floating Mod Menu & Command Center Dashboard
```

---

## Key Features

### 1. Dual-Layer Decoupled Tactical HUD
* **Layer 1: Minimap Radar Viewport (Top-Left)**:
  * Hero marker blips with directional heading arrows (Enemies in Crimson, Allies in Slate, Self in Emerald).
  * Real-time lane minion waves & clusters.
  * Jungle objective timers (Lord, Turtle, Buff camps).
  * 45° Diamond rotation mode & Y-axis inversion support.
* **Layer 2: 3D World Overhead Combat HUD (On-Screen & Edge Radar)**:
  * Dual-layer HP & active shield bars over enemy characters.
  * Skill cooldown timers & Ultimate readiness badges.
  * Battle spell tracking (Flicker, Retribution, Purify, Flameshot).
  * Off-screen 360° perimeter chevrons with dynamic distance clamps.

### 2. Studio-Grade Black & White Design System
* **Monochrome Precision**: Built entirely in Obsidian Void (`#000000` / `#0C0C0C`), Hairline Zinc (`#2C2C2E`), and Stark White (`#FFFFFF`). Zero glowing neon cyber-slop.
* **Tactile Dual-Stepper Sliders**: Precision `[-]` and `[+]` micro-stepping controls flanking thin 2dp slider tracks with live monospace readouts.
* **Dynamic Floating Puck**: Morphing squircle trigger with magnetic edge-docking, live FPS/latency capsule expansion, and one-touch double-tap 5% ghost mode.

### 3. Bulletproof Pipeline Reliability
* **Dynamic Heap Serialization (`json_buffer_t`)**: Replaces fixed stack buffers with dynamic memory allocation to eliminate JSON truncation crashes forever.
* **Self-Healing Watchdog**: The `RenderThread` is wrapped in `Throwable` handlers and monitored by a 500ms supervisor loop that auto-revives the thread in $\le 500\text{ms}$ upon any interruption.
* **Persistent Camera Anchoring**: When `localPlayer` is temporarily null during respawn, coordinates smoothly anchor to `lastKnownLocalX/Y`, preventing HUD jumps.

---

## Project Structure

```
.
├── vemins_daemon.c              # Core Native C ARM64 read-only telemetry daemon
├── build_vemins_daemon.sh       # Compiler script for native daemon
├── vemins_esp.cpp               # Standalone C++ / OpenGL ES overlay engine
├── build_vemins_esp.sh          # Compiler script for C++ engine
├── offsets.json                 # Game memory offsets & data structure maps
├── minimap_config.json          # Default overlay dimensions and geometry config
├── tests/                       # 113-test automated regression & protocol test suite
│   ├── test_blackbox_transitions.py
│   ├── test_daemon_protocol.py
│   ├── test_kotlin_engine_math.py
│   └── test_world_snapshot.py
├── vemins_overlay_app/          # Production Android Studio / Gradle project
│   ├── build_apk.sh             # Standalone offline AAPT2/D8/Kotlinc APK build toolchain
│   ├── veminsEsp.apk            # Signed production APK release (36 MB)
│   └── app/src/main/
│       ├── AndroidManifest.xml
│       ├── java/com/vemins/esp/ # Kotlin engine, math, models, services & UI
│       └── res/                 # Obsidian drawables, layouts, styles, and vector assets
├── ESP_DESIGN_SPEC.md           # Visual layout & rendering layer specifications
├── FIELD_MAP.md                 # Reverse-engineered memory struct fields & offsets
├── ARCHITECTURE.md              # Deep-dive system architecture & protocol specification
└── QUICKSTART.md                # Fast operator installation & calibration guide
```

---

## Quick Start

### 1. Build Native Daemon
```bash
./build_vemins_daemon.sh
```

### 2. Build Android Overlay APK
```bash
cd vemins_overlay_app
./build_apk.sh
```

### 3. Install & Launch
1. Install `vemins_overlay_app/veminsEsp.apk` on your target device.
2. Launch the app, grant the **Display over other apps** overlay permission, and tap **"START OVERLAY"**.
3. Launch Mobile Legends — the overlay will automatically hook the PID and begin streaming live telemetry at 60/120 FPS.

---

## Verification & Tests

Run the complete 113-test automated test suite:
```bash
pytest tests/
```

---

## Security & Disclaimer

> [!IMPORTANT]
> **VeminsESP** is strictly read-only and designed for educational, mathematical coordinate projection, and reverse-engineering research. It does not write to target memory, does not modify game code, and does not alter server packets. Use responsibly in accordance with local regulations and game terms.
