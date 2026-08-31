# BRIEFING — 2026-08-30T20:21:48Z

## Mission
Implement Milestone 1 & 2 (Native Perception Engine & Kotlin Binary Reader) for Vemins ESP.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /data/data/com.termux/files/home/veminsEsp/.agents/worker_m1_m2/
- Original parent: 5580e2a8-b30f-49b5-8218-bc08637dfba1
- Milestone: M1_M2

## 🔒 Key Constraints
- Pure genuine implementation, no dummy/facade implementations or hardcoded test values.
- Sub-1.0ms cycle latency for native memory perception.
- Direct pread /proc/$PID/mem reader with batch contiguous reads (0x220B for LogicBattleManager, 0x300B for LogicPlayer).
- Exact 6,160-byte packed binary schema across C++ and Kotlin.
- Gate 8 authoritative local player resolution: m_RealSelfPlayer (+0x200), fallback (+0x0a0).
- Dictionary parsing: 24B stride, hashCode >= 0 tombstone filtering, continuous coordinates [-52.0, +52.0].
- Minions (+0x128), monsters (+0x0b0), towers (+0xd0..+0xe8).
- Gate Bypass: never gate on battle_state.
- Camera EMA alpha=0.35 continuity across hero death/respawn.
- isfinite() float sanitization on all raw float reads.
- DirectByteBuffer zero-allocation polling and unpack in < 15 µs with 0 GC allocations.
- SurfaceView / ANativeWindow JNI lifecycle methods.
- CMakeLists.txt ARM64 build config.

## Current Parent
- Conversation ID: 5580e2a8-b30f-49b5-8218-bc08637dfba1
- Updated: 2026-08-30T20:21:48Z

## Task Summary
- **What to build**:
  1. C++ Native Engine (`engine_schema.h`, `memory_reader.h`, `memory_reader.cpp`, `jni_bridge.cpp`, `CMakeLists.txt`)
  2. Kotlin Binary Reader & JNI Engine (`VeminsNativeEngine.kt`, `FrameSnapshotBinary.kt`, `BinarySnapshotReader.kt`)
  3. Verification tests and builds.
- **Success criteria**:
  - Exact binary layout matching 6,160 bytes.
  - All test suites passing (`pytest tests/`).
  - Native compilation cleanly verified.
  - Full conformance with explorer / spec miner handoffs.

## Key Decisions Made
- [TBD]

## Change Tracker
- **Files modified**: None yet.
- **Build status**: Untested.
- **Pending issues**: None.

## Quality Status
- **Build/test result**: Not run yet.
- **Lint status**: 0.
- **Tests added/modified**: TBD.

## Loaded Skills
- None explicitly loaded.

## Artifact Index
- `.agents/worker_m1_m2/DISPATCH.md` — Assignment dispatch
- `.agents/worker_m1_m2/progress.md` — Progress tracker
- `.agents/worker_m1_m2/handoff.md` — Final handoff report
