package com.vemins.esp.view

import android.content.Context
import android.graphics.*
import android.util.AttributeSet
import android.view.View
import com.vemins.esp.config.ConfigManager
import com.vemins.esp.config.OverlayConfig
import kotlin.math.cos
import kotlin.math.sin

/**
 * Interactive Live Preview Canvas embedded directly inside MainActivity.
 *
 * Renders a scaled real-time simulation of both:
 * 1. Layer 1: Top-Left Minimap Radar with live Position, Dimensions, Alpha, and Diamond Rotation.
 * 2. Layer 2: Overhead Combat HUD & Off-Screen Edge Radar with Camera Scale, Lift, and Margin parameters.
 */
class PreviewCanvasView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private val configManager = ConfigManager.getInstance(context)
    private var config: OverlayConfig = configManager.getConfig()

    // Paints
    private val paintBg = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#070A10")
        style = Paint.Style.FILL
    }

    private val paintGrid = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#152238")
        strokeWidth = 1f
        style = Paint.Style.STROKE
    }

    private val paintMinimapBg = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }

    private val paintMinimapBorder = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#00E5FF")
        strokeWidth = 1.5f
        style = Paint.Style.STROKE
    }

    private val paintHeroSelf = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#00E676")
        style = Paint.Style.FILL
    }

    private val paintHeroEnemy = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#FF1744")
        style = Paint.Style.FILL
    }

    private val paintHeroAlly = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#2979FF")
        style = Paint.Style.FILL
    }

    private val paintMinion = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#FF9100")
        style = Paint.Style.FILL
    }

    private val paintMonster = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#D500F9")
        style = Paint.Style.FILL
    }

    private val paintHpBg = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#CC121A29")
        style = Paint.Style.FILL
    }

    private val paintHpFill = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#FF1744")
        style = Paint.Style.FILL
    }

    private val paintShieldFill = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#CCFFFFFF")
        style = Paint.Style.FILL
    }

    private val paintBadgeUlt = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#CC00E676")
        style = Paint.Style.FILL
    }

    private val paintBadgeSpell = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#CC2979FF")
        style = Paint.Style.FILL
    }

    private val paintTextWhite = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 9f
        textAlign = Paint.Align.CENTER
        typeface = Typeface.DEFAULT_BOLD
    }

    private val paintTextLabel = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#94A3B8")
        textSize = 9f
        textAlign = Paint.Align.CENTER
    }

    private val paintEdgeChevron = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#FFD600")
        style = Paint.Style.FILL
    }

    private val scratchRect = RectF()
    private val scratchPath = Path()

    init {
        configManager.addListener { newCfg ->
            post {
                config = newCfg
                invalidate()
            }
        }
    }

    fun setConfig(newConfig: OverlayConfig) {
        config = newConfig
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat()
        val h = height.toFloat()
        if (w <= 0 || h <= 0) return

        // 1. Canvas Background with subtle grid lines
        canvas.drawRect(0f, 0f, w, h, paintBg)
        val step = 30f
        var x = 0f
        while (x < w) {
            canvas.drawLine(x, 0f, x, h, paintGrid)
            x += step
        }
        var y = 0f
        while (y < h) {
            canvas.drawLine(0f, y, w, y, paintGrid)
            y += step
        }

        // Compute scaling ratio from reference game resolution (2400x1080) to preview canvas
        val scaleX = w / config.screen.width
        val scaleY = h / config.screen.height

        val m = config.minimap
        val r = config.renderSettings
        val c = config.camera

        // -------------------------------------------------------------
        // LAYER 1: MINIMAP RADAR PREVIEW
        // -------------------------------------------------------------
        val mapX = m.posX * scaleX
        val mapY = m.posY * scaleY
        val mapW = m.width * scaleX
        val mapH = m.height * scaleY
        val mapAlphaInt = (m.alpha * 255).toInt().coerceIn(20, 255)

        paintMinimapBg.color = Color.argb(mapAlphaInt, 12, 18, 30)

        canvas.save()
        val mapCenterX = mapX + mapW / 2f
        val mapCenterY = mapY + mapH / 2f

        if (m.diamondMode || m.rotationDegrees != 0f) {
            canvas.rotate(if (m.diamondMode) 45f else m.rotationDegrees, mapCenterX, mapCenterY)
        }

        scratchRect.set(mapX, mapY, mapX + mapW, mapY + mapH)
        canvas.drawRoundRect(scratchRect, 6f, 6f, paintMinimapBg)
        canvas.drawRoundRect(scratchRect, 6f, 6f, paintMinimapBorder)

        // Draw Minimap Content Primitives
        // Local Hero (Self - Green)
        val selfX = mapCenterX - mapW * 0.15f
        val selfY = mapCenterY + mapH * 0.15f
        val heroRadiusPreview = (r.minimapHeroDotRadius * 0.55f).coerceIn(3f, 16f)
        canvas.drawCircle(selfX, selfY, heroRadiusPreview, paintHeroSelf)

        // Minions (Orange / Blue)
        if (r.minimapShowMinions) {
            val minionRadiusPreview = (r.minimapMinionDotRadius * 0.6f).coerceIn(1.5f, 6f)
            canvas.drawCircle(mapCenterX - mapW * 0.05f, mapCenterY + mapH * 0.05f, minionRadiusPreview, paintMinion)
            canvas.drawCircle(mapCenterX + mapW * 0.05f, mapCenterY - mapH * 0.05f, minionRadiusPreview, paintMinion)
        }

        // Jungle Boss (Purple)
        if (r.minimapShowMonsters) {
            val monsterRadiusPreview = (r.minimapMonsterDotRadius * 0.55f).coerceIn(2.5f, 10f)
            canvas.drawCircle(mapCenterX, mapCenterY, monsterRadiusPreview, paintMonster)
        }

        // Enemy Hero (Red)
        if (r.minimapShowEnemies) {
            val enemyMapX = mapCenterX + mapW * 0.2f
            val enemyMapY = mapCenterY - mapH * 0.2f
            canvas.drawCircle(enemyMapX, enemyMapY, heroRadiusPreview, paintHeroEnemy)
            if (r.minimapShowArrows) {
                canvas.drawLine(enemyMapX, enemyMapY, enemyMapX - 8f, enemyMapY + 4f, paintHeroEnemy)
            }
        }

        // Ally Hero (Blue)
        if (r.minimapShowAllies) {
            val allyMapX = mapCenterX - mapW * 0.25f
            val allyMapY = mapCenterY - mapH * 0.1f
            canvas.drawCircle(allyMapX, allyMapY, heroRadiusPreview, paintHeroAlly)
        }

        canvas.restore()

        // Radar Label
        canvas.drawText("RADAR [${m.width.toInt()}x${m.height.toInt()}]", mapCenterX, mapY + mapH + 12f, paintTextLabel)

        // -------------------------------------------------------------
        // LAYER 2: OVERHEAD COMBAT HUD PREVIEW (Center / Right of Screen)
        // -------------------------------------------------------------
        val hudBaseX = w * 0.65f
        // Lift offset scaled
        val hudLift = c.hudOffsetY * scaleY
        val hudBaseY = (h * 0.55f) - hudLift

        if (r.screenShowOverheadHp) {
            val barW = 75f * r.hudHpBarScale
            val barH = 7f * r.hudHpBarScale
            val left = hudBaseX - barW / 2f
            val top = hudBaseY

            // HP Bar Background
            scratchRect.set(left - 1f, top - 1f, left + barW + 1f, top + barH + 1f)
            canvas.drawRoundRect(scratchRect, 2f, 2f, paintHpBg)

            // HP Bar Fill (65%)
            val hpFillW = barW * 0.65f
            scratchRect.set(left, top, left + hpFillW, top + barH)
            canvas.drawRoundRect(scratchRect, 2f, 2f, paintHpFill)

            // Shield Fill (15%)
            if (r.screenShowShields) {
                scratchRect.set(left + hpFillW, top, left + hpFillW + barW * 0.15f, top + barH)
                canvas.drawRect(scratchRect, paintShieldFill)
            }

            // Health Text Readout
            if (r.screenShowHealthText) {
                canvas.drawText("3,450 / 5,100", hudBaseX, top + barH - 1f, paintTextWhite)
            }

            // Cooldown Badges Row
            if (r.screenShowSkillCooldowns) {
                var badgeX = left
                val badgeScale = (r.hudBadgeRadius / 9.0f).coerceIn(0.6f, 1.8f)
                val badgeW = 24f * badgeScale
                val badgeH = 9f * badgeScale
                if (r.screenShowUltBadge) {
                    scratchRect.set(badgeX, top - (badgeH + 2f), badgeX + badgeW, top - 2f)
                    canvas.drawRoundRect(scratchRect, 2f, 2f, paintBadgeUlt)
                    canvas.drawText("ULT", badgeX + badgeW / 2f, top - (badgeH * 0.3f), paintTextWhite)
                    badgeX += badgeW + 2f
                }
                if (r.screenShowSpellBadge) {
                    scratchRect.set(badgeX, top - (badgeH + 2f), badgeX + badgeW, top - 2f)
                    canvas.drawRoundRect(scratchRect, 2f, 2f, paintBadgeSpell)
                    canvas.drawText("SPL", badgeX + badgeW / 2f, top - (badgeH * 0.3f), paintTextWhite)
                }
            }

            // Distance Text
            if (r.screenShowDistance) {
                canvas.drawText("Hero #18 (14.2m)", hudBaseX, top + barH + 10f, paintTextWhite)
            }

            // Draw Hero Placeholder model
            canvas.drawCircle(hudBaseX, hudBaseY + 28f, 10f, paintHeroEnemy)
        }

        // -------------------------------------------------------------
        // LAYER 3: OFF-SCREEN EDGE RADAR CHEVRON PREVIEW
        // -------------------------------------------------------------
        if (r.screenShowEdgeRadar) {
            val edgeMarginScaled = c.edgeMargin * scaleX
            val chevronX = (w - edgeMarginScaled).coerceIn(20f, w - 10f)
            val chevronY = h * 0.35f

            scratchPath.reset()
            scratchPath.moveTo(chevronX, chevronY)
            scratchPath.lineTo(chevronX - 8f, chevronY - 6f)
            scratchPath.lineTo(chevronX - 5f, chevronY)
            scratchPath.lineTo(chevronX - 8f, chevronY + 6f)
            scratchPath.close()

            canvas.drawPath(scratchPath, paintEdgeChevron)
            canvas.drawText("28m", chevronX - 6f, chevronY + 14f, paintTextWhite)
        }
    }
}
