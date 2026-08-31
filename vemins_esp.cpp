#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <math.h>
#include <fcntl.h>
#include <time.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <vector>
#include <string>

#include "native_surface.h"
#include "gl_renderer.h"
#include "texture_manager.h"

#define DAEMON_PORT 9999

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Configuration structure
struct ESPConfig {
    float screen_w = 2400.0f;
    float screen_h = 1080.0f;
    float minimap_x = 75.0f;
    float minimap_y = 15.0f;
    float minimap_w = 320.0f;
    float minimap_h = 320.0f;
    float cam_scale_x = 38.0f;
    float cam_scale_y = 27.0f;
    float cam_hud_offset_y = 65.0f;
    float edge_margin = 45.0f;
    float max_radar_distance = 45.0f;

    bool minimap_show_enemies = true;
    bool minimap_show_allies = false;
    bool minimap_show_arrows = true;
    bool minimap_show_minions = true;
    bool minimap_show_monsters = true;
    bool screen_show_overhead_hp = true;
    bool screen_show_skill_cooldowns = true;
    bool screen_show_edge_radar = true;
} g_cfg;

static void load_config() {
    const char* paths[] = {
        "/data/local/tmp/minimap_config.json",
        "/data/local/tmp/veminsEsp/minimap_config.json",
        "/sdcard/veminsEsp/minimap_config.json",
        "/sdcard/Download/minimap_config.json",
        "./minimap_config.json",
        "/data/data/com.termux/files/home/veminsEsp/minimap_config.json"
    };

    FILE* fp = NULL;
    for (const char* p : paths) {
        fp = fopen(p, "r");
        if (fp) {
            printf("[Config] Loaded minimap configuration from: %s\n", p);
            break;
        }
    }

    if (!fp) return;

    char buf[4096] = {0};
    fread(buf, 1, sizeof(buf) - 1, fp);
    fclose(fp);

    char* p = NULL;
    if ((p = strstr(buf, "\"pos_x\":"))) sscanf(p + 8, "%f", &g_cfg.minimap_x);
    if ((p = strstr(buf, "\"pos_y\":"))) sscanf(p + 8, "%f", &g_cfg.minimap_y);
    if ((p = strstr(buf, "\"width\":"))) sscanf(p + 8, "%f", &g_cfg.minimap_w);
    if ((p = strstr(buf, "\"height\":"))) sscanf(p + 9, "%f", &g_cfg.minimap_h);
    if ((p = strstr(buf, "\"scale_x\":"))) sscanf(p + 10, "%f", &g_cfg.cam_scale_x);
    if ((p = strstr(buf, "\"scale_y\":"))) sscanf(p + 10, "%f", &g_cfg.cam_scale_y);
    if ((p = strstr(buf, "\"hud_offset_y\":"))) sscanf(p + 15, "%f", &g_cfg.cam_hud_offset_y);
    if ((p = strstr(buf, "\"edge_margin\":"))) sscanf(p + 14, "%f", &g_cfg.edge_margin);
    if ((p = strstr(buf, "\"max_radar_distance\":"))) sscanf(p + 21, "%f", &g_cfg.max_radar_distance);

    printf("[Config] Minimap Bounds: (%.1f, %.1f) [%.1fx%.1f]\n", g_cfg.minimap_x, g_cfg.minimap_y, g_cfg.minimap_w, g_cfg.minimap_h);
}

// Entity Data Structures
struct AbilityInfo {
    int spell_id;
    int slot;
    float rem_s;
    float max_s;
    bool is_cd;
};

struct HeroEntityData {
    uint64_t address;
    int hero_id;
    int level;
    int hp;
    int hp_max;
    int mp;
    int mp_max;
    int shield;
    int magic_shield;
    int camp;
    bool is_dead;
    bool is_local;
    double pos_x;
    double pos_y;
    double facing_x;
    double facing_y;
    std::vector<AbilityInfo> abilities;
    float ult_rem_s;
    bool ult_ready;
};

struct SoldierEntityData {
    int id;
    int camp;
    int hp;
    int hp_max;
    bool is_dead;
    double pos_x;
    double pos_y;
};

struct MonsterEntityData {
    int id;
    int monster_type;
    int hp;
    int hp_max;
    bool is_dead;
    double pos_x;
    double pos_y;
};

struct FrameSnapshot {
    bool in_match;
    int battle_state;
    HeroEntityData local_player;
    std::vector<HeroEntityData> allies;
    std::vector<HeroEntityData> enemies;
    std::vector<SoldierEntityData> soldiers;
    std::vector<MonsterEntityData> monsters;
};

// Memory Reader Handle
static int s_mem_fd = -1;
static pid_t s_mlbb_pid = -1;
static uint64_t s_liblogic_base = 0;
static uint64_t s_libcsharp_base = 0;
static int s_read_fail_count = 0;

static bool read_mem(uint64_t addr, void* buf, size_t size) {
    addr &= 0x0000FFFFFFFFFFFFULL;
    if (s_mem_fd < 0 || addr < 0x10000ULL || !buf || size == 0) return false;
    ssize_t n = pread(s_mem_fd, buf, size, addr);
    if (n == (ssize_t)size) {
        s_read_fail_count = 0;
        return true;
    }
    s_read_fail_count++;
    if (s_read_fail_count > 60) {
        // Target process restarted or invalidated
        if (s_mem_fd >= 0) close(s_mem_fd);
        s_mem_fd = -1;
        s_mlbb_pid = -1;
        s_libcsharp_base = 0;
        s_liblogic_base = 0;
        s_read_fail_count = 0;
    }
    return false;
}

template<typename T>
static T read_val(uint64_t addr) {
    T val = {};
    read_mem(addr, &val, sizeof(T));
    return val;
}

// Memory Parsing Engine (Locked Offsets from FIELD_MAP.md)
static bool resolve_mlbb_bases() {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return false;

    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = 300000; // 300ms timeout
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    struct sockaddr_in serv_addr = {};
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(DAEMON_PORT);
    inet_pton(AF_INET, "127.0.0.1", &serv_addr.sin_addr);

    if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
        close(sock);
        return false;
    }

    // Read Banner
    char buf[1024] = {0};
    recv(sock, buf, sizeof(buf) - 1, 0);

    // Send GET_INFO
    const char* req = "GET_INFO\n";
    send(sock, req, strlen(req), 0);

    memset(buf, 0, sizeof(buf));
    ssize_t n = recv(sock, buf, sizeof(buf) - 1, 0);
    close(sock);

    if (n > 0) {
        buf[n] = '\0';
        char* p_pid = strstr(buf, "\"pid\":");
        if (p_pid) s_mlbb_pid = atoi(p_pid + 6);

        char* p_logic = strstr(buf, "\"liblogic_base\":\"");
        if (p_logic) s_liblogic_base = strtoull(p_logic + 17, NULL, 16);

        char* p_csharp = strstr(buf, "\"libcsharp_base\":\"");
        if (p_csharp) s_libcsharp_base = strtoull(p_csharp + 18, NULL, 16);
    }

    if (s_mlbb_pid > 0 && s_libcsharp_base > 0) {
        char mempath[64];
        snprintf(mempath, sizeof(mempath), "/proc/%d/mem", s_mlbb_pid);
        if (s_mem_fd >= 0) close(s_mem_fd);
        s_mem_fd = open(mempath, O_RDONLY);
        if (s_mem_fd >= 0) {
            printf("[✓] MLBB Memory Connected: PID=%d | libcsharp=0x%lx | liblogic=0x%lx\n",
                   s_mlbb_pid, (unsigned long)s_libcsharp_base, (unsigned long)s_liblogic_base);
            return true;
        }
    }
    return false;
}

static uint64_t get_battle_manager_ptr() {
    if (!s_libcsharp_base) return 0;
    uint64_t class_ptr = read_val<uint64_t>(s_libcsharp_base + 0x7680928);
    if (!class_ptr) return 0;
    uint64_t static_fields = read_val<uint64_t>(class_ptr + 0xb8);
    if (!static_fields) return 0;
    return read_val<uint64_t>(static_fields + 0x00);
}

static void parse_hero_abilities(uint64_t hero_addr, HeroEntityData* hero) {
    if (!hero_addr || !hero) return;
    hero->ult_ready = true;
    hero->ult_rem_s = 0.0f;

    uint64_t skill_comp = read_val<uint64_t>(hero_addr + 0x4e0);
    if (!skill_comp) return;

    uint64_t cd_comp = read_val<uint64_t>(skill_comp + 0x0a8);
    if (!cd_comp) return;

    uint64_t dict_ptr = read_val<uint64_t>(cd_comp + 0x018);
    if (!dict_ptr) return;

    uint64_t entries_ptr = read_val<uint64_t>(dict_ptr + 0x018);
    int32_t count = read_val<int32_t>(dict_ptr + 0x020);
    if (!entries_ptr || count <= 0 || count > 64) return;

    // Stride 24 bytes for dictionary entries
    int slot_idx = 1;
    for (int i = 0; i < count; i++) {
        uint64_t entry_addr = entries_ptr + 0x20 + (i * 24);
        uint64_t cd_data_ptr = read_val<uint64_t>(entry_addr + 0x10);
        if (!cd_data_ptr) continue;

        int32_t spell_id = read_val<int32_t>(cd_data_ptr + 0x10);
        int32_t rem_ms = read_val<int32_t>(cd_data_ptr + 0x14);
        int32_t max_ms = read_val<int32_t>(cd_data_ptr + 0x18);
        uint8_t is_cd = read_val<uint8_t>(cd_data_ptr + 0x20);

        if (spell_id > 0) {
            AbilityInfo ab;
            ab.spell_id = spell_id;
            ab.slot = slot_idx++;
            ab.rem_s = (float)rem_ms / 1000.0f;
            ab.max_s = (float)max_ms / 1000.0f;
            ab.is_cd = (is_cd != 0 && rem_ms > 0);

            if (ab.slot == 3 || ab.slot == 4) {
                if (ab.is_cd) {
                    hero->ult_rem_s = ab.rem_s;
                    hero->ult_ready = false;
                }
            }
            hero->abilities.push_back(ab);
        }
    }
}

static HeroEntityData parse_hero(uint64_t hero_addr, bool is_local) {
    HeroEntityData h = {};
    h.address = hero_addr;
    h.is_local = is_local;
    if (!hero_addr) return h;

    h.hero_id = read_val<int32_t>(hero_addr + 0x0ac);
    h.level = read_val<int32_t>(hero_addr + 0x0b4);
    h.hp = read_val<int32_t>(hero_addr + 0x0c8);
    h.hp_max = read_val<int32_t>(hero_addr + 0x0cc);
    h.mp = read_val<int32_t>(hero_addr + 0x108);
    h.mp_max = read_val<int32_t>(hero_addr + 0x10c);
    h.shield = read_val<int32_t>(hero_addr + 0x0e4);
    h.magic_shield = read_val<int32_t>(hero_addr + 0x0f0);
    h.is_dead = (read_val<uint8_t>(hero_addr + 0x1d0) != 0 || h.hp <= 0);
    h.camp = read_val<int32_t>(hero_addr + 0x1dc);
    h.pos_x = read_val<double>(hero_addr + 0x268);
    h.pos_y = read_val<double>(hero_addr + 0x270);
    h.facing_x = read_val<double>(hero_addr + 0x298);
    h.facing_y = read_val<double>(hero_addr + 0x298 + 8);

    parse_hero_abilities(hero_addr, &h);
    return h;
}

static FrameSnapshot capture_live_snapshot() {
    FrameSnapshot snap = {};
    static time_t s_last_base_retry = 0;
    static time_t s_last_log_time = 0;
    time_t now = time(NULL);

    if (s_mem_fd < 0 || s_libcsharp_base == 0 || s_mlbb_pid <= 0) {
        if (now - s_last_base_retry >= 1) {
            s_last_base_retry = now;
            resolve_mlbb_bases();
        }
        if (s_mem_fd < 0 || s_libcsharp_base == 0) {
            if (now - s_last_log_time >= 5) {
                s_last_log_time = now;
                printf("[Status] Waiting for Mobile Legends match & daemon connection...\n");
            }
            return snap;
        }
    }

    uint64_t mgr_addr = get_battle_manager_ptr();
    if (!mgr_addr) {
        if (now - s_last_base_retry >= 2) {
            s_last_base_retry = now;
            resolve_mlbb_bases();
        }
        return snap;
    }

    snap.battle_state = read_val<int32_t>(mgr_addr + 0x180);

    // Gate 8 Authoritative Local Player (+0x200)
    uint64_t self_ptr = read_val<uint64_t>(mgr_addr + 0x200);
    if (!self_ptr) self_ptr = read_val<uint64_t>(mgr_addr + 0x0a0);
    if (self_ptr) {
        snap.local_player = parse_hero(self_ptr, true);
    }

    uint64_t dict_players = read_val<uint64_t>(mgr_addr + 0x0a8);
    int32_t player_count = dict_players ? read_val<int32_t>(dict_players + 0x020) : 0;

    snap.in_match = (self_ptr != 0) || (player_count > 0) || (snap.battle_state >= 1 && snap.battle_state <= 8);
    if (!snap.in_match) return snap;

    int local_camp = snap.local_player.camp ? snap.local_player.camp : 1;

    // 10 Hero Players Dictionary (+0x0a8)
    if (dict_players) {
        uint64_t entries = read_val<uint64_t>(dict_players + 0x018);
        int32_t count = read_val<int32_t>(dict_players + 0x020);
        if (entries && count > 0 && count <= 32) {
            for (int i = 0; i < count; i++) {
                uint64_t entry_addr = entries + 0x20 + (i * 24);
                uint64_t player_ptr = read_val<uint64_t>(entry_addr + 0x10);
                if (player_ptr && player_ptr != self_ptr) {
                    HeroEntityData h = parse_hero(player_ptr, false);
                    if (h.hero_id > 0) {
                        if (h.camp == local_camp) {
                            snap.allies.push_back(h);
                        } else {
                            snap.enemies.push_back(h);
                        }
                    }
                }
            }
        }
    }

    // Minion Wave Soldiers (+0x128)
    uint64_t soldier_list = read_val<uint64_t>(mgr_addr + 0x128);
    if (soldier_list) {
        uint64_t items = read_val<uint64_t>(soldier_list + 0x010);
        int32_t count = read_val<int32_t>(soldier_list + 0x018);
        if (items && count > 0 && count <= 64) {
            for (int i = 0; i < count; i++) {
                uint64_t s_ptr = read_val<uint64_t>(items + 0x20 + (i * 8));
                if (s_ptr) {
                    SoldierEntityData s = {};
                    s.id = read_val<int32_t>(s_ptr + 0x0ac);
                    s.hp = read_val<int32_t>(s_ptr + 0x0c8);
                    s.hp_max = read_val<int32_t>(s_ptr + 0x0cc);
                    s.is_dead = (read_val<uint8_t>(s_ptr + 0x1d0) != 0 || s.hp <= 0);
                    s.camp = read_val<int32_t>(s_ptr + 0x1dc);
                    s.pos_x = read_val<double>(s_ptr + 0x268);
                    s.pos_y = read_val<double>(s_ptr + 0x270);
                    if (!s.is_dead) snap.soldiers.push_back(s);
                }
            }
        }
    }

    // Jungle Monsters (+0x0b0)
    uint64_t monster_dict = read_val<uint64_t>(mgr_addr + 0x0b0);
    if (monster_dict) {
        uint64_t entries = read_val<uint64_t>(monster_dict + 0x018);
        int32_t count = read_val<int32_t>(monster_dict + 0x020);
        if (entries && count > 0 && count <= 128) {
            for (int i = 0; i < count; i++) {
                uint64_t entry_addr = entries + 0x20 + (i * 24);
                uint64_t m_ptr = read_val<uint64_t>(entry_addr + 0x10);
                if (m_ptr) {
                    MonsterEntityData m = {};
                    m.id = read_val<int32_t>(m_ptr + 0x0ac);
                    m.hp = read_val<int32_t>(m_ptr + 0x0c8);
                    m.hp_max = read_val<int32_t>(m_ptr + 0x0cc);
                    m.is_dead = (read_val<uint8_t>(m_ptr + 0x1d0) != 0 || m.hp <= 0);
                    m.pos_x = read_val<double>(m_ptr + 0x268);
                    m.pos_y = read_val<double>(m_ptr + 0x270);
                    if (!m.is_dead && (fabs(m.pos_x) > 0.1 || fabs(m.pos_y) > 0.1)) {
                        snap.monsters.push_back(m);
                    }
                }
            }
        }
    }

    return snap;
}

// 2D World-to-Minimap Math Normalization
static void world_to_minimap(double wx, double wy, float* out_x, float* out_y) {
    float norm_x = ((float)wx - (-52.0f)) / 104.0f;
    float norm_y = 1.0f - (((float)wy - (-52.0f)) / 104.0f); // Invert Y for top-left screen space

    if (norm_x < 0.0f) norm_x = 0.0f;
    if (norm_x > 1.0f) norm_x = 1.0f;
    if (norm_y < 0.0f) norm_y = 0.0f;
    if (norm_y > 1.0f) norm_y = 1.0f;

    *out_x = g_cfg.minimap_x + (norm_x * g_cfg.minimap_w);
    *out_y = g_cfg.minimap_y + (norm_y * g_cfg.minimap_h);
}

// 3D Isometric / Perspective World-to-Screen Projection
static bool world_to_screen_isometric(double target_x, double target_y, double local_x, double local_y, float* out_x, float* out_y) {
    float dx = (float)(target_x - local_x);
    float dy = (float)(target_y - local_y);

    // 45-degree ground plane rotation
    float iso_x = (dx - dy) * 0.70710678f;
    float iso_y = (dx + dy) * 0.70710678f;

    // True perspective depth along camera ray (Pitch: ~58 deg, Height: 28m)
    float cam_height = 28.0f;
    float depth = cam_height + (iso_y * 0.529919f); // cos(58 deg) ~ 0.529919
    if (depth < 4.0f) depth = 4.0f;
    float persp_scale = cam_height / depth;

    float sx = (g_cfg.screen_w / 2.0f) + (iso_x * g_cfg.cam_scale_x) * persp_scale;
    float sy = (g_cfg.screen_h / 2.0f) - ((iso_y * g_cfg.cam_scale_y) + g_cfg.cam_hud_offset_y) * persp_scale;

    *out_x = sx;
    *out_y = sy;

    return (sx >= 0.0f && sx <= g_cfg.screen_w && sy >= 0.0f && sy <= g_cfg.screen_h);
}

// Off-Screen Perimeter Edge Raycaster
static void calculate_edge_radar(float sx, float sy, float* out_cx, float* out_cy, float* out_angle_deg) {
    float center_x = g_cfg.screen_w / 2.0f;
    float center_y = g_cfg.screen_h / 2.0f;

    float dx = sx - center_x;
    float dy = sy - center_y;
    float angle = atan2f(dy, dx);
    *out_angle_deg = angle * 180.0f / (float)M_PI;

    float pad = g_cfg.edge_margin;
    float min_x = pad;
    float max_x = g_cfg.screen_w - pad;
    float min_y = pad;
    float max_y = g_cfg.screen_h - pad;

    float t_min = 1e9f;
    if (dx > 0.001f) t_min = fminf(t_min, (max_x - center_x) / dx);
    if (dx < -0.001f) t_min = fminf(t_min, (min_x - center_x) / dx);
    if (dy > 0.001f) t_min = fminf(t_min, (max_y - center_y) / dy);
    if (dy < -0.001f) t_min = fminf(t_min, (min_y - center_y) / dy);

    *out_cx = center_x + dx * t_min;
    *out_cy = center_y + dy * t_min;
}

// --- RENDER PASSES ---

static void render_minimap_layer(const FrameSnapshot& snap) {
    GLRenderer& gl = GLRenderer::instance();
    TextureManager& tex = TextureManager::instance();

    // 1. Minions Layer (Blue = Ally, Red = Enemy)
    if (g_cfg.minimap_show_minions) {
        for (const auto& s : snap.soldiers) {
            float mx, my;
            world_to_minimap(s.pos_x, s.pos_y, &mx, &my);
            uint32_t col = (s.camp == snap.local_player.camp) ? COLOR_ALLY_BLUE : COLOR_ENEMY_RED;
            gl.draw_circle_filled(mx, my, 3.5f, col, 12);
        }
    }

    // 2. Jungle Monsters Layer (Lord, Turtle, Buffs)
    if (g_cfg.minimap_show_monsters) {
        for (const auto& m : snap.monsters) {
            float mx, my;
            world_to_minimap(m.pos_x, m.pos_y, &mx, &my);
            bool is_lord = (m.id == 51298);
            bool is_turtle = (m.id == 51312);
            uint32_t col = is_lord ? COLOR_LORD_PURPLE : (is_turtle ? COLOR_TURTLE_GOLD : COLOR_RGBA(245, 158, 11, 200));
            gl.draw_circle_ring(mx, my, 5.5f, 1.8f, col, 16);
        }
    }

    // 3. Local Player Minimap Dot (Green with Direction Arrow)
    if (snap.local_player.address && !snap.local_player.is_dead) {
        float mx, my;
        world_to_minimap(snap.local_player.pos_x, snap.local_player.pos_y, &mx, &my);
        GLuint icon = tex.get_hero_icon(snap.local_player.hero_id);
        gl.draw_textured_circle(icon, mx, my, 11.0f, COLOR_SELF_GREEN, 2.5f);

        if (g_cfg.minimap_show_arrows && (fabs(snap.local_player.facing_x) > 0.01 || fabs(snap.local_player.facing_y) > 0.01)) {
            gl.draw_arrow(mx, my, mx + (float)snap.local_player.facing_x * 18.0f, my - (float)snap.local_player.facing_y * 18.0f, 6.0f, 2.0f, COLOR_SELF_GREEN);
        }
    }

    // 4. Allied Heroes (Blue)
    if (g_cfg.minimap_show_allies) {
        for (const auto& a : snap.allies) {
            if (a.is_dead) continue;
            float mx, my;
            world_to_minimap(a.pos_x, a.pos_y, &mx, &my);
            GLuint icon = tex.get_hero_icon(a.hero_id);
            gl.draw_textured_circle(icon, mx, my, 11.0f, COLOR_ALLY_BLUE, 2.5f);
        }
    }

    // 5. Enemy Heroes (Red with Direction Arrows)
    if (g_cfg.minimap_show_enemies) {
        for (const auto& e : snap.enemies) {
            if (e.is_dead) continue;
            float mx, my;
            world_to_minimap(e.pos_x, e.pos_y, &mx, &my);
            GLuint icon = tex.get_hero_icon(e.hero_id);
            gl.draw_textured_circle(icon, mx, my, 11.0f, COLOR_ENEMY_RED, 2.5f);

            if (g_cfg.minimap_show_arrows && (fabs(e.facing_x) > 0.01 || fabs(e.facing_y) > 0.01)) {
                gl.draw_arrow(mx, my, mx + (float)e.facing_x * 18.0f, my - (float)e.facing_y * 18.0f, 6.0f, 2.0f, COLOR_ENEMY_RED);
            }
        }
    }
}

static void render_screen_hud_layer(const FrameSnapshot& snap) {
    GLRenderer& gl = GLRenderer::instance();
    TextureManager& tex = TextureManager::instance();

    double local_x = snap.local_player.pos_x;
    double local_y = snap.local_player.pos_y;

    for (const auto& enemy : snap.enemies) {
        if (enemy.is_dead || enemy.hp <= 0) continue;

        double dx = enemy.pos_x - local_x;
        double dy = enemy.pos_y - local_y;
        float dist_m = (float)sqrt(dx * dx + dy * dy);

        float sx, sy;
        bool is_on_screen = world_to_screen_isometric(enemy.pos_x, enemy.pos_y, local_x, local_y, &sx, &sy);

        if (is_on_screen) {
            // --- 1. Overhead Combat HUD ---
            if (g_cfg.screen_show_overhead_hp) {
                float hp_pct = (enemy.hp_max > 0) ? ((float)enemy.hp / (float)enemy.hp_max) : 0.0f;
                float shield_pct = (enemy.hp_max > 0) ? ((float)enemy.shield / (float)enemy.hp_max) : 0.0f;
                gl.draw_hp_bar(sx - 35.0f, sy - 16.0f, 70.0f, 6.0f, hp_pct, shield_pct, COLOR_HP_RED);

                char lvl_buf[8];
                snprintf(lvl_buf, sizeof(lvl_buf), "L%d", enemy.level);
                gl.draw_string(sx - 48.0f, sy - 17.0f, lvl_buf, 0.9f, COLOR_TEXT_GOLD);

                char dist_buf[16];
                snprintf(dist_buf, sizeof(dist_buf), "%.0fm", dist_m);
                gl.draw_string(sx - 8.0f, sy - 8.0f, dist_buf, 0.8f, COLOR_TEXT_CYAN);
            }

            // --- 2. Skill & Ultimate Cooldown Badges ---
            if (g_cfg.screen_show_skill_cooldowns) {
                // Ultimate (Slot 3 or 4)
                int ult_id = 0;
                float ult_rem = enemy.ult_rem_s;
                for (const auto& ab : enemy.abilities) {
                    if (ab.slot >= 3 && !ult_id) ult_id = ab.spell_id;
                }
                GLuint ult_tex = tex.get_skill_icon(ult_id);
                gl.draw_cooldown_badge(ult_tex, sx, sy - 34.0f, 11.0f, ult_rem, true);

                // Skill 1
                int s1_id = enemy.abilities.size() > 0 ? enemy.abilities[0].spell_id : 0;
                float s1_rem = enemy.abilities.size() > 0 ? enemy.abilities[0].rem_s : 0.0f;
                GLuint s1_tex = tex.get_skill_icon(s1_id);
                gl.draw_cooldown_badge(s1_tex, sx - 22.0f, sy - 34.0f, 8.5f, s1_rem, false);

                // Skill 2
                int s2_id = enemy.abilities.size() > 1 ? enemy.abilities[1].spell_id : 0;
                float s2_rem = enemy.abilities.size() > 1 ? enemy.abilities[1].rem_s : 0.0f;
                GLuint s2_tex = tex.get_skill_icon(s2_id);
                gl.draw_cooldown_badge(s2_tex, sx + 22.0f, sy - 34.0f, 8.5f, s2_rem, false);
            }
        } else {
            // --- 3. Off-Screen Perimeter Edge Indicator ---
            if (g_cfg.screen_show_edge_radar && dist_m <= g_cfg.max_radar_distance) {
                float cx, cy, angle_deg;
                calculate_edge_radar(sx, sy, &cx, &cy, &angle_deg);

                GLuint hero_icon = tex.get_hero_icon(enemy.hero_id);
                uint32_t alert_col = enemy.ult_ready ? COLOR_HP_RED : COLOR_HP_YELLOW;
                gl.draw_edge_chevron(cx, cy, angle_deg, 14.0f, alert_col);
                gl.draw_textured_circle(hero_icon, cx, cy, 12.0f, alert_col, 2.0f);

                char dist_buf[16];
                snprintf(dist_buf, sizeof(dist_buf), "%.0fm", dist_m);
                gl.draw_string(cx - 8.0f, cy + 14.0f, dist_buf, 0.85f, COLOR_TEXT_WHITE);
            }
        }
    }
}

int main(int argc, char* argv[]) {
    printf("=================================================================\n");
    printf("     VEMINS ESP - NATIVE ON-SCREEN OVERLAY ENGINE (v1.2.0)       \n");
    printf("    [Zero Browser | Hardware-Accelerated SurfaceFlinger HUD]     \n");
    printf("=================================================================\n");

    // 1. Initialize Display & Surface
    NativeOverlayContext overlay_ctx;
    int target_w = 2400, target_h = 1080;
    if (argc > 2) {
        target_w = atoi(argv[1]);
        target_h = atoi(argv[2]);
    }
    native_surface_get_display_metrics(&target_w, &target_h);
    g_cfg.screen_w = (float)target_w;
    g_cfg.screen_h = (float)target_h;

    // Load Minimap and Camera Calibration Configuration
    load_config();

    if (!native_surface_init(&overlay_ctx, target_w, target_h)) {
        fprintf(stderr, "[-] Failed to initialize native overlay surface.\n");
        return 1;
    }

    // 2. Initialize 2D OpenGL ES Renderer
    GLRenderer& gl = GLRenderer::instance();
    if (!gl.init(target_w, target_h)) {
        fprintf(stderr, "[-] Failed to initialize GL renderer.\n");
        native_surface_destroy(&overlay_ctx);
        return 1;
    }

    // 3. Initialize Texture Manager
    TextureManager& tex = TextureManager::instance();
    tex.init();

    printf("[✓] VEMINS ESP Renderer Active at 60 FPS (Resolution: %dx%d)\n", target_w, target_h);

    // 4. Main 60 FPS Render Loop
    while (true) {
        FrameSnapshot snap = capture_live_snapshot();

        native_surface_begin_frame(&overlay_ctx);
        gl.begin();

        if (snap.in_match) {
            render_minimap_layer(snap);
            render_screen_hud_layer(snap);
        }

        gl.end();
        native_surface_end_frame(&overlay_ctx);

        usleep(16666); // ~60 FPS
    }

    native_surface_destroy(&overlay_ctx);
    return 0;
}
