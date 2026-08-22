package com.vemins.esp.model

import org.json.JSONArray
import org.json.JSONObject

/**
 * Comprehensive Snapshot of a single live game frame received from Telemetry Socket.
 */
data class FrameSnapshot(
    val timestampNs: Long = System.nanoTime(),
    val inMatch: Boolean = false,
    val battleState: Int = 0,
    val frameTimeMs: Long = 0L,
    val pid: Int = 0,
    val liblogicBase: Long = 0L,
    val libcsharpBase: Long = 0L,
    val status: String = "ok",
    val version: String = "",
    val buildHash: String = "",
    val localPlayer: HeroEntity? = null,
    val enemies: List<HeroEntity> = emptyList(),
    val allies: List<HeroEntity> = emptyList(),
    val soldiers: List<SoldierEntity> = emptyList(),
    val monsters: List<MonsterEntity> = emptyList(),
    val towers: List<TowerEntity> = emptyList(),
    val rawJson: String? = null
) {
    val totalEntitiesCount: Int
        get() = (if (localPlayer != null) 1 else 0) +
                enemies.size + allies.size +
                soldiers.size + monsters.size + towers.size

    val isGameAttached: Boolean
        get() = pid > 0 && liblogicBase > 0L

    val isValid: Boolean
        get() = inMatch || isGameAttached || enemies.isNotEmpty()

    companion object {
        @JvmField
        val EMPTY = empty()

        /**
         * Creates an empty/offline snapshot.
         */
        fun empty(status: String = "disconnected"): FrameSnapshot {
            return FrameSnapshot(
                timestampNs = System.nanoTime(),
                inMatch = false,
                status = status
            )
        }

        /**
         * Parses a JSON string or line received over the socket.
         */
        fun parse(jsonString: String): FrameSnapshot {
            return try {
                val json = JSONObject(jsonString)
                fromJson(json, jsonString)
            } catch (e: Exception) {
                FrameSnapshot(
                    timestampNs = System.nanoTime(),
                    inMatch = false,
                    status = "parse_error: ${e.message}",
                    rawJson = jsonString
                )
            }
        }

        /**
         * Converts a parsed JSONObject into a structured FrameSnapshot.
         */
        fun fromJson(json: JSONObject, rawSource: String? = null): FrameSnapshot {
            val status = json.optString("status", "ok")
            val pid = json.optInt("pid", 0)

            // Parse hex base addresses
            val liblogicRaw = json.opt("liblogic_base")
            val liblogicBase = parseHexOrLong(liblogicRaw)

            val libcsharpRaw = json.opt("libcsharp_base")
            val libcsharpBase = parseHexOrLong(libcsharpRaw)

            val version = json.optString("version", "")
            val buildHash = json.optString("build_hash", "")
            val inMatch = json.optBoolean("in_match", pid > 0)
            val battleState = json.optInt("battle_state", 0)
            val frameTimeMs = json.optLong("frame_time_ms", 0L)
            val timestampNs = json.optLong("timestamp_ns", System.nanoTime())

            // Local Hero
            val localHeroObj = json.optJSONObject("local_player")
            val localCamp = localHeroObj?.optInt("camp", localHeroObj.optInt("team", 1)) ?: 1
            val localHero = localHeroObj?.let { HeroEntity.fromJson(it, isLocal = true, localCamp = localCamp) }

            // Enemies
            val enemiesList = mutableListOf<HeroEntity>()
            val enemiesArr = json.optJSONArray("enemies")
            if (enemiesArr != null) {
                for (i in 0 until enemiesArr.length()) {
                    val heroObj = enemiesArr.optJSONObject(i)
                    if (heroObj != null) {
                        enemiesList.add(HeroEntity.fromJson(heroObj, isLocal = false, localCamp = localCamp))
                    }
                }
            }

            // Allies
            val alliesList = mutableListOf<HeroEntity>()
            val alliesArr = json.optJSONArray("allies")
            if (alliesArr != null) {
                for (i in 0 until alliesArr.length()) {
                    val heroObj = alliesArr.optJSONObject(i)
                    if (heroObj != null) {
                        alliesList.add(HeroEntity.fromJson(heroObj, isLocal = false, localCamp = localCamp))
                    }
                }
            }

            // Minions (supports "soldiers" or "minions")
            val soldiersList = mutableListOf<SoldierEntity>()
            val soldiersArr = json.optJSONArray("soldiers") ?: json.optJSONArray("minions")
            if (soldiersArr != null) {
                for (i in 0 until soldiersArr.length()) {
                    val sObj = soldiersArr.optJSONObject(i)
                    if (sObj != null) {
                        soldiersList.add(SoldierEntity.fromJson(sObj))
                    }
                }
            }

            // Monsters
            val monstersList = mutableListOf<MonsterEntity>()
            val monstersArr = json.optJSONArray("monsters")
            if (monstersArr != null) {
                for (i in 0 until monstersArr.length()) {
                    val mObj = monstersArr.optJSONObject(i)
                    if (mObj != null) {
                        monstersList.add(MonsterEntity.fromJson(mObj))
                    }
                }
            }

            // Towers
            val towersList = mutableListOf<TowerEntity>()
            val towersArr = json.optJSONArray("towers")
            if (towersArr != null) {
                for (i in 0 until towersArr.length()) {
                    val tObj = towersArr.optJSONObject(i)
                    if (tObj != null) {
                        towersList.add(TowerEntity.fromJson(tObj))
                    }
                }
            }

            return FrameSnapshot(
                timestampNs = timestampNs,
                inMatch = inMatch,
                battleState = battleState,
                frameTimeMs = frameTimeMs,
                pid = pid,
                liblogicBase = liblogicBase,
                libcsharpBase = libcsharpBase,
                status = status,
                version = version,
                buildHash = buildHash,
                localPlayer = localHero,
                enemies = enemiesList,
                allies = alliesList,
                soldiers = soldiersList,
                monsters = monstersList,
                towers = towersList,
                rawJson = rawSource
            )
        }

        private fun parseHexOrLong(value: Any?): Long {
            return when (value) {
                is Number -> value.toLong()
                is String -> {
                    val trimmed = value.trim()
                    if (trimmed.startsWith("0x", ignoreCase = true)) {
                        trimmed.substring(2).toLongOrNull(16) ?: 0L
                    } else {
                        trimmed.toLongOrNull() ?: 0L
                    }
                }
                else -> 0L
            }
        }
    }

    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("timestamp_ns", timestampNs)
            put("in_match", inMatch)
            put("battle_state", battleState)
            put("frame_time_ms", frameTimeMs)
            put("pid", pid)
            put("liblogic_base", "0x${java.lang.Long.toHexString(liblogicBase)}")
            put("libcsharp_base", "0x${java.lang.Long.toHexString(libcsharpBase)}")
            put("status", status)
            put("version", version)
            put("build_hash", buildHash)

            localPlayer?.let { put("local_player", it.toJson()) }

            val enemiesArr = JSONArray()
            enemies.forEach { enemiesArr.put(it.toJson()) }
            put("enemies", enemiesArr)

            val alliesArr = JSONArray()
            allies.forEach { alliesArr.put(it.toJson()) }
            put("allies", alliesArr)

            val soldiersArr = JSONArray()
            soldiers.forEach { soldiersArr.put(it.toJson()) }
            put("soldiers", soldiersArr)

            val monstersArr = JSONArray()
            monsters.forEach { monstersArr.put(it.toJson()) }
            put("monsters", monstersArr)

            val towersArr = JSONArray()
            towers.forEach { towersArr.put(it.toJson()) }
            put("towers", towersArr)
        }
    }
}
