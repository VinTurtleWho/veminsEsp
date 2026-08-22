#!/bin/bash
# ==============================================================================
# build_vemins_daemon.sh — Deterministic Build & Staging for VEMINS ESP Daemon
# Read-only external telemetry daemon for MLBB (No evdev/touch injection).
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SOURCE_FILE="vemins_daemon.c"
OUTPUT_BIN="vemins_daemon"
HASH_FILE="vemins_daemon.hash"
VERSION="1.0.0-ESP"
BUILD_TIME="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"

if [ ! -f "$SOURCE_FILE" ]; then
    echo "[-] Error: $SOURCE_FILE not found in $SCRIPT_DIR"
    exit 1
fi

# 1. Compute SHA-256 hash of vemins_daemon.c
BUILD_HASH="$(sha256sum "$SOURCE_FILE" | awk '{print $1}')"
SHORT_HASH="${BUILD_HASH:0:16}"
echo "$SHORT_HASH" > "$HASH_FILE"

echo "================================================================="
echo "       BUILDING VEMINS_DAEMON (VERSION $VERSION)                "
echo "================================================================="
echo "[+] Source File  : $SOURCE_FILE"
echo "[+] Build Time   : $BUILD_TIME"
echo "[+] SHA-256 Hash : $BUILD_HASH ($SHORT_HASH)"

# 2. Compile Native ARM64 ELF Binary (Android Bionic Target)
CLANG_BIN="/data/data/com.termux/files/usr/bin/clang"
if [ ! -f "$CLANG_BIN" ]; then
    CLANG_BIN="clang"
fi

$CLANG_BIN -O2 -Wall -fPIC \
    -DVEMINS_VERSION="\"$VERSION\"" \
    -DVEMINS_BUILD_HASH="\"$SHORT_HASH\"" \
    -DVEMINS_BUILD_TIME="\"$BUILD_TIME\"" \
    "$SOURCE_FILE" -o "$OUTPUT_BIN" -lm

chmod +x "$OUTPUT_BIN"
echo "[✓] Native binary compiled successfully: $OUTPUT_BIN"

# 3. Stage to APK assets and Shared Storage Volumes for VM Transfer
ASSETS_BIN_DIR="vemins_overlay_app/app/src/main/assets/bin"
if [ -d "$ASSETS_BIN_DIR" ]; then
    cp -f "$OUTPUT_BIN" "$ASSETS_BIN_DIR/vemins_daemon"
    echo "[✓] Staged binary to APK assets: $ASSETS_BIN_DIR/vemins_daemon"
fi

STAGED=0
for dst in "/sdcard" "/sdcard/Download" "/sdcard/veminsEsp" "/storage/emulated/0/Download" "/storage/emulated/0/veminsEsp"; do
    if [ -d "$dst" ]; then
        cp -f "$OUTPUT_BIN" "$dst/vemins_daemon" 2>/dev/null && {
            echo "[✓] Staged binary to: $dst/vemins_daemon"
            STAGED=$((STAGED+1))
        }
    fi
done

echo ""
echo "================================================================="
echo "           MANUAL VM TRANSFER & STARTUP COMMAND                  "
echo "================================================================="
echo "To start vemins_daemon in the VM without touching agent_daemon:"
echo ""
echo "  su -c \"cp /sdcard/vemins_daemon /data/local/tmp/vemins_daemon && chmod 755 /data/local/tmp/vemins_daemon && killall vemins_daemon 2>/dev/null; /data/local/tmp/vemins_daemon &\""
echo "================================================================="
