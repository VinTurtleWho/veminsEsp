package com.vemins.esp.model

import org.json.JSONObject

/**
 * Represents individual ability cooldown observation from LogicSkillComp / CoolDownComp.
 *
 * @property spellId Unique identifier for the skill or spell (e.g. 1810 for Layla S1, 20100 for Flicker).
 * @property slot Numerical slot index (1=Skill 1, 2=Skill 2, 3=Ultimate/Skill 3, 4=Skill 4, 5=Battle Spell).
 * @property remainingCdMs Remaining cooldown time in milliseconds (0 when ready).
 * @property maxCdMs Total maximum cooldown time in milliseconds for the skill.
 * @property isCoolingDown Boolean flag indicating active cooldown state.
 */
data class AbilityInfo(
    val spellId: Int = 0,
    val slot: Int = 0,
    val remainingCdMs: Int = 0,
    val maxCdMs: Int = 0,
    val isCoolingDown: Boolean = false
) {
    val remainingMs: Int get() = remainingCdMs
    val maxMs: Int get() = maxCdMs

    /**
     * Convenience property returning true if the ability is off cooldown and ready for cast.
     */
    val isReady: Boolean
        get() = !isCoolingDown || remainingCdMs <= 50

    /**
     * Cooldown remaining in fractional seconds (e.g. 14.5s).
     */
    val remainingSeconds: Float
        get() = if (isCoolingDown && remainingCdMs > 50) remainingCdMs / 1000.0f else 0.0f

    /**
     * Total cooldown duration in seconds.
     */
    val maxSeconds: Float
        get() = if (maxCdMs > 0) maxCdMs / 1000.0f else 0.0f

    /**
     * Cooldown progress ratio from 0.0 (ready) to 1.0 (just casted).
     */
    val cooldownProgress: Float
        get() = if (maxCdMs > 0 && remainingCdMs > 50 && isCoolingDown) {
            (remainingCdMs.toFloat() / maxCdMs.toFloat()).coerceIn(0.0f, 1.0f)
        } else {
            0.0f
        }

    val progress: Float get() = cooldownProgress

    companion object {
        fun fromJson(json: JSONObject?, slotIndex: Int = 0): AbilityInfo {
            if (json == null) return AbilityInfo(slot = slotIndex)
            val rem = json.optInt("remaining_ms", json.optInt("remaining_cd_ms", 0))
            val max = json.optInt("max_ms", json.optInt("max_cd_ms", 0))
            val isCd = json.optBoolean("is_cooling_down", rem > 50)
            val slot = json.optInt("slot", slotIndex)
            val finalRem = if (isCd && rem > 50) rem else 0
            val finalIsCd = isCd && finalRem > 0
            return AbilityInfo(
                spellId = json.optInt("spell_id", 0),
                slot = slot,
                remainingCdMs = finalRem,
                maxCdMs = max,
                isCoolingDown = finalIsCd
            )
        }
    }

    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("spell_id", spellId)
            put("slot", slot)
            put("remaining_ms", remainingCdMs)
            put("remaining_cd_ms", remainingCdMs)
            put("max_ms", maxCdMs)
            put("max_cd_ms", maxCdMs)
            put("is_cooling_down", isCoolingDown)
        }
    }
}
