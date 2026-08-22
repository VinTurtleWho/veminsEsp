"""
Perception Models: Immutable data models for MLBB game state.
Contains strictly validated entities with evidence-backed field mappings.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class AbilityCooldown:
    """Individual ability cooldown observation from CoolDownData."""
    spell_id: int
    remaining_cd_ms: int      # +0x14 (uiCoolTime: 0 when ready)
    max_cd_ms: int            # +0x18 (originalMaxCdTime)
    start_time_ms: int        # +0x1c (uiStartTime)
    is_cooling_down: bool     # +0x20 (m_isCoolDown)

    @property
    def is_ready(self) -> bool:
        """Pure factual convenience: true if not on cooldown and remaining ms is 0."""
        return not self.is_cooling_down and self.remaining_cd_ms == 0


@dataclass(frozen=True)
class HeroAbilities:
    """Immutable collection of all observed hero abilities and cast state."""
    active_spell_ptr: int = 0                         # +0x058 (m_pCurSpell)
    is_casting: bool = False                          # True if active_spell_ptr != 0
    cooldowns: Tuple[AbilityCooldown, ...] = field(default_factory=tuple)

    def get_by_spell_id(self, spell_id: int) -> Optional[AbilityCooldown]:
        """Lookup cooldown record by specific spell ID."""
        for cd in self.cooldowns:
            if cd.spell_id == spell_id:
                return cd
        return None


@dataclass(frozen=True)
class ItemSlot:
    """Individual equipment slot observation from LogicEquipInfo."""
    slot_index: int           # 0..5
    item_id: int              # +0x10 (m_iEquipId)
    price: int = 0            # +0x30 (m_iInitPrice)


@dataclass(frozen=True)
class HeroInventory:
    """Immutable collection of all observed hero equipment slots and active items."""
    max_slot_count: int = 6                           # +0x010 (iMaxCnt)
    active_slot_index: int = -1                       # +0x078 (m_UseEquipIndex)
    roam_blessing_count: int = 0                      # +0x074 (m_BuyGankShoeCount)
    items: Tuple[ItemSlot, ...] = field(default_factory=tuple)

    @property
    def item_count(self) -> int:
        """Total number of occupied equipment slots (0..6)."""
        return len(self.items)

    @property
    def has_roam_blessing(self) -> bool:
        """Pure factual convenience: true if roam blessing count >= 1."""
        return self.roam_blessing_count > 0

    @property
    def item_ids(self) -> Tuple[int, ...]:
        """Tuple of active item archetype IDs."""
        return tuple(it.item_id for it in self.items)

    def has_item(self, item_id: int) -> bool:
        """Checks whether a specific item ID is present in the inventory."""
        return any(it.item_id == item_id for it in self.items)

    def get_slot(self, slot_index: int) -> Optional[ItemSlot]:
        """Lookup item slot by index (0..5)."""
        for it in self.items:
            if it.slot_index == slot_index:
                return it
        return None


@dataclass(frozen=True)
class ActiveBuff:
    """Individual temporary buff, debuff, or aura effect from LogicEffect."""
    effect_id: int            # +0x14 (m_ID)
    guid: int = 0             # +0x10 (m_uGuid)
    owner_id: int = 0         # +0x20 (m_uOwnerId)
    source_spell_id: int = 0  # +0x84 (m_iOwnSpellId)
    stack_count: int = 1      # +0x90 (m_uTriggerCount)
    value: int = 0            # +0xf0 (iEffectVal)
    is_finished: bool = False # +0x80 (m_bFinish)
    last_update_time: int = 0 # +0x108 (uLastUpdateTime)


@dataclass(frozen=True)
class HeroBuffs:
    """Immutable collection of all active temporary effects on a hero."""
    buffs: Tuple[ActiveBuff, ...] = field(default_factory=tuple)

    @property
    def count(self) -> int:
        """Total number of active buffs."""
        return len(self.buffs)

    def has_effect(self, effect_id: int) -> bool:
        """Checks whether a specific effect ID is currently active."""
        return any(b.effect_id == effect_id for b in self.buffs)

    def get_by_effect_id(self, effect_id: int) -> Optional[ActiveBuff]:
        """Lookup active buff record by effect ID."""
        for b in self.buffs:
            if b.effect_id == effect_id:
                return b
        return None

    def get_by_spell_id(self, src_spell_id: int) -> Optional[ActiveBuff]:
        """Lookup active buff record by source spell ID."""
        for b in self.buffs:
            if b.source_spell_id == src_spell_id:
                return b
        return None


@dataclass(frozen=True)
class HeroStatusEffects:
    """Decoded crowd control and status effect flags from LogicFighter.m_iStatus (+0x1e4)."""
    raw_mask: int = 0
    is_dizzy: bool = False       # Bit 1 (Stun / Daze)
    is_freeze: bool = False      # Bit 2, 19 (Freeze)
    is_up: bool = False          # Bit 3 (Knockup / Airborne)
    is_controlled: bool = False  # Bit 4 (General CC)
    is_silent: bool = False      # Bit 5 (Silence)
    is_bind: bool = False        # Bit 6, 17 (Immobilize / Root)
    is_feared: bool = False      # Bit 7 (Fear)
    is_taunted: bool = False     # Bit 8 (Taunt)
    is_charmed: bool = False     # Bit 9 (Charm / Temptation)
    is_suppressed: bool = False  # Bit 10 (Suppression)
    is_petrified: bool = False   # Bit 11 (Petrification)
    is_stealthed: bool = False   # Bit 16 (Hide / Concealment)
    is_cc_immune: bool = False   # Bit 23, 30 (CC / Control Immune)

    @classmethod
    def from_mask(cls, mask: int) -> "HeroStatusEffects":
        """Decodes raw 32-bit status mask into proven status flags without evaluation."""
        if not mask:
            return cls()
        return cls(
            raw_mask=mask,
            is_dizzy=bool(mask & (1 << 1)),
            is_freeze=bool((mask & (1 << 2)) or (mask & (1 << 19))),
            is_up=bool(mask & (1 << 3)),
            is_controlled=bool(mask & (1 << 4)),
            is_silent=bool(mask & (1 << 5)),
            is_bind=bool((mask & (1 << 6)) or (mask & (1 << 17))),
            is_feared=bool(mask & (1 << 7)),
            is_taunted=bool(mask & (1 << 8)),
            is_charmed=bool(mask & (1 << 9)),
            is_suppressed=bool(mask & (1 << 10)),
            is_petrified=bool(mask & (1 << 11)),
            is_stealthed=bool(mask & (1 << 16)),
            is_cc_immune=bool((mask & (1 << 23)) or (mask & (1 << 30))),
        )


@dataclass(frozen=True)
class HeroCombatAttributes:
    """Immutable collection of runtime-computed combat statistics from LogicFighter.m_AttrComp (+0x4d8)."""
    physical_attack: int = 0         # ATTR_KIND_PHY_ATT (102) -> RESULT (5)
    magic_power: int = 0             # ATTR_KIND_MAG_ATT (103) -> RESULT (5)
    physical_defense: int = 0        # ATTR_KIND_PHY_SHIELD (106) -> RESULT (5)
    magic_defense: int = 0           # ATTR_KIND_MAG_SHIELD (107) -> RESULT (5)
    movement_speed: float = 0.0      # ATTR_KIND_MOV_SPEED (105) -> RESULT (5)
    attack_speed: float = 0.0        # ATTR_KIND_ATT_SPEED (104) -> RESULT (5)
    attack_range: float = 0.0        # Effective attack range
    cooldown_reduction: float = 0.0  # ATTR_KIND_HERO_COOL (36) -> RESULT (5) %
    crit_rate: float = 0.0           # ATTR_KIND_LUCKY_ATT (30) -> RESULT (5) %
    crit_damage_rate: float = 2.0    # Base crit damage multiplier (2.0 = 200%)
    phys_penetration_flat: int = 0   # ATTR_KIND_PHY_VALUE_THROGH (41) -> RESULT (5)
    phys_penetration_percent: float = 0.0  # ATTR_KIND_PHY_THROUGH (12) -> RESULT (5) %
    mag_penetration_flat: int = 0    # ATTR_KIND_MAG_VALUE_THROGH (42) -> RESULT (5)
    mag_penetration_percent: float = 0.0   # ATTR_KIND_MAG_THROUGH (13) -> RESULT (5) %
    physical_lifesteal: float = 0.0  # ATTR_KIND_COMM_ATTACK_SORB (39) -> RESULT (5) %
    spell_vamp: float = 0.0          # ATTR_KIND_SPELL_SORB (40) -> RESULT (5) %
    hp_regen: float = 0.0            # ATTR_KIND_HP_GROWTH (108) -> RESULT (5)
    mana_regen: float = 0.0          # ATTR_KIND_MP_GROWTH (109) -> RESULT (5)


@dataclass(frozen=True)
class HeroEntity:
    address: int
    hero_id: int              # +0xac (m_ID)
    level: int                # +0xb4 (m_Level: 1..15)
    hp: int                   # +0xc8 (m_Hp)
    hp_max: int               # +0xcc (m_HpMax)
    is_dead: bool             # +0x1d0 (m_bDeath)
    camp: int                 # +0x1dc (1=Blue/Ally, 2=Red/Enemy)
    pos_x: float              # +0x268 (m_dRealPosX)
    pos_y: float              # +0x270 (m_dRealPosY)
    gold: int                 # +0x858 (_totalGold)
    is_bot: bool              # +0xb9a (m_IsRobotPlayer)
    is_local_player: bool     # True if matching the active controller
    distance_to_me: float = 0.0

    # Vitals & Resources (PROVEN - P1-3)
    mp: int = 0                       # +0x108 (m_Mp)
    mp_max: int = 0                   # +0x10c (_MpMax)

    # Active Live Shields (PROVEN - P1-3)
    shield: int = 0                   # +0x0e4 (m_AdditionHp1: Primary Active Shield)
    shield_max: int = 0               # +0x0e8 (m_AdditionHp1Max)
    magic_shield: int = 0             # +0x0f0 (m_AdditionHp2: Secondary Magic Shield)
    magic_shield_max: int = 0         # +0x0f4 (m_AdditionHp2Max)
    mech_armor_hp: int = 0            # +0x0d8 (m_MechArmorHp: Mech Armor HP)

    # Invulnerability & Combat State (PROVEN - P1-3)
    is_invulnerable: bool = False     # +0x720 (m_bCantBeHurt)
    kill_bounty: int = 0              # +0xcf0 (m_KillBounty shutdown bounty)

    # Runtime Combat Attributes (PROVEN - P1-4 LogicFighter.m_AttrComp +0x4d8)
    combat_attributes: HeroCombatAttributes = field(default_factory=HeroCombatAttributes)

    # Active Buffs & Temporary Effects (PROVEN - P1-3)
    buffs: HeroBuffs = field(default_factory=HeroBuffs)

    # Abilities & Cooldowns (PROVEN - P1-1)
    abilities: HeroAbilities = field(default_factory=HeroAbilities)

    # Equipment & Inventory (PROVEN - P1-2)
    inventory: HeroInventory = field(default_factory=HeroInventory)

    # Kinematics & Orientation (PROVEN - P0-4)
    facing_x: float = 0.0            # +0x298 (m_v2FaceDir.x)
    facing_y: float = 0.0            # +0x2a0 (m_v2FaceDir.y)
    move_dir_x: float = 0.0          # +0x288 (_v2MoveDir.x)
    move_dir_y: float = 0.0          # +0x290 (_v2MoveDir.y)
    movement_dest_x: float = 0.0     # +0x2b8 (_v2Dest.x: navigation target X, PARTIALLY_PROVEN)
    movement_dest_y: float = 0.0     # +0x2c0 (_v2Dest.y: navigation target Y, PARTIALLY_PROVEN)
    run_speed: float = 0.0           # +0x750 (m_dCurrentRunSpeed)
    attack_speed: float = 0.0        # +0x758 (m_dCurrentAtkSpeed)

    # Visibility (HYPOTHESIS - requires live validation)
    is_visible: bool = True           # +0x73b (m_bInSightValueStatus: minimap visibility flag)

    # Status & CC flags (PROVEN - P0-2)
    status_mask: int = 0             # +0x1e4 (m_iStatus raw bitmask)
    status_effects: HeroStatusEffects = field(default_factory=HeroStatusEffects)
    status: int = 0                  # Backward compatibility alias for status_mask

    # Target Graph Fields (PROVEN - P0-3)
    face_lock_target_id: int = 0     # +0x370 (m_uFaceLockTargetID)
    attacker_id: int = 0             # +0x560 (m_uAttackerId)
    attacker_ptr: int = 0            # +0x588 (m_Attacker)
    be_attack_timestamp: int = 0     # +0x590 (m_uBeAttackTimestamp)
    attack_timestamp: int = 0        # +0x594 (m_uAttackTimestamp)
    target_enemy_ptr: int = 0        # +0x5a8 (m_pEnemy)
    real_enemy_ptr: int = 0          # +0x5b0 (m_pRealEnemy)
    hate_enemy_ptr: int = 0          # +0x5b8 (m_HateEnemy)
    stare_target_guid: int = 0       # +0x5c0 (m_uStareTargetGUID)

    # Player Metadata & Role Setup (PROVEN - FightPlayerData / RoomData)
    assigned_lane: int = 0           # +0x34 / +0x5c (m_iPos: 1=Gold, 2=Exp, 3=Mid, 4=Jungle, 5=Roam)
    battle_spell_id: int = 0         # +0x64 / +0x78 (m_SummonSkillId: 20100=Flicker, 20200=Retri, etc.)
    emblem_id: int = 0               # +0x68 / +0x84 (runeId: Main Emblem Archetype)
    emblem_level: int = 0            # +0x80 (runeLv: Emblem Level 1..60)
    player_name: str = ""            # +0x40 / +0x50 (_sName: Player IGN string)
    rank_level: int = 0              # +0x128 (uiRankLevel: Rank tier)
    rank_stars: int = 0              # +0x12c (uiPVPRank: Rank star count)
    mythic_points: int = 0           # +0x1d4 (iMythPoint: Mythic points)
    elo_rating: int = 0              # +0x134 (iElo: Hidden MMR)
    respawn_time_ms: int = 0         # +0x580 -> +0x20 (ReliveData.iReliveTime remaining countdown)
    killer_id: int = 0               # +0x580 -> +0x30 (ReliveData.iKillerId killer GUID)

    # Telemetry & Combat metrics (VALIDATED)
    in_battle: bool = False          # +0x21c (m_bInBattle)
    born_pos_x: float = 0.0          # +0x340 (fBornPosX)
    born_pos_y: float = 0.0          # +0x348 (fBornPosY)
    hurt_total_value: float = 0.0    # +0x868 (m_HurtTotalValue)
    hurt_hero_value: float = 0.0     # +0x878 (m_HurtHeroValue)
    hurt_tower_value: float = 0.0    # +0x8b8 (m_HurtTowerValue)
    injured_shield: int = 0          # +0x8c8 (m_iInjuredShield total match metric)
    injured_value: float = 0.0       # +0x8d0 (m_InjuredValue)
    cure_teammate: float = 0.0       # +0x920 (m_CureTeammate)
    kill_tower_times: int = 0        # +0x998 (m_ccsKillTowerTimes)
    last_hit_creep: int = 0          # +0x99c (m_ccsLastHitCreep)
    kill_dragon_times: int = 0       # +0x9a0 (m_ccsKillBigDragon)
    kill_outer_tower: int = 0        # +0x9a8 (m_ccsKillOuterTower)
    kill_inner_tower: int = 0        # +0x9ac (m_ccsKillInnerTower)
    kill_inhibitor_tower: int = 0    # +0x9b0 (m_ccsKillInhibitorTower)

    # Convenience Properties for Direct Combat Access
    @property
    def physical_defense(self) -> int:
        """Convenience property accessing runtime computed physical defense (armor)."""
        return self.combat_attributes.physical_defense

    @property
    def magic_defense(self) -> int:
        """Convenience property accessing runtime computed magic defense (magic resistance)."""
        return self.combat_attributes.magic_defense

    @property
    def physical_attack(self) -> int:
        """Convenience property accessing runtime computed physical attack power."""
        return self.combat_attributes.physical_attack

    @property
    def magic_power(self) -> int:
        """Convenience property accessing runtime computed magic power."""
        return self.combat_attributes.magic_power

    @property
    def cooldown_reduction(self) -> float:
        """Convenience property accessing runtime cooldown reduction fraction."""
        return self.combat_attributes.cooldown_reduction

    @property
    def crit_rate(self) -> float:
        """Convenience property accessing runtime critical strike rate fraction."""
        return self.combat_attributes.crit_rate


@dataclass(frozen=True)
class TowerEntity:
    address: int
    tower_id: int             # +0xac (m_ID)
    tower_type: int           # +0x850 (eTowerType / Config)
    hp: int                   # +0xc8 (m_Hp)
    hp_max: int               # +0xcc (m_HpMax)
    is_dead: bool             # +0x1d0 (m_bDeath)
    camp: int                 # +0x1dc (1=Blue, 2=Red)
    pos_x: float              # +0x268 (m_dRealPosX)
    pos_y: float              # +0x270 (m_dRealPosY)
    tower_index: int = 0      # +0x8f0 (m_TowerIndex)
    senior_pos_id: int = 0    # +0x8f4 (m_SeniorPosID)
    guard_id: int = 0         # +0x8f8 (m_uGuardId)
    eye_range: float = 0.0    # +0x928 (m_DefaultEyeRange)
    attack_range: float = 0.0 # +0x930 (m_fAttackRange)
    distance_to_me: float = 0.0


@dataclass(frozen=True)
class SoldierEntity:
    address: int
    soldier_id: int           # +0xac (m_ID)
    soldier_type: int         # +0x8f0 (m_SoldierType: 1=Melee, 2=Ranged, 3=Siege, 4=Super)
    lane: int                 # +0x900 (m_iPathId: 1=Top, 2=Mid, 3=Bot)
    point_index: int          # +0x904 (m_pointIndex)
    hp: int                   # +0xc8 (m_Hp)
    hp_max: int               # +0xcc (m_HpMax)
    is_dead: bool             # +0x1d0 (m_bDeath)
    camp: int                 # +0x1dc (1=Blue, 2=Red)
    pos_x: float              # +0x268 (m_dRealPosX)
    pos_y: float              # +0x270 (m_dRealPosY)
    stake_soldier: bool = False # +0x908 (m_bStakeSoldier)
    distance_to_me: float = 0.0


@dataclass(frozen=True)
class MonsterEntity:
    address: int
    monster_id: int           # +0xac (m_ID)
    monster_type: int         # +0x850 (m_MonsterType)
    hp: int                   # +0xc8 (m_Hp)
    hp_max: int               # +0xcc (m_HpMax)
    is_dead: bool             # +0x1d0 (m_bDeath)
    camp: int                 # +0x1dc
    pos_x: float              # +0x268 (m_dRealPosX)
    pos_y: float              # +0x270 (m_dRealPosY)
    is_wild: bool = False     # True if LogicWildMonster
    base_money: float = 0.0   # +0x858 (m_BaseMoney)
    money: float = 0.0        # +0x868 (m_Money)
    base_exp: int = 0         # +0x878 (m_BaseExp)
    exp: int = 0              # +0x880 (m_Exp)
    distance_to_me: float = 0.0


@dataclass(frozen=True)
class BulletEntity:
    address: int
    bullet_id: int            # +0x020 (m_Id)
    is_destroy: bool          # +0x018 (m_IsDestory)
    fly_distance: float       # +0x048 (dFlyDistance)
    radius: float             # +0x058 (_dRadius)
    owner_ptr: int = 0        # +0x138 (m_pOwner on LogicDirBullet)
    pos_x: float = 0.0        # +0x100 (_vecCurPos.x)
    pos_y: float = 0.0        # +0x108 (_vecCurPos.y)
    dir_x: float = 0.0        # +0x110 (_vecDir.x)
    dir_y: float = 0.0        # +0x118 (_vecDir.y)
    speed: float = 0.0        # +0x0c8 (_dBulletSpeedForShow)


@dataclass(frozen=True)
class WorldSnapshot:
    timestamp_ns: int
    in_match: bool
    local_player: Optional[HeroEntity]
    allies: Tuple[HeroEntity, ...]
    enemies: Tuple[HeroEntity, ...]
    towers: Tuple[TowerEntity, ...]
    soldiers: Tuple[SoldierEntity, ...]
    monsters: Tuple[MonsterEntity, ...]
    bullets: Tuple[BulletEntity, ...]
    sequence_id: int = 0      # Monotonically incrementing frame sequence index
    frame_time_ms: int = 0    # Authoritative simulation time (+0x19c m_uiFrameTime)
    battle_state: int = 0     # +0x180 (_m_eState: 2=Practice, 6=Ranked/Classic)

    @property
    def blue_nexus(self) -> Optional[TowerEntity]:
        """Direct reference to Blue Base Crystal Nexus (ID 1009, Camp 1)."""
        for t in self.towers:
            if t.tower_id == 1009 or (t.tower_type == 1 and t.camp == 1):
                return t
        return None

    @property
    def red_nexus(self) -> Optional[TowerEntity]:
        """Direct reference to Red Base Crystal Nexus (ID 1010, Camp 2)."""
        for t in self.towers:
            if t.tower_id == 1010 or (t.tower_type == 1 and t.camp == 2):
                return t
        return None

    @property
    def blue_fountain(self) -> Optional[TowerEntity]:
        """Direct reference to Blue Base Fountain (Camp 1)."""
        for t in self.towers:
            if t.camp == 1 and abs(t.pos_x - (-50.2)) < 5.0:
                return t
        return None

    @property
    def red_fountain(self) -> Optional[TowerEntity]:
        """Direct reference to Red Base Fountain (Camp 2)."""
        for t in self.towers:
            if t.camp == 2 and abs(t.pos_x - 50.2) < 5.0:
                return t
        return None

