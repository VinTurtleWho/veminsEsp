package com.vemins.esp.service

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.os.Process
import android.util.Log
import android.view.Gravity
import android.view.WindowManager
import com.vemins.esp.R
import com.vemins.esp.VeminsApplication
import com.vemins.esp.config.ConfigManager
import com.vemins.esp.daemon.DaemonManager
import com.vemins.esp.engine.VeminsNativeEngine
import com.vemins.esp.model.BinarySnapshotReader
import com.vemins.esp.model.FrameSnapshot
import com.vemins.esp.model.MutableFrameSnapshot
import com.vemins.esp.net.TelemetryClient
import com.vemins.esp.net.TelemetryListener
import com.vemins.esp.state.ConnectionStatus
import com.vemins.esp.state.OverlayStateManager
import com.vemins.esp.ui.MainActivity
import com.vemins.esp.ui.floating.FloatingMenuManager
import com.vemins.esp.view.OverlaySurfaceView
import java.util.concurrent.atomic.AtomicBoolean

/**
 * 100% Touch-Through Hardware-Accelerated Floating Telemetry Overlay Service.
 *
 * Runs exclusively in the background with zero intrusive floating bubbles or touch-stealing views.
 * Interfaces directly with [VeminsNativeEngine] via zero-copy [DirectByteBuffer] with TCP fallback.
 */
class FloatingOverlayService : Service(), TelemetryListener {

    companion object {
        private const val TAG = "FloatingOverlayService"
        const val ACTION_START = "com.vemins.esp.START"
        const val ACTION_STOP = "com.vemins.esp.STOP"
        const val NOTIFICATION_ID = 1001

        var isServiceRunning = false
            private set
    }

    private lateinit var windowManager: WindowManager
    private lateinit var configManager: ConfigManager
    private var overlaySurfaceView: OverlaySurfaceView? = null
    private var telemetryClient: TelemetryClient? = null
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        configManager = ConfigManager.getInstance(this)

        startForegroundNotification()
        initTouchThroughOverlay()
        initPerceptionEngine()
        FloatingMenuManager.getInstance(this).showTrigger()
        isServiceRunning = true
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        return START_STICKY
    }

    private fun startForegroundNotification() {
        val stopIntent = Intent(this, FloatingOverlayService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this, 0, stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val activityIntent = Intent(this, MainActivity::class.java)
        val activityPendingIntent = PendingIntent.getActivity(
            this, 0, activityIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notificationBuilder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, VeminsApplication.CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }

        val notification = notificationBuilder
            .setContentTitle(getString(R.string.service_notification_title))
            .setContentText(getString(R.string.service_notification_desc))
            .setSmallIcon(R.drawable.ic_bubble)
            .setContentIntent(activityPendingIntent)
            .addAction(R.drawable.ic_bubble, getString(R.string.action_stop), stopPendingIntent)
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    /**
     * Deploys fullscreen transparent surface with 100% touch-through passthrough.
     */
    private fun initTouchThroughOverlay() {
        val overlayType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val currentConfig = configManager.getConfig()
        val flags = WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
                WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED

        val overlayParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            overlayType,
            flags,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 0
            y = 0
        }

        overlaySurfaceView = OverlaySurfaceView(this).apply {
            updateConfig(currentConfig.toMinimapConfig())
        }

        windowManager.addView(overlaySurfaceView, overlayParams)

        // Listen for live config updates from MainActivity or REST API
        configManager.addListener { newConfig ->
            overlaySurfaceView?.updateConfig(newConfig.toMinimapConfig())
        }
    }

    private fun initPerceptionEngine() {
        Log.i(TAG, "[+] Initializing Daemon Watchdog & Telemetry Stream Engine...")
        DaemonManager.getInstance(this).startWatchdog()
        initTelemetry()
    }

    private fun initTelemetry() {
        val config = configManager.getConfig()
        telemetryClient = TelemetryClient.getInstance(
            host = config.server.serverHost,
            port = config.server.serverPort
        )
        telemetryClient?.addListener(this)
        telemetryClient?.start()
    }

    override fun onFrameSnapshot(snapshot: FrameSnapshot) {
        overlaySurfaceView?.updateSnapshot(snapshot)
    }

    override fun onConnected(daemonVersion: String, buildHash: String) {
        Log.i(TAG, "[+] Telemetry Connected to daemon $daemonVersion ($buildHash)")
    }

    override fun onDisconnected(reason: String, willReconnect: Boolean) {
        Log.w(TAG, "[-] Telemetry Disconnected: $reason (willReconnect=$willReconnect)")
    }

    override fun onGameRestart(oldPid: Int, newPid: Int) {
        Log.i(TAG, "[+] Detected Game Transition: PID $oldPid -> $newPid")
    }

    override fun onDestroy() {
        super.onDestroy()
        isServiceRunning = false

        DaemonManager.getInstance(this).stopWatchdog()
        FloatingMenuManager.getInstance(this).destroy()

        telemetryClient?.removeListener(this)
        telemetryClient?.stop()
        telemetryClient = null

        overlaySurfaceView?.let {
            try {
                windowManager.removeView(it)
            } catch (e: Exception) {
                // Ignore if already detached
            }
        }
        overlaySurfaceView = null
    }
}
