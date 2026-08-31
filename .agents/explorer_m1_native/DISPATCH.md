## 2026-08-30T20:17:05Z
You are the Native C++ Implementation Explorer for Milestone 1 (M1).
Your working directory is /data/data/com.termux/files/home/veminsEsp/.agents/explorer_m1_native/
Read:
- /data/data/com.termux/files/home/veminsEsp/ORIGINAL_REQUEST.md
- /data/data/com.termux/files/home/veminsEsp/PROJECT.md
- /data/data/com.termux/files/home/veminsEsp/.agents/explorer_survey_native/handoff.md
- /data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_survey_perception/handoff.md

Task:
Produce a detailed implementation blueprint for the C++ native engine:
1. Complete exact source definitions for `engine_schema.h` with packed struct `FrameSnapshotBinary` (4,880 bytes).
2. Complete source definitions for `memory_reader.h` and `memory_reader.cpp` with cached PID, ELF magic validation, batch `pread` for `LogicBattleManager` (0x220 bytes) and `LogicPlayer` (0x300 bytes), and sub-1.0ms DMA reading.
3. Complete source definitions for `jni_bridge.cpp` implementing all JNI entry points for `com.vemins.esp.engine.VeminsNativeEngine`.
4. Define compilation flags (Clang++ C++17, -O3, -fPIC, -shared, ARM64-v8a) and build integration.

Write your report to `/data/data/com.termux/files/home/veminsEsp/.agents/explorer_m1_native/handoff.md` and update your `progress.md`.
