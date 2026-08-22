package com.vemins.esp.model

import org.json.JSONObject

/**
 * Immutable entity model representing lane minion soldiers.
 *
 * Backed by LogicSoldier records from m_SoldierList (+0x128).
 */
data class SoldierEntity(
    val address: Long = 0L,
    val soldierId: Int = 0,
    val soldierType: Int = 0,
    val lane: Int = 0,
    val pointIndex: Int = 0,
    val hp: Int = 0,
    val hpMax: Int = 0,
    val isDead: Boolean = false,
    val camp: Int = 0,
    val posX: Float = 0.0f,
    val posY: Float = 0.0f,
    var distanceToMe: Float = 0.0f
) {
    /**
     * Normalized health percentage from 0.0f to 1.0f.
     */
    val hpPercent: Float
        get() = if (hpMax > 0) (hp.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 1.0f) else 0.0f

    /**
     * True if minion is a high-value siege cannon or super minion.
     */
    val isSiegeOrSuper: Boolean
        get() = soldierType == 3 || soldierType == 4

    val isEnemy: Boolean
        get() = camp != 1

    companion object {
        fun fromJson(json: JSONObject?): SoldierEntity {
            if (json == null) return SoldierEntity()
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
            return SoldierEntity(
                address = addr,
                soldierId = json.optInt("soldier_id", json.optInt("id", 0)),
                soldierType = json.optInt("soldier_type", 0),
                lane = json.optInt("lane", 0),
                pointIndex = json.optInt("point_index", 0),
                hp = json.optInt("hp", 0),
                hpMax = json.optInt("hp_max", json.optInt("max_hp", 0)),
                isDead = json.optBoolean("is_dead", json.optBoolean("dead", false)),
                camp = json.optInt("camp", json.optInt("team", 0)),
                posX = json.optDouble("pos_x", json.optDouble("x", 0.0)).toFloat(),
                posY = json.optDouble("pos_y", json.optDouble("y", 0.0)).toFloat(),
                distanceToMe = json.optDouble("distance_to_me", 0.0).toFloat()
            )
        }
    }

    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("address", "0x${java.lang.Long.toHexString(address)}")
            put("soldier_id", soldierId)
            put("id", soldierId)
            put("soldier_type", soldierType)
            put("lane", lane)
            put("point_index", pointIndex)
            put("hp", hp)
            put("hp_max", hpMax)
            put("max_hp", hpMax)
            put("is_dead", isDead)
            put("camp", camp)
            put("team", camp)
            put("pos_x", posX.toDouble())
            put("pos_y", posY.toDouble())
            put("distance_to_me", distanceToMe.toDouble())
        }
    }
}
