package com.vemins.esp.model

/**
 * Pre-allocated mutable container for an ability slot.
 * Reused indefinitely with zero heap allocation during per-frame rendering.
 */
class MutableAbilityInfo {
    var spellId: Int = 0
    var slot: Int = 0
    var remainingSeconds: Float = 0.0f
    var maxSeconds: Float = 0.0f
    var isCoolingDown: Boolean = false
    var isReady: Boolean = true

    val cooldownProgress: Float
        get() = if (maxSeconds > 0.0f && remainingSeconds > 0.0f) {
            (remainingSeconds / maxSeconds).coerceIn(0.0f, 1.0f)
        } else {
            0.0f
        }

    fun reset() {
        spellId = 0
        slot = 0
        remainingSeconds = 0.0f
        maxSeconds = 0.0f
        isCoolingDown = false
        isReady = true
    }

    fun toImmutable(): AbilityInfo {
        return AbilityInfo(
            spellId = spellId,
            slot = slot,
            remainingCdMs = (remainingSeconds * 1000f).toInt(),
            maxCdMs = (maxSeconds * 1000f).toInt(),
            isCoolingDown = isCoolingDown
        )
    }
}

/**
 * Pre-allocated mutable hero entity.
 * Directly populated from DirectByteBuffer byte offsets.
 */
class MutableHeroEntity {
    var address: Long = 0L
    var heroId: Int = 0
    var level: Int = 1
    var hp: Int = 0
    var hpMax: Int = 0
    var mp: Int = 0
    var mpMax: Int = 0
    var shield: Int = 0
    var magicShield: Int = 0
    var camp: Int = 0
    var isDead: Boolean = false
    var isLocalPlayer: Boolean = false
    var isInBattle: Boolean = false
    var posX: Float = 0.0f
    var posY: Float = 0.0f
    var facingX: Float = 0.0f
    var facingY: Float = 0.0f
    var moveDirX: Float = 0.0f
    var moveDirY: Float = 0.0f
    var runSpeed: Float = 0.0f
    var attackSpeed: Float = 0.0f
    var gold: Int = 0
    var statusMask: Int = 0
    var faceLockId: Int = 0
    val itemIds = IntArray(6)
    var abilityCount: Int = 0
    val abilities = Array(6) { MutableAbilityInfo() }
    var distanceToMe: Float = 0.0f

    val isAlly: Boolean
        get() = !isLocalPlayer && camp == 1

    val isEnemy: Boolean
        get() = !isLocalPlayer && camp != 1

    val hpPercent: Float
        get() = if (hpMax > 0) (hp.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 1.0f) else 0.0f

    val mpPercent: Float
        get() = if (mpMax > 0) (mp.toFloat() / mpMax.toFloat()).coerceIn(0.0f, 1.0f) else 0.0f

    val shieldPercent: Float
        get() = if (hpMax > 0 && shield > 0) (shield.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 2.0f) else 0.0f

    val ultimateAbility: MutableAbilityInfo?
        get() {
            for (i in 0 until abilityCount) {
                val ab = abilities[i]
                if (ab.slot == 3 || ab.slot == 4) return ab
            }
            for (i in 0 until abilityCount) {
                val ab = abilities[i]
                if (ab.spellId % 100 == 30 || ab.spellId % 100 == 40 || ab.spellId == heroId * 100 + 30) return ab
            }
            for (i in 0 until abilityCount) {
                val ab = abilities[i]
                if (ab.spellId !in 20000..299999 && (ab.spellId % 100 != 10 && ab.spellId % 100 != 20) && ab.spellId > 0) return ab
            }
            return if (abilityCount >= 3) abilities[2] else null
        }

    val isUltReady: Boolean
        get() = ultimateAbility?.isReady ?: true

    val ultCooldownSeconds: Float
        get() = ultimateAbility?.remainingSeconds ?: 0.0f

    val battleSpell: MutableAbilityInfo?
        get() {
            for (i in 0 until abilityCount) {
                val ab = abilities[i]
                if (ab.slot == 5 || ab.spellId in 20000..299999) return ab
            }
            return null
        }

    fun getAbility(slot: Int): MutableAbilityInfo? {
        for (i in 0 until abilityCount) {
            if (abilities[i].slot == slot) return abilities[i]
        }
        return when (slot) {
            1 -> abilities.firstOrNull { it.spellId % 100 == 10 || it.spellId == heroId * 100 + 10 } ?: abilities.getOrNull(0)
            2 -> abilities.firstOrNull { it.spellId % 100 == 20 || it.spellId == heroId * 100 + 20 } ?: abilities.getOrNull(1)
            3, 4 -> ultimateAbility
            5 -> battleSpell
            else -> null
        }
    }

    fun reset() {
        address = 0L
        heroId = 0
        level = 1
        hp = 0
        hpMax = 0
        mp = 0
        mpMax = 0
        shield = 0
        magicShield = 0
        camp = 0
        isDead = false
        isLocalPlayer = false
        isInBattle = false
        posX = 0.0f
        posY = 0.0f
        facingX = 0.0f
        facingY = 0.0f
        moveDirX = 0.0f
        moveDirY = 0.0f
        runSpeed = 0.0f
        attackSpeed = 0.0f
        gold = 0
        statusMask = 0
        faceLockId = 0
        for (i in 0..5) itemIds[i] = 0
        abilityCount = 0
        for (i in 0..5) abilities[i].reset()
        distanceToMe = 0.0f
    }

    fun toImmutable(localCamp: Int = 1): HeroEntity {
        val abilitiesList = mutableListOf<AbilityInfo>()
        for (i in 0 until abilityCount) {
            abilitiesList.add(abilities[i].toImmutable())
        }
        val invList = mutableListOf<InventoryItem>()
        for (i in 0..5) {
            if (itemIds[i] > 0) {
                invList.add(InventoryItem(slot = i + 1, itemId = itemIds[i]))
            }
        }
        return HeroEntity(
            address = address,
            heroId = heroId,
            level = level,
            hp = hp,
            hpMax = hpMax,
            mp = mp,
            mpMax = mpMax,
            shield = shield,
            magicShield = magicShield,
            isDead = isDead,
            camp = camp,
            posX = posX,
            posY = posY,
            facingX = facingX,
            facingY = facingY,
            moveDirX = moveDirX,
            moveDirY = moveDirY,
            runSpeed = runSpeed,
            attackSpeed = attackSpeed,
            gold = gold,
            isLocalPlayer = isLocalPlayer,
            isAlly = !isLocalPlayer && (camp == localCamp),
            isBot = false,
            inBattle = isInBattle,
            distanceToMe = distanceToMe,
            abilities = abilitiesList,
            inventory = invList
        )
    }
}

/**
 * Pre-allocated mutable soldier / minion entity.
 */
class MutableSoldierEntity {
    var address: Long = 0L
    var soldierId: Int = 0
    var soldierType: Int = 0 // 1=Melee, 2=Ranged, 3=Siege, 4=Super
    var pathId: Int = 0      // 1=Top, 2=Mid, 3=Bot
    var camp: Int = 0        // 1=Blue, 2=Red
    var hp: Int = 0
    var hpMax: Int = 0
    var isDead: Boolean = false
    var posX: Float = 0.0f
    var posY: Float = 0.0f
    var distanceToMe: Float = 0.0f

    val hpPercent: Float
        get() = if (hpMax > 0) (hp.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 1.0f) else 0.0f

    val isSiegeOrSuper: Boolean
        get() = soldierType == 3 || soldierType == 4

    val isEnemy: Boolean
        get() = camp != 1

    fun reset() {
        address = 0L
        soldierId = 0
        soldierType = 0
        pathId = 0
        camp = 0
        hp = 0
        hpMax = 0
        isDead = false
        posX = 0.0f
        posY = 0.0f
        distanceToMe = 0.0f
    }

    fun toImmutable(): SoldierEntity {
        return SoldierEntity(
            address = address,
            soldierId = soldierId,
            soldierType = soldierType,
            lane = pathId,
            hp = hp,
            hpMax = hpMax,
            isDead = isDead,
            camp = camp,
            posX = posX,
            posY = posY,
            distanceToMe = distanceToMe
        )
    }
}

/**
 * Pre-allocated mutable monster / creep entity.
 */
class MutableMonsterEntity {
    var address: Long = 0L
    var monsterId: Int = 0
    var monsterType: Int = 0
    var camp: Int = 0
    var hp: Int = 0
    var hpMax: Int = 0
    var isDead: Boolean = false
    var posX: Float = 0.0f
    var posY: Float = 0.0f
    var attackRange: Float = 0.0f
    var distanceToMe: Float = 0.0f

    val hpPercent: Float
        get() = if (hpMax > 0) (hp.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 1.0f) else 0.0f

    val isLord: Boolean
        get() = monsterId == 51298 || (hpMax > 25000)

    val isTurtle: Boolean
        get() = monsterId == 51312 || (hpMax in 12000..25000 && !isLord)

    val isBlueBuff: Boolean
        get() = monsterId == 51248 || monsterType == 2083

    val isRedBuff: Boolean
        get() = monsterId == 51346 || monsterType == 2081

    val isHighPriorityObjective: Boolean
        get() = isLord || isTurtle || isBlueBuff || isRedBuff

    fun reset() {
        address = 0L
        monsterId = 0
        monsterType = 0
        camp = 0
        hp = 0
        hpMax = 0
        isDead = false
        posX = 0.0f
        posY = 0.0f
        attackRange = 0.0f
        distanceToMe = 0.0f
    }

    fun toImmutable(): MonsterEntity {
        return MonsterEntity(
            address = address,
            monsterId = monsterId,
            monsterType = monsterType,
            hp = hp,
            hpMax = hpMax,
            isDead = isDead,
            camp = camp,
            posX = posX,
            posY = posY,
            isWild = true,
            distanceToMe = distanceToMe
        )
    }
}

/**
 * Pre-allocated mutable tower / defense turret entity.
 */
class MutableTowerEntity {
    var address: Long = 0L
    var towerId: Int = 0
    var camp: Int = 0
    var hp: Int = 0
    var hpMax: Int = 0
    var isDead: Boolean = false
    var posX: Float = 0.0f
    var posY: Float = 0.0f
    var attackRange: Float = 0.0f
    var distanceToMe: Float = 0.0f

    val hpPercent: Float
        get() = if (hpMax > 0) (hp.toFloat() / hpMax.toFloat()).coerceIn(0.0f, 1.0f) else 0.0f

    val isEnemy: Boolean
        get() = camp != 1

    fun reset() {
        address = 0L
        towerId = 0
        camp = 0
        hp = 0
        hpMax = 0
        isDead = false
        posX = 0.0f
        posY = 0.0f
        attackRange = 0.0f
        distanceToMe = 0.0f
    }

    fun toImmutable(): TowerEntity {
        return TowerEntity(
            address = address,
            towerId = towerId,
            camp = camp,
            hp = hp,
            hpMax = hpMax,
            isDead = isDead,
            posX = posX,
            posY = posY,
            distanceToMe = distanceToMe
        )
    }
}

/**
 * Pre-allocated mutable FrameSnapshot containing fixed-size entity arrays.
 * Allocated ONCE per render thread. Never instantiated dynamically during render frames.
 */
class MutableFrameSnapshot {
    var magic: Int = 0
    var version: Int = 0
    var timestampNs: Long = 0L
    var frameIndex: Int = 0
    var pid: Int = 0
    var libcsharpBase: Long = 0L
    var liblogicBase: Long = 0L
    var inMatch: Boolean = false
    var battleState: Int = 0
    var localCamp: Int = 1
    var frameTimeMs: Int = 0
    var readLatencyMs: Float = 0.0f

    var heroCount: Int = 0
    val heroes = Array(10) { MutableHeroEntity() }

    var soldierCount: Int = 0
    val soldiers = Array(32) { MutableSoldierEntity() }

    var monsterCount: Int = 0
    val monsters = Array(32) { MutableMonsterEntity() }

    var towerCount: Int = 0
    val towers = Array(22) { MutableTowerEntity() }

    var localHeroIndex: Int = -1

    val localPlayer: MutableHeroEntity?
        get() = if (localHeroIndex in 0 until heroCount) heroes[localHeroIndex] else null

    fun reset() {
        magic = 0
        version = 0
        timestampNs = 0L
        frameIndex = 0
        pid = 0
        libcsharpBase = 0L
        liblogicBase = 0L
        inMatch = false
        battleState = 0
        localCamp = 1
        frameTimeMs = 0
        readLatencyMs = 0.0f
        heroCount = 0
        soldierCount = 0
        monsterCount = 0
        towerCount = 0
        localHeroIndex = -1
    }

    fun toImmutable(): FrameSnapshot {
        var localH: HeroEntity? = null
        val enemies = mutableListOf<HeroEntity>()
        val allies = mutableListOf<HeroEntity>()

        for (i in 0 until heroCount) {
            val h = heroes[i]
            val imm = h.toImmutable(localCamp)
            if (h.isLocalPlayer) {
                localH = imm
            } else if (h.camp == localCamp) {
                allies.add(imm)
            } else {
                enemies.add(imm)
            }
        }

        val sList = mutableListOf<SoldierEntity>()
        for (i in 0 until soldierCount) {
            sList.add(soldiers[i].toImmutable())
        }

        val mList = mutableListOf<MonsterEntity>()
        for (i in 0 until monsterCount) {
            mList.add(monsters[i].toImmutable())
        }

        val tList = mutableListOf<TowerEntity>()
        for (i in 0 until towerCount) {
            tList.add(towers[i].toImmutable())
        }

        return FrameSnapshot(
            timestampNs = timestampNs,
            inMatch = inMatch,
            battleState = battleState,
            frameTimeMs = frameTimeMs.toLong(),
            pid = pid,
            liblogicBase = liblogicBase,
            libcsharpBase = libcsharpBase,
            status = if (inMatch) "ok" else "idle",
            localPlayer = localH,
            enemies = enemies,
            allies = allies,
            soldiers = sList,
            monsters = mList,
            towers = tList
        )
    }
}
