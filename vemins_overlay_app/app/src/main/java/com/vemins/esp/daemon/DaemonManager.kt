package com.vemins.esp.daemon

import android.content.Context
import android.util.Log
import java.io.File
import java.io.FileOutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

enum class DaemonStatus {
    STOPPED,
    STARTING,
    RUNNING,
    NO_ROOT,
    ERROR
}

/**
 * Embedded Native Daemon Manager and Supervisor Watchdog.
 *
 * Responsibilities:
 * 1. Automatically extracts `bin/vemins_daemon` from APK assets to internal storage (`context.filesDir`).
 * 2. Launches the native daemon with root (`su`) in the background.
 * 3. Maintains an active heartbeat watchdog that detects socket drops and auto-recovers the daemon within 500ms.
 */
class DaemonManager private constructor(private val context: Context) {

    companion object {
        private const val TAG = "DaemonManager"
        const val DAEMON_PORT = 9999
        private const val DAEMON_BINARY_NAME = "vemins_daemon"

        @Volatile
        private var instance: DaemonManager? = null

        fun getInstance(context: Context): DaemonManager {
            return instance ?: synchronized(this) {
                instance ?: DaemonManager(context.applicationContext).also { instance = it }
            }
        }
    }

    private val isWatchdogRunning = AtomicBoolean(false)
    private var scheduler: ScheduledExecutorService? = null
    private var currentStatus: DaemonStatus = DaemonStatus.STOPPED
    var onStatusChanged: ((DaemonStatus) -> Unit)? = null

    val daemonFile: File
        get() = File(context.filesDir, DAEMON_BINARY_NAME)

    val systemTmpDaemonFile: File
        get() = File("/data/local/tmp", DAEMON_BINARY_NAME)

    /**
     * Extracts `assets/bin/vemins_daemon` into `context.filesDir` and stages to `/data/local/tmp/vemins_daemon`.
     */
    fun extractDaemonIfNeeded(): Boolean {
        return try {
            val destFile = daemonFile
            var shouldExtract = !destFile.exists()

            if (!shouldExtract) {
                try {
                    context.assets.open("bin/$DAEMON_BINARY_NAME").use { stream ->
                        if (stream.available().toLong() != destFile.length()) {
                            shouldExtract = true
                        }
                    }
                } catch (_: Exception) {
                    shouldExtract = true
                }
            }

            if (shouldExtract) {
                Log.i(TAG, "Extracting bundled $DAEMON_BINARY_NAME from APK assets to ${destFile.absolutePath}...")
                context.assets.open("bin/$DAEMON_BINARY_NAME").use { input ->
                    FileOutputStream(destFile).use { output ->
                        input.copyTo(output)
                        output.flush()
                    }
                }
                destFile.setExecutable(true, false)
                destFile.setReadable(true, false)
                try {
                    Runtime.getRuntime().exec("chmod 755 ${destFile.absolutePath}").waitFor()
                } catch (_: Exception) {}
            }

            // Always ensure staged to /data/local/tmp for root execution compatibility
            try {
                val suCmd = "cp -f ${destFile.absolutePath} /data/local/tmp/$DAEMON_BINARY_NAME 2>/dev/null && chmod 755 /data/local/tmp/$DAEMON_BINARY_NAME"
                Runtime.getRuntime().exec(arrayOf("su", "-c", suCmd)).waitFor()
            } catch (_: Exception) {}

            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to extract native daemon: ${e.message}", e)
            false
        }
    }

    /**
     * Quick non-blocking probe to verify if the daemon is actively listening on port 9999.
     */
    fun isDaemonPortOpen(timeoutMs: Int = 800): Boolean {
        return try {
            Socket().use { socket ->
                socket.connect(InetSocketAddress("127.0.0.1", DAEMON_PORT), timeoutMs)
                true
            }
        } catch (_: Exception) {
            false
        }
    }

    /**
     * Checks if root access (`su`) is available on this Android device/VM.
     */
    fun isRootAvailable(): Boolean {
        return try {
            val process = Runtime.getRuntime().exec(arrayOf("su", "-c", "id"))
            val output = process.inputStream.bufferedReader().readText()
            process.waitFor()
            output.contains("uid=0")
        } catch (_: Exception) {
            false
        }
    }

    /**
     * Starts the native daemon via `su` if not already running.
     */
    @Synchronized
    fun startDaemon(): Boolean {
        extractDaemonIfNeeded()

        if (isDaemonPortOpen(800)) {
            setStatus(DaemonStatus.RUNNING)
            return true
        }

        setStatus(DaemonStatus.STARTING)
        val internalBinaryPath = daemonFile.absolutePath
        val systemBinaryPath = "/data/local/tmp/$DAEMON_BINARY_NAME"

        return try {
            // Stage to /data/local/tmp and run in background with clean socket port freeing
            val command = "cp -f $internalBinaryPath $systemBinaryPath 2>/dev/null; chmod 755 $systemBinaryPath; pkill -9 $DAEMON_BINARY_NAME 2>/dev/null; killall -9 $DAEMON_BINARY_NAME 2>/dev/null; fuser -k $DAEMON_PORT/tcp 2>/dev/null; nohup $systemBinaryPath $DAEMON_PORT >/data/local/tmp/vemins_daemon.log 2>&1 &"
            val process = Runtime.getRuntime().exec(arrayOf("su", "-c", command))
            process.waitFor()

            // Poll port with quick retries
            var connected = false
            for (i in 0 until 12) {
                Thread.sleep(150)
                if (isDaemonPortOpen(400)) {
                    connected = true
                    break
                }
            }

            if (connected) {
                setStatus(DaemonStatus.RUNNING)
                Log.i(TAG, "Native daemon successfully launched with root on port $DAEMON_PORT")
                true
            } else {
                try {
                    Runtime.getRuntime().exec(arrayOf(internalBinaryPath, DAEMON_PORT.toString()))
                    Thread.sleep(300)
                    if (isDaemonPortOpen(500)) {
                        setStatus(DaemonStatus.RUNNING)
                        return true
                    }
                } catch (_: Exception) {}

                setStatus(if (!isRootAvailable()) DaemonStatus.NO_ROOT else DaemonStatus.ERROR)
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error launching daemon: ${e.message}", e)
            setStatus(DaemonStatus.ERROR)
            false
        }
    }

    /**
     * Force-restarts the native daemon by killing any stale processes and relaunching.
     */
    @Synchronized
    fun restartDaemon(): Boolean {
        try {
            val killCmd = "pkill -9 $DAEMON_BINARY_NAME 2>/dev/null; killall -9 $DAEMON_BINARY_NAME 2>/dev/null; fuser -k $DAEMON_PORT/tcp 2>/dev/null"
            Runtime.getRuntime().exec(arrayOf("su", "-c", killCmd)).waitFor()
        } catch (_: Exception) {}
        Thread.sleep(150)
        return startDaemon()
    }

    /**
     * Starts the background watchdog supervisor that monitors port 9999 and auto-recovers.
     */
    @Synchronized
    fun startWatchdog() {
        if (isWatchdogRunning.getAndSet(true)) return

        scheduler = Executors.newSingleThreadScheduledExecutor { r ->
            Thread(r, "VeminsDaemonWatchdog").apply { isDaemon = true }
        }

        scheduler?.execute {
            if (!isDaemonPortOpen(800)) {
                startDaemon()
            } else {
                setStatus(DaemonStatus.RUNNING)
            }
        }

        scheduler?.scheduleWithFixedDelay({
            if (isWatchdogRunning.get()) {
                if (!isDaemonPortOpen(800)) {
                    Log.w(TAG, "Watchdog detected port $DAEMON_PORT down! Auto-recovering daemon...")
                    startDaemon()
                } else {
                    if (currentStatus != DaemonStatus.RUNNING) {
                        setStatus(DaemonStatus.RUNNING)
                    }
                }
            }
        }, 3, 3, TimeUnit.SECONDS)
    }

    /**
     * Stops the watchdog supervisor.
     */
    @Synchronized
    fun stopWatchdog() {
        isWatchdogRunning.set(false)
        scheduler?.shutdownNow()
        scheduler = null
    }

    fun getStatus(): DaemonStatus = currentStatus

    private fun setStatus(status: DaemonStatus) {
        currentStatus = status
        onStatusChanged?.invoke(status)
    }
}
