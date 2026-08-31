package com.vemins.esp.ui

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.widget.*
import com.vemins.esp.R
import com.vemins.esp.config.ConfigManager
import com.vemins.esp.config.OverlayConfig
import com.vemins.esp.daemon.DaemonManager
import com.vemins.esp.net.LocalControlServer
import com.vemins.esp.service.FloatingOverlayService
import com.vemins.esp.state.ConnectionStatus
import com.vemins.esp.state.OverlayState
import com.vemins.esp.state.OverlayStateListener
import com.vemins.esp.state.OverlayStateManager
import com.vemins.esp.view.PreviewCanvasView
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import kotlin.concurrent.thread

/**
 * Studio-Grade Tactical Command Center Dashboard & UI Controller for VeminsESP.
 */
class MainActivity : Activity(), OverlayStateListener, com.vemins.esp.config.ConfigChangeListener {

    private lateinit var configManager: ConfigManager
    private val stateManager = OverlayStateManager.getInstance()
    private val mainHandler = Handler(Looper.getMainLooper())

    // Header & Brand
    private lateinit var ivHeaderLogo: ImageView
    private lateinit var tvBrandTitle: TextView
    private lateinit var tvHeaderVersionBadge: TextView
    private lateinit var tvHeaderStatus: TextView

    // Permission Card
    private lateinit var cardPermission: LinearLayout
    private lateinit var btnGrantPermission: Button

    // Hero Master Actuator Card
    private lateinit var cardHeroControl: LinearLayout
    private lateinit var tvServiceStatus: TextView
    private lateinit var tvServiceDetail: TextView
    private lateinit var btnToggleService: Button

    // Live Calibration Sandbox
    private lateinit var cardSandbox: LinearLayout
    private lateinit var previewContainer: FrameLayout
    private lateinit var previewCanvas: PreviewCanvasView
    private lateinit var btnTogglePreview: TextView
    private lateinit var btnPresetDefault: Button
    private lateinit var btnPresetDiamond: Button
    private lateinit var btnPresetCompact: Button
    private lateinit var btnPresetWide: Button
    private var isPreviewCollapsed = false

    // Real-Time Daemon Diagnostics HUD
    private lateinit var cardDiagnostics: LinearLayout
    private lateinit var tvDaemonStatusBadge: TextView
    private lateinit var tvServerStatusBadge: TextView
    private lateinit var tvDaemonStats: TextView
    private lateinit var btnTestPing: Button
    private lateinit var btnSaveConfig: Button
    private lateinit var btnResetDefaults: Button

    // Tab Bar & Panels
    private lateinit var tabBtnRadar: Button
    private lateinit var tabBtnCombatHud: Button
    private lateinit var tabBtnLayers: Button
    private lateinit var tabBtnStatus: Button
    private lateinit var panelRadar: LinearLayout
    private lateinit var panelCombatHud: LinearLayout
    private lateinit var panelLayers: LinearLayout
    private lateinit var panelStatus: LinearLayout

    // Tab 1: Radar Calibration Controls
    private lateinit var sbMinimapX: SeekBar
    private lateinit var etMinimapX: EditText
    private lateinit var sbMinimapY: SeekBar
    private lateinit var etMinimapY: EditText
    private lateinit var sbMinimapSize: SeekBar
    private lateinit var etMinimapSize: EditText
    private lateinit var sbMinimapAlpha: SeekBar
    private lateinit var etMinimapAlpha: EditText
    private lateinit var sbMinimapHeroRadius: SeekBar
    private lateinit var etMinimapHeroRadius: EditText
    private lateinit var sbMinimapRotation: SeekBar
    private lateinit var etMinimapRotation: EditText
    private lateinit var sbMinimapZoom: SeekBar
    private lateinit var etMinimapZoom: EditText
    private lateinit var sbStretchX: SeekBar
    private lateinit var etStretchX: EditText
    private lateinit var sbStretchY: SeekBar
    private lateinit var etStretchY: EditText
    private lateinit var btnRot0: Button
    private lateinit var btnRot45: Button
    private lateinit var btnRot90: Button
    private lateinit var btnRot180: Button
    private lateinit var btnRot270: Button
    private lateinit var cbMinimapInvertY: CheckBox

    // Tab 2: Combat HUD & Top CD Bar Controls
    private lateinit var cbShowTopCdBar: CheckBox
    private lateinit var sbTopCdBarY: SeekBar
    private lateinit var etTopCdBarY: EditText
    private lateinit var sbTopCdBarScale: SeekBar
    private lateinit var etTopCdBarScale: EditText
    private lateinit var sbScaleX: SeekBar
    private lateinit var etScaleX: EditText
    private lateinit var sbScaleY: SeekBar
    private lateinit var etScaleY: EditText
    private lateinit var sbHudOffsetY: SeekBar
    private lateinit var etHudOffsetY: EditText
    private lateinit var sbHudBadgeRadius: SeekBar
    private lateinit var etHudBadgeRadius: EditText
    private lateinit var sbHudHpBarScale: SeekBar
    private lateinit var etHudHpBarScale: EditText
    private lateinit var cbHighCamera: CheckBox

    // Tab 3: Layers Matrix CheckBoxes (11)
    private lateinit var cbMinimapEnemies: CheckBox
    private lateinit var cbMinimapAllies: CheckBox
    private lateinit var cbMinimapFacing: CheckBox
    private lateinit var cbMinimapMinions: CheckBox
    private lateinit var cbMinimapMonsters: CheckBox
    private lateinit var cbScreenHp: CheckBox
    private lateinit var cbScreenSkillCd: CheckBox
    private lateinit var cbScreenUltBadge: CheckBox
    private lateinit var cbScreenSpellBadge: CheckBox
    private lateinit var cbScreenDistance: CheckBox
    private lateinit var cbScreenEdgeRadar: CheckBox
    private lateinit var cbHideInRecording: CheckBox

    // Tab 4: Vault & Status Controls
    private lateinit var etConfigJson: EditText
    private lateinit var btnExportConfig: Button
    private lateinit var btnImportConfig: Button

    private var isUpdatingFromCode = false

    companion object {
        private const val OVERLAY_PERMISSION_REQUEST_CODE = 2001
        private const val NOTIFICATION_PERMISSION_REQUEST_CODE = 2002
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        configManager = ConfigManager.getInstance(this)
        bindViews()
        setupListeners()
        stateManager.addListener(this)
        configManager.addListener(this)

        // Sync local control server listener
        LocalControlServer.getInstance("127.0.0.1", 8888).onToggleServiceRequest = {
            mainHandler.post {
                if (FloatingOverlayService.isServiceRunning) {
                    stopOverlayService()
                } else {
                    startOverlayService()
                }
                updateUiState()
            }
        }

        populateUiFromConfig(configManager.getConfig())
        requestNotificationPermissionIfNeeded()
        checkAndRequestRootAccess()
    }

    private fun checkAndRequestRootAccess() {
        thread {
            val daemonMgr = DaemonManager.getInstance(this)
            val hasRoot = daemonMgr.isRootAvailable()
            mainHandler.post {
                if (hasRoot) {
                    Toast.makeText(this, "✓ Root Access Granted (UID 0)", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this, "⚠️ Root Access (su) required. Please grant root in Magisk / KernelSU", Toast.LENGTH_LONG).show()
                }
            }
            daemonMgr.startWatchdog()
        }
    }

    override fun onResume() {
        super.onResume()
        populateUiFromConfig(configManager.getConfig())
        updateUiState()
    }

    override fun onDestroy() {
        super.onDestroy()
        configManager.removeListener(this)
        stateManager.removeListener(this)
    }

    override fun onConfigChanged(config: OverlayConfig) {
        mainHandler.post {
            if (!isUpdatingFromCode) {
                populateUiFromConfig(config)
            }
        }
    }

    private fun bindViews() {
        // Header
        ivHeaderLogo = findViewById(R.id.ivHeaderLogo)
        tvBrandTitle = findViewById(R.id.tvBrandTitle)
        tvHeaderVersionBadge = findViewById(R.id.tvHeaderVersionBadge)
        tvHeaderStatus = findViewById(R.id.tvHeaderStatus)

        // Permission Card
        cardPermission = findViewById(R.id.cardPermission)
        btnGrantPermission = findViewById(R.id.btnGrantPermission)

        // Hero Master Actuator Card
        cardHeroControl = findViewById(R.id.cardHeroControl)
        tvServiceStatus = findViewById(R.id.tvServiceStatus)
        tvServiceDetail = findViewById(R.id.tvServiceDetail)
        btnToggleService = findViewById(R.id.btnToggleService)

        // Live Calibration Sandbox
        cardSandbox = findViewById(R.id.cardSandbox)
        previewContainer = findViewById(R.id.previewContainer)
        previewCanvas = findViewById(R.id.previewCanvas)
        btnTogglePreview = findViewById(R.id.btnTogglePreview)
        btnPresetDefault = findViewById(R.id.btnPresetDefault)
        btnPresetDiamond = findViewById(R.id.btnPresetDiamond)
        btnPresetCompact = findViewById(R.id.btnPresetCompact)
        btnPresetWide = findViewById(R.id.btnPresetWide)

        // Real-Time Daemon Diagnostics HUD
        cardDiagnostics = findViewById(R.id.cardDiagnostics)
        tvDaemonStatusBadge = findViewById(R.id.tvDaemonStatusBadge)
        tvServerStatusBadge = findViewById(R.id.tvServerStatusBadge)
        tvDaemonStats = findViewById(R.id.tvDaemonStats)
        btnTestPing = findViewById(R.id.btnTestPing)
        btnSaveConfig = findViewById(R.id.btnSaveConfig)
        btnResetDefaults = findViewById(R.id.btnResetDefaults)

        // Tab Bar & Panels
        tabBtnRadar = findViewById(R.id.tabBtnRadar)
        tabBtnCombatHud = findViewById(R.id.tabBtnCombatHud)
        tabBtnLayers = findViewById(R.id.tabBtnLayers)
        tabBtnStatus = findViewById(R.id.tabBtnStatus)
        panelRadar = findViewById(R.id.panelRadar)
        panelCombatHud = findViewById(R.id.panelCombatHud)
        panelLayers = findViewById(R.id.panelLayers)
        panelStatus = findViewById(R.id.panelStatus)

        // Tab 1: Radar
        sbMinimapX = findViewById(R.id.sbMinimapX)
        etMinimapX = findViewById(R.id.etMinimapX)
        sbMinimapY = findViewById(R.id.sbMinimapY)
        etMinimapY = findViewById(R.id.etMinimapY)
        sbMinimapSize = findViewById(R.id.sbMinimapSize)
        etMinimapSize = findViewById(R.id.etMinimapSize)
        sbMinimapAlpha = findViewById(R.id.sbMinimapAlpha)
        etMinimapAlpha = findViewById(R.id.etMinimapAlpha)
        sbMinimapHeroRadius = findViewById(R.id.sbMinimapHeroRadius)
        etMinimapHeroRadius = findViewById(R.id.etMinimapHeroRadius)
        sbMinimapRotation = findViewById(R.id.sbMinimapRotation)
        etMinimapRotation = findViewById(R.id.etMinimapRotation)
        sbMinimapZoom = findViewById(R.id.sbMinimapZoom)
        etMinimapZoom = findViewById(R.id.etMinimapZoom)
        sbStretchX = findViewById(R.id.sbStretchX)
        etStretchX = findViewById(R.id.etStretchX)
        sbStretchY = findViewById(R.id.sbStretchY)
        etStretchY = findViewById(R.id.etStretchY)
        btnRot0 = findViewById(R.id.btnRot0)
        btnRot45 = findViewById(R.id.btnRot45)
        btnRot90 = findViewById(R.id.btnRot90)
        btnRot180 = findViewById(R.id.btnRot180)
        btnRot270 = findViewById(R.id.btnRot270)
        cbMinimapInvertY = findViewById(R.id.cbMinimapInvertY)

        // Tab 2: Combat HUD & Top CD Bar
        cbShowTopCdBar = findViewById(R.id.cbShowTopCdBar)
        sbTopCdBarY = findViewById(R.id.sbTopCdBarY)
        etTopCdBarY = findViewById(R.id.etTopCdBarY)
        sbTopCdBarScale = findViewById(R.id.sbTopCdBarScale)
        etTopCdBarScale = findViewById(R.id.etTopCdBarScale)
        sbScaleX = findViewById(R.id.sbScaleX)
        etScaleX = findViewById(R.id.etScaleX)
        sbScaleY = findViewById(R.id.sbScaleY)
        etScaleY = findViewById(R.id.etScaleY)
        sbHudOffsetY = findViewById(R.id.sbHudOffsetY)
        etHudOffsetY = findViewById(R.id.etHudOffsetY)
        sbHudBadgeRadius = findViewById(R.id.sbHudBadgeRadius)
        etHudBadgeRadius = findViewById(R.id.etHudBadgeRadius)
        sbHudHpBarScale = findViewById(R.id.sbHudHpBarScale)
        etHudHpBarScale = findViewById(R.id.etHudHpBarScale)
        cbHighCamera = findViewById(R.id.cbHighCamera)

        // Tab 3: Layers
        cbMinimapEnemies = findViewById(R.id.cbMinimapEnemies)
        cbMinimapAllies = findViewById(R.id.cbMinimapAllies)
        cbMinimapFacing = findViewById(R.id.cbMinimapFacing)
        cbMinimapMinions = findViewById(R.id.cbMinimapMinions)
        cbMinimapMonsters = findViewById(R.id.cbMinimapMonsters)
        cbScreenHp = findViewById(R.id.cbScreenHp)
        cbScreenSkillCd = findViewById(R.id.cbScreenSkillCd)
        cbScreenUltBadge = findViewById(R.id.cbScreenUltBadge)
        cbScreenSpellBadge = findViewById(R.id.cbScreenSpellBadge)
        cbScreenDistance = findViewById(R.id.cbScreenDistance)
        cbScreenEdgeRadar = findViewById(R.id.cbScreenEdgeRadar)
        cbHideInRecording = findViewById(R.id.cbHideInRecording)

        // Tab 4: Vault
        etConfigJson = findViewById(R.id.etConfigJson)
        btnExportConfig = findViewById(R.id.btnExportConfig)
        btnImportConfig = findViewById(R.id.btnImportConfig)
    }

    private fun setupListeners() {
        btnGrantPermission.setOnClickListener {
            requestOverlayPermission()
        }

        btnToggleService.setOnClickListener {
            if (!hasOverlayPermission()) {
                Toast.makeText(this, "Please grant Overlay Permission first", Toast.LENGTH_SHORT).show()
                requestOverlayPermission()
                return@setOnClickListener
            }

            if (FloatingOverlayService.isServiceRunning) {
                stopOverlayService()
            } else {
                startOverlayService()
            }
            updateUiState()
        }

        // Live Calibration Preview Collapse/Expand Toggle
        btnTogglePreview.setOnClickListener {
            isPreviewCollapsed = !isPreviewCollapsed
            if (isPreviewCollapsed) {
                previewContainer.visibility = View.GONE
                btnTogglePreview.text = "EXPAND ▼"
            } else {
                previewContainer.visibility = View.VISIBLE
                btnTogglePreview.text = "COLLAPSE ▲"
            }
        }

        // Tab Navigation
        tabBtnRadar.setOnClickListener { selectTab(0) }
        tabBtnCombatHud.setOnClickListener { selectTab(1) }
        tabBtnLayers.setOnClickListener { selectTab(2) }
        tabBtnStatus.setOnClickListener { selectTab(3) }

        // Presets in Sandbox
        btnPresetDefault.setOnClickListener {
            configManager.loadPreset("default")
            populateUiFromConfig(configManager.getConfig())
            Toast.makeText(this, "Standard Radar Preset Applied", Toast.LENGTH_SHORT).show()
        }
        btnPresetDiamond.setOnClickListener {
            configManager.loadPreset("diamond")
            populateUiFromConfig(configManager.getConfig())
            Toast.makeText(this, "45° Diamond Radar Preset Applied", Toast.LENGTH_SHORT).show()
        }
        btnPresetCompact.setOnClickListener {
            configManager.loadPreset("notch_safe")
            populateUiFromConfig(configManager.getConfig())
            Toast.makeText(this, "Notch-Safe Preset Applied", Toast.LENGTH_SHORT).show()
        }
        btnPresetWide.setOnClickListener {
            configManager.loadPreset("ultrawide")
            populateUiFromConfig(configManager.getConfig())
            Toast.makeText(this, "Tablet / Ultrawide Preset Applied", Toast.LENGTH_SHORT).show()
        }

        // --- TAB 1: RADAR SEEKBARS & INPUTS ---
        setupSeekBarWithInput(sbMinimapX, etMinimapX, 0, 800) { v ->
            configManager.updateMinimap(
                posX = v.toFloat(),
                posY = sbMinimapY.progress.toFloat(),
                width = sbMinimapSize.progress.toFloat(),
                height = sbMinimapSize.progress.toFloat()
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbMinimapY, etMinimapY, 0, 600) { v ->
            configManager.updateMinimap(
                posX = sbMinimapX.progress.toFloat(),
                posY = v.toFloat(),
                width = sbMinimapSize.progress.toFloat(),
                height = sbMinimapSize.progress.toFloat()
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbMinimapSize, etMinimapSize, 100, 600) { v ->
            configManager.updateMinimap(
                posX = sbMinimapX.progress.toFloat(),
                posY = sbMinimapY.progress.toFloat(),
                width = v.toFloat(),
                height = v.toFloat()
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbMinimapAlpha, etMinimapAlpha, 10, 100) { v ->
            configManager.updateMinimap(
                posX = sbMinimapX.progress.toFloat(),
                posY = sbMinimapY.progress.toFloat(),
                width = sbMinimapSize.progress.toFloat(),
                height = sbMinimapSize.progress.toFloat(),
                alpha = v / 100.0f
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbMinimapHeroRadius, etMinimapHeroRadius, 5, 25) { v ->
            configManager.updateSizing(heroDotRadius = v.toFloat())
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbMinimapRotation, etMinimapRotation, 0, 360) { v ->
            val cfg = configManager.getConfig().minimap
            configManager.updateMinimap(
                posX = cfg.posX,
                posY = cfg.posY,
                width = cfg.width,
                height = cfg.height,
                rotationDegrees = v.toFloat()
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbMinimapZoom, etMinimapZoom, 50, 200) { v ->
            val cfg = configManager.getConfig().minimap
            configManager.updateMinimap(
                posX = cfg.posX,
                posY = cfg.posY,
                width = cfg.width,
                height = cfg.height,
                radarZoom = v / 100.0f
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbStretchX, etStretchX, 50, 200) { v ->
            val cfg = configManager.getConfig().minimap
            configManager.updateMinimap(
                posX = cfg.posX,
                posY = cfg.posY,
                width = cfg.width,
                height = cfg.height,
                stretchX = v / 100.0f
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbStretchY, etStretchY, 50, 200) { v ->
            val cfg = configManager.getConfig().minimap
            configManager.updateMinimap(
                posX = cfg.posX,
                posY = cfg.posY,
                width = cfg.width,
                height = cfg.height,
                stretchY = v / 100.0f
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        btnRot0.setOnClickListener { setRotationAngle(0) }
        btnRot45.setOnClickListener { setRotationAngle(45) }
        btnRot90.setOnClickListener { setRotationAngle(90) }
        btnRot180.setOnClickListener { setRotationAngle(180) }
        btnRot270.setOnClickListener { setRotationAngle(270) }

        cbMinimapInvertY.setOnCheckedChangeListener { _, checked ->
            if (!isUpdatingFromCode) {
                configManager.updateRenderToggle("invert_y", checked)
                previewCanvas.setConfig(configManager.getConfig())
            }
        }

        // --- TAB 2: COMBAT HUD & TOP CD BAR SEEKBARS & INPUTS ---
        cbShowTopCdBar.setOnCheckedChangeListener { _, checked ->
            if (!isUpdatingFromCode) {
                configManager.updateRenderToggle("show_top_cd_bar", checked)
                previewCanvas.setConfig(configManager.getConfig())
            }
        }

        setupSeekBarWithInput(sbTopCdBarY, etTopCdBarY, 0, 150) { v ->
            val c = configManager.getConfig().camera
            configManager.updateCamera(
                scaleX = c.scaleX,
                scaleY = c.scaleY,
                hudOffsetY = c.hudOffsetY,
                topCdBarPosY = v.toFloat()
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbTopCdBarScale, etTopCdBarScale, 50, 200) { v ->
            val c = configManager.getConfig().camera
            configManager.updateCamera(
                scaleX = c.scaleX,
                scaleY = c.scaleY,
                hudOffsetY = c.hudOffsetY,
                topCdBarScale = v / 100.0f
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithFloatInput(sbScaleX, etScaleX, 100, 800, 10.0f) { v ->
            val c = configManager.getConfig().camera
            configManager.updateCamera(
                scaleX = v,
                scaleY = c.scaleY,
                hudOffsetY = c.hudOffsetY
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithFloatInput(sbScaleY, etScaleY, 100, 600, 10.0f) { v ->
            val c = configManager.getConfig().camera
            configManager.updateCamera(
                scaleX = c.scaleX,
                scaleY = v,
                hudOffsetY = c.hudOffsetY
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbHudOffsetY, etHudOffsetY, 0, 180) { v ->
            val c = configManager.getConfig().camera
            configManager.updateCamera(
                scaleX = c.scaleX,
                scaleY = c.scaleY,
                hudOffsetY = v.toFloat()
            )
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbHudBadgeRadius, etHudBadgeRadius, 5, 20) { v ->
            configManager.updateSizing(hudBadgeRadius = v.toFloat())
            previewCanvas.setConfig(configManager.getConfig())
        }

        setupSeekBarWithInput(sbHudHpBarScale, etHudHpBarScale, 50, 200) { v ->
            configManager.updateSizing(hudHpBarScale = v / 100.0f)
            previewCanvas.setConfig(configManager.getConfig())
        }

        cbHighCamera.setOnCheckedChangeListener { _, checked ->
            if (!isUpdatingFromCode) {
                configManager.updateRenderToggle("high_camera", checked)
                previewCanvas.setConfig(configManager.getConfig())
            }
        }

        // --- TAB 3: LAYERS MATRIX CHECKBOXES (11) ---
        val layerToggles = mapOf(
            cbMinimapEnemies to "minimap_show_enemies",
            cbMinimapAllies to "minimap_show_allies",
            cbMinimapFacing to "minimap_show_arrows",
            cbMinimapMinions to "minimap_show_minions",
            cbMinimapMonsters to "minimap_show_monsters",
            cbScreenHp to "screen_show_overhead_hp",
            cbScreenSkillCd to "screen_show_skill_cooldowns",
            cbScreenUltBadge to "screen_show_ult_badge",
            cbScreenSpellBadge to "screen_show_spell_badge",
            cbScreenDistance to "screen_show_distance",
            cbScreenEdgeRadar to "screen_show_edge_radar",
            cbHideInRecording to "hide_in_recording"
        )

        for ((cb, key) in layerToggles) {
            cb.setOnCheckedChangeListener { _, checked ->
                if (!isUpdatingFromCode) {
                    configManager.updateRenderToggle(key, checked)
                    previewCanvas.setConfig(configManager.getConfig())
                }
            }
        }

        // Diagnostics & Configuration HUD Actions
        btnTestPing.setOnClickListener {
            testApiPing()
        }

        btnSaveConfig.setOnClickListener {
            val ok = configManager.saveConfig()
            updateConfigJsonVault()
            Toast.makeText(
                this,
                if (ok) "✓ Config Saved to SharedPreferences & JSON Vault" else "❌ Save failed",
                Toast.LENGTH_SHORT
            ).show()
        }

        btnResetDefaults.setOnClickListener {
            configManager.resetToDefaults()
            populateUiFromConfig(configManager.getConfig())
            Toast.makeText(this, "↺ Reset to Factory Default Settings", Toast.LENGTH_SHORT).show()
        }

        // Tab 4: Vault Import & Export Actions
        btnExportConfig.setOnClickListener {
            val jsonStr = configManager.toJson().toString(2)
            etConfigJson.setText(jsonStr)
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = ClipData.newPlainText("VeminsESP Config", jsonStr)
            clipboard.setPrimaryClip(clip)
            Toast.makeText(this, "✓ Config JSON exported & copied to clipboard", Toast.LENGTH_SHORT).show()
        }

        btnImportConfig.setOnClickListener {
            var rawJson = etConfigJson.text.toString().trim()
            if (rawJson.isEmpty()) {
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                val clipItem = clipboard.primaryClip?.getItemAt(0)
                rawJson = clipItem?.text?.toString()?.trim() ?: ""
            }

            if (rawJson.isEmpty()) {
                Toast.makeText(this, "Please paste valid configuration JSON into the text field", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            try {
                val jsonObj = JSONObject(rawJson)
                configManager.updateFromJson(jsonObj)
                populateUiFromConfig(configManager.getConfig())
                Toast.makeText(this, "✓ Configuration Imported and Applied", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Toast.makeText(this, "❌ Invalid Config JSON: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun selectTab(index: Int) {
        val activeBg = getDrawable(R.drawable.bg_tab_selected)
        val inactiveBg = getDrawable(R.drawable.bg_tab_unselected)
        val activeColor = getColor(R.color.vemins_bg_dark)
        val inactiveColor = getColor(R.color.vemins_text_secondary)

        tabBtnRadar.background = if (index == 0) activeBg else inactiveBg
        tabBtnRadar.setTextColor(if (index == 0) activeColor else inactiveColor)
        panelRadar.visibility = if (index == 0) View.VISIBLE else View.GONE

        tabBtnCombatHud.background = if (index == 1) activeBg else inactiveBg
        tabBtnCombatHud.setTextColor(if (index == 1) activeColor else inactiveColor)
        panelCombatHud.visibility = if (index == 1) View.VISIBLE else View.GONE

        tabBtnLayers.background = if (index == 2) activeBg else inactiveBg
        tabBtnLayers.setTextColor(if (index == 2) activeColor else inactiveColor)
        panelLayers.visibility = if (index == 2) View.VISIBLE else View.GONE

        tabBtnStatus.background = if (index == 3) activeBg else inactiveBg
        tabBtnStatus.setTextColor(if (index == 3) activeColor else inactiveColor)
        panelStatus.visibility = if (index == 3) View.VISIBLE else View.GONE
    }

    private fun setRotationAngle(angle: Int) {
        val clamped = angle.coerceIn(0, 360)
        sbMinimapRotation.progress = clamped
        etMinimapRotation.setText(clamped.toString())
        val cfg = configManager.getConfig().minimap
        configManager.updateMinimap(
            posX = cfg.posX,
            posY = cfg.posY,
            width = cfg.width,
            height = cfg.height,
            rotationDegrees = clamped.toFloat()
        )
        previewCanvas.setConfig(configManager.getConfig())
    }

    @SuppressLint("SetTextI18n")
    private fun populateUiFromConfig(config: OverlayConfig) {
        isUpdatingFromCode = true

        val m = config.minimap
        sbMinimapX.progress = m.posX.toInt()
        etMinimapX.setText(m.posX.toInt().toString())

        sbMinimapY.progress = m.posY.toInt()
        etMinimapY.setText(m.posY.toInt().toString())

        sbMinimapSize.progress = m.width.toInt()
        etMinimapSize.setText(m.width.toInt().toString())

        val alphaInt = (m.alpha * 100).toInt()
        sbMinimapAlpha.progress = alphaInt
        etMinimapAlpha.setText(alphaInt.toString())

        val r = config.renderSettings
        sbMinimapHeroRadius.progress = r.minimapHeroDotRadius.toInt()
        etMinimapHeroRadius.setText(r.minimapHeroDotRadius.toInt().toString())

        sbMinimapRotation.progress = m.rotationDegrees.toInt()
        etMinimapRotation.setText(m.rotationDegrees.toInt().toString())

        val zoomInt = (m.radarZoom * 100).toInt()
        sbMinimapZoom.progress = zoomInt
        etMinimapZoom.setText(zoomInt.toString())

        val strXInt = (m.stretchX * 100).toInt()
        sbStretchX.progress = strXInt
        etStretchX.setText(strXInt.toString())

        val strYInt = (m.stretchY * 100).toInt()
        sbStretchY.progress = strYInt
        etStretchY.setText(strYInt.toString())

        cbMinimapInvertY.isChecked = m.invertY

        val c = config.camera
        cbShowTopCdBar.isChecked = c.showTopCdBar
        sbTopCdBarY.progress = c.topCdBarPosY.toInt()
        etTopCdBarY.setText(c.topCdBarPosY.toInt().toString())

        val topScaleInt = (c.topCdBarScale * 100).toInt()
        sbTopCdBarScale.progress = topScaleInt
        etTopCdBarScale.setText(topScaleInt.toString())

        sbScaleX.progress = (c.scaleX * 10).toInt()
        etScaleX.setText(String.format(Locale.US, "%.1f", c.scaleX))

        sbScaleY.progress = (c.scaleY * 10).toInt()
        etScaleY.setText(String.format(Locale.US, "%.1f", c.scaleY))

        sbHudOffsetY.progress = c.hudOffsetY.toInt()
        etHudOffsetY.setText(c.hudOffsetY.toInt().toString())

        sbHudBadgeRadius.progress = r.hudBadgeRadius.toInt()
        etHudBadgeRadius.setText(r.hudBadgeRadius.toInt().toString())

        val hpScaleInt = (r.hudHpBarScale * 100).toInt()
        sbHudHpBarScale.progress = hpScaleInt
        etHudHpBarScale.setText(hpScaleInt.toString())

        cbHighCamera.isChecked = c.highCamera

        cbMinimapEnemies.isChecked = r.minimapShowEnemies
        cbMinimapAllies.isChecked = r.minimapShowAllies
        cbMinimapFacing.isChecked = r.minimapShowArrows
        cbMinimapMinions.isChecked = r.minimapShowMinions
        cbMinimapMonsters.isChecked = r.minimapShowMonsters
        cbScreenHp.isChecked = r.screenShowOverheadHp
        cbScreenSkillCd.isChecked = r.screenShowSkillCooldowns
        cbScreenUltBadge.isChecked = r.screenShowUltBadge
        cbScreenSpellBadge.isChecked = r.screenShowSpellBadge
        cbScreenDistance.isChecked = r.screenShowDistance
        cbScreenEdgeRadar.isChecked = r.screenShowEdgeRadar
        cbHideInRecording.isChecked = r.hideInRecording

        updateConfigJsonVault()
        previewCanvas.setConfig(config)
        isUpdatingFromCode = false
    }

    private fun updateConfigJsonVault() {
        try {
            etConfigJson.setText(configManager.toJson().toString(2))
        } catch (_: Exception) {}
    }

    private fun setupSeekBarWithInput(
        seekBar: SeekBar,
        editText: EditText,
        min: Int,
        max: Int,
        onValChanged: (Int) -> Unit
    ) {
        seekBar.max = max
        seekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                val clamped = progress.coerceIn(min, max)
                if (fromUser && !isUpdatingFromCode) {
                    editText.setText(clamped.toString())
                    onValChanged(clamped)
                }
            }
            override fun onStartTrackingTouch(sb: SeekBar?) {}
            override fun onStopTrackingTouch(sb: SeekBar?) {}
        })

        editText.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                if (editText.hasFocus() && !isUpdatingFromCode) {
                    val parsed = s?.toString()?.toIntOrNull()
                    if (parsed != null) {
                        val clamped = parsed.coerceIn(min, max)
                        isUpdatingFromCode = true
                        seekBar.progress = clamped
                        isUpdatingFromCode = false
                        onValChanged(clamped)
                    }
                }
            }
        })

        editText.setOnFocusChangeListener { _, hasFocus ->
            if (!hasFocus) {
                val parsed = editText.text.toString().toIntOrNull() ?: min
                val clamped = parsed.coerceIn(min, max)
                isUpdatingFromCode = true
                seekBar.progress = clamped
                editText.setText(clamped.toString())
                isUpdatingFromCode = false
                onValChanged(clamped)
            }
        }
    }

    private fun setupSeekBarWithFloatInput(
        seekBar: SeekBar,
        editText: EditText,
        minProgress: Int,
        maxProgress: Int,
        scaleFactor: Float,
        onValChanged: (Float) -> Unit
    ) {
        seekBar.max = maxProgress
        seekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                val clamped = progress.coerceIn(minProgress, maxProgress)
                val floatVal = clamped / scaleFactor
                if (fromUser && !isUpdatingFromCode) {
                    editText.setText(String.format(Locale.US, "%.1f", floatVal))
                    onValChanged(floatVal)
                }
            }
            override fun onStartTrackingTouch(sb: SeekBar?) {}
            override fun onStopTrackingTouch(sb: SeekBar?) {}
        })

        editText.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                if (editText.hasFocus() && !isUpdatingFromCode) {
                    val parsed = s?.toString()?.toFloatOrNull()
                    if (parsed != null) {
                        val prog = (parsed * scaleFactor).toInt().coerceIn(minProgress, maxProgress)
                        val floatVal = prog / scaleFactor
                        isUpdatingFromCode = true
                        seekBar.progress = prog
                        isUpdatingFromCode = false
                        onValChanged(floatVal)
                    }
                }
            }
        })

        editText.setOnFocusChangeListener { _, hasFocus ->
            if (!hasFocus) {
                val parsed = editText.text.toString().toFloatOrNull() ?: (minProgress / scaleFactor)
                val prog = (parsed * scaleFactor).toInt().coerceIn(minProgress, maxProgress)
                val floatVal = prog / scaleFactor
                isUpdatingFromCode = true
                seekBar.progress = prog
                editText.setText(String.format(Locale.US, "%.1f", floatVal))
                isUpdatingFromCode = false
                onValChanged(floatVal)
            }
        }
    }

    private fun testApiPing() {
        thread {
            try {
                val url = URL("http://127.0.0.1:8888/api/ping")
                val conn = url.openConnection() as HttpURLConnection
                conn.connectTimeout = 1500
                conn.readTimeout = 1500
                conn.requestMethod = "GET"
                val responseCode = conn.responseCode
                val resp = conn.inputStream.bufferedReader().readText()
                conn.disconnect()

                mainHandler.post {
                    Toast.makeText(this, "✓ API Ping OK ($responseCode): $resp", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                mainHandler.post {
                    Toast.makeText(this, "❌ API Ping Failed: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun hasOverlayPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Settings.canDrawOverlays(this)
        } else {
            true
        }
    }

    private fun requestOverlayPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            try {
                val intent = Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:$packageName")
                )
                startActivityForResult(intent, OVERLAY_PERMISSION_REQUEST_CODE)
            } catch (e: Exception) {
                val fallbackIntent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
                startActivityForResult(fallbackIntent, OVERLAY_PERMISSION_REQUEST_CODE)
            }
        }
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    NOTIFICATION_PERMISSION_REQUEST_CODE
                )
            }
        }
    }

    private fun startOverlayService() {
        try {
            val intent = Intent(this, FloatingOverlayService::class.java).apply {
                action = FloatingOverlayService.ACTION_START
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
            Toast.makeText(this, "VeminsESP Overlay Service Started (100% Touch-Through)", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Toast.makeText(this, "Failed to start overlay: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun stopOverlayService() {
        try {
            val intent = Intent(this, FloatingOverlayService::class.java).apply {
                action = FloatingOverlayService.ACTION_STOP
            }
            startService(intent)
            Toast.makeText(this, "VeminsESP Overlay Service Stopped", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            // Ignore
        }
    }

    @SuppressLint("SetTextI18n")
    private fun updateUiState() {
        val hasOverlay = hasOverlayPermission()
        cardPermission.visibility = if (hasOverlay) View.GONE else View.VISIBLE

        if (FloatingOverlayService.isServiceRunning) {
            tvHeaderStatus.text = "ACTIVE"
            tvHeaderStatus.setTextColor(getColor(R.color.vemins_green))
            tvHeaderStatus.background = getDrawable(R.drawable.bg_badge_green)

            tvServiceStatus.text = getString(R.string.status_running)
            tvServiceStatus.setTextColor(getColor(R.color.vemins_green))

            btnToggleService.text = getString(R.string.btn_stop_overlay)
            btnToggleService.setBackgroundResource(R.drawable.bg_button_danger)
        } else {
            tvHeaderStatus.text = "STOPPED"
            tvHeaderStatus.setTextColor(getColor(R.color.vemins_red))
            tvHeaderStatus.background = getDrawable(R.drawable.bg_badge_red)

            tvServiceStatus.text = getString(R.string.status_stopped)
            tvServiceStatus.setTextColor(getColor(R.color.vemins_text_secondary))

            btnToggleService.text = getString(R.string.btn_start_overlay)
            btnToggleService.setBackgroundResource(R.drawable.bg_button_primary)
        }
    }

    @SuppressLint("SetTextI18n")
    override fun onStateChanged(state: OverlayState) {
        mainHandler.post {
            val stats = state.stats
            when (state.connectionStatus) {
                ConnectionStatus.CONNECTED -> {
                    tvDaemonStatusBadge.text = "CONNECTED"
                    tvDaemonStatusBadge.setTextColor(getColor(R.color.vemins_green))
                    tvDaemonStatusBadge.background = getDrawable(R.drawable.bg_badge_green)
                }
                ConnectionStatus.CONNECTING, ConnectionStatus.RECONNECTING -> {
                    tvDaemonStatusBadge.text = state.connectionStatus.name
                    tvDaemonStatusBadge.setTextColor(getColor(R.color.vemins_yellow))
                    tvDaemonStatusBadge.background = getDrawable(R.drawable.bg_badge_yellow)
                }
                ConnectionStatus.DISCONNECTED, ConnectionStatus.ERROR -> {
                    tvDaemonStatusBadge.text = "STANDBY"
                    tvDaemonStatusBadge.setTextColor(getColor(R.color.vemins_red))
                    tvDaemonStatusBadge.background = getDrawable(R.drawable.bg_badge_red)
                }
            }

            tvDaemonStats.text = "PID: ${if (stats.targetPid > 0) stats.targetPid else "None"} | FPS: ${stats.fps.toInt()} | Latency: ${stats.latencyMs}ms | Frames: ${stats.framesReceived}"
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == OVERLAY_PERMISSION_REQUEST_CODE) {
            updateUiState()
        }
    }
}

