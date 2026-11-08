#!/usr/bin/env bash
# Collect the files python-for-android needs into mobile/app.
#
# Buildozer cannot package files above its source.dir, so this script copies
# the game package, assets, bundled mods and the mobile entry point into a
# small self-contained folder before the APK build.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
APP="$HERE/app"

rm -rf "$APP"
mkdir -p "$APP"

cp "$ROOT/settings.py" "$APP/"
cp -a "$ROOT/game" "$APP/game"
cp -a "$ROOT/assets" "$APP/assets"
cp -a "$ROOT/mods" "$APP/mods"
cp "$HERE/main.py" "$APP/main.py"

# 512x512 launcher icon for Android.
if [ -x "$ROOT/.venv/bin/python" ]; then
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
        "$ROOT/.venv/bin/python" "$ROOT/build/make_icon.py" "$APP/icon.png" 512
elif [ -f "$ROOT/build/afterlight.png" ]; then
    cp "$ROOT/build/afterlight.png" "$APP/icon.png"
fi

find "$APP" -type d -name __pycache__ -prune -exec rm -rf {} +

echo "Prepared mobile app folder: $APP"
du -sh "$APP"
