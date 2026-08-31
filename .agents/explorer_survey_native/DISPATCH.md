## 2026-08-30T20:10:48Z
Perform an in-depth survey of the native C/C++ engine requirements (R1):
1. Analyze existing codebase: `vemins_daemon.c`, `vemins_esp.cpp`, `gl_renderer.cpp`, `native_surface.cpp`, `offsets.json`, `FIELD_MAP.md`, `ARCHITECTURE.md`.
2. Determine how to completely eliminate the external background daemon (`vemins_daemon`) and TCP socket server (`127.0.0.1:9999`) / JSON streaming.
3. Design the in-app native JNI/NDK engine (`libvemins_engine.so`) with root access / direct `/proc/$PID/mem` read-only access (or `process_vm_readv`), zero-overhead PID & memory map caching.
4. Design the compact binary struct schema (`FrameSnapshot`) for zero-allocation, zero-JSON binary frame passing between native C++ memory reader and Kotlin/Android or native renderer.
5. Identify all necessary JNI bindings, C++ header structures, lifecycle management methods, and performance bottlenecks to ensure < 1.0 ms reading latency per tick.
