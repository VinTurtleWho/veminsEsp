# Project: VEMINS ESP Architectural Refactor & UI Redesign

## Architecture
VEMINS ESP is refactored from an external daemon / TCP socket model into an ultra-low latency, in-app native JNI/NDK perception engine (`libvemins_engine.so`) and hardware-accelerated monochrome floating overlay HUD.

```
   ┌────────────────────────────────────────────────────────────────────────┐
   │                         Android App Process                            │
   │                                                                        │
   │  ┌─────────────────────────┐         ┌──────────────────────────────┐  │
   │  │   Obsidian Dashboard    │         │  Hardware SurfaceView HUD    │  │
   │  │    (MainActivity.kt)    │         │  (FloatingOverlayService.kt) │  │
   │  └───────────┬─────────────┘         └──────────────┬───────────────┘  │
   │              │                                      │                  │
   │  Throttled   │ Telemetry (3-4 Hz)     60/120 FPS    │ Surface Pass     │
   │              ▼                                      ▼                  │
   │  ┌──────────────────────────────────────────────────────────────────┐  │
   │  │                    libvemins_engine.so (NDK)                     │  │
   │  │                                                                  │  │
   │  │   ┌────────────────────┐   Direct   ┌────────────────────────┐   │  │
   │  │   │ JNI Bridge & State │◄───────────┤ Dear ImGui ES3 Renderer│   │  │
   │  │   │  (DirectByteBuffer)│   Buffer   │ (ANativeWindow Surface)│   │  │
   │  │   └─────────▲──────────┘            └────────────▲───────────┘   │  │
   │  │             │                                    │               │  │
   │  │             │   FrameSnapshotBinary (Zero-Alloc) │               │  │
   │  │             └──────────────────┬─────────────────┘               │  │
   │  │                                │                                 │  │
   │  │                 ┌──────────────┴──────────────┐                  │  │
   │  │                 │    Batch Memory Reader      │                  │  │
   │  │                 │ (Cached PID, pread / DMA)   │                  │  │
   │  │                 └──────────────┬──────────────┘                  │  │
   │  └────────────────────────────────┼─────────────────────────────────┘  │
   └───────────────────────────────────┼────────────────────────────────────┘
                                       │
                   Direct /proc/$PID/mem (Read-Only)
                                       │
                                       ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                  Game Process: com.mobile.legends                      │
   │   libcsharp.so ──► LogicBattleManager ──► Heroes / Minions / Monsters   │
   └────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Daemon & Socket Elimination | Eliminate `vemins_daemon`, TCP socket server (`127.0.0.1:9999`), and JSON stringification | M1 | Survey / R1 |
| 2 | In-App Native Engine NDK | Build `libvemins_engine.so` with direct `/proc/$PID/mem` read-only DMA access | M1 | Survey / R1 |
| 3 | Binary Schema (Zero-Copy) | Packed `FrameSnapshotBinary` struct (4.8 KB) for zero-allocation frame passing | M1 | Survey / R1 |
| 4 | PID & Memory Map Caching | Cache `s_cached_pid` & `s_libcsharp_base`, validate with 4-byte ELF magic check | M1 | Survey / R1 |
| 5 | Sub-Millisecond Reader Loop | Contiguous batch `pread` blocks reducing syscalls to achieve < 1.0 ms reading latency | M1 | Survey / R1 |
| 6 | JNI Bindings & DirectBuffer | Kotlin `VeminsNativeEngine` bindings with `DirectByteBuffer` zero-copy polling | M1 | Survey / R1 |
| 7 | Deterministic Root Chain | `libcsharp.so + 0x7680928` -> `Il2CppClass + 0xb8` -> `static_fields + 0x00` -> `LogicBattleManager*` | M2 | Survey / R2 |
| 8 | Gate 8 Local Hero Identity | Authoritative `m_RealSelfPlayer (+0x200)` and fallback `m_LocalPlayerLogic (+0x0a0)` | M2 | Survey / R2 |
| 9 | 10-Player Dictionary Parsing | Ingest `m_dicPlayerLogic (+0x0a8)` with 24B stride and `hashCode >= 0` tombstone filtering | M2 | Survey / R2 |
| 10 | 64-Bit Cartesian Coordinates | Parse `m_dRealPosX (+0x268)` and `m_dRealPosY (+0x270)` in range [-52.0, +52.0] | M2 | Survey / R2 |
| 11 | Complete Entity Perception | Decode minions (`+0x128`), monsters (`+0x0b0`), base nexus/towers (`+0xd0..+0xe8`), fountains (`+0xc0/+0xc8`) | M2 | Survey / R2 |
| 12 | Coordinate Continuity & Camera EMA | Preserve `lastKnownLocalX/Y` with EMA ($\alpha=0.35$) on death/respawn; no coordinate snap | M2 | Survey / R2 |
| 13 | NaN / Inf Sanitization | Strict `isfinite()` validation on all float/double coordinates and HP values | M2 | Survey / R2 |
| 14 | Gate Bypass Invariant | Never gate rendering on `battle_state` (`_m_eState (+0x180)`); active when entities exist | M2 | Survey / R2 |
| 15 | Draggable Status Pill | Minimalist squircle badge with monochrome "V" glyph, live FPS, and latency readout | M3 | Survey / R3 |
| 16 | Collapsible Tactical HUD Window | Dark frosted card (`#0C0C0C`, 85% alpha, 1px border) with Minimap Radar, Combat HUD, Entity Layers | M3 | Survey / R3 |
| 17 | Continuous Rotation & Calibration | 0°..360° rotation slider, live X/Y offset and scale sliders in Tactical HUD | M3 | Survey / R3 |
| 18 | 1-Tap Instant Hide / Stow | Dedicated dismiss button with zero touch interference on game viewport | M3 | Survey / R3 |
| 19 | Strict Monochrome Aesthetic | Black & White / Deep Charcoal palette (`#000000`, `#0A0A0A`, `#0C0C0C`, `#1A1A1A`, `#FFFFFF`, `#888888`) | M3 | Survey / R3 |
| 20 | Obsidian Host Dashboard | Overhaul `MainActivity` into sleek, industrial Obsidian & Stark White control center | M3 | Survey / R4 |
| 21 | Decoupled UI Telemetry (3-4 Hz) | Decouple 60/120 FPS render loop from UI telemetry updates throttled to 3-4 Hz | M3 | Survey / R4 |
| 22 | Zero-Allocation Render Loop | Zero heap allocation in per-frame render loop for 0 GC stutter | M3 | Survey / R4 |
| 23 | Offline APK Build & NDK Packaging | Standalone `build_apk.sh` compiling native `libvemins_engine.so` and bundling into APK | M3 | Survey / R4 |
| 24 | E2E Test Infrastructure | Multi-tier test suite covering Tiers 1-4 for perception, schema, projection math, and transitions | E2E | Survey / Verification |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Native JNI/NDK Perception Engine & Binary Schema | Implement `libvemins_engine.so`, `engine_schema.h`, `memory_reader.cpp`, `jni_bridge.cpp`, and Kotlin `VeminsNativeEngine.kt` | none | PLANNED |
| M2 | Robust Entity Perception & Invariant Adherence | 10 heroes, minions, monsters, towers, Gate 8 root, EMA camera continuity, `isfinite()` sanitization, tombstone filtering | M1 | PLANNED |
| M3 | Dear ImGui Floating Overlay & Modern Obsidian Host App | Draggable status pill, collapsible tactical HUD, 1-tap stow, monochrome palette, 3-4 Hz telemetry, 0 GC render loop, `build_apk.sh` packaging | M1, M2 | PLANNED |
| E2E | E2E Testing Track | Independent opaque-box test suite (Tiers 1-4), publishing `TEST_READY.md` | none | PLANNED |
| M4 | Final Milestone & Adversarial Hardening | Pass 100% E2E test suite (Phase 1) + Adversarial coverage hardening (Phase 2, Tier 5) | M3, E2E | PLANNED |

## Interface Contracts

### C++ Native Engine (`engine_schema.h`) <-> Kotlin NDK Bridge (`VeminsNativeEngine.kt`)
- Struct: `FrameSnapshotBinary` (packed, 4,880 bytes).
- Functions:
  - `nativeInit() -> Boolean`
  - `nativeRelease() -> Void`
  - `nativeSetMemFd(fd: Int, pid: Int) -> Boolean`
  - `nativePollSnapshot(buffer: ByteBuffer) -> Int` (returns 1 on success, 0 on no update, -1 on process dead)
  - `nativeGetTelemetry(outStats: FloatArray) -> Void` [fps, latency_ms, hero_count, minion_count, monster_count]
  - `nativeSurfaceCreated(surface: Surface, width: Int, height: Int) -> Boolean`
  - `nativeSurfaceChanged(surface: Surface, width: Int, height: Int) -> Void`
  - `nativeSurfaceDestroyed() -> Void`
  - `nativeDispatchTouch(action: Int, x: Float, y: Float) -> Void`
  - `nativeUpdateConfig(...) -> Void`

### Perception Engine <-> Overlay Rendering Pipeline
- Input: `FrameSnapshotBinary` direct buffer.
- Coordinate range: `pos_x, pos_y` normalized in $[-52.0, +52.0]$.
- Sanitization: All floating-point fields sanitized via `std::isfinite()`.
- Local Hero: Gate 8 bound via `is_local == 1`.
- Camera fallback: `lastKnownLocalX/Y` smoothed with EMA $\alpha = 0.35$.

## Code Layout
- Native C++ Perception Engine: `vemins_overlay_app/app/src/main/cpp/` (or `native/`)
  - `engine_schema.h` — Packed binary schema (`FrameSnapshotBinary`, `HeroEntityBinary`, etc.)
  - `memory_reader.h`, `memory_reader.cpp` — Contiguous batch DMA memory reading, PID caching, ELF validation
  - `entity_parser.h`, `entity_parser.cpp` — Invariant decoding, Gate 8 binding, dictionary traversal, EMA continuity
  - `jni_bridge.cpp` — JNI export functions
  - `CMakeLists.txt` / build scripts
- Android Application: `vemins_overlay_app/app/src/main/`
  - `java/com/vemins/esp/engine/VeminsNativeEngine.kt` — JNI wrapper & direct buffer management
  - `java/com/vemins/esp/model/FrameSnapshotBinary.kt` / `FrameSnapshot.kt` — Binary buffer reader / model
  - `java/com/vemins/esp/ui/MainActivity.kt` — Modern Obsidian & Stark White dashboard (3-4 Hz telemetry)
  - `java/com/vemins/esp/ui/floating/FloatingMenuManager.kt` — Draggable status pill & collapsible Tactical HUD
  - `java/com/vemins/esp/view/OverlaySurfaceView.kt` — Zero-allocation 60/120 FPS hardware canvas
  - `res/values/colors.xml`, `res/values/styles.xml` — Strict monochrome palette
  - `res/layout/layout_floating_status_pill.xml` / `layout_floating_trigger.xml` — Monogram "V" pill
  - `res/layout/layout_floating_mod_menu.xml` — Collapsible tactical card
  - `res/layout/activity_main.xml` — Industrial Obsidian dashboard
- Build Script: `vemins_overlay_app/build_apk.sh`
- Tests: `tests/` — Automated Python regression & E2E suite
