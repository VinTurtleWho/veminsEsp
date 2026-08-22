package com.vemins.esp.net

import android.os.Handler
import android.os.Looper
import android.util.Log
import com.vemins.esp.config.ConfigManager
import com.vemins.esp.config.OverlayConfig
import com.vemins.esp.state.ConnectionStatus
import com.vemins.esp.state.OverlayStateManager
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketException
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Embedded HTTP Control API Server for VeminsESP (com.vemins.esp.net).
 *
 * Exposes REST endpoints:
 * - GET  /api/status : Live application status, FPS, and telemetry frame snapshot summary.
 * - GET  /api/config : Active configuration parameters.
 * - POST /api/config : Dynamic updates to configuration from CLI / Termux.
 * - GET  /api/ping   : Instant health check ping.
 * - POST /api/toggle : Start/stop overlay toggle.
 */
class LocalControlServer(
    private val host: String = DEFAULT_HOST,
    private val port: Int = DEFAULT_PORT,
    private val configManager: ConfigManager = ConfigManager.getInstance(),
    private val stateManager: OverlayStateManager = OverlayStateManager.getInstance()
) {
    companion object {
        const val DEFAULT_HOST = "127.0.0.1"
        const val DEFAULT_PORT = 8888
        private const val TAG = "LocalControlServerESP"

        @Volatile
        private var instance: LocalControlServer? = null

        fun getInstance(port: Int): LocalControlServer {
            return getInstance(DEFAULT_HOST, port)
        }

        fun getInstance(host: String = DEFAULT_HOST, port: Int = DEFAULT_PORT): LocalControlServer {
            return instance ?: synchronized(this) {
                instance ?: LocalControlServer(host, port).also { instance = it }
            }
        }
    }

    private val isRunning = AtomicBoolean(false)
    private var serverSocket: ServerSocket? = null
    private var executor: ExecutorService? = null
    private var serverThread: Thread? = null

    var onToggleServiceRequest: (() -> Unit)? = null

    @Synchronized
    fun start() {
        if (isRunning.compareAndSet(false, true)) {
            executor = Executors.newFixedThreadPool(4)
            serverThread = Thread({ runServerLoop() }, "VeminsEspControlServerThread").apply {
                isDaemon = true
                start()
            }
            Log.i(TAG, "LocalControlServer started on $host:$port")
        }
    }

    @Synchronized
    fun stop() {
        if (isRunning.compareAndSet(true, false)) {
            try {
                serverSocket?.close()
            } catch (e: Exception) {
                Log.w(TAG, "Error closing server socket: ${e.message}")
            }
            serverSocket = null

            executor?.shutdownNow()
            executor = null

            serverThread?.interrupt()
            serverThread = null
            Log.i(TAG, "LocalControlServer stopped")
        }
    }

    fun isRunning(): Boolean = isRunning.get()

    private fun runServerLoop() {
        try {
            val bindAddr = if (host == "0.0.0.0") null else InetAddress.getByName(host)
            serverSocket = ServerSocket(port, 50, bindAddr)
            serverSocket?.reuseAddress = true

            while (isRunning.get() && !Thread.currentThread().isInterrupted) {
                try {
                    val clientSocket = serverSocket?.accept() ?: break
                    executor?.execute {
                        handleClient(clientSocket)
                    }
                } catch (e: SocketException) {
                    if (!isRunning.get()) break
                } catch (e: Exception) {
                    if (!isRunning.get()) break
                    Log.w(TAG, "Error accepting connection: ${e.message}")
                }
            }
        } catch (e: Exception) {
            if (isRunning.get()) {
                Log.e(TAG, "Failed to start server on $host:$port: ${e.message}", e)
            }
        } finally {
            isRunning.set(false)
        }
    }

    private fun handleClient(socket: Socket) {
        try {
            socket.soTimeout = 5000
            val reader = BufferedReader(InputStreamReader(socket.getInputStream(), Charsets.UTF_8))
            val output = socket.getOutputStream()

            val requestLine = reader.readLine() ?: return
            val parts = requestLine.trim().split(" ")
            if (parts.size < 2) return

            val method = parts[0].toUpperCase()
            val fullPath = parts[1]
            val path = fullPath.split("?")[0]

            val headers = mutableMapOf<String, String>()
            var line = reader.readLine()
            while (!line.isNullOrEmpty()) {
                val headerParts = line.split(":", limit = 2)
                if (headerParts.size == 2) {
                    headers[headerParts[0].trim().toLowerCase()] = headerParts[1].trim()
                }
                line = reader.readLine()
            }

            var body = ""
            val contentLength = headers["content-length"]?.toIntOrNull() ?: 0
            if (contentLength > 0) {
                val bodyChars = CharArray(contentLength)
                var readTotal = 0
                while (readTotal < contentLength) {
                    val read = reader.read(bodyChars, readTotal, contentLength - readTotal)
                    if (read < 0) break
                    readTotal += read
                }
                body = String(bodyChars, 0, readTotal)
            }

            when {
                method == "OPTIONS" -> {
                    sendCorsResponse(output, 204, "No Content")
                }
                method == "GET" && (path == "/api/ping" || path == "/ping") -> {
                    val pong = JSONObject().apply {
                        put("status", "ok")
                        put("pong", true)
                        put("port", port)
                    }
                    sendJsonResponse(output, 200, "OK", pong.toString(2))
                }
                method == "GET" && (path == "/api/status" || path == "/status") -> {
                    handleGetStatus(output)
                }
                method == "GET" && (path == "/api/config" || path == "/config") -> {
                    handleGetConfig(output)
                }
                method == "POST" && (path == "/api/config" || path == "/config") -> {
                    handlePostConfig(output, body)
                }
                method == "POST" && (path == "/api/toggle" || path == "/toggle") -> {
                    onToggleServiceRequest?.invoke()
                    val resp = JSONObject().apply {
                        put("status", "ok")
                        put("action", "toggle")
                    }
                    sendJsonResponse(output, 200, "OK", resp.toString(2))
                }
                method == "GET" && (path == "/" || path == "/api") -> {
                    handleGetRoot(output)
                }
                else -> {
                    val notFound = JSONObject().apply {
                        put("status", "error")
                        put("error", "Not Found")
                        put("path", path)
                    }
                    sendJsonResponse(output, 404, "Not Found", notFound.toString(2))
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error handling request: ${e.message}")
        } finally {
            try { socket.close() } catch (_: Exception) {}
        }
    }

    private fun handleGetStatus(out: OutputStream) {
        val state = stateManager.getState()
        val stats = state.stats
        val status = state.connectionStatus

        val resp = JSONObject().apply {
            put("status", "ok")
            put("fps", stats.fps.toDouble())
            put("latency_ms", stats.latencyMs)
            put("target_pid", stats.targetPid)
            put("frames_received", stats.framesReceived)
            put("connection_state", status.name)
            put("connected_to_daemon", status == ConnectionStatus.CONNECTED)
            put("timestamp", System.currentTimeMillis())
        }

        sendJsonResponse(out, 200, "OK", resp.toString(2))
    }

    private fun handleGetConfig(out: OutputStream) {
        val configJson = configManager.getConfig().toJson()
        sendJsonResponse(out, 200, "OK", configJson.toString(2))
    }

    private fun handlePostConfig(out: OutputStream, body: String) {
        try {
            if (body.isEmpty()) {
                val err = JSONObject().apply {
                    put("status", "error")
                    put("error", "Empty request body")
                }
                sendJsonResponse(out, 400, "Bad Request", err.toString(2))
                return
            }

            val json = JSONObject(body)
            val newConfig = OverlayConfig.fromJson(json)
            configManager.updateFullConfig(newConfig, autoSave = true)

            val resp = JSONObject().apply {
                put("status", "success")
                put("message", "Configuration updated successfully")
                put("config", configManager.getConfig().toJson())
            }
            sendJsonResponse(out, 200, "OK", resp.toString(2))
        } catch (e: Exception) {
            val err = JSONObject().apply {
                put("status", "error")
                put("error", "JSON error: ${e.message}")
            }
            sendJsonResponse(out, 400, "Bad Request", err.toString(2))
        }
    }

    private fun handleGetRoot(out: OutputStream) {
        val root = JSONObject().apply {
            put("app", "VeminsESP Local Control Server")
            put("version", "1.0.0-ESP")
            put("endpoints", JSONArray().apply {
                put("GET  /api/ping   : Instant ping check")
                put("GET  /api/status : Returns app status, FPS, and live telemetry summary")
                put("GET  /api/config : Returns current active overlay configuration")
                put("POST /api/config : Updates configuration parameters dynamically")
                put("POST /api/toggle : Toggles overlay service")
            })
        }
        sendJsonResponse(out, 200, "OK", root.toString(2))
    }

    private fun sendCorsResponse(out: OutputStream, statusCode: Int, statusText: String) {
        val headers = "HTTP/1.1 $statusCode $statusText\r\n" +
                "Access-Control-Allow-Origin: *\r\n" +
                "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n" +
                "Access-Control-Allow-Headers: Content-Type, Authorization\r\n" +
                "Content-Length: 0\r\n" +
                "Connection: close\r\n\r\n"
        out.write(headers.toByteArray(Charsets.UTF_8))
        out.flush()
    }

    private fun sendJsonResponse(out: OutputStream, statusCode: Int, statusText: String, json: String) {
        val bytes = json.toByteArray(Charsets.UTF_8)
        val headers = "HTTP/1.1 $statusCode $statusText\r\n" +
                "Content-Type: application/json; charset=UTF-8\r\n" +
                "Content-Length: ${bytes.size}\r\n" +
                "Connection: close\r\n" +
                "Access-Control-Allow-Origin: *\r\n" +
                "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n" +
                "Access-Control-Allow-Headers: Content-Type, Authorization\r\n" +
                "\r\n"
        out.write(headers.toByteArray(Charsets.UTF_8))
        out.write(bytes)
        out.flush()
    }
}
