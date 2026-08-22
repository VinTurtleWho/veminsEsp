/*
 * VEMINS Daemon - Pure Memory & Telemetry Perception Core v2.0
 *
 * Features:
 * 1. 100% Read-Only external telemetry daemon (Zero injection, Zero evdev).
 * 2. Real-time IL2CPP BattleManager traversal and game state parsing in pure C.
 * 3. Extracts local player, enemies, allies, minion waves, jungle camps, towers, and cooldowns.
 * 4. Comprehensive hero ID (1..127) and battle spell ID (20001..21100) name mapping.
 * 5. High-speed multi-client non-blocking TCP socket server on port 9999.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdarg.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/time.h>
#include <time.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <dirent.h>
#include <signal.h>
#include <math.h>

#define HOST_IP "127.0.0.1"
#define HOST_PORT 9999
#define BUFFER_SIZE 65536

#ifndef VEMINS_VERSION
#define VEMINS_VERSION "2.0.0-ESP"
#endif

#ifndef VEMINS_BUILD_HASH
#define VEMINS_BUILD_HASH "2.0-verified"
#endif

#ifndef VEMINS_BUILD_TIME
#define VEMINS_BUILD_TIME "2026-08-22 10:35:00 UTC"
#endif

// Cached process memory handle
static pid_t s_cached_pid = -1;
static int s_cached_mem_fd = -1;
static unsigned long s_liblogic_base = 0;
static unsigned long s_libcsharp_base = 0;

// --- HERO NAME REGISTRY (1..127) ---
static const char *s_hero_names[] = {
    "Unknown", // 0
    "Miya", "Balmond", "Saber", "Alice", "Nana", "Tigreal", "Alucard", "Karina", "Akai", "Franco", // 1-10
    "Bane", "Bruno", "Clint", "Rafaela", "Eudora", "Zilong", "Fanny", "Layla", "Minotaur", "Lolita", // 11-20
    "Hayabusa", "Freya", "Gord", "Natalia", "Kagura", "Chou", "Sun", "Alpha", "Ruby", "Yi Sun-shin", // 21-30
    "Moskov", "Johnson", "Cyclops", "Estes", "Hilda", "Aurora", "Lapu-Lapu", "Vexana", "Roger", "Karrie", // 31-40
    "Gatotkaca", "Harley", "Irithel", "Grock", "Argus", "Odette", "Lancelot", "Diggie", "Hylos", "Zhask", // 41-50
    "Helcurt", "Pharsa", "Lesley", "Jawhead", "Angela", "Gusion", "Valir", "Martis", "Uranus", "Hanabi", // 51-60
    "Chang'e", "Kaja", "Selena", "Aldous", "Claude", "Vale", "Leomord", "Lunox", "Hanzo", "Belerick", // 61-70
    "Kimmy", "Thamuz", "Harith", "Minsitthar", "Kadita", "Faramis", "Badang", "Khufra", "Granger", "Guinevere", // 71-80
    "Esmeralda", "Terizla", "X.Borg", "Ling", "Dyrroth", "Lylia", "Baxia", "Masha", "Wanwan", "Silvanna", // 81-90
    "Carmilla", "Cecilion", "Atlas", "Popol and Kupa", "Yu Zhong", "Luo Yi", "Benedetta", "Khaleed", "Barats", "Brody", // 91-100
    "Yve", "Mathilda", "Paquito", "Gloo", "Beatrix", "Phoveus", "Natan", "Aulus", "Aamon", "Valentina", // 101-110
    "Edith", "Floryn", "Yin", "Melissa", "Xavier", "Julian", "Fredrinn", "Joy", "Novaria", "Arlott", // 111-120
    "Ixia", "Nolan", "Cici", "Chip", "Zhuxin", "Suyou", "Lukas" // 121-127
};
static const int s_hero_names_count = sizeof(s_hero_names) / sizeof(s_hero_names[0]);

static const char *get_hero_name(int32_t hero_id) {
    if (hero_id > 0 && hero_id < s_hero_names_count) {
        return s_hero_names[hero_id];
    }
    return "Hero";
}

static const char *get_spell_name(int32_t spell_id) {
    switch (spell_id) {
        case 20001: case 20100: case 20101: case 20102: case 20103: return "Flicker";
        case 20002: case 20200: case 20201: case 20202: case 20203: return "Retribution";
        case 20003: case 20300: case 20301: return "Inspire";
        case 20004: case 20400: case 20401: return "Sprint";
        case 20005: case 20500: case 20501: return "Revitalize";
        case 20006: case 20600: case 20601: return "Aegis";
        case 20007: case 20700: case 20701: return "Petrify";
        case 20008: case 20800: case 20801: return "Purify";
        case 20009: case 20900: case 20901: return "Flameshot";
        case 20010: case 21000: case 21001: return "Vengeance";
        case 20011: case 21100: case 21101: return "Arrival";
        default:
            if ((spell_id >= 20000 && spell_id < 30000) || (spell_id >= 200000 && spell_id < 300000)) {
                return "BattleSpell";
            }
            return "Spell";
    }
}

static const char *get_monster_name(int32_t monster_id) {
    switch (monster_id) {
        case 51298: return "Lord";
        case 51312: return "Turtle";
        case 51248: return "Blue Buff";
        case 51346: return "Red Buff";
        case 51249: return "Lithowanderer";
        case 51201: return "Crab";
        default: return "Monster";
    }
}

// --- MEMORY ACCESS HELPERS ---

static void invalidate_cached_process() {
    if (s_cached_mem_fd >= 0) {
        close(s_cached_mem_fd);
        s_cached_mem_fd = -1;
    }
    s_cached_pid = -1;
    s_libcsharp_base = 0;
    s_liblogic_base = 0;
}

static int get_cached_mem_fd(pid_t pid) {
    if (pid <= 0) {
        invalidate_cached_process();
        return -1;
    }
    if (pid == s_cached_pid && s_cached_mem_fd >= 0) {
        return s_cached_mem_fd;
    }
    if (s_cached_mem_fd >= 0) {
        close(s_cached_mem_fd);
        s_cached_mem_fd = -1;
    }
    char mempath[64];
    snprintf(mempath, sizeof(mempath), "/proc/%d/mem", pid);
    int fd = open(mempath, O_RDONLY);
    if (fd >= 0) {
        s_cached_pid = pid;
        s_cached_mem_fd = fd;
    } else {
        s_cached_pid = -1;
        s_cached_mem_fd = -1;
    }
    return fd;
}

static bool read_raw(int fd, uint64_t addr, void *buf, size_t size) {
    // Support full 48-bit AArch64 user address space (0x10000000 .. 0x0000FFFFFFFFFFFF)
    if (fd < 0 || addr < 0x10000000ULL || addr >= 0x0001000000000000ULL || !buf || size == 0) return false;
    return (pread(fd, buf, size, (off_t)addr) == (ssize_t)size);
}

static uint64_t read_u64(int fd, uint64_t addr) {
    uint64_t val = 0;
    read_raw(fd, addr, &val, sizeof(val));
    return val;
}

static int32_t read_i32(int fd, uint64_t addr) {
    int32_t val = 0;
    read_raw(fd, addr, &val, sizeof(val));
    return val;
}

static double read_f64(int fd, uint64_t addr) {
    double val = 0.0;
    read_raw(fd, addr, &val, sizeof(val));
    return val;
}

static float read_f32(int fd, uint64_t addr) {
    float val = 0.0f;
    read_raw(fd, addr, &val, sizeof(val));
    return val;
}

static uint8_t read_u8(int fd, uint64_t addr) {
    uint8_t val = 0;
    read_raw(fd, addr, &val, sizeof(val));
    return val;
}

// --- BASE DISCOVERY ---

static unsigned long find_module_base(pid_t pid, const char *module_name) {
    if (pid <= 0 || !module_name) return 0;
    char mapspath[64], line[2048];
    snprintf(mapspath, sizeof(mapspath), "/proc/%d/maps", pid);
    FILE *f = fopen(mapspath, "r");
    if (!f) return 0;
    unsigned long base = 0;
    while (fgets(line, sizeof(line), f)) {
        if (strstr(line, module_name)) {
            unsigned long start = 0;
            if (sscanf(line, "%lx-", &start) == 1) {
                base = start;
                break;
            }
        }
    }
    fclose(f);
    return base;
}

static bool is_pid_alive(pid_t pid) {
    if (pid <= 0) return false;
    return (kill(pid, 0) == 0 || errno == EPERM);
}

static pid_t find_mlbb_pid() {
    // 1. Ultra-fast path: If cached PID is alive and memory descriptor is readable, avoid scanning /proc
    if (s_cached_pid > 0 && is_pid_alive(s_cached_pid)) {
        if (s_cached_mem_fd >= 0 && s_libcsharp_base > 0) {
            uint32_t elf_magic = 0;
            if (pread(s_cached_mem_fd, &elf_magic, 4, (off_t)s_libcsharp_base) == 4 && elf_magic == 0x464c457f) {
                return s_cached_pid;
            }
        }
    }

    // 2. Scan /proc
    DIR *dir = opendir("/proc");
    if (!dir) return (s_cached_pid > 0 && is_pid_alive(s_cached_pid)) ? s_cached_pid : -1;

    struct dirent *entry;
    pid_t best_pid = -1;
    pid_t exact_name_pid = -1;
    pid_t fallback_pid = -1;
    char cmdpath[64], cmdline[512];

    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_type != DT_DIR && entry->d_type != DT_UNKNOWN) continue;
        int id = atoi(entry->d_name);
        if (id <= 0) continue;

        snprintf(cmdpath, sizeof(cmdpath), "/proc/%d/cmdline", id);
        FILE *f = fopen(cmdpath, "r");
        if (f) {
            size_t n = fread(cmdline, 1, sizeof(cmdline) - 1, f);
            fclose(f);
            if (n > 0) {
                for (size_t i = 0; i < n; i++) {
                    if (cmdline[i] == '\0') cmdline[i] = ' ';
                }
                cmdline[n] = '\0';
                if (strstr(cmdline, "com.mobile.legends")) {
                    bool is_auxiliary = (strstr(cmdline, ":") != NULL);

                    unsigned long csharp = find_module_base(id, "libcsharp.so");
                    unsigned long logic = find_module_base(id, "liblogic.so");
                    if (csharp > 0 || logic > 0) {
                        best_pid = id;
                        s_libcsharp_base = csharp;
                        s_liblogic_base = logic;
                        break;
                    }

                    if (!is_auxiliary && exact_name_pid < 0) {
                        exact_name_pid = id;
                    }
                    if (fallback_pid < 0) {
                        fallback_pid = id;
                    }
                }
            }
        }
    }
    closedir(dir);

    pid_t target_pid = (best_pid > 0) ? best_pid : ((exact_name_pid > 0) ? exact_name_pid : fallback_pid);

    if (target_pid > 0) {
        if (target_pid != s_cached_pid) {
            if (s_cached_mem_fd >= 0) {
                close(s_cached_mem_fd);
                s_cached_mem_fd = -1;
            }
            s_cached_pid = target_pid;
            if (!s_libcsharp_base) s_libcsharp_base = find_module_base(target_pid, "libcsharp.so");
            if (!s_liblogic_base) s_liblogic_base = find_module_base(target_pid, "liblogic.so");
        }
        return target_pid;
    }

    invalidate_cached_process();
    return -1;
}

/// --- DYNAMIC STRING BUFFER IMPLEMENTATION ---

typedef struct {
    char *data;
    size_t len;
    size_t cap;
} json_buffer_t;

static void json_buf_init(json_buffer_t *buf, size_t initial_cap) {
    if (!buf) return;
    if (initial_cap == 0) initial_cap = 1024;
    buf->data = (char *)malloc(initial_cap);
    if (buf->data) {
        buf->data[0] = '\0';
        buf->len = 0;
        buf->cap = initial_cap;
    } else {
        buf->len = 0;
        buf->cap = 0;
    }
}

static bool json_buf_ensure_capacity(json_buffer_t *buf, size_t needed) {
    if (!buf) return false;
    if (buf->len + needed + 1 <= buf->cap) {
        return true;
    }
    size_t new_cap = (buf->cap > 0) ? buf->cap * 2 : 1024;
    while (new_cap < buf->len + needed + 1) {
        new_cap *= 2;
    }
    char *new_data = (char *)realloc(buf->data, new_cap);
    if (!new_data) return false;
    buf->data = new_data;
    buf->cap = new_cap;
    return true;
}

static void json_buf_append_str(json_buffer_t *buf, const char *str) {
    if (!buf || !str) return;
    size_t slen = strlen(str);
    if (slen == 0) return;
    if (!json_buf_ensure_capacity(buf, slen)) return;
    memcpy(buf->data + buf->len, str, slen);
    buf->len += slen;
    buf->data[buf->len] = '\0';
}

static void json_buf_append_printf(json_buffer_t *buf, const char *fmt, ...) {
    if (!buf || !fmt) return;
    va_list args, args_copy;
    va_start(args, fmt);
    va_copy(args_copy, args);
    int needed = vsnprintf(NULL, 0, fmt, args);
    va_end(args);
    if (needed > 0) {
        if (json_buf_ensure_capacity(buf, (size_t)needed)) {
            vsnprintf(buf->data + buf->len, (size_t)needed + 1, fmt, args_copy);
            buf->len += (size_t)needed;
            buf->data[buf->len] = '\0';
        }
    }
    va_end(args_copy);
}

static void json_buf_free(json_buffer_t *buf) {
    if (!buf) return;
    if (buf->data) {
        free(buf->data);
        buf->data = NULL;
    }
    buf->len = 0;
    buf->cap = 0;
}

// Strict isfinite validation helper
static inline double safe_float(double v, double fallback, double min, double max) {
    if (!isfinite(v) || isnan(v)) {
        return fallback;
    }
    if (v < min) return min;
    if (v > max) return max;
    return v;
}

// --- IL2CPP ABILITIES & COOLDOWNS PARSER ---

struct AbilitySlotInfo {
    int32_t spell_id;
    int32_t slot;
    int32_t rem_ms;
    int32_t max_ms;
    uint8_t is_cd;
    char name[32];
};

struct HeroAbilitiesInfo {
    float skill1_rem_s;
    float skill1_max_s;
    bool skill1_ready;

    float skill2_rem_s;
    float skill2_max_s;
    bool skill2_ready;

    float ult_rem_s;
    float ult_max_s;
    bool ult_ready;

    int32_t battle_spell_id;
    char battle_spell_name[32];
    float battle_spell_rem_s;
    float battle_spell_max_s;
    bool battle_spell_ready;

    int ability_count;
    struct AbilitySlotInfo abilities[16];
};

static void parse_hero_abilities(int fd, uint64_t hero_addr, int32_t hero_id, struct HeroAbilitiesInfo *out_ab, json_buffer_t *buf) {
    if (out_ab) {
        memset(out_ab, 0, sizeof(*out_ab));
        out_ab->skill1_ready = true;
        out_ab->skill2_ready = true;
        out_ab->ult_ready = true;
        out_ab->battle_spell_ready = true;
        strncpy(out_ab->battle_spell_name, "None", sizeof(out_ab->battle_spell_name) - 1);
    }

    if (buf) {
        json_buf_append_str(buf, "[");
    }

    if (!hero_addr) {
        if (buf) json_buf_append_str(buf, "]");
        return;
    }

    uint64_t skill_comp = read_u64(fd, hero_addr + 0x4e0);
    if (!skill_comp) {
        if (buf) json_buf_append_str(buf, "]");
        return;
    }

    uint64_t cd_comp = read_u64(fd, skill_comp + 0x0a8);
    if (!cd_comp) {
        if (buf) json_buf_append_str(buf, "]");
        return;
    }

    uint64_t dict_ptr = read_u64(fd, cd_comp + 0x018);
    if (!dict_ptr) {
        if (buf) json_buf_append_str(buf, "]");
        return;
    }

    uint64_t entries_ptr = read_u64(fd, dict_ptr + 0x018);
    int32_t count = read_i32(fd, dict_ptr + 0x020);
    if (!entries_ptr || count <= 0 || count > 64) {
        if (buf) json_buf_append_str(buf, "]");
        return;
    }

    int auto_slot = 1;
    int emitted = 0;
    for (int i = 0; i < count; i++) {
        uint64_t entry_addr = entries_ptr + 0x20 + (i * 24);
        uint64_t cd_data_ptr = read_u64(fd, entry_addr + 0x10);
        if (!cd_data_ptr) continue;

        int32_t spell_id = read_i32(fd, cd_data_ptr + 0x10);
        int32_t rem_ms = read_i32(fd, cd_data_ptr + 0x14);
        int32_t max_ms = read_i32(fd, cd_data_ptr + 0x18);
        uint8_t is_cd = read_u8(fd, cd_data_ptr + 0x20);

        if (spell_id <= 0) continue;

        float rem_s = (float)safe_float((double)rem_ms / 1000.0, 0.0, 0.0, 600.0);
        float max_s = (float)safe_float((double)max_ms / 1000.0, 0.0, 0.0, 600.0);
        bool on_cd = (is_cd != 0 && rem_ms > 0);

        int slot = auto_slot;
        int expected_s1 = hero_id * 100 + 10;
        int expected_s2 = hero_id * 100 + 20;
        int expected_s3 = hero_id * 100 + 30;
        int expected_s4 = hero_id * 100 + 40;

        if (spell_id == expected_s1) {
            slot = 1;
        } else if (spell_id == expected_s2) {
            slot = 2;
        } else if (spell_id == expected_s3 || spell_id == expected_s4) {
            slot = 3;
        } else if ((spell_id >= 20000 && spell_id < 30000) || (spell_id >= 200000 && spell_id < 300000)) {
            slot = 5;
        }

        if (out_ab) {
            if (slot == 1 || spell_id == expected_s1) {
                out_ab->skill1_rem_s = rem_s;
                out_ab->skill1_max_s = max_s;
                out_ab->skill1_ready = !on_cd;
            } else if (slot == 2 || spell_id == expected_s2) {
                out_ab->skill2_rem_s = rem_s;
                out_ab->skill2_max_s = max_s;
                out_ab->skill2_ready = !on_cd;
            } else if (slot == 3 || slot == 4 || spell_id == expected_s3 || spell_id == expected_s4) {
                out_ab->ult_rem_s = rem_s;
                out_ab->ult_max_s = max_s;
                out_ab->ult_ready = !on_cd;
            }

            if (slot == 5 || (spell_id >= 20000 && spell_id < 30000) || (spell_id >= 200000 && spell_id < 300000)) {
                out_ab->battle_spell_id = spell_id;
                out_ab->battle_spell_rem_s = rem_s;
                out_ab->battle_spell_max_s = max_s;
                out_ab->battle_spell_ready = !on_cd;
                strncpy(out_ab->battle_spell_name, get_spell_name(spell_id), sizeof(out_ab->battle_spell_name) - 1);
            }

            if (out_ab->ability_count < 16) {
                struct AbilitySlotInfo *item = &out_ab->abilities[out_ab->ability_count++];
                item->spell_id = spell_id;
                item->slot = slot;
                item->rem_ms = rem_ms;
                item->max_ms = max_ms;
                item->is_cd = is_cd;
                strncpy(item->name, (slot == 5) ? out_ab->battle_spell_name : get_spell_name(spell_id), sizeof(item->name) - 1);
            }
        }

        if (buf) {
            if (emitted > 0) json_buf_append_str(buf, ",");
            json_buf_append_printf(buf,
                "{\"spell_id\":%d,\"slot\":%d,\"remaining_ms\":%d,\"remaining_cd_ms\":%d,\"max_ms\":%d,\"max_cd_ms\":%d,\"is_cooling_down\":%s}",
                spell_id, slot, rem_ms, rem_ms, max_ms, max_ms, on_cd ? "true" : "false");
            emitted++;
        }

        auto_slot++;
    }

    if (buf) {
        json_buf_append_str(buf, "]");
    }
}

// --- HERO JSON FORMATTER ---

static void format_hero_json(int fd, uint64_t hero_addr, json_buffer_t *buf) {
    if (!buf) return;
    if (!hero_addr) {
        json_buf_append_str(buf, "null");
        return;
    }

    int32_t hero_id = read_i32(fd, hero_addr + 0x0ac);
    int32_t level = read_i32(fd, hero_addr + 0x0b4);
    int32_t hp = read_i32(fd, hero_addr + 0x0c8);
    int32_t hp_max = read_i32(fd, hero_addr + 0x0cc);
    int32_t mp = read_i32(fd, hero_addr + 0x108);
    int32_t mp_max = read_i32(fd, hero_addr + 0x10c);
    int32_t shield = read_i32(fd, hero_addr + 0x0e4);
    int32_t magic_shield = read_i32(fd, hero_addr + 0x0f0);
    uint8_t is_dead_flag = read_u8(fd, hero_addr + 0x1d0);
    int32_t camp = read_i32(fd, hero_addr + 0x1dc);
    double pos_x = safe_float(read_f64(fd, hero_addr + 0x268), 0.0, -1000.0, 1000.0);
    double pos_y = safe_float(read_f64(fd, hero_addr + 0x270), 0.0, -1000.0, 1000.0);
    double facing_x = safe_float(read_f64(fd, hero_addr + 0x298), 0.0, -1.0, 1.0);
    double facing_y = safe_float(read_f64(fd, hero_addr + 0x298 + 8), 0.0, -1.0, 1.0);
    double move_dir_x = safe_float(read_f64(fd, hero_addr + 0x288), facing_x, -1.0, 1.0);
    double move_dir_y = safe_float(read_f64(fd, hero_addr + 0x290), facing_y, -1.0, 1.0);
    double run_speed = safe_float(read_f64(fd, hero_addr + 0x750), 0.0, 0.0, 2000.0);
    double atk_speed = safe_float(read_f64(fd, hero_addr + 0x758), 0.0, 0.0, 50.0);
    int32_t gold = read_i32(fd, hero_addr + 0x858);

    bool is_alive = (is_dead_flag == 0 && hp > 0);
    const char *h_name = get_hero_name(hero_id);

    struct HeroAbilitiesInfo ab;
    json_buffer_t ab_buf;
    json_buf_init(&ab_buf, 512);
    parse_hero_abilities(fd, hero_addr, hero_id, &ab, &ab_buf);

    double s1_cd = safe_float(ab.skill1_rem_s, 0.0, 0.0, 600.0);
    double s1_max = safe_float(ab.skill1_max_s, 0.0, 0.0, 600.0);
    double s2_cd = safe_float(ab.skill2_rem_s, 0.0, 0.0, 600.0);
    double s2_max = safe_float(ab.skill2_max_s, 0.0, 0.0, 600.0);
    double ult_cd = safe_float(ab.ult_rem_s, 0.0, 0.0, 600.0);
    double ult_max = safe_float(ab.ult_max_s, 0.0, 0.0, 600.0);
    double spell_cd = safe_float(ab.battle_spell_rem_s, 0.0, 0.0, 600.0);
    double spell_max = safe_float(ab.battle_spell_max_s, 0.0, 0.0, 600.0);

    json_buf_append_printf(buf,
        "{\"address\":\"0x%lx\",\"camp\":%d,\"team\":%d,\"hero_id\":%d,\"id\":%d,\"name\":\"%s\","
        "\"hp\":%d,\"max_hp\":%d,\"hp_max\":%d,\"mp\":%d,\"mp_max\":%d,\"shield\":%d,\"magic_shield\":%d,\"level\":%d,"
        "\"pos_x\":%.2f,\"pos_y\":%.2f,\"pos_z\":0.0,\"facing_x\":%.2f,\"facing_y\":%.2f,\"move_dir_x\":%.2f,\"move_dir_y\":%.2f,"
        "\"run_speed\":%.2f,\"attack_speed\":%.2f,\"gold\":%d,\"is_alive\":%s,\"is_dead\":%s,"
        "\"skill1_cd\":%.1f,\"skill1_max\":%.1f,\"skill2_cd\":%.1f,\"skill2_max\":%.1f,"
        "\"ult_cd\":%.1f,\"ult_max_cd\":%.1f,\"spell_id\":%d,\"spell_name\":\"%s\",\"spell_cd\":%.1f,\"spell_max_cd\":%.1f,"
        "\"abilities\":%s}",
        (unsigned long)hero_addr, camp, camp, hero_id, hero_id, h_name,
        hp, hp_max, hp_max, mp, mp_max, shield, magic_shield, level,
        pos_x, pos_y, facing_x, facing_y, move_dir_x, move_dir_y,
        run_speed, atk_speed, gold, is_alive ? "true" : "false", (!is_alive) ? "true" : "false",
        s1_cd, s1_max, s2_cd, s2_max,
        ult_cd, ult_max, ab.battle_spell_id, ab.battle_spell_name, spell_cd, spell_max,
        ab_buf.data ? ab_buf.data : "[]");

    json_buf_free(&ab_buf);
}

// --- ENTITY PARSERS ---

static void parse_soldiers(int fd, uint64_t mgr_addr, int local_camp, json_buffer_t *buf) {
    if (!buf) return;
    json_buf_append_str(buf, "[");
    if (!mgr_addr) {
        json_buf_append_str(buf, "]");
        return;
    }

    int soldier_count = 0;
    uint64_t soldier_list = read_u64(fd, mgr_addr + 0x128);
    if (soldier_list) {
        uint64_t items = read_u64(fd, soldier_list + 0x010);
        int32_t count = read_i32(fd, soldier_list + 0x018);
        if (items && count > 0 && count <= 64) {
            for (int i = 0; i < count; i++) {
                uint64_t s_ptr = read_u64(fd, items + 0x20 + (i * 8));
                if (s_ptr) {
                    int32_t s_id = read_i32(fd, s_ptr + 0x0ac);
                    int32_t s_hp = read_i32(fd, s_ptr + 0x0c8);
                    int32_t s_hp_max = read_i32(fd, s_ptr + 0x0cc);
                    uint8_t s_dead = read_u8(fd, s_ptr + 0x1d0);
                    if (s_dead == 0 && s_hp > 0) {
                        int32_t s_camp = read_i32(fd, s_ptr + 0x1dc);
                        double s_x = safe_float(read_f64(fd, s_ptr + 0x268), 0.0, -1000.0, 1000.0);
                        double s_y = safe_float(read_f64(fd, s_ptr + 0x270), 0.0, -1000.0, 1000.0);
                        int team = (s_camp == local_camp) ? 1 : 2;
                        int s_sid = (s_id > 0) ? s_id : i;

                        if (soldier_count > 0) json_buf_append_str(buf, ",");
                        json_buf_append_printf(buf,
                            "{\"address\":\"0x%lx\",\"camp\":%d,\"soldier_id\":%d,\"team\":%d,\"id\":%d,"
                            "\"hp\":%d,\"max_hp\":%d,\"hp_max\":%d,\"pos_x\":%.2f,\"pos_y\":%.2f,\"pos_z\":0.0}",
                            (unsigned long)s_ptr, s_camp, s_sid, team, s_sid,
                            s_hp, (s_hp_max > 0 ? s_hp_max : s_hp), (s_hp_max > 0 ? s_hp_max : s_hp),
                            s_x, s_y);
                        soldier_count++;
                    }
                }
            }
        }
    }
    json_buf_append_str(buf, "]");
}

static void parse_monsters(int fd, uint64_t mgr_addr, json_buffer_t *buf) {
    if (!buf) return;
    json_buf_append_str(buf, "[");
    if (!mgr_addr) {
        json_buf_append_str(buf, "]");
        return;
    }

    int monster_count = 0;
    uint64_t monster_dict = read_u64(fd, mgr_addr + 0x0b0);
    if (monster_dict) {
        uint64_t entries = read_u64(fd, monster_dict + 0x018);
        int32_t count = read_i32(fd, monster_dict + 0x020);
        if (entries && count > 0 && count <= 64) {
            for (int i = 0; i < count; i++) {
                uint64_t entry_addr = entries + 0x20 + (i * 24);
                uint64_t m_ptr = read_u64(fd, entry_addr + 0x10);
                if (m_ptr) {
                    int32_t m_id = read_i32(fd, m_ptr + 0x0ac);
                    int32_t m_hp = read_i32(fd, m_ptr + 0x0c8);
                    int32_t m_hp_max = read_i32(fd, m_ptr + 0x0cc);
                    uint8_t m_dead = read_u8(fd, m_ptr + 0x1d0);
                    int32_t m_camp = read_i32(fd, m_ptr + 0x1dc);
                    double m_x = safe_float(read_f64(fd, m_ptr + 0x268), 0.0, -1000.0, 1000.0);
                    double m_y = safe_float(read_f64(fd, m_ptr + 0x270), 0.0, -1000.0, 1000.0);

                    if (m_dead == 0 && m_hp > 0 && (fabs(m_x) > 0.1 || fabs(m_y) > 0.1)) {
                        const char *m_name = get_monster_name(m_id);
                        if (monster_count > 0) json_buf_append_str(buf, ",");
                        json_buf_append_printf(buf,
                            "{\"address\":\"0x%lx\",\"id\":%d,\"monster_id\":%d,\"camp\":%d,\"name\":\"%s\","
                            "\"hp\":%d,\"max_hp\":%d,\"hp_max\":%d,\"pos_x\":%.2f,\"pos_y\":%.2f,\"pos_z\":0.0}",
                            (unsigned long)m_ptr, m_id, m_id, m_camp, m_name,
                            m_hp, (m_hp_max > 0 ? m_hp_max : m_hp), (m_hp_max > 0 ? m_hp_max : m_hp),
                            m_x, m_y);
                        monster_count++;
                    }
                }
            }
        }
    }
    json_buf_append_str(buf, "]");
}

static void parse_towers(int fd, uint64_t mgr_addr, int local_camp, json_buffer_t *buf) {
    if (!buf) return;
    json_buf_append_str(buf, "[");
    if (!mgr_addr) {
        json_buf_append_str(buf, "]");
        return;
    }

    int tower_count = 0;

    // 1. Main Towers (+0xd0, +0xd8)
    uint64_t main_towers[2] = {
        read_u64(fd, mgr_addr + 0xd0), // Camp A Main Tower
        read_u64(fd, mgr_addr + 0xd8)  // Camp B Main Tower
    };
    for (int t = 0; t < 2; t++) {
        uint64_t t_ptr = main_towers[t];
        if (t_ptr) {
            int32_t t_id = read_i32(fd, t_ptr + 0x0ac);
            int32_t t_hp = read_i32(fd, t_ptr + 0x0c8);
            int32_t t_hp_max = read_i32(fd, t_ptr + 0x0cc);
            int32_t t_camp = read_i32(fd, t_ptr + 0x1dc);
            uint8_t t_dead = read_u8(fd, t_ptr + 0x1d0);
            double t_x = safe_float(read_f64(fd, t_ptr + 0x268), 0.0, -1000.0, 1000.0);
            double t_y = safe_float(read_f64(fd, t_ptr + 0x270), 0.0, -1000.0, 1000.0);
            float atk_range_raw = read_f32(fd, t_ptr + 0x930);
            double atk_range = safe_float((double)atk_range_raw, 8.5, 0.0, 100.0);

            if (t_dead == 0 && t_hp > 0) {
                int team = (t_camp == local_camp) ? 1 : 2;
                if (tower_count > 0) json_buf_append_str(buf, ",");
                json_buf_append_printf(buf,
                    "{\"address\":\"0x%lx\",\"camp\":%d,\"tower_id\":%d,\"team\":%d,\"id\":%d,"
                    "\"hp\":%d,\"max_hp\":%d,\"hp_max\":%d,\"pos_x\":%.2f,\"pos_y\":%.2f,\"pos_z\":0.0,\"attack_range\":%.2f}",
                    (unsigned long)t_ptr, t_camp, t_id, team, t_id,
                    t_hp, (t_hp_max > 0 ? t_hp_max : 7900), (t_hp_max > 0 ? t_hp_max : 7900),
                    t_x, t_y, atk_range > 0.0 ? atk_range : 8.5);
                tower_count++;
            }
        }
    }

    // 2. Lane Towers (+0xe0, +0xe8)
    uint64_t lane_lists[2] = {
        read_u64(fd, mgr_addr + 0xe0), // Camp A List
        read_u64(fd, mgr_addr + 0xe8)  // Camp B List
    };
    for (int l = 0; l < 2; l++) {
        uint64_t t_list = lane_lists[l];
        if (t_list) {
            uint64_t items = read_u64(fd, t_list + 0x010);
            int32_t count = read_i32(fd, t_list + 0x018);
            if (items && count > 0 && count <= 32) {
                for (int i = 0; i < count; i++) {
                    uint64_t t_ptr = read_u64(fd, items + 0x20 + (i * 8));
                    if (t_ptr) {
                        int32_t t_id = read_i32(fd, t_ptr + 0x0ac);
                        int32_t t_hp = read_i32(fd, t_ptr + 0x0c8);
                        int32_t t_hp_max = read_i32(fd, t_ptr + 0x0cc);
                        int32_t t_camp = read_i32(fd, t_ptr + 0x1dc);
                        uint8_t t_dead = read_u8(fd, t_ptr + 0x1d0);
                        double t_x = safe_float(read_f64(fd, t_ptr + 0x268), 0.0, -1000.0, 1000.0);
                        double t_y = safe_float(read_f64(fd, t_ptr + 0x270), 0.0, -1000.0, 1000.0);
                        float atk_range_raw = read_f32(fd, t_ptr + 0x930);
                        double atk_range = safe_float((double)atk_range_raw, 8.5, 0.0, 100.0);

                        if (t_dead == 0 && t_hp > 0) {
                            int team = (t_camp == local_camp) ? 1 : 2;
                            if (tower_count > 0) json_buf_append_str(buf, ",");
                            json_buf_append_printf(buf,
                                "{\"address\":\"0x%lx\",\"camp\":%d,\"tower_id\":%d,\"team\":%d,\"id\":%d,"
                                "\"hp\":%d,\"max_hp\":%d,\"hp_max\":%d,\"pos_x\":%.2f,\"pos_y\":%.2f,\"pos_z\":0.0,\"attack_range\":%.2f}",
                                (unsigned long)t_ptr, t_camp, t_id, team, t_id,
                                t_hp, (t_hp_max > 0 ? t_hp_max : 5000), (t_hp_max > 0 ? t_hp_max : 5000),
                                t_x, t_y, atk_range > 0.0 ? atk_range : 8.5);
                            tower_count++;
                        }
                    }
                }
            }
        }
    }
    json_buf_append_str(buf, "]");
}

// --- SNAPSHOT GENERATOR ---

static void build_live_snapshot_json(json_buffer_t *buf) {
    if (!buf) return;
    pid_t pid = find_mlbb_pid();
    if (pid <= 0) {
        json_buf_append_printf(buf,
                 "{\"agent\":\"vemins_daemon\",\"version\":\"%s\",\"build_hash\":\"%s\",\"status\":\"waiting\",\"msg\":\"mlbb_not_running\",\"in_match\":false,\"enemies\":[],\"allies\":[],\"soldiers\":[],\"minions\":[],\"monsters\":[],\"towers\":[]}\n",
                 VEMINS_VERSION, VEMINS_BUILD_HASH);
        return;
    }

    if (!s_libcsharp_base) {
        s_libcsharp_base = find_module_base(pid, "libcsharp.so");
    }
    if (!s_liblogic_base) {
        s_liblogic_base = find_module_base(pid, "liblogic.so");
    }

    int mem_fd = get_cached_mem_fd(pid);
    if (mem_fd < 0 || !s_libcsharp_base) {
        json_buf_append_printf(buf,
                 "{\"agent\":\"vemins_daemon\",\"version\":\"%s\",\"build_hash\":\"%s\",\"status\":\"waiting\",\"pid\":%d,\"liblogic_base\":\"0x%lx\",\"libcsharp_base\":\"0x%lx\",\"in_match\":false,\"enemies\":[],\"allies\":[],\"soldiers\":[],\"minions\":[],\"monsters\":[],\"towers\":[]}\n",
                 VEMINS_VERSION, VEMINS_BUILD_HASH, pid, s_liblogic_base, s_libcsharp_base);
        return;
    }

    // BattleManager instance
    uint64_t class_ptr = read_u64(mem_fd, s_libcsharp_base + 0x7680928);
    if (!class_ptr) {
        json_buf_append_printf(buf,
                 "{\"agent\":\"vemins_daemon\",\"version\":\"%s\",\"build_hash\":\"%s\",\"status\":\"ok\",\"pid\":%d,\"liblogic_base\":\"0x%lx\",\"libcsharp_base\":\"0x%lx\",\"in_match\":false,\"enemies\":[],\"allies\":[],\"soldiers\":[],\"minions\":[],\"monsters\":[],\"towers\":[]}\n",
                 VEMINS_VERSION, VEMINS_BUILD_HASH, pid, s_liblogic_base, s_libcsharp_base);
        return;
    }
    uint64_t static_fields = read_u64(mem_fd, class_ptr + 0xb8);
    if (!static_fields) {
        json_buf_append_printf(buf,
                 "{\"agent\":\"vemins_daemon\",\"version\":\"%s\",\"build_hash\":\"%s\",\"status\":\"ok\",\"pid\":%d,\"liblogic_base\":\"0x%lx\",\"libcsharp_base\":\"0x%lx\",\"in_match\":false,\"enemies\":[],\"allies\":[],\"soldiers\":[],\"minions\":[],\"monsters\":[],\"towers\":[]}\n",
                 VEMINS_VERSION, VEMINS_BUILD_HASH, pid, s_liblogic_base, s_libcsharp_base);
        return;
    }
    uint64_t mgr_addr = read_u64(mem_fd, static_fields + 0x00);
    if (!mgr_addr) {
        json_buf_append_printf(buf,
                 "{\"agent\":\"vemins_daemon\",\"version\":\"%s\",\"build_hash\":\"%s\",\"status\":\"ok\",\"pid\":%d,\"liblogic_base\":\"0x%lx\",\"libcsharp_base\":\"0x%lx\",\"in_match\":false,\"enemies\":[],\"allies\":[],\"soldiers\":[],\"minions\":[],\"monsters\":[],\"towers\":[]}\n",
                 VEMINS_VERSION, VEMINS_BUILD_HASH, pid, s_liblogic_base, s_libcsharp_base);
        return;
    }

    int32_t battle_state = read_i32(mem_fd, mgr_addr + 0x180);
    uint32_t frame_time_ms = (uint32_t)read_i32(mem_fd, mgr_addr + 0x19c);
    bool in_match = (battle_state >= 2 && battle_state <= 6);

    // in_match state gating: if !in_match, serialize an empty snapshot immediately without reading deallocated memory
    if (!in_match) {
        struct timespec ts;
        clock_gettime(CLOCK_REALTIME, &ts);
        uint64_t timestamp_ns = ((uint64_t)ts.tv_sec * 1000000000ULL) + (uint64_t)ts.tv_nsec;

        json_buf_append_printf(buf,
                 "{\"agent\":\"vemins_daemon\",\"version\":\"%s\",\"build_hash\":\"%s\",\"status\":\"ok\","
                 "\"pid\":%d,\"liblogic_base\":\"0x%lx\",\"libcsharp_base\":\"0x%lx\","
                 "\"timestamp\":%ld,\"timestamp_ns\":%llu,\"in_match\":false,\"battle_state\":%d,\"frame_time_ms\":%u,"
                 "\"local_player\":null,\"enemies\":[],\"allies\":[],\"soldiers\":[],\"minions\":[],\"monsters\":[],\"towers\":[]}\n",
                 VEMINS_VERSION, VEMINS_BUILD_HASH,
                 pid, s_liblogic_base, s_libcsharp_base,
                 (long)time(NULL), (unsigned long long)timestamp_ns,
                 battle_state, frame_time_ms);
        return;
    }

    uint64_t self_ptr = read_u64(mem_fd, mgr_addr + 0x200);
    if (!self_ptr) self_ptr = read_u64(mem_fd, mgr_addr + 0x0a0);

    json_buffer_t local_buf;
    json_buf_init(&local_buf, 1024);
    int local_camp = 1;
    if (self_ptr) {
        format_hero_json(mem_fd, self_ptr, &local_buf);
        local_camp = read_i32(mem_fd, self_ptr + 0x1dc);
        if (local_camp <= 0) local_camp = 1;
    } else {
        json_buf_append_str(&local_buf, "null");
    }

    // Hero Players Dict (+0x0a8)
    json_buffer_t enemies_buf, allies_buf;
    json_buf_init(&enemies_buf, 2048);
    json_buf_init(&allies_buf, 2048);
    json_buf_append_str(&enemies_buf, "[");
    json_buf_append_str(&allies_buf, "[");
    int enemy_count = 0, ally_count = 0;

    uint64_t dict_players = read_u64(mem_fd, mgr_addr + 0x0a8);
    if (dict_players) {
        uint64_t entries = read_u64(mem_fd, dict_players + 0x018);
        int32_t count = read_i32(mem_fd, dict_players + 0x020);
        if (entries && count > 0 && count <= 32) {
            for (int i = 0; i < count; i++) {
                uint64_t entry_addr = entries + 0x20 + (i * 24);
                uint64_t player_ptr = read_u64(mem_fd, entry_addr + 0x10);
                if (player_ptr && player_ptr != self_ptr) {
                    json_buffer_t h_buf;
                    json_buf_init(&h_buf, 1024);
                    format_hero_json(mem_fd, player_ptr, &h_buf);
                    int camp = read_i32(mem_fd, player_ptr + 0x1dc);

                    if (camp == local_camp) {
                        if (ally_count > 0) json_buf_append_str(&allies_buf, ",");
                        json_buf_append_str(&allies_buf, h_buf.data ? h_buf.data : "{}");
                        ally_count++;
                    } else {
                        if (enemy_count > 0) json_buf_append_str(&enemies_buf, ",");
                        json_buf_append_str(&enemies_buf, h_buf.data ? h_buf.data : "{}");
                        enemy_count++;
                    }
                    json_buf_free(&h_buf);
                }
            }
        }
    }
    json_buf_append_str(&enemies_buf, "]");
    json_buf_append_str(&allies_buf, "]");

    // Minion Wave Soldiers (+0x128)
    json_buffer_t soldiers_buf;
    json_buf_init(&soldiers_buf, 2048);
    parse_soldiers(mem_fd, mgr_addr, local_camp, &soldiers_buf);

    // Jungle Monsters (+0x0b0)
    json_buffer_t monsters_buf;
    json_buf_init(&monsters_buf, 2048);
    parse_monsters(mem_fd, mgr_addr, &monsters_buf);

    // Defensive Turrets / Towers (+0xd0, +0xd8, +0xe0, +0xe8)
    json_buffer_t towers_buf;
    json_buf_init(&towers_buf, 2048);
    parse_towers(mem_fd, mgr_addr, local_camp, &towers_buf);

    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    uint64_t timestamp_ns = ((uint64_t)ts.tv_sec * 1000000000ULL) + (uint64_t)ts.tv_nsec;

    json_buf_append_printf(buf,
             "{\"agent\":\"vemins_daemon\",\"version\":\"%s\",\"build_hash\":\"%s\",\"status\":\"ok\","
             "\"pid\":%d,\"liblogic_base\":\"0x%lx\",\"libcsharp_base\":\"0x%lx\","
             "\"timestamp\":%ld,\"timestamp_ns\":%llu,\"in_match\":%s,\"battle_state\":%d,\"frame_time_ms\":%u,"
             "\"local_player\":%s,\"enemies\":%s,\"allies\":%s,\"soldiers\":%s,\"minions\":%s,\"monsters\":%s,\"towers\":%s}\n",
             VEMINS_VERSION, VEMINS_BUILD_HASH,
             pid, s_liblogic_base, s_libcsharp_base,
             (long)time(NULL), (unsigned long long)timestamp_ns,
             in_match ? "true" : "false", battle_state, frame_time_ms,
             local_buf.data ? local_buf.data : "null",
             enemies_buf.data ? enemies_buf.data : "[]",
             allies_buf.data ? allies_buf.data : "[]",
             soldiers_buf.data ? soldiers_buf.data : "[]",
             soldiers_buf.data ? soldiers_buf.data : "[]",
             monsters_buf.data ? monsters_buf.data : "[]",
             towers_buf.data ? towers_buf.data : "[]");

    json_buf_free(&local_buf);
    json_buf_free(&enemies_buf);
    json_buf_free(&allies_buf);
    json_buf_free(&soldiers_buf);
    json_buf_free(&monsters_buf);
    json_buf_free(&towers_buf);
}

// --- SOCKET SERVER DISPATCHER ---

static void send_resp(int sock, const char *resp) {
    if (sock < 0 || !resp) return;
    send(sock, resp, strlen(resp), MSG_NOSIGNAL);
}

void process_command(int sock, const char *line) {
    if (!line || strlen(line) == 0) return;

    if (strstr(line, "GET_INFO") || strstr(line, "GET_SNAPSHOT") || strstr(line, "GET_WORLD")) {
        json_buffer_t resp_buf;
        json_buf_init(&resp_buf, 4096);
        build_live_snapshot_json(&resp_buf);
        send_resp(sock, resp_buf.data ? resp_buf.data : "{\"status\":\"error\",\"msg\":\"empty_snapshot\"}\n");
        json_buf_free(&resp_buf);
    } else if (strstr(line, "SELF_TEST")) {
        pid_t pid = find_mlbb_pid();
        int mem_fd = get_cached_mem_fd(pid);
        bool mem_ok = false;
        if (mem_fd >= 0 && s_liblogic_base > 0) {
            uint32_t magic = 0;
            if (pread(mem_fd, &magic, 4, (off_t)s_liblogic_base) == 4) {
                mem_ok = (magic == 0x464c457f); // \x7fELF
            }
        }
        char resp[256];
        snprintf(resp, sizeof(resp),
                 "{\"status\":\"ok\",\"mem_readable\":%s,\"pid\":%d,\"liblogic_base\":\"0x%lx\",\"libcsharp_base\":\"0x%lx\",\"version\":\"%s\",\"build_hash\":\"%s\"}\n",
                 mem_ok ? "true" : "false", pid, s_liblogic_base, s_libcsharp_base, VEMINS_VERSION, VEMINS_BUILD_HASH);
        send_resp(sock, resp);
    } else if (strstr(line, "READ_MEM")) {
        int pid_in = 0;
        unsigned long addr = 0;
        int size = 0;
        sscanf(line, "READ_MEM %d %lx %d", &pid_in, &addr, &size);
        if (pid_in <= 0) pid_in = find_mlbb_pid();
        int mem_fd = get_cached_mem_fd(pid_in);
        if (mem_fd >= 0) {
            if (size <= 0 || size > 65536) size = 8;
            unsigned char *mem_buf = (unsigned char *)malloc((size_t)size);
            if (mem_buf) {
                ssize_t r = pread(mem_fd, mem_buf, (size_t)size, (off_t)addr);
                if (r > 0) {
                    char *hex_str = (char *)malloc((size_t)r * 2 + 1);
                    if (hex_str) {
                        for (int i = 0; i < r; i++) {
                            snprintf(hex_str + (i * 2), 3, "%02x", mem_buf[i]);
                        }
                        hex_str[r * 2] = '\0';
                        char *resp = (char *)malloc((size_t)r * 2 + 128);
                        if (resp) {
                            snprintf(resp, (size_t)r * 2 + 128, "{\"status\":\"ok\",\"data\":\"%s\",\"bytes\":%zd}\n", hex_str, r);
                            send_resp(sock, resp);
                            free(resp);
                        }
                        free(hex_str);
                    }
                } else {
                    send_resp(sock, "{\"status\":\"error\",\"msg\":\"pread_failed\"}\n");
                }
                free(mem_buf);
            } else {
                send_resp(sock, "{\"status\":\"error\",\"msg\":\"malloc_failed\"}\n");
            }
        } else {
            send_resp(sock, "{\"status\":\"error\",\"msg\":\"cannot_open_mem\"}\n");
        }
    } else {
        // Default: Return live game snapshot
        json_buffer_t resp_buf;
        json_buf_init(&resp_buf, 4096);
        build_live_snapshot_json(&resp_buf);
        send_resp(sock, resp_buf.data ? resp_buf.data : "{\"status\":\"error\",\"msg\":\"empty_snapshot\"}\n");
        json_buf_free(&resp_buf);
    }
}

int main(int argc, char *argv[]) {
    printf("=====================================================\n");
    printf("  VEMINS ESP Telemetry Daemon v2.0 (LIVE PARSER CORE)\n");
    printf("  [High-Speed In-Memory IL2CPP Snapshot Engine]      \n");
    printf("=====================================================\n");

    signal(SIGPIPE, SIG_IGN);
    signal(SIGCHLD, SIG_IGN);

    int port = (argc > 1) ? atoi(argv[1]) : 9999;
    if (port <= 0) port = 9999;

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket failed");
        return 1;
    }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
#ifdef SO_REUSEPORT
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEPORT, &opt, sizeof(opt));
#endif

    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("bind failed");
        close(server_fd);
        return 1;
    }

    if (listen(server_fd, 10) < 0) {
        perror("listen failed");
        close(server_fd);
        return 1;
    }

    printf("[✓] VEMINS Daemon Active on Port %d (Ready for Overlay Connection)\n", port);

    while (1) {
        struct sockaddr_in client_addr;
        socklen_t addrlen = sizeof(client_addr);
        int client_fd = accept(server_fd, (struct sockaddr *)&client_addr, &addrlen);
        if (client_fd < 0) {
            if (errno == EINTR) continue;
            continue;
        }

        // Fork to handle client without blocking main listener
        pid_t child_pid = fork();
        if (child_pid < 0) {
            perror("fork failed");
            close(client_fd);
            continue;
        }

        if (child_pid == 0) {
            // Child process: close parent server socket
            close(server_fd);

            // Set socket timeouts (5 seconds) to prevent hanging if client drops
            struct timeval tv;
            tv.tv_sec = 5;
            tv.tv_usec = 0;
            setsockopt(client_fd, SOL_SOCKET, SO_RCVTIMEO, (const char *)&tv, sizeof(tv));
            setsockopt(client_fd, SOL_SOCKET, SO_SNDTIMEO, (const char *)&tv, sizeof(tv));

            // Enable TCP_NODELAY for lowest latency
            int flag = 1;
            setsockopt(client_fd, IPPROTO_TCP, TCP_NODELAY, (char *)&flag, sizeof(int));

            // Send initial handshake banner
            char banner[256];
            snprintf(banner, sizeof(banner),
                     "{\"agent\":\"vemins_daemon\",\"version\":\"%s\",\"build_hash\":\"%s\",\"build_time\":\"%s\",\"status\":\"ok\"}\n",
                     VEMINS_VERSION, VEMINS_BUILD_HASH, VEMINS_BUILD_TIME);
            send_resp(client_fd, banner);

            // Keep connection open for continuous request-response streaming
            char buffer[1024];
            while (1) {
                memset(buffer, 0, sizeof(buffer));
                ssize_t bytes_read = recv(client_fd, buffer, sizeof(buffer) - 1, 0);
                if (bytes_read <= 0) {
                    break;
                }
                buffer[bytes_read] = '\0';
                char *nl = strchr(buffer, '\n');
                if (nl) *nl = '\0';
                char *cr = strchr(buffer, '\r');
                if (cr) *cr = '\0';

                process_command(client_fd, buffer);
            }

            if (s_cached_mem_fd >= 0) {
                close(s_cached_mem_fd);
                s_cached_mem_fd = -1;
            }
            close(client_fd);
            exit(0);
        }

        // Parent process: close client socket and continue accepting
        close(client_fd);
    }

    close(server_fd);
    return 0;
}
