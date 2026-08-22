# VALIDATION CONTRACT & PROVENANCE TAXONOMY

**Status**: Authoritative Validation Standard  
**Version**: 1.2.0-PROD  
**Cross-References**:
- System architecture: [`ARCHITECTURE.md`](file:///data/data/com.termux/files/home/veminsEsp/ARCHITECTURE.md)
- Field offset registry: [`FIELD_MAP.md`](file:///data/data/com.termux/files/home/veminsEsp/FIELD_MAP.md)
- Design specification: [`ESP_DESIGN_SPEC.md`](file:///data/data/com.termux/files/home/veminsEsp/ESP_DESIGN_SPEC.md)
- Quickstart guide: [`QUICKSTART.md`](file:///data/data/com.termux/files/home/veminsEsp/QUICKSTART.md)

---

## 1. The 6-Tier Evidence & Provenance Taxonomy

To prevent premature claims of functionality and distinguish synthetic mock tests from live semantic ground truth, all fields and subsystems must strictly use this taxonomy:

| Tier | Name | Criteria | Current Subsystems in Scope |
| :--- | :--- | :--- | :--- |
| **PROVEN** | **Live Empirically Proven** | Directly observed, decoded, and falsification-tested in live match runtime with observable game correlation. | Deterministic Root (`Il2CppClass` +0xb8), Gate 8 local hero, 10 heroes (vitals, gold, 6 items, cooldowns, headings), 20 structures (Nexuses & Turrets with HP), Minion waves, Death bit (`0x200000`), Stun bit (`0x02`), Cartesian coordinates. |
| **PARTIALLY_PROVEN** | **Partially Proven** | Runtime entity/pointer observed, but continuous lifecycle transitions or combat dynamics remain incomplete. | Jungle Creeps & Bosses (camp locations and IDs identified; live kill/respawn transition tracking ongoing), Attacker Lock graph (`m_Attacker`), Active Projectiles container (`m_BulletList`). |
| **STRUCTURALLY_SUPPORTED** | **Structurally Supported** | Supported by IL2CPP class descriptors/type dump offsets, but not yet tested under live active match combat. | Player metadata (`FightPlayerData` lane roles, battle spells, emblem IDs), remaining 12 CC status bits. |
| **HYPOTHESIS** | **Plausible Hypothesis** | Plausible reverse-engineering interpretation that requires controlled live experiments. | `DynamicGrassManager` spatial bush polygon maps, `RoadMgr.Instance` static singleton. |
| **DISPROVEN** | **Experimentally Disproven** | Tested in live memory and contradicted. | `LogicBattleManager + 0x058` as `RoadMgr` (evaluates to NULL `0x0`), stale RVA `0x10c0774` (evaluates to `InvalidOperationException` stub). |
| **NOT_TESTED** | **Untested** | Known to exist in metadata, but never extracted, decoded, or tested. | `LogicTileMap.tileBlockData` 2D obstacle navigation mesh. |

---

## 2. Active Test Suite Baselines

All 113 offline unit, integration, mathematical projection, and protocol tests run and pass cleanly in $<3.0\text{s}$:

```
tests/test_world_snapshot.py:
  - Gate 8 Pointer Identity Resolution tests (3)
  - Hero Vitals, Gold, Coordinates & Level tests (8)
  - Hero Metadata & Role fields (assigned_lane, spell, emblem, IGN, rank) (1)
  - Crowd-Control & Status Effect Bitmask decoding (P0-2) (6)
  - Target Graph Pointer & Combat Interaction Telemetry (P0-3) (8)
  - Projectile Kinematics & Active Bullet tracking (P0-4) (7)
  - Hero Ability & Spell Cooldown parsing (P1-1) (9)
  - Hero Equipment & Item Inventory decoding (P1-2) (8)
  - Hero Buffs, Auras, Shields & Modifiers (P1-3) (8)
tests/test_identity_gate.py:
  - Gate 8 authoritative pointer binding, dynamic switching, fail-closed handling (5)
tests/test_schema_and_proofing.py:
  - Declarative schema validation and field decoding (7)
tests/test_blackbox_transitions.py:
  - BlackBoxValidator invariant and transition detection (8)
tests/test_daemon_protocol.py:
  - Streaming IPC length-prefixed framing and socket fragmentation (4)
tests/test_knowledge_store.py:
  - Typed GameKnowledgeProvider interface conformance (10)
tests/test_knowledge_extractor.py:
  - CData schema discovery and extractor contract testing (3)
tests/test_kotlin_engine_math.py:
  - Isometric coordinate transformations, safeCoerceIn clamping, and raycast bounds (6)
tests/test_kotlin_telemetry_and_config.py:
  - FrameSnapshot JSON parsing, dual-key compatibility, and ConfigManager persistence (3)
tests/test_local_control_and_telemetry.py:
  - LocalControlServer REST endpoints (/api/status, /api/config, /api/toggle, /api/ping) (4)
tests/test_esp_suite.py:
  - End-to-end integration and memory validation (6)
----------------------------------------------------------------------
Total: 113 tests | Failures: 0 | Errors: 0 | Execution Time: 2.91s
```
