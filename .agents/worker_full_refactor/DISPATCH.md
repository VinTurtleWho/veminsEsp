## 2026-08-30T20:34:35Z
You are worker_full_refactor (teamwork_preview_worker).
Working Directory: /data/data/com.termux/files/home/veminsEsp/.agents/worker_full_refactor
Parent Conversation ID: 512a4623-26c6-4adf-86f7-765c852fa504

### Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Authoritative Files (Read First)
1. /data/data/com.termux/files/home/veminsEsp/ORIGINAL_REQUEST.md (MANDATORY: read completely)
2. /data/data/com.termux/files/home/veminsEsp/PROJECT.md
3. /data/data/com.termux/files/home/veminsEsp/TEST_INFRA.md
4. /data/data/com.termux/files/home/veminsEsp/TEST_READY.md
5. Architectural Blueprints & Survey Findings:
   - /data/data/com.termux/files/home/veminsEsp/.agents/explorer_m1_native/handoff.md
   - /data/data/com.termux/files/home/veminsEsp/.agents/explorer_m1_kotlin/handoff.md
   - /data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_m1_benchmarks/handoff.md
   - /data/data/com.termux/files/home/veminsEsp/.agents/explorer_survey_ui_build/handoff.md

### Task Objectives
Implement the complete VEMINS ESP architectural refactor and UI redesign:

1. **M1 & M2: Native C++ Perception Engine (`libvemins_engine.so`) & Memory Invariants**:
   - Create `vemins_overlay_app/app/src/main/cpp/`:
     - `engine_schema.h`: packed binary structs (`FrameSnapshotBinary`, `HeroEntityBinary`, `SoldierEntityBinary`, `MonsterEntityBinary`, `TowerEntityBinary`, `AbilityInfoBinary`, `MinimapConfigBinary`, `EngineConfigBinary`, `TelemetryBinary`). Total frame struct size: exactly 4,880 bytes, magic `0x56454D53`, version `1`.
     - `memory_reader.h` & `memory_reader.cpp`: Direct `/proc/$PID/mem` read-only DMA / `pread` batch reading, cached PID & base address with `kill(pid, 0)` and 4-byte ELF validation (`0x7F 'E' 'L' 'F'`).
     - `entity_parser.h` & `entity_parser.cpp`: Gate 8 local hero binding (`m_RealSelfPlayer +0x200`, fallback `m_LocalPlayerLogic +0x0a0`), 10-player dictionary parsing with 24-byte stride and `hashCode >= 0` tombstone filtering, Cartesian coordinates clamped to [-52.0, +52.0], camera smoothing with EMA alpha=0.35 on death/respawn (`lastKnownLocalX/Y`), minions (`+0x128`), monsters (`+0x0b0`), towers (`+0xd0..+0xe8`), gate bypass invariant (active whenever valid player entities exist), `std::isfinite()` sanitization on all float/double values.
     - `jni_bridge.cpp`: JNI export functions for `VeminsNativeEngine` (`nativeInit`, `nativeRelease`, `nativeSetMemFd`, `nativePollSnapshot` using DirectByteBuffer, `nativeGetTelemetry`, `nativeSurfaceCreated`, `nativeSurfaceChanged`, `nativeSurfaceDestroyed`, `nativeDispatchTouch`, `nativeUpdateConfig`).
     - `CMakeLists.txt`: CMake build file for `libvemins_engine.so`.
   - Update / Create Kotlin Model & Engine Layer:
     - `vemins_overlay_app/app/src/main/java/com/vemins/esp/engine/VeminsNativeEngine.kt`
     - `vemins_overlay_app/app/src/main/java/com/vemins/esp/model/FrameSnapshotBinary.kt` / `BinarySnapshotReader.kt`

2. **M3: Dear ImGui Floating Tactical Overlay & Obsidian Host App**:
   - `FloatingOverlayService.kt` & `FloatingMenuManager.kt`:
     - Draggable Minimalist Status Pill: Squircle badge with "V" monogram, live FPS, and latency readout.
     - Collapsible Tactical HUD Window: Dark frosted card (`#0C0C0C`, 85% opacity, 1px border) with Minimap Radar Viewport, Combat HUD, Entity Layers, 0°..360° rotation slider, live X/Y offset and scale calibration.
     - 1-Tap Instant Hide / Stow button.
   - `MainActivity.kt`: Modern minimalist Obsidian & Stark White dashboard with decoupled telemetry (3-4 Hz throttled).
   - `OverlaySurfaceView.kt`: Zero-allocation 60/120 FPS hardware canvas / SurfaceView.
   - Res files: `colors.xml`, `styles.xml`, and layout XMLs enforcing strict monochrome palette (`#000000`, `#0A0A0A`, `#0C0C0C`, `#1A1A1A`, `#FFFFFF`, `#888888`).
   - `build_apk.sh`: Update standalone build script to compile native C++ `libvemins_engine.so` via `clang++` / NDK, compile Kotlin / Java, resources, and package `veminsEsp.apk`.

3. **Build & Test Verification**:
   - Run full pytest regression suite: `python3 -m pytest tests/ -v` (ensure all 152 tests pass).
   - Run standalone APK build: `cd /data/data/com.termux/files/home/veminsEsp/vemins_overlay_app && ./build_apk.sh` (ensure build succeeds with 0 errors and `veminsEsp.apk` contains `libvemins_engine.so`).
   - Write full handoff report in `/data/data/com.termux/files/home/veminsEsp/.agents/worker_full_refactor/handoff.md`.
   - Send completion message to parent when done.
