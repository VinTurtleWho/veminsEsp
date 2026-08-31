package com.vemins.esp.model

import com.vemins.esp.engine.VeminsNativeEngine
import java.nio.ByteBuffer

/**
 * High-Speed Zero-Allocation Binary Snapshot Unpacker.
 *
 * Reads directly from off-heap [ByteBuffer] at fixed byte offsets into a pre-allocated [MutableFrameSnapshot].
 * Executes in < 15 microseconds per snapshot with 0 bytes heap allocation.
 */
object BinarySnapshotReader {
    private const val EXPECTED_MAGIC = 0x564D4E53 // 'VMNS'

    // Offsets within Header (64 bytes)
    private const val OFFSET_MAGIC = 0
    private const val OFFSET_VERSION = 4
    private const val OFFSET_TIMESTAMP_NS = 8
    private const val OFFSET_FRAME_INDEX = 16
    private const val OFFSET_PID = 20
    private const val OFFSET_LIBCSHARP_BASE = 24
    private const val OFFSET_LIBLOGIC_BASE = 32
    private const val OFFSET_IN_MATCH = 40
    private const val OFFSET_BATTLE_STATE = 41
    private const val OFFSET_LOCAL_CAMP = 44
    private const val OFFSET_FRAME_TIME_MS = 48
    private const val OFFSET_READ_LATENCY_MS = 52
    private const val OFFSET_HERO_COUNT = 56
    private const val OFFSET_SOLDIER_COUNT = 57
    private const val OFFSET_MONSTER_COUNT = 58
    private const val OFFSET_TOWER_COUNT = 59

    // Payload Block Offsets
    private const val OFFSET_HEROES = 64
    private const val HERO_STRIDE = 240
    private const val MAX_HEROES = 10

    private const val OFFSET_SOLDIERS = OFFSET_HEROES + (MAX_HEROES * HERO_STRIDE) // 64 + 2400 = 2464
    private const val SOLDIER_STRIDE = 44
    private const val MAX_SOLDIERS = 32

    private const val OFFSET_MONSTERS = OFFSET_SOLDIERS + (MAX_SOLDIERS * SOLDIER_STRIDE) // 2464 + 1408 = 3872
    private const val MONSTER_STRIDE = 44
    private const val MAX_MONSTERS = 32

    private const val OFFSET_TOWERS = OFFSET_MONSTERS + (MAX_MONSTERS * MONSTER_STRIDE) // 3872 + 1408 = 5280
    private const val TOWER_STRIDE = 40
    private const val MAX_TOWERS = 22

    /**
     * Unpacks the direct buffer into [target].
     * @return true if valid frame unpacked, false if magic check or buffer underflow failed.
     */
    fun unpack(buffer: ByteBuffer, target: MutableFrameSnapshot): Boolean {
        if (buffer.capacity() < VeminsNativeEngine.SNAPSHOT_BUFFER_SIZE) {
            return false
        }

        val magic = buffer.getInt(OFFSET_MAGIC)
        if (magic != EXPECTED_MAGIC) {
            return false
        }

        target.magic = magic
        target.version = buffer.getInt(OFFSET_VERSION)
        target.timestampNs = buffer.getLong(OFFSET_TIMESTAMP_NS)
        target.frameIndex = buffer.getInt(OFFSET_FRAME_INDEX)
        target.pid = buffer.getInt(OFFSET_PID)
        target.libcsharpBase = buffer.getLong(OFFSET_LIBCSHARP_BASE)
        target.liblogicBase = buffer.getLong(OFFSET_LIBLOGIC_BASE)
        target.inMatch = buffer.get(OFFSET_IN_MATCH).toInt() != 0
        target.battleState = buffer.get(OFFSET_BATTLE_STATE).toInt() and 0xFF
        target.localCamp = buffer.getInt(OFFSET_LOCAL_CAMP)
        target.frameTimeMs = buffer.getInt(OFFSET_FRAME_TIME_MS)
        target.readLatencyMs = buffer.getFloat(OFFSET_READ_LATENCY_MS)

        val rawHeroCount = buffer.get(OFFSET_HERO_COUNT).toInt() and 0xFF
        val rawSoldierCount = buffer.get(OFFSET_SOLDIER_COUNT).toInt() and 0xFF
        val rawMonsterCount = buffer.get(OFFSET_MONSTER_COUNT).toInt() and 0xFF
        val rawTowerCount = buffer.get(OFFSET_TOWER_COUNT).toInt() and 0xFF

        target.heroCount = rawHeroCount.coerceIn(0, MAX_HEROES)
        target.soldierCount = rawSoldierCount.coerceIn(0, MAX_SOLDIERS)
        target.monsterCount = rawMonsterCount.coerceIn(0, MAX_MONSTERS)
        target.towerCount = rawTowerCount.coerceIn(0, MAX_TOWERS)
        target.localHeroIndex = -1

        // 1. Unpack Heroes
        for (i in 0 until target.heroCount) {
            val base = OFFSET_HEROES + (i * HERO_STRIDE)
            val hero = target.heroes[i]

            hero.address = buffer.getLong(base)
            hero.heroId = buffer.getInt(base + 8)
            hero.level = buffer.getInt(base + 12)
            hero.hp = buffer.getInt(base + 16)
            hero.hpMax = buffer.getInt(base + 20)
            hero.mp = buffer.getInt(base + 24)
            hero.mpMax = buffer.getInt(base + 28)
            hero.shield = buffer.getInt(base + 32)
            hero.magicShield = buffer.getInt(base + 36)
            hero.camp = buffer.getInt(base + 40)
            hero.isDead = buffer.get(base + 44).toInt() != 0
            hero.isLocalPlayer = buffer.get(base + 45).toInt() != 0
            hero.isInBattle = buffer.get(base + 46).toInt() != 0
            hero.posX = buffer.getFloat(base + 48)
            hero.posY = buffer.getFloat(base + 52)
            hero.facingX = buffer.getFloat(base + 56)
            hero.facingY = buffer.getFloat(base + 60)
            hero.moveDirX = buffer.getFloat(base + 64)
            hero.moveDirY = buffer.getFloat(base + 68)
            hero.runSpeed = buffer.getFloat(base + 72)
            hero.attackSpeed = buffer.getFloat(base + 76)
            hero.gold = buffer.getInt(base + 80)
            hero.statusMask = buffer.getInt(base + 84)
            hero.faceLockId = buffer.getInt(base + 88)

            // Items (6x int32)
            val itemBase = base + 92
            for (itemIdx in 0..5) {
                hero.itemIds[itemIdx] = buffer.getInt(itemBase + (itemIdx * 4))
            }

            val rawAbCount = buffer.get(base + 116).toInt() and 0xFF
            hero.abilityCount = rawAbCount.coerceIn(0, 6)

            // Abilities (6x AbilityBinary @ 20 bytes each)
            val abBase = base + 120
            for (abIdx in 0 until hero.abilityCount) {
                val abOffset = abBase + (abIdx * 20)
                val ab = hero.abilities[abIdx]
                ab.spellId = buffer.getInt(abOffset)
                ab.slot = buffer.getInt(abOffset + 4)
                ab.remainingSeconds = buffer.getFloat(abOffset + 8)
                ab.maxSeconds = buffer.getFloat(abOffset + 12)
                ab.isCoolingDown = buffer.get(abOffset + 16).toInt() != 0
                ab.isReady = buffer.get(abOffset + 17).toInt() != 0
            }

            if (hero.isLocalPlayer) {
                target.localHeroIndex = i
            }
        }

        // 2. Unpack Soldiers
        for (i in 0 until target.soldierCount) {
            val base = OFFSET_SOLDIERS + (i * SOLDIER_STRIDE)
            val sld = target.soldiers[i]

            sld.address = buffer.getLong(base)
            sld.soldierId = buffer.getInt(base + 8)
            sld.soldierType = buffer.getInt(base + 12)
            sld.pathId = buffer.getInt(base + 16)
            sld.camp = buffer.getInt(base + 20)
            sld.hp = buffer.getInt(base + 24)
            sld.hpMax = buffer.getInt(base + 28)
            sld.isDead = buffer.get(base + 32).toInt() != 0
            sld.posX = buffer.getFloat(base + 36)
            sld.posY = buffer.getFloat(base + 40)
        }

        // 3. Unpack Monsters
        for (i in 0 until target.monsterCount) {
            val base = OFFSET_MONSTERS + (i * MONSTER_STRIDE)
            val mon = target.monsters[i]

            mon.address = buffer.getLong(base)
            mon.monsterId = buffer.getInt(base + 8)
            mon.monsterType = buffer.getInt(base + 12)
            mon.camp = buffer.getInt(base + 16)
            mon.hp = buffer.getInt(base + 20)
            mon.hpMax = buffer.getInt(base + 24)
            mon.isDead = buffer.get(base + 28).toInt() != 0
            mon.posX = buffer.getFloat(base + 32)
            mon.posY = buffer.getFloat(base + 36)
            mon.attackRange = buffer.getFloat(base + 40)
        }

        // 4. Unpack Towers
        for (i in 0 until target.towerCount) {
            val base = OFFSET_TOWERS + (i * TOWER_STRIDE)
            val twr = target.towers[i]

            twr.address = buffer.getLong(base)
            twr.towerId = buffer.getInt(base + 8)
            twr.camp = buffer.getInt(base + 12)
            twr.hp = buffer.getInt(base + 16)
            twr.hpMax = buffer.getInt(base + 20)
            twr.isDead = buffer.get(base + 24).toInt() != 0
            twr.posX = buffer.getFloat(base + 28)
            twr.posY = buffer.getFloat(base + 32)
            twr.attackRange = buffer.getFloat(base + 36)
        }

        return true
    }
}
