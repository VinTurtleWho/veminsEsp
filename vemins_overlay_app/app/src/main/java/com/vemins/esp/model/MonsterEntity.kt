package com.vemins.esp.model

import org.json.JSONObject

/**
 * Immutable entity model representing jungle creeps, monsters, and epic bosses.
 *
 * Backed by LogicMonster records from m_dicMonsterLogic (+0x0b0).
 */
data class MonsterEntity(
    val address: Long = 0L,
    val monsterId: Int = 0,
    val monsterType: Int = 0,
    val hp: Int = 0,
    val hpMax: Int = 0,
    val isDead: Boolean = false,
    val camp: Int = 0,
    val posX: Float = 0.0f,
    val posY: Float = 0.0f,
    val isWild: Boolean = true,
    var distanceToMe: Float = 0.0f
) {
    /**
     * Normalized health percentage from 0.0f to 1.0f.
     */
    val hpPercent: Float
        get() = if (hpMax > 0) (hp.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 1.0f) else 0.0f

    /**
     * True if entity is the Lord boss (ID 51298 or near river center @ (0.4, 20.5) / (-0.4, -20.5)).
     */
    val isLord: Boolean
        get() = monsterId == 51298 || (hpMax > 25000)

    /**
     * True if entity is the Turtle boss (ID 51312 or hpMax in 12k-20k range near river).
     */
    val isTurtle: Boolean
        get() = monsterId == 51312 || (hpMax in 12000..25000 && !isLord)

    /**
     * True if entity is Blue Buff (Statue / Serpent, ID 51248).
     */
    val isBlueBuff: Boolean
        get() = monsterId == 51248 || (monsterType == 2083)

    /**
     * True if entity is Red Buff (Fiend / Molten, ID 51346).
     */
    val isRedBuff: Boolean
        get() = monsterId == 51346 || (monsterType == 2081)

    /**
     * True if this is a primary epic objective or buff (Lord, Turtle, Blue/Red Buff).
     */
    val isHighPriorityObjective: Boolean
        get() = isLord || isTurtle || isBlueBuff || isRedBuff

    companion object {
        fun fromJson(json: JSONObject?): MonsterEntity {
            if (json == null) return MonsterEntity()
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
            val hp = json.optInt("hp", 0)
            val hpMax = json.optInt("hp_max", json.optInt("max_hp", 0))
            val isDead = json.optBoolean("is_dead", if (json.has("is_alive")) !json.optBoolean("is_alive", true) else (hp <= 0 && json.has("hp")))
            return MonsterEntity(
                address = addr,
                monsterId = json.optInt("monster_id", json.optInt("id", 0)),
                monsterType = json.optInt("monster_type", 0),
                hp = hp,
                hpMax = hpMax,
                isDead = isDead,
                camp = json.optInt("camp", json.optInt("team", 0)),
                posX = json.optDouble("pos_x", json.optDouble("x", 0.0)).toFloat(),
                posY = json.optDouble("pos_y", json.optDouble("y", 0.0)).toFloat(),
                isWild = json.optBoolean("is_wild", true),
                distanceToMe = json.optDouble("distance_to_me", 0.0).toFloat()
            )
        }
    }

    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("address", "0x${java.lang.Long.toHexString(address)}")
            put("monster_id", monsterId)
            put("monster_type", monsterType)
            put("hp", hp)
            put("hp_max", hpMax)
            put("is_dead", isDead)
            put("camp", camp)
            put("pos_x", posX.toDouble())
            put("pos_y", posY.toDouble())
            put("is_wild", isWild)
            put("distance_to_me", distanceToMe.toDouble())
        }
    }
}
