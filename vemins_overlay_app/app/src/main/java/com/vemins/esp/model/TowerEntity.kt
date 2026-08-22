package com.vemins.esp.model

import org.json.JSONObject

/**
 * Defensive Turret / Tower entity.
 *
 * @property address Memory address in target process.
 * @property towerId Tower identifier.
 * @property camp Camp affiliation (1 = Blue/Camp A, 2 = Red/Camp B).
 * @property hp Current hitpoints.
 * @property hpMax Maximum hitpoints.
 * @property isDead Boolean death flag.
 * @property posX World X coordinate.
 * @property posY World Y coordinate.
 * @property distanceToMe Euclidean distance in meters from the local player.
 */
data class TowerEntity(
    val address: Long = 0L,
    val towerId: Int = 0,
    val camp: Int = 0,
    val hp: Int = 0,
    val hpMax: Int = 0,
    val isDead: Boolean = false,
    val posX: Float = 0.0f,
    val posY: Float = 0.0f,
    val distanceToMe: Float = 0.0f
) {
    val hpPercent: Float
        get() = if (hpMax > 0) (hp.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 1.0f) else 0.0f

    val isEnemy: Boolean
        get() = camp != 1

    companion object {
        fun fromJson(json: JSONObject?): TowerEntity {
            if (json == null) return TowerEntity()
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
            return TowerEntity(
                address = addr,
                towerId = json.optInt("tower_id", json.optInt("id", 0)),
                camp = json.optInt("camp", json.optInt("team", 0)),
                hp = json.optInt("hp", 0),
                hpMax = json.optInt("hp_max", json.optInt("max_hp", 0)),
                isDead = json.optBoolean("is_dead", json.optBoolean("dead", false)),
                posX = json.optDouble("pos_x", json.optDouble("x", 0.0)).toFloat(),
                posY = json.optDouble("pos_y", json.optDouble("y", 0.0)).toFloat(),
                distanceToMe = json.optDouble("distance_to_me", 0.0).toFloat()
            )
        }
    }

    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("address", "0x${java.lang.Long.toHexString(address)}")
            put("tower_id", towerId)
            put("id", towerId)
            put("camp", camp)
            put("team", camp)
            put("hp", hp)
            put("hp_max", hpMax)
            put("max_hp", hpMax)
            put("is_dead", isDead)
            put("pos_x", posX.toDouble())
            put("pos_y", posY.toDouble())
            put("distance_to_me", distanceToMe.toDouble())
        }
    }
}
