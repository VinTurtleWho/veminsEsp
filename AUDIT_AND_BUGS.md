# VEMINS ESP // DEEP AUDIT, BUG DIAGNOSIS & REFACTOR SPECIFICATION

**Document Version:** 2.0.0-AUDIT  
**Status:** COMPLETE AUDIT & REMEDIATION PLAN  
**System Target:** Mobile Legends: Bang Bang (ARM64-v8a / Android 8.0 - 15)  

---

## 1. Executive Summary & Core Diagnoses

This document captures all verified bugs, root causes, architectural debt, and user-reported issues identified during the comprehensive audit of the **VEMINS ESP** repository.

### Summary of Critical Problems Identified by User & Code Audit:
1. **Minimap Calibration & Rotation Chaos:**
   - User has to manually re-adjust rotation (315° vs 135°) and settings every single match.
   - Working in-game settings:
     - Hero Icon Size: `16`
     - Minimap Position: `X: 0, Y: 0`
     - Radar Size: `342`
     - Alpha Opacity: `0` (Fully transparent radar background)
     - Radar Zoom: `200`
     - Invert Y-Axis: `true`
     - Rotation: `315°` (or opposite `135°` depending on map side)
   - **Root Cause:** In MLBB, player spawn side changes each match (Base Camp 1 / Blue side at bottom-left vs Base Camp 2 / Red side at top-right). Because the camera ground orientation mirrors or flips by 180° depending on spawn camp, static configurations fail across matches.
2. **3D Combat Overlay Lateral Offset & Distance Skew:**
   - 3D overhead badges and health bars do not lock over the enemy character model.
   - At long distances, badges float far out to the side of the screen; as you walk closer, they slide toward the enemy.
   - **Root Cause:**
     - The current projection math calculates target position strictly as an offset from the local hero (`dx = targetX - localX, dy = targetY - localY`), anchoring screen center `(cx, cy)` to `localPlayer`.
     - When the player slides or pans their camera across the battlefield (or targets enemies at distance), screen center is **no longer on the local hero**. The true camera focus has shifted.
     - Furthermore, the perspective depth equation uses an artificial non-linear `cos(58°)` divisor (`camHeight / (camHeight + isoY * cosPitch)`) that aggressively skews X coordinates whenever `isoY` is large, pulling distant targets sideways.
3. **Top Enemy Status Strip (Ability Slots & Battle Spell Incomplete):**
   - The top status bar only shows 2 abilities instead of the full 3 or 4 hero skills + Battle Spell.
   - Icons fail to load and look low-quality/sloppy.
   - **Root Cause:**
     - In `vemins_daemon.c` (`parse_hero_abilities`), the dictionary iteration only maps slot 1, slot 2, and slot 3/ult, with passive / slot 4 / transformed skills misclassified or dropped.
     - In `OverlaySurfaceView.kt` (`renderTopCdBar`), ability lookup hardcodes `enemy.getAbility(1)`, `enemy.getAbility(2)`, and `enemy.getAbility(3)` instead of dynamically rendering all skills in `enemy.abilities` plus `enemy.battleSpell`.
     - In `IconCacheManager.kt`, circular cropping and asset path resolution uses hardcoded `"skills/$heroId/skill1.png"` paths while the bundled assets in `assets/skills/` are often structured as `assets/skills/{heroId}/{skillId}.png` or flat numbers without fallback to high-res vector fallbacks.
4. **Architectural Duplication & UI Sloppiness:**
   - Four duplicate implementations of perception / math / rendering (C daemon, C++ native overlay, Kotlin app + NDK bridge, Python scripts).
   - `vemins_overlay_app` contains unused `VeminsNativeEngine` / JNI bindings, falling back to heavy JSON string parsing at 60 FPS over local TCP, creating garbage collection pauses.
   - The UI contains conflicting cyberpunk, cyan, and rainbow elements rather than a clean, unified, high-contrast, minimalist HUD.

---

## 2. Deep Root-Cause Analysis

### 2.1 The 3D Overlay "Side-Floating" Bug

#### Existing Math in `IsometricProjection.kt`:
```kotlin
val dx = targetX - localX
val dy = targetY - localY

val totalYawDeg = 45.0 + rotationDegrees
val totalYawRad = Math.toRadians(totalYawDeg).toFloat()
val cosYaw = kotlin.math.cos(totalYawRad)
val sinYaw = kotlin.math.sin(totalYawRad)

val isoX = dx * cosYaw - dy * sinYaw
val isoY = dx * sinYaw + dy * cosYaw

val depth = (camHeight + (isoY * cosPitch)).coerceAtLeast(4.0f)
val perspScale = camHeight / depth

val sx = cx + (isoX * scaleX) * perspScale
val sy = cy - ((isoY * scaleY) + lift) * perspScale
```

#### Why it Breaks:
1. **Camera Center != Local Player:**
   In MLBB, the camera follows the local player with dynamic look-ahead damping, ability targeting pans, and minimap touch panning. Using `localX, localY` as the origin assumes the player is permanently frozen at `(cx, cy)`. Any offset between the camera focus and the player creates an angular error.
2. **Perspective Divisor Cross-Coupling:**
   Multiplying `isoX * scaleX` by `perspScale = camHeight / (camHeight + isoY * cosPitch)` introduces severe lateral distortion. When an enemy is far up the lane (`isoY` is large), `perspScale` drops to `0.3`, drastically compressing the X-distance relative to Y. Because the camera is actually an axonometric/trimetric projection with fixed focal length, this non-linear divisor bends straight lane alignments into curved arcs.
3. **Yaw Offset Misalignment:**
   When `rotationDegrees` is set to `315°` for the minimap, `totalYawDeg` becomes `45 + 315 = 360° = 0°`, effectively disabling the 45° map yaw for the 3D world view! The minimap rotation was erroneously linked to the 3D world-to-screen projection.

---

## 3. Verified Working Baseline Configurations

The user confirmed the exact functional settings that match MLBB viewport geometry:

| Parameter | Calibrated Value | Rationale / Target |
| :--- | :--- | :--- |
| **Hero Icon Size** | `16` | Perfectly matches MLBB minimap hero avatar scale |
| **Minimap Pos X** | `0.0` | Anchors to screen top-left bezel |
| **Minimap Pos Y** | `0.0` | Anchors to screen top-left bezel |
| **Radar Size** | `342.0` | Matches default 6.7" / 2400x1080 display radar radius |
| **Radar Zoom** | `2.0 (200%)` | Correct scale factor for 104m world coordinate span |
| **Alpha / Opacity** | `0.0 (0%)` | Transparent overlay; does not obscure underlying game map |
| **Invert Y-Axis** | `true` | Inverts Cartesian world Y to screen pixel Y |
| **Rotation Degrees** | `315.0°` (Camp A) / `135.0°` (Camp B) | Diagonal diamond radar alignment aligned with river flow |

---

## 4. Remediation Plan & Architecture Roadmap

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 PHASE 1: PERMANENT CONFIG & CALIBRATION                │
  │  - Set user's working values as hard defaults in ConfigManager.        │
  │  - Add Auto-Camp Detection (auto-flip 315° <-> 135° on match start).   │
  │  - Add manual 1-tap 180° flip button in floating menu.                 │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
  ┌───────────────────────────────────▼────────────────────────────────────┐
  │              PHASE 2: 3D WORLD-TO-SCREEN FOUNDATION FIX                │
  │  - Decouple minimap rotation from 3D camera yaw.                       │
  │  - Eliminate non-linear depth cross-talk causing lateral side-float.   │
  │  - Implement true axonometric projection with adjustable camera anchor.│
  │  - Add live 3D screen alignment calibration slider in Mod Menu.        │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
  ┌───────────────────────────────────▼────────────────────────────────────┐
  │         PHASE 3: TOP ENEMY HUD & ABILITY PIPELINE OVERHAUL             │
  │  - Fix IL2CPP ability slot traversal in daemon (all 4 skills + spell). │
  │  - Fix asset loading in IconCacheManager (guaranteed icon resolution). │
  │  - Clean, high-contrast, professional top HUD rendering.               │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
  ┌───────────────────────────────────▼────────────────────────────────────┐
  │        PHASE 4: CODEBASE CLEANUP & SINGLE-PIPELINE CONVERGENCE         │
  │  - Archive/remove loose redundant root scripts into tools/ or legacy/. │
  │  - Unify project documentation (README, ARCHITECTURE, FIELD_MAP).      │
  │  - Optimize memory allocation & eliminate GC pauses.                   │
  └────────────────────────────────────────────────────────────────────────┘
```
