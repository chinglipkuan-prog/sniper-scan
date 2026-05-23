#!/bin/bash
set -e

echo "=== Building SniperScan APK (targetSdk=33) ==="

BUILD_DIR="/tmp/apkbuild"
OUTPUT_DIR="/root/stockapp"
PKG="com.sniper.scan"
ANDROID_JAR="/usr/lib/android-sdk/platforms/android-33/android.jar"
BUILD_TOOLS="/usr/lib/android-sdk/build-tools/34.0.0"

# Clean previous build artifacts
rm -rf "$BUILD_DIR/obj" "$BUILD_DIR/gen" "$BUILD_DIR/dex" "$BUILD_DIR/build"
mkdir -p "$BUILD_DIR/obj" "$BUILD_DIR/gen" "$BUILD_DIR/build"

# Step 1: Generate R.java
echo ">>> [1/6] Generating R.java with aapt2..."
cd "$BUILD_DIR"
aapt2 compile --dir res -o build/res.zip 2>&1

# Step 2: Link resources and generate R.java
echo ">>> [2/6] Linking resources..."
aapt2 link -o build/unsigned.apk \
  --manifest AndroidManifest.xml \
  -I "$ANDROID_JAR" \
  --java gen \
  build/res.zip 2>&1

# Step 3: Compile Java source
echo ">>> [3/6] Compiling Java source..."
javac -d obj \
  -classpath "$ANDROID_JAR" \
  -sourcepath src \
  --release 8 \
  src/com/sniper/scan/MainActivity.java gen/com/sniper/scan/R.java 2>&1

# Step 4: Convert to DEX
echo ">>> [4/6] Converting to DEX with d8..."
cd "$BUILD_DIR"
mkdir -p dex
"$BUILD_TOOLS/d8" --release \
  --lib "$ANDROID_JAR" \
  --output dex \
  $(find obj -name "*.class") 2>&1

# Step 5: Add DEX to APK
echo ">>> [5/6] Adding DEX to APK..."
cd "$BUILD_DIR"
aapt2 add build/unsigned.apk classes.dex 2>&1 || {
  # If classes.dex is in dex/ subdir
  cp dex/classes.dex .
  aapt2 add build/unsigned.apk classes.dex 2>&1
}

# If aapt2 add doesn't work, use zip
if [ ! -f build/unsigned.apk ]; then
  echo "Using zip to add DEX..."
  cd "$BUILD_DIR"
  cp build/unsigned.apk . 2>/dev/null || true
  mkdir -p build/tmp
  cd build/tmp
  unzip -o ../res.zip 2>/dev/null
  cp "$BUILD_DIR/dex/classes.dex" .
  # Rewrite manifest from source
  cp "$BUILD_DIR/AndroidManifest.xml" .
  zip -r ../unsigned.apk . -x "*.DS_Store" 2>&1
fi

echo ">>> [6/6] Signing the APK..."

# Generate keystore if needed
if [ ! -f "$BUILD_DIR/keystore.jks" ]; then
  echo "Creating keystore..."
  keytool -genkey -v -keystore "$BUILD_DIR/keystore.jks" \
    -alias sniper -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass sniper123 -keypass sniper123 \
    -dname "CN=SniperScan, OU=Dev, O=Sniper, L=City, ST=State, C=US" 2>&1
fi

# Sign
apksigner sign --ks "$BUILD_DIR/keystore.jks" \
  --ks-pass pass:sniper123 \
  --key-pass pass:sniper123 \
  --ks-key-alias sniper \
  --out "$OUTPUT_DIR/SniperScan-v2.0.apk" \
  build/unsigned.apk 2>&1

# Verify
echo "=== Verification ==="
aapt dump badging "$OUTPUT_DIR/SniperScan-v2.0.apk" 2>/dev/null | head -10
apksigner verify --verbose "$OUTPUT_DIR/SniperScan-v2.0.apk" 2>&1 | tail -5

echo ""
echo "✅ DONE! APK: $OUTPUT_DIR/SniperScan-v2.0.apk"
ls -lh "$OUTPUT_DIR/SniperScan-v2.0.apk"
