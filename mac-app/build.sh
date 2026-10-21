#!/bin/bash
set -e

SRC_DIR="/Users/admin/samsung-tv-controller/mac-app"
FRONTEND_DIR="/Users/admin/samsung-tv-controller/frontend"
ICON_PATH="/Users/admin/samsung-tv-controller/AppIcon.icns"
APP_DIR="/Users/admin/Applications/Samsung TV Controller.app"

echo "🚀 Building native macOS application: Samsung TV Controller.app..."

# 1. Clean previous bundle
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources/web"

# 2. Compile native Swift Mach-O binary
echo "Compiling native Swift binary with Cocoa & WebKit..."
swiftc \
    "$SRC_DIR/SamsungClient.swift" \
    "$SRC_DIR/AppDelegate.swift" \
    "$SRC_DIR/main.swift" \
    -framework Cocoa \
    -framework WebKit \
    -framework Network \
    -O \
    -o "$APP_DIR/Contents/MacOS/Samsung TV Controller"

# 3. Copy Web UI assets into Resources/web
echo "Copying web resources..."
cp "$FRONTEND_DIR/index.html" "$APP_DIR/Contents/Resources/web/index.html"
cp "$FRONTEND_DIR/style.css"  "$APP_DIR/Contents/Resources/web/style.css"
cp "$FRONTEND_DIR/app.js"     "$APP_DIR/Contents/Resources/web/app.js"

# 4. Copy App Icon
if [ -f "$ICON_PATH" ]; then
    cp "$ICON_PATH" "$APP_DIR/Contents/Resources/AppIcon.icns"
fi

# 5. Write Info.plist
cat << 'EOF' > "$APP_DIR/Contents/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>Samsung TV Controller</string>
    <key>CFBundleExecutable</key>
    <string>Samsung TV Controller</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.antigravity.samsung-tv-controller</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Samsung TV Controller</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0.0</string>
    <key>CFBundleVersion</key>
    <string>2</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
        <key>NSAllowsLocalNetworking</key>
        <true/>
    </dict>
</dict>
</plist>
EOF

chmod +x "$APP_DIR/Contents/MacOS/Samsung TV Controller"

echo "✅ Successfully built standalone native macOS application at:"
echo "   $APP_DIR"
file "$APP_DIR/Contents/MacOS/Samsung TV Controller"
