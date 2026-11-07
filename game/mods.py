"""Python mod loader and the public modding API for AFTERLIGHT.

A mod is either a folder containing ``mod.py`` (and an optional
``mod.json``) or a single ``.py`` file inside the ``mods/`` directory.
Each mod must define ``setup(api)``.  See ``mods/README.md`` for the full
API reference and an example.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import traceback
from pathlib import Path

from game.crafting import RECIPES, Recipe
from game.items import (
    ITEMS,
    ItemDef,
    clear_icon_cache,
    register_item_icon,
)
from game.localization import STRINGS
from game.paths import mods_folders as default_mods_folders
from game.resources import KIND_WEIGHTS, NODE_DATA


API_VERSION = 1


def _safe_id(value):
    """Turn arbitrary text into a safe content id."""

    text = str(value).strip().lower()
    cleaned = "".join(
        character
        if character.isascii() and (character.isalnum() or character in "_-")
        else "_"
        for character in text
    )
    return cleaned.strip("_")


def _load_metadata(path):
    """Read mod.json (when present) and build a metadata dictionary."""

    if path.is_dir():
        manifest_path = path / "mod.json"
        mod_file = path / "mod.py"
        default_id = path.name
    else:
        manifest_path = path.with_suffix(".json")
        mod_file = path
        default_id = path.stem

    metadata = {
        "id": _safe_id(default_id) or default_id,
        "name": default_id,
        "version": "0.0.0",
        "author": "",
        "description": "",
        "api_version": API_VERSION,
        "enabled": True,
        "path": path,
        "file": mod_file,
        "status": "pending",
        "error": "",
    }

    if manifest_path.exists():
        try:
            with manifest_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            metadata["error"] = f"mod.json: {error}"
            print(f"[mods] could not read {manifest_path}: {error}")
            data = None

        if isinstance(data, dict):
            for key in (
                "id",
                "name",
                "version",
                "author",
                "description",
                "api_version",
                "enabled",
            ):
                if key in data:
                    metadata[key] = data[key]

    metadata["id"] = _safe_id(metadata["id"]) or _safe_id(default_id) or "mod"
    metadata["enabled"] = bool(metadata.get("enabled", True))

    try:
        metadata["api_version"] = int(metadata.get("api_version", API_VERSION))
    except (TypeError, ValueError):
        metadata["api_version"] = API_VERSION

    return metadata


class ModAPI:
    """Object passed to every mod's ``setup(api)`` function."""

    def __init__(self, manager, mod_id):
        self._manager = manager
        self.mod_id = mod_id

    # -- convenience access ---------------------------------------------
    @property
    def game(self):
        return self._manager.game

    @property
    def items(self):
        return ITEMS

    @property
    def recipes(self):
        return RECIPES

    @property
    def strings(self):
        return STRINGS

    def log(self, *args):
        print(f"[mod:{self.mod_id}]", *args)

    def notify(self, text, color=None, duration=2.0):
        game = self.game

        if game is None:
            return

        game.notifications.add(
            str(text),
            color=color or (230, 230, 230),
            duration=float(duration),
        )

    def give(self, item_id, count=1):
        game = self.game

        if game is None:
            return int(count)

        return game.player.inventory.add(item_id, int(count))

    # -- content registration -------------------------------------------
    def register_item(
        self,
        item_id,
        name_ru,
        name_en,
        *,
        category="material",
        max_stack=99,
        damage=0.0,
        reach=0.0,
        heal=0.0,
        hunger=0.0,
        light=0.0,
        tool="",
        description_ru="",
        description_en="",
        icon=None,
        override=False,
    ):
        """Register a new item.

        ``icon`` can be a callable drawing on a 64x64 RGBA surface, a path
        to an image, or ``None`` for a generated placeholder.
        """

        item_id = _safe_id(item_id)

        if not item_id:
            raise ValueError("item id must not be empty")

        if item_id in ITEMS and not override:
            self.log(f"item '{item_id}' already exists; skipped")
            return ITEMS[item_id]

        item = ItemDef(
            id=item_id,
            name_ru=str(name_ru),
            name_en=str(name_en),
            category=str(category),
            max_stack=max(1, int(max_stack)),
            damage=float(damage),
            reach=float(reach),
            heal=float(heal),
            hunger=float(hunger),
            light=float(light),
            tool=str(tool),
            description_ru=str(description_ru),
            description_en=str(description_en),
        )

        ITEMS[item_id] = item

        if icon is not None:
            register_item_icon(item_id, icon)
        elif override:
            register_item_icon(item_id, None)

        clear_icon_cache(item_id)
        return item

    def register_item_icon(self, item_id, icon):
        """Add or replace an icon for an already registered item."""

        item_id = _safe_id(item_id)
        register_item_icon(item_id, icon)

    def register_recipe(
        self,
        recipe_id,
        result,
        amount,
        ingredients,
        name_ru,
        name_en,
        *,
        description_ru="",
        description_en="",
        override=False,
    ):
        """Register a crafting recipe."""

        recipe_id = _safe_id(recipe_id)
        result = _safe_id(result)

        if not recipe_id:
            raise ValueError("recipe id must not be empty")

        if not isinstance(ingredients, dict) or not ingredients:
            raise ValueError("ingredients must be a non-empty dict")

        clean_ingredients = {}

        for item_id, count in ingredients.items():
            clean_id = _safe_id(item_id)

            try:
                clean_count = int(count)
            except (TypeError, ValueError):
                raise ValueError(f"invalid ingredient count for '{item_id}'")

            if clean_id and clean_count > 0:
                clean_ingredients[clean_id] = clean_count

        if not clean_ingredients:
            raise ValueError("ingredients must contain at least one item")

        existing = next(
            (recipe for recipe in RECIPES if recipe.id == recipe_id),
            None,
        )

        if existing is not None:
            if not override:
                self.log(f"recipe '{recipe_id}' already exists; skipped")
                return existing

            RECIPES.remove(existing)

        recipe = Recipe(
            id=recipe_id,
            result=result,
            amount=max(1, int(amount)),
            ingredients=clean_ingredients,
            name_ru=str(name_ru),
            name_en=str(name_en),
            description_ru=str(description_ru),
            description_en=str(description_en),
        )

        RECIPES.append(recipe)

        if result not in ITEMS:
            self.log(f"recipe '{recipe_id}' result '{result}' is not registered yet")

        return recipe

    def register_resource(
        self,
        kind,
        name_ru,
        name_en,
        prompt_ru,
        prompt_en,
        *,
        hits=3,
        respawn=60.0,
        weight=0,
        height=60.0,
        interaction_height=None,
        drops=None,
        draw=None,
        draw_stump=None,
        color=(120, 130, 140),
        stump_color=(74, 78, 84),
        override=False,
    ):
        """Register a harvestable world resource.

        ``drops`` is called as ``drops(node, player, rng)`` and must return
        a list of ``(item_id, count)`` tuples.  ``draw`` is called as
        ``draw(surface, x, ground_y)``.  A positive ``weight`` makes the
        resource spawn naturally in generated chunks.
        """

        kind = _safe_id(kind)

        if not kind:
            raise ValueError("resource kind must not be empty")

        if kind in NODE_DATA and not override:
            self.log(f"resource '{kind}' already exists; skipped")
            return NODE_DATA[kind]

        data = {
            "name_ru": str(name_ru),
            "name_en": str(name_en),
            "prompt_ru": str(prompt_ru),
            "prompt_en": str(prompt_en),
            "hits": max(1, int(hits)),
            "respawn": max(0.0, float(respawn)),
            "height": float(height),
            "drops": drops,
            "draw": draw,
            "draw_stump": draw_stump,
            "color": tuple(color),
            "stump_color": tuple(stump_color),
        }

        if interaction_height is not None:
            data["interaction_height"] = float(interaction_height)

        NODE_DATA[kind] = data

        KIND_WEIGHTS[:] = [
            (existing_kind, existing_weight)
            for existing_kind, existing_weight in KIND_WEIGHTS
            if existing_kind != kind
        ]

        if float(weight) > 0:
            KIND_WEIGHTS.append((kind, float(weight)))

        return data

    def add_strings(self, language, mapping):
        """Add or override localization strings.

        ``language`` is ``"ru"`` or ``"en"``.  A dict of languages is also
        accepted: ``api.add_strings({"ru": {...}, "en": {...}})``.
        """

        if isinstance(language, dict):
            for language_code, language_mapping in language.items():
                self.add_strings(language_code, language_mapping)
            return

        if language not in STRINGS:
            raise ValueError(f"unknown language '{language}'")

        if not isinstance(mapping, dict):
            raise TypeError("mapping must be a dict")

        STRINGS[language].update(
            {str(key): str(value) for key, value in mapping.items()}
        )

    # -- events ----------------------------------------------------------
    def on(self, event, callback):
        """Subscribe a callback to an event.  Returns the callback."""

        return self._manager.add_hook(self.mod_id, event, callback)

    def off(self, event, callback):
        """Remove a previously registered callback."""

        self._manager.remove_hook(self.mod_id, event, callback)

    def on_key(self, expected_key, callback):
        """Convenience helper for handling one keyboard key."""

        def wrapper(game, key, **kwargs):
            if key == expected_key:
                return callback(game)

        return self.on("key", wrapper)

    # -- mod save data ---------------------------------------------------
    def set_save_data(self, key, value):
        """Store JSON-serializable data inside the game save file."""

        try:
            json.dumps(value)
        except (TypeError, ValueError) as error:
            raise TypeError(f"mod save data must be JSON serializable: {error}")

        bucket = self._manager.save_data.setdefault(self.mod_id, {})
        bucket[str(key)] = copy.deepcopy(value)

    def get_save_data(self, key, default=None):
        bucket = self._manager.save_data.get(self.mod_id, {})
        return copy.deepcopy(bucket.get(str(key), default))


class ModManager:
    """Discovers, loads and dispatches events for all installed mods."""

    def __init__(self, mods_folder=None):
        if mods_folder is None:
            self.mods_folders = default_mods_folders()
        else:
            self.mods_folders = [Path(mods_folder)]

        self.mods_folder = self.mods_folders[0] if self.mods_folders else None
        self.game = None
        self.mods = []
        self.hooks = {}
        self.save_data = {}
        self.errors = []
        self.loaded = False
        self._hook_failures = set()

    def attach(self, game):
        self.game = game

    # -- discovery / loading --------------------------------------------
    def discover(self):
        """Return metadata for every mod candidate found on disk.

        Mods are loaded from every configured folder, so a frozen AppImage
        can expose its bundled examples and the player's own mods at once.
        """

        found = []
        seen_paths = set()

        for folder in self.mods_folders:
            if not folder.exists():
                continue

            for entry in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
                if entry.name.startswith((".", "_", "__")):
                    continue

                resolved = entry.resolve()

                if resolved in seen_paths:
                    continue

                seen_paths.add(resolved)

                if entry.is_dir():
                    mod_file = entry / "mod.py"

                    if mod_file.exists():
                        found.append(_load_metadata(entry))
                elif entry.suffix.lower() == ".py":
                    found.append(_load_metadata(entry))

        return found

    def load_all(self):
        """Load every enabled mod.  Errors never stop the game."""

        self.mods = []
        self.hooks = {}
        self.save_data = {}
        self.errors = []
        self._hook_failures = set()
        self.loaded = False

        seen_ids = set()

        for metadata in self.discover():
            if metadata["id"] in seen_ids:
                metadata["status"] = "error"
                metadata["error"] = "duplicate mod id"
                self.errors.append((metadata["id"], metadata["error"]))
                self.mods.append(metadata)
                continue

            seen_ids.add(metadata["id"])

            if not metadata["enabled"]:
                metadata["status"] = "disabled"
                self.mods.append(metadata)
                continue

            if metadata["api_version"] > API_VERSION:
                metadata["status"] = "error"
                metadata["error"] = (
                    f"mod needs API {metadata['api_version']}, "
                    f"game provides {API_VERSION}"
                )
                self.errors.append((metadata["id"], metadata["error"]))
                print(f"[mods] {metadata['id']}: {metadata['error']}")
                self.mods.append(metadata)
                continue

            self._load_mod(metadata)
            self.mods.append(metadata)

        self.loaded = True
        self.emit("mods_loaded", game=self.game)
        return self.loaded_mods()

    def _load_mod(self, metadata):
        path = Path(metadata["file"])
        module_name = f"afterlight_mod_{metadata['id']}_{len(self.mods)}"

        search_path = str(path.parent)

        if search_path not in sys.path:
            sys.path.insert(0, search_path)

        try:
            spec = importlib.util.spec_from_file_location(module_name, path)

            if spec is None or spec.loader is None:
                raise ImportError(f"cannot create import spec for {path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            setup = getattr(module, "setup", None)

            if not callable(setup):
                raise AttributeError("mod.py must define setup(api)")

            api = ModAPI(self, metadata["id"])
            metadata["api"] = api
            metadata["module"] = module

            setup(api)

            metadata["status"] = "loaded"
            print(
                f"[mods] loaded {metadata['id']} "
                f"v{metadata['version']} ({metadata['name']})"
            )

        except Exception:
            metadata["status"] = "error"
            metadata["error"] = traceback.format_exc()
            self.errors.append((metadata["id"], metadata["error"]))
            print(f"[mods] failed to load {metadata['id']}:\n{metadata['error']}")

    # -- event dispatch --------------------------------------------------
    def add_hook(self, mod_id, event, callback):
        if not callable(callback):
            raise TypeError("hook callback must be callable")

        self.hooks.setdefault(str(event), []).append((mod_id, callback))
        return callback

    def remove_hook(self, mod_id, event, callback):
        handlers = self.hooks.get(str(event), [])
        self.hooks[str(event)] = [
            (handler_mod_id, handler)
            for handler_mod_id, handler in handlers
            if not (handler_mod_id == mod_id and handler == callback)
        ]

    def emit(self, event, **kwargs):
        """Call all hooks for an event and return non-None results."""

        results = []

        for mod_id, callback in list(self.hooks.get(str(event), [])):
            try:
                result = callback(**kwargs)

                if result is not None:
                    results.append(result)

            except Exception:
                self._report_hook_error(mod_id, event, callback)

        return results

    def _report_hook_error(self, mod_id, event, callback):
        key = (mod_id, str(event), id(callback))

        if key in self._hook_failures:
            return

        self._hook_failures.add(key)
        text = traceback.format_exc()
        self.errors.append((mod_id, f"{event}: {text}"))
        print(f"[mods] hook error in {mod_id}.{event}:\n{text}")

    # -- save data -------------------------------------------------------
    def export_save_data(self):
        return copy.deepcopy(self.save_data)

    def import_save_data(self, data):
        self.save_data = {}

        if not isinstance(data, dict):
            return

        for mod_id, values in data.items():
            if isinstance(values, dict):
                self.save_data[str(mod_id)] = copy.deepcopy(values)

    # -- queries ---------------------------------------------------------
    def loaded_mods(self):
        return [
            metadata
            for metadata in self.mods
            if metadata.get("status") == "loaded"
        ]

    def failed_mods(self):
        return [
            metadata
            for metadata in self.mods
            if metadata.get("status") == "error"
        ]

    def disabled_mods(self):
        return [
            metadata
            for metadata in self.mods
            if metadata.get("status") == "disabled"
        ]

    @property
    def mod_count(self):
        return len(self.loaded_mods())

    # -- shutdown --------------------------------------------------------
    def shutdown(self):
        self.emit("shutdown", game=self.game)

        for metadata in self.mods:
            module = metadata.get("module")
            api = metadata.get("api")
            teardown = getattr(module, "teardown", None) if module else None

            if not callable(teardown) or api is None:
                continue

            try:
                teardown(api)
            except Exception:
                print(
                    f"[mods] teardown error in {metadata['id']}:\n"
                    f"{traceback.format_exc()}"
                )
