package com.vemins.esp.ui.floating

import android.animation.ValueAnimator
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.graphics.Point
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.DisplayMetrics
import android.view.*
import android.view.animation.DecelerateInterpolator
import android.view.animation.OvershootInterpolator
import android.widget.*
import com.vemins.esp.R
import com.vemins.esp.config.ConfigChangeListener
import com.vemins.esp.config.ConfigManager
import com.vemins.esp.config.OverlayConfig
import com.vemins.esp.daemon.DaemonManager
import com.vemins.esp.state.ConnectionStatus
import com.vemins.esp.state.OverlayState
import com.vemins.esp.state.OverlayStateListener
import com.vemins.esp.state.OverlayStateManager
import com.vemins.esp.ui.MainActivity
import kotlin.math.abs
import kotlin.math.hypot

/**
 * Cyber-Dark In-Game Floating Mod Menu & Draggable Puck Controller.
 *
 * Provides real-time in-game telemetry calibration, magnetic screen docking,
 * stealth ghost mode (5% opacity), and seamless window touch management.
 */
class FloatingMenuManager private constructor(private val context: Context) :
    ConfigChangeListener, OverlayStateListener {

    companion object {
        private const val PUCK_SIZE_DP = 38
        private const val MENU_WIDTH_DP = 290
        private const val DOUBLE_TAP_TIMEOUT_MS = 320L
        private const val TOUCH_SLOP_DP = 8

        @Volatile
        private var instance: FloatingMenuManager? = null

        fun getInstance(context: Context): FloatingMenuManager {
            return instance ?: synchronized(this) {
                instance ?: FloatingMenuManager(context.applicationContext ?: context).also {
                    instance = it
                }
            }
        }
    }

    private val windowManager: WindowManager =
        context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private val configManager: ConfigManager = ConfigManager.getInstance(context)
    private val stateManager: OverlayStateManager = OverlayStateManager.getInstance()
    private val mainHandler = Handler(Looper.getMainLooper())

    private val density: Float = context.resources.displayMetrics.density
    private val puckSizePx: Int = (PUCK_SIZE_DP * density).toInt()
    private val menuWidthPx: Int = (MENU_WIDTH_DP * density).toInt()
    private val touchSlopPx: Float = TOUCH_SLOP_DP * density

    // Floating Views
    private var triggerView: View? = null
    private var modMenuView: View? = null
    private lateinit var triggerParams: WindowManager.LayoutParams
    private lateinit var menuParams: WindowManager.LayoutParams

    // State
    var isTriggerShowing: Boolean = false
        private set
    var isMenuExpanded: Boolean = false
        private set
    var isStealthMode: Boolean = false
        private set

    // Touch & Gesture Tracking
    private var lastClickTime: Long = 0L
    private var isUpdatingFromCode: Boolean = false
    private var currentActiveTab: Int = 0

    // Animators
    private var dockAnimator: ValueAnimator? = null

    init {
        initLayoutParams()
        configManager.addListener(this)
        stateManager.addListener(this)
    }

    private fun getOverlayWindowType(): Int {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }
    }

    private fun initLayoutParams() {
        val screen = getScreenDimensions()

        // 1. Draggable Trigger Puck Window Params (Consumes touch ONLY on the 38x38dp puck)
        triggerParams = WindowManager.LayoutParams(
            puckSizePx,
            puckSizePx,
            getOverlayWindowType(),
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
                    WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 0 // Docked to left edge initially
            y = (screen.y * 0.28f).toInt()
        }

        // 2. Mod Menu Card Window Params (Consumes touch ONLY within the 290dp frosted card)
        menuParams = WindowManager.LayoutParams(
            menuWidthPx,
            WindowManager.LayoutParams.WRAP_CONTENT,
            getOverlayWindowType(),
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
                    WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = (puckSizePx * 1.2f).toInt()
            y = (screen.y * 0.20f).toInt()
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    fun showTrigger() {
        mainHandler.post {
            if (triggerView == null) {
                val inflater = LayoutInflater.from(context)
                triggerView = inflater.inflate(R.layout.layout_floating_trigger, null)
                setupTriggerTouchListener(triggerView!!)
            }

            if (!isTriggerShowing && triggerView != null) {
                try {
                    windowManager.addView(triggerView, triggerParams)
                    isTriggerShowing = true
                    updateStatusDot()
                } catch (e: Exception) {
                    System.err.println("[FloatingMenuManager] Failed to add trigger view: ${e.message}")
                }
            }
        }
    }

    fun hideTrigger() {
        mainHandler.post {
            collapseMenu()
            if (isTriggerShowing && triggerView != null) {
                try {
                    windowManager.removeView(triggerView)
                } catch (_: Exception) {}
                isTriggerShowing = false
            }
        }
    }

    fun toggleMenu() {
        if (isMenuExpanded) {
            collapseMenu()
        } else {
            expandMenu()
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    fun expandMenu() {
        mainHandler.post {
            if (isMenuExpanded) return@post

            // If in stealth mode, restore normal visibility
            if (isStealthMode) {
                setStealthMode(false)
            }

            if (modMenuView == null) {
                val inflater = LayoutInflater.from(context)
                modMenuView = inflater.inflate(R.layout.layout_floating_mod_menu, null)
                bindModMenuViews(modMenuView!!)
            }

            // Position Mod Menu card relative to Trigger Puck & Screen bounds
            val screen = getScreenDimensions()
            val targetX = if (triggerParams.x < screen.x / 2) {
                // Docked Left -> Open to right of trigger
                (triggerParams.x + puckSizePx + (8 * density).toInt()).coerceAtMost(screen.x - menuWidthPx - (8 * density).toInt())
            } else {
                // Docked Right -> Open to left of trigger
                (triggerParams.x - menuWidthPx - (8 * density).toInt()).coerceAtLeast((8 * density).toInt())
            }

            val targetY = (triggerParams.y - (20 * density).toInt())
                .coerceIn((20 * density).toInt(), (screen.y - (300 * density).toInt()).coerceAtLeast((20 * density).toInt()))

            menuParams.x = targetX
            menuParams.y = targetY

            populateModMenuFromConfig(configManager.getConfig())

            try {
                if (modMenuView?.parent == null) {
                    windowManager.addView(modMenuView, menuParams)
                } else {
                    windowManager.updateViewLayout(modMenuView, menuParams)
                }
                isMenuExpanded = true

                // Animated cyber pop-in
                modMenuView?.alpha = 0f
                modMenuView?.scaleX = 0.85f
                modMenuView?.scaleY = 0.85f
                modMenuView?.animate()
                    ?.alpha(1.0f)
                    ?.scaleX(1.0f)
                    ?.scaleY(1.0f)
                    ?.setDuration(200)
                    ?.setInterpolator(OvershootInterpolator(1.1f))
                    ?.start()

            } catch (e: Exception) {
                System.err.println("[FloatingMenuManager] Failed to add mod menu view: ${e.message}")
            }
        }
    }

    fun collapseMenu() {
        mainHandler.post {
            if (!isMenuExpanded || modMenuView == null) return@post

            modMenuView?.animate()
                ?.alpha(0f)
                ?.scaleX(0.85f)
                ?.scaleY(0.85f)
                ?.setDuration(150)
                ?.withEndAction {
                    try {
                        if (modMenuView?.parent != null) {
                            windowManager.removeView(modMenuView)
                        }
                    } catch (_: Exception) {}
                    isMenuExpanded = false
                }
                ?.start()
        }
    }

    /**
     * Toggles 5% opacity Ghost Stealth Mode on double-tap or stealth button.
     */
    fun setStealthMode(enabled: Boolean) {
        isStealthMode = enabled
        mainHandler.post {
            triggerView?.let { puck ->
                if (enabled) {
                    puck.alpha = 0.05f
                    puck.setBackgroundResource(R.drawable.bg_floating_trigger_stealth)
                    collapseMenu()
                } else {
                    puck.alpha = 1.0f
                    puck.setBackgroundResource(R.drawable.bg_floating_trigger)
                }
            }
        }
    }

    fun toggleStealthMode() {
        setStealthMode(!isStealthMode)
    }

    // =========================================================================
    // TOUCH HANDLING & MAGNETIC DOCKING
    // =========================================================================
    @SuppressLint("ClickableViewAccessibility")
    private fun setupTriggerTouchListener(view: View) {
        var initialX = 0
        var initialY = 0
        var initialTouchX = 0f
        var initialTouchY = 0f
        var isDragging = false

        view.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    dockAnimator?.cancel()
                    initialX = triggerParams.x
                    initialY = triggerParams.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    isDragging = false
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = event.rawX - initialTouchX
                    val dy = event.rawY - initialTouchY
                    if (!isDragging && hypot(dx.toDouble(), dy.toDouble()) > touchSlopPx) {
                        isDragging = true
                    }

                    if (isDragging) {
                        val screen = getScreenDimensions()
                        triggerParams.x = (initialX + dx.toInt()).coerceIn(0, screen.x - puckSizePx)
                        triggerParams.y = (initialY + dy.toInt()).coerceIn(0, screen.y - puckSizePx)
                        try {
                            windowManager.updateViewLayout(triggerView, triggerParams)
                        } catch (_: Exception) {}
                    }
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (!isDragging) {
                        val now = System.currentTimeMillis()
                        if (now - lastClickTime < DOUBLE_TAP_TIMEOUT_MS) {
                            // Double tap detected -> Toggle Stealth Ghost Mode!
                            toggleStealthMode()
                            lastClickTime = 0L
                        } else {
                            lastClickTime = now
                            // Single tap -> Toggle Menu or Wake up from stealth
                            if (isStealthMode) {
                                setStealthMode(false)
                                expandMenu()
                            } else {
                                toggleMenu()
                            }
                        }
                    } else {
                        // Drag released -> Snap magnetically to nearest screen edge
                        snapToNearestEdge()
                    }
                    true
                }
                else -> false
            }
        }
    }

    private fun snapToNearestEdge() {
        val screen = getScreenDimensions()
        val currentX = triggerParams.x
        val midX = (screen.x - puckSizePx) / 2
        val targetX = if (currentX < midX) 0 else (screen.x - puckSizePx)

        dockAnimator?.cancel()
        dockAnimator = ValueAnimator.ofInt(currentX, targetX).apply {
            duration = 240
            interpolator = DecelerateInterpolator(1.5f)
            addUpdateListener { animator ->
                val animatedX = animator.animatedValue as Int
                triggerParams.x = animatedX
                try {
                    if (isTriggerShowing && triggerView?.parent != null) {
                        windowManager.updateViewLayout(triggerView, triggerParams)
                    }
                } catch (_: Exception) {}
            }
            start()
        }
    }

    // =========================================================================
    // MOD MENU BINDINGS & LOGIC
    // =========================================================================
    @SuppressLint("ClickableViewAccessibility")
    private fun bindModMenuViews(root: View) {
        // Dragging the Mod Menu Header to reposition card
        val header = root.findViewById<View>(R.id.modMenuHeader)
        var menuInitialX = 0
        var menuInitialY = 0
        var menuTouchX = 0f
        var menuTouchY = 0f

        header?.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    menuInitialX = menuParams.x
                    menuInitialY = menuParams.y
                    menuTouchX = event.rawX
                    menuTouchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = event.rawX - menuTouchX
                    val dy = event.rawY - menuTouchY
                    val screen = getScreenDimensions()
                    menuParams.x = (menuInitialX + dx.toInt()).coerceIn(0, screen.x - menuWidthPx)
                    menuParams.y = (menuInitialY + dy.toInt()).coerceIn(0, screen.y - (100 * density).toInt())
                    try {
                        windowManager.updateViewLayout(modMenuView, menuParams)
                    } catch (_: Exception) {}
                    true
                }
                else -> false
            }
        }

        // Close & Stealth Buttons
        root.findViewById<View>(R.id.btnModClose)?.setOnClickListener {
            collapseMenu()
        }

        root.findViewById<View>(R.id.btnModStealth)?.setOnClickListener {
            toggleStealthMode()
        }

        // Tabs
        val tabRadar = root.findViewById<Button>(R.id.btnModTabRadar)
        val tabCombat = root.findViewById<Button>(R.id.btnModTabCombat)
        val tabLayers = root.findViewById<Button>(R.id.btnModTabLayers)
        val tabSys = root.findViewById<Button>(R.id.btnModTabSys)

        tabRadar?.setOnClickListener { selectTab(0) }
        tabCombat?.setOnClickListener { selectTab(1) }
        tabLayers?.setOnClickListener { selectTab(2) }
        tabSys?.setOnClickListener { selectTab(3) }

        // --- TAB 1: RADAR CONTROLS ---
        // Presets
        root.findViewById<View>(R.id.btnModPresetStd)?.setOnClickListener {
            configManager.loadPreset("default")
            populateModMenuFromConfig(configManager.getConfig())
        }
        root.findViewById<View>(R.id.btnModPresetDiamond)?.setOnClickListener {
            configManager.loadPreset("diamond")
            populateModMenuFromConfig(configManager.getConfig())
        }
        root.findViewById<View>(R.id.btnModPresetNotch)?.setOnClickListener {
            configManager.loadPreset("notch_safe")
            populateModMenuFromConfig(configManager.getConfig())
        }
        root.findViewById<View>(R.id.btnModPresetWide)?.setOnClickListener {
            configManager.loadPreset("ultrawide")
            populateModMenuFromConfig(configManager.getConfig())
        }

        // Minimap X
        val sbMinimapX = root.findViewById<SeekBar>(R.id.sbModMinimapX)
        val tvValMinimapX = root.findViewById<TextView>(R.id.tvValMinimapX)
        val btnDecMinimapX = root.findViewById<Button>(R.id.btnDecMinimapX)
        val btnIncMinimapX = root.findViewById<Button>(R.id.btnIncMinimapX)

        setupModSlider(sbMinimapX, tvValMinimapX, btnDecMinimapX, btnIncMinimapX, min = 0, max = 800, step = 5) { v ->
            val cfg = configManager.getConfig().minimap
            configManager.updateMinimap(
                posX = v.toFloat(),
                posY = cfg.posY,
                width = cfg.width,
                height = cfg.height
            )
        }

        // Minimap Y
        val sbMinimapY = root.findViewById<SeekBar>(R.id.sbModMinimapY)
        val tvValMinimapY = root.findViewById<TextView>(R.id.tvValMinimapY)
        val btnDecMinimapY = root.findViewById<Button>(R.id.btnDecMinimapY)
        val btnIncMinimapY = root.findViewById<Button>(R.id.btnIncMinimapY)

        setupModSlider(sbMinimapY, tvValMinimapY, btnDecMinimapY, btnIncMinimapY, min = 0, max = 600, step = 5) { v ->
            val cfg = configManager.getConfig().minimap
            configManager.updateMinimap(
                posX = cfg.posX,
                posY = v.toFloat(),
                width = cfg.width,
                height = cfg.height
            )
        }

        // Minimap Size
        val sbMinimapSize = root.findViewById<SeekBar>(R.id.sbModMinimapSize)
        val tvValMinimapSize = root.findViewById<TextView>(R.id.tvValMinimapSize)
        val btnDecMinimapSize = root.findViewById<Button>(R.id.btnDecMinimapSize)
        val btnIncMinimapSize = root.findViewById<Button>(R.id.btnIncMinimapSize)

        setupModSlider(sbMinimapSize, tvValMinimapSize, btnDecMinimapSize, btnIncMinimapSize, min = 100, max = 600, step = 10) { v ->
            val cfg = configManager.getConfig().minimap
            configManager.updateMinimap(
                posX = cfg.posX,
                posY = cfg.posY,
                width = v.toFloat(),
                height = v.toFloat()
            )
        }

        // Minimap Alpha
        val sbMinimapAlpha = root.findViewById<SeekBar>(R.id.sbModMinimapAlpha)
        val tvValMinimapAlpha = root.findViewById<TextView>(R.id.tvValMinimapAlpha)
        val btnDecMinimapAlpha = root.findViewById<Button>(R.id.btnDecMinimapAlpha)
        val btnIncMinimapAlpha = root.findViewById<Button>(R.id.btnIncMinimapAlpha)

        setupModSlider(sbMinimapAlpha, tvValMinimapAlpha, btnDecMinimapAlpha, btnIncMinimapAlpha, min = 10, max = 100, step = 5, isPercent = true) { v ->
            val cfg = configManager.getConfig().minimap
            configManager.updateMinimap(
                posX = cfg.posX,
                posY = cfg.posY,
                width = cfg.width,
                height = cfg.height,
                alpha = v / 100f
            )
        }

        // Hero Icon Size
        val sbHeroSize = root.findViewById<SeekBar>(R.id.sbModHeroSize)
        val tvValHeroSize = root.findViewById<TextView>(R.id.tvValHeroSize)
        val btnDecHeroSize = root.findViewById<Button>(R.id.btnDecHeroSize)
        val btnIncHeroSize = root.findViewById<Button>(R.id.btnIncHeroSize)

        setupModSlider(sbHeroSize, tvValHeroSize, btnDecHeroSize, btnIncHeroSize, min = 5, max = 25, step = 1) { v ->
            configManager.updateSizing(heroDotRadius = v.toFloat())
        }

        // Diamond & Invert Y Switches
        root.findViewById<Switch>(R.id.switchModDiamond)?.setOnCheckedChangeListener { _, checked ->
            if (!isUpdatingFromCode) {
                configManager.updateRenderToggle("diamond_mode", checked)
            }
        }
        root.findViewById<Switch>(R.id.switchModInvertY)?.setOnCheckedChangeListener { _, checked ->
            if (!isUpdatingFromCode) {
                configManager.updateRenderToggle("invert_y", checked)
            }
        }

        // --- TAB 2: COMBAT CONTROLS ---
        // Scale X
        val sbScaleX = root.findViewById<SeekBar>(R.id.sbModScaleX)
        val tvValScaleX = root.findViewById<TextView>(R.id.tvValScaleX)
        val btnDecScaleX = root.findViewById<Button>(R.id.btnDecScaleX)
        val btnIncScaleX = root.findViewById<Button>(R.id.btnIncScaleX)

        setupModFloatSlider(sbScaleX, tvValScaleX, btnDecScaleX, btnIncScaleX, min = 100, max = 800, scale = 10f, step = 5) { v ->
            val cfg = configManager.getConfig().camera
            configManager.updateCamera(scaleX = v, scaleY = cfg.scaleY, hudOffsetY = cfg.hudOffsetY)
        }

        // Scale Y
        val sbScaleY = root.findViewById<SeekBar>(R.id.sbModScaleY)
        val tvValScaleY = root.findViewById<TextView>(R.id.tvValScaleY)
        val btnDecScaleY = root.findViewById<Button>(R.id.btnDecScaleY)
        val btnIncScaleY = root.findViewById<Button>(R.id.btnIncScaleY)

        setupModFloatSlider(sbScaleY, tvValScaleY, btnDecScaleY, btnIncScaleY, min = 100, max = 600, scale = 10f, step = 5) { v ->
            val cfg = configManager.getConfig().camera
            configManager.updateCamera(scaleX = cfg.scaleX, scaleY = v, hudOffsetY = cfg.hudOffsetY)
        }

        // HUD Lift
        val sbHudLift = root.findViewById<SeekBar>(R.id.sbModHudLift)
        val tvValHudLift = root.findViewById<TextView>(R.id.tvValHudLift)
        val btnDecHudLift = root.findViewById<Button>(R.id.btnDecHudLift)
        val btnIncHudLift = root.findViewById<Button>(R.id.btnIncHudLift)

        setupModSlider(sbHudLift, tvValHudLift, btnDecHudLift, btnIncHudLift, min = 0, max = 180, step = 5) { v ->
            val cfg = configManager.getConfig().camera
            configManager.updateCamera(scaleX = cfg.scaleX, scaleY = cfg.scaleY, hudOffsetY = v.toFloat())
        }

        // Edge Margin
        val sbEdgeMargin = root.findViewById<SeekBar>(R.id.sbModEdgeMargin)
        val tvValEdgeMargin = root.findViewById<TextView>(R.id.tvValEdgeMargin)
        val btnDecEdgeMargin = root.findViewById<Button>(R.id.btnDecEdgeMargin)
        val btnIncEdgeMargin = root.findViewById<Button>(R.id.btnIncEdgeMargin)

        setupModSlider(sbEdgeMargin, tvValEdgeMargin, btnDecEdgeMargin, btnIncEdgeMargin, min = 10, max = 120, step = 5) { v ->
            val cfg = configManager.getConfig().camera
            configManager.updateRadar(edgeMargin = v.toFloat(), maxRadarDistance = cfg.maxRadarDistance)
        }

        // Max Distance
        val sbMaxDist = root.findViewById<SeekBar>(R.id.sbModMaxDist)
        val tvValMaxDist = root.findViewById<TextView>(R.id.tvValMaxDist)
        val btnDecMaxDist = root.findViewById<Button>(R.id.btnDecMaxDist)
        val btnIncMaxDist = root.findViewById<Button>(R.id.btnIncMaxDist)

        setupModSlider(sbMaxDist, tvValMaxDist, btnDecMaxDist, btnIncMaxDist, min = 15, max = 90, step = 5, unit = "m") { v ->
            val cfg = configManager.getConfig().camera
            configManager.updateRadar(edgeMargin = cfg.edgeMargin, maxRadarDistance = v.toFloat())
        }

        // HUD Badge Size
        val sbBadgeSize = root.findViewById<SeekBar>(R.id.sbModBadgeSize)
        val tvValBadgeSize = root.findViewById<TextView>(R.id.tvValBadgeSize)
        val btnDecBadgeSize = root.findViewById<Button>(R.id.btnDecBadgeSize)
        val btnIncBadgeSize = root.findViewById<Button>(R.id.btnIncBadgeSize)

        setupModSlider(sbBadgeSize, tvValBadgeSize, btnDecBadgeSize, btnIncBadgeSize, min = 5, max = 20, step = 1) { v ->
            configManager.updateSizing(hudBadgeRadius = v.toFloat())
        }

        // HP Bar Scale
        val sbHpScale = root.findViewById<SeekBar>(R.id.sbModHpScale)
        val tvValHpScale = root.findViewById<TextView>(R.id.tvValHpScale)
        val btnDecHpScale = root.findViewById<Button>(R.id.btnDecHpScale)
        val btnIncHpScale = root.findViewById<Button>(R.id.btnIncHpScale)

        setupModSlider(sbHpScale, tvValHpScale, btnDecHpScale, btnIncHpScale, min = 50, max = 200, step = 10, isPercent = true) { v ->
            configManager.updateSizing(hudHpBarScale = v / 100f)
        }

        root.findViewById<Switch>(R.id.switchModHighCamera)?.setOnCheckedChangeListener { _, checked ->
            if (!isUpdatingFromCode) {
                configManager.updateRenderToggle("high_camera", checked)
            }
        }

        // --- TAB 3: LAYERS SWITCHES ---
        val layerMap = mapOf(
            R.id.swModEnemies to "minimap_show_enemies",
            R.id.swModAllies to "minimap_show_allies",
            R.id.swModArrows to "minimap_show_arrows",
            R.id.swModMinions to "minimap_show_minions",
            R.id.swModMonsters to "minimap_show_monsters",
            R.id.swModHpBars to "screen_show_overhead_hp",
            R.id.swModSkillCd to "screen_show_skill_cooldowns",
            R.id.swModUltBadge to "screen_show_ult_badge",
            R.id.swModSpellBadge to "screen_show_spell_badge",
            R.id.swModDistance to "screen_show_distance",
            R.id.swModEdgeRadar to "screen_show_edge_radar"
        )

        for ((viewId, configKey) in layerMap) {
            root.findViewById<Switch>(viewId)?.setOnCheckedChangeListener { _, checked ->
                if (!isUpdatingFromCode) {
                    configManager.updateRenderToggle(configKey, checked)
                }
            }
        }

        // --- TAB 4: SYS ACTIONS ---
        root.findViewById<Button>(R.id.btnModSaveConfig)?.setOnClickListener {
            val ok = configManager.saveConfig()
            Toast.makeText(context, if (ok) "✓ Config Saved" else "❌ Save failed", Toast.LENGTH_SHORT).show()
        }

        root.findViewById<Button>(R.id.btnModRestartDaemon)?.setOnClickListener {
            Toast.makeText(context, "⚡ Restarting Root Daemon...", Toast.LENGTH_SHORT).show()
            Thread {
                val ok = DaemonManager.getInstance(context).restartDaemon()
                mainHandler.post {
                    Toast.makeText(context, if (ok) "✓ Root Daemon Active (Port 9999)" else "❌ Daemon restart failed", Toast.LENGTH_SHORT).show()
                }
            }.start()
        }

        root.findViewById<Button>(R.id.btnModToggleGhost)?.setOnClickListener {
            toggleStealthMode()
        }

        root.findViewById<Button>(R.id.btnModResetDefaults)?.setOnClickListener {
            configManager.resetToDefaults()
            populateModMenuFromConfig(configManager.getConfig())
            Toast.makeText(context, "↺ Reset to Factory Defaults", Toast.LENGTH_SHORT).show()
        }

        root.findViewById<Button>(R.id.btnModOpenDashboard)?.setOnClickListener {
            collapseMenu()
            val intent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
            }
            context.startActivity(intent)
        }

        // Initialize active tab styling and visibility
        selectTab(currentActiveTab)
    }

    private fun selectTab(index: Int) {
        currentActiveTab = index
        val root = modMenuView ?: return

        val tabRadar = root.findViewById<Button>(R.id.btnModTabRadar)
        val tabCombat = root.findViewById<Button>(R.id.btnModTabCombat)
        val tabLayers = root.findViewById<Button>(R.id.btnModTabLayers)
        val tabSys = root.findViewById<Button>(R.id.btnModTabSys)

        val panelRadar = root.findViewById<View>(R.id.panelModRadar)
        val panelCombat = root.findViewById<View>(R.id.panelModCombat)
        val panelLayers = root.findViewById<View>(R.id.panelModLayers)
        val panelSys = root.findViewById<View>(R.id.panelModSys)

        val selBg = context.getDrawable(R.drawable.bg_chip_tab_selected)
        val unselBg = context.getDrawable(R.drawable.bg_chip_tab_unselected)
        val activeTextColor = context.getColor(R.color.vemins_bg_dark)
        val inactiveTextColor = context.getColor(R.color.vemins_text_secondary)

        tabRadar?.background = if (index == 0) selBg else unselBg
        tabRadar?.setTextColor(if (index == 0) activeTextColor else inactiveTextColor)
        panelRadar?.visibility = if (index == 0) View.VISIBLE else View.GONE

        tabCombat?.background = if (index == 1) selBg else unselBg
        tabCombat?.setTextColor(if (index == 1) activeTextColor else inactiveTextColor)
        panelCombat?.visibility = if (index == 1) View.VISIBLE else View.GONE

        tabLayers?.background = if (index == 2) selBg else unselBg
        tabLayers?.setTextColor(if (index == 2) activeTextColor else inactiveTextColor)
        panelLayers?.visibility = if (index == 2) View.VISIBLE else View.GONE

        tabSys?.background = if (index == 3) selBg else unselBg
        tabSys?.setTextColor(if (index == 3) activeTextColor else inactiveTextColor)
        panelSys?.visibility = if (index == 3) View.VISIBLE else View.GONE
    }

    @SuppressLint("SetTextI18n")
    private fun populateModMenuFromConfig(config: OverlayConfig) {
        val root = modMenuView ?: return
        isUpdatingFromCode = true

        val m = config.minimap
        root.findViewById<SeekBar>(R.id.sbModMinimapX)?.progress = m.posX.toInt()
        root.findViewById<TextView>(R.id.tvValMinimapX)?.text = m.posX.toInt().toString()

        root.findViewById<SeekBar>(R.id.sbModMinimapY)?.progress = m.posY.toInt()
        root.findViewById<TextView>(R.id.tvValMinimapY)?.text = m.posY.toInt().toString()

        root.findViewById<SeekBar>(R.id.sbModMinimapSize)?.progress = m.width.toInt()
        root.findViewById<TextView>(R.id.tvValMinimapSize)?.text = m.width.toInt().toString()

        val alphaInt = (m.alpha * 100).toInt()
        root.findViewById<SeekBar>(R.id.sbModMinimapAlpha)?.progress = alphaInt
        root.findViewById<TextView>(R.id.tvValMinimapAlpha)?.text = "$alphaInt%"

        root.findViewById<Switch>(R.id.switchModDiamond)?.isChecked = m.diamondMode
        root.findViewById<Switch>(R.id.switchModInvertY)?.isChecked = m.invertY

        val c = config.camera
        root.findViewById<SeekBar>(R.id.sbModScaleX)?.progress = (c.scaleX * 10).toInt()
        root.findViewById<TextView>(R.id.tvValScaleX)?.text = String.format("%.1f", c.scaleX)

        root.findViewById<SeekBar>(R.id.sbModScaleY)?.progress = (c.scaleY * 10).toInt()
        root.findViewById<TextView>(R.id.tvValScaleY)?.text = String.format("%.1f", c.scaleY)

        root.findViewById<SeekBar>(R.id.sbModHudLift)?.progress = c.hudOffsetY.toInt()
        root.findViewById<TextView>(R.id.tvValHudLift)?.text = c.hudOffsetY.toInt().toString()

        root.findViewById<SeekBar>(R.id.sbModEdgeMargin)?.progress = c.edgeMargin.toInt()
        root.findViewById<TextView>(R.id.tvValEdgeMargin)?.text = c.edgeMargin.toInt().toString()

        root.findViewById<SeekBar>(R.id.sbModMaxDist)?.progress = c.maxRadarDistance.toInt()
        root.findViewById<TextView>(R.id.tvValMaxDist)?.text = "${c.maxRadarDistance.toInt()}m"

        root.findViewById<Switch>(R.id.switchModHighCamera)?.isChecked = c.highCamera

        val r = config.renderSettings
        root.findViewById<SeekBar>(R.id.sbModHeroSize)?.progress = r.minimapHeroDotRadius.toInt()
        root.findViewById<TextView>(R.id.tvValHeroSize)?.text = r.minimapHeroDotRadius.toInt().toString()

        root.findViewById<SeekBar>(R.id.sbModBadgeSize)?.progress = r.hudBadgeRadius.toInt()
        root.findViewById<TextView>(R.id.tvValBadgeSize)?.text = r.hudBadgeRadius.toInt().toString()

        val hpScaleInt = (r.hudHpBarScale * 100).toInt()
        root.findViewById<SeekBar>(R.id.sbModHpScale)?.progress = hpScaleInt
        root.findViewById<TextView>(R.id.tvValHpScale)?.text = "$hpScaleInt%"

        root.findViewById<Switch>(R.id.swModEnemies)?.isChecked = r.minimapShowEnemies
        root.findViewById<Switch>(R.id.swModAllies)?.isChecked = r.minimapShowAllies
        root.findViewById<Switch>(R.id.swModArrows)?.isChecked = r.minimapShowArrows
        root.findViewById<Switch>(R.id.swModMinions)?.isChecked = r.minimapShowMinions
        root.findViewById<Switch>(R.id.swModMonsters)?.isChecked = r.minimapShowMonsters
        root.findViewById<Switch>(R.id.swModHpBars)?.isChecked = r.screenShowOverheadHp
        root.findViewById<Switch>(R.id.swModSkillCd)?.isChecked = r.screenShowSkillCooldowns
        root.findViewById<Switch>(R.id.swModUltBadge)?.isChecked = r.screenShowUltBadge
        root.findViewById<Switch>(R.id.swModSpellBadge)?.isChecked = r.screenShowSpellBadge
        root.findViewById<Switch>(R.id.swModDistance)?.isChecked = r.screenShowDistance
        root.findViewById<Switch>(R.id.swModEdgeRadar)?.isChecked = r.screenShowEdgeRadar

        isUpdatingFromCode = false
    }

    private fun setupModSlider(
        seekBar: SeekBar?,
        valText: TextView?,
        decBtn: Button?,
        incBtn: Button?,
        min: Int,
        max: Int,
        step: Int,
        isPercent: Boolean = false,
        unit: String = "",
        onChanged: (Int) -> Unit
    ) {
        if (seekBar == null) return
        seekBar.max = max

        seekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            @SuppressLint("SetTextI18n")
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                val clamped = progress.coerceAtLeast(min)
                val text = if (isPercent) "$clamped%" else "$clamped$unit"
                valText?.text = text
                if (fromUser && !isUpdatingFromCode) {
                    onChanged(clamped)
                }
            }
            override fun onStartTrackingTouch(sb: SeekBar?) {}
            override fun onStopTrackingTouch(sb: SeekBar?) {}
        })

        decBtn?.setOnClickListener {
            val newVal = (seekBar.progress - step).coerceIn(min, max)
            seekBar.progress = newVal
            onChanged(newVal)
        }

        incBtn?.setOnClickListener {
            val newVal = (seekBar.progress + step).coerceIn(min, max)
            seekBar.progress = newVal
            onChanged(newVal)
        }
    }

    private fun setupModFloatSlider(
        seekBar: SeekBar?,
        valText: TextView?,
        decBtn: Button?,
        incBtn: Button?,
        min: Int,
        max: Int,
        scale: Float,
        step: Int,
        onChanged: (Float) -> Unit
    ) {
        if (seekBar == null) return
        seekBar.max = max

        seekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                val clamped = progress.coerceAtLeast(min)
                val floatVal = clamped / scale
                valText?.text = String.format("%.1f", floatVal)
                if (fromUser && !isUpdatingFromCode) {
                    onChanged(floatVal)
                }
            }
            override fun onStartTrackingTouch(sb: SeekBar?) {}
            override fun onStopTrackingTouch(sb: SeekBar?) {}
        })

        decBtn?.setOnClickListener {
            val newVal = (seekBar.progress - step).coerceIn(min, max)
            seekBar.progress = newVal
            onChanged(newVal / scale)
        }

        incBtn?.setOnClickListener {
            val newVal = (seekBar.progress + step).coerceIn(min, max)
            seekBar.progress = newVal
            onChanged(newVal / scale)
        }
    }

    // =========================================================================
    // OBSERVER CALLBACKS
    // =========================================================================
    override fun onConfigChanged(config: OverlayConfig) {
        mainHandler.post {
            if (isMenuExpanded) {
                populateModMenuFromConfig(config)
            }
        }
    }

    @SuppressLint("SetTextI18n")
    override fun onStateChanged(state: OverlayState) {
        mainHandler.post {
            updateStatusDot()

            val root = modMenuView ?: return@post
            val stats = state.stats
            val badge = root.findViewById<TextView>(R.id.tvModSysStatusBadge)
            val detail = root.findViewById<TextView>(R.id.tvModSysStatsDetail)
            val footer = root.findViewById<TextView>(R.id.tvModFooterStats)

            when (state.connectionStatus) {
                ConnectionStatus.CONNECTED -> {
                    badge?.text = "CONNECTED"
                    badge?.setTextColor(context.getColor(R.color.vemins_green))
                    badge?.background = context.getDrawable(R.drawable.bg_badge_green)
                }
                ConnectionStatus.CONNECTING, ConnectionStatus.RECONNECTING -> {
                    badge?.text = state.connectionStatus.name
                    badge?.setTextColor(context.getColor(R.color.vemins_yellow))
                    badge?.background = context.getDrawable(R.drawable.bg_badge_yellow)
                }
                ConnectionStatus.DISCONNECTED, ConnectionStatus.ERROR -> {
                    badge?.text = "STANDBY"
                    badge?.setTextColor(context.getColor(R.color.vemins_red))
                    badge?.background = context.getDrawable(R.drawable.bg_badge_red)
                }
            }

            detail?.text = "PID: ${if (stats.targetPid > 0) stats.targetPid else "--"} | FPS: ${stats.fps.toInt()} | Latency: ${stats.latencyMs}ms | Frames: ${stats.framesReceived}"
            footer?.text = "STREAM: 127.0.0.1:9999 • ${stats.fps.toInt()} FPS"
        }
    }

    private fun updateStatusDot() {
        val dot = triggerView?.findViewById<View>(R.id.vStatusDot) ?: return
        when (stateManager.getState().connectionStatus) {
            ConnectionStatus.CONNECTED -> dot.setBackgroundResource(R.drawable.bg_status_dot_green)
            ConnectionStatus.CONNECTING, ConnectionStatus.RECONNECTING -> dot.setBackgroundResource(R.drawable.bg_status_dot_yellow)
            ConnectionStatus.DISCONNECTED, ConnectionStatus.ERROR -> dot.setBackgroundResource(R.drawable.bg_status_dot_red)
        }
    }

    private fun getScreenDimensions(): Point {
        val dm = context.resources.displayMetrics
        return Point(dm.widthPixels, dm.heightPixels)
    }

    fun destroy() {
        mainHandler.post {
            dockAnimator?.cancel()
            configManager.removeListener(this)
            stateManager.removeListener(this)

            if (isMenuExpanded && modMenuView != null) {
                try {
                    windowManager.removeView(modMenuView)
                } catch (_: Exception) {}
                isMenuExpanded = false
            }

            if (isTriggerShowing && triggerView != null) {
                try {
                    windowManager.removeView(triggerView)
                } catch (_: Exception) {}
                isTriggerShowing = false
            }

            triggerView = null
            modMenuView = null
            instance = null
        }
    }
}
