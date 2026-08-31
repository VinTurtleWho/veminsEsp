# VEMINS ESP Test Infrastructure & Verification Strategy

**Document Status**: Authoritative Test Infrastructure Specification  
**Scope**: End-to-End (E2E) Opaque-Box & Multi-Tier Verification Suite for VEMINS ESP Refactor  
**Target Suite**: `tests/test_e2e_refactor.py`  
**Execution Command**: `python3 -m pytest tests/test_e2e_refactor.py`

---

## 1. Executive Summary

The VEMINS ESP architectural refactor transitions the system from an external background daemon (`vemins_daemon`) communicating over a localhost TCP socket (`127.0.0.1:9999`) with JSON serialization into an ultra-low latency, in-app native JNI/NDK perception engine (`libvemins_engine.so`) backed by packed binary frame buffers (`FrameSnapshotBinary`, 4,880 bytes) and a hardware-accelerated monochrome floating tactical overlay.

This document establishes the test infrastructure, multi-tier testing strategy, boundary constraints, and verification methodology to guarantee total correctness, strict invariant adherence, sub-millisecond execution, and zero garbage collection (GC) churn.

---

## 2. Multi-Tier Testing Taxonomy

The test suite in `tests/test_e2e_refactor.py` is organized into 4 distinct verification tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        E2E Verification Tiers                          │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Tier 4: Real-World Application Scenarios                         │  │
│  │  - Full 5v5 Teamfight Simulation (10 Heroes, Vitals, CC, Spells) │  │
│  │  - Jungle Boss Contest (Lord/Turtle aggro, death, buff claim)    │  │
│  │  - UI Overlay State Changes (Pill drag, stow, radar calibration) │  │
│  └──────────────────────────────────▲───────────────────────────────┘  │
│                                     │                                  │
│  ┌──────────────────────────────────┴───────────────────────────────┐  │
│  │ Tier 3: Cross-Feature Combinations                               │  │
│  │  - Gate 8 Local Hero + Death/Respawn EMA Camera Smoothing        │  │
│  │  - 360° Continuous Rotation + Isometric W2S Projection + Raycast │  │
│  │  - Dynamic Entity Reallocation & Binary Buffer Synchronization   │  │
│  └──────────────────────────────────▲───────────────────────────────┘  │
│                                     │                                  │
│  ┌──────────────────────────────────┴───────────────────────────────┐  │
│  │ Tier 2: Boundary & Corner Cases                                  │  │
│  │  - World Coordinate Clamping in [-52.0, +52.0]                    │  │
│  │  - NaN & Infinity Floating-Point Sanitization (isfinite)         │  │
│  │  - Tombstone Filtering in Dictionary Traversal (hashCode >= 0)   │  │
│  │  - Zero HP / Dead Hero Vitals, Shield & Mech Armor Isolation     │  │
│  │  - Null Pointers, Dead PIDs, Corrupted VTables Fail-Closed       │  │
│  └──────────────────────────────────▲───────────────────────────────┘  │
│                                     │                                  │
│  ┌──────────────────────────────────┴───────────────────────────────┐  │
│  │ Tier 1: Core Feature Coverage (>=5 Tests per R1-R4 Feature)      │  │
│  │  - R1: Native Engine, Binary Schema, PID Caching, Latency Budget │  │
│  │  - R2: Entity Invariants, 10 Heroes, Minions, Bosses, Structures │  │
│  │  - R3: Dear ImGui Floating Overlay, Monochrome Palette, Radar    │  │
│  │  - R4: Obsidian Dashboard, 3-4 Hz Telemetry, 0 GC Per-Frame Data │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Specification by Tier

### Tier 1: Feature Coverage (R1 – R4)
- **R1: Direct Native Perception Engine & Binary Schema**:
  - `FrameSnapshotBinary` packed struct layout: Verify fixed 4,880-byte size, zero alignment holes, schema magic `0x564D4E53` ('VMNS'), and version 1.
  - Zero-JSON Binary Frame Ingestion: Verify raw byte buffer serialization and direct field extraction without string parsing.
  - PID and ELF Magic Caching: Verify `s_cached_pid` and `s_libcsharp_base` validation via 4-byte ELF magic (`0x464C457F`).
  - Sub-Millisecond Batch Reader Latency: Verify mock DMA batch reading completes well under the $1.0\text{ ms}$ threshold budget ($<0.5\text{ ms}$).
  - JNI DirectByteBuffer Interface: Verify memory mapping contract between C++ struct layout and Kotlin direct buffer reader.

- **R2: Robust Entity Perception & Memory Invariants**:
  - Gate 8 Authoritative Local Hero Resolution: Verify strict binding to `m_RealSelfPlayer (+0x200)` with fallback to `m_LocalPlayerLogic (+0x0a0)`.
  - 10-Player Dictionary Ingestion: Verify traversal of `m_dicPlayerLogic (+0x0a8)` with 24-byte entry stride and tombstone filtering (`hashCode >= 0`).
  - 64-Bit Continuous Cartesian Coordinates: Verify reading of `m_dRealPosX (+0x268)` and `m_dRealPosY (+0x270)` in $[-52.0, +52.0]$.
  - Minion Waves & Jungle Bosses: Verify decoding of `m_SoldierList (+0x128)` and `m_dicMonsterLogic (+0x0b0)` (Lord 51298, Turtle 51312, Buffs 51248/51346).
  - Defensive Structures: Verify decoding of Camp A/B Nexuses (`+0xd0/+0xd8`) and lane turrets (`+0xe0/+0xe8`).

- **R3: Dear ImGui Floating Tactical HUD**:
  - Strict Monochrome Palette: Verify color constants `#000000`, `#0A0A0A`, `#0C0C0C`, `#1A1A1A`, `#FFFFFF`, `#888888` without neon accents.
  - Minimap Radar Projection: Verify 2D linear mapping with $Y$-axis inversion and 45° diamond coordinate matrix.
  - Continuous $0^\circ \dots 360^\circ$ Rotation: Verify arbitrary angle rotation of radar blips and heading arrows.
  - Isometric World-to-Screen Projection: Verify 45° camera projection with vertical HUD offset lift.
  - Off-Screen Edge Radar Clamping: Verify perimeter ray-box intersection and border heading angle calculation.

- **R4: Modern Obsidian Host App & Rendering Optimization**:
  - Telemetry Throttling: Verify background UI telemetry updates are throttled to 3–4 Hz while render loop runs at 60/120 FPS.
  - Zero-Allocation Render Loop: Verify per-frame data structures reuse scratch containers (`Point2D`, `IsometricResult`, `EdgeRadarResult`) with 0 heap allocations.
  - Asset Manifest Mappings: Verify 127 heroes and 11 spells are indexed correctly in `manifest.json`.
  - Clean Lifecycle Resource Release: Verify surface destruction cleanly frees buffers, file descriptors, and native handles.

---

### Tier 2: Boundary & Corner Cases
1. **Coordinate Bounds [-52.0, +52.0]**: Coordinates at $-52.0$, $+52.0$, and extreme out-of-bounds ($\pm 100.0, \pm 999.0$) are safely clamped or normalized without math exceptions.
2. **NaN / Inf Sanitization**: Any NaN or $\pm\infty$ float/double coordinates, health values, or movement speeds are sanitized via `std::isfinite()` fallback to zero or default.
3. **Tombstone Filtering**: Dictionary slots with `hashCode < 0` (freed/deleted entities) are skipped without terminating traversal.
4. **Zero HP / Dead Hero Vitals**: Entity with $\text{HP}=0$ or `is_dead=1` maintains valid spatial telemetry while correctly indicating inactive status.
5. **Null Pointers & Target Restarts**: Null `LogicBattleManager`, null `m_dicPlayerLogic`, unmapped memory, and terminated PIDs fail-closed safely returning empty frame snapshots.

---

### Tier 3: Cross-Feature Combinations
1. **Gate 8 + Death/Respawn EMA Camera Smoothing**:
   - When local hero dies and pointer temporarily becomes NULL or inactive, camera anchors to `(lastKnownLocalX, lastKnownLocalY)`.
   - On hero respawn at base fountain, camera position smoothly converges using Exponential Moving Average:
     $$P_{\text{cam}}(t) = (1 - \alpha) P_{\text{cam}}(t-1) + \alpha P_{\text{local}}(t), \quad \alpha = 0.35$$
   - Verified across 10 consecutive frames: coordinates transition smoothly with zero flickering or sudden jumps.
2. **360° Rotation + Isometric W2S + Edge Radar**:
   - Entities rotated across $0^\circ, 90^\circ, 180^\circ, 270^\circ, 360^\circ$ maintain consistent isometric screen projections and correct off-screen raycast border points.
3. **Dynamic Entity Reallocation**:
   - Ingesting a frame snapshot where player pointers migrate dictionary indices does not corrupt hero tracking or Gate 8 identity.

---

### Tier 4: Real-World Application Scenarios
1. **Full 5v5 Teamfight Simulation**:
   - 10 active players (5 Blue, 5 Red) engaged in combat.
   - Active vitals: Damage taken, shields granted, ability cooldown countdowns (S1, S2, Ult, Battle Spell).
   - Status mask: Stun (`0x02`), Silence (`0x08`), Airborne (`0x10`) active.
   - 2 minion waves pushing mid lane + lane turret firing.
   - Complete frame snapshot serialization and verification of all entity counts and fields.
2. **Jungle Boss Contest (Lord/Turtle)**:
   - Jungle Lord (HP: 24,000) engaged in river pit.
   - Aggro radius tracking, health depletion over consecutive ticks, death event transition, and kill bounty award.
3. **Floating UI Overlay State Changes**:
   - Status pill position dragging: $(X, Y)$ updates smoothly.
   - Tactical HUD window expand / collapse state transitions.
   - Minimap radar calibration adjustments (X/Y offsets, scale multipliers, rotation angle).
   - Entity layer toggles (e.g. Hide Minions, Show Heroes Only) filtering output without mutating underlying snapshot data.
   - 1-Tap instant stow trigger activating minimal pass-through overlay mode.

---

## 4. Test Execution & Environment

- **Framework**: `pytest` / `unittest` (Python 3.10+)
- **Test File**: `tests/test_e2e_refactor.py`
- **Execution Command**:
  ```bash
  python3 -m pytest tests/test_e2e_refactor.py -v
  ```
- **Full Regression Command**:
  ```bash
  python3 -m pytest
  ```

---

## 5. Traceability Matrix

| Requirement | Test Class / Category in `test_e2e_refactor.py` | Coverage Status |
| :--- | :--- | :--- |
| **R1: Native Engine & Binary Schema** | `TestTier1FeatureCoverage.test_r1_*` (6 test cases) | Verified |
| **R2: Robust Entity Perception & Invariants** | `TestTier1FeatureCoverage.test_r2_*` (6 test cases) | Verified |
| **R3: Dear ImGui Floating Tactical HUD** | `TestTier1FeatureCoverage.test_r3_*` (6 test cases) | Verified |
| **R4: Modern Obsidian Host App & Optimization**| `TestTier1FeatureCoverage.test_r4_*` (5 test cases) | Verified |
| **Tier 2: Boundary & Corner Cases** | `TestTier2BoundaryAndCornerCases` (7 test cases) | Verified |
| **Tier 3: Cross-Feature Combinations** | `TestTier3CrossFeatureCombinations` (5 test cases) | Verified |
| **Tier 4: Real-World Scenarios** | `TestTier4RealWorldScenarios` (4 test cases) | Verified |

---

## 6. Sign-off Criteria
1. All test cases in `test_e2e_refactor.py` execute and pass with 0 failures and 0 errors.
2. Binary struct layouts match `engine_schema.h` with exact byte-for-byte packing (4,880 bytes).
3. Coordinate transformations match Kotlin `MinimapProjection.kt` and `IsometricProjection.kt` formulas within $0.01$ pixel epsilon.
4. Total execution time of the full test suite remains $< 3.0\text{ seconds}$.
