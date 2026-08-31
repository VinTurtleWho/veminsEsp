#include <iostream>
#include <cstdint>
#include <cstddef>
#include <cassert>

#define MAX_HEROES 10
#define MAX_SOLDIERS 32
#define MAX_MONSTERS 32
#define MAX_TOWERS 22
#define MAX_ABILITIES 6

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
    AbilityBinary abilities[MAX_ABILITIES]; // 120 (6 * 20 = 120)
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
    int32_t hp;             // 20
    int32_t hp_max;         // 24
    uint8_t is_dead;        // 28
    uint8_t pad[3];         // 29
    float pos_x;            // 32
    float pos_y;            // 36
    float attack_range;     // 40
} MonsterEntityBinary; // 44 bytes

typedef struct {
    uint64_t address;       // 0
    int32_t id;             // 8
    int32_t camp;           // 12
    int32_t hp;             // 16
    int32_t hp_max;         // 20
    uint8_t is_dead;        // 24
    uint8_t pad[3];         // 25
    float pos_x;            // 28
    float pos_y;            // 32
    float attack_range;     // 36
} TowerEntityBinary; // 40 bytes

typedef struct {
    uint32_t magic;         // 0 (0x564D4E53)
    uint32_t version;       // 4 (1)
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
    
    // Counts
    uint8_t hero_count;     // 56
    uint8_t soldier_count;  // 57
    uint8_t monster_count;  // 58
    uint8_t tower_count;    // 59
    uint8_t pad[4];         // 60

    // Contiguous Payload Arrays
    HeroEntityBinary heroes[MAX_HEROES];        // 64 + 10 * 240 = 2464
    SoldierEntityBinary soldiers[MAX_SOLDIERS]; // 2464 + 32 * 44 = 3872
    MonsterEntityBinary monsters[MAX_MONSTERS]; // 3872 + 32 * 44 = 5280
    TowerEntityBinary towers[MAX_TOWERS];       // 5280 + 22 * 40 = 6160
} FrameSnapshotBinary;

#pragma pack(pop)

int main() {
    std::cout << "sizeof(AbilityBinary): " << sizeof(AbilityBinary) << std::endl;
    std::cout << "sizeof(HeroEntityBinary): " << sizeof(HeroEntityBinary) << std::endl;
    std::cout << "sizeof(SoldierEntityBinary): " << sizeof(SoldierEntityBinary) << std::endl;
    std::cout << "sizeof(MonsterEntityBinary): " << sizeof(MonsterEntityBinary) << std::endl;
    std::cout << "sizeof(TowerEntityBinary): " << sizeof(TowerEntityBinary) << std::endl;
    std::cout << "sizeof(FrameSnapshotBinary): " << sizeof(FrameSnapshotBinary) << std::endl;
    
    std::cout << "Offset of heroes: " << offsetof(FrameSnapshotBinary, heroes) << std::endl;
    std::cout << "Offset of soldiers: " << offsetof(FrameSnapshotBinary, soldiers) << std::endl;
    std::cout << "Offset of monsters: " << offsetof(FrameSnapshotBinary, monsters) << std::endl;
    std::cout << "Offset of towers: " << offsetof(FrameSnapshotBinary, towers) << std::endl;
    return 0;
}
