"""Entry point used by the Android/iOS packaging scaffold.

When this file is copied into the mobile app folder it finds the bundled
``game`` package next to itself.  It can also be launched directly from
``mobile/`` during development, in which case it falls back to the repository
root.
"""

import os
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

for candidate in (HERE, ROOT):
    if (candidate / "game").is_dir():
        sys.path.insert(0, str(candidate))
        break

# Touch controls are always on for packaged mobile builds.  The same flag is
# useful for previewing the layout on a desktop.
os.environ.setdefault("AFTERLIGHT_MOBILE", "1")

# Keep saves/settings inside the app's private writable storage on Android.
# python-for-android identifies the platform with ANDROID_ARGUMENT rather than
# sys.platform, so check both.  ANDROID_PRIVATE points at the app's files
# directory; HOME is not guaranteed to be set (or writable) there.
if (
    sys.platform == "android" or "ANDROID_ARGUMENT" in os.environ
) and "AFTERLIGHT_DATA_DIR" not in os.environ:
    base = os.environ.get("ANDROID_PRIVATE") or os.environ.get("HOME")
    if not base:
        base = str(Path.home())
    os.environ["AFTERLIGHT_DATA_DIR"] = str(Path(base) / "afterlight")


from game.game import Game  # noqa: E402


if __name__ == "__main__":
    Game().run()
