"""Harvestable world resources: trees, rocks, bushes and mushrooms."""

import math
import random

import pygame

from game.items import get_icon
from game.localization import tr
from game.paths import resource_path


TILES_FOLDER = resource_path("assets", "images", "tiles")

CHUNK_TILES = 24

NODE_DATA = {
    "tree": {
        "name_key": "node_tree",
        "prompt_key": "prompt_chop",
        "hits": 4,
        "respawn": 55.0,
        "height": 170,
    },
    "rock": {
        "name_key": "node_rock",
        "prompt_key": "prompt_mine",
        "hits": 4,
        "respawn": 70.0,
        "height": 62,
    },
    "bush": {
        "name_key": "node_bush",
        "prompt_key": "prompt_gather",
        "hits": 2,
        "respawn": 40.0,
        "height": 58,
    },
    "mushroom": {
        "name_key": "node_mushroom",
        "prompt_key": "prompt_gather",
        "hits": 1,
        "respawn": 30.0,
        "height": 34,
    },
    "ruin": {
        "name_key": "node_ruin",
        "prompt_key": "prompt_search",
        "hits": 3,
        "respawn": 180.0,
        "height": 120,
    },
}

KIND_WEIGHTS = [
    ("tree", 42),
    ("rock", 25),
    ("bush", 21),
    ("mushroom", 12),
]

# Resource distribution per biome.  Biomes make long journeys feel different
# instead of repeating the same forest everywhere.
BIOME_WEIGHTS = {
    "forest": {"tree": 46, "rock": 16, "bush": 24, "mushroom": 14},
    "plains": {"tree": 18, "rock": 26, "bush": 42, "mushroom": 14},
    "highlands": {"tree": 18, "rock": 58, "bush": 10, "mushroom": 14},
    "swamp": {"tree": 24, "rock": 12, "bush": 30, "mushroom": 34},
}

BIOME_DENSITY = {
    "forest": (2, 4),
    "plains": (1, 3),
    "highlands": (1, 3),
    "swamp": (2, 4),
}

# One ancient ruin appears every this many chunks.
LANDMARK_INTERVAL = 6

_mushroom_image = None


def _get_mushroom_image():
    global _mushroom_image

    if _mushroom_image is not None:
        return _mushroom_image

    path = TILES_FOLDER / "mushroom_brown.png"

    if path.exists():
        try:
            _mushroom_image = pygame.image.load(str(path)).convert_alpha()
            _mushroom_image = pygame.transform.smoothscale(_mushroom_image, (58, 58))
        except pygame.error:
            _mushroom_image = None

    return _mushroom_image


class ResourceNode:
    def __init__(self, node_id, kind, x, ground_y):
        data = NODE_DATA[kind]

        self.id = node_id
        self.kind = kind
        self.x = float(x)
        self.ground_y = float(ground_y)

        self.max_hp = data.get("hits", 3)
        self.hp = self.max_hp
        self.respawn_time = data.get("respawn", 60.0)
        self.respawn_timer = 0.0
        self.alive = True

        self.shake = 0.0
        self.hit_flash = 0.0
        self.anim_time = random.random() * 10

    @property
    def data(self):
        return NODE_DATA[self.kind]

    @property
    def interaction_y(self):
        if "interaction_height" in self.data:
            return self.ground_y - self.data["interaction_height"]

        if self.kind == "tree":
            return self.ground_y - 70
        if self.kind == "bush":
            return self.ground_y - 35
        if self.kind == "mushroom":
            return self.ground_y - 18
        if self.kind == "ruin":
            return self.ground_y - 60
        return self.ground_y - 25

    def update(self, delta_time):
        self.anim_time += delta_time

        if not self.alive:
            self.respawn_timer -= delta_time

            if self.respawn_timer <= 0:
                self.alive = True
                self.hp = self.max_hp
                self.hit_flash = 0.0
            return

        self.shake = max(0.0, self.shake - delta_time * 3.5)
        self.hit_flash = max(0.0, self.hit_flash - delta_time * 4.0)

    def harvest(self, player, rng):
        if not self.alive:
            return None

        self.hp -= 1
        self.shake = 0.22
        self.hit_flash = 0.3

        tool = player.inventory.selected_tool()
        drops = []
        custom_drops = self.data.get("drops")

        if callable(custom_drops):
            try:
                drops = list(custom_drops(self, player, rng))
            except Exception as error:
                print(f"Resource drops error ({self.kind}): {error}")
                drops = []
        elif self.kind == "tree":
            amount = 2 if tool == "axe" else 1
            drops.append(("wood", amount))

            if rng.random() < 0.55:
                drops.append(("fiber", 1))

        elif self.kind == "rock":
            amount = 2 if tool == "pickaxe" else 1
            drops.append(("stone", amount))

            if rng.random() < 0.3:
                drops.append(("stone", 1))

        elif self.kind == "bush":
            drops.append(("fiber", rng.randint(1, 2)))

            if rng.random() < 0.75:
                drops.append(("berry", rng.randint(1, 2)))

        elif self.kind == "mushroom":
            drops.append(("mushroom", rng.randint(1, 2)))

            if rng.random() < 0.3:
                drops.append(("fiber", 1))

        elif self.kind == "ruin":
            drops.append(("stone", rng.randint(1, 3)))

            if rng.random() < 0.5:
                drops.append(("bone", 1))

            if rng.random() < 0.18:
                drops.append(("torch", 1))

        depleted = self.hp <= 0

        if depleted:
            self.alive = False
            self.respawn_timer = self.respawn_time

        return drops, depleted

    def prompt(self, language):
        name = self.data.get(f"name_{language}")

        if name is None:
            name = tr(language, self.data.get("name_key", self.kind))

        prompt = self.data.get(f"prompt_{language}")

        if prompt is not None:
            try:
                return prompt.format(name=name)
            except (KeyError, ValueError):
                return prompt

        return tr(language, self.data.get("prompt_key", "prompt_gather"), name=name)

    # -- drawing ---------------------------------------------------------
    def draw(self, surface, camera, highlighted=False):
        screen_x = round(self.x - camera.offset.x)
        ground_y = round(self.ground_y - camera.offset.y)

        if screen_x < -260 or screen_x > surface.get_width() + 260:
            return

        if not self.alive:
            self.draw_stump(surface, screen_x, ground_y)
            return

        shake = math.sin(self.anim_time * 55) * self.shake * 14
        x = screen_x + shake

        if highlighted:
            glow = pygame.Surface((110, 110), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 235, 130, 45), (55, 55), 52)
            surface.blit(glow, (x - 55, ground_y - 75))

        if self.kind == "tree":
            self.draw_tree(surface, x, ground_y)
        elif self.kind == "rock":
            self.draw_rock(surface, x, ground_y)
        elif self.kind == "bush":
            self.draw_bush(surface, x, ground_y)
        elif self.kind == "mushroom":
            self.draw_mushroom(surface, x, ground_y)
        elif self.kind == "ruin":
            self.draw_ruin(surface, x, ground_y)
        else:
            drawer = self.data.get("draw")

            if callable(drawer):
                try:
                    drawer(surface, x, ground_y)
                except Exception as error:
                    print(f"Resource draw error ({self.kind}): {error}")
                    pygame.draw.circle(
                        surface,
                        self.data.get("color", (120, 130, 140)),
                        (int(x), int(ground_y - 20)),
                        20,
                    )
            else:
                pygame.draw.circle(
                    surface,
                    self.data.get("color", (120, 130, 140)),
                    (int(x), int(ground_y - 20)),
                    20,
                )

    def draw_stump(self, surface, x, ground_y):
        pygame.draw.ellipse(surface, (36, 27, 21), (x - 24, ground_y - 8, 48, 14))

        if self.kind == "tree":
            pygame.draw.rect(surface, (85, 56, 34), (x - 12, ground_y - 22, 24, 22), border_radius=4)
            pygame.draw.ellipse(surface, (123, 85, 51), (x - 12, ground_y - 27, 24, 12))
        elif self.kind == "rock":
            pygame.draw.ellipse(surface, (79, 84, 89), (x - 18, ground_y - 12, 36, 14))
        elif self.kind == "bush":
            pygame.draw.ellipse(surface, (48, 84, 50), (x - 20, ground_y - 10, 40, 12))
        else:
            drawer = self.data.get("draw_stump")

            if callable(drawer):
                try:
                    drawer(surface, x, ground_y)
                except Exception as error:
                    print(f"Resource stump draw error ({self.kind}): {error}")
            else:
                pygame.draw.ellipse(
                    surface,
                    self.data.get("stump_color", (74, 78, 84)),
                    (x - 18, ground_y - 10, 36, 13),
                )

    def draw_tree(self, surface, x, ground_y):
        pygame.draw.ellipse(surface, (22, 29, 23), (x - 42, ground_y - 12, 84, 18))

        trunk = pygame.Rect(x - 14, ground_y - 158, 28, 158)
        pygame.draw.rect(surface, (79, 53, 34), trunk, border_radius=7)
        pygame.draw.rect(surface, (105, 72, 43), (trunk.x + 5, trunk.y, 9, trunk.height), border_radius=4)
        pygame.draw.line(surface, (64, 42, 27), (x + 6, ground_y - 10), (x + 6, ground_y - 120), 3)

        canopy = [
            (x, ground_y - 190, 62, (43, 91, 55)),
            (x - 48, ground_y - 160, 48, (37, 81, 49)),
            (x + 50, ground_y - 158, 50, (50, 105, 61)),
            (x - 24, ground_y - 208, 44, (55, 118, 66)),
            (x + 28, ground_y - 204, 46, (48, 108, 61)),
            (x + 2, ground_y - 174, 58, (59, 127, 71)),
        ]

        for cx, cy, radius, color in canopy:
            pygame.draw.circle(surface, color, (cx, cy), radius)

        for cx, cy, radius, _ in canopy[2:]:
            pygame.draw.circle(
                surface,
                (76, 150, 84),
                (cx - radius // 3, cy - radius // 3),
                max(8, radius // 3),
            )

    def draw_rock(self, surface, x, ground_y):
        pygame.draw.ellipse(surface, (22, 24, 26), (x - 42, ground_y - 12, 84, 18))

        points = [
            (x - 42, ground_y - 6),
            (x - 32, ground_y - 40),
            (x - 8, ground_y - 58),
            (x + 26, ground_y - 50),
            (x + 44, ground_y - 18),
            (x + 34, ground_y - 4),
        ]
        pygame.draw.polygon(surface, (96, 102, 108), points)
        pygame.draw.polygon(
            surface,
            (133, 140, 146),
            [(x - 32, ground_y - 40), (x - 8, ground_y - 58), (x + 18, ground_y - 52), (x - 4, ground_y - 34)],
        )
        pygame.draw.polygon(
            surface,
            (69, 74, 79),
            [(x - 42, ground_y - 6), (x + 34, ground_y - 4), (x + 20, ground_y - 22), (x - 18, ground_y - 26)],
        )
        pygame.draw.line(surface, (55, 59, 63), (x - 6, ground_y - 34), (x + 8, ground_y - 12), 3)
        pygame.draw.line(surface, (55, 59, 63), (x + 8, ground_y - 12), (x + 24, ground_y - 30), 2)

    def draw_bush(self, surface, x, ground_y):
        pygame.draw.ellipse(surface, (22, 29, 23), (x - 36, ground_y - 10, 72, 15))

        circles = [
            (x - 22, ground_y - 24, 24),
            (x + 20, ground_y - 22, 25),
            (x, ground_y - 38, 30),
            (x - 8, ground_y - 18, 26),
        ]

        for cx, cy, radius in circles:
            pygame.draw.circle(surface, (45, 96, 52), (cx, cy), radius)

        pygame.draw.circle(surface, (68, 130, 69), (x - 6, ground_y - 48), 15)

        berry_positions = [
            (x - 20, ground_y - 34),
            (x + 13, ground_y - 38),
            (x + 28, ground_y - 22),
            (x - 5, ground_y - 22),
            (x - 31, ground_y - 18),
        ]

        for bx, by in berry_positions:
            pygame.draw.circle(surface, (193, 42, 62), (bx, by), 4)
            pygame.draw.circle(surface, (247, 142, 146), (bx - 1, by - 1), 1)

    def draw_mushroom(self, surface, x, ground_y):
        image = _get_mushroom_image()

        pygame.draw.ellipse(surface, (22, 29, 23), (x - 20, ground_y - 8, 40, 12))

        if image is not None:
            surface.blit(image, (x - 29, ground_y - 56))
            return

        pygame.draw.rect(surface, (219, 204, 174), (x - 7, ground_y - 28, 14, 26), border_radius=4)
        pygame.draw.ellipse(surface, (169, 59, 46), (x - 28, ground_y - 48, 56, 32))
        pygame.draw.circle(surface, (238, 218, 196), (x - 10, ground_y - 37), 4)
        pygame.draw.circle(surface, (238, 218, 196), (x + 11, ground_y - 33), 3)

    def draw_ruin(self, surface, x, ground_y):
        pygame.draw.ellipse(surface, (26, 28, 30), (x - 52, ground_y - 12, 104, 18))

        # Fallen slabs around the base.
        pygame.draw.polygon(
            surface,
            (92, 98, 104),
            [
                (x - 48, ground_y - 4),
                (x - 30, ground_y - 22),
                (x - 2, ground_y - 14),
                (x - 16, ground_y - 2),
            ],
        )
        pygame.draw.polygon(
            surface,
            (108, 115, 121),
            [
                (x + 14, ground_y - 6),
                (x + 36, ground_y - 26),
                (x + 52, ground_y - 14),
                (x + 40, ground_y - 2),
            ],
        )

        # Broken pillar.
        pygame.draw.rect(
            surface,
            (104, 110, 116),
            (x - 14, ground_y - 104, 28, 96),
            border_radius=3,
        )
        pygame.draw.rect(
            surface,
            (128, 135, 141),
            (x - 14, ground_y - 104, 8, 96),
            border_radius=2,
        )
        pygame.draw.polygon(
            surface,
            (78, 83, 88),
            [
                (x - 14, ground_y - 104),
                (x - 6, ground_y - 118),
                (x + 4, ground_y - 110),
                (x + 14, ground_y - 104),
            ],
        )

        # Cracks and moss.
        pygame.draw.line(
            surface,
            (62, 66, 70),
            (x - 4, ground_y - 96),
            (x + 8, ground_y - 66),
            2,
        )
        pygame.draw.line(
            surface,
            (62, 66, 70),
            (x + 8, ground_y - 66),
            (x - 2, ground_y - 38),
            2,
        )

        for moss_x, moss_y, radius in (
            (x - 18, ground_y - 8, 7),
            (x + 22, ground_y - 6, 6),
            (x + 4, ground_y - 116, 5),
        ):
            pygame.draw.circle(surface, (58, 108, 62), (moss_x, moss_y), radius)

        # A slowly pulsing rune marks the landmark from afar.
        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 2.4)
        glow = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.circle(
            glow,
            (120, 225, 255, int(30 + 30 * pulse)),
            (32, 32),
            30,
        )
        surface.blit(glow, (x - 32, ground_y - 92))

        rune_color = (140, 235, 255) if pulse > 0.35 else (90, 180, 210)
        pygame.draw.circle(surface, rune_color, (x, ground_y - 60), 9, 2)
        pygame.draw.line(surface, rune_color, (x - 5, ground_y - 60), (x + 5, ground_y - 60), 2)
        pygame.draw.line(surface, rune_color, (x, ground_y - 65), (x, ground_y - 55), 2)


class ResourceManager:
    def __init__(self, world):
        self.world = world
        self.tile_size = world.tile_size
        self.chunk_pixels = CHUNK_TILES * self.tile_size
        self.seed = world.seed

        self.chunks = {}
        self.nodes = []

    # -- generation ------------------------------------------------------
    def _make_node(self, node_id, kind, tile_x):
        ground_y = self.world.get_surface_y(tile_x)
        x = tile_x * self.tile_size + self.tile_size / 2
        node = ResourceNode(node_id, kind, x, ground_y)
        self.nodes.append(node)
        return node

    def _weights_for_biome(self, biome):
        weights = dict(BIOME_WEIGHTS.get(biome, BIOME_WEIGHTS["forest"]))

        # Modded resources keep their global weight in every biome.
        for kind, weight in KIND_WEIGHTS:
            if kind not in weights and weight > 0:
                weights[kind] = weight

        return weights

    @staticmethod
    def _pick_kind(weights, rng):
        kinds = list(weights)

        if not kinds:
            return "tree"

        return rng.choices(
            kinds,
            weights=[weights[kind] for kind in kinds],
        )[0]

    def _generate_chunk(self, chunk_index):
        if chunk_index in self.chunks:
            return self.chunks[chunk_index]

        rng = random.Random(self.seed * 7919 + chunk_index * 104729)
        nodes = []
        used_tiles = set()
        chunk_start = chunk_index * CHUNK_TILES

        # Guarantee a friendly starting area with a node within reach.
        if chunk_index == 0:
            for tile_x, kind in (
                (1, "tree"),
                (2, "rock"),
                (5, "bush"),
                (7, "mushroom"),
                (9, "tree"),
                (14, "rock"),
            ):
                used_tiles.add(tile_x)
                nodes.append(
                    self._make_node(f"start:{tile_x}:{kind}", kind, tile_x)
                )
        elif chunk_index % LANDMARK_INTERVAL == 0:
            # Rare ancient ruin landmark.
            tile_x = chunk_start + rng.randrange(4, CHUNK_TILES - 4)
            used_tiles.add(tile_x)
            nodes.append(
                self._make_node(
                    f"ruin:{chunk_index}:{tile_x}",
                    "ruin",
                    tile_x,
                )
            )

        biome = self.world.get_biome(chunk_start + CHUNK_TILES // 2)
        weights = self._weights_for_biome(biome)
        low, high = BIOME_DENSITY.get(biome, (1, 3))
        count = rng.randint(low, high)

        # Occasional extra growth makes forests and swamps feel denser.
        if rng.random() < 0.28:
            count += rng.randint(1, 2)

        for _ in range(count):
            tile_x = chunk_start + rng.randrange(1, CHUNK_TILES - 1)

            if tile_x in used_tiles or tile_x <= 0:
                continue

            used_tiles.add(tile_x)
            kind = self._pick_kind(weights, rng)

            nodes.append(
                self._make_node(
                    f"{chunk_index}:{tile_x}:{kind}",
                    kind,
                    tile_x,
                )
            )

            # Small clusters of the same resource.
            if kind in ("tree", "bush", "mushroom") and rng.random() < 0.3:
                for _ in range(rng.randint(1, 2)):
                    neighbor = tile_x + rng.choice((-2, -1, 1, 2))

                    if neighbor in used_tiles or neighbor <= 0:
                        continue
                    if not (chunk_start + 1 <= neighbor < chunk_start + CHUNK_TILES - 1):
                        continue

                    used_tiles.add(neighbor)
                    nodes.append(
                        self._make_node(
                            f"{chunk_index}:{neighbor}:{kind}",
                            kind,
                            neighbor,
                        )
                    )

        self.chunks[chunk_index] = nodes
        return nodes

    def ensure_around(self, camera_x, screen_width):
        first = max(
            0,
            int((camera_x - self.chunk_pixels) // self.chunk_pixels),
        )
        last = int((camera_x + screen_width) // self.chunk_pixels) + 1

        for chunk_index in range(first, last + 1):
            self._generate_chunk(chunk_index)

    # -- updates ---------------------------------------------------------
    def update(self, delta_time, player, camera, screen_width):
        self.ensure_around(camera.offset.x, screen_width)

        for node in self.nodes:
            node.update(delta_time)

        return self.get_nearest(player)

    def get_nearest(self, player):
        player_x = player.position.x + player.rect.width / 2
        player_y = player.position.y + player.rect.height / 2

        nearest = None
        nearest_distance = 120.0

        for node in self.nodes:
            if not node.alive:
                continue

            dx = node.x - player_x
            dy = node.interaction_y - player_y

            if abs(dx) > 115:
                continue

            distance = math.hypot(dx, dy * 0.75)

            if distance < nearest_distance:
                nearest_distance = distance
                nearest = node

        return nearest

    def draw(self, surface, camera, highlighted=None):
        visible = []

        for node in self.nodes:
            screen_x = node.x - camera.offset.x

            if -260 <= screen_x <= surface.get_width() + 260:
                visible.append(node)

        # Trees and bushes behind rocks/mushrooms gives a little depth.
        order = {"tree": 0, "bush": 1, "rock": 2, "mushroom": 3}
        visible.sort(key=lambda node: (node.ground_y, order.get(node.kind, 0), node.x))

        for node in visible:
            node.draw(surface, camera, node is highlighted)


def draw_item_pickup_icon(surface, item_id, position, size=24):
    """Utility used by particle/pickup effects."""
    icon = get_icon(item_id, size)
    surface.blit(icon, position)
