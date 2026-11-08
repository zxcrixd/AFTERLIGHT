[app]
title = AFTERLIGHT
package.name = afterlight
package.domain = org.afterlight

# Filled by prepare_android.sh with the game, assets and bundled mods.
source.dir = app
source.include_exts = py,png,jpg,jpeg,ogg,wav,json,md,txt,ttf
source.exclude_dirs = __pycache__,saves

version = 0.2.0
requirements = python3,pygame

orientation = landscape
fullscreen = 1
icon.filename = %(source.dir)s/icon.png

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a

# build_android.sh installs build-tools 33.0.2 (matching AGP 7.1.2) and
# platform 33 before the build.  Without this, Buildozer upgrades to the
# newest build-tools, which can be incompatible with the pinned Gradle/AGP.
android.skip_update = True

# Pin python-for-android to the last release that builds the stock pygame
# recipe (2.1.0) with Python 3.10.  Newer p4a releases use Python 3.14, which
# pygame 2.1.0 cannot compile against.
p4a.branch = v2023.09.16
android.permissions = VIBRATE
android.apptheme = "@android:style/Theme.NoTitleBar.Fullscreen"
android.accept_sdk_license = True

[buildozer]
log_level = 2
# The container runs as root; its root maps to the host user via rootless
# podman, so files stay owned by the host user.
warn_on_root = 0
