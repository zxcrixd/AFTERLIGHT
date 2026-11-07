
import random

import pygame

from settings import TILE_SIZE, WORLD_SEED
from game.paths import resource_path
from game.terrain import Terrain


GRASS = (48, 83, 53)
DIRT = (91, 72, 52)
STONE = (91, 94, 91)

# Multiplicative tints applied to the grass texture so biomes are visible
# without needing extra art assets.
BIOME_TINTS = {
    "forest": (255, 255, 255),
    "plains": (255, 232, 168),
    "highlands": (204, 216, 232),
    "swamp": (176, 216, 164),
}


TILES_FOLDER = resource_path("assets", "images", "tiles")

BACKGROUNDS_FOLDER = resource_path("assets", "images", "backgrounds")


class World:
    def __init__(self, seed=None):
        self.tile_size = TILE_SIZE
        self.seed = int(WORLD_SEED if seed is None else seed)

        self.terrain = Terrain(self.seed)

        self.textures = {
            "grass": self.load_texture(
                "terrain_grass_block_top.png"
            ),
            "dirt": self.load_texture(
                "terrain_dirt_block_top.png"
            ),
            "stone": self.load_texture(
                "terrain_stone_block_top.png"
            ),
        }

        self.grass_tints = self._build_grass_tints()

        self.backgrounds = {
            "day": self.load_background(
                "background_color_trees.png"
            ),
            "night": self.load_background(
                "background_color_night_trees.png"
            ),
        }

        self.current_background = "night"
        self.background_scroll_speed = 0.25

    def load_texture(self, filename):
        path = TILES_FOLDER / filename

        if not path.exists():
            print(f"World texture not found: {path}")
            return None

        try:
            image = pygame.image.load(
                str(path)
            ).convert_alpha()

            return pygame.transform.scale(
                image,
                (self.tile_size, self.tile_size),
            )

        except pygame.error as error:
            print(f"World texture error: {error}")
            return None

    def _build_grass_tints(self):
        tints = {}
        grass = self.textures.get("grass")

        if grass is None:
            return tints

        for biome, tint in BIOME_TINTS.items():
            if tint == (255, 255, 255):
                tints[biome] = grass
                continue

            tinted = grass.copy()
            tinted.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
            tints[biome] = tinted

        return tints

    def load_background(self, filename):
        path = BACKGROUNDS_FOLDER / filename

        if not path.exists():
            print(f"Background not found: {path}")
            return None

        try:
            return pygame.image.load(
                str(path)
            ).convert()

        except pygame.error as error:
            print(f"Background loading error: {error}")
            return None

    def set_background(self, name):
        if name in self.backgrounds:
            if self.backgrounds[name] is not None:
                self.current_background = name

    def draw_background(self, surface, camera):
        width, height = surface.get_size()

        background = self.backgrounds.get(
            self.current_background
        )

        if background is None:
            surface.fill((12, 16, 24))
            return

        scale = max(
            width / background.get_width(),
            height / background.get_height(),
        )

        background_width = int(
            background.get_width() * scale
        )

        background_height = int(
            background.get_height() * scale
        )

        scaled = pygame.transform.scale(
            background,
            (background_width, background_height),
        )

        vertical_offset = (
            height - background_height
        ) // 2

        if background_width <= width:
            surface.blit(
                scaled,
                (
                    (width - background_width) // 2,
                    vertical_offset,
                ),
            )
            return

        max_offset = background_width - width

        camera_offset = int(
            camera.offset.x * self.background_scroll_speed
        )

        background_offset = camera_offset % background_width

        background_offset = min(
            background_offset,
            max_offset,
        )

        surface.blit(
            scaled,
            (-background_offset, vertical_offset),
        )

        if background_offset > 0:
            surface.blit(
                scaled,
                (
                    background_width - background_offset,
                    vertical_offset,
                ),
            )

    def get_surface_y(self, tile_x):
        return self.terrain.get_surface_y(tile_x)

    def get_biome(self, tile_x):
        return self.terrain.get_biome(tile_x)

    def get_tile(self, x, y):
        surface_row = self.terrain.get_height(x)

        if y < surface_row:
            return None

        if y == surface_row:
            return "grass"

        depth = y - surface_row

        if depth <= 3:
            return "dirt"

        rng = random.Random(
            self.seed + x * 73856093 + y * 19349663
        )

        if rng.random() < 0.8:
            return "dirt"

        return "stone"

    def is_solid(self, x, y):
        return self.get_tile(x, y) is not None

    def draw(self, surface, camera):
        self.draw_background(surface, camera)

        width, height = surface.get_size()

        start_x = max(
            0,
            int(camera.offset.x // self.tile_size),
        )

        end_x = (
            start_x
            + width // self.tile_size
            + 2
        )

        start_y = max(
            0,
            int(camera.offset.y // self.tile_size),
        )

        end_y = (
            start_y
            + height // self.tile_size
            + 2
        )

        for x in range(start_x, end_x):
            surface_row = self.terrain.get_height(x)

            for y in range(
                max(start_y, surface_row),
                end_y,
            ):
                tile_type = self.get_tile(x, y)

                if tile_type is None:
                    continue

                world_x = x * self.tile_size
                world_y = y * self.tile_size

                rect = pygame.Rect(
                    round(world_x - camera.offset.x),
                    round(world_y - camera.offset.y),
                    self.tile_size,
                    self.tile_size,
                )

                texture = self.textures[tile_type]

                if tile_type == "grass":
                    texture = self.grass_tints.get(
                        self.terrain.get_biome(x),
                        texture,
                    )

                if texture is not None:
                    surface.blit(texture, rect)
                else:
                    color = {
                        "grass": GRASS,
                        "dirt": DIRT,
                        "stone": STONE,
                    }[tile_type]

                    pygame.draw.rect(
                        surface,
                        color,
                        rect,
                    )
