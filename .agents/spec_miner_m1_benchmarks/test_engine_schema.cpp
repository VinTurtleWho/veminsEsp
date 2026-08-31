/**
 * Standalone M1 Verification Suite: Engine Binary Schema Packing & Offsets
 * Validates deterministic memory layout, byte offsets, and alignment across C++ and NDK.
 */

#include <iostream>
#include <iomanip>
#include <cstdint>
#include <cstddef>
#include <cassert>
#include <cstring>
#include <cmath>

#define VEMINS_SCHEMA_MAGIC 0x564D4E53 // 'VMNS'
#define VEMINS_SCHEMA_VERSION 1
#define MAX_HEROES 10
#define MAX_SOLDIERS 32
#define MAX_MONSTERS 32
#define MAX_TOWERS 22
#define MAX_ABILITIES 6

#pragma pack(push, 1)

// Cooldown & Ability Slot (20 bytes)
typedef struct {
    int32_t spell_id;       // 0x00
    int32_t slot;           // 0x04 (1=S1, 2=S2, 3=Ult, 5=Spell)
    float remaining_s;      // 0x08
    float max_s;            // 0x0C
    uint8_t is_cooling_down;// 0x10 (1 if cooling down, 0 if ready)
    uint8_t is_ready;       // 0x11 (1 if ready to cast)
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
    uint8_t is_local;       // 0x2D: 1 if self player (Gate 8), 0 otherwise
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
    uint64_t libcsharp_base;// 0x18: Base address of libcsharp.so
    uint64_t liblogic_base; // 0x20: Base address of liblogic.so
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

// Compile-Time Packing & Layout Assertions
static_assert(sizeof(AbilityBinary) == 20, "AbilityBinary packing error: must be 20 bytes");
static_assert(sizeof(HeroEntityBinary) == 240, "HeroEntityBinary packing error: must be 240 bytes");
static_assert(sizeof(SoldierEntityBinary) == 44, "SoldierEntityBinary packing error: must be 44 bytes");
static_assert(sizeof(MonsterEntityBinary) == 44, "MonsterEntityBinary packing error: must be 44 bytes");
static_assert(sizeof(TowerEntityBinary) == 40, "TowerEntityBinary packing error: must be 40 bytes");
static_assert(sizeof(FrameSnapshotBinary) == 6160, "FrameSnapshotBinary packing error: must be 6160 bytes");

// Field Offset Assertions: AbilityBinary
static_assert(offsetof(AbilityBinary, spell_id) == 0, "AbilityBinary.spell_id offset mismatch");
static_assert(offsetof(AbilityBinary, slot) == 4, "AbilityBinary.slot offset mismatch");
static_assert(offsetof(AbilityBinary, remaining_s) == 8, "AbilityBinary.remaining_s offset mismatch");
static_assert(offsetof(AbilityBinary, max_s) == 12, "AbilityBinary.max_s offset mismatch");
static_assert(offsetof(AbilityBinary, is_cooling_down) == 16, "AbilityBinary.is_cooling_down offset mismatch");
static_assert(offsetof(AbilityBinary, is_ready) == 17, "AbilityBinary.is_ready offset mismatch");

// Field Offset Assertions: HeroEntityBinary
static_assert(offsetof(HeroEntityBinary, address) == 0, "HeroEntityBinary.address offset mismatch");
static_assert(offsetof(HeroEntityBinary, hero_id) == 8, "HeroEntityBinary.hero_id offset mismatch");
static_assert(offsetof(HeroEntityBinary, level) == 12, "HeroEntityBinary.level offset mismatch");
static_assert(offsetof(HeroEntityBinary, hp) == 16, "HeroEntityBinary.hp offset mismatch");
static_assert(offsetof(HeroEntityBinary, hp_max) == 20, "HeroEntityBinary.hp_max offset mismatch");
static_assert(offsetof(HeroEntityBinary, mp) == 24, "HeroEntityBinary.mp offset mismatch");
static_assert(offsetof(HeroEntityBinary, mp_max) == 28, "HeroEntityBinary.mp_max offset mismatch");
static_assert(offsetof(HeroEntityBinary, shield) == 32, "HeroEntityBinary.shield offset mismatch");
static_assert(offsetof(HeroEntityBinary, magic_shield) == 36, "HeroEntityBinary.magic_shield offset mismatch");
static_assert(offsetof(HeroEntityBinary, camp) == 40, "HeroEntityBinary.camp offset mismatch");
static_assert(offsetof(HeroEntityBinary, is_dead) == 44, "HeroEntityBinary.is_dead offset mismatch");
static_assert(offsetof(HeroEntityBinary, is_local) == 45, "HeroEntityBinary.is_local offset mismatch");
static_assert(offsetof(HeroEntityBinary, is_in_battle) == 46, "HeroEntityBinary.is_in_battle offset mismatch");
static_assert(offsetof(HeroEntityBinary, pos_x) == 48, "HeroEntityBinary.pos_x offset mismatch");
static_assert(offsetof(HeroEntityBinary, pos_y) == 52, "HeroEntityBinary.pos_y offset mismatch");
static_assert(offsetof(HeroEntityBinary, facing_x) == 56, "HeroEntityBinary.facing_x offset mismatch");
static_assert(offsetof(HeroEntityBinary, facing_y) == 60, "HeroEntityBinary.facing_y offset mismatch");
static_assert(offsetof(HeroEntityBinary, move_dir_x) == 64, "HeroEntityBinary.move_dir_x offset mismatch");
static_assert(offsetof(HeroEntityBinary, move_dir_y) == 68, "HeroEntityBinary.move_dir_y offset mismatch");
static_assert(offsetof(HeroEntityBinary, run_speed) == 72, "HeroEntityBinary.run_speed offset mismatch");
static_assert(offsetof(HeroEntityBinary, attack_speed) == 76, "HeroEntityBinary.attack_speed offset mismatch");
static_assert(offsetof(HeroEntityBinary, gold) == 80, "HeroEntityBinary.gold offset mismatch");
static_assert(offsetof(HeroEntityBinary, status_mask) == 84, "HeroEntityBinary.status_mask offset mismatch");
static_assert(offsetof(HeroEntityBinary, face_lock_id) == 88, "HeroEntityBinary.face_lock_id offset mismatch");
static_assert(offsetof(HeroEntityBinary, item_ids) == 92, "HeroEntityBinary.item_ids offset mismatch");
static_assert(offsetof(HeroEntityBinary, ability_count) == 116, "HeroEntityBinary.ability_count offset mismatch");
static_assert(offsetof(HeroEntityBinary, abilities) == 120, "HeroEntityBinary.abilities offset mismatch");

// Field Offset Assertions: SoldierEntityBinary
static_assert(offsetof(SoldierEntityBinary, address) == 0, "SoldierEntityBinary.address offset mismatch");
static_assert(offsetof(SoldierEntityBinary, id) == 8, "SoldierEntityBinary.id offset mismatch");
static_assert(offsetof(SoldierEntityBinary, soldier_type) == 12, "SoldierEntityBinary.soldier_type offset mismatch");
static_assert(offsetof(SoldierEntityBinary, path_id) == 16, "SoldierEntityBinary.path_id offset mismatch");
static_assert(offsetof(SoldierEntityBinary, camp) == 20, "SoldierEntityBinary.camp offset mismatch");
static_assert(offsetof(SoldierEntityBinary, hp) == 24, "SoldierEntityBinary.hp offset mismatch");
static_assert(offsetof(SoldierEntityBinary, hp_max) == 28, "SoldierEntityBinary.hp_max offset mismatch");
static_assert(offsetof(SoldierEntityBinary, is_dead) == 32, "SoldierEntityBinary.is_dead offset mismatch");
static_assert(offsetof(SoldierEntityBinary, pos_x) == 36, "SoldierEntityBinary.pos_x offset mismatch");
static_assert(offsetof(SoldierEntityBinary, pos_y) == 40, "SoldierEntityBinary.pos_y offset mismatch");

// Field Offset Assertions: MonsterEntityBinary
static_assert(offsetof(MonsterEntityBinary, address) == 0, "MonsterEntityBinary.address offset mismatch");
static_assert(offsetof(MonsterEntityBinary, id) == 8, "MonsterEntityBinary.id offset mismatch");
static_assert(offsetof(MonsterEntityBinary, monster_type) == 12, "MonsterEntityBinary.monster_type offset mismatch");
static_assert(offsetof(MonsterEntityBinary, camp) == 16, "MonsterEntityBinary.camp offset mismatch");
static_assert(offsetof(MonsterEntityBinary, hp) == 20, "MonsterEntityBinary.hp offset mismatch");
static_assert(offsetof(MonsterEntityBinary, hp_max) == 24, "MonsterEntityBinary.hp_max offset mismatch");
static_assert(offsetof(MonsterEntityBinary, is_dead) == 28, "MonsterEntityBinary.is_dead offset mismatch");
static_assert(offsetof(MonsterEntityBinary, pos_x) == 32, "MonsterEntityBinary.pos_x offset mismatch");
static_assert(offsetof(MonsterEntityBinary, pos_y) == 36, "MonsterEntityBinary.pos_y offset mismatch");
static_assert(offsetof(MonsterEntityBinary, attack_range) == 40, "MonsterEntityBinary.attack_range offset mismatch");

// Field Offset Assertions: TowerEntityBinary
static_assert(offsetof(TowerEntityBinary, address) == 0, "TowerEntityBinary.address offset mismatch");
static_assert(offsetof(TowerEntityBinary, id) == 8, "TowerEntityBinary.id offset mismatch");
static_assert(offsetof(TowerEntityBinary, camp) == 12, "TowerEntityBinary.camp offset mismatch");
static_assert(offsetof(TowerEntityBinary, hp) == 16, "TowerEntityBinary.hp offset mismatch");
static_assert(offsetof(TowerEntityBinary, hp_max) == 20, "TowerEntityBinary.hp_max offset mismatch");
static_assert(offsetof(TowerEntityBinary, is_dead) == 24, "TowerEntityBinary.is_dead offset mismatch");
static_assert(offsetof(TowerEntityBinary, pos_x) == 28, "TowerEntityBinary.pos_x offset mismatch");
static_assert(offsetof(TowerEntityBinary, pos_y) == 32, "TowerEntityBinary.pos_y offset mismatch");
static_assert(offsetof(TowerEntityBinary, attack_range) == 36, "TowerEntityBinary.attack_range offset mismatch");

// Field Offset Assertions: FrameSnapshotBinary
static_assert(offsetof(FrameSnapshotBinary, magic) == 0, "FrameSnapshotBinary.magic offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, version) == 4, "FrameSnapshotBinary.version offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, timestamp_ns) == 8, "FrameSnapshotBinary.timestamp_ns offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, frame_index) == 16, "FrameSnapshotBinary.frame_index offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, pid) == 20, "FrameSnapshotBinary.pid offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, libcsharp_base) == 24, "FrameSnapshotBinary.libcsharp_base offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, liblogic_base) == 32, "FrameSnapshotBinary.liblogic_base offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, in_match) == 40, "FrameSnapshotBinary.in_match offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, battle_state) == 41, "FrameSnapshotBinary.battle_state offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, local_camp) == 44, "FrameSnapshotBinary.local_camp offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, frame_time_ms) == 48, "FrameSnapshotBinary.frame_time_ms offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, read_latency_ms) == 52, "FrameSnapshotBinary.read_latency_ms offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, hero_count) == 56, "FrameSnapshotBinary.hero_count offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, soldier_count) == 57, "FrameSnapshotBinary.soldier_count offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, monster_count) == 58, "FrameSnapshotBinary.monster_count offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, tower_count) == 59, "FrameSnapshotBinary.tower_count offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, heroes) == 64, "FrameSnapshotBinary.heroes offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, soldiers) == 2464, "FrameSnapshotBinary.soldiers offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, monsters) == 3872, "FrameSnapshotBinary.monsters offset mismatch");
static_assert(offsetof(FrameSnapshotBinary, towers) == 5280, "FrameSnapshotBinary.towers offset mismatch");

void TestEndianness() {
    uint32_t val = 0x12345678;
    uint8_t* ptr = reinterpret_cast<uint8_t*>(&val);
    assert(ptr[0] == 0x78 && "Target platform must be Little-Endian for direct memory layout mapping");
    std::cout << "  [PASS] Little-Endian byte order verified." << std::endl;
}

void TestDirectBufferRoundtrip() {
    FrameSnapshotBinary frame;
    std::memset(&frame, 0, sizeof(frame));

    frame.magic = VEMINS_SCHEMA_MAGIC;
    frame.version = VEMINS_SCHEMA_VERSION;
    frame.timestamp_ns = 1725048924000000000ULL;
    frame.frame_index = 4200;
    frame.pid = 1337;
    frame.libcsharp_base = 0x7000000000ULL;
    frame.liblogic_base = 0x7100000000ULL;
    frame.in_match = 1;
    frame.battle_state = 6;
    frame.local_camp = 1;
    frame.frame_time_ms = 125430;
    frame.read_latency_ms = 0.32f;
    frame.hero_count = 2;
    frame.soldier_count = 1;
    frame.monster_count = 1;
    frame.tower_count = 1;

    // Local Hero
    frame.heroes[0].address = 0x72001000ULL;
    frame.heroes[0].hero_id = 18; // Layla
    frame.heroes[0].level = 15;
    frame.heroes[0].hp = 4200;
    frame.heroes[0].hp_max = 4200;
    frame.heroes[0].mp = 1500;
    frame.heroes[0].mp_max = 1500;
    frame.heroes[0].shield = 350;
    frame.heroes[0].camp = 1;
    frame.heroes[0].is_dead = 0;
    frame.heroes[0].is_local = 1; // Gate 8
    frame.heroes[0].is_in_battle = 1;
    frame.heroes[0].pos_x = -12.45f;
    frame.heroes[0].pos_y = 34.12f;
    frame.heroes[0].facing_x = 0.707f;
    frame.heroes[0].facing_y = 0.707f;
    frame.heroes[0].move_dir_x = 1.0f;
    frame.heroes[0].move_dir_y = 0.0f;
    frame.heroes[0].run_speed = 5.2f;
    frame.heroes[0].attack_speed = 1.65f;
    frame.heroes[0].gold = 10450;
    frame.heroes[0].status_mask = 0;
    frame.heroes[0].face_lock_id = 0x9999;
    frame.heroes[0].item_ids[0] = 101;
    frame.heroes[0].item_ids[1] = 102;
    frame.heroes[0].ability_count = 1;
    frame.heroes[0].abilities[0].spell_id = 1801;
    frame.heroes[0].abilities[0].slot = 1;
    frame.heroes[0].abilities[0].remaining_s = 2.4f;
    frame.heroes[0].abilities[0].max_s = 8.0f;
    frame.heroes[0].abilities[0].is_cooling_down = 1;
    frame.heroes[0].abilities[0].is_ready = 0;

    // Simulate Kotlin DirectByteBuffer mapping via direct raw byte buffer
    uint8_t buffer[sizeof(FrameSnapshotBinary)];
    std::memcpy(buffer, &frame, sizeof(FrameSnapshotBinary));

    // Deserialization check
    const FrameSnapshotBinary* read_frame = reinterpret_cast<const FrameSnapshotBinary*>(buffer);
    assert(read_frame->magic == 0x564D4E53);
    assert(read_frame->version == 1);
    assert(read_frame->pid == 1337);
    assert(read_frame->hero_count == 2);
    assert(read_frame->heroes[0].hero_id == 18);
    assert(read_frame->heroes[0].is_local == 1);
    assert(std::abs(read_frame->heroes[0].pos_x - (-12.45f)) < 0.0001f);
    assert(std::abs(read_frame->heroes[0].pos_y - 34.12f) < 0.0001f);
    assert(read_frame->heroes[0].abilities[0].is_cooling_down == 1);
    assert(std::abs(read_frame->heroes[0].abilities[0].remaining_s - 2.4f) < 0.0001f);

    std::cout << "  [PASS] DirectByteBuffer simulation roundtrip verified." << std::endl;
}

int main() {
    std::cout << "=======================================================" << std::endl;
    std::cout << "[TEST] Running test_engine_schema verification harness" << std::endl;
    std::cout << "=======================================================" << std::endl;

    TestEndianness();
    TestDirectBufferRoundtrip();

    std::cout << "-------------------------------------------------------" << std::endl;
    std::cout << "  sizeof(AbilityBinary)       = " << sizeof(AbilityBinary) << " bytes" << std::endl;
    std::cout << "  sizeof(HeroEntityBinary)    = " << sizeof(HeroEntityBinary) << " bytes" << std::endl;
    std::cout << "  sizeof(SoldierEntityBinary) = " << sizeof(SoldierEntityBinary) << " bytes" << std::endl;
    std::cout << "  sizeof(MonsterEntityBinary) = " << sizeof(MonsterEntityBinary) << " bytes" << std::endl;
    std::cout << "  sizeof(TowerEntityBinary)   = " << sizeof(TowerEntityBinary) << " bytes" << std::endl;
    std::cout << "  sizeof(FrameSnapshotBinary) = " << sizeof(FrameSnapshotBinary) << " bytes (Fixed)" << std::endl;
    std::cout << "=======================================================" << std::endl;
    std::cout << "[SUCCESS] All static compile-time & runtime schema tests passed." << std::endl;
    std::cout << "=======================================================" << std::endl;

    return 0;
}
