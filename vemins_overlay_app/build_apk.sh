#!/usr/bin/env bash
set -e

# ==============================================================================
# VeminsESP — Standalone CLI Build System
# Compiles Android Application using local SDK tools: AAPT2, D8, Kotlinc, apksigner
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo " [VEMINS ESP] Building Android Floating Overlay App (VeminsESP)"
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
ANDROID_JAR="$SDK_DIR/platforms/android-36/android.jar"
if [ ! -f "$ANDROID_JAR" ]; then
    ANDROID_JAR=$(find "$SDK_DIR/platforms" -name "android.jar" | sort -V | tail -n 1)
fi
if [ -z "$ANDROID_JAR" ] || [ ! -f "$ANDROID_JAR" ]; then
    echo "[-] Error: android.jar not found in $SDK_DIR/platforms."
    exit 1
fi
echo "[+] Using Android Platform JAR: $ANDROID_JAR"

# 3. Locate Build Tools (AAPT2, D8, Zipalign, apksigner)
AAPT2_BIN="/data/data/com.termux/files/usr/bin/aapt2"
if [ ! -x "$AAPT2_BIN" ]; then
    AAPT2_BIN=$(which aapt2 2>/dev/null || find "$SDK_DIR/build-tools" -name "aapt2" | sort -V | tail -n 1)
fi

D8_JAR="$SDK_DIR/build-tools/35.0.0/lib/d8.jar"
if [ ! -f "$D8_JAR" ]; then
    D8_JAR=$(find "$SDK_DIR/build-tools" -name "d8.jar" | sort -V | tail -n 1)
fi

APKSIGNER_JAR="$SDK_DIR/build-tools/35.0.0/lib/apksigner.jar"
if [ ! -f "$APKSIGNER_JAR" ]; then
    APKSIGNER_JAR=$(find "$SDK_DIR/build-tools" -name "apksigner.jar" | sort -V | tail -n 1)
fi

ZIPALIGN_BIN=$(which zipalign 2>/dev/null || find "$SDK_DIR/build-tools" -name "zipalign" | sort -V | tail -n 1)

if [ -z "$AAPT2_BIN" ]; then
    echo "[-] Error: aapt2 not found."
    exit 1
fi
if [ -z "$D8_JAR" ]; then
    echo "[-] Error: d8.jar not found."
    exit 1
fi
if [ -z "$ZIPALIGN_BIN" ]; then
    echo "[-] Error: zipalign not found."
    exit 1
fi

echo "[+] AAPT2: $AAPT2_BIN"
echo "[+] D8: $D8_JAR"
echo "[+] Zipalign: $ZIPALIGN_BIN"
echo "[+] apksigner: $APKSIGNER_JAR"

# 4. Locate Kotlin Compiler & Standard Library
GRADLE_KOTLIN_DIR="/data/data/com.termux/files/home/.gradle/wrapper/dists/gradle-8.14.3-bin/cv11ve7ro1n3o1j4so8xd9n66/gradle-8.14.3/lib"
if [ ! -d "$GRADLE_KOTLIN_DIR" ]; then
    GRADLE_KOTLIN_DIR=$(find /data/data/com.termux/files/home/.gradle/ /root/.gradle/ -name "gradle-8.14.3" -type d 2>/dev/null | head -n 1)/lib
fi

KOTLIN_STDLIB_JAR=$(find "$GRADLE_KOTLIN_DIR" -name "kotlin-stdlib-2*.jar" 2>/dev/null | head -n 1)
if [ -z "$KOTLIN_STDLIB_JAR" ] || [ ! -f "$KOTLIN_STDLIB_JAR" ]; then
    KOTLIN_STDLIB_JAR=$(find /data/data/com.termux/files/home/.gradle/ /root/.gradle/ -name "kotlin-stdlib-2*.jar" 2>/dev/null | head -n 1)
fi
if [ -z "$KOTLIN_STDLIB_JAR" ] || [ ! -f "$KOTLIN_STDLIB_JAR" ]; then
    KOTLIN_STDLIB_JAR="/usr/share/java/kotlin-stdlib.jar"
fi

echo "[+] Kotlin Compiler Dir: $GRADLE_KOTLIN_DIR"
echo "[+] Kotlin StdLib: $KOTLIN_STDLIB_JAR"

# 5. Prepare Build Directories
BUILD_DIR="$SCRIPT_DIR/build"
GEN_DIR="$BUILD_DIR/gen"
CLASSES_DIR="$BUILD_DIR/classes"
R_CLASSES_DIR="$BUILD_DIR/r_classes"
DEX_DIR="$BUILD_DIR/dex"
OUT_APK="$SCRIPT_DIR/veminsEsp.apk"

rm -rf "$BUILD_DIR"
mkdir -p "$GEN_DIR" "$CLASSES_DIR" "$R_CLASSES_DIR" "$DEX_DIR"

# 6. Compile Resources with AAPT2
echo "[*] Step 1/6: Compiling Android resources with AAPT2..."
"$AAPT2_BIN" compile --dir app/src/main/res -o "$BUILD_DIR/compiled_res.zip"

ASSETS_ARG=""
if [ -d "app/src/main/assets" ]; then
    ASSETS_ARG="-A app/src/main/assets"
fi

echo "[*] Step 2/6: Linking resources & generating R.java..."
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
echo "[*] Step 3/6: Compiling R.java & Kotlin source files..."
R_JAVA_SRCS=$(find "$GEN_DIR" -name "*.java" 2>/dev/null || true)
if [ -n "$R_JAVA_SRCS" ]; then
    javac -cp "$ANDROID_JAR" -d "$R_CLASSES_DIR" $R_JAVA_SRCS
fi

JAVA_APP_SRCS=$(find app/src/main/java -name "*.java" 2>/dev/null || true)
if [ -n "$JAVA_APP_SRCS" ]; then
    javac -cp "$ANDROID_JAR:$R_CLASSES_DIR" -d "$CLASSES_DIR" $JAVA_APP_SRCS
fi

KOTLIN_SRCS=$(find app/src/main/java -name "*.kt")

if [ -d "$GRADLE_KOTLIN_DIR" ]; then
    java -cp "$GRADLE_KOTLIN_DIR/*" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler \
        -jvm-target 1.8 \
        -no-stdlib \
        -cp "$ANDROID_JAR:$R_CLASSES_DIR:$CLASSES_DIR:$KOTLIN_STDLIB_JAR" \
        -d "$CLASSES_DIR" \
        $KOTLIN_SRCS
elif which kotlinc >/dev/null 2>&1; then
    kotlinc -cp "$ANDROID_JAR:$R_CLASSES_DIR:$CLASSES_DIR:$KOTLIN_STDLIB_JAR" -d "$CLASSES_DIR" $KOTLIN_SRCS
else
    echo "[-] Error: No suitable Kotlin compiler found."
    exit 1
fi

# 8. Convert Class Files to Android Dalvik Executable (DEX)
echo "[*] Step 4/6: Dexing bytecode with D8 (min-api 21)..."
jar cf "$BUILD_DIR/app_classes.jar" -C "$CLASSES_DIR" . -C "$R_CLASSES_DIR" .
java -cp "$D8_JAR" com.android.tools.r8.D8 \
    --release \
    --min-api 21 \
    --lib "$ANDROID_JAR" \
    --output "$DEX_DIR" \
    "$BUILD_DIR/app_classes.jar" \
    "$KOTLIN_STDLIB_JAR"

# 9. Package DEX into APK & Zipalign
echo "[*] Step 5/6: Packaging DEX and aligning APK with 4-byte boundaries..."
(cd "$DEX_DIR" && zip -u -q "$BUILD_DIR/unaligned.apk" classes*.dex)
"$ZIPALIGN_BIN" -f -p 4 "$BUILD_DIR/unaligned.apk" "$BUILD_DIR/aligned.apk"

# 10. Generate Debug Keystore if missing & Sign APK
echo "[*] Step 6/6: Signing APK with apksigner (v1 + v2 + v3 schemes)..."
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

if [ -n "$APKSIGNER_JAR" ]; then
    java -jar "$APKSIGNER_JAR" sign \
        --ks "$KEYSTORE" \
        --ks-pass pass:android \
        --ks-key-alias androiddebugkey \
        --key-pass pass:android \
        --out "$OUT_APK" \
        "$BUILD_DIR/aligned.apk"

    echo "[*] Verifying APK Signature..."
    java -jar "$APKSIGNER_JAR" verify --verbose "$OUT_APK"
elif which apksigner >/dev/null 2>&1; then
    apksigner sign \
        --ks "$KEYSTORE" \
        --ks-pass pass:android \
        --ks-key-alias androiddebugkey \
        --key-pass pass:android \
        --out "$OUT_APK" \
        "$BUILD_DIR/aligned.apk"
    apksigner verify --verbose "$OUT_APK"
fi

# Also stage to vemins_overlay_app.apk for backwards compatibility
cp -f "$OUT_APK" "$SCRIPT_DIR/vemins_overlay_app.apk" 2>/dev/null || true

echo "================================================================================"
echo " [SUCCESS] VeminsESP APK successfully generated!"
echo " Artifact: $OUT_APK"
echo " Size: $(du -h "$OUT_APK" | cut -f1)"
echo "================================================================================"
