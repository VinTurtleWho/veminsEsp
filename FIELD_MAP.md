# AUTHORITATIVE PERCEPTION FIELD MAP & MEMORY OFFSETS (LOCKED & VERIFIED)

**Status**: Authoritative Field Registry (Core Offsets LOCKED & VERIFIED)  
**Cross-Reference**: Spatial evidence, coordinate frames, and anchor measurements are governed authoritatively by [`docs/SPATIAL_VERIFICATION.md`](file:///data/data/com.termux/files/home/veminsEsp/docs/SPATIAL_VERIFICATION.md). Anti-patterns and pitfall history are in [`docs/INVESTIGATION_HISTORY.md`](file:///data/data/com.termux/files/home/veminsEsp/docs/INVESTIGATION_HISTORY.md).

---

## 1. Match Engine & Roots

### `LogicBattleManager` (IL2CPP Dump Line: 359481)

- **Deterministic Base Root**: `libcsharp.so + 0x7680928` $\to$ `Il2CppClass(LogicBattleManager) + 0xb8` $\to$ `static_fields + 0x00` $\to$ `LogicBattleManager*` (**LOCKED & VERIFIED**).

| Field | Offset | Type | Semantic Name | Classification | Evidence & Provenance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_roadMgr` | `+0x058` | `uint64` | `inline_road_mgr_ptr` | `DISPROVEN` | **Contradicted live**: Evaluates to `0x0` (NULL) in 64-bit runtime. `RoadMgr.Instance` static singleton is an independent `HYPOTHESIS`. |
| `m_LocalPlayerLogic` | `+0x0a0` | `uint64` | `local_player_logic_ptr` | `PROVEN / LOCKED` | Fallback hero pointer; verified by RVA `0x1648e7c` disassembly (`ldr x0, [x0, #0xa0] ; ret`). |
| `m_dicPlayerLogic` | `+0x0a8` | `uint64` | `players_dict_ptr` | `PROVEN / LOCKED` | `Dictionary<uint64, LogicPlayer*>` containing all 10 match participants. Verified & Locked. |
| `m_dicMonsterLogic` | `+0x0b0` | `uint64` | `monsters_dict_ptr` | `PARTIALLY_PROVEN` | `Dictionary<uint64, LogicMonster*>` containing 126 jungle camps. Boss/Buff locations identified; live transition tracking ongoing. |
| `m_CampAFountain` | `+0xc0` | `uint64` | `camp_a_fountain_ptr` | `PROVEN / LOCKED` | Blue Base Fountain (`LogicFountain*`) @ `(-50.2, 0.0)`. Verified & Locked. |
| `m_CampBFountain` | `+0xc8` | `uint64` | `camp_b_fountain_ptr` | `PROVEN / LOCKED` | Red Base Fountain (`LogicFountain*`) @ `(+50.2, 0.0)`. Verified & Locked. |
| `m_CampAMainTower` | `+0xd0` | `uint64` | `camp_a_nexus_ptr` | `PROVEN / LOCKED` | Blue Base Crystal Nexus (`LogicTower*` ID 1009) @ `(-41.22, 0.00)`, HP 7900. Verified & Locked. |
| `m_CampBMainTower` | `+0xd8` | `uint64` | `camp_b_nexus_ptr` | `PROVEN / LOCKED` | Red Base Crystal Nexus (`LogicTower*` ID 1010) @ `(+41.22, 0.00)`, HP 7900. Verified & Locked. |
| `m_CampAList` | `+0xe0` | `uint64` | `camp_a_turrets_ptr` | `PROVEN / LOCKED` | `List<LogicTower*>` for Camp A lane defense towers (9 Turrets). Verified & Locked. |
| `m_CampBList` | `+0xe8` | `uint64` | `camp_b_turrets_ptr` | `PROVEN / LOCKED` | `List<LogicTower*>` for Camp B lane defense towers (9 Turrets). Verified & Locked. |
| `m_SoldierList` | `+0x128` | `uint64` | `soldier_list_ptr` | `PROVEN / LOCKED` | `List<LogicSoldier*>` active lane minions (16–25 soldiers). Verified & Locked. |
| `m_BlockBulletList` | `+0x130` | `uint64` | `block_bullet_list_ptr` | `PROVEN / LOCKED` | `List<LogicBullet>` active projectiles and block bullets (IL2CPP line 359499). Verified & Locked. |
| `m_SyncOperPlayerList` | `+0x138` | `uint64` | `sync_oper_player_list_ptr` | `PROVEN / LOCKED` | `List<LogicPlayer>` synchronized frame operation players (IL2CPP line 359500). Verified & Locked. |
| `_m_eState` | `+0x180` | `int32` | `battle_state` | `PROVEN / LOCKED` | Match lifecycle state (`2` = Practice/Custom, `6` = Live 5v5 Ranked/Classic). Verified & Locked. |
| `m_uiFrameTime` | `+0x19c` | `uint32` | `frame_time_ms` | `PROVEN / LOCKED` | Monotonic match simulation elapsed clock in ms. Verified & Locked. |
| `m_RealSelfPlayer` | `+0x200` | `uint64` | `real_self_player_ptr` | `PROVEN / LOCKED` | **Gate 8 Authoritative Root**: Local hero `LogicPlayer*` (Verified live in 5v5). Verified & Locked. |

---

## 2. Hero Entity (`LogicPlayer` / `LogicFighter`)

| Field | Offset | Type | Semantic Name | Classification | Evidence & Provenance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `m_ID` | `+0x0ac` | `int32` | `hero_id` | `PROVEN / LOCKED` | Archetype hero identifier (e.g. 18 = Layla, 78, 90). |
| `m_Level` | `+0x0b4` | `int32` | `level` | `PROVEN / LOCKED` | Hero level (bounds: 1..15). |
| `m_Hp` | `+0x0c8` | `int32` | `hp` | `PROVEN / LOCKED` | Current hitpoints. Drops to 0 on death. |
| `m_HpMax` | `+0x0cc` | `int32` | `hp_max` | `PROVEN / LOCKED` | Maximum hitpoints. |
| `m_Mp` | `+0x108` | `int32` | `mana` | `PROVEN / LOCKED` | Current mana / energy. |
| `m_MpMax` | `+0x10c` | `int32` | `mana_max` | `PROVEN / LOCKED` | Maximum mana / energy. |
| `m_AdditionHp1` | `+0x0e4` | `int32` | `shield` | `PROVEN / LOCKED` | Normal temporary shield hitpoints. |
| `m_AdditionHp2` | `+0x0f0` | `int32` | `magic_shield` | `PROVEN / LOCKED` | Magic-only absorption shield. |
| `m_bDeath` | `+0x1d0` | `uint8` | `is_dead` | `PROVEN / LOCKED` | Boolean death flag (`1` = dead). |
| `m_iStatus` | `+0x1e4` | `int32` | `status_mask` | `PARTIALLY_PROVEN` | Stun (`0x02`), Death (`0x200000` on Beatrix), Attack (`0x02000000`) PROVEN live. Remaining 12 CC flags are STRUCTURALLY_SUPPORTED. |
| `_bInHeroBattle`| `+0x22c`| `uint8` | `is_in_hero_battle`| `PROVEN / LOCKED` | PvP Hero-vs-Hero engagement flag. |
| `m_dRealPosX` | `+0x268` | `double` | `pos_x` | `PROVEN / LOCKED` | Real spatial X coordinate in world units. |
| `m_dRealPosY` | `+0x270` | `double` | `pos_y` | `PROVEN / LOCKED` | Real spatial Y coordinate in world units. |
| `_v2MoveDir` | `+0x288` | `double[2]`| `move_dir` | `PROVEN / LOCKED` | Movement joystick heading vector (0,0 when stationary). |
| `m_v2FaceDir` | `+0x298` | `double[2]`| `face_dir` | `PROVEN / LOCKED` | Facing orientation unit vector. |
| `_v2Dest` | `+0x2b8` | `double[2]`| `dest_pos` | `PARTIALLY_PROVEN`| Navigation target destination coordinate. |
| `m_uFaceLockTargetID`| `+0x370`| `uint32`| `face_lock_id`| `PROVEN / LOCKED` | Active lock-on target entity GUID. |
| `auras` | `+0x4c0` | `uint64` | `auras_dict_ptr` | `PARTIALLY_PROVEN`| Dictionary of active temporary buffs and durations (Dump line 1103921). |
| `m_AttrComp` | `+0x4d8` | `uint64` | `attr_comp_ptr` | `PROVEN / LOCKED` | Pointer to `AttributeComp` (runtime computed combat attributes). |
| `m_SkillComp` | `+0x4e0` | `uint64` | `skill_comp_ptr` | `PROVEN / LOCKED` | Pointer to `LogicSkillComp` (15–25 active ability records). |
| `m_EquipComp` | `+0x4f8` | `uint64` | `equip_comp_ptr` | `PROVEN / LOCKED` | Pointer to `LogicEquipComp` (16-byte unboxed item entries). |
| `m_uAttackerId` | `+0x560` | `uint32` | `attacker_id` | `PROVEN / LOCKED` | Entity GUID of last damage dealer. |
| `m_ReliveData` | `+0x580` | `uint64` | `relive_data_ptr`| `PROVEN / LOCKED` | Respawn countdown ms (+0x20) and killer ID (+0x30). |
| `m_Attacker` | `+0x588` | `uint64` | `attacker_ptr` | `PROVEN / LOCKED` | `LogicFighter*` pointer to attacking entity. |
| `m_pEnemy` | `+0x5a8` | `uint64` | `target_enemy_ptr`| `PARTIALLY_PROVEN`| Active auto-attack target lock pointer (0x0 when idle). |
| `m_pRealEnemy` | `+0x5b0` | `uint64` | `real_enemy_ptr` | `PARTIALLY_PROVEN`| True hero pointer behind clones/decoys. |
| `m_bInSightValueStatus`| `+0x73b`| `uint8`| `in_sight_status`| `HYPOTHESIS` | Minimap vision visibility flag. |
| `m_dCurrentRunSpeed`| `+0x750`| `double`| `run_speed` | `PROVEN / LOCKED` | Real-time movement velocity in units/sec. |
| `m_dCurrentAtkSpeed`| `+0x758`| `double`| `attack_speed` | `PROVEN / LOCKED` | Real-time attack speed multiplier. |
| `_totalGold` | `+0x858` | `int32` | `total_gold` | `PROVEN / LOCKED` | Total acquired match gold (matches scoreboard). |

---

## 3. Sub-Components & Collections

### `AttributeComp` (`PROVEN / LOCKED`)
* `LogicFighter + 0x4d8` $\to$ `AttributeComp*` (inherits `AttrData`)
* `AttrData + 0x038` $\to$ `m_dictIncreaseAttrs` (`Dictionary<int32, AttrIncrease>`)
* `AttrIncrease` struct (stride = 48 bytes):
  * `+0x10`: `int32 id` (`ATTR_KIND` enum)
  * `+0x14 + (5 * 4)` = `+0x28`: `int32 result` (`ATTR_INDEX_RESULT` — final runtime computed value)
  * Key `106` (`ATTR_KIND_PHY_SHIELD`): Physical Defense (Armor)
  * Key `107` (`ATTR_KIND_MAG_SHIELD`): Magic Defense (Magic Resistance)
  * Key `102` (`ATTR_KIND_PHY_ATT`): Physical Attack
  * Key `103` (`ATTR_KIND_MAG_ATT`): Magic Power
  * Key `105` (`ATTR_KIND_MOV_SPEED`): Movement Speed
  * Key `104` (`ATTR_KIND_ATT_SPEED`): Attack Speed Modifier
  * Key `36` (`ATTR_KIND_HERO_COOL`): Cooldown Reduction %
  * Key `30` (`ATTR_KIND_LUCKY_ATT`): Crit Rate %
  * Key `41` (`ATTR_KIND_PHY_VALUE_THROGH`): Flat Physical Penetration
  * Key `42` (`ATTR_KIND_MAG_VALUE_THROGH`): Flat Magic Penetration
  * Key `12` (`ATTR_KIND_PHY_THROUGH`): % Physical Penetration
  * Key `13` (`ATTR_KIND_MAG_THROUGH`): % Magic Penetration

### `LogicSkillComp` & `CoolDownComp` (`PROVEN / LOCKED`)
* `LogicSkillComp + 0x0a8` $\to$ `CoolDownComp*`
* `CoolDownComp + 0x018` $\to$ `m_DicCoolInfo` (`Dictionary<int32, CoolDownData*>`)
* `CoolDownData`:
  * `+0x10`: `int32 iSpellID`
  * `+0x14`: `int32 uiCoolTime` (remaining cooldown ms; 0 when ready)
  * `+0x18`: `int32 originalMaxCdTime` (max cooldown ms)
  * `+0x20`: `uint8 m_isCoolDown` (boolean cooling down flag)

### `LogicEquipComp` (`PROVEN / LOCKED`)
* `LogicEquipComp + 0x028` $\to$ `EquipDictionary`
* `EquipDictionary + 0x018` $\to$ `entries` (16-byte unboxed struct array: `hash_code`, `next`, `slot_index`, `item_id`).
* `+0x078`: `int32 m_UseEquipIndex` (active item slot index).

---

## 4. Structures, Minions, Jungle & Map Geometry

### `LogicTower` (`PROVEN / LOCKED`)
* `+0x0ac`: `int32 m_ID` (1009/1010 Nexus, 1015/1016 Inhibitor, 1013/1014 Inner, 1007/1008 Outer)
* `+0x0c8`: `int32 m_Hp` & `+0x0cc`: `int32 m_HpMax` (7900 / 7300 / 5700 / 4500)
* `+0x1dc`: `int32 m_EntityCampType` (1 = Blue, 2 = Red)
* `+0x268`: `double m_dRealPosX` & `+0x270`: `double m_dRealPosY`
* `+0x1d0`: `uint8 m_bDeath` (Destroyed boolean flag)
* `+0x930`: `float m_fAttackRange` (Defensive firing radius = 8.5 units)

### `LogicSoldier` (`PROVEN / LOCKED`)
* `+0x0ac`: `int32 m_ID`
* `+0x8f0`: `int32 m_SoldierType` (1=Melee, 2=Ranged, 3=Siege, 4=Super)
* `+0x900`: `int32 m_iPathId` (1=Top, 2=Mid, 3=Bot)
* `+0x0c8`: `int32 m_Hp` & `+0x0cc`: `int32 m_HpMax`
* `+0x268`: `double m_dRealPosX` & `+0x270`: `double m_dRealPosY`

### `LogicMonster` (`PARTIALLY_PROVEN`)
* `+0x0ac`: `int32 m_ID` (51298=Lord @ `(0.4, 20.5)`, 51312=Turtle @ `(0.4, 20.5)`, 51248=Blue Buff @ `(±18.1, ∓13.6)`, 51346=Red Buff @ `(∓13.8, ±11.1)`)
* `+0x0c8`: `int32 m_Hp` & `+0x0cc`: `int32 m_HpMax` (33,984 for Lord, 16,487 for Turtle)
* `+0x1d0`: `uint8 m_bDeath`
* `+0x868`: `double m_Money` & `+0x880`: `int32 m_Exp`

### Navigation & Map Grid
* `RoadMgr.Instance` (Independent Static Singleton): `HYPOTHESIS / UNTESTED`.
* `LogicTileMap.tileBlockData` (+0x78 in `LogicTileMap`): `UNTESTED`.
* `DynamicGrassManager` (Line 284900): `HYPOTHESIS / UNTESTED`. Bush geometry must not be inferred solely from `status_mask & 0x10000`.

