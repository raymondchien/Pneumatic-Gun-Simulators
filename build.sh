#!/bin/bash
# Build script for macOS and Linux executable builds using py-app-standalone

set -e  # Exit on error

echo "Building standalone executables for Pneumatic Gun Simulators..."
echo "Platform: $(uname -s)"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install it first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "Using uv version: $(uv --version)"
echo ""

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf py-standalone

# Build the standalone distribution from local package
echo "Building standalone Python environment from local package..."
uvx py-app-standalone . --source-only

# On macOS, create .app bundles
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "Creating macOS .app bundles..."

    # Find the Python installation directory
    PYTHON_DIR=$(find py-standalone -maxdepth 1 -name "cpython-*" -type d | head -1)

    if [ -z "$PYTHON_DIR" ]; then
        echo "Error: Could not find Python installation directory"
        exit 1
    fi

    # Function to convert PNG to ICNS
    png_to_icns() {
        local PNG_PATH="$1"
        local ICNS_PATH="$2"
        local ICONSET_PATH="${ICNS_PATH%.icns}.iconset"

        echo "Converting $PNG_PATH to $ICNS_PATH..."

        # Create iconset directory
        mkdir -p "$ICONSET_PATH"

        # Generate icons at various sizes
        sips -z 16 16     "$PNG_PATH" --out "$ICONSET_PATH/icon_16x16.png" > /dev/null 2>&1
        sips -z 32 32     "$PNG_PATH" --out "$ICONSET_PATH/icon_16x16@2x.png" > /dev/null 2>&1
        sips -z 32 32     "$PNG_PATH" --out "$ICONSET_PATH/icon_32x32.png" > /dev/null 2>&1
        sips -z 64 64     "$PNG_PATH" --out "$ICONSET_PATH/icon_32x32@2x.png" > /dev/null 2>&1
        sips -z 128 128   "$PNG_PATH" --out "$ICONSET_PATH/icon_128x128.png" > /dev/null 2>&1
        sips -z 256 256   "$PNG_PATH" --out "$ICONSET_PATH/icon_128x128@2x.png" > /dev/null 2>&1
        sips -z 256 256   "$PNG_PATH" --out "$ICONSET_PATH/icon_256x256.png" > /dev/null 2>&1
        sips -z 512 512   "$PNG_PATH" --out "$ICONSET_PATH/icon_256x256@2x.png" > /dev/null 2>&1
        sips -z 512 512   "$PNG_PATH" --out "$ICONSET_PATH/icon_512x512.png" > /dev/null 2>&1
        sips -z 1024 1024 "$PNG_PATH" --out "$ICONSET_PATH/icon_512x512@2x.png" > /dev/null 2>&1

        # Convert iconset to icns
        iconutil -c icns "$ICONSET_PATH" -o "$ICNS_PATH"

        # Clean up iconset directory
        rm -rf "$ICONSET_PATH"

        echo "Created $ICNS_PATH"
    }

    # Function to create .app bundle
    create_app_bundle() {
        local APP_NAME="$1"
        local EXECUTABLE_NAME="$2"
        local BUNDLE_ID="$3"
        local ICON_PNG="$4"  # Optional icon path

        echo "Creating $APP_NAME.app..."

        # Create .app structure
        mkdir -p "dist/$APP_NAME.app/Contents/MacOS"
        mkdir -p "dist/$APP_NAME.app/Contents/Resources"

        # Copy the entire py-standalone directory into Resources
        cp -R py-standalone "dist/$APP_NAME.app/Contents/Resources/"

        # Handle icon if provided
        local ICON_FILE=""
        if [ -n "$ICON_PNG" ] && [ -f "$ICON_PNG" ]; then
            ICON_FILE="AppIcon.icns"
            png_to_icns "$ICON_PNG" "dist/$APP_NAME.app/Contents/Resources/$ICON_FILE"
        fi

        # Create launcher script
        cat > "dist/$APP_NAME.app/Contents/MacOS/$APP_NAME" << 'EOF'
#!/bin/bash
# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Run the actual Python executable
exec "$DIR/../Resources/py-standalone/cpython-"*"/bin/EXEC_NAME" "$@"
EOF
        # Replace EXEC_NAME with actual executable name
        sed -i '' "s/EXEC_NAME/$EXECUTABLE_NAME/g" "dist/$APP_NAME.app/Contents/MacOS/$APP_NAME"
        chmod +x "dist/$APP_NAME.app/Contents/MacOS/$APP_NAME"

        # Create Info.plist
        cat > "dist/$APP_NAME.app/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
EOF
        # Add icon file reference if icon was provided
        if [ -n "$ICON_FILE" ]; then
            cat >> "dist/$APP_NAME.app/Contents/Info.plist" << EOF
    <key>CFBundleIconFile</key>
    <string>$ICON_FILE</string>
EOF
        fi
        cat >> "dist/$APP_NAME.app/Contents/Info.plist" << EOF
</dict>
</plist>
EOF
    }

    # Create dist directory
    mkdir -p dist

    # Create both .app bundles with icons
    create_app_bundle "Spring Piston Simulator" "spring-piston-simulator" "com.pneumaticgunsimulators.springpiston" "icons/spring-piston-icon.png"
    create_app_bundle "Nomad Simulator" "nomad-simulator" "com.pneumaticgunsimulators.nomad" "icons/nomad-icon.png"

    echo ""
    echo "macOS .app bundles created in dist/"
fi

echo ""
echo "Build complete!"
echo ""

if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS .app bundles are located in:"
    echo "  ./dist/"
    echo ""
    echo "Available applications:"
    ls -d dist/*.app
    echo ""
    echo "Double-click the .app files to launch, or run:"
    echo "  open 'dist/Spring Piston Simulator.app'"
    echo "  open 'dist/Nomad Simulator.app'"
else
    echo "The standalone executables are located in:"
    echo "  ./py-standalone/cpython-*/bin/"
    echo ""
    echo "Available executables:"
    find py-standalone -name "nomad-simulator" -o -name "spring-piston-simulator"
    echo ""
    echo "You can move the entire py-standalone directory to any compatible system."
fi

