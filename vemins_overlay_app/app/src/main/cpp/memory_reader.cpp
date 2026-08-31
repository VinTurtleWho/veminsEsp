#include "memory_reader.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <time.h>
#include <math.h>
#include <android/log.h>

#define LOG_TAG "VeminsNativeEngine"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)
#define LOGD(...) __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, __VA_ARGS__)

// Invariant Constants
static const uint64_t RVA_STATIC_ROOT = 0x7680928;
static const uint32_t ELF_MAGIC = 0x464C457F; // "\x7fELF" Little Endian
static const float EMA_ALPHA = 0.35f;
static const float COORD_MIN = -52.0f;
static const float COORD_MAX = 52.0f;

// Global Reader State
static int s_cached_mem_fd = -1;
static int s_cached_pid = -1;
static uint64_t s_libcsharp_base = 0;
static uint64_t s_liblogic_base = 0;
static uint32_t s_frame_counter = 0;

// Camera Continuity State
static float s_last_known_local_x = 0.0f;
static float s_last_known_local_y = 0.0f;
static bool s_has_last_known_pos = false;

// Performance Telemetry State
static float s_last_latency_ms = 0.0f;
static uint64_t s_last_frame_time_ns = 0;
static float s_current_fps = 0.0f;

// ============================================================================
// Coordinate Sanitization & Safety Helpers
// ============================================================================
static inline float sanitize_coord(double val, float fallback, float min_v, float max_v) {
    if (!isfinite(val)) return fallback;
    float f = (float)val;
    if (f < min_v) return min_v;
    if (f > max_v) return max_v;
    return f;
}

static inline float sanitize_float(float val, float fallback) {
    if (!isfinite(val)) return fallback;
    return val;
}

static inline uint64_t get_monotonic_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

// ============================================================================
// Direct Memory Read Helpers
// ============================================================================
static inline bool read_mem(int fd, uint64_t addr, void *buf, size_t size) {
    addr &= 0x0000FFFFFFFFFFFFULL;
    if (fd < 0 || addr < 0x10000 || buf == nullptr || size == 0) return false;
    ssize_t bytes = pread(fd, buf, size, static_cast<off_t>(addr));
    return (bytes == static_cast<ssize_t>(size));
}

static inline uint64_t read_u64(int fd, uint64_t addr) {
    uint64_t val = 0;
    if (read_mem(fd, addr, &val, sizeof(val))) {
        return val;
    }
    return 0;
}

static inline int32_t read_i32(int fd, uint64_t addr) {
    int32_t val = 0;
    if (read_mem(fd, addr, &val, sizeof(val))) {
        return val;
    }
    return 0;
}

// ============================================================================
// Memory Map Scanning (Only Executed on Cold Start / Re-Scan)
// ============================================================================
static uint64_t find_module_base(int pid, const char *module_name) {
    if (pid <= 0 || module_name == nullptr) return 0;
    char path[128];
    snprintf(path, sizeof(path), "/proc/%d/maps", pid);
    FILE *f = fopen(path, "r");
    if (!f) return 0;

    char line[512];
    uint64_t base = 0;
    while (fgets(line, sizeof(line), f)) {
        if (strstr(line, module_name) && strstr(line, "r-xp")) {
            char *endptr = nullptr;
            base = strtoull(line, &endptr, 16);
            break;
        }
    }
    fclose(f);
    return base;
}

// ============================================================================
// Reader Lifecycle Implementations
// ============================================================================
void memory_reader_init(void) {
    s_cached_mem_fd = -1;
    s_cached_pid = -1;
    s_libcsharp_base = 0;
    s_liblogic_base = 0;
    s_frame_counter = 0;
    s_has_last_known_pos = false;
    s_last_known_local_x = 0.0f;
    s_last_known_local_y = 0.0f;
}

void memory_reader_release(void) {
    if (s_cached_mem_fd >= 0) {
        close(s_cached_mem_fd);
        s_cached_mem_fd = -1;
    }
    s_cached_pid = -1;
    s_libcsharp_base = 0;
    s_liblogic_base = 0;
}

bool memory_reader_set_fd(int fd, int pid) {
    if (s_cached_mem_fd >= 0 && s_cached_mem_fd != fd) {
        close(s_cached_mem_fd);
    }
    s_cached_mem_fd = fd;
    s_cached_pid = pid;
    s_libcsharp_base = 0;
    s_liblogic_base = 0;
    return (s_cached_mem_fd >= 0 && s_cached_pid > 0);
}

bool memory_reader_is_attached(void) {
    return (s_cached_mem_fd >= 0 && s_cached_pid > 0 && memory_reader_check_liveness());
}

bool memory_reader_check_liveness(void) {
    if (s_cached_pid <= 0) return false;
    return (kill(s_cached_pid, 0) == 0);
}

bool memory_reader_validate_elf_magic(uint64_t base_addr) {
    if (s_cached_mem_fd < 0 || base_addr == 0) return false;
    uint32_t magic = 0;
    if (read_mem(s_cached_mem_fd, base_addr, &magic, sizeof(magic))) {
        return (magic == ELF_MAGIC);
    }
    return false;
}

// ============================================================================
// Entity Parsing Helpers (Batch Ingestion)
// ============================================================================
static void parse_hero_entity(int fd, uint64_t player_addr, uint64_t self_ptr, HeroEntityBinary *hero) {
    memset(hero, 0, sizeof(HeroEntityBinary));
    hero->address = player_addr;
    if (player_addr == 0) return;

    // Batch read 0x300 bytes of LogicPlayer
    uint8_t raw[0x300];
    if (!read_mem(fd, player_addr, raw, sizeof(raw))) return;

    // Extract core vitals
    hero->hero_id = *reinterpret_cast<int32_t*>(&raw[0x0ac]);
    hero->level = *reinterpret_cast<int32_t*>(&raw[0x0b4]);
    hero->hp = *reinterpret_cast<int32_t*>(&raw[0x0c8]);
    hero->hp_max = *reinterpret_cast<int32_t*>(&raw[0x0cc]);
    hero->shield = *reinterpret_cast<int32_t*>(&raw[0x0e4]);
    hero->magic_shield = *reinterpret_cast<int32_t*>(&raw[0x0f0]);
    hero->mp = *reinterpret_cast<int32_t*>(&raw[0x108]);
    hero->mp_max = *reinterpret_cast<int32_t*>(&raw[0x10c]);
    hero->is_dead = (raw[0x1d0] != 0 || hero->hp <= 0) ? 1 : 0;
    hero->camp = *reinterpret_cast<int32_t*>(&raw[0x1dc]);
    hero->status_mask = *reinterpret_cast<int32_t*>(&raw[0x1e4]);
    hero->is_in_battle = raw[0x21c];

    // Cartesian Coordinates & Vectors
    double raw_x = *reinterpret_cast<double*>(&raw[0x268]);
    double raw_y = *reinterpret_cast<double*>(&raw[0x270]);
    hero->pos_x = sanitize_coord(raw_x, 0.0f, COORD_MIN, COORD_MAX);
    hero->pos_y = sanitize_coord(raw_y, 0.0f, COORD_MIN, COORD_MAX);

    double move_x = *reinterpret_cast<double*>(&raw[0x288]);
    double move_y = *reinterpret_cast<double*>(&raw[0x290]);
    hero->move_dir_x = sanitize_float(static_cast<float>(move_x), 0.0f);
    hero->move_dir_y = sanitize_float(static_cast<float>(move_y), 0.0f);

    double face_x = *reinterpret_cast<double*>(&raw[0x298]);
    double face_y = *reinterpret_cast<double*>(&raw[0x2a0]);
    hero->facing_x = sanitize_float(static_cast<float>(face_x), 1.0f);
    hero->facing_y = sanitize_float(static_cast<float>(face_y), 0.0f);

    hero->face_lock_id = *reinterpret_cast<int32_t*>(&raw[0x370]);

    // Read remaining extended attributes with scalar reads if valid
    double run_spd = 0.0;
    if (read_mem(fd, player_addr + 0x750, &run_spd, sizeof(run_spd))) {
        hero->run_speed = sanitize_float(static_cast<float>(run_spd), 340.0f);
    } else {
        hero->run_speed = 340.0f;
    }

    double atk_spd = 0.0;
    if (read_mem(fd, player_addr + 0x758, &atk_spd, sizeof(atk_spd))) {
        hero->attack_speed = sanitize_float(static_cast<float>(atk_spd), 1.0f);
    } else {
        hero->attack_speed = 1.0f;
    }

    int32_t gold_val = 0;
    if (read_mem(fd, player_addr + 0x858, &gold_val, sizeof(gold_val))) {
        hero->gold = gold_val;
    }

    // Gate 8 Identity Matching
    hero->is_local = (self_ptr != 0 && player_addr == self_ptr) ? 1 : 0;
}

static void parse_hero_abilities(int fd, uint64_t player_addr, uint32_t current_battle_time, HeroEntityBinary *hero) {
    hero->ability_count = 0;
    if (player_addr == 0 || fd < 0) return;

    // LogicPlayer.m_SkillComp is at +0x4e0 (IL2CPP 64-bit primary), fallback +0x4c0
    uint64_t skill_comp_ptr = read_u64(fd, player_addr + 0x4e0);
    if (skill_comp_ptr < 0x10000) {
        skill_comp_ptr = read_u64(fd, player_addr + 0x4c0);
    }
    if (skill_comp_ptr < 0x10000) return;

    // LogicSkillComp.m_CoolDownComp is at +0x0a8
    uint64_t cd_comp_ptr = read_u64(fd, skill_comp_ptr + 0x0a8);
    if (cd_comp_ptr < 0x10000) return;

    // CoolDownComp.m_DicCoolInfo is at +0x018
    uint64_t dict_ptr = read_u64(fd, cd_comp_ptr + 0x018);
    if (dict_ptr < 0x10000) return;

    uint64_t entries_ptr = read_u64(fd, dict_ptr + 0x018);
    int32_t entry_count = read_i32(fd, dict_ptr + 0x020);
    if (entries_ptr < 0x10000 || entry_count <= 0 || entry_count > 32) return;

    uint8_t entries_buf[32 * 24];
    size_t bytes_to_read = (entry_count > 32 ? 32 : entry_count) * 24;
    if (!read_mem(fd, entries_ptr + 0x20, entries_buf, bytes_to_read)) return;

    int32_t hero_id = hero->hero_id;
    int expected_s1 = hero_id * 100 + 10;
    int expected_s2 = hero_id * 100 + 20;
    int expected_s3 = hero_id * 100 + 30;
    int expected_s4 = hero_id * 100 + 40;

    uint8_t ab_cnt = 0;
    for (int i = 0; i < entry_count && ab_cnt < MAX_ABILITIES; ++i) {
        size_t offset = i * 24;
        int32_t hash_code = *reinterpret_cast<int32_t*>(&entries_buf[offset + 0x00]);
        int32_t key_spell_id = *reinterpret_cast<int32_t*>(&entries_buf[offset + 0x08]);
        uint64_t cd_data_ptr = *reinterpret_cast<uint64_t*>(&entries_buf[offset + 0x10]);

        if (hash_code >= 0 && cd_data_ptr >= 0x10000) {
            uint8_t cd_buf[32];
            if (read_mem(fd, cd_data_ptr + 0x010, cd_buf, sizeof(cd_buf))) {
                int32_t iSpellID = *reinterpret_cast<int32_t*>(&cd_buf[0x00]);
                uint32_t uiCoolTime = *reinterpret_cast<uint32_t*>(&cd_buf[0x04]);
                uint32_t originalMaxCdTime = *reinterpret_cast<uint32_t*>(&cd_buf[0x08]);
                uint32_t uiStartTime = *reinterpret_cast<uint32_t*>(&cd_buf[0x0c]);
                uint8_t m_isCoolDown = cd_buf[0x10];

                int32_t final_spell_id = (iSpellID > 0) ? iSpellID : key_spell_id;
                if (final_spell_id <= 0) continue;

                uint32_t end_time = uiStartTime + uiCoolTime;
                float rem_s = 0.0f;
                uint8_t is_cooling = (m_isCoolDown != 0) ? 1 : 0;

                if (is_cooling && current_battle_time > 0 && end_time > current_battle_time) {
                    uint32_t diff_ms = end_time - current_battle_time;
                    if (diff_ms > 50) {
                        rem_s = static_cast<float>(diff_ms) / 1000.0f;
                    } else {
                        rem_s = 0.0f;
                        is_cooling = 0;
                    }
                } else if (is_cooling && uiCoolTime > 0) {
                    rem_s = static_cast<float>(uiCoolTime) / 1000.0f;
                } else {
                    rem_s = 0.0f;
                    is_cooling = 0;
                }

                float max_s = (originalMaxCdTime > 0) ? (static_cast<float>(originalMaxCdTime) / 1000.0f) : (static_cast<float>(uiCoolTime) / 1000.0f);
                if (max_s <= 0.0f && rem_s > 0.0f) max_s = rem_s;

                // Determine semantic skill slot
                int slot = ab_cnt + 1;
                if (final_spell_id == expected_s1 || (final_spell_id % 100 == 10)) {
                    slot = 1;
                } else if (final_spell_id == expected_s2 || (final_spell_id % 100 == 20)) {
                    slot = 2;
                } else if (final_spell_id == expected_s3 || (final_spell_id % 100 == 30)) {
                    slot = 3;
                } else if (final_spell_id == expected_s4 || (final_spell_id % 100 == 40)) {
                    slot = 4;
                } else if ((final_spell_id >= 20000 && final_spell_id < 30000) || (final_spell_id >= 200000 && final_spell_id < 300000)) {
                    slot = 5;
                }

                AbilityBinary *ab = &hero->abilities[ab_cnt];
                ab->spell_id = final_spell_id;
                ab->slot = slot;
                ab->remaining_s = rem_s;
                ab->max_s = max_s;
                ab->is_cooling_down = is_cooling;
                ab->is_ready = (is_cooling == 0 || rem_s <= 0.0f) ? 1 : 0;
                ab_cnt++;
            }
        }
    }
    hero->ability_count = ab_cnt;
}

static void parse_soldier_entity(int fd, uint64_t soldier_addr, SoldierEntityBinary *soldier) {
    memset(soldier, 0, sizeof(SoldierEntityBinary));
    soldier->address = soldier_addr;
    if (soldier_addr == 0) return;

    uint8_t raw[0x280];
    if (!read_mem(fd, soldier_addr, raw, sizeof(raw))) return;

    soldier->id = *reinterpret_cast<int32_t*>(&raw[0x0ac]);
    soldier->hp = *reinterpret_cast<int32_t*>(&raw[0x0c8]);
    soldier->hp_max = *reinterpret_cast<int32_t*>(&raw[0x0cc]);
    soldier->is_dead = (raw[0x1d0] != 0 || soldier->hp <= 0) ? 1 : 0;
    soldier->camp = static_cast<uint8_t>(*reinterpret_cast<int32_t*>(&raw[0x1dc]));

    double rx = *reinterpret_cast<double*>(&raw[0x268]);
    double ry = *reinterpret_cast<double*>(&raw[0x270]);
    soldier->pos_x = sanitize_coord(rx, 0.0f, COORD_MIN, COORD_MAX);
    soldier->pos_y = sanitize_coord(ry, 0.0f, COORD_MIN, COORD_MAX);

    // Soldier type (+0x8f0) and Lane (+0x900)
    int32_t st = 1, lane = 2;
    read_mem(fd, soldier_addr + 0x8f0, &st, sizeof(st));
    read_mem(fd, soldier_addr + 0x900, &lane, sizeof(lane));
    soldier->soldier_type = static_cast<int32_t>(st);
    soldier->path_id = static_cast<int32_t>(lane);
}

static void parse_monster_entity(int fd, uint64_t monster_addr, MonsterEntityBinary *monster) {
    memset(monster, 0, sizeof(MonsterEntityBinary));
    monster->address = monster_addr;
    if (monster_addr == 0) return;

    uint8_t raw[0x280];
    if (!read_mem(fd, monster_addr, raw, sizeof(raw))) return;

    monster->id = *reinterpret_cast<int32_t*>(&raw[0x0ac]);
    monster->hp = *reinterpret_cast<int32_t*>(&raw[0x0c8]);
    monster->hp_max = *reinterpret_cast<int32_t*>(&raw[0x0cc]);
    monster->is_dead = (raw[0x1d0] != 0 || monster->hp <= 0) ? 1 : 0;
    monster->camp = static_cast<uint8_t>(*reinterpret_cast<int32_t*>(&raw[0x1dc]));

    double rx = *reinterpret_cast<double*>(&raw[0x268]);
    double ry = *reinterpret_cast<double*>(&raw[0x270]);
    monster->pos_x = sanitize_coord(rx, 0.0f, COORD_MIN, COORD_MAX);
    monster->pos_y = sanitize_coord(ry, 0.0f, COORD_MIN, COORD_MAX);

    int32_t mt = 1;
    read_mem(fd, monster_addr + 0x850, &mt, sizeof(mt));
    monster->monster_type = static_cast<int32_t>(mt);
    monster->attack_range = 6.5f;
}

static void parse_tower_entity(int fd, uint64_t tower_addr, TowerEntityBinary *tower) {
    memset(tower, 0, sizeof(TowerEntityBinary));
    tower->address = tower_addr;
    if (tower_addr == 0) return;

    uint8_t raw[0x280];
    if (!read_mem(fd, tower_addr, raw, sizeof(raw))) return;

    tower->id = *reinterpret_cast<int32_t*>(&raw[0x0ac]);
    tower->hp = *reinterpret_cast<int32_t*>(&raw[0x0c8]);
    tower->hp_max = *reinterpret_cast<int32_t*>(&raw[0x0cc]);
    tower->is_dead = (raw[0x1d0] != 0 || tower->hp <= 0) ? 1 : 0;
    tower->camp = static_cast<uint8_t>(*reinterpret_cast<int32_t*>(&raw[0x1dc]));

    double rx = *reinterpret_cast<double*>(&raw[0x268]);
    double ry = *reinterpret_cast<double*>(&raw[0x270]);
    tower->pos_x = sanitize_coord(rx, 0.0f, COORD_MIN, COORD_MAX);
    tower->pos_y = sanitize_coord(ry, 0.0f, COORD_MIN, COORD_MAX);
    tower->attack_range = 8.5f;
}

// ============================================================================
// Main Memory Poll Tick (Sub-1.0ms DMA)
// ============================================================================
int memory_reader_poll_frame(FrameSnapshotBinary *out_snapshot) {
    if (!out_snapshot) return -1;
    memset(out_snapshot, 0, sizeof(FrameSnapshotBinary));

    out_snapshot->magic = VEMINS_SCHEMA_MAGIC;
    out_snapshot->version = VEMINS_SCHEMA_VERSION;
    out_snapshot->timestamp_ns = get_monotonic_ns();
    out_snapshot->frame_index = ++s_frame_counter;
    out_snapshot->pid = s_cached_pid;

    uint64_t t_start = out_snapshot->timestamp_ns;

    // 1. Liveness check
    if (!memory_reader_check_liveness()) {
        return -1; // Target process dead
    }

    int fd = s_cached_mem_fd;
    if (fd < 0) return -1;

    // 2. Validate / discover base address
    if (s_libcsharp_base == 0 || !memory_reader_validate_elf_magic(s_libcsharp_base)) {
        s_libcsharp_base = find_module_base(s_cached_pid, "libcsharp.so");
        if (s_libcsharp_base == 0 || !memory_reader_validate_elf_magic(s_libcsharp_base)) {
            return 0; // Game starting up / module not loaded yet
        }
    }
    out_snapshot->libcsharp_base = s_libcsharp_base;

    // 3. Resolve Static Root Pointer Chain:
    // libcsharp.so + 0x7680928 -> Il2CppClass + 0xb8 -> static_fields + 0x00 -> LogicBattleManager*
    uint64_t klass_ptr = read_u64(fd, s_libcsharp_base + RVA_STATIC_ROOT);
    if (klass_ptr < 0x10000) return 0;

    uint64_t static_fields = read_u64(fd, klass_ptr + 0xb8);
    if (static_fields < 0x10000) return 0;

    uint64_t mgr_ptr = read_u64(fd, static_fields + 0x00);
    if (mgr_ptr < 0x10000) return 0;

    // 4. Batch Read LogicBattleManager Block (0x220 bytes)
    uint8_t mgr_block[0x220];
    if (!read_mem(fd, mgr_ptr, mgr_block, sizeof(mgr_block))) {
        return 0;
    }

    uint64_t local_player_logic = *reinterpret_cast<uint64_t*>(&mgr_block[0x0a0]);
    uint64_t dic_player_ptr = *reinterpret_cast<uint64_t*>(&mgr_block[0x0a8]);
    uint64_t dic_monster_ptr = *reinterpret_cast<uint64_t*>(&mgr_block[0x0b0]);
    uint64_t main_tower_a = *reinterpret_cast<uint64_t*>(&mgr_block[0x0d0]);
    uint64_t main_tower_b = *reinterpret_cast<uint64_t*>(&mgr_block[0x0d8]);
    uint64_t list_soldier_ptr = *reinterpret_cast<uint64_t*>(&mgr_block[0x128]);
    int32_t state_val = *reinterpret_cast<int32_t*>(&mgr_block[0x180]);
    uint32_t frame_time = *reinterpret_cast<uint32_t*>(&mgr_block[0x19c]);
    uint64_t real_self_player = *reinterpret_cast<uint64_t*>(&mgr_block[0x200]);

    out_snapshot->battle_state = static_cast<uint8_t>(state_val);
    out_snapshot->frame_time_ms = frame_time;

    // Gate 8 Authoritative Hero Pointer Resolution
    uint64_t authoritative_self_ptr = (real_self_player >= 0x10000) ? real_self_player : local_player_logic;

    // 5. Ingest Player Dictionary (m_dicPlayerLogic @ +0x0a8)
    uint8_t hero_cnt = 0;
    if (dic_player_ptr >= 0x10000) {
        uint64_t entries_ptr = read_u64(fd, dic_player_ptr + 0x018);
        int32_t entry_count = read_i32(fd, dic_player_ptr + 0x020);
        if (entries_ptr >= 0x10000 && entry_count > 0 && entry_count <= 20) {
            // Coalesced read of 24-byte entry array
            size_t bytes_to_read = entry_count * 24;
            uint8_t entries_buf[20 * 24];
            if (read_mem(fd, entries_ptr + 0x20, entries_buf, bytes_to_read)) {
                for (int i = 0; i < entry_count && hero_cnt < MAX_HEROES; ++i) {
                    size_t offset = i * 24;
                    int32_t hash_code = *reinterpret_cast<int32_t*>(&entries_buf[offset + 0x00]);
                    uint64_t player_ptr = *reinterpret_cast<uint64_t*>(&entries_buf[offset + 0x10]);
                    // Enforce hashCode >= 0 tombstone filter
                    if (hash_code >= 0 && player_ptr >= 0x10000) {
                        parse_hero_entity(fd, player_ptr, authoritative_self_ptr, &out_snapshot->heroes[hero_cnt]);
                        parse_hero_abilities(fd, player_ptr, frame_time, &out_snapshot->heroes[hero_cnt]);
                        if (out_snapshot->heroes[hero_cnt].is_local) {
                            out_snapshot->local_camp = out_snapshot->heroes[hero_cnt].camp;
                        }
                        hero_cnt++;
                    }
                }
            }
        }
    }
    out_snapshot->hero_count = hero_cnt;

    // Enforce local player identification fallback if direct pointer comparison did not match
    bool has_local = false;
    for (uint8_t i = 0; i < hero_cnt; ++i) {
        if (out_snapshot->heroes[i].is_local) {
            has_local = true;
            out_snapshot->local_camp = out_snapshot->heroes[i].camp;
            break;
        }
    }
    if (!has_local && hero_cnt > 0) {
        int target_camp = (out_snapshot->local_camp > 0) ? out_snapshot->local_camp : 1;
        for (uint8_t i = 0; i < hero_cnt; ++i) {
            if (out_snapshot->heroes[i].camp == target_camp && !out_snapshot->heroes[i].is_dead) {
                out_snapshot->heroes[i].is_local = 1;
                out_snapshot->local_camp = out_snapshot->heroes[i].camp;
                has_local = true;
                break;
            }
        }
        if (!has_local) {
            out_snapshot->heroes[0].is_local = 1;
            out_snapshot->local_camp = out_snapshot->heroes[0].camp;
        }
    }

    // Gate Bypass: Match is active if valid hero entities exist
    out_snapshot->in_match = (hero_cnt > 0 || authoritative_self_ptr >= 0x10000) ? 1 : 0;

    // 6. Camera Continuity & EMA Anchor
    for (uint8_t i = 0; i < hero_cnt; ++i) {
        if (out_snapshot->heroes[i].is_local) {
            if (!out_snapshot->heroes[i].is_dead) {
                float target_x = out_snapshot->heroes[i].pos_x;
                float target_y = out_snapshot->heroes[i].pos_y;
                if (!s_has_last_known_pos) {
                    s_last_known_local_x = target_x;
                    s_last_known_local_y = target_y;
                    s_has_last_known_pos = true;
                } else {
                    s_last_known_local_x = s_last_known_local_x + EMA_ALPHA * (target_x - s_last_known_local_x);
                    s_last_known_local_y = s_last_known_local_y + EMA_ALPHA * (target_y - s_last_known_local_y);
                }
            }
            break;
        }
    }

    // 7. Ingest Minions (m_SoldierList @ +0x128)
    uint8_t sld_cnt = 0;
    if (list_soldier_ptr >= 0x10000) {
        uint64_t items_ptr = read_u64(fd, list_soldier_ptr + 0x010);
        int32_t count = read_i32(fd, list_soldier_ptr + 0x018);
        if (items_ptr >= 0x10000 && count > 0 && count <= 64) {
            uint64_t sld_ptrs[64];
            size_t bytes_to_read = (count < 64 ? count : 64) * sizeof(uint64_t);
            if (read_mem(fd, items_ptr + 0x20, sld_ptrs, bytes_to_read)) {
                for (int i = 0; i < count && sld_cnt < MAX_SOLDIERS; ++i) {
                    if (sld_ptrs[i] >= 0x10000) {
                        parse_soldier_entity(fd, sld_ptrs[i], &out_snapshot->soldiers[sld_cnt]);
                        if (!out_snapshot->soldiers[sld_cnt].is_dead) {
                            sld_cnt++;
                        }
                    }
                }
            }
        }
    }
    out_snapshot->soldier_count = sld_cnt;

    // 8. Ingest Jungle Monsters (m_dicMonsterLogic @ +0x0b0)
    uint8_t mon_cnt = 0;
    if (dic_monster_ptr >= 0x10000) {
        uint64_t entries_ptr = read_u64(fd, dic_monster_ptr + 0x018);
        int32_t count = read_i32(fd, dic_monster_ptr + 0x020);
        if (entries_ptr >= 0x10000 && count > 0 && count <= 32) {
            uint8_t entries_buf[32 * 24];
            size_t bytes_to_read = count * 24;
            if (read_mem(fd, entries_ptr + 0x20, entries_buf, bytes_to_read)) {
                for (int i = 0; i < count && mon_cnt < MAX_MONSTERS; ++i) {
                    size_t offset = i * 24;
                    int32_t hash_code = *reinterpret_cast<int32_t*>(&entries_buf[offset + 0x00]);
                    uint64_t mon_ptr = *reinterpret_cast<uint64_t*>(&entries_buf[offset + 0x10]);
                    if (hash_code >= 0 && mon_ptr >= 0x10000) {
                        parse_monster_entity(fd, mon_ptr, &out_snapshot->monsters[mon_cnt]);
                        if (!out_snapshot->monsters[mon_cnt].is_dead &&
                            (fabsf(out_snapshot->monsters[mon_cnt].pos_x) > 0.1f ||
                             fabsf(out_snapshot->monsters[mon_cnt].pos_y) > 0.1f)) {
                            mon_cnt++;
                        }
                    }
                }
            }
        }
    }
    out_snapshot->monster_count = mon_cnt;

    // 9. Ingest Defensive Towers & Nexus Crystals
    uint8_t twr_cnt = 0;
    if (main_tower_a >= 0x10000 && twr_cnt < MAX_TOWERS) {
        parse_tower_entity(fd, main_tower_a, &out_snapshot->towers[twr_cnt]);
        twr_cnt++;
    }
    if (main_tower_b >= 0x10000 && twr_cnt < MAX_TOWERS) {
        parse_tower_entity(fd, main_tower_b, &out_snapshot->towers[twr_cnt]);
        twr_cnt++;
    }
    out_snapshot->tower_count = twr_cnt;

    // 10. Record Sub-1.0ms DMA Latency & Frame Rate
    uint64_t t_end = get_monotonic_ns();
    float latency = static_cast<float>(t_end - t_start) / 1000000.0f; // ms
    out_snapshot->read_latency_ms = latency;
    s_last_latency_ms = latency;

    if (s_last_frame_time_ns > 0) {
        uint64_t dt_ns = t_end - s_last_frame_time_ns;
        if (dt_ns > 0) {
            float instant_fps = 1000000000.0f / static_cast<float>(dt_ns);
            s_current_fps = (s_current_fps == 0.0f) ? instant_fps : (0.9f * s_current_fps + 0.1f * instant_fps);
        }
    }
    s_last_frame_time_ns = t_end;

    return 1; // Success
}

void memory_reader_get_stats(float *out_fps, float *out_latency_ms,
                             int *out_heroes, int *out_soldiers, int *out_monsters) {
    (void)out_heroes;
    (void)out_soldiers;
    (void)out_monsters;
    if (out_fps) *out_fps = s_current_fps;
    if (out_latency_ms) *out_latency_ms = s_last_latency_ms;
}
