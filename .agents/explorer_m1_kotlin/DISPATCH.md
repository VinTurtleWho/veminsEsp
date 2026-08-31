## 2026-08-30T20:17:05Z
You are the Kotlin JNI Integration Explorer for Milestone 1 (M1).
Your working directory is /data/data/com.termux/files/home/veminsEsp/.agents/explorer_m1_kotlin/
Read:
- /data/data/com.termux/files/home/veminsEsp/ORIGINAL_REQUEST.md
- /data/data/com.termux/files/home/veminsEsp/PROJECT.md
- /data/data/com.termux/files/home/veminsEsp/.agents/explorer_survey_native/handoff.md
- /data/data/com.termux/files/home/veminsEsp/.agents/explorer_survey_ui_build/handoff.md

Task:
Produce a detailed implementation blueprint for Kotlin JNI bindings and zero-copy binary ingestion:
1. Design `VeminsNativeEngine.kt` in `com.vemins.esp.engine` with DirectByteBuffer management and JNI declarations.
2. Design zero-allocation binary reader `FrameSnapshotBinary.kt` / `BinarySnapshotReader.kt` that directly unpacks the DirectByteBuffer without creating short-lived Java heap objects.
3. Plan migration of `TelemetryClient.kt` and `FloatingOverlayService.kt` to poll native direct buffers instead of TCP socket JSON.
4. Ensure zero GC pauses during 60/120 FPS render ticks.

Write your report to `/data/data/com.termux/files/home/veminsEsp/.agents/explorer_m1_kotlin/handoff.md` and update your `progress.md`.
