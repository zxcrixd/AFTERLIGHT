# Mobile scaffold

This folder packages AFTERLIGHT for touch devices.  The desktop game is
unchanged: the touch layer activates only when the game runs on Android/iOS
or when `AFTERLIGHT_MOBILE=1` is set.

## Touch controls

| Control | Action |
| --- | --- |
| `<` / `>` | Move left / right |
| `JUMP` | Jump |
| `ATK` | Attack |
| `USE` | Gather, eat, place or interact |
| `INV` | Inventory and crafting |
| `II` | Pause |

The overlay screens still use normal tap/mouse events, so inventory slots,
crafting rows and pause buttons work with a finger.

Preview the layout on a desktop:

```bash
AFTERLIGHT_MOBILE=1 python main.py
```

## Android (Buildozer / python-for-android)

Requirements: Linux, Python 3, Java 17, and the usual Buildozer toolchain.
The first build downloads the Android SDK/NDK and can take a while.

```bash
python -m venv .venv-mobile
source .venv-mobile/bin/activate
pip install buildozer cython
cd mobile
./prepare_android.sh
buildozer -v android debug
```

If the host has no compilers or Android SDK, the same build runs in the
official Buildozer container.  The wrapper stages the SDK/NDK, pins
build-tools to a version compatible with the Gradle/AGP pair shipped by
python-for-android, and builds a debug APK:

```bash
./mobile/build_android.sh
```

The container needs a lot of small-file I/O.  If the project lives on a slow
USB drive, keep the caches in RAM and only reuse the already-pulled image:

```bash
ANDROID_BUILD_ROOT=/tmp/opencode/android-build \
ANDROID_CACHE_ROOT=/dev/shm/afterlight-android/.buildozer \
ANDROID_LOCAL_BUILD=/tmp/opencode/android-build/local-build \
ANDROID_PODMAN_ROOT="$PWD/../android-build" \
    ./mobile/build_android.sh
```

The APK is written to `mobile/bin/`.  Install it with:

```bash
adb install -r bin/afterlight-0.2.0-arm64-v8a-debug.apk
```

Notes:

- `buildozer.spec` uses the `pygame` recipe and pins python-for-android to
  `v2023.09.16`.  That release builds CPython 3.10 + pygame 2.1.0; newer p4a
  releases use Python 3.14, which pygame 2.1.0 cannot compile against.
  Use `pygame-ce` only if your python-for-android version ships that recipe.
- `build_android.sh` installs `platforms;android-33` and `build-tools;33.0.2`
  and sets `android.skip_update = True`.  Without the pin, Buildozer upgrades
  to the newest build-tools (for example 37.0.0), which the pinned Gradle
  7.4.1 / AGP 7.1.2 pair may reject.
- `prepare_android.sh` copies `game/`, `assets/`, `mods/`, `settings.py` and
  the mobile entry point into `mobile/app/`.  Buildozer only sees that folder.
- On Android the game renders at the desktop logical resolution (1280x720)
  with `pygame.SCALED`, so the UI layout is identical and rendering is fast
  on high-DPI phones.
- Saves and settings go to the app's private data directory
  (`AFTERLIGHT_DATA_DIR`, default `$ANDROID_PRIVATE/afterlight` on Android).
- To ship a mod, put it in `mods/` before running `prepare_android.sh`, or
  place it in the app's `afterlight/mods` folder on the device.

## iOS

There is no official pygame-ce Buildozer target for iOS.  The touch layer and
`mobile/main.py` are platform-agnostic; an iOS port needs an SDL2/Xcode
project that embeds CPython and pygame-ce, then starts `mobile/main.py`.
Keep the same `AFTERLIGHT_MOBILE=1` flag and the touch controls will appear.

## Desktop packaging

See the main [`README.md`](../README.md) for the AppImage build.
