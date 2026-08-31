# VEMINS // ESP (v1.3.0-PROD)

<div align="center">
  <img src="vemins_overlay_app/app/src/main/res/drawable/ic_bubble.xml" width="96" height="96" alt="Vemins ESP Logo" />
  <h3>High-Precision Read-Only Memory Telemetry & Transparent Tactical Overlay</h3>
  <p><b>Obsidian & Stark White Industrial Design • True 3D Perspective Engine • Zero-Injection Security • 60/120 FPS DMA Direct Surface</b></p>

  [![Python Tests](https://img.shields.io/badge/Tests-171%2F171%20Passing-30D158?style=flat-square)](tests/)
  [![Platform](https://img.shields.io/badge/Platform-Android%20ARM64-FFFFFF?style=flat-square&logo=android)](vemins_overlay_app/)
  [![Architecture](https://img.shields.io/badge/Architecture-Bionic%20Native%20%2B%20Kotlin%202.0-FFFFFF?style=flat-square)](ARCHITECTURE.md)
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
                 ▼  (TCP Stream @ 127.0.0.1:9999 / Binary Telemetry)
  [ VeminsESP Android App (Kotlin 2.0 / SurfaceView) ]
     ├── True 3D Perspective Projection Engine (Depth Division Math)
     ├── Dynamic Minimap Rotation Engine (Center-Anchored Angle Sync)
     ├── 500ms Self-Healing Supervisor Watchdog
     └── In-Game Floating Mod Menu & Command Center Dashboard
```

---

## Key Features

### 1. True 3D Perspective Projection Engine
* **Non-Linear Depth Division**: Replaced flat linear scaling with a physics-accurate 3D perspective depth equation:
  $$Z_{\text{depth}} = H_{\text{cam}} + iso_y \cdot \cos(\text{pitch})$$
  $$\text{persp\_scale} = \frac{H_{\text{cam}}}{Z_{\text{depth}}}$$
* **Long-Range Target Precision**: Accurate overhead badge alignment for extreme-range snipes (Novaria S2, Layla Ultimate, Flameshot, Moskov S1/S3) with zero badge drift.
* **Vertical Head Lift Compensation**: Dynamically scales overhead health bars and cooldown badges directly above hero 3D models at any camera distance.

### 2. Synchronized Minimap Rotation Engine
* **Center-Anchored Rotation**: Rotates world coordinates smoothly around the minimap's center anchor without offset drift or diamond clipping.
* **Heading Arrow Synchronization**: Hero heading and velocity direction vectors automatically synchronize with custom minimap rotation angles.
* **Fixed Radar Frame**: Bounding UI container remains locked to screen coordinates while internal radar blips and rotations move fluidly.

### 3. Dual-Layer Decoupled Tactical HUD
* **Layer 1: Minimap Radar Viewport (Top-Left)**:
  * Hero marker blips with directional heading arrows (Enemies in Crimson, Allies in Slate, Self in Emerald).
  * Real-time lane minion waves & siege clusters.
  * Jungle objective timers (Lord, Turtle, Buff camps).
  * 45° Diamond rotation mode & dynamic angle slider.
* **Layer 2: 3D World Overhead Combat HUD (On-Screen & Edge Radar)**:
  * Dual-layer HP & active shield bars over enemy characters.
  * Skill cooldown timers & Ultimate readiness badges.
  * Battle spell tracking (Flicker, Retribution, Purify, Flameshot).
  * Off-screen 360° perimeter chevrons with dynamic distance clamps.

### 4. Studio-Grade Black & White Design System
* **Monochrome Precision**: Built entirely in Obsidian Void (`#000000` / `#0C0C0C`), Hairline Zinc (`#2C2C2E`), and Stark White (`#FFFFFF`).
* **Tactile Dual-Stepper Sliders**: Precision `[-]` and `[+]` micro-stepping controls flanking thin 2dp slider tracks with live monospace readouts.
* **Simplified Human-Friendly Settings**: Intuitive labels for 3D Spread Width, Distance Depth, Floating Height, and Top Screen Enemy Status Strip.
* **Dynamic Floating Puck**: Morphing squircle trigger with magnetic edge-docking, live FPS/latency capsule expansion, and one-touch double-tap ghost mode.

### 5. Bulletproof Pipeline Reliability
* **Dynamic Heap Serialization (`json_buffer_t`)**: Dynamic memory allocation eliminates JSON truncation crashes.
* **Self-Healing Watchdog**: The `RenderThread` is monitored by a 500ms supervisor loop that auto-revives the thread upon interruption.
* **Persistent Camera Anchoring**: When `localPlayer` is temporarily null during respawn, coordinates smoothly anchor to `lastKnownLocalX/Y`.

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
├── minimap_projection.py        # Python 3D perspective & 2D minimap projection engine
├── esp_overlay_engine.py        # Python headless overlay rendering engine
├── tests/                       # 171-test automated regression & mathematical test suite
│   ├── test_adversarial_stress.py
│   ├── test_blackbox_transitions.py
│   ├── test_daemon_protocol.py
│   ├── test_e2e_refactor.py
│   ├── test_kotlin_engine_math.py
│   └── test_world_snapshot.py
├── vemins_overlay_app/          # Production Android Studio / Gradle project
│   ├── build_apk.sh             # Standalone offline AAPT2/D8/Kotlinc APK build toolchain
│   ├── veminsEsp.apk            # Signed production APK release
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

### 1. Run Automated Test Suite
```bash
pytest
```
*Expected Output: `171 passed in ~2.5s`*

### 2. Build Native Daemon & ESP Engine
```bash
bash build_vemins_daemon.sh
bash build_vemins_esp.sh
```

### 3. Launch Android Floating Overlay App
Install and launch `vemins_overlay_app/veminsEsp.apk` on Android ARM64, grant Overlay and Root permissions, and tap **Start Overlay**.
