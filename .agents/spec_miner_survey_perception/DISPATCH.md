## 2026-08-30T20:10:48Z

Task:
Perform a comprehensive specification mining and technical survey for Entity Perception & Battlefield Memory Invariants (R2):
1. Analyze `offsets.json`, `FIELD_MAP.md`, `ARCHITECTURE.md`, `class_enum.py`, `minimap_projection.py`, `perception/`, and `LIVE_FULL_WORLD_SNAPSHOT.json`.
2. Extract exact memory chain invariants:
   - Module: `libcsharp.so`
   - Static root chain: `libcsharp.so + 0x7680928` -> `Il2CppClass + 0xb8` -> `static_fields + 0x00` -> `LogicBattleManager*`
   - Local Hero (Gate 8): `m_RealSelfPlayer` @ `+0x200` (fallback `+0x0a0`)
   - Player Dictionary: `m_dicPlayerLogic` @ `+0x0a8` (24-byte entry stride, `hashCode >= 0` tombstone filtering)
   - 64-bit continuous Cartesian coordinates: `m_dRealPosX (+0x268)` and `m_dRealPosY (+0x270)` in range [-52.0, +52.0]
   - Entities: Minions @ `+0x128`, Monsters @ `+0x0b0`, Towers @ `+0xd0, +0xd8, +0xe0, +0xe8`
   - Gate Bypass: Never gate on `battle_state`.
3. Specify camera tracking & coordinate continuity (`lastKnownLocalX/Y` anchor when localPlayer is null on death/respawn), strict `isfinite()` NaN/Inf sanitization, dictionary hole handling, and dynamic entity reallocations.
4. Detail all entity types, fields, packing requirements, and projection math requirements.

Write complete spec mining report to `/data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_survey_perception/handoff.md` and update `progress.md`.
