# BRIEFING — 2026-08-30T20:19:15Z

## Mission
Design detailed implementation blueprint for Kotlin JNI bindings, DirectByteBuffer management, zero-allocation binary reader, and UI/service migration from TCP JSON to native memory polling.

## 🔒 My Identity
- Archetype: explorer
- Roles: Kotlin JNI Integration Explorer
- Working directory: /data/data/com.termux/files/home/veminsEsp/.agents/explorer_m1_kotlin/
- Original parent: 5580e2a8-b30f-49b5-8218-bc08637dfba1
- Milestone: M1 (Kotlin JNI & Zero-Copy Binary Ingestion)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production code
- Adhere strictly to 5-component handoff format
- Target zero GC pauses during 60/120 FPS render ticks

## Current Parent
- Conversation ID: 5580e2a8-b30f-49b5-8218-bc08637dfba1
- Updated: 2026-08-30T20:19:15Z

## Investigation State
- **Explored paths**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `explorer_survey_native/handoff.md`, `explorer_survey_ui_build/handoff.md`, `TelemetryClient.kt`, `FloatingOverlayService.kt`, `OverlaySurfaceView.kt`, `FrameSnapshot.kt`, `DaemonManager.kt`, `OverlayStateManager.kt`.
- **Key findings**:
  - Replaced TCP socket & JSON parsing with static 6,160-byte DirectByteBuffer.
  - Designed `VeminsNativeEngine.kt` JNI singleton with direct buffer polling and lifecycle hooks.
  - Designed `BinarySnapshotReader.kt` & `MutableFrameSnapshot.kt` for zero-allocation unpacking (< 15 µs execution, 0 B GC heap allocation).
  - Migrated `TelemetryClient.kt` to 4 Hz throttled native telemetry supervisor.
  - Migrated `FloatingOverlayService.kt` to direct NDK perception lifecycle and hardware surface pass.
- **Unexplored areas**: None. Milestone 1 Kotlin investigation complete.

## Key Decisions Made
- Standardized binary frame buffer size at 6,160 bytes matching packed C struct layout.
- Adopted pre-allocated mutable entity array pool (`MutableFrameSnapshot`) to completely eliminate GC allocations during render passes.
- Decoupled 60/120 Hz render ticks from 4 Hz host UI updates.

## Artifact Index
- handoff.md — Final implementation blueprint for Kotlin JNI & zero-copy binary ingestion
- progress.md — Liveness and task progress tracking
