#!/usr/bin/env python3
"""
Live Truth Monitor (live_truth_monitor.py)
Reads directly from live running MLBB process via DaemonMemoryReader over TCP.
Captures snapshots, computes deltas against previous baselines, and logs raw ground truth.
Zero mocks. Zero fake stimuli. Pure read-only observability.
"""

import json
import os
import struct
import sys
import time
from typing import Dict, Any, Optional

from perception.memory_reader import DaemonMemoryReader
from perception.models import HeroStatusEffects
from perception.parser import EntityParser


class LiveTruthMonitor:
    def __init__(self, host: str = "127.0.0.1", port: int = 9999):
        self.reader = DaemonMemoryReader(host=host, port=port, timeout=5.0)
        self.connected = False
        self.pid = 0
        self.liblogic_base = 0
        self.hero_ptr = 0
        self.baseline: Optional[Dict[str, Any]] = None
        self.history_file = "LIVE_TRUTH_TRANSITIONS.json"
        self.transitions = []

    def connect(self) -> bool:
        self.connected = self.reader.connect()
        if self.connected:
            info = self.reader.get_info()
            self.pid = info.get("pid", 0)
            self.liblogic_base = info.get("liblogic_base", 0)
        return self.connected

    def scan_hero(self) -> int:
        from perception.orchestrator import ProductionPerceptionOrchestrator
        orchestrator = ProductionPerceptionOrchestrator(self.reader)
        mgr_addr = orchestrator.discover_battle_manager()
        if mgr_addr > 0:
            self.hero_ptr = orchestrator.engine.resolve_local_player_from_manager(mgr_addr)
        else:
            self.hero_ptr = 0
        return self.hero_ptr

    def capture_raw_hero(self) -> Optional[Dict[str, Any]]:
        if not self.hero_ptr:
            self.scan_hero()
        if not self.hero_ptr:
            return None

        raw = self.reader.read_bytes(self.hero_ptr, 0x1000)
        if len(raw) < 0x1000:
            return None

        t_now = time.time()
        vtable = struct.unpack_from("<Q", raw, 0x000)[0]
        hero_id = struct.unpack_from("<i", raw, 0x0ac)[0]
        level = struct.unpack_from("<i", raw, 0x0b4)[0]
        hp = struct.unpack_from("<i", raw, 0x0c8)[0]
        hp_max = struct.unpack_from("<i", raw, 0x0cc)[0]
        mech_armor = struct.unpack_from("<i", raw, 0x0d8)[0]
        shield1 = struct.unpack_from("<i", raw, 0x0e4)[0]
        shield1_max = struct.unpack_from("<i", raw, 0x0e8)[0]
        shield2 = struct.unpack_from("<i", raw, 0x0f0)[0]
        shield2_max = struct.unpack_from("<i", raw, 0x0f4)[0]
        mp = struct.unpack_from("<i", raw, 0x108)[0]
        mp_max = struct.unpack_from("<i", raw, 0x10c)[0]
        is_dead = (raw[0x1d0] != 0)
        camp = struct.unpack_from("<i", raw, 0x1dc)[0]
        raw_status = struct.unpack_from("<i", raw, 0x1e4)[0]
        pos_x = struct.unpack_from("<d", raw, 0x268)[0]
        pos_y = struct.unpack_from("<d", raw, 0x270)[0]
        run_speed = struct.unpack_from("<d", raw, 0x750)[0]
        atk_speed = struct.unpack_from("<d", raw, 0x758)[0]
        target_enemy = struct.unpack_from("<Q", raw, 0x5a8)[0]
        attacker = struct.unpack_from("<Q", raw, 0x588)[0]
        skill_comp_ptr = struct.unpack_from("<Q", raw, 0x4e0)[0]
        equip_comp_ptr = struct.unpack_from("<Q", raw, 0x4f8)[0]
        auras_dict_ptr = struct.unpack_from("<Q", raw, 0x4c0)[0]

        abilities = EntityParser.decode_cooldowns(self.reader, skill_comp_ptr)
        inventory = EntityParser.decode_inventory(self.reader, equip_comp_ptr)
        buffs = EntityParser.decode_buffs(self.reader, auras_dict_ptr)

        return {
            "timestamp": t_now,
            "hero_ptr": self.hero_ptr,
            "vtable": vtable,
            "hero_id": hero_id,
            "level": level,
            "hp": hp,
            "hp_max": hp_max,
            "mp": mp,
            "mp_max": mp_max,
            "shield": shield1,
            "magic_shield": shield2,
            "is_dead": is_dead,
            "camp": camp,
            "raw_status": raw_status,
            "pos_x": pos_x,
            "pos_y": pos_y,
            "run_speed": run_speed,
            "attack_speed": atk_speed,
            "target_enemy_ptr": target_enemy,
            "attacker_ptr": attacker,
            "skill_comp_ptr": skill_comp_ptr,
            "equip_comp_ptr": equip_comp_ptr,
            "auras_dict_ptr": auras_dict_ptr,
            "is_casting": abilities.is_casting,
            "active_spell_ptr": abilities.active_spell_ptr,
            "cooldowns": [
                {
                    "spell_id": cd.spell_id,
                    "remaining_cd_ms": cd.remaining_cd_ms,
                    "max_cd_ms": cd.max_cd_ms,
                    "is_cooling_down": cd.is_cooling_down
                }
                for cd in abilities.cooldowns
            ],
            "inventory": {
                "item_count": inventory.item_count,
                "active_slot_index": inventory.active_slot_index,
                "items": [
                    {"slot": it.slot_index, "item_id": it.item_id, "price": it.price}
                    for it in inventory.items
                ]
            },
            "buffs": [
                {"effect_id": b.effect_id, "guid": b.guid, "stacks": b.stack_count, "val": b.value}
                for b in buffs.buffs
            ]
        }

    def close(self):
        self.reader.close()


def print_baseline_summary(snap: Dict[str, Any]):
    print("\n=================================================================")
    print("                CURRENT LIVE HERO BASELINE                       ")
    print("=================================================================")
    print(f"  Hero Identity : Hero ID {snap['hero_id']} | Level {snap['level']} | Camp {snap['camp']}")
    print(f"  Hero Pointer  : {hex(snap['hero_ptr'])} | VTable: {hex(snap['vtable'])}")
    print(f"  Vitals        : HP {snap['hp']}/{snap['hp_max']} | MP {snap['mp']}/{snap['mp_max']}")
    print(f"  Shields       : Primary {snap['shield']} | Magic {snap['magic_shield']}")
    print(f"  Kinematics    : Pos ({snap['pos_x']:.2f}, {snap['pos_y']:.2f}) | Speed {snap['run_speed']:.2f}")
    print(f"  Status        : Dead={snap['is_dead']} | StatusMask={hex(snap['raw_status'])}")
    print(f"  Target Graph  : Target={hex(snap['target_enemy_ptr'])} | Attacker={hex(snap['attacker_ptr'])}")
    print(f"  Abilities     : Casting={snap['is_casting']} | Cooldown Records={len(snap['cooldowns'])}")
    for cd in snap['cooldowns'][:6]:
        print(f"      * Spell {cd['spell_id']}: {cd['remaining_cd_ms']}/{cd['max_cd_ms']}ms (CD: {cd['is_cooling_down']})")
    print(f"  Inventory     : Item Count={snap['inventory']['item_count']} | Active Slot={snap['inventory']['active_slot_index']}")
    for it in snap['inventory']['items']:
        print(f"      * Slot {it['slot']}: Item ID {it['item_id']}")
    print(f"  Active Buffs  : Buff Count={len(snap['buffs'])}")
    for b in snap['buffs']:
        print(f"      * Effect {b['effect_id']}: Stacks={b['stacks']}, Val={b['val']}")
    print("=================================================================\n")


if __name__ == "__main__":
    mon = LiveTruthMonitor()
    if not mon.connect():
        print("[!] ERROR: Failed to connect to agent_daemon at 127.0.0.1:9999")
        sys.exit(1)

    print(f"[✓] Connected to agent_daemon (PID {mon.pid}, liblogic {hex(mon.liblogic_base)})")
    ptr = mon.scan_hero()
    if not ptr:
        print("[!] No active hero pointer found.")
        mon.close()
        sys.exit(1)

    snap = mon.capture_raw_hero()
    if snap:
        print_baseline_summary(snap)
        with open("CURRENT_LIVE_BASELINE.json", "w") as f:
            json.dump(snap, f, indent=2)
    mon.close()
