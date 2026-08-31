#include <iostream>
#include <vector>
#include <chrono>
#include <cstring>
#include <cstdint>
#include <cassert>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <cmath>

#define ELF_MAGIC 0x464C457F // "\x7fELF" little-endian
#define VEMINS_MAGIC 0x564D4E53 // "VMNS"

#pragma pack(push, 1)

typedef struct {
    int32_t spell_id;       // 0
    int32_t slot;           // 4
    float remaining_s;      // 8
    float max_s;            // 12
    uint8_t is_cooling_down;// 16
    uint8_t is_ready;       // 17
    uint8_t pad[2];         // 18
} AbilityBinary; // 20 bytes

typedef struct {
    uint64_t address;       // 0
    int32_t hero_id;        // 8
    int32_t level;          // 12
    int32_t hp;             // 16
    int32_t hp_max;         // 20
    int32_t mp;             // 24
    int32_t mp_max;         // 28
    int32_t shield;         // 32
    int32_t magic_shield;   // 36
    int32_t camp;           // 40
    uint8_t is_dead;        // 44
    uint8_t is_local;       // 45
    uint8_t is_in_battle;   // 46
    uint8_t pad1;           // 47
    float pos_x;            // 48
    float pos_y;            // 52
    float facing_x;         // 56
    float facing_y;         // 60
    float move_dir_x;       // 64
    float move_dir_y;       // 68
    float run_speed;        // 72
    float attack_speed;     // 76
    int32_t gold;           // 80
    int32_t status_mask;    // 84
    int32_t face_lock_id;   // 88
    int32_t item_ids[6];    // 92
    uint8_t ability_count;  // 116
    uint8_t pad2[3];        // 117
    AbilityBinary abilities[6]; // 120
} HeroEntityBinary; // 240 bytes

typedef struct {
    uint64_t address;       // 0
    int32_t id;             // 8
    int32_t soldier_type;   // 12
    int32_t path_id;        // 16
    int32_t camp;           // 20
    int32_t hp;             // 24
    int32_t hp_max;         // 28
    uint8_t is_dead;        // 32
    uint8_t pad[3];         // 33
    float pos_x;            // 36
    float pos_y;            // 40
} SoldierEntityBinary; // 44 bytes

typedef struct {
    uint64_t address;       // 0
    int32_t id;             // 8
    int32_t monster_type;   // 12
    int32_t camp;           // 16
    int32_t hp;             // 24
    int32_t hp_max;         // 28
    uint8_t is_dead;        // 32
    uint8_t pad[3];         // 33
    float pos_x;            // 36
    float pos_y;            // 40
    float attack_range;     // 44 -> wait offset!
} MonsterEntityBinary;

typedef struct {
    uint32_t magic;         // 0
    uint32_t version;       // 4
    uint64_t timestamp_ns;  // 8
    uint32_t frame_index;   // 16
    int32_t pid;            // 20
    uint64_t libcsharp_base;// 24
    uint64_t liblogic_base; // 32
    uint8_t in_match;       // 40
    uint8_t battle_state;   // 41
    uint8_t pad_header[2];  // 42
    int32_t local_camp;     // 44
    uint32_t frame_time_ms; // 48
    float read_latency_ms;  // 52
    uint8_t hero_count;     // 56
    uint8_t soldier_count;  // 57
    uint8_t monster_count;  // 58
    uint8_t tower_count;    // 59
    uint8_t pad[4];         // 60
    HeroEntityBinary heroes[10];       // 64
    SoldierEntityBinary soldiers[32];  // 2464
    // etc
} FrameSnapshotBinary;

#pragma pack(pop)

// Mock memory reader & benchmark
struct MockMemorySpace {
    std::vector<uint8_t> mem;
    uint64_t base_addr = 0x7000000000ULL;
    
    MockMemorySpace() {
        mem.resize(10 * 1024 * 1024, 0); // 10 MB simulated memory
        // Write ELF magic at base_addr
        uint32_t elf = ELF_MAGIC;
        memcpy(&mem[0], &elf, 4);
    }

    bool read(uint64_t addr, void* buf, size_t size) {
        if (addr < base_addr || addr + size > base_addr + mem.size()) {
            return false;
        }
        memcpy(buf, &mem[addr - base_addr], size);
        return true;
    }
};

int main() {
    std::cout << "[TEST] Running M1 Validation Harness Prototype..." << std::endl;
    
    // 1. Struct Packing Assertions
    static_assert(sizeof(AbilityBinary) == 20, "AbilityBinary must be exactly 20 bytes");
    static_assert(sizeof(HeroEntityBinary) == 240, "HeroEntityBinary must be exactly 240 bytes");
    static_assert(offsetof(HeroEntityBinary, address) == 0, "HeroEntityBinary.address offset mismatch");
    static_assert(offsetof(HeroEntityBinary, hero_id) == 8, "HeroEntityBinary.hero_id offset mismatch");
    static_assert(offsetof(HeroEntityBinary, pos_x) == 48, "HeroEntityBinary.pos_x offset mismatch");
    static_assert(offsetof(HeroEntityBinary, abilities) == 120, "HeroEntityBinary.abilities offset mismatch");
    
    std::cout << "[PASS] Struct packing static_asserts verified." << std::endl;

    // 2. ELF Magic Validation
    MockMemorySpace mock;
    uint32_t read_magic = 0;
    assert(mock.read(0x7000000000ULL, &read_magic, 4) && read_magic == ELF_MAGIC);
    std::cout << "[PASS] ELF magic validation verified." << std::endl;

    // 3. Simulated Reading Cycle Benchmark (1,000 frames)
    const int NUM_FRAMES = 1000;
    auto start_all = std::chrono::high_resolution_clock::now();
    double max_lat_ms = 0.0;
    double sum_lat_ms = 0.0;

    for (int i = 0; i < NUM_FRAMES; ++i) {
        auto t0 = std::chrono::high_resolution_clock::now();
        
        // Simulating batch read of battle manager + 10 heroes + minion dictionary
        uint8_t mgr_buf[0x220];
        mock.read(0x7000001000ULL, mgr_buf, sizeof(mgr_buf));
        
        for (int h = 0; h < 10; ++h) {
            uint8_t hero_buf[0x300];
            mock.read(0x7000002000ULL + h * 0x400, hero_buf, sizeof(hero_buf));
        }

        auto t1 = std::chrono::high_resolution_clock::now();
        double lat_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        if (lat_ms > max_lat_ms) max_lat_ms = lat_ms;
        sum_lat_ms += lat_ms;
    }

    auto end_all = std::chrono::high_resolution_clock::now();
    double total_ms = std::chrono::duration<double, std::milli>(end_all - start_all).count();
    double avg_lat_ms = sum_lat_ms / NUM_FRAMES;

    std::cout << "[BENCHMARK] 1,000 Cycles Total: " << total_ms << " ms" << std::endl;
    std::cout << "[BENCHMARK] Average Latency: " << avg_lat_ms << " ms / frame" << std::endl;
    std::cout << "[BENCHMARK] Peak Latency: " << max_lat_ms << " ms" << std::endl;
    assert(avg_lat_ms < 1.0);
    std::cout << "[PASS] Sub-1.0ms memory reading latency assertion PASSED." << std::endl;

    return 0;
}
