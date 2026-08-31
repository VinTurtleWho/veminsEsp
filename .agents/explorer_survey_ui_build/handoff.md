# Handoff Report: UI & Build Toolchain Exploration (R3, R4, Verification)

**Author**: UI & Build Toolchain Explorer  
**Date**: 2026-08-30T20:15:00Z  
**Target Subsystems**: Android Floating Overlay UI, Host Application (`MainActivity`), Rendering Pipeline (`OverlaySurfaceView`), Standalone Build System (`build_apk.sh`), and Test Harness (`tests/`).

---

## 1. Observation

Direct code and toolchain inspection across the repository revealed the following concrete architectural facts:

### 1.1 Android App Structure & File Inventory (`vemins_overlay_app/`)
- **Root Directory**: `vemins_overlay_app/`
- **Application Package**: `com.vemins.esp` (targetSdk 35, minSdk 21/26)
- **Kotlin & Java Source Files** (`app/src/main/java/com/vemins/esp/`):
  1. `VeminsApplication.kt` — Application entry point, notification channel initialization (`vemins_overlay_channel`).
  2. `ui/MainActivity.kt` (886 lines) — Host configuration and telemetry dashboard; controls permissions, service state, live calibration sandbox, 4-tab panel (Radar, Combat HUD, Layers, Status/Vault), and daemon diagnostics.
  3. `service/FloatingOverlayService.kt` (188 lines) — Foreground service managing a fullscreen `FLAG_NOT_TOUCHABLE` transparent overlay window (`OverlaySurfaceView`) and launching `FloatingMenuManager`.
  4. `ui/floating/FloatingMenuManager.kt` (948 lines) — Floating trigger puck (`layout_floating_trigger.xml`, 38×38 dp) and mod menu card (`layout_floating_mod_menu.xml`, 290 dp frosted card); handles dragging, double-tap stealth mode, magnetic docking animator, and 4-tab controls.
  5. `view/OverlaySurfaceView.kt` (1241 lines) — Hardware-accelerated transparent canvas rendered on a dedicated `RenderThread` (`THREAD_PRIORITY_URGENT_DISPLAY`) via `lockHardwareCanvas()` (API 23+) with fallback to `lockCanvas()`. Pre-allocates `Paint`, `Path`, `RectF`, `Point2D`, `IsometricResult`, and `EdgeRadarResult` scratch buffers.
  6. `view/PreviewCanvasView.kt` (381 lines) — Sandbox canvas inside `MainActivity` rendering simulated heroes and radar frames for offline calibration.
  7. `view/CalibrationDialogView.kt` (347 lines) — Modal calibration dialog view with sliders for live tuning.
  8. `math/MinimapProjection.kt` (301 lines) — Implements 2D world-to-minimap Cartesian mapping in $[-52.0, +52.0]$, 45° diamond coordinate matrix $(x_{\text{rot}} = \frac{x-y}{\sqrt{2}}, y_{\text{rot}} = \frac{x+y}{\sqrt{2}})$, custom angle rotation, and velocity heading arrows.
  9. `math/IsometricProjection.kt` (252 lines) — 3D-to-2D isometric camera projection ($iso_x = (\Delta x - \Delta y)\frac{\sqrt{2}}{2}, iso_y = (\Delta x + \Delta y)\frac{\sqrt{2}}{2}$), camera vertical lift, and off-screen ray-box perimeter clamping.
  10. `assets/IconCacheManager.kt` (514 lines) — In-memory LRU bitmap cache (32 MB) storing circular cropped hero portraits (127 heroes), skill badges, and battle spell icons.
  11. `config/ConfigManager.kt` (848 lines) — SharedPreferences and JSON persistence for `ScreenConfig`, `MinimapConfig`, `CameraConfig`, and `RenderSettings`.
  12. `state/OverlayStateManager.kt` (253 lines) — Thread-safe atomic state coordination between telemetry, config, and UI observers.
  13. `daemon/DaemonManager.kt` (230 lines) — Root companion extractor and supervisor watchdog (`su -c /data/local/tmp/vemins_daemon`).
  14. `net/TelemetryClient.kt` (374 lines) — Background TCP socket client connecting to localhost `127.0.0.1:9999` and parsing newline-delimited JSON.
  15. `net/LocalControlServer.kt` (301 lines) — Embedded HTTP/REST API server (`127.0.0.1:8888`) exposing `/api/status`, `/api/config`, `/api/ping`.
  16. `model/FrameSnapshot.kt` (231 lines) — Data model for live frames parsed from string JSON using `org.json.JSONObject`.
  17. `model/HeroEntity.kt`, `model/MonsterEntity.kt`, `model/SoldierEntity.kt`, `model/TowerEntity.kt`, `model/AbilityInfo.kt`, `model/MinimapConfig.kt` — Entity model definitions.
- **XML Resources** (`app/src/main/res/`):
  - 39 XML files: `activity_main.xml` (1329 lines), `layout_floating_mod_menu.xml` (1530 lines), `layout_floating_trigger.xml` (30 lines), `colors.xml` (95 lines), `styles.xml`, and 33 drawable XMLs.
- **Android Manifest** (`AndroidManifest.xml`):
  - Permissions: `SYSTEM_ALERT_WINDOW`, `INTERNET`, `ACCESS_NETWORK_STATE`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_SPECIAL_USE` (subtype: "Floating game telemetry visual overlay and real-time HUD"), `POST_NOTIFICATIONS`.

### 1.2 Build Toolchain (`vemins_overlay_app/build_apk.sh`)
- Standalone bash build script (224 lines) invoking:
  1. `aapt2 compile` (`app/src/main/res` $\to$ `compiled_res.zip`)
  2. `aapt2 link` (`android.jar` + `AndroidManifest.xml` + assets $\to$ `unaligned.apk` + `R.java`)
  3. `javac` + `kotlinc` / `K2JVMCompiler` (compiles Kotlin & Java sources against `android.jar`, `kotlin-stdlib.jar`, `r_classes`)
  4. `d8.jar` (min-api 21 bytecode dexing)
  5. `zip` + `zipalign` (4-byte alignment $\to$ `aligned.apk`)
  6. `apksigner.jar` (debug keystore RSA 2048 signing)
- **Current Native Library Handling**: Currently, `build_apk.sh` only dexes Java/Kotlin and does not compile native C++ NDK sources (`libvemins_engine.so`) or pack `lib/arm64-v8a/` into the APK.

### 1.3 Pre-Existing Test Harness (`tests/`)
- Test execution: `python3 -m pytest tests/`
- **Result**: `113 passed in 2.47s` across 11 test modules:
  - `test_kotlin_engine_math.py` (6 tests) — Minimap normalization, invert-y, 45° isometric camera math, off-screen edge radar clamping, 45° diamond rotation matrix, heading vector rotation, manifest asset validation.
  - `test_blackbox_transitions.py` (8 tests) — Kinematics, damage, healing/level-up, death/respawn, ability cooldowns vs passive countdown ticks, item purchase/sale, shields/buffs, tower destruction.
  - `test_daemon_protocol.py` (4 tests) — Build hash verification, metadata contract, structured error decoding, `/proc/$PID/maps` filtering rules.
  - `test_world_snapshot.py` (57 tests) — Full schema validation, entity decoding, pointer verification, status bitmasks.
  - `test_esp_suite.py`, `test_identity_gate.py`, `test_knowledge_extractor.py`, `test_knowledge_store.py`, `test_kotlin_telemetry_and_config.py`, `test_local_control_and_telemetry.py`, `test_schema_and_proofing.py`.

---

## 2. Logic Chain & Gap Analysis

### 2.1 Floating UI & Overlay Architecture (Requirement R3)

| Design Spec Requirement | Current State in Codebase | Recommended Refactor / Implementation |
|---|---|---|
| **Hardware-Accelerated Transparent HUD** | Implemented via `OverlaySurfaceView` with `lockHardwareCanvas()` and `RenderThread`. Dedicated C++ standalone EGL/GLES in `vemins_esp.cpp`. | Maintain high-priority `RenderThread` (`THREAD_PRIORITY_URGENT_DISPLAY`), optimize frame pacing for 60/120 Hz refresh rates, and eliminate any remaining GC allocations in the hot draw path. |
| **Draggable Minimalist Status Pill** | `layout_floating_trigger.xml` is a 38×38 dp squircle with an icon and green/yellow/red dot. | Overhaul into a compact horizontal/squircle badge (`layout_floating_status_pill.xml` / `FloatingMenuManager.kt`) displaying the stark white **"V" monogram**, live numeric FPS counter (e.g. `120 FPS`), and memory sync latency (e.g. `0.4ms`), with smooth magnetic docking. |
| **Collapsible Tactical HUD Window** | `layout_floating_mod_menu.xml` is 290 dp with 4 horizontal tab buttons and long scrollable panels. | Redesign into a sleek dark frosted card (`#0C0C0C`, 85% opacity, crisp 1px `#2C2C2E` border) with Dear ImGui-style collapsible tree headers: `[-] Minimap Radar Viewport` (hero blips, heading arrows, X/Y calibration, scaling, continuous $0^\circ \dots 360^\circ$ rotation slider), `[-] Combat HUD` (Overhead HP/shield, skill CD sweeps, ult status, $360^\circ$ edge chevrons), and `[-] Entity Layers` (monochrome switches for Enemies, Allies, Minions, Monsters, Towers). |
| **1-Tap Instant Hide / Stow Button** | Floating mod menu has close `X` button and double-tap stealth mode. | Provide a dedicated instant stow / hide button that immediately collapses the menu into the compact status pill with zero touch interference (`FLAG_NOT_TOUCHABLE` on transparent regions). |
| **Monochrome Aesthetic System** | Current UI still uses legacy accent colors (`#30D158` green, `#FF453A` red, `#FF9F0A` yellow, cyan badges) in several XML drawables and paints. | Replace all colored drawables and paints with a strict monochrome Obsidian / Stark White / Deep Charcoal palette: `#000000` (pure black), `#0A0A0A` (void), `#0C0C0C` (card surface), `#1A1A1A` / `#1C1C1E` (elevated elements), `#2C2C2E` (1px crisp borders), `#FFFFFF` (stark white text & active indicators), `#888888` / `#A1A1A6` (muted secondary labels). Zero neon cyan or purple glow. |

### 2.2 Host Application & Rendering Optimization (Requirement R4)

| Design Spec Requirement | Current State in Codebase | Recommended Refactor / Implementation |
|---|---|---|
| **Obsidian & Stark White Dashboard** | `activity_main.xml` has dark background but contains legacy cyan/green/yellow badges and colored status indicators. | Re-skin `activity_main.xml` and `MainActivity.kt` with the industrial Stark White & Obsidian aesthetic, clean typography, minimalist monochrome cards, and refined toggle switches. |
| **Decoupled Telemetry Logging (3–4 Hz)** | `MainActivity.kt` updates UI state directly inside `onStateChanged(state: OverlayState)` whenever triggered by `OverlayStateManager`. If snapshots stream at 60 Hz, the Main-Thread message queue is flooded. | Introduce a throttled UI update loop (3–4 Hz, ~250–333 ms period) using a dedicated coroutine / Handler timer that polls or throttles state broadcasts to `MainActivity`, leaving the Main-Thread message queue 100% responsive. |
| **Zero-Allocation Per-Frame Render Loop** | `OverlaySurfaceView.kt` pre-allocates scratch math objects (`scratchPointA`, `scratchPointB`, `scratchIsoResult`, `scratchEdgeRadarResult`, `scratchRectF`). However, `FrameSnapshot.parse()` and `TelemetryClient` still perform string JSON parsing (`JSONObject`, `optJSONArray`, `ArrayList` allocations). | In the JNI/NDK migration (R1), pass packed native binary buffers (`FrameSnapshot` struct) directly to `OverlaySurfaceView` or C++ renderer without JSON parsing, string allocation, or intermediate heap objects. |
| **Clean Subsystem Lifecycle Management** | `FloatingOverlayService.onDestroy()` stops watchdog, removes views, and terminates telemetry client. | Ensure deterministic release of native memory handles, file descriptors (`/proc/$PID/mem`), OpenGL/Surface textures, and background threads upon service stop or app backgrounding. |

### 2.3 Standalone Build Toolchain & Native Packaging (`build_apk.sh`)

| Requirement | Current State | Target Enhancement |
|---|---|---|
| **NDK / CMake C++ Compilation** | `build_apk.sh` compiles only Java/Kotlin classes into `classes.dex`. Native C++ code is compiled separately via `build_vemins_esp.sh`. | Integrate native shared library compilation into `build_apk.sh`: invoke `clang++` (targeting Android `aarch64-linux-android`) to build `libvemins_engine.so` from native perception sources, and package `lib/arm64-v8a/libvemins_engine.so` into the unaligned APK before zipalign and signing. |
| **Offline Toolchain Compatibility** | AAPT2, D8, Kotlinc (`K2JVMCompiler`), zipalign, and apksigner run 100% offline using local Termux / Android SDK paths. | Maintain 100% offline standalone capability without Gradle daemon dependencies. |

---

## 3. Caveats & Assumptions

1. **Read-Only Investigation**: As an explorer agent, this survey analyzes problems and documents findings without modifying source code files directly.
2. **Offline Toolchain Assumptions**: Termux local environment contains `aapt2`, `d8.jar`, `K2JVMCompiler` (in Gradle wrapper lib), `zipalign`, and `apksigner.jar`. Compiling the native shared library requires `clang++` with `-shared -fPIC` and standard Bionic NDK headers/libraries available in Termux (`/data/data/com.termux/files/usr/lib`).
3. **Android 14+ / 15+ Compatibility**: Target SDK 35 requires foreground service type `specialUse` with `PROPERTY_SPECIAL_USE_FGS_SUBTYPE` declared in `AndroidManifest.xml` (already satisfied).

---

## 4. Conclusion & Architectural Recommendations

### 4.1 Recommended File Modifications for Implementation Phase

1. **`vemins_overlay_app/app/src/main/res/values/colors.xml`**:
   - Enforce strict monochrome palette:
     ```xml
     <color name="vemins_bg_black">#000000</color>
     <color name="vemins_bg_void">#0A0A0A</color>
     <color name="vemins_card_surface">#0C0C0C</color>
     <color name="vemins_card_elevated">#1A1A1A</color>
     <color name="vemins_border_subtle">#1C1C1E</color>
     <color name="vemins_border_crisp">#2C2C2E</color>
     <color name="vemins_text_stark_white">#FFFFFF</color>
     <color name="vemins_text_muted_gray">#888888</color>
     <color name="vemins_accent_white">#FFFFFF</color>
     ```
   - Eliminate all neon cyan and purple glows.
2. **`vemins_overlay_app/app/src/main/res/layout/layout_floating_trigger.xml` & `FloatingMenuManager.kt`**:
   - Transform the trigger puck into a draggable Status Pill showing the monochrome "V" glyph, live FPS readout, and latency counter.
3. **`vemins_overlay_app/app/src/main/res/layout/layout_floating_mod_menu.xml` & `FloatingMenuManager.kt`**:
   - Implement the Collapsible Tactical HUD Window with dark frosted glass background (`#0C0C0C`, 85% opacity, 1px border `#2C2C2E`), Dear ImGui-style collapsible tree headers (`[-] Minimap Radar Viewport`, `[-] Combat HUD`, `[-] Entity Layers`), and 1-tap instant hide button.
4. **`vemins_overlay_app/app/src/main/java/com/vemins/esp/ui/MainActivity.kt` & `layout/activity_main.xml`**:
   - Overhaul into Obsidian & Stark White control dashboard.
   - Decouple telemetry updates: throttle UI telemetry refresh rate to 3–4 Hz (250–333 ms) to prevent Main-Thread saturation.
5. **`vemins_overlay_app/app/src/main/java/com/vemins/esp/view/OverlaySurfaceView.kt`**:
   - Update paints to adhere strictly to the monochrome palette with high-contrast stark white vectors and muted charcoal boundaries.
   - Enforce zero-allocation per frame (0 GC stutter).
6. **`vemins_overlay_app/build_apk.sh`**:
   - Add step to compile `libvemins_engine.so` via `clang++` with `-shared -fPIC` and package `lib/arm64-v8a/libvemins_engine.so` into the APK before signing.

---

## 5. Verification Method

To independently verify the survey observations and validate downstream implementations:

1. **Run Pytest Regression Suite**:
   ```bash
   python3 -m pytest tests/
   ```
   *Expected*: All 113 tests in `tests/` pass with zero failures.

2. **Verify Mathematical Consistency**:
   ```bash
   python3 -m pytest tests/test_kotlin_engine_math.py tests/test_blackbox_transitions.py tests/test_world_snapshot.py -v
   ```
   *Expected*: Validates 45° diamond matrix projection, coordinate normalization in $[-52.0, +52.0]$, isometric 3D-to-2D projection, and edge radar raycasting.

3. **Verify Android APK Build Script Execution**:
   ```bash
   bash vemins_overlay_app/build_apk.sh
   ```
   *Expected*: Compiles resources with AAPT2, sources with Kotlinc/javac, dexes with D8, packages native libraries, zipaligns, signs with apksigner, and generates `veminsEsp.apk` with zero errors.

4. **Verify Manifest & Layout Resource Integrity**:
   Inspect `app/src/main/AndroidManifest.xml`, `colors.xml`, `layout_floating_mod_menu.xml`, and `activity_main.xml` for structural validity and monochrome compliance.
