"""Procedural terrain: seeded multi-octave height field and biomes."""

import math
import random

from settings import TILE_SIZE, WORLD_SEED


BIOMES = ("forest", "plains", "highlands", "swamp")

# Base surface height in tiles. The spawn plateau uses exactly this value.
SPAWN_HEIGHT = 8


class Terrain:
    """Deterministic terrain built from several layers of value noise.

    Every world is defined by a single integer seed.  The same seed always
    produces the same hills, biomes and spawn plateau, which makes saves and
    shared seeds reproducible while each new game gets its own world.
    """

    def __init__(self, seed=None):
        self.tile_size = TILE_SIZE
        self.seed = int(WORLD_SEED if seed is None else seed)

        self.base_height = SPAWN_HEIGHT
        self.height_variation = 4
        self.noise_scale = 13.0

        # (frequency multiplier, amplitude)
        self.octaves = (
            (1.0, 1.0),
            (2.3, 0.52),
            (5.1, 0.26),
        )

        self._height_cache = {}
        self._biome_cache = {}
        self._noise_cache = {}

    # -- noise -----------------------------------------------------------
    @staticmethod
    def smooth(value):
        return value * value * (3 - 2 * value)

    def get_noise_value(self, point, salt=0):
        """Return a deterministic pseudo-random value in ``[-1, 1]``."""

        key = (point, salt)

        cached = self._noise_cache.get(key)
        if cached is not None:
            return cached

        rng = random.Random(
            (self.seed * 1000003)
            ^ (point * 73856093)
            ^ (salt * 19349663)
        )
        value = rng.uniform(-1.0, 1.0)
        self._noise_cache[key] = value
        return value

    def _sample(self, x, scale, salt):
        """Smoothly interpolate the noise between two lattice points."""

        position = x / scale
        left = math.floor(position)
        right = left + 1
        blend = self.smooth(position - left)

        left_value = self.get_noise_value(left, salt)
        right_value = self.get_noise_value(right, salt)

        return left_value * (1.0 - blend) + right_value * blend

    def _raw_height(self, tile_x):
        total = 0.0
        amplitude_sum = 0.0

        for index, (frequency, amplitude) in enumerate(self.octaves):
            total += (
                self._sample(tile_x, self.noise_scale / frequency, index + 1)
                * amplitude
            )
            amplitude_sum += amplitude

        noise = total / amplitude_sum if amplitude_sum else 0.0
        return self.base_height + noise * self.height_variation

    # -- public API ------------------------------------------------------
    def get_height(self, tile_x):
        if tile_x in self._height_cache:
            return self._height_cache[tile_x]

        height = self._raw_height(tile_x)

        # A flat, safe spawn plateau with smooth shoulders so the player
        # always starts on solid, level ground.
        distance = abs(tile_x - 1)

        if distance <= 3:
            blend = 1.0
        elif distance <= 8:
            blend = self.smooth(1.0 - (distance - 3) / 5.0)
        else:
            blend = 0.0

        if blend > 0.0:
            height = self.base_height * blend + height * (1.0 - blend)

        result = max(4, min(15, round(height)))
        self._height_cache[tile_x] = result
        return result

    def get_surface_y(self, tile_x):
        return self.get_height(tile_x) * self.tile_size

    def get_biome(self, tile_x):
        """Return the biome name for a column of tiles."""

        if tile_x in self._biome_cache:
            return self._biome_cache[tile_x]

        # Keep the starting area forested and friendly.
        if -4 <= tile_x <= 14:
            biome = "forest"
        else:
            elevation = self._sample(tile_x, 38.0, 21)
            moisture = self._sample(tile_x, 27.0, 22)
            detail = self._sample(tile_x, 9.0, 23)

            if elevation > 0.34:
                biome = "highlands"
            elif moisture > 0.24:
                biome = "swamp"
            elif elevation < -0.3 and detail < 0.12:
                biome = "plains"
            else:
                biome = "forest"

        self._biome_cache[tile_x] = biome
        return biome
