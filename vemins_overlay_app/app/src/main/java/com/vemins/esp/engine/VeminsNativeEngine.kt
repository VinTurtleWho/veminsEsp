package com.vemins.esp.engine

import android.util.Log
import android.view.Surface
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicBoolean

/**
 * VeminsNativeEngine - High-Performance NDK Perception Engine Bridge.
 * Interfaces directly with libvemins_engine.so with zero-copy DirectByteBuffer frame polling.
 */
object VeminsNativeEngine {
    private const val TAG = "VeminsNativeEngine"
    private const val LIB_NAME = "vemins_engine"

    /**
     * Exact binary snapshot payload size in bytes (matches sizeof(FrameSnapshotBinary)).
     * 64 (Header) + 2400 (Heroes) + 1408 (Soldiers) + 1408 (Monsters) + 880 (Towers) = 6160 bytes.
     */
    const val SNAPSHOT_BUFFER_SIZE = 6160

    private val isLibraryLoaded = AtomicBoolean(false)
    private val isInitialized = AtomicBoolean(false)

    /**
     * Pre-allocated Direct ByteBuffer allocated in off-heap native memory.
     * Fixed size of 6,160 bytes, aligned to native Little-Endian byte order.
     */
    val directBuffer: ByteBuffer by lazy {
        ByteBuffer.allocateDirect(SNAPSHOT_BUFFER_SIZE).order(ByteOrder.LITTLE_ENDIAN)
    }

    /**
     * Pre-allocated scratch array for native telemetry diagnostics.
     * Layout: [0]=FPS, [1]=ReadLatencyMs, [2]=HeroCount, [3]=MinionCount, [4]=MonsterCount
     */
    val scratchTelemetryStats = FloatArray(8)

    init {
        try {
            loadNativeLibrary()
        } catch (t: Throwable) {
            Log.w(TAG, "Native library load deferred: ${t.message}")
        }
    }

    fun loadNativeLibrary(): Boolean {
        if (isLibraryLoaded.get()) return true
        return try {
            try {
                System.loadLibrary("c++_shared")
            } catch (_: Throwable) {}
            System.loadLibrary(LIB_NAME)
            isLibraryLoaded.set(true)
            Log.i(TAG, "Successfully loaded native perception library '$LIB_NAME'")
            true
        } catch (t: Throwable) {
            Log.w(TAG, "Native library '$LIB_NAME' not available in runtime: ${t.message}")
            false
        }
    }

    fun initEngine(): Boolean {
        if (!isLibraryLoaded.get() && !loadNativeLibrary()) return false
        if (isInitialized.get()) return true

        return try {
            val ok = nativeInit()
            isInitialized.set(ok)
            if (ok) {
                Log.i(TAG, "Native perception engine initialized successfully")
            } else {
                Log.e(TAG, "nativeInit() returned false")
            }
            ok
        } catch (t: Throwable) {
            Log.e(TAG, "Error initializing native engine", t)
            false
        }
    }

    fun releaseEngine() {
        if (!isInitialized.getAndSet(false)) return
        try {
            nativeRelease()
            Log.i(TAG, "Native perception engine released")
        } catch (t: Throwable) {
            Log.e(TAG, "Error releasing native engine", t)
        }
    }

    fun setMemoryFileDescriptor(fd: Int, pid: Int): Boolean {
        if (!isInitialized.get() && !initEngine()) return false
        return try {
            nativeSetMemFd(fd, pid)
        } catch (t: Throwable) {
            Log.e(TAG, "Error setting mem fd: ${t.message}", t)
            false
        }
    }

    fun pollSnapshot(buffer: ByteBuffer = directBuffer): Int {
        if (!isInitialized.get() && !initEngine()) return -2
        return try {
            nativePollSnapshot(buffer)
        } catch (t: Throwable) {
            Log.e(TAG, "Error polling snapshot: ${t.message}", t)
            -1
        }
    }

    fun getTelemetry(outStats: FloatArray = scratchTelemetryStats) {
        if (!isInitialized.get()) return
        try {
            nativeGetTelemetry(outStats)
        } catch (t: Throwable) {
            Log.e(TAG, "Error getting telemetry: ${t.message}", t)
        }
    }

    // =========================================================================
    // JNI Native Declarations
    // =========================================================================

    external fun nativeInit(): Boolean
    external fun nativeRelease()
    external fun nativeSetMemFd(fd: Int, pid: Int): Boolean
    external fun nativePollSnapshot(buffer: ByteBuffer): Int
    external fun nativeGetTelemetry(outStats: FloatArray)

    // Hardware SurfaceView Bindings
    external fun nativeSurfaceCreated(surface: Surface, width: Int, height: Int): Boolean
    external fun nativeSurfaceChanged(surface: Surface, width: Int, height: Int)
    external fun nativeSurfaceDestroyed()
    external fun nativeDispatchTouch(action: Int, x: Float, y: Float)
    external fun nativeUpdateConfig(
        minimapX: Float, minimapY: Float, minimapW: Float, minimapH: Float,
        scaleX: Float, scaleY: Float, rotationDeg: Float,
        showEnemies: Boolean, showMonsters: Boolean
    )
}
