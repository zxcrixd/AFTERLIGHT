#!/usr/bin/env bash
# Build an Android debug APK with Buildozer inside a podman container.
#
# The host has no Android SDK/NDK and no C toolchain, so the official
# kivy/buildozer image provides them.  Toolchain caches live next to the
# project (or under $ANDROID_BUILD_ROOT) so they survive container rebuilds
# and do not fill the small root filesystem.
#
# Usage:
#   ./mobile/build_android.sh [buildozer args...]
#
# Default command: buildozer -v android debug
#
# Layout overrides (useful when the project drive is slow):
#   ANDROID_BUILD_ROOT   base folder for temporary/build state
#   ANDROID_CACHE_ROOT   global Buildozer cache (SDK/NDK/python-for-android)
#   ANDROID_LOCAL_BUILD  local Buildozer build tree (p4a dist + Gradle project)
#   ANDROID_PODMAN_ROOT  podman graphroot (reuse a pre-pulled image here)
#
# Example: keep the heavy build on tmpfs but reuse the image on disk:
#   ANDROID_BUILD_ROOT=/tmp/opencode/android-build \
#   ANDROID_PODMAN_ROOT=/path/to/android-build \
#       ./mobile/build_android.sh

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"

DEFAULT_BUILD_ROOT="$(cd "$ROOT/../.." && pwd)/android-build"
BUILD_ROOT="${ANDROID_BUILD_ROOT:-$DEFAULT_BUILD_ROOT}"
CACHE_ROOT="${ANDROID_CACHE_ROOT:-$BUILD_ROOT/.buildozer}"
LOCAL_BUILD="${ANDROID_LOCAL_BUILD:-$BUILD_ROOT/local-build}"
PODMAN_ROOT="${ANDROID_PODMAN_ROOT:-$BUILD_ROOT}"
IMAGE="${BUILDOZER_IMAGE:-docker.io/kivy/buildozer:latest}"

SDK_VERSION="33"
BUILD_TOOLS_VERSION="33.0.2"
NDK_VERSION="25b"
SDK_PLATFORM="$CACHE_ROOT/android/platform"
SDK_DIR="$SDK_PLATFORM/android-sdk"
NDK_DIR="$SDK_PLATFORM/android-ndk-r$NDK_VERSION"
DOWNLOADS="$CACHE_ROOT/downloads"

mkdir -p \
    "$BUILD_ROOT/podman-runroot" \
    "$BUILD_ROOT/tmp" \
    "$BUILD_ROOT/container-tmp" \
    "$BUILD_ROOT/.android" \
    "$BUILD_ROOT/.gradle" \
    "$BUILD_ROOT/.cache" \
    "$BUILD_ROOT/cmake-shim" \
    "$CACHE_ROOT" \
    "$LOCAL_BUILD" \
    "$PODMAN_ROOT/podman-storage" \
    "$DOWNLOADS"
chmod 1777 "$BUILD_ROOT/container-tmp"

# CMake 4 removed compatibility with projects that declare
# cmake_minimum_required(VERSION < 3.5).  Several libraries bundled by
# python-for-android (libjpeg-turbo, libpng, ...) still do, so a configure
# call fails with "Compatibility with CMake < 3.5 has been removed".
# This shim injects the documented escape hatch for configure calls only.
cat > "$BUILD_ROOT/cmake-shim/cmake" <<'EOF'
#!/bin/sh
case "${1:-}" in
    --build|--install|--version|--help|--system-information|-E|-P)
        exec /usr/bin/cmake "$@"
        ;;
esac
exec /usr/bin/cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "$@"
EOF
chmod +x "$BUILD_ROOT/cmake-shim/cmake"

# Rootless podman storage.  By default it lives in the build root; point
# ANDROID_PODMAN_ROOT at an existing graphroot to avoid re-pulling the image.
STORAGE_CONF="$BUILD_ROOT/storage.conf"
cat > "$STORAGE_CONF" <<EOF
[storage]
driver = "overlay"
graphroot = "$PODMAN_ROOT/podman-storage"
runroot = "$BUILD_ROOT/podman-runroot"

[storage.options]
mount_program = "/usr/bin/fuse-overlayfs"
EOF

export CONTAINERS_STORAGE_CONF="$STORAGE_CONF"
export TMPDIR="$BUILD_ROOT/tmp"

# curl wrapper: the host's socks ALL_PROXY breaks downloads.
FETCH_ENV=(env -u ALL_PROXY -u all_proxy)
if [ -n "${HTTP_PROXY:-}" ]; then
    FETCH_ENV+=("HTTP_PROXY=$HTTP_PROXY" "HTTPS_PROXY=$HTTP_PROXY")
fi

fetch() {
    local url="$1" out="$2"
    if [ -s "$out" ]; then
        return 0
    fi
    echo "Downloading $url"
    "${FETCH_ENV[@]}" curl -fL --retry 3 --retry-delay 2 -o "$out" "$url"
}

# ---------------------------------------------------------------------------
# Stage the SDK and NDK on the host.
#
# Buildozer 1.6 always upgrades to the newest build-tools, which can be newer
# than the Gradle/AGP pair shipped by python-for-android 2023.09.16.  We pin
# build-tools 33.0.2, install it ourselves, and set android.skip_update in the
# spec so Buildozer keeps it.  The SDK root must contain tools/bin/sdkmanager
# because Buildozer still calls it to list build-tools.
# ---------------------------------------------------------------------------
stage_sdk() {
    if [ ! -x "$SDK_DIR/tools/bin/sdkmanager" ]; then
        local zip="$DOWNLOADS/commandlinetools-linux.zip"
        fetch "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" "$zip"

        local tmp="$SDK_DIR/.cmdline-tools.tmp"
        rm -rf "$tmp" "$SDK_DIR/cmdline-tools"
        mkdir -p "$tmp"
        unzip -q "$zip" -d "$tmp"
        mkdir -p "$SDK_DIR/cmdline-tools"
        mv "$tmp/cmdline-tools" "$SDK_DIR/cmdline-tools/latest"
        rm -rf "$tmp" "$zip"
        ln -sfn "cmdline-tools/latest" "$SDK_DIR/tools"
    fi

    if [ ! -f "$SDK_DIR/platforms/android-$SDK_VERSION/android.jar" ] \
        || [ ! -x "$SDK_DIR/build-tools/$BUILD_TOOLS_VERSION/aidl" ]; then
        local sdk_env=(env -u ALL_PROXY -u all_proxy)
        if [ -n "${HTTP_PROXY:-}" ]; then
            sdk_env+=("HTTP_PROXY=$HTTP_PROXY" "HTTPS_PROXY=$HTTP_PROXY")
        fi

        yes | "${sdk_env[@]}" "$SDK_DIR/tools/bin/sdkmanager" \
            --sdk_root="$SDK_DIR" --licenses >/dev/null 2>&1 || true

        "${sdk_env[@]}" "$SDK_DIR/tools/bin/sdkmanager" \
            --sdk_root="$SDK_DIR" \
            "platform-tools" \
            "platforms;android-$SDK_VERSION" \
            "build-tools;$BUILD_TOOLS_VERSION"
    fi
}

stage_ndk() {
    if [ -f "$NDK_DIR/source.properties" ]; then
        return 0
    fi

    local zip="$DOWNLOADS/android-ndk-r$NDK_VERSION-linux.zip"
    fetch "https://dl.google.com/android/repository/android-ndk-r$NDK_VERSION-linux.zip" "$zip"

    rm -rf "$NDK_DIR"
    unzip -q "$zip" -d "$SDK_PLATFORM"
    rm -f "$zip"
}

echo "Staging Android SDK in $SDK_DIR"
stage_sdk
echo "Staging Android NDK in $NDK_DIR"
stage_ndk

# Collect the app files Buildozer packages.
"$HERE/prepare_android.sh"

if [ "$#" -gt 0 ]; then
    CMD=("$@")
else
    CMD=(-v android debug)
fi

PROXY_ARGS=()
if [ -n "${HTTP_PROXY:-}" ]; then
    PROXY_ARGS+=(
        -e "HTTP_PROXY=$HTTP_PROXY"
        -e "HTTPS_PROXY=$HTTP_PROXY"
        -e "http_proxy=$HTTP_PROXY"
        -e "https_proxy=$HTTP_PROXY"
        -e "NO_PROXY=${NO_PROXY:-localhost,127.0.0.1}"
        -e "no_proxy=${NO_PROXY:-localhost,127.0.0.1}"
    )
fi

# ALL_PROXY (socks) breaks pip/git/sdkmanager in the container; drop it.
# The container's root maps to the host user through rootless podman, so the
# bind-mounted caches stay writable and files remain owned by the host user.
# We bypass the image entrypoint: it recursively chowns all of /home/user on
# every start, which is very slow once the SDK/NDK caches are populated.
exec env -u ALL_PROXY -u all_proxy \
    podman run --rm \
        --pull=never \
        --network=host \
        --ipc=host \
        --security-opt label=disable \
        -e HOME=/home/user \
        -e VIRTUAL_ENV=/home/user/.venv \
        -e CMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -e PATH=/home/user/cmake-shim:/home/user/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        -e GRADLE_USER_HOME=/home/user/.gradle \
        -e PIP_NO_CACHE_DIR=1 \
        -e TMPDIR=/tmp \
        -v "$HERE:/home/user/hostcwd" \
        -v "$LOCAL_BUILD:/home/user/hostcwd/.buildozer" \
        -v "$CACHE_ROOT:/home/user/.buildozer" \
        -v "$BUILD_ROOT/cmake-shim:/home/user/cmake-shim:ro" \
        -v "$BUILD_ROOT/.android:/home/user/.android" \
        -v "$BUILD_ROOT/.gradle:/home/user/.gradle" \
        -v "$BUILD_ROOT/.cache:/home/user/.cache" \
        -v "$BUILD_ROOT/container-tmp:/tmp" \
        "${PROXY_ARGS[@]}" \
        --entrypoint /bin/bash \
        "$IMAGE" -lc '
            set -e
            PY=/home/user/.venv/bin/python
            # python-for-android v2023.09.16 needs distutils (setuptools
            # provides it on modern Python) plus its runtime dependencies.
            # Install them into the venv: the venv disables user
            # site-packages, so the Buildozer default "--user" install would
            # be invisible to it.
            if ! "$PY" -c "import setuptools, appdirs, jinja2, sh, toml, build" >/dev/null 2>&1; then
                "$PY" -m pip install --quiet \
                    setuptools appdirs "colorama>=0.3.3" jinja2 \
                    "sh>=1.10,<2.0" build toml packaging
            fi
            cd /home/user/hostcwd
            exec /home/user/.venv/bin/buildozer "$@"
        ' bash "${CMD[@]}"
