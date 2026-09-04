package com.vemins.esp.model

import org.json.JSONArray
import org.json.JSONObject

/**
 * Combat attributes for a hero entity.
 */
data class CombatAttributes(
    val physicalAttack: Int = 0,
    val magicPower: Int = 0,
    val physicalDefense: Int = 0,
    val magicDefense: Int = 0,
    val cooldownReduction: Float = 0.0f,
    val critRate: Float = 0.0f,
    val physPenetrationFlat: Int = 0,
    val physPenetrationPercent: Float = 0.0f,
    val magPenetrationFlat: Int = 0,
    val magPenetrationPercent: Float = 0.0f,
    val physicalLifesteal: Float = 0.0f,
    val spellVamp: Float = 0.0f
) {
    companion object {
        fun fromJson(json: JSONObject?): CombatAttributes {
            if (json == null) return CombatAttributes()
            return CombatAttributes(
                physicalAttack = json.optInt("physical_attack", 0),
                magicPower = json.optInt("magic_power", 0),
                physicalDefense = json.optInt("physical_defense", 0),
                magicDefense = json.optInt("magic_defense", 0),
                cooldownReduction = json.optDouble("cooldown_reduction", 0.0).toFloat(),
                critRate = json.optDouble("crit_rate", 0.0).toFloat(),
                physPenetrationFlat = json.optInt("phys_penetration_flat", 0),
                physPenetrationPercent = json.optDouble("phys_penetration_percent", 0.0).toFloat(),
                magPenetrationFlat = json.optInt("mag_penetration_flat", 0),
                magPenetrationPercent = json.optDouble("mag_penetration_percent", 0.0).toFloat(),
                physicalLifesteal = json.optDouble("physical_lifesteal", 0.0).toFloat(),
                spellVamp = json.optDouble("spell_vamp", 0.0).toFloat()
            )
        }
    }

    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("physical_attack", physicalAttack)
            put("magic_power", magicPower)
            put("physical_defense", physicalDefense)
            put("magic_defense", magicDefense)
            put("cooldown_reduction", cooldownReduction.toDouble())
            put("crit_rate", critRate.toDouble())
            put("phys_penetration_flat", physPenetrationFlat)
            put("phys_penetration_percent", physPenetrationPercent.toDouble())
            put("mag_penetration_flat", magPenetrationFlat)
            put("mag_penetration_percent", magPenetrationPercent.toDouble())
            put("physical_lifesteal", physicalLifesteal.toDouble())
            put("spell_vamp", spellVamp.toDouble())
        }
    }
}

/**
 * Inventory item equipped by a hero.
 */
data class InventoryItem(
    val slot: Int = 0,
    val itemId: Int = 0
) {
    companion object {
        fun fromJson(json: JSONObject?): InventoryItem {
            if (json == null) return InventoryItem()
            return InventoryItem(
                slot = json.optInt("slot", 0),
                itemId = json.optInt("item_id", 0)
            )
        }
    }

    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("slot", slot)
            put("item_id", itemId)
        }
    }
}

/**
 * Immutable entity model representing a Hero in the match (Local Player, Ally, or Enemy).
 *
 * Backed by authoritative offsets from LogicPlayer / LogicFighter.
 */
data class HeroEntity(
    val address: Long = 0L,
    val heroId: Int = 0,
    val level: Int = 1,
    val hp: Int = 0,
    val hpMax: Int = 0,
    val mp: Int = 0,
    val mpMax: Int = 0,
    val shield: Int = 0,
    val magicShield: Int = 0,
    val isDead: Boolean = false,
    val camp: Int = 0,
    val posX: Float = 0.0f,
    val posY: Float = 0.0f,
    val facingX: Float = 0.0f,
    val facingY: Float = 0.0f,
    val moveDirX: Float = 0.0f,
    val moveDirY: Float = 0.0f,
    val runSpeed: Float = 0.0f,
    val attackSpeed: Float = 0.0f,
    val gold: Int = 0,
    val isLocalPlayer: Boolean = false,
    val isAlly: Boolean = false,
    val isBot: Boolean = false,
    val inBattle: Boolean = false,
    var distanceToMe: Float = 0.0f,
    val abilities: List<AbilityInfo> = emptyList(),
    val combatAttributes: CombatAttributes? = null,
    val inventory: List<InventoryItem> = emptyList()
) {
    /**
     * Normalized health percentage from 0.0f to 1.0f.
     */
    val hpPercent: Float
        get() = if (hpMax > 0) (hp.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 1.0f) else 0.0f

    val mpPercent: Float
        get() = if (mpMax > 0) (mp.toFloat() / mpMax.toFloat()).coerceIn(0.0f, 1.0f) else 0.0f

    /**
     * Shield proportion relative to max HP.
     */
    val shieldPercent: Float
        get() = if (hpMax > 0 && shield > 0) (shield.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 2.0f) else 0.0f

    /**
     * Magic shield proportion relative to max HP.
     */
    val magicShieldPercent: Float
        get() = if (hpMax > 0 && magicShield > 0) (magicShield.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 2.0f) else 0.0f

    /**
     * Total effective health including active physical and magic shields.
     */
    val effectiveHp: Int
        get() = hp + shield + magicShield

    val isEnemy: Boolean
        get() = !isLocalPlayer && !isAlly

    /**
     * Determines whether this hero archetype possesses 4 core active abilities rather than the standard 3.
     * Detected dynamically from telemetry observations (slot 4 exists) or canonical hero ID table.
     */
    fun hasFourSkills(): Boolean {
        if (abilities.any { it.slot == 4 || it.spellId % 100 == 40 || it.spellId == heroId * 100 + 40 }) return true
        return when (heroId) {
            50, 68, 101, 105, 115, 116, 126, 127 -> true
            else -> false
        }
    }

    /**
     * Look up ability info by slot index (1=S1, 2=S2, 3=S3/Ult, 4=S4/Ult, 5=Battle Spell).
     */
    fun getAbility(slot: Int): AbilityInfo? {
        val bySlot = abilities.firstOrNull { it.slot == slot }
        if (bySlot != null) return bySlot

        val fourSkills = hasFourSkills()
        return when (slot) {
            1 -> abilities.firstOrNull { it.spellId % 100 == 10 || it.spellId == heroId * 100 + 10 } ?: abilities.getOrNull(0)
            2 -> abilities.firstOrNull { it.spellId % 100 == 20 || it.spellId == heroId * 100 + 20 } ?: abilities.getOrNull(1)
            3 -> {
                abilities.firstOrNull { it.spellId % 100 == 30 || it.spellId == heroId * 100 + 30 } ?: abilities.getOrNull(2)
            }
            4 -> {
                if (fourSkills) {
                    abilities.firstOrNull { it.spellId % 100 == 40 || it.spellId == heroId * 100 + 40 } ?: abilities.getOrNull(3)
                } else null
            }
            5 -> abilities.firstOrNull { it.slot == 5 || (it.spellId in 20000..299999) } ?: abilities.lastOrNull()
            else -> null
        }
    }

    /**
     * Direct reference to Ultimate skill (slot 4 for 4-skill heroes, slot 3 for 3-skill heroes).
     */
    val ultimateAbility: AbilityInfo?
        get() {
            val fourSkills = hasFourSkills()
            val targetSlot = if (fourSkills) 4 else 3
            return abilities.firstOrNull { it.slot == targetSlot }
                ?: if (fourSkills) {
                    abilities.firstOrNull { it.spellId % 100 == 40 || it.spellId == heroId * 100 + 40 }
                        ?: abilities.firstOrNull { it.slot == 3 || it.spellId % 100 == 30 }
                } else {
                    abilities.firstOrNull { it.spellId % 100 == 30 || it.spellId == heroId * 100 + 30 }
                        ?: abilities.firstOrNull { it.slot == 3 }
                }
                ?: abilities.firstOrNull { it.spellId !in 20000..299999 && (it.spellId % 100 != 10 && it.spellId % 100 != 20) && it.spellId > 0 }
        }

    /**
     * Returns true if ultimate ability is ready to fire.
     */
    val isUltReady: Boolean
        get() = ultimateAbility?.isReady ?: true

    /**
     * Cooldown remaining on ultimate in seconds (0.0 if ready).
     */
    val ultCooldownSeconds: Float
        get() = ultimateAbility?.remainingSeconds ?: 0.0f

    /**
     * Direct reference to Battle Spell (slot 5 or spell IDs in battle spell range e.g. 20100..299999).
     */
    val battleSpell: AbilityInfo?
        get() = abilities.firstOrNull { it.slot == 5 || (it.spellId in 20000..299999) }

    companion object {
        fun fromJson(json: JSONObject?, isLocal: Boolean = false, localCamp: Int = 1): HeroEntity {
            if (json == null) return HeroEntity()

            val addrRaw = json.opt("address")
            val addr = when (addrRaw) {
                is Number -> addrRaw.toLong()
                is String -> if (addrRaw.startsWith("0x", ignoreCase = true)) {
                    addrRaw.substring(2).toLongOrNull(16) ?: 0L
                } else {
                    addrRaw.toLongOrNull() ?: 0L
                }
                else -> 0L
            }

            val camp = json.optInt("camp", json.optInt("team", 0))
            val isLocalResolved = json.optBoolean("is_local_player", isLocal)
            val isAllyResolved = json.optBoolean("is_ally", !isLocalResolved && camp == localCamp)

            val abilitiesList = mutableListOf<AbilityInfo>()
            val absArr = json.optJSONArray("abilities")
            if (absArr != null) {
                for (i in 0 until absArr.length()) {
                    val abObj = absArr.optJSONObject(i)
                    if (abObj != null) {
                        abilitiesList.add(AbilityInfo.fromJson(abObj, i + 1))
                    }
                }
            }

            val invList = mutableListOf<InventoryItem>()
            val invArr = json.optJSONArray("inventory")
            if (invArr != null) {
                for (i in 0 until invArr.length()) {
                    val itemObj = invArr.optJSONObject(i)
                    if (itemObj != null) {
                        invList.add(InventoryItem.fromJson(itemObj))
                    }
                }
            }

            val combatAttrObj = json.optJSONObject("combat_attributes")
            val combatAttr = combatAttrObj?.let { CombatAttributes.fromJson(it) }

            val hp = json.optInt("hp", 0)
            val hpMax = json.optInt("hp_max", json.optInt("max_hp", 0))
            val isDead = json.optBoolean("is_dead", if (json.has("is_alive")) !json.optBoolean("is_alive", true) else (hp <= 0 && json.has("hp")))

            return HeroEntity(
                address = addr,
                heroId = json.optInt("hero_id", json.optInt("id", 0)),
                level = json.optInt("level", 1),
                hp = hp,
                hpMax = hpMax,
                mp = json.optInt("mp", 0),
                mpMax = json.optInt("mp_max", json.optInt("max_mp", 0)),
                shield = json.optInt("shield", 0),
                magicShield = json.optInt("magic_shield", 0),
                isDead = isDead,
                camp = camp,
                posX = json.optDouble("pos_x", json.optDouble("x", 0.0)).toFloat(),
                posY = json.optDouble("pos_y", json.optDouble("y", 0.0)).toFloat(),
                facingX = json.optDouble("facing_x", 0.0).toFloat(),
                facingY = json.optDouble("facing_y", 0.0).toFloat(),
                moveDirX = json.optDouble("move_dir_x", json.optDouble("facing_x", 0.0)).toFloat(),
                moveDirY = json.optDouble("move_dir_y", json.optDouble("facing_y", 0.0)).toFloat(),
                runSpeed = json.optDouble("run_speed", 0.0).toFloat(),
                attackSpeed = json.optDouble("attack_speed", 0.0).toFloat(),
                gold = json.optInt("gold", 0),
                isLocalPlayer = isLocalResolved,
                isAlly = isAllyResolved,
                isBot = json.optBoolean("is_bot", false),
                inBattle = json.optBoolean("in_battle", false),
                distanceToMe = json.optDouble("distance_to_me", 0.0).toFloat(),
                abilities = abilitiesList,
                combatAttributes = combatAttr,
                inventory = invList
            )
        }
    }

    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("address", "0x${java.lang.Long.toHexString(address)}")
            put("hero_id", heroId)
            put("level", level)
            put("hp", hp)
            put("hp_max", hpMax)
            put("mp", mp)
            put("mp_max", mpMax)
            put("shield", shield)
            put("magic_shield", magicShield)
            put("is_dead", isDead)
            put("camp", camp)
            put("pos_x", posX.toDouble())
            put("pos_y", posY.toDouble())
            put("facing_x", facingX.toDouble())
            put("facing_y", facingY.toDouble())
            put("move_dir_x", moveDirX.toDouble())
            put("move_dir_y", moveDirY.toDouble())
            put("run_speed", runSpeed.toDouble())
            put("attack_speed", attackSpeed.toDouble())
            put("gold", gold)
            put("is_local_player", isLocalPlayer)
            put("is_ally", isAlly)
            put("is_bot", isBot)
            put("in_battle", inBattle)
            put("distance_to_me", distanceToMe.toDouble())

            val abArr = JSONArray()
            abilities.forEach { abArr.put(it.toJson()) }
            put("abilities", abArr)

            combatAttributes?.let { put("combat_attributes", it.toJson()) }

            val invArr = JSONArray()
            inventory.forEach { invArr.put(it.toJson()) }
            put("inventory", invArr)
        }
    }
}
