#!/usr/bin/env bash
# Build AFTERLIGHT into a single-file x86_64 AppImage.
#
# Usage:
#   ./build_appimage.sh
#
# Environment overrides:
#   PYTHON=/path/to/python       Python that has pygame-ce + PyInstaller
#   APPIMAGE_NAME=...            Output file name
#   SKIP_DOWNLOAD=1              Fail instead of downloading appimagetool

set -euo pipefail

cd "$(dirname "$0")"
ROOT="$PWD"

PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
PYINSTALLER="${PYINSTALLER:-$ROOT/.venv/bin/pyinstaller}"

BUILD_DIR="$ROOT/build"
DIST_DIR="$ROOT/dist"
TOOLS_DIR="$BUILD_DIR/tools"
APPDIR="$BUILD_DIR/AFTERLIGHT.AppDir"
APPIMAGE="${APPIMAGE_NAME:-$ROOT/AFTERLIGHT-x86_64.AppImage}"

if [ ! -x "$PYTHON" ]; then
    echo "Python not found: $PYTHON" >&2
    echo "Set PYTHON=/path/to/python or create .venv first." >&2
    exit 1
fi

if [ ! -x "$PYINSTALLER" ]; then
    echo "PyInstaller not found: $PYINSTALLER" >&2
    echo "Install it with: $PYTHON -m pip install pyinstaller" >&2
    exit 1
fi

echo "==> Generating icon"
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
    "$PYTHON" "$BUILD_DIR/make_icon.py" "$BUILD_DIR/afterlight.png"

echo "==> Running PyInstaller"
rm -rf "$DIST_DIR" "$BUILD_DIR/pyinstaller" "$APPDIR"

"$PYINSTALLER" \
    --noconfirm \
    --clean \
    --windowed \
    --name AFTERLIGHT \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR/pyinstaller" \
    --specpath "$BUILD_DIR" \
    --add-data "$ROOT/assets:assets" \
    --add-data "$ROOT/mods:mods" \
    --collect-data pygame \
    "$ROOT/main.py"

echo "==> Assembling AppDir"
mkdir -p \
    "$APPDIR/usr/bin" \
    "$APPDIR/usr/share/applications" \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cp -a "$DIST_DIR/AFTERLIGHT/." "$APPDIR/usr/bin/"
cp "$BUILD_DIR/afterlight.desktop" "$APPDIR/afterlight.desktop"
cp "$BUILD_DIR/afterlight.desktop" "$APPDIR/usr/share/applications/afterlight.desktop"
cp "$BUILD_DIR/afterlight.png" "$APPDIR/afterlight.png"
cp "$BUILD_DIR/afterlight.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/afterlight.png"
cp "$BUILD_DIR/AppRun" "$APPDIR/AppRun"

chmod +x "$APPDIR/AppRun" "$APPDIR/usr/bin/AFTERLIGHT"

echo "==> Fetching appimagetool"
TOOL="$TOOLS_DIR/appimagetool-x86_64.AppImage"
RUNTIME="$TOOLS_DIR/runtime-x86_64"

if [ ! -x "$TOOL" ]; then
    if [ "${SKIP_DOWNLOAD:-0}" = "1" ]; then
        echo "appimagetool is missing and SKIP_DOWNLOAD=1" >&2
        exit 1
    fi

    mkdir -p "$TOOLS_DIR"
    curl -L --fail --retry 3 \
        -o "$TOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$TOOL"
fi

# Newer appimagetool builds download the runtime themselves, which fails
# behind some proxies.  Fetch it explicitly and pass it to the tool.
if [ ! -f "$RUNTIME" ]; then
    if [ "${SKIP_DOWNLOAD:-0}" = "1" ]; then
        echo "AppImage runtime is missing and SKIP_DOWNLOAD=1" >&2
        exit 1
    fi

    mkdir -p "$TOOLS_DIR"
    curl -L --fail --retry 3 \
        -o "$RUNTIME" \
        "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64"
fi

echo "==> Packing AppImage"
rm -f "$APPIMAGE"

ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 \
    "$TOOL" --no-appstream --runtime-file "$RUNTIME" "$APPDIR" "$APPIMAGE"

chmod +x "$APPIMAGE"

echo
echo "Done: $APPIMAGE"
ls -lh "$APPIMAGE"
