package com.vemins.esp.net

import com.vemins.esp.model.FrameSnapshot
import com.vemins.esp.state.ConnectionStatus
import com.vemins.esp.state.OverlayStateManager
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.net.SocketException
import java.net.SocketTimeoutException
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.random.Random

/**
 * Listener interface for telemetry network events.
 */
interface TelemetryListener {
    fun onConnected(daemonVersion: String, buildHash: String) {}
    fun onFrameSnapshot(snapshot: FrameSnapshot) {}
    fun onDisconnected(reason: String, willReconnect: Boolean) {}
    fun onError(e: Throwable) {}
    fun onGameRestart(oldPid: Int, newPid: Int) {}
}

/**
 * Ultra-low-latency TCP Socket Telemetry Client.
 *
 * Connects to the local native daemon at 127.0.0.1:9999 with TCP_NODELAY enabled,
 * continuously queries/receives live game frames, parses them into FrameSnapshot objects,
 * and maintains an automatic reconnection loop with exponential backoff.
 */
class TelemetryClient(
    private val host: String = DEFAULT_HOST,
    private val port: Int = DEFAULT_PORT,
    private val targetFps: Int = 60,
    private val connectTimeoutMs: Int = 1500,
    private val readTimeoutMs: Int = 2000,
    private val initialBackoffMs: Long = 50L,
    private val maxBackoffMs: Long = 500L
) {
    companion object {
        const val DEFAULT_HOST = "127.0.0.1"
        const val DEFAULT_PORT = 9999
        private const val CMD_GET_INFO = "GET_INFO\n"
        private const val BUFFER_SIZE = 65536

        @Volatile
        private var instance: TelemetryClient? = null

        fun getInstance(
            host: String = DEFAULT_HOST,
            port: Int = DEFAULT_PORT
        ): TelemetryClient {
            return instance ?: synchronized(this) {
                instance ?: TelemetryClient(host, port).also { instance = it }
            }
        }
    }

    private val isRunning = AtomicBoolean(false)
    private val isConnected = AtomicBoolean(false)
    private var workerThread: Thread? = null

    private var socket: Socket? = null
    private var reader: BufferedReader? = null
    private var writer: OutputStream? = null

    private var lastKnownPid: Int = 0
    private var currentBackoffMs: Long = initialBackoffMs

    private val listeners = CopyOnWriteArrayList<TelemetryListener>()
    private val stateManager = OverlayStateManager.getInstance()

    fun addListener(listener: TelemetryListener) {
        listeners.addIfAbsent(listener)
    }

    fun removeListener(listener: TelemetryListener) {
        listeners.remove(listener)
    }

    fun isConnected(): Boolean = isConnected.get()

    fun isRunning(): Boolean = isRunning.get()

    /**
     * Starts the telemetry client worker loop on a dedicated high-priority daemon thread.
     */
    @Synchronized
    fun start() {
        if (isRunning.getAndSet(true)) {
            return // Already running
        }

        workerThread = Thread({
            runClientLoop()
        }, "vemins-telemetry-client").apply {
            isDaemon = true
            priority = Thread.MAX_PRIORITY
            start()
        }
    }

    /**
     * Stops the telemetry client and closes all active sockets and streams.
     */
    @Synchronized
    fun stop() {
        if (!isRunning.getAndSet(false)) {
            return
        }

        closeSocket()
        workerThread?.interrupt()
        workerThread = null
        isConnected.set(false)
        stateManager.updateConnectionStatus(ConnectionStatus.DISCONNECTED, "Stopped")
    }

    /**
     * Main background network loop with auto-reconnection and exponential backoff.
     */
    private fun runClientLoop() {
        val targetFrameIntervalNs = (1_000_000_000L / targetFps.coerceIn(1, 120))
        val cmdBytes = CMD_GET_INFO.toByteArray(Charsets.UTF_8)

        while (isRunning.get()) {
            try {
                stateManager.updateConnectionStatus(
                    if (currentBackoffMs > initialBackoffMs) ConnectionStatus.RECONNECTING else ConnectionStatus.CONNECTING,
                    "Connecting to $host:$port..."
                )

                // 1. Establish ultra-low-latency TCP connection
                val newSocket = Socket().apply {
                    tcpNoDelay = true              // Disable Nagle's algorithm for sub-millisecond dispatch
                    reuseAddress = true
                    receiveBufferSize = BUFFER_SIZE
                    sendBufferSize = 16384
                    soTimeout = readTimeoutMs
                    keepAlive = true
                    // Optimize performance preferences: (connectionTime, latency, bandwidth)
                    setPerformancePreferences(0, 2, 1)
                }

                newSocket.connect(InetSocketAddress(host, port), connectTimeoutMs)
                socket = newSocket

                val inStream = newSocket.getInputStream()
                val outStream = newSocket.getOutputStream()
                val bufferedReader = BufferedReader(InputStreamReader(inStream, Charsets.UTF_8), BUFFER_SIZE)

                reader = bufferedReader
                writer = outStream

                // Consume initial handshake banner sent by daemon upon connect
                var daemonVersion = ""
                var buildHash = ""
                try {
                    val bannerLine = bufferedReader.readLine()
                    if (!bannerLine.isNullOrBlank()) {
                        val bannerJson = JSONObject(bannerLine)
                        daemonVersion = bannerJson.optString("version", "")
                        buildHash = bannerJson.optString("build_hash", "")
                        if (daemonVersion.isNotBlank()) {
                            stateManager.setDaemonMetadata(daemonVersion, buildHash)
                        }
                    }
                } catch (_: Exception) {}

                isConnected.set(true)
                currentBackoffMs = initialBackoffMs // Reset backoff on successful connect

                stateManager.updateConnectionStatus(ConnectionStatus.CONNECTED, "Connected to $host:$port")
                for (listener in listeners) {
                    try {
                        listener.onConnected(daemonVersion, buildHash)
                    } catch (ignored: Exception) {}
                }

                // 2. Continuous frame polling & parsing loop (instant frame query)
                while (isRunning.get()) {
                    val frameStartNs = System.nanoTime()
                    val requestStartTimeMs = System.currentTimeMillis()

                    // Send GET_INFO query
                    outStream.write(cmdBytes)
                    outStream.flush()

                    // Read JSON response line
                    val line = bufferedReader.readLine() ?: throw SocketException("Socket closed by remote daemon (EOF)")

                    val roundTripLatencyMs = System.currentTimeMillis() - requestStartTimeMs
                    val rawBytesLen = line.length

                    // Parse FrameSnapshot
                    val snapshot = FrameSnapshot.parse(line)

                    // If snapshot has version metadata, update state manager
                    if (snapshot.version.isNotBlank()) {
                        stateManager.setDaemonMetadata(snapshot.version, snapshot.buildHash)
                    }

                    // Detect Game Restart / PID Transitions
                    if (lastKnownPid > 0 && snapshot.pid > 0 && snapshot.pid != lastKnownPid) {
                        for (listener in listeners) {
                            try {
                                listener.onGameRestart(lastKnownPid, snapshot.pid)
                            } catch (e: Exception) {
                                System.err.println("[TelemetryClient] Listener error onGameRestart: ${e.message}")
                            }
                        }
                    }
                    if (snapshot.pid > 0) {
                        lastKnownPid = snapshot.pid
                    }

                    // Publish snapshot to StateManager and listeners
                    stateManager.onFrameReceived(snapshot, rawBytesLen, roundTripLatencyMs)
                    for (listener in listeners) {
                        try {
                            listener.onFrameSnapshot(snapshot)
                        } catch (e: Exception) {
                            System.err.println("[TelemetryClient] Listener error onFrameSnapshot: ${e.message}")
                        }
                    }

                    // Precise frame rate pacing
                    val frameDurationNs = System.nanoTime() - frameStartNs
                    val sleepNs = targetFrameIntervalNs - frameDurationNs
                    if (sleepNs > 1_000_000L) { // > 1ms
                        val sleepMs = sleepNs / 1_000_000L
                        val sleepRemainingNs = (sleepNs % 1_000_000L).toInt()
                        Thread.sleep(sleepMs, sleepRemainingNs)
                    }
                }

            } catch (e: InterruptedException) {
                // Thread interrupted for shutdown
                break
            } catch (e: Exception) {
                if (!isRunning.get()) break

                isConnected.set(false)
                closeSocket()

                val errorMsg = e.message ?: e.javaClass.simpleName
                stateManager.onErrorOccurred("Telemetry error: $errorMsg")
                stateManager.onReconnectAttempt()

                for (listener in listeners) {
                    try {
                        listener.onError(e)
                        listener.onDisconnected(errorMsg, willReconnect = isRunning.get())
                    } catch (ex: Exception) {
                        System.err.println("[TelemetryClient] Listener error onDisconnected: ${ex.message}")
                    }
                }

                // Sub-60ms exponential backoff with jitter
                val jitter = Random.nextLong(0, 15)
                val sleepTimeMs = (currentBackoffMs + jitter).coerceAtMost(maxBackoffMs)
                currentBackoffMs = (currentBackoffMs * 2).coerceAtMost(maxBackoffMs)

                try {
                    Thread.sleep(sleepTimeMs)
                } catch (ie: InterruptedException) {
                    break
                }
            } finally {
                closeSocket()
            }
        }

        isConnected.set(false)
        stateManager.updateConnectionStatus(ConnectionStatus.DISCONNECTED, "Disconnected")
    }

    private fun closeSocket() {
        try {
            reader?.close()
        } catch (ignored: Exception) {}
        try {
            writer?.close()
        } catch (ignored: Exception) {}
        try {
            socket?.close()
        } catch (ignored: Exception) {}
        reader = null
        writer = null
        socket = null
    }
}
