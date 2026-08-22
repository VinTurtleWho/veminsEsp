import json

ITEMS_DATA = [
    # Physical Attack Items (Tier 3)
    (101, "Blade of Despair", "ATTACK", 3010, {"physical_attack": 160, "move_speed_pct": 5}, {"name": "Despair", "description": "+25% Physical Attack against enemy units below 50% HP for 2s"}),
    (102, "Demon Hunter Sword", "ATTACK", 2180, {"physical_attack": 35, "attack_speed_pct": 25}, {"name": "Devour", "description": "Basic attacks deal 8% of target current HP as extra physical damage"}),
    (103, "Malefic Roar", "ATTACK", 2060, {"physical_attack": 60}, {"name": "Armor Buster", "description": "Gain 0.05% extra physical penetration per point of enemy physical defense (up to 20%)"}),
    (104, "Windtalker", "ATTACK", 1820, {"attack_speed_pct": 40, "move_speed": 20, "crit_rate_pct": 10}, {"name": "Typhoon", "description": "Basic attacks release splash magic damage hitting up to 3 enemies"}),
    (105, "Wind of Nature", "ATTACK", 1910, {"physical_attack": 30, "attack_speed_pct": 20, "lifesteal_pct": 10}, {"name": "Wind Chant", "active": True, "cooldown_s": 70, "description": "Immunity to all physical damage for 2.0s"}),
    (106, "Berserker's Fury", "ATTACK", 2250, {"physical_attack": 65, "crit_rate_pct": 25, "crit_damage_pct": 40}, {"name": "Doom", "description": "Crit hits grant 5% extra Physical Attack for 2s"}),
    (107, "Haas' Claws", "ATTACK", 2020, {"physical_attack": 30, "attack_speed_pct": 20, "crit_rate_pct": 20, "lifesteal_pct": 25}, {"name": "Frenzy", "description": "Critical strikes grant 20% extra Attack Speed for 2s"}),
    (108, "Endless Battle", "ATTACK", 2470, {"physical_attack": 65, "hp": 250, "cooldown_reduction_pct": 10, "hybrid_lifesteal_pct": 8, "move_speed_pct": 5, "mana_regen": 5}, {"name": "Divine Justice", "description": "After casting a skill, next basic attack deals 60% of Physical Attack as True Damage"}),
    (109, "Corrosion Scythe", "ATTACK", 2050, {"physical_attack": 30, "attack_speed_pct": 35, "move_speed_pct": 5}, {"name": "Corrosion", "description": "Basic attacks slow enemy by 8% (up to 40%) and increase attack speed by 6% (up to 30%)"}),
    (110, "Golden Staff", "ATTACK", 2000, {"physical_attack": 55, "attack_speed_pct": 15}, {"name": "Endless Strike", "description": "Converts 1% Crit Chance into 1% Attack Speed; every 3rd basic attack triggers on-hit effects twice"}),
    (111, "Rose Gold Meteor", "ATTACK", 2120, {"physical_attack": 60, "magic_defense": 23, "lifesteal_pct": 10}, {"name": "Lifeline", "description": "Gains a 510-1350 shield and 25 Magic Defense when HP drops below 30%"}),
    (112, "Sea Halberd", "ATTACK", 2050, {"physical_attack": 80, "attack_speed_pct": 20}, {"name": "Lifebane", "description": "Reduces target shield and HP regen by 50% for 3s; deals 8% extra damage to heroes with higher HP"}),
    (113, "Hunter Strike", "ATTACK", 2010, {"physical_attack": 80, "cooldown_reduction_pct": 10, "physical_pen_flat": 15}, {"name": "Retribution", "description": "Dealing damage 5 times grants 50% Movement Speed decaying over 3s"}),
    (114, "Blade of the Heptaseas", "ATTACK", 1950, {"physical_attack": 70, "hp": 250, "physical_pen_flat": 15}, {"name": "Ambush", "description": "Next basic attack deals 160 + 40% Total AD bonus damage and slows by 40%"}),
    (115, "War Axe", "ATTACK", 2100, {"physical_attack": 25, "hp": 550, "cooldown_reduction_pct": 10, "spell_vamp_pct": 12}, {"name": "Fighting Spirit", "description": "Grants extra AD and penetration per stack, max 6 stacks"}),
    (116, "Bloodlust Axe", "ATTACK", 1970, {"physical_attack": 70, "cooldown_reduction_pct": 10, "spell_vamp_pct": 20}, {"name": "Bloodlust", "description": "+20% Spell Vamp"}),
    (117, "Great Dragon Spear", "ATTACK", 2140, {"physical_attack": 70, "cooldown_reduction_pct": 10, "crit_rate_pct": 20}, {"name": "Supreme Warrior", "description": "Casting Ultimate grants 30% Movement Speed for 7.5s"}),

    # Magic Power Items (Tier 3)
    (201, "Holy Crystal", "MAGIC", 2180, {"magic_power": 100}, {"name": "Mystery", "description": "+21%-35% Magic Power (scaling with level)"}),
    (202, "Lightning Truncheon", "MAGIC", 2250, {"magic_power": 75, "mana": 400, "cooldown_reduction_pct": 10}, {"name": "Resonate", "description": "Every 6s, next skill damages up to 3 enemies scaling with max mana"}),
    (203, "Glowing Wand", "MAGIC", 2200, {"magic_power": 75, "hp": 400, "move_speed_pct": 5}, {"name": "Scorch", "description": "Burns target for 1.5% Max HP as magic damage per second for 3s, reduces healing by 50%"}),
    (204, "Divine Glaive", "MAGIC", 1970, {"magic_power": 65, "magic_pen_pct": 40}, {"name": "Spellbreaker", "description": "+0.1% Magic Penetration per point of enemy Magic Defense (up to 20%)"}),
    (205, "Blood Wings", "MAGIC", 3000, {"magic_power": 175, "hp": 500}, {"name": "Guard", "description": "Gains an 800 + 100% Magic Power shield and 30 Movement Speed"}),
    (206, "Genius Wand", "MAGIC", 2000, {"magic_power": 75, "move_speed_pct": 5, "magic_pen_flat": 10}, {"name": "Magic Defense Shred", "description": "Reduces target Magic Defense by 3-7 per hit for 2s (up to 3 stacks)"}),
    (207, "Clock of Destiny", "MAGIC", 1950, {"magic_power": 60, "hp": 500, "mana": 600}, {"name": "Time", "description": "Gain 20 HP and 5 Magic Power every 20s, up to 10 stacks"}),
    (208, "Concentrated Energy", "MAGIC", 2020, {"magic_power": 70, "hp": 700, "hybrid_lifesteal_pct": 20}, {"name": "Recharge", "description": "Dealing magic damage increases Magic Power by 5 per stack for 5s (up to 6 stacks)"}),
    (209, "Ice Queen Wand", "MAGIC", 2240, {"magic_power": 75, "mana": 300, "move_speed_pct": 7, "spell_vamp_pct": 10}, {"name": "Ice Bound", "description": "Skills slow enemy by 10% for 2s (up to 30%)"}),
    (210, "Feather of Heaven", "MAGIC", 2030, {"magic_power": 55, "attack_speed_pct": 30, "cooldown_reduction_pct": 5}, {"name": "Affliction", "description": "Basic attacks deal 50 + 30% Magic Power as extra Magic Damage"}),
    (211, "Starlium Scythe", "MAGIC", 2220, {"magic_power": 70, "cooldown_reduction_pct": 10, "hybrid_lifesteal_pct": 8, "mana_regen": 6}, {"name": "Crisis", "description": "After skill cast, next basic attack deals 100 + 100% Magic Power as True Damage"}),
    (212, "Enchanted Talisman", "MAGIC", 1870, {"magic_power": 50, "hp": 250, "cooldown_reduction_pct": 20}, {"name": "Mana Spring", "description": "Restores 15% Max Mana every 10s; increases max CD reduction cap by 5%"}),
    (213, "Winter Crown", "MAGIC", 1910, {"magic_power": 60, "physical_defense": 25, "hp": 400}, {"name": "Frozen", "active": True, "cooldown_s": 100, "description": "Become frozen and invulnerable for 2.0s"}),

    # Defense Items (Tier 3)
    (301, "Athena's Shield", "DEFENSE", 2150, {"hp": 900, "magic_defense": 62, "hp_regen": 2}, {"name": "Shield", "description": "Reduces incoming magic damage by 25% for 3s upon taking magic damage"}),
    (302, "Antique Cuirass", "DEFENSE", 2170, {"hp": 920, "physical_defense": 54, "hp_regen": 4}, {"name": "Deter", "description": "When hit by an enemy skill, reduces attacker's physical attack by 8% (up to 3 stacks)"}),
    (303, "Dominance Ice", "DEFENSE", 2010, {"mana": 500, "physical_defense": 70, "move_speed_pct": 5}, {"name": "Arctic Cold", "description": "Reduces nearby enemy attack speed by 70% of base and reduces shield/HP regen by 50%"}),
    (304, "Immortality", "DEFENSE", 2120, {"hp": 800, "physical_defense": 20}, {"name": "Immortal", "cooldown_s": 210, "description": "Resurrect 2.5s after death with 16% Max HP and 220-1200 shield"}),
    (305, "Radiant Armor", "DEFENSE", 1880, {"hp": 950, "magic_defense": 52, "hp_regen": 12}, {"name": "Holy Blessing", "description": "Taking continuous magic damage grants 5-8 magic damage reduction per stack, max 6 stacks"}),
    (306, "Blade Armor", "DEFENSE", 1960, {"physical_defense": 90, "crit_damage_reduction_pct": 20}, {"name": "Bladed Armor", "description": "Reflects 25% of attacker's physical basic attack damage back to attacker"}),
    (307, "Oracle", "DEFENSE", 2060, {"hp": 850, "magic_defense": 42, "physical_defense": 25, "cooldown_reduction_pct": 10}, {"name": "Bless", "description": "Increases shield absorption and HP regen effects received by 30%"}),
    (308, "Brute Force Breastplate", "DEFENSE", 1870, {"hp": 600, "physical_defense": 23, "magic_defense": 23, "cooldown_reduction_pct": 10}, {"name": "Brute Force", "description": "Skills and basic attacks grant 6 Physical Attack & Magic Power, 2% Move Speed, and 15% CC resilience (max 6 stacks)"}),
    (309, "Guardian Helmet", "DEFENSE", 2200, {"hp": 1550, "hp_regen": 20}, {"name": "Recovery", "description": "Regenerates 2.5% Max HP per second out of combat"}),
    (310, "Twilight Armor", "DEFENSE", 2100, {"hp": 1200, "physical_defense": 20}, {"name": "Twilight", "description": "Taking physical damage exceeding 600 reduces damage above 600 by 20% and deals AOE true damage"}),
    (311, "Thunder Belt", "DEFENSE", 1990, {"hp": 800, "mana": 400, "physical_defense": 30, "magic_defense": 30, "cooldown_reduction_pct": 10}, {"name": "Thunderbolt", "description": "Basic attacks deal True Damage scaling with hybrid defense and permanently grant +1 Hybrid Defense on hero hit"}),
    (312, "Cursed Helmet", "DEFENSE", 1760, {"hp": 1200, "magic_defense": 25}, {"name": "Burning Soul", "description": "Deals 1.2% Max HP as magic damage per second to nearby enemies (increased by 140% against minions/creeps)"}),

    # Movement Boots (Tier 2)
    (401, "Warrior Boots", "MOVEMENT", 720, {"move_speed": 40, "physical_defense": 22}, {"name": "Valor", "description": "+5 Physical Defense per physical hit received (up to 25)"}),
    (402, "Tough Boots", "MOVEMENT", 700, {"move_speed": 40, "magic_defense": 22}, {"name": "Fortitude", "description": "Reduces CC and slow durations by 30%"}),
    (403, "Magic Shoes", "MOVEMENT", 710, {"move_speed": 40, "cooldown_reduction_pct": 10}, {"name": "CDR", "description": "+10% Cooldown Reduction"}),
    (404, "Arcane Boots", "MOVEMENT", 690, {"move_speed": 40, "magic_pen_flat": 10}, {"name": "Magic Pen", "description": "+10 Magic Penetration"}),
    (405, "Swift Boots", "MOVEMENT", 710, {"move_speed": 40, "attack_speed_pct": 15}, {"name": "Attack Speed", "description": "+15% Attack Speed"}),
    (406, "Rapid Boots", "MOVEMENT", 750, {"move_speed": 70}, {"name": "Side Effect", "description": "Dealing or taking damage reduces Movement Speed by 25 for 5s"}),
    (407, "Demon Shoes", "MOVEMENT", 720, {"move_speed": 40, "mana_regen": 10}, {"name": "Mysticism", "description": "Hero kills restore 10% Max Mana, minion kills restore 4% Max Mana"}),

    # Roaming Boots Blessings
    (501, "Roam: Conceal", "ROAM", 0, {}, {"name": "Conceal", "active": True, "cooldown_s": 80, "description": "Grants nearby allies Camouflage and 30%-75% Movement Speed for 5s"}),
    (502, "Roam: Encourage", "ROAM", 0, {}, {"name": "Encourage", "description": "Increases Physical Attack & Magic Power by 13-33 and Attack Speed by 15% for nearby allies"}),
    (503, "Roam: Favor", "ROAM", 0, {}, {"name": "Favor", "description": "Casting a heal/shield skill restores an additional 300-750 HP to the lowest HP ally every 10s"}),
    (504, "Roam: Dire Hit", "ROAM", 0, {}, {"name": "Dire Hit", "description": "Damaging an enemy below 35% HP deals 7%-18% Max HP extra hybrid damage (30s CD)"}),

    # Basic Component Items (Tier 1 & Tier 2)
    (601, "Dagger", "COMPONENT", 250, {"physical_attack": 15}, {}),
    (602, "Legion Sword", "COMPONENT", 910, {"physical_attack": 60}, {}),
    (603, "Vampire Mallet", "COMPONENT", 400, {"physical_attack": 8, "lifesteal_pct": 8}, {}),
    (604, "Javelin", "COMPONENT", 380, {"crit_rate_pct": 8}, {}),
    (605, "Knife", "COMPONENT", 280, {"attack_speed_pct": 10}, {}),
    (606, "Regular Spear", "COMPONENT", 600, {"physical_attack": 20, "attack_speed_pct": 10}, {}),
    (607, "Mystery Codex", "COMPONENT", 300, {"magic_power": 15}, {}),
    (608, "Magic Wand", "COMPONENT", 820, {"magic_power": 45}, {}),
    (609, "Tome of Evil", "COMPONENT", 950, {"magic_power": 35, "cooldown_reduction_pct": 8}, {}),
    (610, "Power Crystal", "COMPONENT", 220, {"mana": 280}, {}),
    (611, "Leather Armor", "COMPONENT", 220, {"physical_defense": 15}, {}),
    (612, "Silence Robe", "COMPONENT", 1020, {"hp": 540, "magic_defense": 30}, {}),
    (613, "Healing Necklace", "COMPONENT", 140, {"hp_regen": 2}, {}),
    (614, "Vitality Crystal", "COMPONENT", 300, {"hp": 230}, {}),
    (615, "Boots", "COMPONENT", 250, {"move_speed": 20}, {})
]

items_dict = {}
for item in ITEMS_DATA:
    iid, name, cat, price, stats, passive = item
    items_dict[str(iid)] = {
        "id": iid,
        "name": name,
        "category": cat,
        "price": price,
        "stats": stats,
        "passive": passive
    }

output_path = "/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/items.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(items_dict, f, indent=2)

print(f"Successfully generated {len(items_dict)} Equipment Items into {output_path}!")
