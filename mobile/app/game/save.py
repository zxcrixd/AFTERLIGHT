"""JSON save/load for the survival run."""

import json

from game.paths import data_folder


SAVE_FOLDER = data_folder()
SAVE_FILE = SAVE_FOLDER / "game.json"


def has_save():
    if not SAVE_FILE.exists():
        return False

    try:
        with SAVE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return isinstance(data, dict) and "player" in data
    except (OSError, json.JSONDecodeError):
        return False


def save_game(game):
    SAVE_FOLDER.mkdir(parents=True, exist_ok=True)

    player = game.player

    data = {
        "version": 2,
        "world_seed": int(game.world.seed),
        "player": {
            "x": player.position.x,
            "y": player.position.y,
            "health": player.health,
            "hunger": player.hunger,
            "stamina": player.stamina,
            "selected": player.inventory.selected,
            "inventory": player.inventory.to_list(),
        },
        "time_of_day": game.daynight.time_of_day,
        "day": game.daynight.day,
        "kills": game.kills,
        "campfires": [
            {"x": campfire.x, "y": campfire.ground_y}
            for campfire in game.campfires
        ],
    }

    mods = getattr(game, "mods", None)

    if mods is not None:
        data["mods"] = mods.export_save_data()
        mods.emit("save", game=game, data=data)

    try:
        with SAVE_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        return True
    except OSError as error:
        print(f"Could not save game: {error}")
        return False


def load_game():
    if not SAVE_FILE.exists():
        return None

    try:
        with SAVE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not load game: {error}")
        return None

    if not isinstance(data, dict) or "player" not in data:
        return None

    return data


def delete_save():
    try:
        if SAVE_FILE.exists():
            SAVE_FILE.unlink()
    except OSError as error:
        print(f"Could not delete save: {error}")
