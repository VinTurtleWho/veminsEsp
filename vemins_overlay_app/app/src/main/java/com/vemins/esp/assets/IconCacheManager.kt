package com.vemins.esp.assets

import android.content.Context
import android.content.res.AssetManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.BitmapShader
import android.graphics.Canvas
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Shader
import android.util.Log
import android.util.LruCache
import org.json.JSONObject
import java.io.File
import java.io.InputStream
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors

/**
 * High-Performance In-Memory Asset Pipeline & Circular Icon Cache.
 *
 * Capabilities:
 * 1. Pre-loads and caches circular-cropped hero portraits, skill icons, spell icons,
 *    and jungle objective icons in memory using [android.util.LruCache].
 * 2. Parses and maintains Hero ID-to-Name and Spell ID-to-Name mappings using `manifest.json`.
 * 3. High-quality anti-aliased circular cropping with zero runtime per-frame allocation.
 * 4. Thread-safe background pre-loading pipeline.
 */
class IconCacheManager private constructor(context: Context?) {

    companion object {
        private const val TAG = "IconCacheManager"
        private const val DEFAULT_CACHE_SIZE_BYTES = 32 * 1024 * 1024 // 32 MB default

        @Volatile
        private var INSTANCE: IconCacheManager? = null

        /**
         * Returns the singleton instance of [IconCacheManager].
         */
        @JvmStatic
        fun getInstance(context: Context? = null): IconCacheManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: IconCacheManager(context?.applicationContext ?: context).also { INSTANCE = it }
            }
        }

        /**
         * Creates a circular cropped [Bitmap] with smooth anti-aliasing and optional scaling.
         *
         * @param source Original source bitmap.
         * @param targetDiameter Target diameter in pixels. If <= 0, uses min(source.width, source.height).
         * @return Circular cropped ARGB_8888 bitmap.
         */
        @JvmStatic
        fun createCircularBitmap(source: Bitmap, targetDiameter: Int = 0): Bitmap {
            val srcWidth = source.width
            val srcHeight = source.height
            val minSrcDimension = Math.min(srcWidth, srcHeight)
            val diameter = if (targetDiameter > 0) targetDiameter else minSrcDimension
            val radius = diameter / 2.0f

            val output = Bitmap.createBitmap(diameter, diameter, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(output)

            val shader = BitmapShader(source, Shader.TileMode.CLAMP, Shader.TileMode.CLAMP)

            // Center-crop scale matrix
            val matrix = Matrix()
            val scale = diameter.toFloat() / minSrcDimension.toFloat()
            val dx = (diameter - srcWidth * scale) * 0.5f
            val dy = (diameter - srcHeight * scale) * 0.5f
            matrix.setScale(scale, scale)
            matrix.postTranslate(dx, dy)
            shader.setLocalMatrix(matrix)

            val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG).apply {
                this.shader = shader
                isDither = true
            }

            canvas.drawCircle(radius, radius, radius, paint)
            return output
        }
    }

    // Memory LRU Cache for circular bitmaps
    private val memoryCache: LruCache<String, Bitmap>

    // ID to Name and Asset Path Mappings
    private val heroNames = ConcurrentHashMap<Int, String>()
    private val spellNames = ConcurrentHashMap<Int, String>()
    private val heroAssetPaths = ConcurrentHashMap<Int, String>()
    private val skillAssetPaths = ConcurrentHashMap<Int, String>()
    private val spellAssetPaths = ConcurrentHashMap<Int, String>()
    private val spellNameAssetPaths = ConcurrentHashMap<String, String>()

    private val assetManager: AssetManager? = context?.assets
    private val backgroundExecutor = Executors.newSingleThreadExecutor()

    init {
        // Compute available memory budget for LRU cache (1/8th of available max heap)
        val maxMemory = (Runtime.getRuntime().maxMemory()).toInt()
        val cacheSize = if (maxMemory > 0) Math.min(maxMemory / 8, 64 * 1024 * 1024) else DEFAULT_CACHE_SIZE_BYTES

        memoryCache = object : LruCache<String, Bitmap>(cacheSize) {
            override fun sizeOf(key: String, bitmap: Bitmap): Int {
                return bitmap.byteCount
            }
        }

        // Initialize built-in default mappings
        initDefaultMappings()

        // Ingest manifest.json
        loadManifest(context)
    }

    // -------------------------------------------------------------------------
    // MANIFEST INGESTION & NAME MAPPING
    // -------------------------------------------------------------------------

    private fun initDefaultMappings() {
        // Default Core Battle Spells & IL2CPP Key Variants
        val defaultSpells = mapOf(
            20001 to "Flicker", 20100 to "Flicker", 20101 to "Flicker", 20102 to "Flicker", 20103 to "Flicker",
            20002 to "Retribution", 20200 to "Retribution", 20201 to "Retribution", 20202 to "Retribution", 20203 to "Retribution",
            20003 to "Inspire", 20300 to "Inspire", 20301 to "Inspire",
            20004 to "Sprint", 20400 to "Sprint", 20401 to "Sprint",
            20005 to "Revitalize", 20500 to "Revitalize", 20501 to "Revitalize",
            20006 to "Aegis", 20600 to "Aegis", 20601 to "Aegis",
            20007 to "Petrify", 20700 to "Petrify", 20701 to "Petrify",
            20008 to "Purify", 20800 to "Purify", 20801 to "Purify",
            20009 to "Flameshot", 20900 to "Flameshot", 20901 to "Flameshot",
            20010 to "Vengeance", 21000 to "Vengeance", 21001 to "Vengeance",
            20011 to "Arrival", 21100 to "Arrival", 21101 to "Arrival"
        )
        spellNames.putAll(defaultSpells)

        for ((id, name) in defaultSpells) {
            val lower = name.lowercase()
            spellAssetPaths[id] = "spells/$lower.png"
            spellNameAssetPaths[lower] = "spells/$lower.png"
        }

        // Default Common Hero Names
        val defaultHeroes = mapOf(
            1 to "Miya", 2 to "Balmond", 3 to "Saber", 4 to "Alice", 5 to "Nana",
            6 to "Tigreal", 7 to "Alucard", 8 to "Karina", 9 to "Akai", 10 to "Franco",
            11 to "Bane", 12 to "Bruno", 13 to "Clint", 14 to "Rafaela", 15 to "Eudora",
            16 to "Zilong", 17 to "Fanny", 18 to "Layla", 19 to "Minotaur", 20 to "Lolita",
            21 to "Hayabusa", 22 to "Freya", 23 to "Gord", 24 to "Natalia", 25 to "Kagura",
            26 to "Chou", 27 to "Sun", 28 to "Alpha", 29 to "Ruby", 30 to "Yi Sun-shin",
            31 to "Moskov", 32 to "Johnson", 33 to "Cyclops", 34 to "Estes", 35 to "Hilda",
            36 to "Aurora", 37 to "Lapu-Lapu", 38 to "Vexana", 39 to "Roger", 40 to "Karrie",
            41 to "Gatotkaca", 42 to "Harley", 43 to "Irithel", 44 to "Grock", 45 to "Argus",
            46 to "Odette", 47 to "Lancelot", 48 to "Diggie", 49 to "Hylos", 50 to "Zhask",
            51 to "Helcurt", 52 to "Pharsa", 53 to "Lesley", 54 to "Jawhead", 55 to "Angela",
            56 to "Gusion", 57 to "Valir", 58 to "Martis", 59 to "Uranus", 60 to "Hanabi",
            61 to "Chang'e", 62 to "Kaja", 63 to "Selena", 64 to "Aldous", 65 to "Claude",
            66 to "Vale", 67 to "Leomord", 68 to "Lunox", 69 to "Hanzo", 70 to "Belerick",
            71 to "Kimmy", 72 to "Thamuz", 73 to "Harith", 74 to "Minsitthar", 75 to "Kadita",
            76 to "Faramis", 77 to "Badang", 78 to "Khufra", 79 to "Granger", 80 to "Guinevere",
            81 to "Esmeralda", 82 to "Terizla", 83 to "X.Borg", 84 to "Ling", 85 to "Dyrroth",
            86 to "Lylia", 87 to "Baxia", 88 to "Masha", 89 to "Wanwan", 90 to "Silvanna",
            91 to "Cecilion", 92 to "Carmilla", 93 to "Atlas", 94 to "Popol and Kupa", 95 to "Yu Zhong",
            96 to "Luo Yi", 97 to "Benedetta", 98 to "Khaleed", 99 to "Barats", 100 to "Brody",
            101 to "Yve", 102 to "Mathilda", 103 to "Paquito", 104 to "Gloo", 105 to "Beatrix",
            106 to "Phoveus", 107 to "Natan", 108 to "Aulus", 109 to "Aamon", 110 to "Valentina",
            111 to "Edith", 112 to "Floryn", 113 to "Yin", 114 to "Melissa", 115 to "Xavier",
            116 to "Julian", 117 to "Fredrinn", 118 to "Joy", 119 to "Novaria", 120 to "Arlott",
            121 to "Ixia", 122 to "Nolan", 123 to "Cici", 124 to "Chip", 125 to "Zhuxin",
            126 to "Suyou", 127 to "Lukas"
        )
        heroNames.putAll(defaultHeroes)
    }

    /**
     * Loads and parses `manifest.json` from assets or filesystem fallback.
     */
    fun loadManifest(context: Context?) {
        try {
            var jsonString: String? = null

            // 1. Try reading from Android AssetManager
            if (assetManager != null) {
                try {
                    val stream: InputStream = assetManager.open("manifest.json")
                    jsonString = stream.bufferedReader().use { it.readText() }
                } catch (e: Exception) {
                    // Fallback
                }
            }

            // 2. Try reading from file system if assets stream unavailable
            if (jsonString == null) {
                val candidateFiles = listOf(
                    File("assets/manifest.json"),
                    File("app/src/main/assets/manifest.json"),
                    File("/data/data/com.termux/files/home/veminsEsp/assets/manifest.json"),
                    File("/data/data/com.termux/files/home/veminsEsp/vemins_overlay_app/app/src/main/assets/manifest.json")
                )
                for (file in candidateFiles) {
                    if (file.exists() && file.canRead()) {
                        jsonString = file.readText()
                        break
                    }
                }
            }

            if (jsonString != null) {
                parseManifestJson(jsonString)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Could not load manifest.json: ${e.message}")
        }
    }

    private fun parseManifestJson(jsonString: String) {
        val root = JSONObject(jsonString)

        // Parse Hero Asset Paths
        val heroesObj = root.optJSONObject("heroes")
        if (heroesObj != null) {
            val keys = heroesObj.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                val heroId = k.toIntOrNull()
                if (heroId != null) {
                    var path = heroesObj.optString(k)
                    path = sanitizeAssetPath(path, "heroes/$heroId.png")
                    heroAssetPaths[heroId] = path
                }
            }
        }

        // Parse Skill Asset Paths
        val skillsObj = root.optJSONObject("skills")
        if (skillsObj != null) {
            val keys = skillsObj.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                val skillId = k.toIntOrNull()
                if (skillId != null) {
                    var path = skillsObj.optString(k)
                    path = sanitizeAssetPath(path, "skills/$skillId.png")
                    skillAssetPaths[skillId] = path
                }
            }
        }

        // Parse Spell Asset Paths
        val spellsObj = root.optJSONObject("spells")
        if (spellsObj != null) {
            val keys = spellsObj.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                val spellId = k.toIntOrNull()
                var path = spellsObj.optString(k)
                path = sanitizeAssetPath(path, "spells/$k.png")
                if (spellId != null) {
                    spellAssetPaths[spellId] = path
                }
                spellNameAssetPaths[k.lowercase()] = path
            }
        }

        // Parse Hero Names
        val heroNamesObj = root.optJSONObject("hero_names")
        if (heroNamesObj != null) {
            val keys = heroNamesObj.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                val heroId = k.toIntOrNull()
                if (heroId != null) {
                    heroNames[heroId] = heroNamesObj.getString(k)
                }
            }
        }

        // Parse Spell Names
        val spellNamesObj = root.optJSONObject("spell_names")
        if (spellNamesObj != null) {
            val keys = spellNamesObj.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                val spellId = k.toIntOrNull()
                if (spellId != null) {
                    spellNames[spellId] = spellNamesObj.getString(k)
                }
            }
        }

        Log.i(TAG, "Manifest loaded: ${heroNames.size} heroes, ${spellNames.size} spells, ${skillAssetPaths.size} skills mapped.")
    }

    private fun sanitizeAssetPath(path: String, fallback: String): String {
        if (path.isEmpty()) return fallback
        // If absolute path, extract relative asset path
        val idx = path.indexOf("assets/")
        return if (idx != -1) {
            path.substring(idx + "assets/".length)
        } else if (path.startsWith("/")) {
            fallback
        } else {
            path
        }
    }

    // -------------------------------------------------------------------------
    // NAME MAPPINGS
    // -------------------------------------------------------------------------

    /**
     * Resolves human-readable hero name for a given hero ID.
     */
    fun getHeroName(heroId: Int): String {
        return heroNames[heroId] ?: "Hero #$heroId"
    }

    /**
     * Resolves human-readable battle spell name for a given spell ID.
     */
    fun getSpellName(spellId: Int): String {
        return spellNames[spellId] ?: "Spell #$spellId"
    }

    // -------------------------------------------------------------------------
    // BITMAP RETRIEVAL & CIRCULAR CROPPING
    // -------------------------------------------------------------------------

    /**
     * Retrieves a pre-cropped circular hero portrait bitmap from cache or assets.
     */
    fun getHeroPortrait(heroId: Int, targetDiameter: Int = 0): Bitmap? {
        if (heroId <= 0) return null
        val cacheKey = "hero_${heroId}_${targetDiameter}"

        val cached = memoryCache.get(cacheKey)
        if (cached != null) return cached

        val relativePath = heroAssetPaths[heroId] ?: "heroes/$heroId.png"
        val rawBitmap = loadBitmapFromAssets(relativePath) ?: return null

        val circular = createCircularBitmap(rawBitmap, targetDiameter)
        memoryCache.put(cacheKey, circular)
        return circular
    }

    /**
     * Retrieves a pre-cropped circular skill icon bitmap from cache or assets.
     */
    fun getSkillIcon(skillId: Int, targetDiameter: Int = 0): Bitmap? {
        if (skillId <= 0) return null
        val cacheKey = "skill_${skillId}_${targetDiameter}"

        val cached = memoryCache.get(cacheKey)
        if (cached != null) return cached

        var rawBitmap: Bitmap? = null
        val relativePath = skillAssetPaths[skillId]
        if (relativePath != null) {
            rawBitmap = loadBitmapFromAssets(relativePath)
        }

        if (rawBitmap == null) {
            rawBitmap = loadBitmapFromAssets("skills/$skillId.png")
        }

        if (rawBitmap == null && skillId >= 100) {
            val heroId = skillId / 100
            val sub = skillId % 100
            val slotCandidates = when (sub) {
                10 -> listOf("skills/$heroId/skill1.png", "skills/${heroId}0.png", "skills/${heroId}10.png")
                20 -> listOf("skills/$heroId/skill2.png", "skills/${heroId}20.png")
                30, 40 -> listOf("skills/$heroId/ult.png", "skills/${heroId}30.png", "skills/${heroId}40.png")
                0 -> listOf("skills/$heroId/passive.png", "skills/${heroId}00.png")
                else -> listOf("skills/$heroId/skill1.png", "skills/$heroId/ult.png")
            }
            for (cand in slotCandidates) {
                rawBitmap = loadBitmapFromAssets(cand)
                if (rawBitmap != null) break
            }
        }

        if (rawBitmap == null) return null

        val circular = createCircularBitmap(rawBitmap, targetDiameter)
        memoryCache.put(cacheKey, circular)
        return circular
    }

    /**
     * Retrieves a pre-cropped circular battle spell icon bitmap from cache or assets.
     */
    fun getSpellIcon(spellId: Int, targetDiameter: Int = 0): Bitmap? {
        if (spellId <= 0) return null
        val cacheKey = "spell_${spellId}_${targetDiameter}"

        val cached = memoryCache.get(cacheKey)
        if (cached != null) return cached

        var rawBitmap: Bitmap? = null
        val relativePath = spellAssetPaths[spellId]
        if (relativePath != null) {
            rawBitmap = loadBitmapFromAssets(relativePath)
        }

        if (rawBitmap == null) {
            val name = spellNames[spellId]?.lowercase()
            if (name != null) {
                rawBitmap = loadBitmapFromAssets("spells/$name.png")
            }
        }

        if (rawBitmap == null) {
            rawBitmap = loadBitmapFromAssets("spells/$spellId.png")
        }

        // Semantic IL2CPP range fallback
        if (rawBitmap == null && spellId >= 20000) {
            val fallbackName = when (spellId) {
                in 20001..20001, in 20100..20199 -> "flicker"
                in 20002..20002, in 20200..20299 -> "retribution"
                in 20003..20003, in 20300..20399 -> "inspire"
                in 20004..20004, in 20400..20499 -> "sprint"
                in 20005..20005, in 20500..20599 -> "revitalize"
                in 20006..20006, in 20600..20699 -> "aegis"
                in 20007..20007, in 20700..20799 -> "petrify"
                in 20008..20008, in 20800..20899 -> "purify"
                in 20009..20009, in 20900..20999 -> "flameshot"
                in 20010..20010, in 21000..21099 -> "vengeance"
                in 20011..20011, in 21100..21199 -> "arrival"
                else -> "flicker"
            }
            rawBitmap = loadBitmapFromAssets("spells/$fallbackName.png")
        }

        if (rawBitmap == null) return null

        val circular = createCircularBitmap(rawBitmap, targetDiameter)
        memoryCache.put(cacheKey, circular)
        return circular
    }

    /**
     * Retrieves a battle spell icon by its string name (e.g. "flicker", "retribution").
     */
    fun getSpellIconByName(spellName: String, targetDiameter: Int = 0): Bitmap? {
        val cleanName = spellName.trim().lowercase()
        val cacheKey = "spell_name_${cleanName}_${targetDiameter}"

        val cached = memoryCache.get(cacheKey)
        if (cached != null) return cached

        val relativePath = spellNameAssetPaths[cleanName] ?: "spells/$cleanName.png"
        val rawBitmap = loadBitmapFromAssets(relativePath) ?: return null

        val circular = createCircularBitmap(rawBitmap, targetDiameter)
        memoryCache.put(cacheKey, circular)
        return circular
    }

    /**
     * Unified resolver for any hero ability icon (Skill 1, 2, 3/Ult, 4, or Battle Spell).
     * Guarantees an icon is returned using hero folders, skill IDs, and spell mappings.
     */
    fun getHeroAbilityIcon(heroId: Int, slot: Int, spellId: Int = 0, targetDiameter: Int = 0): Bitmap? {
        val cacheKey = "hero_ab_${heroId}_${slot}_${spellId}_${targetDiameter}"
        val cached = memoryCache.get(cacheKey)
        if (cached != null) return cached

        var bitmap: Bitmap? = null

        // 1. If Battle Spell (Slot 5 or Spell ID in 20000..299999)
        if (slot == 5 || (spellId in 20000..299999)) {
            val effSpellId = if (spellId > 0) spellId else 20001
            bitmap = getSpellIcon(effSpellId, targetDiameter)
        }

        // 2. Direct Spell ID Lookup
        if (bitmap == null && spellId > 0) {
            bitmap = getSkillIcon(spellId, targetDiameter)
        }

        // 3. Hero-specific folder fallback
        if (bitmap == null && heroId > 0) {
            val candidates = when (slot) {
                1 -> listOf(
                    "skills/$heroId/skill1.png",
                    "skills/${heroId}10.png",
                    "skills/${heroId * 100 + 10}.png"
                )
                2 -> listOf(
                    "skills/$heroId/skill2.png",
                    "skills/${heroId}20.png",
                    "skills/${heroId * 100 + 20}.png"
                )
                3 -> listOf(
                    "skills/$heroId/ult.png",
                    "skills/$heroId/skill3.png",
                    "skills/${heroId}30.png",
                    "skills/${heroId * 100 + 30}.png"
                )
                4 -> listOf(
                    "skills/$heroId/skill4.png",
                    "skills/$heroId/ult.png",
                    "skills/${heroId}40.png",
                    "skills/${heroId * 100 + 40}.png"
                )
                5 -> listOf(
                    "spells/flicker.png",
                    "spells/20001.png"
                )
                else -> listOf(
                    "skills/$heroId/skill1.png",
                    "skills/$heroId/ult.png"
                )
            }
            for (path in candidates) {
                val raw = loadBitmapFromAssets(path)
                if (raw != null) {
                    bitmap = createCircularBitmap(raw, targetDiameter)
                    break
                }
            }
        }

        // 4. Ultimate / Hero Portrait fallback
        if (bitmap == null && heroId > 0) {
            val ultRaw = loadBitmapFromAssets("skills/$heroId/ult.png")
            if (ultRaw != null) {
                bitmap = createCircularBitmap(ultRaw, targetDiameter)
            } else {
                bitmap = getHeroPortrait(heroId, targetDiameter)
            }
        }

        if (bitmap != null) {
            memoryCache.put(cacheKey, bitmap)
        }
        return bitmap
    }

    /**
     * Retrieves an objective icon (e.g. "lord", "turtle", "buff_blue", "buff_red").
     */
    fun getObjectiveIcon(objectiveKey: String, targetDiameter: Int = 0): Bitmap? {
        val cleanKey = objectiveKey.trim().lowercase()
        val cacheKey = "obj_${cleanKey}_${targetDiameter}"

        val cached = memoryCache.get(cacheKey)
        if (cached != null) return cached

        val candidatePaths = listOf(
            "objectives/$cleanKey.png",
            "objectives/${cleanKey}_icon.png",
            "$cleanKey.png"
        )

        var rawBitmap: Bitmap? = null
        for (path in candidatePaths) {
            rawBitmap = loadBitmapFromAssets(path)
            if (rawBitmap != null) break
        }

        if (rawBitmap == null) return null

        val circular = createCircularBitmap(rawBitmap, targetDiameter)
        memoryCache.put(cacheKey, circular)
        return circular
    }

    // -------------------------------------------------------------------------
    // INTERNAL BITMAP LOADING (ASSETMANAGER & FILE FALLBACK)
    // -------------------------------------------------------------------------

    private fun loadBitmapFromAssets(relativePath: String): Bitmap? {
        // 1. Try Android AssetManager
        if (assetManager != null) {
            try {
                assetManager.open(relativePath).use { stream ->
                    return BitmapFactory.decodeStream(stream)
                }
            } catch (e: Exception) {
                // Ignore and fall through to filesystem fallback
            }
        }

        // 2. Try Local Filesystem candidates
        val candidates = listOf(
            File("app/src/main/assets", relativePath),
            File("assets", relativePath),
            File("/data/data/com.termux/files/home/veminsEsp/assets", relativePath),
            File("/data/data/com.termux/files/home/veminsEsp/vemins_overlay_app/app/src/main/assets", relativePath)
        )

        for (file in candidates) {
            if (file.exists() && file.canRead()) {
                try {
                    return BitmapFactory.decodeFile(file.absolutePath)
                } catch (e: Exception) {
                    // Continue to next candidate
                }
            }
        }

        return null
    }

    // -------------------------------------------------------------------------
    // ASYNCHRONOUS PRE-LOADING
    // -------------------------------------------------------------------------

    /**
     * Pre-loads common battle spells and active hero portraits in the background.
     */
    fun preloadCommon(heroIds: Collection<Int> = emptyList()) {
        backgroundExecutor.execute {
            // Pre-load common battle spells
            for (spellId in spellNames.keys) {
                getSpellIcon(spellId, 0)
            }

            // Pre-load specified heroes
            for (heroId in heroIds) {
                getHeroPortrait(heroId, 0)
            }
        }
    }

    /**
     * Clears all bitmaps from memory cache.
     */
    fun clearCache() {
        memoryCache.evictAll()
    }
}
