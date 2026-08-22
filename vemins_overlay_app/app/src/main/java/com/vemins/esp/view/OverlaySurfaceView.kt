package com.vemins.esp.view

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.PorterDuff
import android.graphics.Rect
import android.graphics.RectF
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.Process
import android.util.AttributeSet
import android.util.Log
import android.view.SurfaceHolder
import android.view.SurfaceView
import com.vemins.esp.assets.IconCacheManager
import com.vemins.esp.math.EdgeRadarResult
import com.vemins.esp.math.IsometricProjection
import com.vemins.esp.math.IsometricResult
import com.vemins.esp.math.MinimapProjection
import com.vemins.esp.math.Point2D
import com.vemins.esp.math.safeCoerceIn
import com.vemins.esp.model.AbilityInfo
import com.vemins.esp.model.FrameSnapshot
import com.vemins.esp.model.HeroEntity
import com.vemins.esp.model.MinimapConfig
import com.vemins.esp.model.MonsterEntity
import com.vemins.esp.model.SoldierEntity
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import kotlin.math.cos
import kotlin.math.sin

/**
 * High-Performance 60 FPS Hardware-Accelerated SurfaceView Rendering Engine.
 *
 * Dedicated transparent floating overlay canvas for VEMINS ESP.
 *
 * Architecture Highlights:
 * 1. Dedicated High-Priority [RenderThread] (`THREAD_PRIORITY_URGENT_DISPLAY`).
 * 2. Hardware-accelerated canvas via `lockHardwareCanvas()` (API 23+) with automatic fallback.
 * 3. Double-buffered atomic snapshot updates using [AtomicReference] (zero lock contention).
 * 4. Zero-allocation draw passes: All [Paint], [Path], [RectF], and transform containers are pre-allocated.
 * 5. Integrated with [IconCacheManager] for circular-cropped hero portraits, skill badges, and battle spell icons.
 * 6. Decoupled Dual-Layer Rendering:
 *    - Layer 1: Top-Left Minimap Viewport Radar (45° diamond coordinate projection, hero portraits, heading vectors).
 *    - Layer 2: Main In-Game Screen Overhead Combat HUD (HP/Shield bars, Ult & Spell CD sweeps) & Perimeter Edge Radar.
 */
class OverlaySurfaceView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : SurfaceView(context, attrs, defStyleAttr), SurfaceHolder.Callback {

    companion object {
        private const val TAG = "OverlaySurfaceView"
        private const val TARGET_FPS = 60
        private const val FRAME_PERIOD_NS = 1_000_000_000L / TARGET_FPS
    }

    // Atomic Thread-Safe State
    private val snapshotRef = AtomicReference<FrameSnapshot>(FrameSnapshot.EMPTY)
    private val configRef = AtomicReference<MinimapConfig>(MinimapConfig())

    // Projection Engines
    private val minimapProjection = MinimapProjection(configRef.get())
    private val isometricProjection = IsometricProjection(configRef.get())

    // In-Memory Asset Pipeline & Icon Cache
    private val iconCache = IconCacheManager.getInstance(context)

    // Render Thread Management & Supervisor Watchdog
    private var renderThread: RenderThread? = null
    private val isSurfaceReady = AtomicBoolean(false)
    private val watchdogHandler = Handler(Looper.getMainLooper())
    private val watchdogRunnable = object : Runnable {
        override fun run() {
            try {
                if (isSurfaceReady.get()) {
                    val current = renderThread
                    if (current == null || !current.isAlive || !current.isRunning.get()) {
                        Log.w(TAG, "Watchdog detected dead or stopped RenderThread. Auto-reviving...")
                        startRenderThread()
                    }
                }
            } catch (t: Throwable) {
                Log.e(TAG, "Error in RenderThread watchdog supervisor", t)
            } finally {
                if (isSurfaceReady.get()) {
                    watchdogHandler.postDelayed(this, 500L)
                }
            }
        }
    }

    // Persistent Local Player Camera Tracking & EMA Smoothing
    @Volatile
    private var lastKnownLocalX: Float = 0.0f
    @Volatile
    private var lastKnownLocalY: Float = 0.0f
    @Volatile
    private var hasValidLocalPos: Boolean = false

    // Set-cached Hero Preloading (avoids redundant preloadCommon calls)
    @Volatile
    private var lastPreloadedHeroIds: Set<Int> = emptySet()

    // Performance & FPS Diagnostics
    var showFpsCounter: Boolean = true
    private var measuredFps: Float = 60.0f

    // -------------------------------------------------------------------------
    // PRE-ALLOCATED GRAPHICS ASSETS (ZERO HEAP ALLOCATION PER FRAME)
    // -------------------------------------------------------------------------

    // --- Pre-allocated Math Scratch Holders ---
    private val scratchPointA = Point2D()
    private val scratchPointB = Point2D()
    private val scratchIsoResult = IsometricResult()
    private val scratchEdgeRadarResult = EdgeRadarResult()

    // --- Pre-allocated Geometry Paths & Rects ---
    private val scratchRectF = RectF()
    private val scratchDstRect = RectF()
    private val scratchSrcRect = Rect()
    private val scratchHpBgRect = RectF()
    private val scratchHpFillRect = RectF()
    private val scratchShieldRect = RectF()
    private val scratchBadgeRect = RectF()
    private val scratchSweepRect = RectF()
    private val scratchPath = Path()
    private val scratchArrowPath = Path()

    // --- Paints: Minimap Layer ---
    private val paintMinimapBg = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(120, 10, 15, 26)
        style = Paint.Style.FILL
    }

    private val paintMinimapBorder = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(200, 0, 229, 255) // Cyan glow
        style = Paint.Style.STROKE
        strokeWidth = 1.5f
    }

    private val paintHeroSelf = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(0, 230, 118) // Green
        style = Paint.Style.FILL
    }

    private val paintHeroAlly = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(33, 150, 243) // Blue
        style = Paint.Style.FILL
    }

    private val paintHeroEnemy = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(229, 57, 53) // Red
        style = Paint.Style.FILL
    }

    private val paintBorderSelf = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(0, 230, 118)
        style = Paint.Style.STROKE
        strokeWidth = 2.0f
    }

    private val paintBorderAlly = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(33, 150, 243)
        style = Paint.Style.STROKE
        strokeWidth = 2.0f
    }

    private val paintBorderEnemy = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(229, 57, 53)
        style = Paint.Style.STROKE
        strokeWidth = 2.0f
    }

    private val paintHeroStrokeWhite = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 1.5f
    }

    private val paintArrowSelf = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(0, 255, 128)
        style = Paint.Style.STROKE
        strokeWidth = 2.5f
        strokeCap = Paint.Cap.ROUND
    }

    private val paintArrowEnemy = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(255, 64, 64)
        style = Paint.Style.STROKE
        strokeWidth = 2.5f
        strokeCap = Paint.Cap.ROUND
    }

    private val paintArrowAlly = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(64, 160, 255)
        style = Paint.Style.STROKE
        strokeWidth = 2.0f
        strokeCap = Paint.Cap.ROUND
    }

    private val paintMinionAlly = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(79, 195, 247) // Light Blue
        style = Paint.Style.FILL
    }

    private val paintMinionEnemy = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(255, 112, 67) // Coral Red
        style = Paint.Style.FILL
    }

    private val paintMonsterLord = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(255, 215, 0) // Gold
        style = Paint.Style.FILL
    }

    private val paintMonsterTurtle = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(0, 229, 255) // Cyan
        style = Paint.Style.FILL
    }

    private val paintMonsterBuffBlue = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(171, 71, 188) // Purple
        style = Paint.Style.FILL
    }

    private val paintMonsterBuffRed = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(255, 138, 101) // Orange
        style = Paint.Style.FILL
    }

    private val paintMonsterCreep = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(189, 189, 189) // Grey
        style = Paint.Style.FILL
    }

    // --- Paints: Main Screen Overhead Combat HUD ---
    private val paintHudBg = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(200, 15, 18, 24)
        style = Paint.Style.FILL
    }

    private val paintHudBorder = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(220, 200, 200, 200)
        style = Paint.Style.STROKE
        strokeWidth = 1.0f
    }

    private val paintHpGreen = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(76, 175, 80)
        style = Paint.Style.FILL
    }

    private val paintHpYellow = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(255, 214, 0)
        style = Paint.Style.FILL
    }

    private val paintHpRed = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(244, 67, 54)
        style = Paint.Style.FILL
    }

    private val paintShieldWhite = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(220, 255, 255, 255)
        style = Paint.Style.FILL
    }

    private val paintShieldMagic = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(220, 0, 229, 255)
        style = Paint.Style.FILL
    }

    private val paintBadgeReady = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(230, 46, 125, 50) // Emerald Green
        style = Paint.Style.FILL
    }

    private val paintBadgeCd = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(230, 198, 40, 40) // Dark Red
        style = Paint.Style.FILL
    }

    private val paintBadgeSpell = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(230, 21, 101, 192) // Dark Blue
        style = Paint.Style.FILL
    }

    private val paintCooldownSweep = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(170, 0, 0, 0)
        style = Paint.Style.FILL
    }

    private val paintBitmapFilter = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG).apply {
        isDither = true
    }

    // --- Paints: Text & Typography ---
    private val paintTextMinimapHero = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 9.0f
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
        setShadowLayer(2.0f, 1.0f, 1.0f, Color.BLACK)
    }

    private val paintTextHp = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 9.5f
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
        setShadowLayer(2.0f, 1.0f, 1.0f, Color.BLACK)
    }

    private val paintTextHeroName = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 10.0f
        textAlign = Paint.Align.LEFT
        isFakeBoldText = true
        setShadowLayer(2.0f, 1.0f, 1.0f, Color.BLACK)
    }

    private val paintTextLevel = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(255, 215, 0)
        textSize = 9.0f
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
    }

    private val paintTextBadge = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 8.5f
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
        setShadowLayer(1.5f, 1.0f, 1.0f, Color.BLACK)
    }

    private val paintTextDistance = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(255, 235, 59)
        textSize = 10.0f
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
        setShadowLayer(2.0f, 1.0f, 1.0f, Color.BLACK)
    }

    // --- Paints: Off-Screen Edge Radar ---
    private val paintRadarChevronFill = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(230, 229, 57, 53)
        style = Paint.Style.FILL
    }

    private val paintRadarChevronReadyFill = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(240, 255, 179, 0) // Amber Alert if Ult is ready
        style = Paint.Style.FILL
    }

    private val paintRadarChevronStroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 1.5f
    }

    private val paintRadarPillBg = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(210, 20, 24, 33)
        style = Paint.Style.FILL
    }

    private val paintFps = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(0, 255, 0)
        textSize = 18.0f
        textAlign = Paint.Align.LEFT
        isFakeBoldText = true
        setShadowLayer(3.0f, 1.0f, 1.0f, Color.BLACK)
    }

    init {
        holder.addCallback(this)
        holder.setFormat(PixelFormat.TRANSLUCENT)
        setZOrderOnTop(true)
    }

    // Grace period caching to prevent 1-frame blank flashes during match transitions
    @Volatile
    private var lastValidSnapshot: FrameSnapshot = FrameSnapshot.EMPTY
    @Volatile
    private var lastValidTimeNs: Long = 0L

    // -------------------------------------------------------------------------
    // PUBLIC API FOR ATOMIC STATE UPDATES
    // -------------------------------------------------------------------------

    /**
     * Atomically swaps the latest telemetry snapshot for the rendering thread.
     * Zero-allocation, non-blocking call.
     */
    fun updateSnapshot(snapshot: FrameSnapshot) {
        snapshotRef.set(snapshot)
        if (snapshot.inMatch || snapshot.isValid || snapshot.totalEntitiesCount > 0) {
            lastValidSnapshot = snapshot
            lastValidTimeNs = System.nanoTime()
        }

        // Set-cached hero preloading: preloadCommon is only called when active hero IDs actually change
        val activeHeroIds = HashSet<Int>(10)
        snapshot.localPlayer?.let { if (it.heroId > 0) activeHeroIds.add(it.heroId) }
        for (i in snapshot.enemies.indices) {
            val hId = snapshot.enemies[i].heroId
            if (hId > 0) activeHeroIds.add(hId)
        }
        for (i in snapshot.allies.indices) {
            val hId = snapshot.allies[i].heroId
            if (hId > 0) activeHeroIds.add(hId)
        }

        if (activeHeroIds.isNotEmpty() && activeHeroIds != lastPreloadedHeroIds) {
            lastPreloadedHeroIds = activeHeroIds
            iconCache.preloadCommon(activeHeroIds)
        }
    }

    /**
     * Atomically updates projection configuration and recalculates cached transforms.
     */
    @Synchronized
    fun updateConfig(config: MinimapConfig) {
        configRef.set(config)
        minimapProjection.updateConfig(config)
        isometricProjection.updateConfig(config)
    }

    /**
     * Returns the currently active configuration.
     */
    fun getConfig(): MinimapConfig = configRef.get()

    // -------------------------------------------------------------------------
    // SURFACE LIFECYCLE CALLBACKS
    // -------------------------------------------------------------------------

    override fun surfaceCreated(holder: SurfaceHolder) {
        Log.i(TAG, "Overlay Surface created. Initializing 60 FPS RenderThread & Watchdog.")
        isSurfaceReady.set(true)
        startRenderThread()
        startWatchdog()
    }

    override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) {
        Log.i(TAG, "Overlay Surface changed: ${width}x$height")
        val currentCfg = configRef.get()
        if (currentCfg.screenWidth != width.toFloat() || currentCfg.screenHeight != height.toFloat()) {
            val updated = currentCfg.copy(
                screenWidth = width.toFloat(),
                screenHeight = height.toFloat()
            )
            updateConfig(updated)
        }
    }

    override fun surfaceDestroyed(holder: SurfaceHolder) {
        Log.i(TAG, "Overlay Surface destroyed. Stopping RenderThread & Watchdog.")
        isSurfaceReady.set(false)
        stopWatchdog()
        stopRenderThread()
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        if (isSurfaceReady.get()) {
            startRenderThread()
            startWatchdog()
        }
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        stopWatchdog()
        stopRenderThread()
    }

    private fun startWatchdog() {
        watchdogHandler.removeCallbacks(watchdogRunnable)
        watchdogHandler.postDelayed(watchdogRunnable, 500L)
    }

    private fun stopWatchdog() {
        watchdogHandler.removeCallbacks(watchdogRunnable)
    }

    @Synchronized
    private fun startRenderThread() {
        if (!isSurfaceReady.get()) return
        val current = renderThread
        if (current != null && current.isAlive) {
            current.isRunning.set(true)
            return
        }
        renderThread = RenderThread(holder).apply {
            isRunning.set(true)
            start()
        }
    }

    @Synchronized
    private fun stopRenderThread() {
        renderThread?.let { thread ->
            thread.isRunning.set(false)
            thread.interrupt()
            var retry = true
            var attempts = 0
            while (retry && attempts < 5) {
                try {
                    thread.join(100)
                    retry = false
                } catch (e: InterruptedException) {
                    Thread.currentThread().interrupt()
                    break
                } catch (t: Throwable) {
                    break
                }
                attempts++
            }
        }
        renderThread = null
    }

    // -------------------------------------------------------------------------
    // DEDICATED HIGH-PRIORITY RENDER THREAD (60 FPS HARDWARE CANVAS LOOP)
    // -------------------------------------------------------------------------

    private inner class RenderThread(private val surfaceHolder: SurfaceHolder) : Thread("VeminsRenderThread") {
        val isRunning = AtomicBoolean(false)

        private var frameCount = 0
        private var lastFpsTimestampNs = System.nanoTime()

        override fun run() {
            try {
                try {
                    // Elevate thread priority for stutter-free display synchronization
                    Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_DISPLAY)
                } catch (t: Throwable) {
                    Log.w(TAG, "Could not set THREAD_PRIORITY_URGENT_DISPLAY, using MAX_PRIORITY fallback: ${t.message}")
                    try {
                        priority = MAX_PRIORITY
                    } catch (ignored: Throwable) {}
                }

                while (isRunning.get()) {
                    try {
                        val frameStartNs = System.nanoTime()

                        if (isSurfaceReady.get() && surfaceHolder.surface.isValid) {
                            var canvas: Canvas? = null
                            try {
                                // Hardware-accelerated canvas (API 23+) with lockCanvas fallback
                                canvas = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                                    try {
                                        surfaceHolder.lockHardwareCanvas()
                                    } catch (e: Throwable) {
                                        try {
                                            surfaceHolder.lockCanvas()
                                        } catch (e2: Throwable) {
                                            null
                                        }
                                    }
                                } else {
                                    try {
                                        surfaceHolder.lockCanvas()
                                    } catch (e: Throwable) {
                                        null
                                    }
                                }

                                if (canvas != null) {
                                    renderFrame(canvas)
                                }
                            } catch (t: Throwable) {
                                Log.e(TAG, "Render pass exception", t)
                            } finally {
                                if (canvas != null) {
                                    try {
                                        surfaceHolder.unlockCanvasAndPost(canvas)
                                    } catch (t: Throwable) {
                                        Log.e(TAG, "unlockCanvasAndPost exception", t)
                                    }
                                }
                            }
                        }

                        // FPS & Performance Tracking
                        frameCount++
                        val nowNs = System.nanoTime()
                        val elapsedNs = nowNs - lastFpsTimestampNs
                        if (elapsedNs >= 1_000_000_000L) {
                            measuredFps = (frameCount * 1_000_000_000.0f) / elapsedNs
                            frameCount = 0
                            lastFpsTimestampNs = nowNs
                        }

                        // Frame Pacing Sleep (~60 FPS)
                        val renderDurationNs = System.nanoTime() - frameStartNs
                        val sleepNs = FRAME_PERIOD_NS - renderDurationNs
                        if (sleepNs > 1_000_000L) {
                            try {
                                sleep(sleepNs / 1_000_000L, (sleepNs % 1_000_000L).toInt())
                            } catch (e: InterruptedException) {
                                Thread.currentThread().interrupt()
                                break
                            }
                        }
                    } catch (t: Throwable) {
                        Log.e(TAG, "Uncaught exception in RenderThread frame loop", t)
                    }
                }
            } catch (t: Throwable) {
                Log.e(TAG, "Fatal RenderThread crash", t)
            } finally {
                isRunning.set(false)
            }
        }
    }

    // -------------------------------------------------------------------------
    // ZERO-ALLOCATION DRAW PASSES
    // -------------------------------------------------------------------------

    private fun renderFrame(canvas: Canvas) {
        // Clear transparent surface
        canvas.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR)

        var snapshot = snapshotRef.get()
        val config = configRef.get()
        val now = System.nanoTime()

        // Grace period fallback during momentary match transitions / frame drop
        if (!snapshot.inMatch && !snapshot.isValid && snapshot.totalEntitiesCount == 0) {
            if ((now - lastValidTimeNs) < 800_000_000L && (lastValidSnapshot.inMatch || lastValidSnapshot.isValid || lastValidSnapshot.totalEntitiesCount > 0)) {
                snapshot = lastValidSnapshot
            }
        }

        val isStandby = !snapshot.inMatch && !snapshot.isValid && snapshot.totalEntitiesCount == 0

        // 1. Render Layer 1: Top-Left Minimap Radar (Always renders boundary & radar box)
        renderMinimapLayer(canvas, snapshot, config, isStandby)

        // 2. Render Layer 2: Main Screen Overhead Combat HUD & Edge Radar (only when active match)
        if (!isStandby) {
            renderScreenHudLayer(canvas, snapshot, config)
        }

        // Optional Diagnostics / FPS Overlay
        if (showFpsCounter) {
            if (isStandby) {
                canvas.drawText("VEMINS ESP: Standby (FPS: ${measuredFps.toInt()})", 40.0f, 60.0f, paintFps)
            } else {
                canvas.drawText("FPS: ${measuredFps.toInt()}", 40.0f, 60.0f, paintFps)
            }
        }
    }

    // -------------------------------------------------------------------------
    // LAYER 1: MINIMAP RADAR PASS (TOP-LEFT RADAR VIEWPORT)
    // -------------------------------------------------------------------------

    private fun renderMinimapLayer(
        canvas: Canvas,
        snapshot: FrameSnapshot,
        config: MinimapConfig,
        isStandby: Boolean = false
    ) {
        // 1. Minimap Background Bounding Box & Radar Box (Always rendered, even in standby)
        scratchRectF.set(
            config.mapPosX,
            config.mapPosY,
            config.mapPosX + config.mapWidth,
            config.mapPosY + config.mapHeight
        )
        canvas.drawRoundRect(scratchRectF, 8.0f, 8.0f, paintMinimapBg)
        canvas.drawRoundRect(scratchRectF, 8.0f, 8.0f, paintMinimapBorder)

        // If in Standby, suppress all dynamic entities (minions, monsters, heroes)
        if (isStandby) {
            return
        }

        // 2. Minions Layer (Blue for Ally, Coral/Red for Enemy)
        if (config.minimapShowMinions) {
            for (i in snapshot.soldiers.indices) {
                val soldier = snapshot.soldiers[i]
                if (soldier.isDead || soldier.hp <= 0) continue

                minimapProjection.worldToMinimap(soldier.posX, soldier.posY, scratchPointA, useDiamond = true)
                val paint = if (soldier.camp == 1) paintMinionAlly else paintMinionEnemy
                val radius = if (soldier.isSiegeOrSuper) config.minimapMinionDotRadius * 1.4f else config.minimapMinionDotRadius
                canvas.drawCircle(scratchPointA.x, scratchPointA.y, radius, paint)
            }
        }

        // 3. Jungle Creeps & Boss Objectives
        if (config.minimapShowMonsters) {
            for (i in snapshot.monsters.indices) {
                val monster = snapshot.monsters[i]
                if (monster.isDead || monster.hp <= 0) continue

                minimapProjection.worldToMinimap(monster.posX, monster.posY, scratchPointA, useDiamond = true)
                val paint = when {
                    monster.isLord -> paintMonsterLord
                    monster.isTurtle -> paintMonsterTurtle
                    monster.isBlueBuff -> paintMonsterBuffBlue
                    monster.isRedBuff -> paintMonsterBuffRed
                    else -> paintMonsterCreep
                }

                val radius = if (monster.isHighPriorityObjective) {
                    config.minimapMonsterDotRadius * 1.5f
                } else {
                    config.minimapMonsterDotRadius
                }

                canvas.drawCircle(scratchPointA.x, scratchPointA.y, radius, paint)
                if (monster.isHighPriorityObjective) {
                    canvas.drawCircle(scratchPointA.x, scratchPointA.y, radius + 1.5f, paintHeroStrokeWhite)
                }
            }
        }

        // 4. Local Player Hero Dot (Green) & Heading Arrow
        val lp = snapshot.localPlayer
        if (lp != null && !lp.isDead && lp.hp > 0) {
            minimapProjection.worldToMinimap(lp.posX, lp.posY, scratchPointA, useDiamond = true)

            // Draw Heading Arrow
            if (config.minimapShowArrows && (lp.facingX != 0.0f || lp.facingY != 0.0f)) {
                minimapProjection.calculateDirectionArrow(
                    scratchPointA.x,
                    scratchPointA.y,
                    lp.facingX,
                    lp.facingY,
                    config.minimapArrowLength,
                    scratchPointB,
                    rotate45 = true
                )
                drawArrow(canvas, scratchPointA.x, scratchPointA.y, scratchPointB.x, scratchPointB.y, paintArrowSelf)
            }

            // Draw Circular Portrait or Green Dot
            drawCircularHeroPortrait(
                canvas,
                lp.heroId,
                scratchPointA.x,
                scratchPointA.y,
                config.minimapHeroDotRadius,
                paintHeroSelf,
                paintBorderSelf
            )
        }

        // 5. Allied Heroes Dots (Blue)
        if (config.minimapShowAllies) {
            for (i in snapshot.allies.indices) {
                val ally = snapshot.allies[i]
                if (ally.isDead || ally.hp <= 0) continue

                minimapProjection.worldToMinimap(ally.posX, ally.posY, scratchPointA, useDiamond = true)

                if (config.minimapShowArrows && (ally.facingX != 0.0f || ally.facingY != 0.0f)) {
                    minimapProjection.calculateDirectionArrow(
                        scratchPointA.x,
                        scratchPointA.y,
                        ally.facingX,
                        ally.facingY,
                        config.minimapArrowLength,
                        scratchPointB,
                        rotate45 = true
                    )
                    drawArrow(canvas, scratchPointA.x, scratchPointA.y, scratchPointB.x, scratchPointB.y, paintArrowAlly)
                }

                drawCircularHeroPortrait(
                    canvas,
                    ally.heroId,
                    scratchPointA.x,
                    scratchPointA.y,
                    config.minimapHeroDotRadius,
                    paintHeroAlly,
                    paintBorderAlly
                )
            }
        }

        // 6. Enemy Heroes Dots (Red) & Heading Vectors
        if (config.minimapShowEnemies) {
            for (i in snapshot.enemies.indices) {
                val enemy = snapshot.enemies[i]
                if (enemy.isDead || enemy.hp <= 0) continue

                minimapProjection.worldToMinimap(enemy.posX, enemy.posY, scratchPointA, useDiamond = true)

                if (config.minimapShowArrows && (enemy.facingX != 0.0f || enemy.facingY != 0.0f)) {
                    minimapProjection.calculateDirectionArrow(
                        scratchPointA.x,
                        scratchPointA.y,
                        enemy.facingX,
                        enemy.facingY,
                        config.minimapArrowLength,
                        scratchPointB,
                        rotate45 = true
                    )
                    drawArrow(canvas, scratchPointA.x, scratchPointA.y, scratchPointB.x, scratchPointB.y, paintArrowEnemy)
                }

                drawCircularHeroPortrait(
                    canvas,
                    enemy.heroId,
                    scratchPointA.x,
                    scratchPointA.y,
                    config.minimapHeroDotRadius,
                    paintHeroEnemy,
                    paintBorderEnemy
                )
            }
        }
    }

    /**
     * Draws a circular hero portrait icon cached by [IconCacheManager],
     * with fallback to a solid colored circle + Hero ID label.
     */
    private fun drawCircularHeroPortrait(
        canvas: Canvas,
        heroId: Int,
        cx: Float,
        cy: Float,
        radius: Float,
        fallbackPaint: Paint,
        borderPaint: Paint
    ) {
        val diameter = (radius * 2.0f).toInt()
        val portrait = if (heroId > 0) iconCache.getHeroPortrait(heroId, diameter) else null

        if (portrait != null) {
            scratchDstRect.set(cx - radius, cy - radius, cx + radius, cy + radius)
            canvas.drawBitmap(portrait, null, scratchDstRect, paintBitmapFilter)
        } else {
            canvas.drawCircle(cx, cy, radius, fallbackPaint)
            if (heroId > 0) {
                canvas.drawText(heroId.toString(), cx, cy + 3.0f, paintTextMinimapHero)
            }
        }

        canvas.drawCircle(cx, cy, radius, borderPaint)
    }

    // -------------------------------------------------------------------------
    // LAYER 2: MAIN SCREEN OVERHEAD COMBAT HUD & EDGE RADAR PASS
    // -------------------------------------------------------------------------

    private fun renderScreenHudLayer(canvas: Canvas, snapshot: FrameSnapshot, config: MinimapConfig) {
        val lp = snapshot.localPlayer
        if (lp != null && (!lp.isDead || lp.hp > 0 || lp.posX != 0.0f || lp.posY != 0.0f)) {
            val dx = lp.posX - lastKnownLocalX
            val dy = lp.posY - lastKnownLocalY
            val jumpDistSq = dx * dx + dy * dy
            if (!hasValidLocalPos || jumpDistSq > 900.0f) { // > 30m instant teleport / new match
                lastKnownLocalX = lp.posX
                lastKnownLocalY = lp.posY
                hasValidLocalPos = true
            } else {
                // Exponential Moving Average (EMA) smoothing for stable camera tracking
                val alpha = 0.35f
                lastKnownLocalX += alpha * (lp.posX - lastKnownLocalX)
                lastKnownLocalY += alpha * (lp.posY - lastKnownLocalY)
            }
        }

        val localX = if (hasValidLocalPos) lastKnownLocalX else (lp?.posX ?: 0.0f)
        val localY = if (hasValidLocalPos) lastKnownLocalY else (lp?.posY ?: 0.0f)

        for (i in snapshot.enemies.indices) {
            val enemy = snapshot.enemies[i]
            if (enemy.isDead || enemy.hp <= 0) continue

            // 3D-to-2D Isometric World-to-Screen Projection
            isometricProjection.worldToScreen(
                enemy.posX,
                enemy.posY,
                localX,
                localY,
                config.hudOffsetY,
                scratchIsoResult
            )

            if (scratchIsoResult.isOnScreen) {
                // On-Screen Overhead Combat HUD
                if (config.screenShowOverheadHp) {
                    drawOverheadCombatHud(canvas, enemy, scratchIsoResult.screenX, scratchIsoResult.screenY, scratchIsoResult.distanceM, config)
                }
            } else {
                // Off-Screen Perimeter Edge Radar
                if (config.screenShowEdgeRadar && scratchIsoResult.distanceM <= config.maxRadarDistance) {
                    drawOffScreenEdgeRadar(canvas, enemy, scratchIsoResult.screenX, scratchIsoResult.screenY, scratchIsoResult.distanceM, config)
                }
            }
        }
    }

    /**
     * Draws the Overhead Combat HUD directly above an on-screen enemy hero model:
     * - Health & Active Shield bar
     * - Numerical HP / Max HP readout & Level badge
     * - Hero Name
     * - Ultimate & Skill cooldown badges with radial sweep arcs
     * - Distance in meters
     */
    private fun drawOverheadCombatHud(
        canvas: Canvas,
        enemy: HeroEntity,
        centerX: Float,
        centerY: Float,
        distanceM: Float,
        config: MinimapConfig
    ) {
        val barWidth = 136.0f * config.hudHpBarScale
        val barHeight = 12.0f * config.hudHpBarScale
        val halfW = barWidth / 2.0f

        val left = centerX - halfW
        val top = centerY
        val right = centerX + halfW
        val bottom = centerY + barHeight

        // 1. Hero Name & Level Header (Above HP Bar)
        val heroName = iconCache.getHeroName(enemy.heroId)
        val levelLabel = "Lv.${enemy.level} $heroName"
        canvas.drawText(levelLabel, left, top - 20.0f, paintTextHeroName)

        // 2. Cooldown Badges Row (Above HP Bar)
        if (config.screenShowSkillCooldowns) {
            drawCooldownBadges(canvas, enemy, centerX, top - 4.0f, config)
        }

        // 3. HP Bar Background
        scratchHpBgRect.set(left - 1.0f, top - 1.0f, right + 1.0f, bottom + 1.0f)
        canvas.drawRoundRect(scratchHpBgRect, 3.0f, 3.0f, paintHudBg)
        canvas.drawRoundRect(scratchHpBgRect, 3.0f, 3.0f, paintHudBorder)

        // 4. HP Fill Bar (Green / Yellow / Red based on HP percentage)
        val hpPct = enemy.hpPercent
        val fillRight = left + (barWidth * hpPct)
        if (fillRight > left) {
            scratchHpFillRect.set(left, top, fillRight, bottom)
            val hpPaint = when {
                hpPct > 0.45f -> paintHpGreen
                hpPct > 0.20f -> paintHpYellow
                else -> paintHpRed
            }
            canvas.drawRoundRect(scratchHpFillRect, 2.0f, 2.0f, hpPaint)
        }

        // 5. Active Physical & Magic Shields Overlay
        if (config.screenShowShields && (enemy.shield > 0 || enemy.magicShield > 0)) {
            val shieldPct = enemy.shieldPercent
            if (shieldPct > 0.0f) {
                val shieldRight = (fillRight + (barWidth * shieldPct)).coerceAtMost(right)
                scratchShieldRect.set(fillRight, top, shieldRight, bottom)
                canvas.drawRect(scratchShieldRect, paintShieldWhite)
            }
        }

        // 6. HP Text Readout
        if (config.screenShowHealthText) {
            val hpText = "${enemy.hp}/${enemy.hpMax}"
            canvas.drawText(hpText, centerX, top + barHeight - 2.5f, paintTextHp)
        }

        // 7. Distance Readout (Below HP Bar)
        if (config.screenShowDistance) {
            val distText = String.format("%.1fm", distanceM)
            canvas.drawText(distText, centerX, bottom + 13.0f, paintTextDistance)
        }
    }

    /**
     * Renders tactical Cooldown badges with circular icons & radial sweep overlays:
     * - Skills 1 & 2: Circular icons with cooldown sweep
     * - Ultimate (Skill 3/4): Highlighted circular icon with "RDY" or countdown
     * - Battle Spell: Circular spell icon with cooldown sweep
     */
    private fun drawCooldownBadges(
        canvas: Canvas,
        enemy: HeroEntity,
        centerX: Float,
        badgeBottomY: Float,
        config: MinimapConfig
    ) {
        val badgeRadius = config.hudBadgeRadius
        val spacing = badgeRadius * 2.44f

        val ult = enemy.ultimateAbility
        val s1 = enemy.getAbility(1)
        val s2 = enemy.getAbility(2)
        val spell = if (config.screenShowBattleSpell) enemy.battleSpell else null

        val activeCount = (if (s1 != null && s1.spellId > 0) 1 else 0) +
                (if (s2 != null && s2.spellId > 0) 1 else 0) +
                (if (ult != null) 1 else 0) +
                (if (spell != null) 1 else 0)

        val totalW = (activeCount.coerceAtLeast(1) - 1) * spacing
        var currentX = centerX - (totalW / 2.0f)
        val cy = badgeBottomY - badgeRadius

        // 1. Skill 1 Badge
        if (s1 != null && s1.spellId > 0) {
            drawCircularSkillBadge(canvas, s1, currentX, cy, badgeRadius, isUlt = false)
            currentX += spacing
        }

        // 2. Skill 2 Badge
        if (s2 != null && s2.spellId > 0) {
            drawCircularSkillBadge(canvas, s2, currentX, cy, badgeRadius, isUlt = false)
            currentX += spacing
        }

        // 3. Ultimate Badge (Slot 3 or 4)
        if (ult != null) {
            val ultRadius = badgeRadius * 1.22f
            drawCircularSkillBadge(canvas, ult, currentX, cy, ultRadius, isUlt = true)
            currentX += spacing
        }

        // 4. Battle Spell Badge
        if (spell != null) {
            drawCircularSpellBadge(canvas, spell, currentX, cy, badgeRadius)
        }
    }

    /**
     * Draws an individual circular skill badge with radial cooldown sweep arc.
     */
    private fun drawCircularSkillBadge(
        canvas: Canvas,
        ability: AbilityInfo,
        cx: Float,
        cy: Float,
        radius: Float,
        isUlt: Boolean
    ) {
        val diameter = (radius * 2.0f).toInt()
        val iconBitmap = if (ability.spellId > 0) iconCache.getSkillIcon(ability.spellId, diameter) else null

        // 1. Draw Base Icon / Solid Fill
        if (iconBitmap != null) {
            scratchDstRect.set(cx - radius, cy - radius, cx + radius, cy + radius)
            canvas.drawBitmap(iconBitmap, null, scratchDstRect, paintBitmapFilter)
        } else {
            val fillPaint = if (ability.isReady) (if (isUlt) paintBadgeReady else paintBadgeSpell) else paintBadgeCd
            canvas.drawCircle(cx, cy, radius, fillPaint)
        }

        // 2. Radial Cooldown Sweep Arc Overlay
        if (!ability.isReady) {
            val progress = ability.cooldownProgress
            val sweepAngle = progress * 360.0f
            scratchSweepRect.set(cx - radius, cy - radius, cx + radius, cy + radius)
            canvas.drawArc(scratchSweepRect, -90.0f, sweepAngle, true, paintCooldownSweep)

            // Cooldown Number
            val cdText = if (ability.remainingSeconds >= 10.0f) {
                "${ability.remainingSeconds.toInt()}"
            } else {
                String.format("%.1f", ability.remainingSeconds)
            }
            canvas.drawText(cdText, cx, cy + 3.0f, paintTextBadge)
        } else if (isUlt) {
            canvas.drawText("RDY", cx, cy + 3.0f, paintTextBadge)
        }

        // 3. Outer Border Ring
        val borderPaint = if (ability.isReady) (if (isUlt) paintBorderSelf else paintBorderAlly) else paintBorderEnemy
        canvas.drawCircle(cx, cy, radius, borderPaint)
    }

    /**
     * Draws a circular battle spell icon with cooldown sweep overlay.
     */
    private fun drawCircularSpellBadge(
        canvas: Canvas,
        spell: AbilityInfo,
        cx: Float,
        cy: Float,
        radius: Float
    ) {
        val diameter = (radius * 2.0f).toInt()
        val iconBitmap = if (spell.spellId > 0) iconCache.getSpellIcon(spell.spellId, diameter) else null

        if (iconBitmap != null) {
            scratchDstRect.set(cx - radius, cy - radius, cx + radius, cy + radius)
            canvas.drawBitmap(iconBitmap, null, scratchDstRect, paintBitmapFilter)
        } else {
            val fillPaint = if (spell.isReady) paintBadgeSpell else paintBadgeCd
            canvas.drawCircle(cx, cy, radius, fillPaint)
        }

        if (!spell.isReady) {
            val progress = spell.cooldownProgress
            val sweepAngle = progress * 360.0f
            scratchSweepRect.set(cx - radius, cy - radius, cx + radius, cy + radius)
            canvas.drawArc(scratchSweepRect, -90.0f, sweepAngle, true, paintCooldownSweep)

            val cdText = "${spell.remainingSeconds.toInt()}s"
            canvas.drawText(cdText, cx, cy + 3.0f, paintTextBadge)
        }

        val borderPaint = if (spell.isReady) paintBorderAlly else paintBorderEnemy
        canvas.drawCircle(cx, cy, radius, borderPaint)
    }

    /**
     * Renders Off-Screen Perimeter Edge Indicator:
     * - Directional chevron arrow clamped to screen border pointing to enemy
     * - Circular hero portrait badge
     * - Distance pill badge (e.g. "Ling 18m")
     * - Amber Alert styling if enemy Ultimate is READY
     */
    private fun drawOffScreenEdgeRadar(
        canvas: Canvas,
        enemy: HeroEntity,
        screenX: Float,
        screenY: Float,
        distanceM: Float,
        config: MinimapConfig
    ) {
        isometricProjection.calculateEdgeRadar(screenX, screenY, config.edgeMargin, scratchEdgeRadarResult)

        val cx = scratchEdgeRadarResult.clampedX
        val cy = scratchEdgeRadarResult.clampedY
        val angleDeg = scratchEdgeRadarResult.angleDeg
        val isUltReady = enemy.isUltReady

        // 1. Draw Directional Chevron Arrow
        canvas.save()
        canvas.translate(cx, cy)
        canvas.rotate(angleDeg)

        scratchPath.reset()
        scratchPath.moveTo(14.0f, 0.0f)
        scratchPath.lineTo(-8.0f, -10.0f)
        scratchPath.lineTo(-3.0f, 0.0f)
        scratchPath.lineTo(-8.0f, 10.0f)
        scratchPath.close()

        val chevronPaint = if (isUltReady) paintRadarChevronReadyFill else paintRadarChevronFill
        canvas.drawPath(scratchPath, chevronPaint)
        canvas.drawPath(scratchPath, paintRadarChevronStroke)
        canvas.restore()

        // 2. Draw Adjacent Info Pill with Hero Portrait & Distance
        val pillW = 68.0f
        val pillH = 20.0f
        val maxPillX = (config.screenWidth - pillW - 10.0f).coerceAtLeast(10.0f)
        val maxPillY = (config.screenHeight - pillH - 10.0f).coerceAtLeast(10.0f)
        val pillX = (cx - pillW / 2.0f).safeCoerceIn(10.0f, maxPillX)
        val pillY = (cy + 16.0f).safeCoerceIn(10.0f, maxPillY)

        scratchBadgeRect.set(pillX, pillY, pillX + pillW, pillY + pillH)
        canvas.drawRoundRect(scratchBadgeRect, 4.0f, 4.0f, paintRadarPillBg)
        canvas.drawRoundRect(scratchBadgeRect, 4.0f, 4.0f, if (isUltReady) paintBadgeReady else paintHudBorder)

        // Draw small hero portrait inside pill
        val heroPortrait = if (enemy.heroId > 0) iconCache.getHeroPortrait(enemy.heroId, 16) else null
        if (heroPortrait != null) {
            scratchDstRect.set(pillX + 2.0f, pillY + 2.0f, pillX + 18.0f, pillY + 18.0f)
            canvas.drawBitmap(heroPortrait, null, scratchDstRect, paintBitmapFilter)
        }

        val heroName = iconCache.getHeroName(enemy.heroId)
        val infoText = "$heroName ${distanceM.toInt()}m"
        canvas.drawText(infoText, pillX + (if (heroPortrait != null) 42.0f else 34.0f), pillY + 13.5f, paintTextBadge)
    }

    /**
     * Helper to draw a directional arrow line with a pointed arrowhead.
     */
    private fun drawArrow(
        canvas: Canvas,
        startX: Float,
        startY: Float,
        endX: Float,
        endY: Float,
        paint: Paint
    ) {
        canvas.drawLine(startX, startY, endX, endY, paint)

        val dx = endX - startX
        val dy = endY - startY
        val angle = Math.atan2(dy.toDouble(), dx.toDouble())
        val arrowHeadLength = 6.0f
        val arrowHeadAngle = Math.PI / 6.0 // 30 degrees

        val x1 = (endX - arrowHeadLength * cos(angle - arrowHeadAngle)).toFloat()
        val y1 = (endY - arrowHeadLength * sin(angle - arrowHeadAngle)).toFloat()
        val x2 = (endX - arrowHeadLength * cos(angle + arrowHeadAngle)).toFloat()
        val y2 = (endY - arrowHeadLength * sin(angle + arrowHeadAngle)).toFloat()

        scratchArrowPath.reset()
        scratchArrowPath.moveTo(endX, endY)
        scratchArrowPath.lineTo(x1, y1)
        scratchArrowPath.moveTo(endX, endY)
        scratchArrowPath.lineTo(x2, y2)

        canvas.drawPath(scratchArrowPath, paint)
    }
}
