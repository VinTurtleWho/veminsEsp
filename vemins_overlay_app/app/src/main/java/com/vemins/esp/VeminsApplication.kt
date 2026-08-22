package com.vemins.esp

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.vemins.esp.config.ConfigManager
import com.vemins.esp.net.LocalControlServer

class VeminsApplication : Application() {

    companion object {
        const val CHANNEL_ID = "vemins_overlay_channel"
        const val CHANNEL_NAME = "VeminsESP Tactical Overlay"
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()

        // Initialize ConfigManager with Application Context
        ConfigManager.getInstance(this)

        // Start Local Control Server on 127.0.0.1:8888
        try {
            LocalControlServer.getInstance("127.0.0.1", 8888).start()
        } catch (e: Exception) {
            System.err.println("[VeminsApplication] Failed to start LocalControlServer: ${e.message}")
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps VeminsESP Hardware-Passthrough Overlay active"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }
}
