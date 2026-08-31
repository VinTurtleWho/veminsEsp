#!/system/bin/sh
# ==============================================================================
# start_esp.sh — 1-Click Universal Starter for VEMINS Overlay & Daemon
# ==============================================================================

echo "====================================================="
echo "  Starting VEMINS ESP & Memory Daemon in VM...       "
echo "====================================================="

# 1. Kill old processes to free port 9999
pkill -9 vemins_daemon 2>/dev/null || true
pkill -9 agent_daemon 2>/dev/null || true
fuser -k 9999/tcp 2>/dev/null || true
sleep 0.2

# 2. Auto-copy newest files and APK from shared storage
APK_PATH=""
for src in \
    /sdcard/Download \
    /sdcard/veminsEsp \
    /sdcard \
    /storage/emulated/0/Download \
    /storage/emulated/0/veminsEsp \
    /sdcard/VMOSfiletransferstation; do
    if [ -f "$src/vemins_daemon" ]; then
        cp -f "$src/vemins_daemon" /data/local/tmp/vemins_daemon 2>/dev/null || true
    fi
    if [ -f "$src/minimap_config.json" ]; then
        cp -f "$src/minimap_config.json" /data/local/tmp/minimap_config.json 2>/dev/null || true
    fi
    if [ -d "$src/assets" ] && [ ! -d "/data/local/tmp/assets" ]; then
        mkdir -p /data/local/tmp/assets 2>/dev/null || true
        cp -rf "$src/assets/"* /data/local/tmp/assets/ 2>/dev/null || true
    fi
    if [ -f "$src/veminsEsp.apk" ] && [ -z "$APK_PATH" ]; then
        APK_PATH="$src/veminsEsp.apk"
    elif [ -f "$src/vemins_overlay_app.apk" ] && [ -z "$APK_PATH" ]; then
        APK_PATH="$src/vemins_overlay_app.apk"
    fi
done

# 3. Check and start Memory Daemon
if [ ! -f /data/local/tmp/vemins_daemon ]; then
    echo "[-] Error: /data/local/tmp/vemins_daemon not found!"
    exit 1
fi

chmod 755 /data/local/tmp/vemins_daemon 2>/dev/null || true

nohup /data/local/tmp/vemins_daemon 9999 > /data/local/tmp/vemins_daemon.log 2>&1 &
sleep 0.3
echo "[✓] vemins_daemon running in background on port 9999"

# 4. Auto-install overlay APK if not already installed
if ! pm list packages | grep -q "com.vemins.esp"; then
    if [ -n "$APK_PATH" ]; then
        echo "[+] Installing VEMINS Overlay App from $APK_PATH..."
        pm install -r "$APK_PATH" 2>/dev/null && echo "[✓] Overlay App Installed successfully!"
    else
        echo "[-] Note: Install veminsEsp.apk manually if not installed."
    fi
fi

# 5. Automatically grant Overlay & Notification Permissions (Root)
appops set com.vemins.esp SYSTEM_ALERT_WINDOW allow 2>/dev/null || true
pm grant com.vemins.esp android.permission.POST_NOTIFICATIONS 2>/dev/null || true

# 6. Launch Overlay Foreground Service & Dashboard
if pm list packages | grep -q "com.vemins.esp"; then
    am start-foreground-service -n com.vemins.esp/.service.FloatingOverlayService 2>/dev/null || \
    am startservice -n com.vemins.esp/.service.FloatingOverlayService 2>/dev/null || \
    am start -n com.vemins.esp/.ui.MainActivity 2>/dev/null || true
    echo "[✓] VEMINS Floating Overlay Service Launched (com.vemins.esp)!"
fi

echo "====================================================="
echo "  VEMINS ESP ACTIVE! Launch Mobile Legends to play.  "
echo "  • Package    : com.vemins.esp                      "
echo "  • Daemon Log : /data/local/tmp/vemins_daemon.log   "
echo "====================================================="
