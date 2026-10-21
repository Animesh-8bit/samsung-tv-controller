#!/bin/bash
set -e

APP_NAME="Samsung TV Controller"
APP_DIR="${HOME}/Applications/${APP_NAME}.app"
CONTROLLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔨 Installing Chrome App version: ${APP_NAME}.app..."
rm -rf "${APP_DIR}"
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"

# Copy Icon
if [ -f "${CONTROLLER_DIR}/AppIcon.icns" ]; then
    cp "${CONTROLLER_DIR}/AppIcon.icns" "${APP_DIR}/Contents/Resources/AppIcon.icns"
fi

# Create Info.plist
cat << 'PLIST' > "${APP_DIR}/Contents/Info.plist"
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
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

# Create Launcher Executable
cat << LAUNCHER > "${APP_DIR}/Contents/MacOS/Samsung TV Controller"
#!/bin/bash
DIR="${CONTROLLER_DIR}"
PORT=5588

# Check if server is already running
if ! lsof -ti :\$PORT >/dev/null 2>&1; then
    nohup "\$DIR/.venv/bin/python3" -m uvicorn backend.server:app \\
        --app-dir "\$DIR" \\
        --host 127.0.0.1 \\
        --port \$PORT \\
        > "\$DIR/server.log" 2>&1 &
    
    # Wait for server to become ready
    for i in {1..20}; do
        if curl -s "http://127.0.0.1:\$PORT/api/status" >/dev/null 2>&1; then
            break
        fi
        sleep 0.15
    done
fi

# Launch standalone Chrome app window
if [ -d "/Applications/Google Chrome.app" ]; then
    open -na "Google Chrome" --args --app="http://127.0.0.1:\$PORT" --window-size=380,820
else
    open "http://127.0.0.1:\$PORT"
fi
LAUNCHER

chmod +x "${APP_DIR}/Contents/MacOS/Samsung TV Controller"

echo "✅ Installed ${APP_NAME}.app to ${HOME}/Applications"
