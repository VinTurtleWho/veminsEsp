package com.vemins.esp.model

/**
 * Immutable configuration defining screen layout, minimap viewport, camera projection parameters,
 * and visual rendering toggles for the VEMINS ESP overlay.
 */
data class MinimapConfig(
    // Screen Resolution
    val screenWidth: Float = 2400.0f,
    val screenHeight: Float = 1080.0f,

    // Layer 1: Minimap Viewport Bounds
    val mapPosX: Float = 75.0f,
    val mapPosY: Float = 15.0f,
    val mapWidth: Float = 320.0f,
    val mapHeight: Float = 320.0f,
    val mapAlpha: Float = 0.85f,
    val rotationDegrees: Float = 0.0f,
    val radarZoom: Float = 1.0f,
    val stretchX: Float = 1.0f,
    val stretchY: Float = 1.0f,
    val invertY: Boolean = true,

    // Layer 2: 3D-to-2D Isometric Camera & Top CD Bar Calibration
    val scaleX: Float = 38.0f,
    val scaleY: Float = 27.0f,
    val hudOffsetY: Float = 65.0f,
    val edgeMargin: Float = 45.0f,
    val maxRadarDistance: Float = 45.0f,
    val highCamera: Boolean = true,
    val usePerspective: Boolean = true,
    val cameraPitch: Float = 58.0f,
    val showTopCdBar: Boolean = true,
    val topCdBarPosY: Float = 28.0f,
    val topCdBarScale: Float = 1.0f,

    // World Cartesian Coordinate Bounds
    val minX: Float = -52.0f,
    val maxX: Float = 52.0f,
    val minY: Float = -52.0f,
    val maxY: Float = 52.0f,

    // Visual Render Toggles & Styles (Layer 1 - Minimap)
    val minimapShowEnemies: Boolean = true,
    val minimapShowAllies: Boolean = false,
    val minimapShowArrows: Boolean = true,
    val minimapShowMinions: Boolean = true,
    val minimapShowMonsters: Boolean = true,
    val minimapHeroDotRadius: Float = 9.0f,
    val minimapArrowLength: Float = 18.0f,
    val minimapMinionDotRadius: Float = 3.5f,
    val minimapMonsterDotRadius: Float = 7.0f,

    // Visual Render Toggles & Styles (Layer 2 - Main Screen Overhead HUD & Top CD Bar)
    val screenShowOverheadHp: Boolean = true,
    val screenShowSkillCooldowns: Boolean = true,
    val screenShowUltBadge: Boolean = true,
    val screenShowSpellBadge: Boolean = true,
    val screenShowBattleSpell: Boolean = true,
    val screenShowDistance: Boolean = true,
    val screenShowEdgeRadar: Boolean = false,
    val screenShowHeroNames: Boolean = true,
    val screenShowHealthText: Boolean = true,
    val screenShowShields: Boolean = true,
    val hudBadgeRadius: Float = 9.0f,
    val hudHpBarScale: Float = 1.0f,
    val hideInRecording: Boolean = false
) {
    val worldWidth: Float
        get() = if (maxX != minX) maxX - minX else 104.0f

    val worldHeight: Float
        get() = if (maxY != minY) maxY - minY else 104.0f

    val screenCenterX: Float
        get() = screenWidth / 2.0f

    val screenCenterY: Float
        get() = screenHeight / 2.0f
}

