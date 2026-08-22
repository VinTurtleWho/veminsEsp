#!/bin/bash
# ==============================================================================
# build_vemins_esp.sh — Build Native Android On-Screen ESP Overlay Executable
# Compiles with Android NDK Bionic clang++ (targeting /system/bin/linker64).
# Bundles libc++_shared.so for seamless execution inside Android VMs.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OUTPUT_BIN="vemins_esp"
VERSION="1.3.0-ESP"

echo "================================================================="
echo "       BUILDING VEMINS_ESP NATIVE ANDROID OVERLAY ($VERSION)     "
echo "================================================================="

CLANG_BIN="/data/data/com.termux/files/usr/bin/clang++"
if [ ! -f "$CLANG_BIN" ]; then
    CLANG_BIN="clang++"
fi

$CLANG_BIN -O3 -std=c++17 -Wall -fPIC \
    -L/data/data/com.termux/files/usr/lib \
    gl_bindings.cpp \
    native_surface.cpp \
    texture_manager.cpp \
    gl_renderer.cpp \
    vemins_esp.cpp \
    -o "$OUTPUT_BIN" \
    -lm -ldl

chmod +x "$OUTPUT_BIN"
echo "[✓] Native Android binary compiled: $OUTPUT_BIN"

# Stage to shared storage volumes for VM transfer
LIBCPP="/data/data/com.termux/files/usr/lib/libc++_shared.so"

for dst in "/sdcard" "/sdcard/Download" "/sdcard/veminsEsp" "/storage/emulated/0/Download"; do
    if [ -d "$dst" ]; then
        cp -f "$OUTPUT_BIN" "$dst/vemins_esp" 2>/dev/null && {
            echo "[✓] Staged binary to: $dst/vemins_esp"
        }
        if [ -f "$LIBCPP" ]; then
            cp -f "$LIBCPP" "$dst/libc++_shared.so" 2>/dev/null && {
                echo "[✓] Staged libc++_shared.so to: $dst/libc++_shared.so"
            }
        fi
        if [ -f "start_esp.sh" ]; then
            cp -f "start_esp.sh" "$dst/start_esp.sh" 2>/dev/null
        fi
        if [ -f "minimap_config.json" ]; then
            cp -f "minimap_config.json" "$dst/minimap_config.json" 2>/dev/null
        fi
        if [ -d "assets" ]; then
            mkdir -p "$dst/assets" 2>/dev/null || true
            cp -rf assets/* "$dst/assets/" 2>/dev/null || true
        fi
    fi
done

echo "================================================================="
