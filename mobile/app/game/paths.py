"""Filesystem helpers that work from source and inside a frozen AppImage.

Bundled read-only content (assets, example mods) lives next to the game or
inside PyInstaller's ``_MEIPASS`` folder.  Player data (saves, settings and
installed mods) must be writable, so frozen builds store it in the user's
XDG data directory instead of the read-only AppImage mount.
"""

import os
import sys
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent.parent
RESOURCE_FOLDER = Path(getattr(sys, "_MEIPASS", PROJECT_FOLDER))


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def is_android():
    """True on Android, where python-for-android sets ANDROID_ARGUMENT."""

    return sys.platform == "android" or "ANDROID_ARGUMENT" in os.environ


def resource_path(*parts):
    """Return a path to bundled, read-only content."""

    return RESOURCE_FOLDER.joinpath(*parts)


def data_folder():
    """Return the writable folder for saves, settings and user mods."""

    override = os.environ.get("AFTERLIGHT_DATA_DIR")

    if override:
        folder = Path(override).expanduser()
    elif is_frozen():
        xdg_data = os.environ.get("XDG_DATA_HOME")

        if xdg_data:
            base = Path(xdg_data).expanduser()
        else:
            base = Path.home() / ".local" / "share"

        folder = base / "afterlight"
    else:
        folder = PROJECT_FOLDER / "saves"

    folder.mkdir(parents=True, exist_ok=True)
    return folder


def data_path(*parts):
    return data_folder().joinpath(*parts)


def mods_folders():
    """Return every folder that may contain mods, in load order."""

    folders = []

    if is_frozen():
        # Example mods shipped inside the AppImage.
        folders.append(resource_path("mods"))

        # Mods installed by the player (created on first launch).
        user_mods = data_folder() / "mods"
        user_mods.mkdir(parents=True, exist_ok=True)
        folders.append(user_mods)
    else:
        folders.append(PROJECT_FOLDER / "mods")

        # Android/iOS builds run from a normal folder rather than a
        # PyInstaller bundle, but still keep player mods in writable storage.
        if is_android() or sys.platform == "ios":
            user_mods = data_folder() / "mods"
            user_mods.mkdir(parents=True, exist_ok=True)
            folders.append(user_mods)

    return folders
