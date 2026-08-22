"""
Black-Box Perception Validator (perception/blackbox_validator.py)
A pure downstream consumer of WorldSnapshot.
Completely agnostic to underlying memory reader, mock buffer, or live process.
Validates WorldSnapshot integrity, Gate 8 exclusivity, and state transition causality.
"""

from typing import Dict, Any, Optional, List
from perception.models import WorldSnapshot, HeroEntity


class BlackBoxValidator:
    """Validates public WorldSnapshot contracts without access to internal parsers."""

    def __init__(self):
        self.snapshots_inspected: int = 0
        self.validation_errors: List[str] = []

    def validate_snapshot(self, snap: WorldSnapshot) -> Dict[str, Any]:
        """
        Validates the internal consistency and invariant rules of a single WorldSnapshot.
        """
        self.snapshots_inspected += 1
        errors = []

        # 1. Temporal & Sequence Invariants
        if snap.sequence_id <= 0:
            errors.append(f"Invalid sequence_id: {snap.sequence_id}")
        if snap.timestamp_ns <= 0:
            errors.append(f"Invalid timestamp_ns: {snap.timestamp_ns}")

        # 2. Local Player Gate 8 Exclusivity
        if snap.local_player is not None:
            lp = snap.local_player
            if not lp.is_local_player:
                errors.append("local_player.is_local_player is False")
            if lp.level < 1 or lp.level > 15:
                errors.append(f"local_player.level out of bounds: {lp.level}")
            if lp.camp not in (1, 2):
                errors.append(f"local_player.camp invalid: {lp.camp}")
            if not lp.is_dead and (lp.hp <= 0 or lp.hp > lp.hp_max):
                errors.append(f"local_player HP invalid: {lp.hp}/{lp.hp_max}")

            # Ensure local player is never duplicated in allies or enemies
            if any(a.address == lp.address for a in snap.allies):
                errors.append("local_player duplicated in allies list")
            if any(e.address == lp.address for e in snap.enemies):
                errors.append("local_player duplicated in enemies list")

        # 3. Entity Separation
        for a in snap.allies:
            if a.is_local_player:
                errors.append(f"Ally hero {hex(a.address)} has is_local_player=True")
        for e in snap.enemies:
            if e.is_local_player:
                errors.append(f"Enemy hero {hex(e.address)} has is_local_player=True")

        return {
            "valid": len(errors) == 0,
            "sequence_id": snap.sequence_id,
            "has_local_player": snap.local_player is not None,
            "allies_count": len(snap.allies),
            "enemies_count": len(snap.enemies),
            "towers_count": len(snap.towers),
            "errors": errors
        }

    def detect_transition(
        self,
        before: WorldSnapshot,
        after: WorldSnapshot,
        expected_event: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compares two consecutive WorldSnapshots and records unambiguous semantic state transitions.
        Distinguishes active gameplay events from passive time ticks.
        """
        deltas: Dict[str, Any] = {}
        meaningful_event_count = 0

        # 1. Temporal & Monotonic Sequence Progression
        seq_delta = after.sequence_id - before.sequence_id
        time_delta_ms = (after.timestamp_ns - before.timestamp_ns) / 1_000_000.0
        frame_time_delta_ms = after.frame_time_ms - before.frame_time_ms

        deltas["seq_delta"] = seq_delta
        deltas["time_delta_ms"] = time_delta_ms
        deltas["frame_time_delta_ms"] = frame_time_delta_ms

        # 2. Local Player Deep Semantic Transition Tracking
        if before.local_player and after.local_player:
            lp_b = before.local_player
            lp_a = after.local_player

            # A. Kinematics / Movement
            dx = lp_a.pos_x - lp_b.pos_x
            dy = lp_a.pos_y - lp_b.pos_y
            dist = (dx**2 + dy**2)**0.5
            if dist > 0.01 or abs(lp_a.run_speed - lp_b.run_speed) > 0.01:
                deltas["movement"] = {
                    "pos_before": (round(lp_b.pos_x, 3), round(lp_b.pos_y, 3)),
                    "pos_after": (round(lp_a.pos_x, 3), round(lp_a.pos_y, 3)),
                    "distance": round(dist, 3),
                    "speed_before": lp_b.run_speed,
                    "speed_after": lp_a.run_speed
                }
                meaningful_event_count += 1

            # B. Level Up
            if lp_a.level > lp_b.level:
                deltas["level_up"] = {
                    "level_before": lp_b.level,
                    "level_after": lp_a.level,
                    "hp_max_before": lp_b.hp_max,
                    "hp_max_after": lp_a.hp_max,
                    "max_hp_growth": lp_a.hp_max - lp_b.hp_max
                }
                meaningful_event_count += 1

            # C. Vitals: Damage Taken vs Healing Received
            delta_hp = lp_a.hp - lp_b.hp
            delta_shield = lp_a.shield - lp_b.shield
            delta_magic_shield = lp_a.magic_shield - lp_b.magic_shield

            if delta_hp < 0:
                deltas["damage_taken"] = {
                    "hp_before": lp_b.hp,
                    "hp_after": lp_a.hp,
                    "damage_amount": abs(delta_hp),
                    "attacker_addr": lp_a.attacker_ptr or lp_a.attacker_id
                }
                meaningful_event_count += 1
            elif delta_hp > 0 and lp_a.level == lp_b.level and not (lp_b.is_dead and not lp_a.is_dead):
                deltas["healing_received"] = {
                    "hp_before": lp_b.hp,
                    "hp_after": lp_a.hp,
                    "heal_amount": delta_hp
                }
                meaningful_event_count += 1

            # D. Shields Change
            if delta_shield != 0 or delta_magic_shield != 0:
                deltas["shield_changed"] = {
                    "shield_before": lp_b.shield,
                    "shield_after": lp_a.shield,
                    "magic_shield_before": lp_b.magic_shield,
                    "magic_shield_after": lp_a.magic_shield,
                    "delta_shield": delta_shield,
                    "delta_magic_shield": delta_magic_shield
                }
                meaningful_event_count += 1

            # E. Death and Respawn Transitions
            if not lp_b.is_dead and (lp_a.is_dead or lp_a.hp <= 0):
                deltas["death"] = {
                    "dead_before": False,
                    "dead_after": True,
                    "final_hp": lp_a.hp
                }
                meaningful_event_count += 1
            elif lp_b.is_dead and not lp_a.is_dead and lp_a.hp > 0:
                deltas["respawn"] = {
                    "dead_before": True,
                    "dead_after": False,
                    "respawn_hp": lp_a.hp
                }
                meaningful_event_count += 1

            # F. Ability Cast Events vs Cooldown Countdown Ticks
            cast_events = []
            cooldown_ticks = []

            # 1. Active Channeling / Casting flag transition
            if not lp_b.abilities.is_casting and lp_a.abilities.is_casting:
                cast_events.append({
                    "type": "channel_start",
                    "active_spell_ptr": lp_a.abilities.active_spell_ptr
                })

            # 2. Cooldown entry comparison
            cds_b = {cd.spell_id: cd for cd in lp_b.abilities.cooldowns}
            cds_a = {cd.spell_id: cd for cd in lp_a.abilities.cooldowns}

            for sid, cd_after in cds_a.items():
                cd_before = cds_b.get(sid)
                if not cd_before:
                    if cd_after.is_cooling_down or cd_after.remaining_cd_ms > 0:
                        cast_events.append({
                            "type": "cooldown_initiated",
                            "spell_id": sid,
                            "remaining_cd_ms": cd_after.remaining_cd_ms,
                            "max_cd_ms": cd_after.max_cd_ms
                        })
                else:
                    # Case A: Ability was ready -> now cooling down OR cooldown jumped up (cast trigger)
                    if (not cd_before.is_cooling_down and cd_after.is_cooling_down) or (cd_after.remaining_cd_ms > cd_before.remaining_cd_ms + 100):
                        cast_events.append({
                            "type": "cooldown_initiated",
                            "spell_id": sid,
                            "cd_before": cd_before.remaining_cd_ms,
                            "cd_after": cd_after.remaining_cd_ms,
                            "max_cd_ms": cd_after.max_cd_ms
                        })
                    # Case B: Passive clock tick (cooldown decreasing)
                    elif cd_before.is_cooling_down and cd_after.remaining_cd_ms < cd_before.remaining_cd_ms:
                        cooldown_ticks.append({
                            "spell_id": sid,
                            "cd_before": cd_before.remaining_cd_ms,
                            "cd_after": cd_after.remaining_cd_ms,
                            "decrement_ms": cd_before.remaining_cd_ms - cd_after.remaining_cd_ms
                        })

            if cast_events:
                deltas["cast_events"] = cast_events
                meaningful_event_count += 1
            if cooldown_ticks:
                deltas["cooldown_ticks"] = cooldown_ticks

            # G. Inventory: Purchase vs Sale vs Swap
            items_b = {it.slot_index: it for it in lp_b.inventory.items}
            items_a = {it.slot_index: it for it in lp_a.inventory.items}
            ids_b = set(it.item_id for it in lp_b.inventory.items)
            ids_a = set(it.item_id for it in lp_a.inventory.items)

            new_ids = ids_a - ids_b
            removed_ids = ids_b - ids_a

            if new_ids:
                deltas["item_purchased"] = [{
                    "item_id": iid,
                    "slot_index": next(s for s, it in items_a.items() if it.item_id == iid)
                } for iid in new_ids]
                meaningful_event_count += 1
            elif removed_ids:
                deltas["item_sold"] = [{
                    "item_id": iid,
                    "slot_index": next(s for s, it in items_b.items() if it.item_id == iid)
                } for iid in removed_ids]
                meaningful_event_count += 1
            elif items_a != items_b and len(items_a) == len(items_b) and ids_a == ids_b:
                deltas["item_swapped"] = {
                    "slots_before": {s: it.item_id for s, it in items_b.items()},
                    "slots_after": {s: it.item_id for s, it in items_a.items()}
                }
                meaningful_event_count += 1

            # H. Buffs & Modifiers: Gain vs Loss vs Stacking
            buffs_b = {b.effect_id: b for b in lp_b.buffs.buffs}
            buffs_a = {b.effect_id: b for b in lp_a.buffs.buffs}
            b_ids_b = set(buffs_b.keys())
            b_ids_a = set(buffs_a.keys())

            new_buffs = b_ids_a - b_ids_b
            lost_buffs = b_ids_b - b_ids_a
            stacked_buffs = []

            for bid in (b_ids_a & b_ids_b):
                if buffs_a[bid].stack_count != buffs_b[bid].stack_count:
                    stacked_buffs.append({
                        "effect_id": bid,
                        "stack_before": buffs_b[bid].stack_count,
                        "stack_after": buffs_a[bid].stack_count
                    })

            if new_buffs:
                deltas["buff_gained"] = [{
                    "effect_id": bid,
                    "stack_count": buffs_a[bid].stack_count,
                    "source_spell_id": buffs_a[bid].source_spell_id
                } for bid in new_buffs]
                meaningful_event_count += 1
            if lost_buffs:
                deltas["buff_lost"] = [{
                    "effect_id": bid,
                    "was_finished": buffs_b[bid].is_finished
                } for bid in lost_buffs]
                meaningful_event_count += 1
            if stacked_buffs:
                deltas["buff_stacked"] = stacked_buffs
                meaningful_event_count += 1

        # 3. Match Entities Lifecycle Summaries
        # Towers
        towers_b = {t.address: t for t in before.towers}
        towers_a = {t.address: t for t in after.towers}
        destroyed_towers = []
        for addr, tw_after in towers_a.items():
            tw_before = towers_b.get(addr)
            if tw_before and not tw_before.is_dead and (tw_after.is_dead or tw_after.hp <= 0):
                destroyed_towers.append({
                    "address": addr,
                    "camp": tw_after.camp,
                    "tower_type": tw_after.tower_type
                })
        if destroyed_towers:
            deltas["towers_destroyed"] = destroyed_towers
            meaningful_event_count += 1

        # Enemy deaths
        enemies_b = {e.address: e for e in before.enemies}
        enemies_a = {e.address: e for e in after.enemies}
        enemy_deaths = []
        for addr, en_after in enemies_a.items():
            en_before = enemies_b.get(addr)
            if en_before and not en_before.is_dead and (en_after.is_dead or en_after.hp <= 0):
                enemy_deaths.append({
                    "address": addr,
                    "hero_id": en_after.hero_id,
                    "level": en_after.level
                })
        if enemy_deaths:
            deltas["enemy_deaths"] = enemy_deaths
            meaningful_event_count += 1

        # Ally deaths
        allies_b = {a.address: a for a in before.allies}
        allies_a = {a.address: a for a in after.allies}
        ally_deaths = []
        for addr, al_after in allies_a.items():
            al_before = allies_b.get(addr)
            if al_before and not al_before.is_dead and (al_after.is_dead or al_after.hp <= 0):
                ally_deaths.append({
                    "address": addr,
                    "hero_id": al_after.hero_id,
                    "level": al_after.level
                })
        if ally_deaths:
            deltas["ally_deaths"] = ally_deaths
            meaningful_event_count += 1

        # Monsters killed
        monsters_b = {m.address: m for m in before.monsters}
        monsters_a = {m.address: m for m in after.monsters}
        monsters_killed = []
        for addr, mon_after in monsters_a.items():
            mon_before = monsters_b.get(addr)
            if mon_before and not mon_before.is_dead and (mon_after.is_dead or mon_after.hp <= 0):
                monsters_killed.append({
                    "address": addr,
                    "monster_id": mon_after.monster_id
                })
        if monsters_killed:
            deltas["monsters_killed"] = monsters_killed
            meaningful_event_count += 1

        return {
            "expected_event": expected_event,
            "has_delta": meaningful_event_count > 0,
            "deltas": deltas
        }
