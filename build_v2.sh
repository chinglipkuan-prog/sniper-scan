#!/bin/bash
set -e

echo "=== Building SniperScan APK v2 (targetSdk=33, minSdk=21) ==="

BUILD_DIR="/tmp/apkbuild"
OUTPUT_DIR="/root/stockapp"
ANDROID_JAR="/usr/lib/android-sdk/platforms/android-33/android.jar"
BUILD_TOOLS="/usr/lib/android-sdk/build-tools/30.0.3"

# Clean
rm -rf "$BUILD_DIR/obj" "$BUILD_DIR/gen" "$BUILD_DIR/dex" "$BUILD_DIR/build"
mkdir -p "$BUILD_DIR/obj" "$BUILD_DIR/gen" "$BUILD_DIR/build" "$BUILD_DIR/dex"

# Step 1: Compile resources
echo ">>> [1/6] Compiling resources..."
cd "$BUILD_DIR"
aapt2 compile --dir res -o build/res.zip 2>&1

# Step 2: Link resources
echo ">>> [2/6] Linking resources..."
aapt2 link -o build/unsigned.apk \
  --manifest AndroidManifest.xml \
  -I "$ANDROID_JAR" \
  --java gen \
  --min-sdk-version 21 \
  --target-sdk-version 33 \
  build/res.zip 2>&1

# Step 3: Compile Java
echo ">>> [3/6] Compiling Java source..."
javac -d obj \
  -classpath "$ANDROID_JAR" \
  -sourcepath src \
  --release 8 \
  src/com/sniper/scan/MainActivity.java gen/com/sniper/scan/R.java 2>&1

# Step 4: Convert to DEX using dx (more compatible)
echo ">>> [4/6] Converting to DEX..."
cd "$BUILD_DIR"
"$BUILD_TOOLS/dx" --dex --output=dex/classes.dex \
  obj 2>&1

# Step 5: Add DEX to APK
echo ">>> [5/6] Packaging APK..."
cp dex/classes.dex "$BUILD_DIR/"
cd "$BUILD_DIR"
zip -u build/unsigned.apk classes.dex 2>&1

# Step 6: Sign
echo ">>> [6/6] Signing..."
if [ ! -f "$BUILD_DIR/keystore.jks" ]; then
  keytool -genkey -v -keystore "$BUILD_DIR/keystore.jks" \
    -alias sniper -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass sniper123 -keypass sniper123 \
    -dname "CN=SniperScan, OU=Dev, O=Sniper, L=City, ST=State, C=US" 2>&1
fi

apksigner sign --ks "$BUILD_DIR/keystore.jks" \
  --ks-pass pass:sniper123 \
  --key-pass pass:sniper123 \
  --ks-key-alias sniper \
  --out "$OUTPUT_DIR/SniperScan-v2.0.apk" \
  build/unsigned.apk 2>&1

# Verify
echo ""
echo "=== Verification ==="
aapt dump badging "$OUTPUT_DIR/SniperScan-v2.0.apk" 2>/dev/null | grep -E "package:|sdkVersion|targetSdkVersion|application-label"
echo ""
apksigner verify --verbose "$OUTPUT_DIR/SniperScan-v2.0.apk" 2>&1 | tail -3

echo ""
echo "✅ DONE! APK: $OUTPUT_DIR/SniperScan-v2.0.apk"
ls -lh "$OUTPUT_DIR/SniperScan-v2.0.apk"
