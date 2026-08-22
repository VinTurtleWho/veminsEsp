package com.vemins.esp.config

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.OutputStreamWriter
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Screen dimensions configuration.
 */
data class ScreenConfig(
    var width: Float = 2400.0f,
    var height: Float = 1080.0f
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("width", width.toDouble())
        put("height", height.toDouble())
    }

    companion object {
        fun fromJson(json: JSONObject?): ScreenConfig {
            if (json == null) return ScreenConfig()
            return ScreenConfig(
                width = json.optDouble("width", 2400.0).toFloat(),
                height = json.optDouble("height", 1080.0).toFloat()
            )
        }
    }
}

/**
 * Minimap radar bounding box and orientation configuration.
 */
data class MinimapConfig(
    var posX: Float = 75.0f,
    var posY: Float = 15.0f,
    var width: Float = 320.0f,
    var height: Float = 320.0f,
    var alpha: Float = 0.85f,
    var rotationDegrees: Float = 0.0f,
    var invertY: Boolean = true,
    var diamondMode: Boolean = false
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("pos_x", posX.toDouble())
        put("pos_y", posY.toDouble())
        put("width", width.toDouble())
        put("height", height.toDouble())
        put("alpha", alpha.toDouble())
        put("rotation_degrees", rotationDegrees.toDouble())
        put("invert_y", invertY)
        put("diamond_mode", diamondMode)
    }

    companion object {
        fun fromJson(json: JSONObject?): MinimapConfig {
            if (json == null) return MinimapConfig()
            val rot = json.optDouble("rotation_degrees", 0.0).toFloat()
            val diamond = json.optBoolean("diamond_mode", rot == 45.0f)
            return MinimapConfig(
                posX = json.optDouble("pos_x", 75.0).toFloat(),
                posY = json.optDouble("pos_y", 15.0).toFloat(),
                width = json.optDouble("width", 320.0).toFloat(),
                height = json.optDouble("height", 320.0).toFloat(),
                alpha = json.optDouble("alpha", 0.85).toFloat(),
                rotationDegrees = if (diamond && rot == 0.0f) 45.0f else rot,
                invertY = json.optBoolean("invert_y", true),
                diamondMode = diamond
            )
        }
    }
}

/**
 * Isometric camera and World-to-Screen projection scaling configuration.
 */
data class CameraConfig(
    var scaleX: Float = 38.0f,
    var scaleY: Float = 27.0f,
    var hudOffsetY: Float = 65.0f,
    var edgeMargin: Float = 45.0f,
    var maxRadarDistance: Float = 45.0f,
    var highCamera: Boolean = true
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("scale_x", scaleX.toDouble())
        put("scale_y", scaleY.toDouble())
        put("hud_offset_y", hudOffsetY.toDouble())
        put("edge_margin", edgeMargin.toDouble())
        put("max_radar_distance", maxRadarDistance.toDouble())
        put("high_camera", highCamera)
    }

    companion object {
        fun fromJson(json: JSONObject?): CameraConfig {
            if (json == null) return CameraConfig()
            return CameraConfig(
                scaleX = json.optDouble("scale_x", 38.0).toFloat(),
                scaleY = json.optDouble("scale_y", 27.0).toFloat(),
                hudOffsetY = json.optDouble("hud_offset_y", 65.0).toFloat(),
                edgeMargin = json.optDouble("edge_margin", 45.0).toFloat(),
                maxRadarDistance = json.optDouble("max_radar_distance", 45.0).toFloat(),
                highCamera = json.optBoolean("high_camera", true)
            )
        }
    }
}

/**
 * World coordinate bounds (MLBB standard Cartesian range [-52, 52]).
 */
data class WorldBoundsConfig(
    var minX: Float = -52.0f,
    var maxX: Float = 52.0f,
    var minY: Float = -52.0f,
    var maxY: Float = 52.0f
) {
    val worldWidth: Float get() = if (maxX != minX) maxX - minX else 104.0f
    val worldHeight: Float get() = if (maxY != minY) maxY - minY else 104.0f

    fun toJson(): JSONObject = JSONObject().apply {
        put("min_x", minX.toDouble())
        put("max_x", maxX.toDouble())
        put("min_y", minY.toDouble())
        put("max_y", maxY.toDouble())
    }

    companion object {
        fun fromJson(json: JSONObject?): WorldBoundsConfig {
            if (json == null) return WorldBoundsConfig()
            return WorldBoundsConfig(
                minX = json.optDouble("min_x", -52.0).toFloat(),
                maxX = json.optDouble("max_x", 52.0).toFloat(),
                minY = json.optDouble("min_y", -52.0).toFloat(),
                maxY = json.optDouble("max_y", 52.0).toFloat()
            )
        }
    }
}

/**
 * HUD Render layer visibility and styling toggles.
 */
data class RenderSettingsConfig(
    var minimapShowEnemies: Boolean = true,
    var minimapShowAllies: Boolean = false,
    var minimapShowArrows: Boolean = true,
    var minimapShowMinions: Boolean = true,
    var minimapShowMonsters: Boolean = true,
    var minimapHeroDotRadius: Float = 9.0f,
    var minimapArrowLength: Float = 18.0f,
    var minimapMinionDotRadius: Float = 3.5f,
    var minimapMonsterDotRadius: Float = 7.0f,
    var screenShowOverheadHp: Boolean = true,
    var screenShowShields: Boolean = true,
    var screenShowSkillCooldowns: Boolean = true,
    var screenShowUltBadge: Boolean = true,
    var screenShowSpellBadge: Boolean = true,
    var screenShowBattleSpell: Boolean = true,
    var screenShowDistance: Boolean = true,
    var screenShowEdgeRadar: Boolean = true,
    var screenShowHeroNames: Boolean = true,
    var screenShowHealthText: Boolean = true,
    var hudBadgeRadius: Float = 9.0f,
    var hudHpBarScale: Float = 1.0f
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("minimap_show_enemies", minimapShowEnemies)
        put("minimap_show_allies", minimapShowAllies)
        put("minimap_show_arrows", minimapShowArrows)
        put("minimap_show_minions", minimapShowMinions)
        put("minimap_show_monsters", minimapShowMonsters)
        put("minimap_hero_dot_radius", minimapHeroDotRadius.toDouble())
        put("minimap_arrow_length", minimapArrowLength.toDouble())
        put("minimap_minion_dot_radius", minimapMinionDotRadius.toDouble())
        put("minimap_monster_dot_radius", minimapMonsterDotRadius.toDouble())
        put("screen_show_overhead_hp", screenShowOverheadHp)
        put("screen_show_shields", screenShowShields)
        put("screen_show_skill_cooldowns", screenShowSkillCooldowns)
        put("screen_show_ult_badge", screenShowUltBadge)
        put("screen_show_spell_badge", screenShowSpellBadge)
        put("screen_show_battle_spell", screenShowBattleSpell)
        put("screen_show_distance", screenShowDistance)
        put("screen_show_edge_radar", screenShowEdgeRadar)
        put("screen_show_hero_names", screenShowHeroNames)
        put("screen_show_health_text", screenShowHealthText)
        put("hud_badge_radius", hudBadgeRadius.toDouble())
        put("hud_hp_bar_scale", hudHpBarScale.toDouble())
    }

    companion object {
        fun fromJson(json: JSONObject?): RenderSettingsConfig {
            if (json == null) return RenderSettingsConfig()
            return RenderSettingsConfig(
                minimapShowEnemies = json.optBoolean("minimap_show_enemies", true),
                minimapShowAllies = json.optBoolean("minimap_show_allies", false),
                minimapShowArrows = json.optBoolean("minimap_show_arrows", true),
                minimapShowMinions = json.optBoolean("minimap_show_minions", true),
                minimapShowMonsters = json.optBoolean("minimap_show_monsters", true),
                minimapHeroDotRadius = json.optDouble("minimap_hero_dot_radius", 9.0).toFloat(),
                minimapArrowLength = json.optDouble("minimap_arrow_length", 18.0).toFloat(),
                minimapMinionDotRadius = json.optDouble("minimap_minion_dot_radius", 3.5).toFloat(),
                minimapMonsterDotRadius = json.optDouble("minimap_monster_dot_radius", 7.0).toFloat(),
                screenShowOverheadHp = json.optBoolean("screen_show_overhead_hp", true),
                screenShowShields = json.optBoolean("screen_show_shields", true),
                screenShowSkillCooldowns = json.optBoolean("screen_show_skill_cooldowns", true),
                screenShowUltBadge = json.optBoolean("screen_show_ult_badge", true),
                screenShowSpellBadge = json.optBoolean("screen_show_spell_badge", true),
                screenShowBattleSpell = json.optBoolean("screen_show_battle_spell", true),
                screenShowDistance = json.optBoolean("screen_show_distance", true),
                screenShowEdgeRadar = json.optBoolean("screen_show_edge_radar", true),
                screenShowHeroNames = json.optBoolean("screen_show_hero_names", true),
                screenShowHealthText = json.optBoolean("screen_show_health_text", true),
                hudBadgeRadius = json.optDouble("hud_badge_radius", 9.0).toFloat(),
                hudHpBarScale = json.optDouble("hud_hp_bar_scale", 1.0).toFloat()
            )
        }
    }
}

/**
 * Server endpoint connection configuration.
 */
data class ServerConfig(
    var serverHost: String = "127.0.0.1",
    var serverPort: Int = 9999,
    var controlServerPort: Int = 8888
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("server_host", serverHost)
        put("server_port", serverPort)
        put("control_server_port", controlServerPort)
    }

    companion object {
        fun fromJson(json: JSONObject?): ServerConfig {
            if (json == null) return ServerConfig()
            return ServerConfig(
                serverHost = json.optString("server_host", "127.0.0.1"),
                serverPort = json.optInt("server_port", 9999),
                controlServerPort = json.optInt("control_server_port", 8888)
            )
        }
    }
}

/**
 * Root ESP overlay configuration container.
 */
data class OverlayConfig(
    val screen: ScreenConfig = ScreenConfig(),
    val minimap: MinimapConfig = MinimapConfig(),
    val camera: CameraConfig = CameraConfig(),
    val worldBounds: WorldBoundsConfig = WorldBoundsConfig(),
    val renderSettings: RenderSettingsConfig = RenderSettingsConfig(),
    val server: ServerConfig = ServerConfig()
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("screen", screen.toJson())
        put("minimap", minimap.toJson())
        put("camera", camera.toJson())
        put("world_bounds", worldBounds.toJson())
        put("render_settings", renderSettings.toJson())
        put("server", server.toJson())
    }

    fun deepCopy(): OverlayConfig {
        return OverlayConfig(
            screen = screen.copy(),
            minimap = minimap.copy(),
            camera = camera.copy(),
            worldBounds = worldBounds.copy(),
            renderSettings = renderSettings.copy(),
            server = server.copy()
        )
    }

    /**
     * Converts to immutable projection MinimapConfig used by math projection engines.
     */
    fun toMinimapConfig(): com.vemins.esp.model.MinimapConfig {
        return com.vemins.esp.model.MinimapConfig(
            screenWidth = screen.width,
            screenHeight = screen.height,
            mapPosX = minimap.posX,
            mapPosY = minimap.posY,
            mapWidth = minimap.width,
            mapHeight = minimap.height,
            mapAlpha = minimap.alpha,
            rotationDegrees = if (minimap.diamondMode) 45.0f else minimap.rotationDegrees,
            invertY = minimap.invertY,
            scaleX = camera.scaleX,
            scaleY = camera.scaleY,
            hudOffsetY = camera.hudOffsetY,
            edgeMargin = camera.edgeMargin,
            maxRadarDistance = camera.maxRadarDistance,
            highCamera = camera.highCamera,
            minX = worldBounds.minX,
            maxX = worldBounds.maxX,
            minY = worldBounds.minY,
            maxY = worldBounds.maxY,
            minimapShowEnemies = renderSettings.minimapShowEnemies,
            minimapShowAllies = renderSettings.minimapShowAllies,
            minimapShowArrows = renderSettings.minimapShowArrows,
            minimapShowMinions = renderSettings.minimapShowMinions,
            minimapShowMonsters = renderSettings.minimapShowMonsters,
            minimapHeroDotRadius = renderSettings.minimapHeroDotRadius,
            minimapArrowLength = renderSettings.minimapArrowLength,
            minimapMinionDotRadius = renderSettings.minimapMinionDotRadius,
            minimapMonsterDotRadius = renderSettings.minimapMonsterDotRadius,
            screenShowOverheadHp = renderSettings.screenShowOverheadHp,
            screenShowShields = renderSettings.screenShowShields,
            screenShowSkillCooldowns = renderSettings.screenShowSkillCooldowns,
            screenShowUltBadge = renderSettings.screenShowUltBadge,
            screenShowSpellBadge = renderSettings.screenShowSpellBadge,
            screenShowBattleSpell = renderSettings.screenShowBattleSpell,
            screenShowDistance = renderSettings.screenShowDistance,
            screenShowEdgeRadar = renderSettings.screenShowEdgeRadar,
            screenShowHealthText = renderSettings.screenShowHealthText,
            hudBadgeRadius = renderSettings.hudBadgeRadius,
            hudHpBarScale = renderSettings.hudHpBarScale
        )
    }

    companion object {
        fun fromMinimapConfig(m: com.vemins.esp.model.MinimapConfig): OverlayConfig {
            return OverlayConfig(
                screen = ScreenConfig(width = m.screenWidth, height = m.screenHeight),
                minimap = MinimapConfig(
                    posX = m.mapPosX,
                    posY = m.mapPosY,
                    width = m.mapWidth,
                    height = m.mapHeight,
                    alpha = m.mapAlpha,
                    rotationDegrees = m.rotationDegrees,
                    invertY = m.invertY,
                    diamondMode = m.rotationDegrees == 45.0f
                ),
                camera = CameraConfig(
                    scaleX = m.scaleX,
                    scaleY = m.scaleY,
                    hudOffsetY = m.hudOffsetY,
                    edgeMargin = m.edgeMargin,
                    maxRadarDistance = m.maxRadarDistance,
                    highCamera = m.highCamera
                ),
                worldBounds = WorldBoundsConfig(
                    minX = m.minX,
                    maxX = m.maxX,
                    minY = m.minY,
                    maxY = m.maxY
                ),
                renderSettings = RenderSettingsConfig(
                    minimapShowEnemies = m.minimapShowEnemies,
                    minimapShowAllies = m.minimapShowAllies,
                    minimapShowArrows = m.minimapShowArrows,
                    minimapShowMinions = m.minimapShowMinions,
                    minimapShowMonsters = m.minimapShowMonsters,
                    minimapHeroDotRadius = m.minimapHeroDotRadius,
                    minimapArrowLength = m.minimapArrowLength,
                    minimapMinionDotRadius = m.minimapMinionDotRadius,
                    minimapMonsterDotRadius = m.minimapMonsterDotRadius,
                    screenShowOverheadHp = m.screenShowOverheadHp,
                    screenShowShields = m.screenShowShields,
                    screenShowSkillCooldowns = m.screenShowSkillCooldowns,
                    screenShowUltBadge = m.screenShowUltBadge,
                    screenShowSpellBadge = m.screenShowSpellBadge,
                    screenShowBattleSpell = m.screenShowBattleSpell,
                    screenShowDistance = m.screenShowDistance,
                    screenShowEdgeRadar = m.screenShowEdgeRadar,
                    screenShowHealthText = m.screenShowHealthText,
                    hudBadgeRadius = m.hudBadgeRadius,
                    hudHpBarScale = m.hudHpBarScale
                ),
                server = ServerConfig()
            )
        }

        fun fromJson(json: JSONObject): OverlayConfig {
            return OverlayConfig(
                screen = ScreenConfig.fromJson(json.optJSONObject("screen")),
                minimap = MinimapConfig.fromJson(json.optJSONObject("minimap")),
                camera = CameraConfig.fromJson(json.optJSONObject("camera")),
                worldBounds = WorldBoundsConfig.fromJson(json.optJSONObject("world_bounds")),
                renderSettings = RenderSettingsConfig.fromJson(json.optJSONObject("render_settings")),
                server = ServerConfig.fromJson(json.optJSONObject("server"))
            )
        }

        fun parse(jsonString: String): OverlayConfig {
            return try {
                fromJson(JSONObject(jsonString))
            } catch (e: Exception) {
                OverlayConfig()
            }
        }
    }
}

/**
 * Observer callback interface for configuration updates.
 */
fun interface ConfigChangeListener {
    fun onConfigChanged(config: OverlayConfig)
}

/**
 * Thread-safe Configuration Manager handling persistent load/save across SharedPreferences
 * and synced with `minimap_config.json`.
 */
class ConfigManager(
    private val context: Context? = null,
    private val customConfigFile: File? = null
) {
    companion object {
        private const val PREFS_NAME = "vemins_esp_config"
        private const val BACKUP_CONFIG_NAME = "minimap_config.json.bak"
        private const val TMP_CONFIG_NAME = "minimap_config.json.tmp"

        @Volatile
        private var instance: ConfigManager? = null

        fun getInstance(context: Context? = null, file: File? = null): ConfigManager {
            return instance ?: synchronized(this) {
                instance ?: ConfigManager(context?.applicationContext ?: context, file).also { instance = it }
            }
        }
    }

    private val lock = Any()
    private var activeConfig: OverlayConfig = OverlayConfig()
    private val listeners = CopyOnWriteArrayList<ConfigChangeListener>()
    private val prefs: SharedPreferences? = context?.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    private val configFile: File
        get() {
            if (customConfigFile != null) return customConfigFile
            if (context != null) {
                return File(context.filesDir, "minimap_config.json")
            }
            return File("/sdcard/Download/minimap_config.json")
        }

    init {
        loadConfig()
    }

    /**
     * Retrieves a copy of the current active configuration.
     */
    fun getConfig(): OverlayConfig {
        synchronized(lock) {
            return activeConfig.deepCopy()
        }
    }

    /**
     * Registers a listener to be notified immediately on configuration changes.
     */
    fun addListener(listener: ConfigChangeListener) {
        listeners.addIfAbsent(listener)
        // Immediately notify with current config
        listener.onConfigChanged(getConfig())
    }

    /**
     * Unregisters a previously added configuration listener.
     */
    fun removeListener(listener: ConfigChangeListener) {
        listeners.remove(listener)
    }

    /**
     * Loads the configuration from disk / SharedPreferences. Falls back to default if file is missing or invalid.
     */
    fun loadConfig(): OverlayConfig {
        synchronized(lock) {
            var loaded = false

            // 1. Try loading from SharedPreferences first (fastest and safest on Android)
            if (prefs != null && prefs.contains("config_json")) {
                try {
                    val jsonStr = prefs.getString("config_json", null)
                    if (!jsonStr.isNullOrBlank()) {
                        activeConfig = OverlayConfig.parse(jsonStr)
                        loaded = true
                    }
                } catch (e: Exception) {
                    System.err.println("[ConfigManager] Error reading SharedPreferences: ${e.message}")
                }
            }

            // 2. Try loading from primary JSON File
            if (!loaded) {
                try {
                    val file = configFile
                    if (file.exists() && file.canRead()) {
                        val content = file.readText(Charsets.UTF_8)
                        if (content.isNotBlank()) {
                            val json = JSONObject(content)
                            activeConfig = OverlayConfig.fromJson(json)
                            loaded = true
                        }
                    }
                } catch (e: Exception) {
                    System.err.println("[ConfigManager] Error reading config file: ${e.message}")
                }
            }

            // 3. Try loading from fallback shared storage / Termux paths
            if (!loaded) {
                val candidatePaths = listOf(
                    "/sdcard/Download/minimap_config.json",
                    "/sdcard/veminsEsp/minimap_config.json",
                    "/data/data/com.termux/files/home/veminsEsp/minimap_config.json"
                )
                for (p in candidatePaths) {
                    try {
                        val f = File(p)
                        if (f.exists() && f.canRead()) {
                            val content = f.readText(Charsets.UTF_8)
                            if (content.isNotBlank()) {
                                activeConfig = OverlayConfig.fromJson(JSONObject(content))
                                loaded = true
                                break
                            }
                        }
                    } catch (_: Exception) {}
                }
            }

            // 4. Default configuration
            if (!loaded) {
                activeConfig = OverlayConfig()
            }
            saveToSharedPreferences()

            notifyListeners()
            return activeConfig.deepCopy()
        }
    }

    /**
     * Atomically saves the current active configuration to disk and SharedPreferences.
     */
    fun saveConfig(): Boolean {
        synchronized(lock) {
            saveToSharedPreferences()
            return try {
                val jsonString = activeConfig.toJson().toString(2)

                // Save to app internal files directory
                writeJsonToFile(configFile, jsonString)

                // Also try syncing to /sdcard/Download if accessible
                try {
                    val sdFile = File("/sdcard/Download/minimap_config.json")
                    if (sdFile.parentFile?.exists() == true || sdFile.parentFile?.mkdirs() == true) {
                        writeJsonToFile(sdFile, jsonString)
                    }
                } catch (_: Exception) {}

                true
            } catch (e: Exception) {
                System.err.println("[ConfigManager] Failed to save config file: ${e.message}")
                true // still return true since SharedPreferences succeeded
            }
        }
    }

    private fun writeJsonToFile(targetFile: File, jsonContent: String) {
        try {
            val parentDir = targetFile.parentFile
            if (parentDir != null && !parentDir.exists()) {
                parentDir.mkdirs()
            }

            val tmpFile = File(parentDir ?: File("."), "${targetFile.name}.tmp")
            FileOutputStream(tmpFile).use { fos ->
                OutputStreamWriter(fos, Charsets.UTF_8).use { writer ->
                    writer.write(jsonContent)
                    writer.flush()
                }
            }

            if (targetFile.exists()) {
                val backupFile = File(parentDir ?: File("."), "${targetFile.name}.bak")
                try { targetFile.copyTo(backupFile, overwrite = true) } catch (_: Exception) {}
            }

            if (!tmpFile.renameTo(targetFile)) {
                try {
                    tmpFile.copyTo(targetFile, overwrite = true)
                    tmpFile.delete()
                } catch (_: Exception) {}
            }
        } catch (e: Exception) {
            System.err.println("[ConfigManager] writeJsonToFile error: ${e.message}")
        }
    }

    private fun saveToSharedPreferences() {
        try {
            prefs?.edit()?.apply {
                putString("config_json", activeConfig.toJson().toString())
                putFloat("minimap_x", activeConfig.minimap.posX)
                putFloat("minimap_y", activeConfig.minimap.posY)
                putFloat("minimap_width", activeConfig.minimap.width)
                putFloat("minimap_height", activeConfig.minimap.height)
                putFloat("minimap_alpha", activeConfig.minimap.alpha)
                putFloat("camera_scale_x", activeConfig.camera.scaleX)
                putFloat("camera_scale_y", activeConfig.camera.scaleY)
                putFloat("camera_lift", activeConfig.camera.hudOffsetY)
                putFloat("edge_margin", activeConfig.camera.edgeMargin)
                apply()
            }
        } catch (_: Exception) {}
    }

    /**
     * Updates minimap viewport coordinates, dimensions, alpha and rotation.
     */
    fun updateMinimap(
        posX: Float,
        posY: Float,
        width: Float,
        height: Float,
        alpha: Float? = null,
        invertY: Boolean? = null,
        diamondMode: Boolean? = null
    ) {
        synchronized(lock) {
            activeConfig.minimap.posX = posX
            activeConfig.minimap.posY = posY
            activeConfig.minimap.width = width
            activeConfig.minimap.height = height
            if (alpha != null) {
                activeConfig.minimap.alpha = alpha.coerceIn(0.1f, 1.0f)
            }
            if (invertY != null) {
                activeConfig.minimap.invertY = invertY
            }
            if (diamondMode != null) {
                activeConfig.minimap.diamondMode = diamondMode
                activeConfig.minimap.rotationDegrees = if (diamondMode) 45.0f else 0.0f
            }
        }
        saveToSharedPreferences()
        notifyListeners()
    }

    /**
     * Updates camera isometric projection scaling and HUD offset.
     */
    fun updateCamera(scaleX: Float, scaleY: Float, hudOffsetY: Float, highCamera: Boolean? = null) {
        synchronized(lock) {
            activeConfig.camera.scaleX = scaleX
            activeConfig.camera.scaleY = scaleY
            activeConfig.camera.hudOffsetY = hudOffsetY
            if (highCamera != null) {
                activeConfig.camera.highCamera = highCamera
            }
        }
        saveToSharedPreferences()
        notifyListeners()
    }

    /**
     * Updates edge radar margins and maximum detection distance.
     */
    fun updateRadar(edgeMargin: Float, maxRadarDistance: Float) {
        synchronized(lock) {
            activeConfig.camera.edgeMargin = edgeMargin
            activeConfig.camera.maxRadarDistance = maxRadarDistance
        }
        saveToSharedPreferences()
        notifyListeners()
    }

    /**
     * Updates visual element sizing (hero portraits, minion dots, monster dots, HUD badges, and HP bar scale).
     */
    fun updateSizing(
        heroDotRadius: Float? = null,
        minionDotRadius: Float? = null,
        monsterDotRadius: Float? = null,
        hudBadgeRadius: Float? = null,
        hudHpBarScale: Float? = null
    ) {
        synchronized(lock) {
            if (heroDotRadius != null) {
                activeConfig.renderSettings.minimapHeroDotRadius = heroDotRadius.coerceIn(5.0f, 35.0f)
            }
            if (minionDotRadius != null) {
                activeConfig.renderSettings.minimapMinionDotRadius = minionDotRadius.coerceIn(2.0f, 15.0f)
            }
            if (monsterDotRadius != null) {
                activeConfig.renderSettings.minimapMonsterDotRadius = monsterDotRadius.coerceIn(3.0f, 25.0f)
            }
            if (hudBadgeRadius != null) {
                activeConfig.renderSettings.hudBadgeRadius = hudBadgeRadius.coerceIn(5.0f, 25.0f)
            }
            if (hudHpBarScale != null) {
                activeConfig.renderSettings.hudHpBarScale = hudHpBarScale.coerceIn(0.5f, 2.5f)
            }
        }
        saveToSharedPreferences()
        notifyListeners()
    }

    /**
     * Updates a single render toggle by key name.
     */
    fun updateRenderToggle(key: String, enabled: Boolean) {
        synchronized(lock) {
            when (key) {
                "minimap_show_enemies" -> activeConfig.renderSettings.minimapShowEnemies = enabled
                "minimap_show_allies" -> activeConfig.renderSettings.minimapShowAllies = enabled
                "minimap_show_arrows" -> activeConfig.renderSettings.minimapShowArrows = enabled
                "minimap_show_minions" -> activeConfig.renderSettings.minimapShowMinions = enabled
                "minimap_show_monsters" -> activeConfig.renderSettings.minimapShowMonsters = enabled
                "screen_show_overhead_hp" -> activeConfig.renderSettings.screenShowOverheadHp = enabled
                "screen_show_shields" -> activeConfig.renderSettings.screenShowShields = enabled
                "screen_show_skill_cooldowns" -> activeConfig.renderSettings.screenShowSkillCooldowns = enabled
                "screen_show_ult_badge" -> activeConfig.renderSettings.screenShowUltBadge = enabled
                "screen_show_spell_badge" -> activeConfig.renderSettings.screenShowSpellBadge = enabled
                "screen_show_battle_spell" -> activeConfig.renderSettings.screenShowBattleSpell = enabled
                "screen_show_distance" -> activeConfig.renderSettings.screenShowDistance = enabled
                "screen_show_edge_radar" -> activeConfig.renderSettings.screenShowEdgeRadar = enabled
                "screen_show_hero_names" -> activeConfig.renderSettings.screenShowHeroNames = enabled
                "screen_show_health_text" -> activeConfig.renderSettings.screenShowHealthText = enabled
                "invert_y" -> activeConfig.minimap.invertY = enabled
                "diamond_mode" -> {
                    activeConfig.minimap.diamondMode = enabled
                    activeConfig.minimap.rotationDegrees = if (enabled) 45.0f else 0.0f
                }
                "high_camera" -> activeConfig.camera.highCamera = enabled
            }
        }
        saveToSharedPreferences()
        notifyListeners()
    }

    /**
     * Updates screen resolution dimensions.
     */
    fun updateScreenDimensions(width: Float, height: Float) {
        synchronized(lock) {
            activeConfig.screen.width = width
            activeConfig.screen.height = height
        }
        notifyListeners()
    }

    /**
     * Replaces the active configuration entirely.
     */
    fun updateFullConfig(newConfig: OverlayConfig, autoSave: Boolean = true) {
        synchronized(lock) {
            activeConfig = newConfig.deepCopy()
        }
        if (autoSave) {
            saveConfig()
        } else {
            saveToSharedPreferences()
        }
        notifyListeners()
    }

    fun toJson(): JSONObject = getConfig().toJson()

    fun updateFromJson(json: JSONObject) {
        val newConfig = OverlayConfig.fromJson(json)
        updateFullConfig(newConfig, autoSave = true)
    }

    /**
     * Resets all parameters to factory defaults and persists to disk.
     */
    fun resetToDefaults() {
        synchronized(lock) {
            activeConfig = OverlayConfig()
        }
        saveConfig()
        notifyListeners()
    }

    /**
     * Loads a pre-calibrated layout preset.
     */
    fun loadPreset(presetName: String) {
        synchronized(lock) {
            when (presetName.toLowerCase()) {
                "default", "standard" -> {
                    activeConfig.minimap.posX = 75.0f
                    activeConfig.minimap.posY = 15.0f
                    activeConfig.minimap.width = 320.0f
                    activeConfig.minimap.height = 320.0f
                    activeConfig.minimap.diamondMode = false
                    activeConfig.minimap.rotationDegrees = 0.0f
                    activeConfig.camera.scaleX = 38.0f
                    activeConfig.camera.scaleY = 27.0f
                    activeConfig.camera.hudOffsetY = 65.0f
                }
                "diamond", "diamond_radar" -> {
                    activeConfig.minimap.posX = 75.0f
                    activeConfig.minimap.posY = 15.0f
                    activeConfig.minimap.width = 340.0f
                    activeConfig.minimap.height = 340.0f
                    activeConfig.minimap.diamondMode = true
                    activeConfig.minimap.rotationDegrees = 45.0f
                }
                "notch_safe", "compact" -> {
                    activeConfig.minimap.posX = 110.0f
                    activeConfig.minimap.posY = 20.0f
                    activeConfig.minimap.width = 280.0f
                    activeConfig.minimap.height = 280.0f
                }
                "ultrawide", "tablet" -> {
                    activeConfig.minimap.posX = 120.0f
                    activeConfig.minimap.posY = 25.0f
                    activeConfig.minimap.width = 380.0f
                    activeConfig.minimap.height = 380.0f
                    activeConfig.camera.scaleX = 42.0f
                    activeConfig.camera.scaleY = 30.0f
                }
            }
        }
        saveConfig()
        notifyListeners()
    }

    private fun notifyListeners() {
        val snapshot = getConfig()
        for (listener in listeners) {
            try {
                listener.onConfigChanged(snapshot)
            } catch (e: Exception) {
                System.err.println("[ConfigManager] Listener threw exception: ${e.message}")
            }
        }
    }
}

