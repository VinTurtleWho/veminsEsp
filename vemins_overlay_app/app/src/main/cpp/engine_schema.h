#ifndef VEMINS_ENGINE_SCHEMA_H
#define VEMINS_ENGINE_SCHEMA_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define VEMINS_SCHEMA_MAGIC 0x564D4E53 // 'VMNS' in Little-Endian
#define VEMINS_SCHEMA_VERSION 1

#define MAX_HEROES 10
#define MAX_SOLDIERS 32
#define MAX_MONSTERS 32
#define MAX_TOWERS 22
#define MAX_ABILITIES 6
#define MAX_ITEMS 6

#define VEMINS_SNAPSHOT_BUFFER_SIZE 6160

#pragma pack(push, 1)

// ============================================================================
// Ability Slot & Cooldown Binary Struct (20 bytes)
// ============================================================================
typedef struct {
    int32_t spell_id;        // Archetype spell ID (e.g. 10810, 20001)
    int32_t slot;            // 1=S1, 2=S2, 3=Ult, 4=S4, 5=BattleSpell, 6=Recall
    float remaining_s;       // Remaining cooldown in seconds (0.0 = ready)
    float max_s;             // Total cooldown duration in seconds
    uint8_t is_cooling_down; // 1 if active cooldown, 0 if ready
    uint8_t is_ready;        // 1 if ready to cast (cooldown == 0)
    uint8_t pad[2];          // Explicit 2-byte alignment padding
} AbilityBinary;

static_assert(sizeof(AbilityBinary) == 20, "AbilityBinary size must be exactly 20 bytes");

// ============================================================================
// Hero Entity Binary Struct (240 bytes)
// ============================================================================
typedef struct {
    uint64_t address;        // Virtual memory address in game process
    int32_t hero_id;         // Hero Archetype ID (1..127)
    int32_t level;           // Hero level (1..15)
    int32_t hp;              // Current Hitpoints (0 if dead)
    int32_t hp_max;          // Maximum Hitpoints
    int32_t mp;              // Current Mana / Energy
    int32_t mp_max;          // Maximum Mana / Energy
    int32_t shield;          // Primary shield HP (+0x0e4)
    int32_t magic_shield;    // Secondary magic shield HP (+0x0f0)
    int32_t camp;            // 1 = Blue / Ally, 2 = Red / Enemy
    uint8_t is_dead;         // 1 if dead (m_bDeath != 0 or hp <= 0)
    uint8_t is_local;        // 1 if self player (Gate 8 matched)
    uint8_t is_in_battle;    // 1 if active in combat (+0x21c)
    uint8_t pad1;            // Explicit 1-byte alignment padding
    float pos_x;             // Continuous Cartesian X [-52.0, +52.0]
    float pos_y;             // Continuous Cartesian Y [-52.0, +52.0]
    float facing_x;          // Normalized facing unit vector X
    float facing_y;          // Normalized facing unit vector Y
    float move_dir_x;        // Normalized movement joystick heading X
    float move_dir_y;        // Normalized movement joystick heading Y
    float run_speed;         // Real-time movement speed (units/sec)
    float attack_speed;      // Attack speed multiplier
    int32_t gold;            // Cumulative match gold (+0x858)
    int32_t status_mask;     // 32-bit Crowd Control bitmask (+0x1e4)
    int32_t face_lock_id;    // Active lock-on target entity GUID (+0x370)
    int32_t item_ids[MAX_ITEMS]; // 6 equipped item archetype IDs (6 * 4 = 24 bytes)
    uint8_t ability_count;   // Populated ability count (0..6)
    uint8_t pad2[3];         // Explicit 3-byte alignment padding
    AbilityBinary abilities[MAX_ABILITIES]; // 6 * 20 = 120 bytes
} HeroEntityBinary;

static_assert(sizeof(HeroEntityBinary) == 240, "HeroEntityBinary size must be exactly 240 bytes");

// ============================================================================
// Minion / Soldier Entity Binary Struct (44 bytes)
// ============================================================================
typedef struct {
    uint64_t address;        // Virtual memory address in game process
    int32_t id;              // Minion instance GUID / ID
    int32_t soldier_type;    // 1=Melee, 2=Ranged, 3=Siege, 4=Super
    int32_t path_id;         // 1=Top, 2=Mid, 3=Bot
    int32_t camp;            // 1 = Blue, 2 = Red
    int32_t hp;              // Current HP
    int32_t hp_max;          // Max HP
    uint8_t is_dead;         // 1 if dead (hp <= 0 or is_dead != 0)
    uint8_t pad[3];          // Explicit 3-byte padding
    float pos_x;             // Continuous Cartesian X [-52.0, +52.0]
    float pos_y;             // Continuous Cartesian Y [-52.0, +52.0]
} SoldierEntityBinary;

static_assert(sizeof(SoldierEntityBinary) == 44, "SoldierEntityBinary size must be exactly 44 bytes");

// ============================================================================
// Jungle Monster Entity Binary Struct (44 bytes)
// ============================================================================
typedef struct {
    uint64_t address;        // Virtual memory address in game process
    int32_t id;              // Archetype ID (51298 Lord, 51312 Turtle, etc.)
    int32_t monster_type;    // Monster category / camp type
    int32_t camp;            // Neutral (0) or team camp
    int32_t hp;              // Current HP
    int32_t hp_max;          // Max HP
    uint8_t is_dead;         // 1 if killed / inactive
    uint8_t pad[3];          // Explicit 3-byte padding
    float pos_x;             // Continuous Cartesian X [-52.0, +52.0]
    float pos_y;             // Continuous Cartesian Y [-52.0, +52.0]
    float attack_range;      // Aggro / trigger radius
} MonsterEntityBinary;

static_assert(sizeof(MonsterEntityBinary) == 44, "MonsterEntityBinary size must be exactly 44 bytes");

// ============================================================================
// Defensive Tower & Structure Binary Struct (40 bytes)
// ============================================================================
typedef struct {
    uint64_t address;        // Virtual memory address in game process
    int32_t id;              // Tower ID (1009/1010 Nexus, 1007 Outer, etc.)
    int32_t camp;            // 1 = Blue, 2 = Red
    int32_t hp;              // Current HP
    int32_t hp_max;          // Max HP (7900 Nexus, 7300/5700/4500 Turrets)
    uint8_t is_dead;         // 1 if destroyed
    uint8_t pad[3];          // Explicit 3-byte padding
    float pos_x;             // Continuous Cartesian X [-52.0, +52.0]
    float pos_y;             // Continuous Cartesian Y [-52.0, +52.0]
    float attack_range;      // Firing radius (default ~8.5)
} TowerEntityBinary;

static_assert(sizeof(TowerEntityBinary) == 40, "TowerEntityBinary size must be exactly 40 bytes");

// ============================================================================
// Root Frame Snapshot Binary Struct (Total: Exactly 6,160 bytes)
// ============================================================================
typedef struct {
    // 1. Header (64 bytes)
    uint32_t magic;          // 0x00: 0x564D4E53 ('VMNS')
    uint32_t version;        // 0x04: Schema Version = 1
    uint64_t timestamp_ns;   // 0x08: CLOCK_MONOTONIC nanoseconds
    uint32_t frame_index;    // 0x10: Monotonic frame counter
    int32_t pid;             // 0x14: Game process PID
    uint64_t libcsharp_base; // 0x18: Base virtual address of libcsharp.so
    uint64_t liblogic_base;  // 0x20: Base virtual address of liblogic.so
    uint8_t in_match;        // 0x28: 1 if match is active, 0 otherwise
    uint8_t battle_state;    // 0x29: IL2CPP battle state (_m_eState @ +0x180)
    uint8_t pad_header[2];   // 0x2A: Alignment padding
    int32_t local_camp;      // 0x2C: 1 = Blue, 2 = Red
    uint32_t frame_time_ms;  // 0x30: Match simulation monotonic clock (ms @ +0x19c)
    float read_latency_ms;   // 0x34: Memory reader cycle duration in milliseconds
    
    // Counts (4 bytes)
    uint8_t hero_count;      // 0x38: Total active heroes (0..10)
    uint8_t soldier_count;   // 0x39: Total active minions (0..32)
    uint8_t monster_count;   // 0x3A: Total active jungle monsters (0..32)
    uint8_t tower_count;     // 0x3B: Total active defense structures (0..22)
    uint8_t pad[4];          // 0x3C: Header padding to 64 bytes
    
    // 2. Contiguous Fixed-Size Payload Arrays (6,096 bytes)
    HeroEntityBinary heroes[MAX_HEROES];        // Offset 64   (10 * 240 = 2,400 bytes)
    SoldierEntityBinary soldiers[MAX_SOLDIERS]; // Offset 2464 (32 * 44  = 1,408 bytes)
    MonsterEntityBinary monsters[MAX_MONSTERS]; // Offset 3872 (32 * 44  = 1,408 bytes)
    TowerEntityBinary towers[MAX_TOWERS];       // Offset 5280 (22 * 40  =   880 bytes)
} FrameSnapshotBinary;

static_assert(sizeof(FrameSnapshotBinary) == 6160, "FrameSnapshotBinary size must be exactly 6,160 bytes");

#pragma pack(pop)

#endif // VEMINS_ENGINE_SCHEMA_H
