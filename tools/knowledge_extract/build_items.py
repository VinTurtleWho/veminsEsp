import json
import os

# 1. Authoritative Items (Both 4-digit Game ID and 3-digit sequential)
ITEMS = {
    # Physical
    "2011": { "id": 2011, "alias_id": 101, "name": "Blade of Despair", "category": "ATTACK", "price": 3010, "tier": 3, "stats": { "physical_attack": 160, "move_speed_pct": 5 }, "passive": { "name": "Despair", "description": "+25% Physical Attack against units below 50% HP" } },
    "2002": { "id": 2002, "alias_id": 102, "name": "Demon Hunter Sword", "category": "ATTACK", "price": 2180, "tier": 3, "stats": { "physical_attack": 35, "attack_speed_pct": 25 }, "passive": { "name": "Devour", "description": "8% current HP as extra physical damage" } },
    "2003": { "id": 2003, "alias_id": 103, "name": "Malefic Roar", "category": "ATTACK", "price": 2060, "tier": 3, "stats": { "physical_attack": 60 }, "passive": { "name": "Armor Buster", "description": "+0.05% Physical Pen per enemy Armor point" } },
    "2005": { "id": 2005, "alias_id": 104, "name": "Windtalker", "category": "ATTACK", "price": 1820, "tier": 3, "stats": { "attack_speed_pct": 40, "move_speed": 20, "crit_rate_pct": 10 }, "passive": { "name": "Typhoon", "description": "Splash magic damage hitting up to 3 enemies" } },
    "2023": { "id": 2023, "alias_id": 105, "name": "Wind of Nature", "category": "ATTACK", "price": 1910, "tier": 3, "stats": { "physical_attack": 30, "attack_speed_pct": 20, "lifesteal_pct": 10 }, "active": { "name": "Wind Chant", "cooldown_s": 70, "description": "Physical damage immunity for 2.0s" } },
    "2001": { "id": 2001, "alias_id": 106, "name": "Berserker's Fury", "category": "ATTACK", "price": 2250, "tier": 3, "stats": { "physical_attack": 65, "crit_rate_pct": 25, "crit_damage_pct": 40 }, "passive": { "name": "Doom", "description": "+5% Physical Attack on crit" } },
    "2004": { "id": 2004, "alias_id": 107, "name": "Haas' Claws", "category": "ATTACK", "price": 2020, "tier": 3, "stats": { "physical_attack": 30, "attack_speed_pct": 20, "crit_rate_pct": 20, "lifesteal_pct": 25 }, "passive": { "name": "Frenzy", "description": "+20% Attack Speed on crit" } },
    "2008": { "id": 2008, "alias_id": 108, "name": "Endless Battle", "category": "ATTACK", "price": 2470, "tier": 3, "stats": { "physical_attack": 65, "hp": 250, "cooldown_reduction_pct": 10, "hybrid_lifesteal_pct": 8, "move_speed_pct": 5, "mana_regen": 5 }, "passive": { "name": "Divine Justice", "description": "60% Physical Attack True Damage after skill" } },
    "2006": { "id": 2006, "alias_id": 109, "name": "Corrosion Scythe", "category": "ATTACK", "price": 2050, "tier": 3, "stats": { "physical_attack": 30, "attack_speed_pct": 35, "move_speed_pct": 5 }, "passive": { "name": "Corrosion", "description": "Slows enemy by 8% and increases AS by 6%" } },
    "2007": { "id": 2007, "alias_id": 110, "name": "Golden Staff", "category": "ATTACK", "price": 2000, "tier": 3, "stats": { "physical_attack": 55, "attack_speed_pct": 15 }, "passive": { "name": "Endless Strike", "description": "Every 3rd basic attack triggers on-hit effects twice" } },
    "2009": { "id": 2009, "alias_id": 111, "name": "Rose Gold Meteor", "category": "ATTACK", "price": 2120, "tier": 3, "stats": { "physical_attack": 60, "magic_defense": 23, "lifesteal_pct": 10 }, "passive": { "name": "Lifeline", "description": "Gains shield when HP drops below 30%" } },
    "2010": { "id": 2010, "alias_id": 112, "name": "Sea Halberd", "category": "ATTACK", "price": 2050, "tier": 3, "stats": { "physical_attack": 80, "attack_speed_pct": 20 }, "passive": { "name": "Lifebane", "description": "50% healing/shield reduction" } },
    "2012": { "id": 2012, "alias_id": 113, "name": "Hunter Strike", "category": "ATTACK", "price": 2010, "tier": 3, "stats": { "physical_attack": 80, "cooldown_reduction_pct": 10, "physical_pen_flat": 15 }, "passive": { "name": "Retribution", "description": "+50% Movement Speed after 5 hits" } },
    "2013": { "id": 2013, "alias_id": 114, "name": "Blade of the Heptaseas", "category": "ATTACK", "price": 1950, "tier": 3, "stats": { "physical_attack": 70, "hp": 250, "physical_pen_flat": 15 }, "passive": { "name": "Ambush", "description": "Next basic attack deals 160 + 40% AD bonus damage" } },
    "2014": { "id": 2014, "alias_id": 115, "name": "War Axe", "category": "ATTACK", "price": 2100, "tier": 3, "stats": { "physical_attack": 25, "hp": 550, "cooldown_reduction_pct": 10, "spell_vamp_pct": 12 }, "passive": { "name": "Fighting Spirit", "description": "Extra AD and penetration per stack" } },
    "2015": { "id": 2015, "alias_id": 116, "name": "Bloodlust Axe", "category": "ATTACK", "price": 1970, "tier": 3, "stats": { "physical_attack": 70, "cooldown_reduction_pct": 10, "spell_vamp_pct": 20 }, "passive": { "name": "Bloodlust", "description": "+20% Spell Vamp" } },
    "2016": { "id": 2016, "alias_id": 117, "name": "Great Dragon Spear", "category": "ATTACK", "price": 2140, "tier": 3, "stats": { "physical_attack": 70, "cooldown_reduction_pct": 10, "crit_rate_pct": 20 }, "passive": { "name": "Supreme Warrior", "description": "+30% Move Speed on Ult" } },

    # Magic
    "1051": { "id": 1051, "alias_id": 201, "name": "Holy Crystal", "category": "MAGIC", "price": 2180, "tier": 3, "stats": { "magic_power": 100 }, "passive": { "name": "Mystery", "description": "+21%-35% Magic Power scaling with level" } },
    "1052": { "id": 1052, "alias_id": 202, "name": "Lightning Truncheon", "category": "MAGIC", "price": 2250, "tier": 3, "stats": { "magic_power": 75, "mana": 400, "cooldown_reduction_pct": 10 }, "passive": { "name": "Resonate", "description": "Bonus magic damage scaling with max mana" } },
    "1053": { "id": 1053, "alias_id": 203, "name": "Glowing Wand", "category": "MAGIC", "price": 2200, "tier": 3, "stats": { "magic_power": 75, "hp": 400, "move_speed_pct": 5 }, "passive": { "name": "Scorch", "description": "1.5% Max HP burn per second for 3s" } },
    "1054": { "id": 1054, "alias_id": 204, "name": "Divine Glaive", "category": "MAGIC", "price": 1970, "tier": 3, "stats": { "magic_power": 65, "magic_pen_pct": 40 }, "passive": { "name": "Spellbreaker", "description": "+0.1% Magic Pen per enemy Magic Defense" } },
    "1055": { "id": 1055, "alias_id": 205, "name": "Blood Wings", "category": "MAGIC", "price": 3000, "tier": 3, "stats": { "magic_power": 175, "hp": 500 }, "passive": { "name": "Guard", "description": "800 + 100% AP shield" } },
    "1056": { "id": 1056, "alias_id": 206, "name": "Genius Wand", "category": "MAGIC", "price": 2000, "tier": 3, "stats": { "magic_power": 75, "move_speed_pct": 5, "magic_pen_flat": 10 }, "passive": { "name": "Magic Shred", "description": "Reduces target Magic Defense by 3-7 per hit" } },
    "1057": { "id": 1057, "alias_id": 207, "name": "Clock of Destiny", "category": "MAGIC", "price": 1950, "tier": 3, "stats": { "magic_power": 60, "hp": 500, "mana": 600 }, "passive": { "name": "Time", "description": "Gain HP and AP every 20s" } },
    "1058": { "id": 1058, "alias_id": 208, "name": "Concentrated Energy", "category": "MAGIC", "price": 2020, "tier": 3, "stats": { "magic_power": 70, "hp": 700, "hybrid_lifesteal_pct": 20 }, "passive": { "name": "Recharge", "description": "+5 AP per stack" } },
    "1059": { "id": 1059, "alias_id": 209, "name": "Ice Queen Wand", "category": "MAGIC", "price": 2240, "tier": 3, "stats": { "magic_power": 75, "mana": 300, "move_speed_pct": 7, "spell_vamp_pct": 10 }, "passive": { "name": "Ice Bound", "description": "Skills slow enemy by 10% (up to 30%)" } },
    "1060": { "id": 1060, "alias_id": 210, "name": "Feather of Heaven", "category": "MAGIC", "price": 2030, "tier": 3, "stats": { "magic_power": 55, "attack_speed_pct": 30, "cooldown_reduction_pct": 5 }, "passive": { "name": "Affliction", "description": "Basic attacks deal 50 + 30% AP extra magic damage" } },
    "1061": { "id": 1061, "alias_id": 211, "name": "Starlium Scythe", "category": "MAGIC", "price": 2220, "tier": 3, "stats": { "magic_power": 70, "cooldown_reduction_pct": 10, "hybrid_lifesteal_pct": 8, "mana_regen": 6 }, "passive": { "name": "Crisis", "description": "100 + 100% AP True Damage after skill" } },
    "1062": { "id": 1062, "alias_id": 212, "name": "Enchanted Talisman", "category": "MAGIC", "price": 1870, "tier": 3, "stats": { "magic_power": 50, "hp": 250, "cooldown_reduction_pct": 20 }, "passive": { "name": "Mana Spring", "description": "15% Max Mana regen every 10s" } },
    "1063": { "id": 1063, "alias_id": 213, "name": "Winter Crown", "category": "MAGIC", "price": 1910, "tier": 3, "stats": { "magic_power": 60, "physical_defense": 25, "hp": 400 }, "active": { "name": "Frozen", "cooldown_s": 100, "description": "Frozen and invulnerable for 2.0s" } },

    # Defense
    "3001": { "id": 3001, "alias_id": 301, "name": "Athena's Shield", "category": "DEFENSE", "price": 2150, "tier": 3, "stats": { "hp": 900, "magic_defense": 62, "hp_regen": 2 }, "passive": { "name": "Shield", "description": "-25% incoming magic damage for 3s" } },
    "3002": { "id": 3002, "alias_id": 302, "name": "Antique Cuirass", "category": "DEFENSE", "price": 2170, "tier": 3, "stats": { "hp": 920, "physical_defense": 54, "hp_regen": 4 }, "passive": { "name": "Deter", "description": "-8% enemy physical attack on skill hit" } },
    "3003": { "id": 3003, "alias_id": 303, "name": "Dominance Ice", "category": "DEFENSE", "price": 2010, "tier": 3, "stats": { "mana": 500, "physical_defense": 70, "move_speed_pct": 5 }, "passive": { "name": "Arctic Cold", "description": "-70% enemy attack speed, -50% healing/shields" } },
    "3004": { "id": 3004, "alias_id": 304, "name": "Immortality", "category": "DEFENSE", "price": 2120, "tier": 3, "stats": { "hp": 800, "physical_defense": 20 }, "passive": { "name": "Immortal", "cooldown_s": 210, "description": "Resurrect 2.5s after death with 16% HP" } },
    "3005": { "id": 3005, "alias_id": 305, "name": "Radiant Armor", "category": "DEFENSE", "price": 1880, "tier": 3, "stats": { "hp": 950, "magic_defense": 52, "hp_regen": 12 }, "passive": { "name": "Holy Blessing", "description": "Magic damage reduction per stack" } },
    "3006": { "id": 3006, "alias_id": 306, "name": "Blade Armor", "category": "DEFENSE", "price": 1960, "tier": 3, "stats": { "physical_defense": 90, "crit_damage_reduction_pct": 20 }, "passive": { "name": "Bladed Armor", "description": "Reflects 25% physical basic attack damage" } },
    "3007": { "id": 3007, "alias_id": 307, "name": "Oracle", "category": "DEFENSE", "price": 2060, "tier": 3, "stats": { "hp": 850, "magic_defense": 42, "physical_defense": 25, "cooldown_reduction_pct": 10 }, "passive": { "name": "Bless", "description": "+30% shield and HP regen received" } },
    "3008": { "id": 3008, "alias_id": 308, "name": "Brute Force Breastplate", "category": "DEFENSE", "price": 1870, "tier": 3, "stats": { "hp": 600, "physical_defense": 23, "magic_defense": 23, "cooldown_reduction_pct": 10 }, "passive": { "name": "Brute Force", "description": "Grants AD, AP, Move Speed, and 15% CC resilience" } },
    "3009": { "id": 3009, "alias_id": 309, "name": "Guardian Helmet", "category": "DEFENSE", "price": 2200, "tier": 3, "stats": { "hp": 1550, "hp_regen": 20 }, "passive": { "name": "Recovery", "description": "Regenerates 2.5% Max HP/s out of combat" } },
    "3010": { "id": 3010, "alias_id": 310, "name": "Twilight Armor", "category": "DEFENSE", "price": 2100, "tier": 3, "stats": { "hp": 1200, "physical_defense": 20 }, "passive": { "name": "Twilight", "description": "Reduces physical burst damage above 600" } },
    "3011": { "id": 3011, "alias_id": 311, "name": "Thunder Belt", "category": "DEFENSE", "price": 1990, "tier": 3, "stats": { "hp": 800, "mana": 400, "physical_defense": 30, "magic_defense": 30, "cooldown_reduction_pct": 10 }, "passive": { "name": "Thunderbolt", "description": "Basic attacks deal True Damage and permanently stack +1 Hybrid Defense" } },
    "3012": { "id": 3012, "alias_id": 312, "name": "Cursed Helmet", "category": "DEFENSE", "price": 1760, "tier": 3, "stats": { "hp": 1200, "magic_defense": 25 }, "passive": { "name": "Burning Soul", "description": "1.2% Max HP magic damage/s to nearby enemies" } },

    # Movement Boots
    "4001": { "id": 4001, "alias_id": 401, "name": "Warrior Boots", "category": "MOVEMENT", "price": 720, "tier": 2, "stats": { "move_speed": 40, "physical_defense": 22 }, "passive": { "name": "Valor", "description": "+5 Physical Defense per physical hit received" } },
    "4002": { "id": 4002, "alias_id": 402, "name": "Tough Boots", "category": "MOVEMENT", "price": 700, "tier": 2, "stats": { "move_speed": 40, "magic_defense": 22 }, "passive": { "name": "Fortitude", "description": "Reduces CC and slow durations by 30%" } },
    "4003": { "id": 4003, "alias_id": 403, "name": "Magic Shoes", "category": "MOVEMENT", "price": 710, "tier": 2, "stats": { "move_speed": 40, "cooldown_reduction_pct": 10 }, "passive": { "name": "CDR", "description": "+10% Cooldown Reduction" } },
    "4004": { "id": 4004, "alias_id": 404, "name": "Arcane Boots", "category": "MOVEMENT", "price": 690, "tier": 2, "stats": { "move_speed": 40, "magic_pen_flat": 10 }, "passive": { "name": "Magic Pen", "description": "+10 Magic Penetration" } },
    "4005": { "id": 4005, "alias_id": 405, "name": "Swift Boots", "category": "MOVEMENT", "price": 710, "tier": 2, "stats": { "move_speed": 40, "attack_speed_pct": 15 }, "passive": { "name": "Attack Speed", "description": "+15% Attack Speed" } },
    "4006": { "id": 4006, "alias_id": 406, "name": "Rapid Boots", "category": "MOVEMENT", "price": 750, "tier": 2, "stats": { "move_speed": 70 }, "passive": { "name": "Side Effect", "description": "-25 Move Speed on combat" } },
    "4007": { "id": 4007, "alias_id": 407, "name": "Demon Shoes", "category": "MOVEMENT", "price": 720, "tier": 2, "stats": { "move_speed": 40, "mana_regen": 10 }, "passive": { "name": "Mysticism", "description": "Mana restore on hero/minion kill" } }
}

# Also add alias keys for backwards compatibility
items_with_aliases = dict(ITEMS)
for k, item in ITEMS.items():
    if "alias_id" in item:
        items_with_aliases[str(item["alias_id"])] = item

with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/items.json", "w") as f:
    json.dump(items_with_aliases, f, indent=2)

print(f"Generated {len(items_with_aliases)} Item entries in items.json!")
