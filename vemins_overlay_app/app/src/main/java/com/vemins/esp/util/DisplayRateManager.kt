package com.vemins.esp.util

import android.os.Handler
import android.os.Looper
import android.util.Log
import java.io.DataOutputStream
import java.util.concurrent.Executors

/**
 * Utility to unlock and force locked 120Hz display refresh rate on Android (ColorOS / OnePlus / Realme / AOSP).
 *
 * Overrides thermal and game space refresh rate caps by setting min/peak refresh rate
 * directly in system settings and unlocking game touch panel optimizations via root.
 */
object DisplayRateManager {

    private const val TAG = "DisplayRateManager"
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    private const val FORCE_120HZ_SCRIPT =
        "content insert --uri content://settings/system --bind name:s:min_refresh_rate --bind value:s:120.0; " +
        "content insert --uri content://settings/system --bind name:s:peak_refresh_rate --bind value:s:120.0; " +
        "content insert --uri content://settings/system --bind name:s:user_refresh_rate --bind value:s:120; " +
        "content insert --uri content://settings/secure --bind name:s:user_refresh_rate --bind value:s:120; " +
        "content insert --uri content://settings/global --bind name:s:oplus_display_dynamic_refresh_rate --bind value:s:0; " +
        "content insert --uri content://settings/global --bind name:s:oplus_display_refresh_rate --bind value:s:1; " +
        "content insert --uri content://settings/system --bind name:s:oplus_customize_display_fps --bind value:s:120; " +
        "echo 1 > /proc/touchpanel/game_switch_enable 2>/dev/null; " +
        "echo 0 > /proc/touchpanel/oplus_tp_limit_enable 2>/dev/null; " +
        "setprop debug.refresh_rate.view_override 1 2>/dev/null"

    private const val RESTORE_AUTO_SCRIPT =
        "content insert --uri content://settings/system --bind name:s:min_refresh_rate --bind value:s:60.0; " +
        "content insert --uri content://settings/system --bind name:s:peak_refresh_rate --bind value:s:120.0; " +
        "content insert --uri content://settings/global --bind name:s:oplus_display_dynamic_refresh_rate --bind value:s:1"

    /**
     * Executes root commands asynchronously to lock display refresh rate to 120Hz.
     */
    fun force120Hz(callback: ((Boolean) -> Unit)? = null) {
        executor.execute {
            val success = executeRootScript(FORCE_120HZ_SCRIPT)
            Log.i(TAG, "[+] Force 120Hz command result: success=$success")
            mainHandler.post {
                callback?.invoke(success)
            }
        }
    }

    /**
     * Restores automatic dynamic refresh rate.
     */
    fun restoreAutoHz(callback: ((Boolean) -> Unit)? = null) {
        executor.execute {
            val success = executeRootScript(RESTORE_AUTO_SCRIPT)
            mainHandler.post {
                callback?.invoke(success)
            }
        }
    }

    /**
     * Synchronously writes active flag for the Magisk/KernelSU stealth module.
     */
    fun setStealthModuleActive(active: Boolean) {
        executor.execute {
            val flagVal = if (active) "1" else "0"
            executeRootScript("echo $flagVal > /data/local/tmp/vemins_stealth_active 2>/dev/null; chmod 666 /data/local/tmp/vemins_stealth_active 2>/dev/null")
        }
    }

    private fun executeRootScript(script: String): Boolean {
        var process: Process? = null
        var os: DataOutputStream? = null
        return try {
            process = Runtime.getRuntime().exec("su")
            os = DataOutputStream(process.outputStream)
            os.writeBytes(script + "\nexit\n")
            os.flush()
            val exitCode = process.waitFor()
            exitCode == 0
        } catch (e: Exception) {
            Log.e(TAG, "[-] Root execution failed: ${e.message}")
            false
        } finally {
            try {
                os?.close()
            } catch (_: Exception) {}
            try {
                process?.destroy()
            } catch (_: Exception) {}
        }
    }
}
