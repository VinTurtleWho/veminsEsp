package com.vemins.esp.view

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.util.AttributeSet
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.*
import com.vemins.esp.config.ConfigManager
import com.vemins.esp.config.OverlayConfig
import com.vemins.esp.state.ConnectionStatus
import com.vemins.esp.state.OverlayState
import com.vemins.esp.state.OverlayStateListener
import com.vemins.esp.state.OverlayStateManager

/**
 * Floating Interactive Calibration Dialog Panel.
 *
 * Provides real-time sliders and checkboxes for:
 * 1. Minimap radar bounds (X, Y, Width, Height, Y-Inversion)
 * 2. Isometric camera projection zoom scales (Scale X, Scale Y, HUD Offset, Edge Margin, Max Radar Distance)
 * 3. HUD layer visibility toggles (Enemies, Allies, Minions, Jungle, HP Bars, Skill CDs, Battle Spell, Edge Radar)
 * 4. Draggable floating window with live FPS, latency, and connection status metrics.
 */
class CalibrationDialogView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : FrameLayout(context, attrs, defStyleAttr), OverlayStateListener {

    private val configManager = ConfigManager.getInstance()
    private val stateManager = OverlayStateManager.getInstance()
    private val mainHandler = Handler(Looper.getMainLooper())

    private var windowManager: WindowManager? = null
    private var windowLayoutParams: WindowManager.LayoutParams? = null

    // Touch dragging coordinates
    private var initialX = 0
    private var initialY = 0
    private var initialTouchX = 0f
    private var initialTouchY = 0f

    // Header & Status Views
    private lateinit var statusBadgeTextView: TextView
    private lateinit var fpsBadgeTextView: TextView

    // Minimap Sliders & Labels
    private lateinit var sliderMinimapX: SeekBar
    private lateinit var labelMinimapX: TextView
    private lateinit var sliderMinimapY: SeekBar
    private lateinit var labelMinimapY: TextView
    private lateinit var sliderMinimapW: SeekBar
    private lateinit var labelMinimapW: TextView
    private lateinit var sliderMinimapH: SeekBar
    private lateinit var labelMinimapH: TextView
    private lateinit var cbInvertY: CheckBox

    // Camera Sliders & Labels
    private lateinit var sliderScaleX: SeekBar
    private lateinit var labelScaleX: TextView
    private lateinit var sliderScaleY: SeekBar
    private lateinit var labelScaleY: TextView
    private lateinit var sliderHudOffset: SeekBar
    private lateinit var labelHudOffset: TextView
    private lateinit var sliderEdgeMargin: SeekBar
    private lateinit var labelEdgeMargin: TextView
    private lateinit var sliderMaxRadarDist: SeekBar
    private lateinit var labelMaxRadarDist: TextView
    private lateinit var cbHighCamera: CheckBox

    // HUD Layer Checkboxes
    private lateinit var cbShowEnemies: CheckBox
    private lateinit var cbShowAllies: CheckBox
    private lateinit var cbShowArrows: CheckBox
    private lateinit var cbShowMinions: CheckBox
    private lateinit var cbShowMonsters: CheckBox
    private lateinit var cbShowOverheadHp: CheckBox
    private lateinit var cbShowSkillCd: CheckBox
    private lateinit var cbShowBattleSpell: CheckBox
    private lateinit var cbShowDistance: CheckBox
    private lateinit var cbShowEdgeRadar: CheckBox

    // Callback when closed or minimized
    var onCloseClickListener: (() -> Unit)? = null

    init {
        setupUi()
        stateManager.addListener(this)
        applyConfigToUi(configManager.getConfig())
    }

    /**
     * Attaches WindowManager layout params to enable dragging support.
     */
    fun attachToWindowManager(wm: WindowManager, params: WindowManager.LayoutParams) {
        this.windowManager = wm
        this.windowLayoutParams = params
    }

    @SuppressLint("ClickableViewAccessibility", "SetTextI18n")
    private fun setupUi() {
        val dp = context.resources.displayMetrics.density

        // Root container styling (Dark Cyberpunk Glassmorphism)
        val rootBg = GradientDrawable().apply {
            setColor(Color.parseColor("#E60C101A")) // 90% opacity dark navy
            cornerRadius = 16 * dp
            setStroke((1.5f * dp).toInt(), Color.parseColor("#3300E5FF")) // Cyan neon border
        }
        background = rootBg
        setPadding((12 * dp).toInt(), (12 * dp).toInt(), (12 * dp).toInt(), (12 * dp).toInt())

        val mainLayout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT)
        }

        // --- 1. HEADER (Draggable) ---
        val headerLayout = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 0, 0, (8 * dp).toInt())
        }

        val titleView = TextView(context).apply {
            text = "⚡ VEMINS ESP CALIBRATION"
            setTextColor(Color.parseColor("#00E5FF"))
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            layoutParams = LinearLayout.LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f)
        }

        statusBadgeTextView = TextView(context).apply {
            text = "DISCONNECTED"
            textSize = 10f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#FF5252"))
            setPadding((6 * dp).toInt(), (2 * dp).toInt(), (6 * dp).toInt(), (2 * dp).toInt())
            background = GradientDrawable().apply {
                setColor(Color.parseColor("#33FF5252"))
                cornerRadius = 4 * dp
            }
        }

        fpsBadgeTextView = TextView(context).apply {
            text = "0 FPS"
            textSize = 10f
            typeface = Typeface.MONOSPACE
            setTextColor(Color.parseColor("#00E5FF"))
            setPadding((6 * dp).toInt(), 0, (6 * dp).toInt(), 0)
        }

        val btnClose = Button(context).apply {
            text = "✕"
            setTextColor(Color.WHITE)
            textSize = 14f
            background = GradientDrawable().apply {
                setColor(Color.parseColor("#33FFFFFF"))
                cornerRadius = 12 * dp
            }
            layoutParams = LinearLayout.LayoutParams((28 * dp).toInt(), (28 * dp).toInt()).apply {
                marginStart = (6 * dp).toInt()
            }
            setOnClickListener {
                onCloseClickListener?.invoke()
                stateManager.setCalibrationOpen(false)
            }
        }

        headerLayout.addView(titleView)
        headerLayout.addView(statusBadgeTextView)
        headerLayout.addView(fpsBadgeTextView)
        headerLayout.addView(btnClose)

        // Dragging touch listener on header
        headerLayout.setOnTouchListener { _, event ->
            val lp = windowLayoutParams
            val wm = windowManager
            if (lp != null && wm != null) {
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        initialX = lp.x
                        initialY = lp.y
                        initialTouchX = event.rawX
                        initialTouchY = event.rawY
                        true
                    }
                    MotionEvent.ACTION_MOVE -> {
                        lp.x = initialX + (event.rawX - initialTouchX).toInt()
                        lp.y = initialY + (event.rawY - initialTouchY).toInt()
                        wm.updateViewLayout(this, lp)
                        true
                    }
                    else -> false
                }
            } else {
                false
            }
        }

        mainLayout.addView(headerLayout)

        // Divider
        mainLayout.addView(createDivider(dp))

        // --- SCROLLABLE CONTENT ---
        val scrollView = ScrollView(context).apply {
            layoutParams = LinearLayout.LayoutParams(LayoutParams.MATCH_PARENT, (380 * dp).toInt())
            isVerticalScrollBarEnabled = true
        }

        val contentLayout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, (6 * dp).toInt(), 0, (6 * dp).toInt())
        }

        // --- SECTION 1: MINIMAP CALIBRATION ---
        contentLayout.addView(createSectionHeader("1. MINIMAP RADAR BOUNDS", dp))

        // Minimap X (0 - 800)
        labelMinimapX = createLabel("Minimap Pos X: 75 px", dp)
        sliderMinimapX = createSeekBar(0, 800, 75) { progress ->
            labelMinimapX.text = "Minimap Pos X: $progress px"
            configManager.updateMinimap(
                progress.toFloat(),
                sliderMinimapY.progress.toFloat(),
                sliderMinimapW.progress.toFloat(),
                sliderMinimapH.progress.toFloat()
            )
        }
        contentLayout.addView(labelMinimapX)
        contentLayout.addView(sliderMinimapX)

        // Minimap Y (0 - 500)
        labelMinimapY = createLabel("Minimap Pos Y: 15 px", dp)
        sliderMinimapY = createSeekBar(0, 500, 15) { progress ->
            labelMinimapY.text = "Minimap Pos Y: $progress px"
            configManager.updateMinimap(
                sliderMinimapX.progress.toFloat(),
                progress.toFloat(),
                sliderMinimapW.progress.toFloat(),
                sliderMinimapH.progress.toFloat()
            )
        }
        contentLayout.addView(labelMinimapY)
        contentLayout.addView(sliderMinimapY)

        // Minimap Width (100 - 800)
        labelMinimapW = createLabel("Minimap Width: 320 px", dp)
        sliderMinimapW = createSeekBar(100, 800, 320) { progress ->
            labelMinimapW.text = "Minimap Width: $progress px"
            configManager.updateMinimap(
                sliderMinimapX.progress.toFloat(),
                sliderMinimapY.progress.toFloat(),
                progress.toFloat(),
                sliderMinimapH.progress.toFloat()
            )
        }
        contentLayout.addView(labelMinimapW)
        contentLayout.addView(sliderMinimapW)

        // Minimap Height (100 - 800)
        labelMinimapH = createLabel("Minimap Height: 320 px", dp)
        sliderMinimapH = createSeekBar(100, 800, 320) { progress ->
            labelMinimapH.text = "Minimap Height: $progress px"
            configManager.updateMinimap(
                sliderMinimapX.progress.toFloat(),
                sliderMinimapY.progress.toFloat(),
                sliderMinimapW.progress.toFloat(),
                progress.toFloat()
            )
        }
        contentLayout.addView(labelMinimapH)
        contentLayout.addView(sliderMinimapH)

        cbInvertY = createCheckBox("Invert Minimap Y-Axis (Default: Checked)", true) { checked ->
            configManager.updateRenderToggle("invert_y", checked)
        }
        contentLayout.addView(cbInvertY)

        contentLayout.addView(createDivider(dp))

        // --- SECTION 2: ISOMETRIC CAMERA PROJECTION ---
        contentLayout.addView(createSectionHeader("2. ISOMETRIC CAMERA PROJECTION (W2S)", dp))

        // Camera Scale X (10 - 80, step 0.5)
        labelScaleX = createLabel("Camera Scale X: 38.0", dp)
        sliderScaleX = createSeekBar(100, 800, 380) { progress ->
            val scaleVal = progress / 10.0f
            labelScaleX.text = "Camera Scale X: ${String.format("%.1f", scaleVal)}"
            configManager.updateCamera(
                scaleVal,
                sliderScaleY.progress / 10.0f,
                sliderHudOffset.progress.toFloat()
            )
        }
        contentLayout.addView(labelScaleX)
        contentLayout.addView(sliderScaleX)

        // Camera Scale Y (10 - 80, step 0.5)
        labelScaleY = createLabel("Camera Scale Y: 27.0", dp)
        sliderScaleY = createSeekBar(100, 800, 270) { progress ->
            val scaleVal = progress / 10.0f
            labelScaleY.text = "Camera Scale Y: ${String.format("%.1f", scaleVal)}"
            configManager.updateCamera(
                sliderScaleX.progress / 10.0f,
                scaleVal,
                sliderHudOffset.progress.toFloat()
            )
        }
        contentLayout.addView(labelScaleY)
        contentLayout.addView(sliderScaleY)

        // Overhead HUD Offset Y (0 - 200 px)
        labelHudOffset = createLabel("Overhead HUD Lift: 65 px", dp)
        sliderHudOffset = createSeekBar(0, 200, 65) { progress ->
            labelHudOffset.text = "Overhead HUD Lift: $progress px"
            configManager.updateCamera(
                sliderScaleX.progress / 10.0f,
                sliderScaleY.progress / 10.0f,
                progress.toFloat()
            )
        }
        contentLayout.addView(labelHudOffset)
        contentLayout.addView(sliderHudOffset)

        // Edge Margin (0 - 150 px)
        labelEdgeMargin = createLabel("Edge Radar Margin: 45 px", dp)
        sliderEdgeMargin = createSeekBar(0, 150, 45) { progress ->
            labelEdgeMargin.text = "Edge Radar Margin: $progress px"
            configManager.updateRadar(progress.toFloat(), sliderMaxRadarDist.progress.toFloat())
        }
        contentLayout.addView(labelEdgeMargin)
        contentLayout.addView(sliderEdgeMargin)

        // Max Radar Distance (10 - 100 m)
        labelMaxRadarDist = createLabel("Max Radar Distance: 45 m", dp)
        sliderMaxRadarDist = createSeekBar(10, 100, 45) { progress ->
            labelMaxRadarDist.text = "Max Radar Distance: $progress m"
            configManager.updateRadar(sliderEdgeMargin.progress.toFloat(), progress.toFloat())
        }
        contentLayout.addView(labelMaxRadarDist)
        contentLayout.addView(sliderMaxRadarDist)

        cbHighCamera = createCheckBox("High Camera Viewport Scale", true) { checked ->
            configManager.updateRenderToggle("high_camera", checked)
        }
        contentLayout.addView(cbHighCamera)

        contentLayout.addView(createDivider(dp))

        // --- SECTION 3: HUD LAYER VISIBILITY TOGGLES ---
        contentLayout.addView(createSectionHeader("3. HUD LAYER VISIBILITY TOGGLES", dp))

        cbShowEnemies = createCheckBox("Layer 1: Minimap Enemies (Red)", true) { checked ->
            configManager.updateRenderToggle("minimap_show_enemies", checked)
        }
        cbShowAllies = createCheckBox("Layer 1: Minimap Allies (Blue)", false) { checked ->
            configManager.updateRenderToggle("minimap_show_allies", checked)
        }
        cbShowArrows = createCheckBox("Layer 1: Heading Direction Vectors", true) { checked ->
            configManager.updateRenderToggle("minimap_show_arrows", checked)
        }
        cbShowMinions = createCheckBox("Layer 1: Lane Minion Waves (Dots)", true) { checked ->
            configManager.updateRenderToggle("minimap_show_minions", checked)
        }
        cbShowMonsters = createCheckBox("Layer 1: Jungle Creeps & Bosses", true) { checked ->
            configManager.updateRenderToggle("minimap_show_monsters", checked)
        }
        cbShowOverheadHp = createCheckBox("Layer 2: Overhead HP & Shield Bar", true) { checked ->
            configManager.updateRenderToggle("screen_show_overhead_hp", checked)
        }
        cbShowSkillCd = createCheckBox("Layer 2: Skill & Ultimate Cooldowns", true) { checked ->
            configManager.updateRenderToggle("screen_show_skill_cooldowns", checked)
        }
        cbShowBattleSpell = createCheckBox("Layer 2: Battle Spell Tracker", true) { checked ->
            configManager.updateRenderToggle("screen_show_battle_spell", checked)
        }
        cbShowDistance = createCheckBox("Layer 2: Distance Readout (Meters)", true) { checked ->
            configManager.updateRenderToggle("screen_show_distance", checked)
        }
        cbShowEdgeRadar = createCheckBox("Layer 2: Off-Screen Edge Chevrons", true) { checked ->
            configManager.updateRenderToggle("screen_show_edge_radar", checked)
        }

        contentLayout.addView(cbShowEnemies)
        contentLayout.addView(cbShowAllies)
        contentLayout.addView(cbShowArrows)
        contentLayout.addView(cbShowMinions)
        contentLayout.addView(cbShowMonsters)
        contentLayout.addView(cbShowOverheadHp)
        contentLayout.addView(cbShowSkillCd)
        contentLayout.addView(cbShowBattleSpell)
        contentLayout.addView(cbShowDistance)
        contentLayout.addView(cbShowEdgeRadar)

        scrollView.addView(contentLayout)
        mainLayout.addView(scrollView)

        // --- 4. ACTION BUTTONS FOOTER ---
        mainLayout.addView(createDivider(dp))

        val footerLayout = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, (8 * dp).toInt(), 0, 0)
        }

        val btnSave = Button(context).apply {
            text = "💾 SAVE CONFIG"
            setTextColor(Color.WHITE)
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            background = GradientDrawable().apply {
                setColor(Color.parseColor("#00B4D8"))
                cornerRadius = 8 * dp
            }
            layoutParams = LinearLayout.LayoutParams(0, (36 * dp).toInt(), 1f).apply {
                marginEnd = (6 * dp).toInt()
            }
            setOnClickListener {
                val ok = configManager.saveConfig()
                Toast.makeText(
                    context,
                    if (ok) "✓ Config Saved to minimap_config.json" else "❌ Failed to save config",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }

        val btnReset = Button(context).apply {
            text = "↺ RESET"
            setTextColor(Color.parseColor("#CBD5E1"))
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            background = GradientDrawable().apply {
                setColor(Color.parseColor("#334155"))
                cornerRadius = 8 * dp
            }
            layoutParams = LinearLayout.LayoutParams(0, (36 * dp).toInt(), 1f).apply {
                marginStart = (6 * dp).toInt()
            }
            setOnClickListener {
                configManager.resetToDefaults()
                applyConfigToUi(configManager.getConfig())
                Toast.makeText(context, "↺ Reset to Default ESP Config", Toast.LENGTH_SHORT).show()
            }
        }

        footerLayout.addView(btnSave)
        footerLayout.addView(btnReset)
        mainLayout.addView(footerLayout)

        addView(mainLayout)
    }

    /**
     * Synchronizes UI sliders and checkboxes with the provided OverlayConfig.
     */
    @SuppressLint("SetTextI18n")
    fun applyConfigToUi(config: OverlayConfig) {
        val m = config.minimap
        sliderMinimapX.progress = m.posX.toInt()
        labelMinimapX.text = "Minimap Pos X: ${m.posX.toInt()} px"

        sliderMinimapY.progress = m.posY.toInt()
        labelMinimapY.text = "Minimap Pos Y: ${m.posY.toInt()} px"

        sliderMinimapW.progress = m.width.toInt()
        labelMinimapW.text = "Minimap Width: ${m.width.toInt()} px"

        sliderMinimapH.progress = m.height.toInt()
        labelMinimapH.text = "Minimap Height: ${m.height.toInt()} px"

        cbInvertY.isChecked = m.invertY

        val c = config.camera
        sliderScaleX.progress = (c.scaleX * 10).toInt()
        labelScaleX.text = "Camera Scale X: ${String.format("%.1f", c.scaleX)}"

        sliderScaleY.progress = (c.scaleY * 10).toInt()
        labelScaleY.text = "Camera Scale Y: ${String.format("%.1f", c.scaleY)}"

        sliderHudOffset.progress = c.hudOffsetY.toInt()
        labelHudOffset.text = "Overhead HUD Lift: ${c.hudOffsetY.toInt()} px"

        sliderEdgeMargin.progress = c.edgeMargin.toInt()
        labelEdgeMargin.text = "Edge Radar Margin: ${c.edgeMargin.toInt()} px"

        sliderMaxRadarDist.progress = c.maxRadarDistance.toInt()
        labelMaxRadarDist.text = "Max Radar Distance: ${c.maxRadarDistance.toInt()} m"

        cbHighCamera.isChecked = c.highCamera

        val r = config.renderSettings
        cbShowEnemies.isChecked = r.minimapShowEnemies
        cbShowAllies.isChecked = r.minimapShowAllies
        cbShowArrows.isChecked = r.minimapShowArrows
        cbShowMinions.isChecked = r.minimapShowMinions
        cbShowMonsters.isChecked = r.minimapShowMonsters
        cbShowOverheadHp.isChecked = r.screenShowOverheadHp
        cbShowSkillCd.isChecked = r.screenShowSkillCooldowns
        cbShowBattleSpell.isChecked = r.screenShowBattleSpell
        cbShowDistance.isChecked = r.screenShowDistance
        cbShowEdgeRadar.isChecked = r.screenShowEdgeRadar
    }

    // --- OverlayStateListener Callbacks ---

    @SuppressLint("SetTextI18n")
    override fun onStateChanged(state: OverlayState) {
        mainHandler.post {
            // Update FPS & Latency
            val fpsVal = state.stats.fps
            val latVal = state.stats.latencyMs
            fpsBadgeTextView.text = "${fpsVal.toInt()} FPS | ${latVal}ms"

            // Update Connection Status Badge
            when (state.connectionStatus) {
                ConnectionStatus.CONNECTED -> {
                    statusBadgeTextView.text = if (state.stats.targetPid > 0) "ATTACHED [PID:${state.stats.targetPid}]" else "ONLINE"
                    statusBadgeTextView.setTextColor(Color.parseColor("#00E676")) // Green
                    (statusBadgeTextView.background as? GradientDrawable)?.setColor(Color.parseColor("#3300E676"))
                }
                ConnectionStatus.CONNECTING, ConnectionStatus.RECONNECTING -> {
                    statusBadgeTextView.text = state.connectionStatus.name
                    statusBadgeTextView.setTextColor(Color.parseColor("#FFD600")) // Yellow
                    (statusBadgeTextView.background as? GradientDrawable)?.setColor(Color.parseColor("#33FFD600"))
                }
                ConnectionStatus.DISCONNECTED, ConnectionStatus.ERROR -> {
                    statusBadgeTextView.text = state.connectionStatus.name
                    statusBadgeTextView.setTextColor(Color.parseColor("#FF5252")) // Red
                    (statusBadgeTextView.background as? GradientDrawable)?.setColor(Color.parseColor("#33FF5252"))
                }
            }
        }
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        stateManager.removeListener(this)
    }

    // --- HELPER VIEW FACTORIES ---

    private fun createSectionHeader(title: String, dp: Float): TextView {
        return TextView(context).apply {
            text = title
            setTextColor(Color.parseColor("#8A99AD"))
            textSize = 11f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, (10 * dp).toInt(), 0, (4 * dp).toInt())
        }
    }

    private fun createLabel(text: String, dp: Float): TextView {
        return TextView(context).apply {
            this.text = text
            setTextColor(Color.parseColor("#CBD5E1"))
            textSize = 12f
            setPadding(0, (4 * dp).toInt(), 0, 0)
        }
    }

    private fun createSeekBar(min: Int, max: Int, initial: Int, onProgress: (Int) -> Unit): SeekBar {
        return SeekBar(context).apply {
            this.max = max
            this.progress = initial
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                    val clamped = progress.coerceAtLeast(min)
                    if (fromUser) {
                        onProgress(clamped)
                    }
                }
                override fun onStartTrackingTouch(sb: SeekBar?) {}
                override fun onStopTrackingTouch(sb: SeekBar?) {}
            })
        }
    }

    private fun createCheckBox(title: String, initial: Boolean, onChecked: (Boolean) -> Unit): CheckBox {
        return CheckBox(context).apply {
            text = title
            setTextColor(Color.parseColor("#E2E8F0"))
            textSize = 12f
            isChecked = initial
            setOnCheckedChangeListener { _, checked ->
                onChecked(checked)
            }
        }
    }

    private fun createDivider(dp: Float): View {
        return View(context).apply {
            setBackgroundColor(Color.parseColor("#1FFFFFFF"))
            layoutParams = LinearLayout.LayoutParams(LayoutParams.MATCH_PARENT, (1 * dp).toInt()).apply {
                topMargin = (6 * dp).toInt()
                bottomMargin = (6 * dp).toInt()
            }
        }
    }
}
