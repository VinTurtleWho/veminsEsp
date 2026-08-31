#!/data/data/com.termux/files/usr/bin/bash
set -e

# ==============================================================================
# VeminsESP — Standalone CLI Build System
# Compiles Native C++ libvemins_engine.so + Kotlin/Android App
# Built with: Clang++, AAPT2, D8, Kotlinc, apksigner
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo " [VEMINS ESP] Building Native Perception Engine & Android Overlay App"
echo " Project Root: $SCRIPT_DIR"
echo "================================================================================"

# 1. Detect Android SDK & Java Environment
SDK_CANDIDATES=(
    "$ANDROID_HOME"
    "$ANDROID_SDK_ROOT"
    "/data/data/com.termux/files/home/android-sdk"
    "/usr/lib/android-sdk"
    "/opt/android-sdk"
)

SDK_DIR=""
for dir in "${SDK_CANDIDATES[@]}"; do
    if [ -n "$dir" ] && [ -d "$dir/platforms" ]; then
        SDK_DIR="$dir"
        break
    fi
done

if [ -z "$SDK_DIR" ]; then
    echo "[-] Error: Android SDK not found in standard paths."
    exit 1
fi
echo "[+] Using Android SDK: $SDK_DIR"

# 2. Locate Android Platform JAR
ANDROID_JAR="$SDK_DIR/platforms/android-35/android.jar"
if [ ! -f "$ANDROID_JAR" ]; then
    ANDROID_JAR=$(find "$SDK_DIR/platforms" -name "android.jar" | sort -V | tail -n 1)
fi
if [ -z "$ANDROID_JAR" ] || [ ! -f "$ANDROID_JAR" ]; then
    echo "[-] Error: android.jar not found in $SDK_DIR/platforms."
    exit 1
fi
echo "[+] Using Android Platform JAR: $ANDROID_JAR"

# 3. Locate Build Tools (AAPT2, D8, apksigner, Kotlinc, Clang++)
AAPT2_BIN="/data/data/com.termux/files/usr/bin/aapt2"
if [ ! -x "$AAPT2_BIN" ]; then
    AAPT2_BIN=$(which aapt2 2>/dev/null || find "$SDK_DIR/build-tools" -name "aapt2" | sort -V | tail -n 1)
fi

D8_BIN=$(which d8 2>/dev/null || true)
D8_JAR="/data/data/com.termux/files/usr/share/java/d8.jar"
if [ ! -f "$D8_JAR" ]; then
    D8_JAR=$(find "$SDK_DIR/build-tools" -name "d8.jar" 2>/dev/null | sort -V | tail -n 1)
fi

APKSIGNER_BIN=$(which apksigner 2>/dev/null || true)
APKSIGNER_JAR="/data/data/com.termux/files/usr/share/java/apksigner.jar"
if [ ! -f "$APKSIGNER_JAR" ]; then
    APKSIGNER_JAR=$(find "$SDK_DIR/build-tools" -name "apksigner.jar" 2>/dev/null | sort -V | tail -n 1)
fi

ZIPALIGN_BIN=$(which zipalign 2>/dev/null || find "$SDK_DIR/build-tools" -name "zipalign" 2>/dev/null | sort -V | tail -n 1 || true)

KOTLIN_STDLIB_JAR="/data/data/com.termux/files/usr/opt/kotlin/lib/kotlin-stdlib.jar"
if [ ! -f "$KOTLIN_STDLIB_JAR" ]; then
    KOTLIN_STDLIB_JAR=$(find /data/data/com.termux/files/usr/ /usr/share/ -name "kotlin-stdlib.jar" 2>/dev/null | head -n 1)
fi

echo "[+] AAPT2: $AAPT2_BIN"
echo "[+] D8: ${D8_BIN:-$D8_JAR}"
echo "[+] apksigner: ${APKSIGNER_BIN:-$APKSIGNER_JAR}"
echo "[+] Kotlin StdLib: $KOTLIN_STDLIB_JAR"

# 4. Prepare Build Directories
BUILD_DIR="$SCRIPT_DIR/build"
GEN_DIR="$BUILD_DIR/gen"
CLASSES_DIR="$BUILD_DIR/classes"
R_CLASSES_DIR="$BUILD_DIR/r_classes"
DEX_DIR="$BUILD_DIR/dex"
JNILIBS_DIR="$SCRIPT_DIR/app/src/main/jniLibs/arm64-v8a"
OUT_APK="$SCRIPT_DIR/veminsEsp.apk"

rm -rf "$BUILD_DIR"
mkdir -p "$GEN_DIR" "$CLASSES_DIR" "$R_CLASSES_DIR" "$DEX_DIR" "$JNILIBS_DIR"

# 5. Compile Native C++ Perception Engine (libvemins_engine.so)
echo "[*] Step 1/7: Compiling Native C++ Engine (libvemins_engine.so)..."
clang++ -O3 -ffast-math -flto -fPIC -shared -Wall -Wextra -Werror -nostdlib++ \
    -Wl,-soname,libvemins_engine.so \
    -I app/src/main/cpp \
    app/src/main/cpp/memory_reader.cpp \
    app/src/main/cpp/jni_bridge.cpp \
    -lc -lm -ldl -llog -landroid \
    -o "$JNILIBS_DIR/libvemins_engine.so"

if [ -f "/data/data/com.termux/files/usr/lib/libc++_shared.so" ]; then
    cp -f "/data/data/com.termux/files/usr/lib/libc++_shared.so" "$JNILIBS_DIR/" 2>/dev/null || true
fi

echo "[+] Native Engine compiled: $JNILIBS_DIR/libvemins_engine.so ($(du -h "$JNILIBS_DIR/libvemins_engine.so" | cut -f1))"

# 6. Compile Resources with AAPT2
echo "[*] Step 2/7: Compiling Android resources with AAPT2..."
"$AAPT2_BIN" compile --dir app/src/main/res -o "$BUILD_DIR/compiled_res.zip"

ASSETS_ARG=""
if [ -d "app/src/main/assets" ]; then
    ASSETS_ARG="-A app/src/main/assets"
fi

echo "[*] Step 3/7: Linking resources & generating R.java..."
"$AAPT2_BIN" link \
    -I "$ANDROID_JAR" \
    --manifest app/src/main/AndroidManifest.xml \
    -o "$BUILD_DIR/unaligned.apk" \
    --java "$GEN_DIR" \
    --extra-packages com.vemins.esp:com.vemins.overlay \
    "$BUILD_DIR/compiled_res.zip" \
    $ASSETS_ARG \
    --auto-add-overlay

# 7. Compile Java & Kotlin Sources
echo "[*] Step 4/7: Compiling R.java & Kotlin source files..."
R_JAVA_SRCS=$(find "$GEN_DIR" -name "*.java" 2>/dev/null || true)
if [ -n "$R_JAVA_SRCS" ]; then
    javac -cp "$ANDROID_JAR" -d "$R_CLASSES_DIR" $R_JAVA_SRCS
fi

JAVA_APP_SRCS=$(find app/src/main/java -name "*.java" 2>/dev/null || true)
if [ -n "$JAVA_APP_SRCS" ]; then
    javac -cp "$ANDROID_JAR:$R_CLASSES_DIR" -d "$CLASSES_DIR" $JAVA_APP_SRCS
fi

KOTLIN_SRCS=$(find app/src/main/java -name "*.kt")

kotlinc -cp "$ANDROID_JAR:$R_CLASSES_DIR:$CLASSES_DIR:$KOTLIN_STDLIB_JAR" -d "$CLASSES_DIR" $KOTLIN_SRCS

# 8. Convert Class Files to Android Dalvik Executable (DEX)
echo "[*] Step 5/7: Dexing bytecode with D8..."
jar cf "$BUILD_DIR/app_classes.jar" -C "$CLASSES_DIR" . -C "$R_CLASSES_DIR" .

if [ -n "$D8_BIN" ]; then
    "$D8_BIN" --release --min-api 21 --lib "$ANDROID_JAR" --output "$DEX_DIR" \
        "$BUILD_DIR/app_classes.jar" "$KOTLIN_STDLIB_JAR"
elif [ -f "$D8_JAR" ]; then
    java -cp "$D8_JAR" com.android.tools.r8.D8 \
        --release --min-api 21 --lib "$ANDROID_JAR" --output "$DEX_DIR" \
        "$BUILD_DIR/app_classes.jar" "$KOTLIN_STDLIB_JAR"
else
    echo "[-] Error: D8 dexer not found."
    exit 1
fi

# 9. Package DEX & Native Libraries into APK
echo "[*] Step 6/7: Packaging DEX & Native libraries into APK..."
(cd "$DEX_DIR" && zip -u -q "$BUILD_DIR/unaligned.apk" classes*.dex)
mkdir -p "$BUILD_DIR/lib/arm64-v8a"
cp -f "$JNILIBS_DIR"/*.so "$BUILD_DIR/lib/arm64-v8a/" 2>/dev/null || true
(cd "$BUILD_DIR" && zip -u -q "$BUILD_DIR/unaligned.apk" lib/arm64-v8a/*.so)

if [ -n "$ZIPALIGN_BIN" ] && [ -x "$ZIPALIGN_BIN" ]; then
    "$ZIPALIGN_BIN" -f -p 4 "$BUILD_DIR/unaligned.apk" "$BUILD_DIR/aligned.apk"
else
    cp "$BUILD_DIR/unaligned.apk" "$BUILD_DIR/aligned.apk"
fi

# 10. Sign APK with apksigner (v1 + v2 + v3 schemes)
echo "[*] Step 7/7: Signing APK with apksigner..."
KEYSTORE="$SCRIPT_DIR/debug.keystore"
if [ ! -f "$KEYSTORE" ]; then
    keytool -genkeypair -v \
        -keystore "$KEYSTORE" \
        -storepass android \
        -alias androiddebugkey \
        -keypass android \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -dname "CN=VeminsESP Debug,O=Vemins,C=US"
fi

if [ -n "$APKSIGNER_BIN" ]; then
    "$APKSIGNER_BIN" sign \
        --ks "$KEYSTORE" \
        --ks-pass pass:android \
        --ks-key-alias androiddebugkey \
        --key-pass pass:android \
        --out "$OUT_APK" \
        "$BUILD_DIR/aligned.apk"
    "$APKSIGNER_BIN" verify --verbose "$OUT_APK"
elif [ -f "$APKSIGNER_JAR" ]; then
    java -jar "$APKSIGNER_JAR" sign \
        --ks "$KEYSTORE" \
        --ks-pass pass:android \
        --ks-key-alias androiddebugkey \
        --key-pass pass:android \
        --out "$OUT_APK" \
        "$BUILD_DIR/aligned.apk"
    java -jar "$APKSIGNER_JAR" verify --verbose "$OUT_APK"
fi

cp -f "$OUT_APK" "$SCRIPT_DIR/vemins_overlay_app.apk" 2>/dev/null || true

echo "================================================================================"
echo " [SUCCESS] VeminsESP APK successfully built with Native C++ Engine!"
echo " Artifact: $OUT_APK"
echo " Size: $(du -h "$OUT_APK" | cut -f1)"
echo "================================================================================"
