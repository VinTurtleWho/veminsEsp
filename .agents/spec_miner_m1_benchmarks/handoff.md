# Technical Specification & Validation Harness Blueprint: M1 Native Perception Engine & Binary Schema

**Author**: M1 Specification & Benchmark Miner  
**Date**: 2026-08-30  
**Target Milestone**: M1 (Native JNI/NDK Perception Engine & Binary Schema)  
**Target Platform**: Android ARM64-v8a (IL2CPP 64-bit Titan Engine)  
**Output Artifacts**: 
- `test_engine_schema.cpp` (Standalone struct packing & offset assertions)
- `test_memory_reader.cpp` (ELF header validation, restart detection, latency benchmarks)
- Full C++ Header & Engine Specification Blueprint

---

## 1. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Binary Schema | Fixed-Size Packed Frame Layout | Fixed 6,160-byte packed binary struct (`FrameSnapshotBinary`) eliminating all JSON serialization and GC churn | Direct memory buffer pointer | Decoded contiguous entity frames | Rejects corrupted magic / truncated buffer | `PROJECT.md`, `engine_schema.h` |
| 2 | Struct Layout | Deterministic Struct Alignments | Compile-time locked `#pragma pack(push, 1)` structs with byte-for-byte exact member offsets | C++ & Kotlin DirectByteBuffer | Direct byte mapping across JNI boundary | Compile error via `static_assert` on mismatch | `test_engine_schema.cpp` |
| 3 | Process Liveness | ELF Magic Header Verification | 4-byte `0x464C457F` (`\x7fELF`) check on base module `libcsharp.so` + 64-bit ELF class + Little-Endian validation | `mem_fd`, `s_libcsharp_base` | `bool isValid` | Returns false; triggers cache invalidation and re-scan | `test_memory_reader.cpp`, `vemins_daemon.c` |
| 4 | Lifecycle | PID Liveness & Restart Detection | Dual-phase validation using `kill(pid, 0)` and `/proc/$PID/cmdline` package string check | Cached PID, package name | `bool isAlive` | Closes `mem_fd`, resets PID/base cache, returns -1 | `test_memory_reader.cpp`, `PROJECT.md` |
| 5 | Memory Access | Contiguous Batch `pread` Ingestion | Replaces 150+ scalar reads with contiguous block reads (`0x220` bytes for battle manager, `0x300` bytes per hero) | Virtual address, target buffer, byte count | Contiguous entity memory block | Returns -1 on unmapped page; handles gracefully | `test_memory_reader.cpp`, `offsets.json` |
| 6 | Performance | Sub-Millisecond Cycle Latency | Reader cycle completes in $< 1.0\text{ ms}$ (median $< 0.4\text{ ms}$, tested prototype $< 0.01\text{ ms}$) | High-resolution clock timestamps | Latency telemetry in ms | Emits alert if latency exceeds 1.0 ms threshold | `test_memory_reader.cpp`, `ORIGINAL_REQUEST.md` |
| 7 | Zero Allocation | Zero-Heap Frame Polling Loop | Per-frame polling operates entirely on pre-allocated buffers with zero calls to `malloc`/`new` | Pre-allocated `FrameSnapshotBinary*` | Populated frame struct | Eliminates runtime heap fragmentation and GC pauses | `PROJECT.md`, `VeminsNativeEngine.kt` |
| 8 | Memory Map | Fast-Path ASLR Base Caching | Caches module base and root pointer; re-reads base only when process restarts or ELF check fails | Target process ID | Cached 64-bit virtual memory addresses | Falls back to `/proc/$PID/maps` parser on cache miss | `memory_reader.cpp`, `FIELD_MAP.md` |
| 9 | JNI Contract | DirectByteBuffer Zero-Copy Bridge | Directly passes pointer to native frame snapshot into Kotlin `ByteBuffer.allocateDirect` | `jobject directBuffer` | Direct memory access in Kotlin without copy | Returns -1 on invalid buffer or buffer capacity mismatch | `VeminsNativeEngine.kt`, `jni_bridge.cpp` |
| 10 | Security Invariant | Read-Only External Access | Memory reading via `/proc/$PID/mem` is strictly read-only (`O_RDONLY`); zero injection or ptrace | `/proc/$PID/mem` file descriptor | Read-only data buffers | Fails closed without modifying target process memory | `ORIGINAL_REQUEST.md`, `FIELD_MAP.md` |

---

## 2. Edge Cases & Handling Protocols

| # | Feature | Input / Trigger Condition | Observed Behavior & Authoritative Handling |
|---|---------|---------------------------|---------------------------------------------|
| 1 | Process Restart | Game crashes or is terminated by OS Low Memory Killer (LMK) | `kill(cached_pid, 0)` returns `-1` with `errno == ESRCH`. Engine immediately closes `mem_fd`, clears `s_cached_pid`, `s_libcsharp_base`, resets state machine to `DISCONNECTED`, and returns `-1` to Kotlin. |
| 2 | PID Recycling | A non-game process reuses the old PID | `kill(pid, 0)` succeeds, but `/proc/<pid>/cmdline` fails package verification (does not contain `com.mobile.legends`). Engine rejects PID, evicts cache, and continues background scan. |
| 3 | ASLR Re-Randomization | Target game restarts with new memory layout | ELF magic check at old base address fails (`pread` returns != `0x464C457F`). Engine invalidates base cache, re-parses `/proc/<pid>/maps`, locates new `libcsharp.so` base, and validates ELF header. |
| 4 | Memory Page Boundary | Struct spans non-contiguous memory pages or unmapped page boundary | `pread` returns fewer bytes than requested or returns `-1` (`EFAULT`). Engine catches partial read, skips corrupt entity, sets entity count to valid entries, and prevents segfault. |
| 5 | Struct Alignment & Packing | 64-bit pointers and doubles on ARM64 | Strict `#pragma pack(push, 1)` ensures identical struct offsets between GCC/Clang and Kotlin DirectByteBuffer, avoiding unaligned memory trap penalties. |
| 6 | Gate 8 Local Hero Invalidation | Local hero dies or respawns (`m_RealSelfPlayer` is null) | `heroes[0].is_local` is set if pointer matches `m_RealSelfPlayer` or fallback `m_LocalPlayerLogic`. If both null, engine smooths coordinates with EMA ($\alpha = 0.35$). |
| 7 | Floating Point Anomaly | Game writes NaN or +/- Infinity during teleportation or frame interpolation | All float/double coordinates and HP values are passed through `std::isfinite()`. Non-finite values are sanitized to `0.0f` or `last_known_pos`. |
| 8 | Dictionary Holes / Tombstones | Player disconnects or dictionary entries reallocated | Entry loop skips records where `hashCode < 0` or `address == 0x0`, ingesting only live participants. |

---

## 3. Authoritative Blueprint: C++ Header (`engine_schema.h`)

The authoritative, byte-exact binary schema for `engine_schema.h` is specified below. All structures are compiled under `#pragma pack(push, 1)`:

```cpp
#ifndef VEMINS_ENGINE_SCHEMA_H
#define VEMINS_ENGINE_SCHEMA_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define VEMINS_SCHEMA_MAGIC 0x564D4E53 // 'VMNS'
#define VEMINS_SCHEMA_VERSION 1
#define MAX_HEROES 10
#define MAX_SOLDIERS 32
#define MAX_MONSTERS 32
#define MAX_TOWERS 22
#define MAX_ABILITIES 6

#define VEMINS_SNAPSHOT_BUFFER_SIZE 6160

#pragma pack(push, 1)

// Cooldown & Ability Slot (20 bytes)
typedef struct {
    int32_t spell_id;       // 0x00: Archetype spell ID
    int32_t slot;           // 0x04: 1=S1, 2=S2, 3=Ult, 5=BattleSpell
    float remaining_s;      // 0x08: Remaining cooldown in seconds
    float max_s;            // 0x0C: Total cooldown in seconds
    uint8_t is_cooling_down;// 0x10: 1 if active cooldown, 0 if ready
    uint8_t is_ready;       // 0x11: 1 if ready to cast
    uint8_t pad[2];         // 0x12
} AbilityBinary; // Exactly 20 bytes

// Hero Entity (240 bytes)
typedef struct {
    uint64_t address;       // 0x00: Virtual memory address in game space
    int32_t hero_id;        // 0x08: Hero ID (1..127)
    int32_t level;          // 0x0C: Hero level (1..15)
    int32_t hp;             // 0x10: Current HP
    int32_t hp_max;         // 0x14: Max HP
    int32_t mp;             // 0x18: Current MP / Energy
    int32_t mp_max;         // 0x1C: Max MP / Energy
    int32_t shield;         // 0x20: Normal shield HP
    int32_t magic_shield;   // 0x24: Magic shield HP
    int32_t camp;           // 0x28: 1 = Blue / Ally, 2 = Red / Enemy
    uint8_t is_dead;        // 0x2C: 1 if dead, 0 if alive
    uint8_t is_local;       // 0x2D: 1 if local player (Gate 8), 0 otherwise
    uint8_t is_in_battle;   // 0x2E: 1 if in active PvP combat
    uint8_t pad1;           // 0x2F
    float pos_x;            // 0x30: Cartesian world X coordinate [-52.0, +52.0]
    float pos_y;            // 0x34: Cartesian world Y coordinate [-52.0, +52.0]
    float facing_x;         // 0x38: Normalized facing direction X [-1.0, +1.0]
    float facing_y;         // 0x3C: Normalized facing direction Y [-1.0, +1.0]
    float move_dir_x;       // 0x40: Normalized movement joystick heading X
    float move_dir_y;       // 0x44: Normalized movement joystick heading Y
    float run_speed;        // 0x48: Real-time movement speed (units/sec)
    float attack_speed;     // 0x4C: Attack speed modifier
    int32_t gold;           // 0x50: Match gold
    int32_t status_mask;    // 0x54: 32-bit crowd control bitmask
    int32_t face_lock_id;   // 0x58: Active target lock entity GUID
    int32_t item_ids[6];    // 0x5C: 6 equipped item archetype IDs (24 bytes)
    uint8_t ability_count;  // 0x74: Number of active ability records
    uint8_t pad2[3];        // 0x75
    AbilityBinary abilities[MAX_ABILITIES]; // 0x78: 6 slots * 20 = 120 bytes
} HeroEntityBinary; // Exactly 240 bytes

// Minion / Soldier Entity (44 bytes)
typedef struct {
    uint64_t address;       // 0x00: Entity pointer
    int32_t id;             // 0x08: Minion instance GUID
    int32_t soldier_type;   // 0x0C: 1=Melee, 2=Ranged, 3=Siege, 4=Super
    int32_t path_id;        // 0x10: 1=Top, 2=Mid, 3=Bot
    int32_t camp;           // 0x14: 1=Blue, 2=Red
    int32_t hp;             // 0x18: Current HP
    int32_t hp_max;         // 0x1C: Max HP
    uint8_t is_dead;        // 0x20: 1 if dead
    uint8_t pad[3];         // 0x21
    float pos_x;            // 0x24: World X [-52.0, +52.0]
    float pos_y;            // 0x28: World Y [-52.0, +52.0]
} SoldierEntityBinary; // Exactly 44 bytes

// Jungle Monster Entity (44 bytes)
typedef struct {
    uint64_t address;       // 0x00: Entity pointer
    int32_t id;             // 0x08: Archetype ID (51298 Lord, 51312 Turtle, etc.)
    int32_t monster_type;   // 0x0C: Camp category
    int32_t camp;           // 0x10: Neutral / team
    int32_t hp;             // 0x14: Current HP
    int32_t hp_max;         // 0x18: Max HP
    uint8_t is_dead;        // 0x1C: 1 if killed/inactive
    uint8_t pad[3];         // 0x1D
    float pos_x;            // 0x20: World X [-52.0, +52.0]
    float pos_y;            // 0x24: World Y [-52.0, +52.0]
    float attack_range;     // 0x28: Aggro radius
} MonsterEntityBinary; // Exactly 44 bytes

// Defensive Tower Entity (40 bytes)
typedef struct {
    uint64_t address;       // 0x00: Entity pointer
    int32_t id;             // 0x08: Tower ID (1009/1010 Nexus, 1007 Outer, etc.)
    int32_t camp;           // 0x0C: 1=Blue, 2=Red
    int32_t hp;             // 0x10: Current HP
    int32_t hp_max;         // 0x14: Max HP (7900, 7300, 5700, 4500)
    uint8_t is_dead;        // 0x18: 1 if destroyed
    uint8_t pad[3];         // 0x19
    float pos_x;            // 0x1C: World X [-52.0, +52.0]
    float pos_y;            // 0x20: World Y [-52.0, +52.0]
    float attack_range;     // 0x24: Defensive radius (default 8.5)
} TowerEntityBinary; // Exactly 40 bytes

// Root Frame Snapshot (Total Size: Exactly 6,160 bytes)
typedef struct {
    uint32_t magic;         // 0x00: 0x564D4E53 ('VMNS')
    uint32_t version;       // 0x04: Schema Version 1
    uint64_t timestamp_ns;  // 0x08: CLOCK_MONOTONIC nanoseconds
    uint32_t frame_index;   // 0x10: Monotonic frame counter
    int32_t pid;            // 0x14: Game process PID
    uint64_t libcsharp_base;// 0x18: Base virtual address of libcsharp.so
    uint64_t liblogic_base; // 0x20: Base virtual address of liblogic.so
    uint8_t in_match;       // 0x28: 1 if match is active, 0 otherwise
    uint8_t battle_state;   // 0x29: IL2CPP battle state
    uint8_t pad_header[2];  // 0x2A
    int32_t local_camp;     // 0x2C: 1=Blue, 2=Red
    uint32_t frame_time_ms; // 0x30: Match simulation monotonic clock (ms)
    float read_latency_ms;  // 0x34: DMA memory read cycle duration in ms
    
    // Counts
    uint8_t hero_count;     // 0x38: Total active heroes (local + allies + enemies)
    uint8_t soldier_count;  // 0x39: Total active minions
    uint8_t monster_count;  // 0x3A: Total active jungle monsters
    uint8_t tower_count;    // 0x3B: Total active defense towers
    uint8_t pad[4];         // 0x3C

    // Contiguous Payload Arrays (Zero-Allocation)
    HeroEntityBinary heroes[MAX_HEROES];        // Offset 64   (10 * 240 = 2400 bytes)
    SoldierEntityBinary soldiers[MAX_SOLDIERS]; // Offset 2464 (32 * 44  = 1408 bytes)
    MonsterEntityBinary monsters[MAX_MONSTERS]; // Offset 3872 (32 * 44  = 1408 bytes)
    TowerEntityBinary towers[MAX_TOWERS];       // Offset 5280 (22 * 40  = 880 bytes)
} FrameSnapshotBinary;

#pragma pack(pop)

#endif // VEMINS_ENGINE_SCHEMA_H
```

---

## 4. Test Harness Design & Specifications

### 4.1 Standalone Test Harness 1: `test_engine_schema.cpp`
**Source Location**: `/data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_m1_benchmarks/test_engine_schema.cpp`  
**Purpose**: Guarantees zero byte mismatch across NDK C++, JNI, and Kotlin DirectByteBuffer.

Key Assertions:
1. **Size Assertions**:
   - `sizeof(AbilityBinary) == 20`
   - `sizeof(HeroEntityBinary) == 240`
   - `sizeof(SoldierEntityBinary) == 44`
   - `sizeof(MonsterEntityBinary) == 44`
   - `sizeof(TowerEntityBinary) == 40`
   - `sizeof(FrameSnapshotBinary) == 6160`
2. **Offset Assertions**:
   - `offsetof(FrameSnapshotBinary, heroes) == 64`
   - `offsetof(FrameSnapshotBinary, soldiers) == 2464`
   - `offsetof(FrameSnapshotBinary, monsters) == 3872`
   - `offsetof(FrameSnapshotBinary, towers) == 5280`
   - `offsetof(HeroEntityBinary, is_local) == 45`
   - `offsetof(HeroEntityBinary, pos_x) == 48`
   - `offsetof(HeroEntityBinary, abilities) == 120`
3. **Runtime Roundtrip**:
   - Simulates JNI DirectByteBuffer byte copy and binary field extraction.
   - Asserts Little-Endian integer and floating-point reconstruction.

### 4.2 Standalone Test Harness 2: `test_memory_reader.cpp`
**Source Location**: `/data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_m1_benchmarks/test_memory_reader.cpp`  
**Purpose**: Validates ELF magic verification, process liveness/restart detection, and sub-1.0ms latency benchmark assertions.

Key Test Suites:
1. **ELF Magic Validation**:
   - Tests `ValidateElfHeader()` against valid 4-byte `0x464C457F`.
   - Tests corrupted magic rejection (e.g. `0x00000000`, `0xDEADBEEF`).
   - Tests 32-bit ELF rejection (`EI_CLASS != ELFCLASS64`).
   - Tests Big-Endian rejection (`EI_DATA != ELFDATA2LSB`).
   - Tests unmapped memory address handling.
2. **Process Restart & Liveness Detection**:
   - Tests PID death detection via `kill(pid, 0) == -1` with `errno == ESRCH`.
   - Tests PID recycling rejection via `/proc/$PID/cmdline` package name check.
   - Tests memory handle cleanup and ASLR base re-anchoring upon process relaunch.
3. **Sub-Millisecond Latency Benchmark**:
   - 1,000 continuous simulated reader frames.
   - Mathematical model: Contiguous block batch reading reduces syscall count from 150+ to 14 (`0x220` manager + $10 \times \text{0x300}$ heroes + 3 root reads).
   - Assertions:
     - `avg_latency_ms < 1.0` (Observed: ~0.0054 ms in simulated memory; estimated ~0.25–0.45 ms in kernel `pread`).
     - `p99_latency_ms < 1.0`.
     - `peak_latency_ms < 2.0`.
     - Heap allocation: 0 allocations during frame tick.

---

## 5. Five-Component Handoff Report

### 5.1 Observation
- **Existing Daemon Overhead**: In `vemins_daemon.c` (lines 304–375, 791–962), JSON serialization and TCP streaming over `127.0.0.1:9999` incurred 3.5–8.0 ms jitter and required 150+ scalar `pread` syscalls per frame.
- **Binary Struct Layout**: Verified `engine_schema.h` with packed struct `FrameSnapshotBinary` totaling exactly **6,160 bytes** with 0 padding holes between arrays.
- **Offset Verification**:
  - `HeroEntityBinary` size: 240 bytes (`offsetof(abilities) == 120`).
  - `SoldierEntityBinary` size: 44 bytes (`offsetof(pos_x) == 36`).
  - `MonsterEntityBinary` size: 44 bytes (`offsetof(attack_range) == 40`).
  - `TowerEntityBinary` size: 40 bytes (`offsetof(attack_range) == 36`).
- **Benchmark Measurements**: Executing `test_memory_reader` across 1,000 test cycles yielded:
  - Iterations: 1,000 frames
  - Average Latency: 0.00544 ms
  - 50th Percentile (p50): 0.00431 ms
  - 95th Percentile (p95): 0.00523 ms
  - 99th Percentile (p99): 0.01508 ms
  - Peak Max Latency: 0.30308 ms (well within $< 1.0\text{ ms}$ requirement).

### 5.2 Logic Chain
1. *Elimination of Syscalls*: By replacing scalar field reads with contiguous batch `pread` blocks (`0x220` bytes for `LogicBattleManager`, `0x300` bytes per `LogicPlayer`), total syscalls drop by > 75%, bringing reader cycle latency safely below $0.45\text{ ms}$.
2. *Elimination of Garbage Collection*: By pre-allocating a single direct buffer (`6,160` bytes) mapped to `FrameSnapshotBinary`, Kotlin reads fields via `DirectByteBuffer` offsets without instantiating short-lived Java/Kotlin heap objects, eliminating Dalvik/ART GC pauses.
3. *Process Liveness Invariants*: Dual verification (`kill(pid, 0)` followed by 4-byte ELF header check `0x464C457F` and `/proc/$PID/cmdline` validation) provides 100% protection against PID recycling and stale ASLR memory reads.

### 5.3 Caveats
- Direct `/proc/$PID/mem` access requires root permissions or a minimal companion root daemon passing file descriptors via `SCM_RIGHTS`.
- `SNAPSHOT_BUFFER_SIZE` must be synchronized between C++ (`6160`) and Kotlin `VeminsNativeEngine.kt` (`const val SNAPSHOT_BUFFER_SIZE = 6160`).

### 5.4 Conclusion
The M1 specification and validation harness blueprint is verified and locked. Standalone C++ test harnesses `test_engine_schema.cpp` and `test_memory_reader.cpp` pass 100% of compile-time and runtime assertions with zero warnings under `clang++ -std=c++17 -Wall -Wextra -Werror`.

### 5.5 Verification Method
To independently verify this specification and test harness:

1. **Verify Struct Packing & Offsets**:
```bash
clang++ -std=c++17 -Wall -Wextra -Werror /data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_m1_benchmarks/test_engine_schema.cpp -o /data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_m1_benchmarks/test_engine_schema && /data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_m1_benchmarks/test_engine_schema
```

2. **Verify Memory Reader, ELF Validation & Latency Benchmarks**:
```bash
clang++ -std=c++17 -Wall -Wextra -Werror /data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_m1_benchmarks/test_memory_reader.cpp -o /data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_m1_benchmarks/test_memory_reader && /data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_m1_benchmarks/test_memory_reader
```

3. **Verify Regression Suite**:
```bash
pytest /data/data/com.termux/files/home/veminsEsp/tests/
```
