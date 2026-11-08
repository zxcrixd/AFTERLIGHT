"""Example AFTERLIGHT mod.

This file is intentionally small but touches every major modding feature:
items, icons, recipes, world resources, event hooks and mod save data.
Copy the folder, rename it, and start building your own content.
"""

import random

import pygame


def draw_crystal(surface):
    """Icon drawer for the ``crystal`` item (64x64 RGBA surface)."""

    pygame.draw.polygon(
        surface,
        (86, 206, 255),
        [(32, 4), (54, 22), (46, 56), (18, 56), (10, 22)],
    )
    pygame.draw.polygon(
        surface,
        (170, 240, 255),
        [(32, 8), (46, 24), (32, 34), (18, 24)],
    )
    pygame.draw.polygon(
        surface,
        (52, 156, 214),
        [(32, 34), (46, 24), (46, 54), (32, 60)],
    )
    pygame.draw.line(surface, (235, 253, 255), (26, 16), (34, 30), 3)


def draw_crystal_sword(surface):
    """Icon drawer for the ``crystal_sword`` item."""

    pygame.draw.polygon(
        surface,
        (110, 220, 255),
        [(31, 4), (39, 12), (25, 44), (19, 38)],
    )
    pygame.draw.line(surface, (235, 253, 255), (34, 9), (22, 39), 2)
    pygame.draw.line(surface, (79, 52, 35), (17, 40), (31, 53), 8)
    pygame.draw.line(surface, (245, 214, 120), (12, 45), (28, 29), 4)
    pygame.draw.circle(surface, (140, 230, 255), (23, 33), 3)


def draw_crystal_cluster(surface, x, ground_y):
    """World drawing for the custom ``crystal_cluster`` resource."""

    x = int(x)
    ground_y = int(ground_y)

    pygame.draw.ellipse(
        surface,
        (28, 32, 38),
        (x - 30, ground_y - 10, 60, 16),
    )

    crystals = (
        (x - 16, ground_y - 10, 16, 34),
        (x + 4, ground_y - 8, 20, 48),
        (x + 22, ground_y - 6, 13, 27),
    )

    for cx, base_y, width, height in crystals:
        pygame.draw.polygon(
            surface,
            (72, 184, 236),
            [
                (cx, base_y - height),
                (cx + width // 2, base_y - height // 2),
                (cx + width // 3, base_y),
                (cx - width // 3, base_y),
                (cx - width // 2, base_y - height // 2),
            ],
        )
        pygame.draw.polygon(
            surface,
            (178, 241, 255),
            [
                (cx, base_y - height),
                (cx + width // 4, base_y - height // 2),
                (cx, base_y - 4),
            ],
        )

    glow = pygame.Surface((100, 100), pygame.SRCALPHA)
    pygame.draw.circle(glow, (90, 220, 255, 34), (50, 50), 46)
    surface.blit(glow, (x - 50, ground_y - 72))


def draw_crystal_stump(surface, x, ground_y):
    x = int(x)
    ground_y = int(ground_y)
    pygame.draw.ellipse(
        surface,
        (58, 120, 150),
        (x - 18, ground_y - 10, 36, 13),
    )


def setup(api):
    api.log("Crystal Example is loading")

    api.register_item(
        "crystal",
        "Кристалл",
        "Crystal",
        category="material",
        max_stack=50,
        description_ru="Светящийся кристалл, найденный в глубинах мира.",
        description_en="A glowing crystal found deep in the world.",
        icon=draw_crystal,
    )

    api.register_item(
        "crystal_sword",
        "Кристальный меч",
        "Crystal Sword",
        category="weapon",
        max_stack=1,
        damage=46,
        reach=78,
        description_ru="Сияющий клинок. Разрубает зомби и освещает путь.",
        description_en="A shining blade. Cuts zombies apart and lights the way.",
        icon=draw_crystal_sword,
    )

    api.register_recipe(
        "crystal_sword",
        "crystal_sword",
        1,
        {"crystal": 3, "bone": 2, "fiber": 2},
        "Кристальный меч",
        "Crystal Sword",
        description_ru="Оружие из светящихся кристаллов.",
        description_en="A weapon made of glowing crystals.",
    )

    api.register_resource(
        "crystal_cluster",
        "Кристаллы",
        "Crystal Cluster",
        "E — добыть: {name}",
        "E — mine: {name}",
        hits=3,
        respawn=90.0,
        weight=8,
        height=60,
        interaction_height=32,
        drops=lambda node, player, rng: [
            ("crystal", rng.randint(1, 2)),
        ],
        draw=draw_crystal_cluster,
        draw_stump=draw_crystal_stump,
        color=(90, 210, 250),
        stump_color=(58, 120, 150),
    )

    def on_game_start(game):
        mined = api.get_save_data("mined", 0)

        if mined:
            api.notify(
                f"Кристаллов добыто: {mined}",
                color=(130, 225, 255),
                duration=3.0,
            )
        else:
            api.notify(
                "Example Mod: ищите светящиеся кристаллы!",
                color=(130, 225, 255),
                duration=3.5,
            )

    def on_player_damage(game, player, amount, source):
        # Each crystal in the inventory absorbs 8% damage, up to 24%.
        crystals = min(3, player.inventory.count("crystal"))
        return amount * (1.0 - 0.08 * crystals)

    def on_enemy_death(game, zombie, drops):
        if random.random() < 0.2:
            drops = list(drops)
            drops.append(("crystal", 1))

        return drops

    def on_harvest(game, node, player, drops, depleted):
        if node.kind != "crystal_cluster":
            return None

        mined = api.get_save_data("mined", 0) + 1
        api.set_save_data("mined", mined)

        if mined % 5 == 0:
            api.notify(
                f"Добыто кристаллов: {mined}",
                color=(130, 225, 255),
                duration=2.5,
            )

        return None

    def on_craft(game, recipe, item):
        if recipe.id == "crystal_sword":
            api.notify(
                "Кристальный меч готов к бою!",
                color=(170, 240, 255),
                duration=3.0,
            )

    def on_load(game, data):
        api.log("save data loaded:", api.get_save_data("mined", 0))

    def on_save(game, data):
        api.log("saving mod data:", api.get_save_data("mined", 0))

    api.on("game_start", on_game_start)
    api.on("player_damage", on_player_damage)
    api.on("enemy_death", on_enemy_death)
    api.on("harvest", on_harvest)
    api.on("craft", on_craft)
    api.on("load", on_load)
    api.on("save", on_save)


def teardown(api):
    api.log("Crystal Example unloaded")
