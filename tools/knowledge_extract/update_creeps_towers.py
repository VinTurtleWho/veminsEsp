import json

# 1. Update creeps_towers.json
creeps_towers = {
    "wave_cadence": {
        "initial_spawn_s": 10.0,
        "interval_s": 30.0,
        "first_siege_wave_index": 2,
        "lane_bonus_cutoff_s": 300.0,
        "lane_modifiers": {
            "gold_lane": {
                "siege_gold_multiplier": 1.35,
                "siege_exp_multiplier": 1.00,
                "duration_s": 300.0
            },
            "exp_lane": {
                "siege_gold_multiplier": 1.00,
                "siege_exp_multiplier": 1.35,
                "duration_s": 300.0
            },
            "mid_lane": {
                "siege_gold_multiplier": 1.00,
                "siege_exp_multiplier": 1.00,
                "duration_s": 300.0
            }
        },
        "last_hit_bonus_pct": 30,
        "base_move_speed": 300,
        "late_game_speedup_start_s": 540,
        "max_late_game_speedup_pct": 20,
        "lord_wave_speedup_pct": 20
    },
    "minions": {
        "1": { "id": 1, "key": "melee", "name": "Melee Minion", "soldier_type": 1, "base_hp": 850, "hp_growth_per_min": 45, "base_move_speed": 300, "gold_reward": 60, "exp_reward": 50, "attack_range": 1.5 },
        "2": { "id": 2, "key": "caster", "name": "Caster Minion", "soldier_type": 2, "base_hp": 550, "hp_growth_per_min": 35, "base_move_speed": 300, "gold_reward": 45, "exp_reward": 35, "attack_range": 5.5 },
        "3": { "id": 3, "key": "siege", "name": "Siege Catapult", "soldier_type": 3, "base_hp": 1600, "hp_growth_per_min": 90, "base_move_speed": 300, "gold_reward": 95, "exp_reward": 75, "attack_range": 6.5 },
        "4": { "id": 4, "key": "super_melee", "name": "Super Melee Minion", "soldier_type": 4, "base_hp": 3800, "hp_growth_per_min": 160, "base_move_speed": 300, "gold_reward": 100, "exp_reward": 80, "attack_range": 1.5 },
        "5": { "id": 5, "key": "super_caster", "name": "Super Caster Minion", "soldier_type": 5, "base_hp": 2600, "hp_growth_per_min": 120, "base_move_speed": 300, "gold_reward": 90, "exp_reward": 70, "attack_range": 5.5 },
        "6": { "id": 6, "key": "super_siege", "name": "Super Siege Catapult", "soldier_type": 6, "base_hp": 4800, "hp_growth_per_min": 200, "base_move_speed": 300, "gold_reward": 120, "exp_reward": 95, "attack_range": 6.5 },
        "7": { "id": 7, "key": "enhanced_lord_minion", "name": "Enhanced Lord Minion", "soldier_type": 7, "base_hp": 5200, "hp_growth_per_min": 220, "base_move_speed": 360, "gold_reward": 130, "exp_reward": 105, "attack_range": 6.0, "lord_buff_speed_mult": 1.20 },
        "melee": { "id": 1, "key": "melee", "name": "Melee Minion", "soldier_type": 1, "base_hp": 850, "hp_growth_per_min": 45, "base_move_speed": 300, "gold_reward": 60, "exp_reward": 50, "attack_range": 1.5 },
        "caster": { "id": 2, "key": "caster", "name": "Caster Minion", "soldier_type": 2, "base_hp": 550, "hp_growth_per_min": 35, "base_move_speed": 300, "gold_reward": 45, "exp_reward": 35, "attack_range": 5.5 },
        "siege": { "id": 3, "key": "siege", "name": "Siege Catapult", "soldier_type": 3, "base_hp": 1600, "hp_growth_per_min": 90, "base_move_speed": 300, "gold_reward": 95, "exp_reward": 75, "attack_range": 6.5 },
        "super": { "id": 4, "key": "super_melee", "name": "Super Melee Minion", "soldier_type": 4, "base_hp": 3800, "hp_growth_per_min": 160, "base_move_speed": 300, "gold_reward": 100, "exp_reward": 80, "attack_range": 1.5 }
    },
    "monsters": {
        "51346": {
            "id": 51346, "key": "red_buff", "name": "Fiend (Red Buff)",
            "first_spawn_s": 30, "respawn_time_s": 90, "buff_duration_s": 75.0,
            "base_hp": 4800, "hp_growth_per_min": 180, "leash_radius": 7.0,
            "buff_effects": { "slow_melee_pct": [60, 80], "slow_ranged_pct": [20, 40], "true_damage_burn": 50, "scaling_ad_pct": 50 }
        },
        "51248": {
            "id": 51248, "key": "blue_buff", "name": "Core Guard (Blue Buff)",
            "first_spawn_s": 30, "respawn_time_s": 90, "buff_duration_s": 75.0,
            "base_hp": 4800, "hp_growth_per_min": 180, "leash_radius": 7.0,
            "buff_effects": { "cdr_pct": 10, "mana_cost_reduction_pct": 20, "energy_cost_reduction_pct": 20, "energy_sustain_kill_pct": 8 }
        },
        "51001": {
            "id": 51001, "key": "lithowanderer", "name": "Lithowanderer",
            "first_spawn_s": 43, "respawn_time_s": 120, "patrol_duration_s": 45,
            "base_hp": 3000, "hp_growth_per_min": 120, "leash_radius": 5.0,
            "buff_effects": { "river_move_speed_pct": 15, "grants_vision_ward": True }
        },
        "51002": { "id": 51002, "key": "small_camp", "name": "Standard Jungle Camp", "first_spawn_s": 30, "base_hp": 3200, "hp_growth_per_min": 150, "respawn_time_s": 70, "leash_radius": 6.0 },
        "red_buff": { "id": 51346, "key": "red_buff", "name": "Fiend (Red Buff)", "first_spawn_s": 30, "respawn_time_s": 90, "buff_duration_s": 75.0, "base_hp": 4800, "hp_growth_per_min": 180, "leash_radius": 7.0 },
        "blue_buff": { "id": 51248, "key": "blue_buff", "name": "Core Guard (Blue Buff)", "first_spawn_s": 30, "respawn_time_s": 90, "buff_duration_s": 75.0, "base_hp": 4800, "hp_growth_per_min": 180, "leash_radius": 7.0 },
        "lithowanderer": { "id": 51001, "key": "lithowanderer", "name": "Lithowanderer", "first_spawn_s": 43, "respawn_time_s": 120, "patrol_duration_s": 45, "base_hp": 3000, "hp_growth_per_min": 120, "leash_radius": 5.0 },
        "small_camp": { "id": 51002, "key": "small_camp", "name": "Standard Jungle Camp", "first_spawn_s": 30, "base_hp": 3200, "hp_growth_per_min": 150, "respawn_time_s": 70, "leash_radius": 6.0 }
    },
    "bosses": {
        "51312": {
            "id": 51312, "key": "turtle", "name": "Turtle",
            "first_spawn_s": 120, "despawn_s": 480, "respawn_time_s": 120, "max_spawns": 3,
            "base_hp": 16487, "hp_growth_per_min": 850,
            "rewards": {
                "team_gold": 120, "team_exp": 160,
                "killer_shield_base": 400, "killer_shield_per_level": 40, "killer_true_damage": True
            }
        },
        "51298": {
            "id": 51298, "key": "lord", "name": "Lord",
            "first_spawn_s": 480, "respawn_time_s": 180,
            "base_hp": 33984, "hp_growth_per_min": 2200,
            "evolution_stages": {
                "base_lord": { "time_range_s": [480, 719], "abilities": ["Stomp Knockup", "Lane Push"] },
                "enhanced_lord": { "time_range_s": [720, 1079], "charge_crash_true_dmg_pct": 0.50, "abilities": ["Stomp Knockup", "Turret Charge Crash (50% Max HP True Damage)"] },
                "evolved_lord": { "time_range_s": [1080, 99999], "charge_crash_true_dmg_pct": 0.50, "minion_damage_reduction_pct": 0.15, "lord_allied_hero_dr_pct": 0.40, "abilities": ["Stomp Knockup", "Turret Charge Crash", "15% Minion DR Aura", "Lord's Blessing True Damage"] }
            }
        },
        "turtle": { "id": 51312, "key": "turtle", "name": "Turtle", "first_spawn_s": 120, "despawn_s": 480, "respawn_time_s": 120, "base_hp": 16487, "hp_growth_per_min": 850 },
        "lord": { "id": 51298, "key": "lord", "name": "Lord", "first_spawn_s": 480, "respawn_time_s": 180, "base_hp": 33984, "hp_growth_per_min": 2200 }
    },
    "structures": {
        "1001": { "id": 1001, "key": "outer_turret", "name": "Outer Turret (T1)", "base_hp": 4800, "armor": 40, "energy_shield_duration_s": 300, "plate_gold": 120, "num_plates": 3, "attack_damage": 420 },
        "1002": { "id": 1002, "key": "inner_turret", "name": "Inner Turret (T2)", "base_hp": 5500, "armor": 50, "attack_damage": 520 },
        "1003": { "id": 1003, "key": "inhibitor_turret", "name": "Inhibitor Turret (T3)", "base_hp": 6500, "armor": 60, "attack_damage": 620, "spawns_super_minions_on_loss": True },
        "1010": { "id": 1010, "key": "base_nexus", "name": "Base Nexus", "base_hp": 8000, "armor": 70, "attack_damage": 720, "hp_regen_out_of_combat": 50 },
        "outer_turret": { "id": 1001, "key": "outer_turret", "name": "Outer Turret (T1)", "base_hp": 4800, "armor": 40, "energy_shield_duration_s": 300, "plate_gold": 120, "num_plates": 3 },
        "inner_turret": { "id": 1002, "key": "inner_turret", "name": "Inner Turret (T2)", "base_hp": 5500, "armor": 50 },
        "inhibitor_turret": { "id": 1003, "key": "inhibitor_turret", "name": "Inhibitor Turret (T3)", "base_hp": 6500, "armor": 60, "spawns_super_minions_on_loss": True },
        "base_nexus": { "id": 1010, "key": "base_nexus", "name": "Base Nexus", "base_hp": 8000, "armor": 70, "hp_regen_out_of_combat": 50 },
        "combat_rules": {
            "attack_range": 8.0,
            "true_sight_range": 8.5,
            "consecutive_hit_ramp_pct": 40,
            "max_consecutive_ramp_mult": 2.50,
            "backdoor_damage_reduction_pct": 75,
            "fountain_true_damage_per_tick": 1000
        }
    }
}

with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/creeps_towers.json", "w") as f:
    json.dump(creeps_towers, f, indent=2)

print("Updated creeps_towers.json successfully!")
