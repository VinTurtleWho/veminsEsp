package com.vemins.esp.state

import com.vemins.esp.config.ConfigManager
import com.vemins.esp.config.OverlayConfig
import com.vemins.esp.model.FrameSnapshot
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference

/**
 * Lifecycle and connection status of the telemetry socket.
 */
enum class ConnectionStatus {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    RECONNECTING,
    ERROR
}

/**
 * Performance and telemetry metrics.
 */
data class TelemetryStats(
    val fps: Float = 0.0f,
    val latencyMs: Long = 0L,
    val framesReceived: Long = 0L,
    val bytesReceived: Long = 0L,
    val reconnectCount: Int = 0,
    val errorCount: Int = 0,
    val lastFrameTimestampNs: Long = 0L,
    val daemonVersion: String = "",
    val daemonBuildHash: String = "",
    val targetPid: Int = 0,
    val liblogicBase: Long = 0L
)

/**
 * Complete immutable state snapshot of the overlay subsystem.
 */
data class OverlayState(
    val connectionStatus: ConnectionStatus = ConnectionStatus.DISCONNECTED,
    val latestSnapshot: FrameSnapshot = FrameSnapshot.empty(),
    val config: OverlayConfig = OverlayConfig(),
    val stats: TelemetryStats = TelemetryStats(),
    val isCalibrationOpen: Boolean = false,
    val statusMessage: String = "Ready"
)

/**
 * Observer interface for overlay state changes.
 */
interface OverlayStateListener {
    fun onStateChanged(state: OverlayState) {}
    fun onSnapshotUpdated(snapshot: FrameSnapshot) {}
    fun onConnectionStatusChanged(status: ConnectionStatus, message: String) {}
}

/**
 * Central State Manager for VEMINS Floating Overlay App.
 * Coordinates between TelemetryClient, ConfigManager, and UI Render Layers.
 */
class OverlayStateManager private constructor() {

    companion object {
        @Volatile
        private var instance: OverlayStateManager? = null

        fun getInstance(): OverlayStateManager {
            return instance ?: synchronized(this) {
                instance ?: OverlayStateManager().also { instance = it }
            }
        }
    }

    private val stateRef = AtomicReference(OverlayState())
    private val listeners = CopyOnWriteArrayList<OverlayStateListener>()

    // FPS Calculation
    private val frameCount = AtomicLong(0L)
    private var lastFpsCalculationTimeNs = System.nanoTime()
    private var framesSinceLastFps = 0L
    private var currentFps = 0.0f

    // Latency EMA
    private var smoothedLatencyMs = 0L

    init {
        // Observe configuration changes from ConfigManager
        ConfigManager.getInstance().addListener { newConfig ->
            updateState { it.copy(config = newConfig) }
        }
    }

    fun getState(): OverlayState = stateRef.get()

    fun addListener(listener: OverlayStateListener) {
        listeners.addIfAbsent(listener)
        listener.onStateChanged(stateRef.get())
    }

    fun removeListener(listener: OverlayStateListener) {
        listeners.remove(listener)
    }

    /**
     * Updates connection status and broadcasts to observers.
     */
    fun updateConnectionStatus(status: ConnectionStatus, message: String = "") {
        val oldState = stateRef.get()
        val newState = oldState.copy(
            connectionStatus = status,
            statusMessage = if (message.isNotBlank()) message else status.name
        )
        stateRef.set(newState)

        for (listener in listeners) {
            try {
                listener.onConnectionStatusChanged(status, message)
                listener.onStateChanged(newState)
            } catch (e: Exception) {
                System.err.println("[OverlayStateManager] Listener error: ${e.message}")
            }
        }
    }

    /**
     * Updates the latest ingested FrameSnapshot from TelemetryClient.
     */
    fun onFrameReceived(snapshot: FrameSnapshot, rawBytesLength: Int = 0, roundTripLatencyMs: Long = 0L) {
        val nowNs = System.nanoTime()
        val totalFrames = frameCount.incrementAndGet()
        framesSinceLastFps++

        // Calculate FPS window (every 500ms)
        val elapsedSec = (nowNs - lastFpsCalculationTimeNs) / 1_000_000_000.0
        if (elapsedSec >= 0.5) {
            currentFps = (framesSinceLastFps / elapsedSec).toFloat()
            framesSinceLastFps = 0
            lastFpsCalculationTimeNs = nowNs
        }

        // Exponential moving average for latency
        smoothedLatencyMs = if (smoothedLatencyMs == 0L) {
            roundTripLatencyMs
        } else {
            (smoothedLatencyMs * 0.8 + roundTripLatencyMs * 0.2).toLong()
        }

        val oldState = stateRef.get()
        val oldStats = oldState.stats

        val resolvedPid = if (snapshot.pid > 0) {
            snapshot.pid
        } else if (snapshot.status == "waiting" || snapshot.status == "disconnected") {
            0
        } else {
            oldStats.targetPid
        }

        val newStats = oldStats.copy(
            fps = currentFps,
            latencyMs = smoothedLatencyMs,
            framesReceived = totalFrames,
            bytesReceived = oldStats.bytesReceived + rawBytesLength,
            lastFrameTimestampNs = nowNs,
            daemonVersion = if (snapshot.version.isNotBlank()) snapshot.version else oldStats.daemonVersion,
            daemonBuildHash = if (snapshot.buildHash.isNotBlank()) snapshot.buildHash else oldStats.daemonBuildHash,
            targetPid = resolvedPid,
            liblogicBase = if (snapshot.liblogicBase > 0L) snapshot.liblogicBase else oldStats.liblogicBase
        )

        val newState = oldState.copy(
            latestSnapshot = snapshot,
            stats = newStats
        )
        stateRef.set(newState)

        for (listener in listeners) {
            try {
                listener.onSnapshotUpdated(snapshot)
                listener.onStateChanged(newState)
            } catch (e: Exception) {
                System.err.println("[OverlayStateManager] Listener error onFrameReceived: ${e.message}")
            }
        }
    }

    /**
     * Records a reconnect attempt in stats.
     */
    fun onReconnectAttempt() {
        updateState { s ->
            s.copy(stats = s.stats.copy(reconnectCount = s.stats.reconnectCount + 1))
        }
    }

    /**
     * Records an error event in stats.
     */
    fun onErrorOccurred(errorMsg: String) {
        updateState { s ->
            s.copy(
                statusMessage = errorMsg,
                stats = s.stats.copy(errorCount = s.stats.errorCount + 1)
            )
        }
    }

    /**
     * Toggles the calibration panel visibility state.
     */
    fun setCalibrationOpen(isOpen: Boolean) {
        updateState { it.copy(isCalibrationOpen = isOpen) }
    }

    /**
     * Sets daemon metadata from handshake banner.
     */
    fun setDaemonMetadata(version: String, buildHash: String) {
        updateState { s ->
            s.copy(stats = s.stats.copy(daemonVersion = version, daemonBuildHash = buildHash))
        }
    }

    private inline fun updateState(transform: (OverlayState) -> OverlayState) {
        while (true) {
            val current = stateRef.get()
            val next = transform(current)
            if (stateRef.compareAndSet(current, next)) {
                for (listener in listeners) {
                    try {
                        listener.onStateChanged(next)
                    } catch (e: Exception) {
                        System.err.println("[OverlayStateManager] Listener error: ${e.message}")
                    }
                }
                break
            }
        }
    }
}
