# Teamwork Project Prompt — Draft

> Status: Ready for launch — awaiting user approval
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Small focused team (single self-contained architectural refactor and UI redesign)

This is a focused architectural refactor and UI redesign; keep the team small and focused. Refactor VEMINS ESP to eliminate the external daemon binary and TCP/JSON streaming overhead in favor of an ultra-fast, robust in-app native JNI/NDK memory perception engine with root access, lock in all reverse-engineered battlefield memory invariants, and completely overhaul both the in-game floating overlay and the host app into an ultra-responsive, modern minimalist "heavenly" rich UI (Dear ImGui-style floating overlay + obsidian monochrome dashboard).

Working directory: `/data/data/com.termux/files/home/veminsEsp`
Integrity mode: `development`

---

## Architectural Context & Reference Invariants

- **Root Access & Isolation**: Memory reading is strictly read-only and external via `/proc/$PID/mem` (or `process_vm_readv`), requiring zero code injection, zero ptrace attachment (`TracerPid == 0`), zero function hooking, and zero target memory modification.
- **Battlefield Memory Invariants** (Reference: `MlbbBot` / `offsets.json` / `FIELD_MAP.md`):
  - Base dynamic link module: `libcsharp.so`
  - Static root chain: `libcsharp.so + 0x7680928` $\to$ `Il2CppClass + 0xb8` $\to$ `static_fields + 0x00` $\to$ `LogicBattleManager*`
  - Local Hero (Gate 8): `m_RealSelfPlayer` @ offset `+0x200` (fallback `+0x0a0`)
  - Player Dictionary: `m_dicPlayerLogic` @ offset `+0x0a8` (24-byte entry stride, enforcing `hashCode >= 0` tombstone filtering)
  - 64-bit Continuous Cartesian Coordinates: `m_dRealPosX (+0x268)` and `m_dRealPosY (+0x270)` in range $[-52.0, +52.0]$
  - Entities: Minions @ `+0x128`, Monsters @ `+0x0b0`, Towers @ `+0xd0, +0xd8, +0xe0, +0xe8`
  - Gate Bypass: Never gate rendering on `battle_state`; treat match as active whenever valid player entity pointers exist.

---

## Requirements

### R1. Direct High-Performance Native JNI/NDK Perception Engine
- Eliminate the external background daemon binary (`vemins_daemon`), localhost TCP socket server (`127.0.0.1:9999`), socket reconnect state machines, and stringified JSON serialization.
- Implement an in-app native C++ engine (`libvemins_engine.so` / NDK) that obtains read-only `/proc/$PID/mem` access via a minimal root companion or compact binary IPC bridge.
- Direct binary frame encoding: encode raw entity arrays into packed, fixed-size C structs (`FrameSnapshot` binary schema) with zero string formatting and zero JSON parsing.
- Implement zero-overhead PID & memory map caching: once the game process is discovered, cache base addresses and only re-scan if `kill(pid, 0) != 0`.
- Memory reader cycle latency must execute in $< 1.0\text{ ms}$ per tick.

### R2. Robust Entity Perception & Invariant Adherence
- Decode all active entities across all 10 players, minion waves, jungle camps (Lord, Turtle, Buffs), and towers.
- Maintain persistent camera tracking and coordinate continuity: when `localPlayer` is temporarily null during respawn or death, smoothly anchor to `lastKnownLocalX/Y` without HUD flickering or coordinate jumps.
- Enforce strict `isfinite()` validation on all floating-point coordinates and health values to prevent NaN / Infinity propagation.
- Gracefully handle dictionary holes, dynamic entity reallocation, and target game restarts without crashing or leaking resources.

### R3. Rich Dear ImGui-Style Floating Tactical Overlay
- Build a hardware-accelerated, transparent floating HUD rendered with Dear ImGui (OpenGL ES 3.0 / SurfaceView):
  - **Draggable Minimalist Status Pill**: Compact squircle badge displaying the monochrome "V" monogram, live FPS, and memory sync latency.
  - **Collapsible Tactical HUD Window**: Semi-transparent dark frosted card (`#0C0C0C`, 85% opacity, crisp 1px border) with collapsible headers:
    - `[-] Minimap Radar Viewport`: Real-time hero blips, heading orientation arrows, live X/Y offset calibration, scaling, and smooth $0^\circ \dots 360^\circ$ rotation slider.
    - `[-] Combat HUD`: Toggles and scale factors for Overhead HP/shield bars, skill cooldown sweeps, ultimate status badges, and $360^\circ$ off-screen edge chevrons.
    - `[-] Entity Layers`: Independent monochrome toggle switches for Enemies, Allies, Minions, Monsters, and Towers.
  - **1-Tap Instant Hide / Stow**: Dedicated dismiss button allowing immediate stowing/collapsing during intense combat with zero touch interference.
  - **Aesthetic System**: Strict monochrome Black & White / Deep Charcoal palette (`#000000`, `#0A0A0A`, `#1A1A1A`, `#FFFFFF`, `#888888`) with crisp typography and zero neon glow.

### R4. Modern Minimalist Android Host App & Rendering Optimization
- Overhaul `MainActivity` into a sleek, industrial Obsidian & Stark White control dashboard.
- Decouple 60/120 FPS hardware canvas/OpenGL rendering from background UI telemetry logging (throttled to 3–4 Hz) to eliminate Main-Thread message queue saturation.
- Implement zero-allocation per-frame loops in the render pipeline to completely eliminate Garbage Collection (GC) pauses and frame drops.
- Clean lifecycle management: starting/stopping overlay services cleanly releases native memory handles, file descriptors, and OpenGL contexts.

---

## Verification Resources & Test Harness

- **Automated Regression Suite**: Pre-existing pytest suite in `tests/` (`test_kotlin_engine_math.py`, `test_blackbox_transitions.py`, `test_daemon_protocol.py`, `test_world_snapshot.py`).
- **Binary Struct & Projection Math Tests**: Automated validation of binary struct packing, coordinate clamping in $[-52.0, +52.0]$, isometric camera projection transforms, and rotation matrices.
- **Offline Build Toolchain**: Standalone offline APK build script `./build_apk.sh` in `vemins_overlay_app/` verifying AAPT2, D8, Kotlinc, and CMake / NDK compilation with zero build errors.

---

## Acceptance Criteria

### Performance & Telemetry Latency
- [ ] Direct native memory reading cycle completes in $< 1.0\text{ ms}$ per tick with 0 socket/TCP overhead.
- [ ] Overlay renders stably at 60/120 FPS with $< 5\%$ Main Thread CPU utilization and 0 GC stutter events during active rendering.

### Perception & Coordinate Accuracy
- [ ] Radar correctly projects all 10 heroes, minion waves, and jungle monsters with continuous coordinates and smooth rotation ($0^\circ \dots 360^\circ$).
- [ ] Camera tracking smoothly preserves coordinates through hero death, respawn, and dictionary reallocations without jumping.
- [ ] NaN and Inf values are 100% sanitized before reaching the rendering pipeline.

### Floating UI & UX Experience
- [ ] Strict Black & White / Deep Charcoal modern minimalist aesthetic (no neon cyan/purple glow).
- [ ] Floating Dear ImGui menu is rich, responsive, comfortably customizable with collapsible tree nodes, and dismissible with 1 tap.
- [ ] Touch dispatch is 100% reliable: dragging moves the HUD smoothly, and transparent areas allow native touch pass-through to underlying games.

### Build & Code Quality
- [ ] Pytest test suite passes 100% cleanly (`pytest tests/`).
- [ ] Android APK builds cleanly via `./build_apk.sh` with integrated native shared library `libvemins_engine.so`.
- [ ] Codebase is cleanly structured with well-separated concerns (memory reader, binary decoder, projection math, UI/renderer).
