#!/system/bin/sh
# Universal 1-Click VM Daemon Starter for VEMINS ESP (Read-Only Telemetry)

echo "====================================================="
echo "  Starting VEMINS ESP Daemon in VM...               "
echo "====================================================="

# 1. Kill any existing instance
pkill -9 vemins_daemon 2>/dev/null || true
pkill -9 agent_daemon 2>/dev/null || true
fuser -k 9999/tcp 2>/dev/null || true

# 2. Locate and copy the newest binary to /data/local/tmp
COPIED=0
for src in \
    /sdcard/Download/vemins_daemon \
    /sdcard/Download/vemins_daemon.txt \
    /sdcard/vemins_daemon \
    /sdcard/vemins_daemon.txt \
    /storage/emulated/0/veminsEsp/vemins_daemon \
    /storage/emulated/0/Download/vemins_daemon \
    /sdcard/VMOSfiletransferstation/vemins_daemon; do
    if [ -f "$src" ]; then
        cp -f "$src" /data/local/tmp/vemins_daemon
        COPIED=1
        echo "[+] Found and copied binary from: $src"
        break
    fi
done

if [ $COPIED -eq 0 ] && [ ! -f /data/local/tmp/vemins_daemon ]; then
    echo "[!] Error: vemins_daemon not found in /sdcard/Download or /sdcard. Please import it first."
    exit 1
fi

# 3. Set full permissions
chmod 777 /data/local/tmp/vemins_daemon

# 4. Start in background
nohup /data/local/tmp/vemins_daemon 9999 > /data/local/tmp/vemins_daemon.log 2>&1 &

sleep 0.5
echo "[✓] vemins_daemon is now running in background on port 9999!"
echo "[✓] Log file: /data/local/tmp/vemins_daemon.log"
echo "====================================================="
