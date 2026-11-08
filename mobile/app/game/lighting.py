"""Day/night cycle and soft lighting for torches and campfires."""

import math

import pygame

from game.localization import tr


class DayNightCycle:
    def __init__(self, length=240.0, time_of_day=0.32):
        self.length = length
        self.time_of_day = time_of_day % 1.0
        self.day = 1
        self._last_time = self.time_of_day

    def update(self, delta_time):
        self._last_time = self.time_of_day
        self.time_of_day = (self.time_of_day + delta_time / self.length) % 1.0

        if self.time_of_day < self._last_time:
            self.day += 1

    @property
    def darkness(self):
        t = self.time_of_day

        if t < 0.2 or t >= 0.82:
            return 168
        if t < 0.32:
            return int(168 * (1.0 - (t - 0.2) / 0.12))
        if t < 0.68:
            return 0
        if t < 0.82:
            return int(168 * ((t - 0.68) / 0.14))

        return 168

    @property
    def is_night(self):
        return self.darkness > 82

    @property
    def phase_key(self):
        t = self.time_of_day

        if t < 0.22:
            return "night"
        if t < 0.32:
            return "dawn"
        if t < 0.55:
            return "morning"
        if t < 0.68:
            return "noon"
        if t < 0.82:
            return "dusk"

        return "night"

    def phase_name(self, language):
        return tr(language, self.phase_key)

    @property
    def clock_text(self):
        total_minutes = int(self.time_of_day * 24 * 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    @property
    def darkness_ratio(self):
        return self.darkness / 168.0


class Lighting:
    def __init__(self):
        self._gradient_cache = {}
        self._stars = []
        self._overlay = None
        self._star_overlay = None

        import random

        rng = random.Random(1337)

        for _ in range(70):
            self._stars.append(
                (
                    rng.random(),
                    rng.random() * 0.62,
                    rng.choice((1, 1, 1, 2)),
                    rng.uniform(0.45, 1.0),
                )
            )

    def _gradient(self, radius):
        # Quantize to keep flickering campfires from creating dozens of textures.
        radius = max(24, (int(radius) // 8) * 8)

        if radius in self._gradient_cache:
            return self._gradient_cache[radius]

        size = 64
        base = pygame.Surface((size, size), pygame.SRCALPHA)

        for y in range(size):
            for x in range(size):
                dx = (x + 0.5) / size * 2.0 - 1.0
                dy = (y + 0.5) / size * 2.0 - 1.0
                distance = math.hypot(dx, dy)

                if distance <= 0.12:
                    alpha = 0
                else:
                    alpha = int(255 * min(1.0, (distance - 0.12) / 0.88) ** 1.25)

                base.set_at((x, y), (255, 255, 255, alpha))

        gradient = pygame.transform.smoothscale(base, (radius * 2, radius * 2))
        self._gradient_cache[radius] = gradient
        return gradient

    def draw_stars(self, surface, darkness):
        if darkness < 40:
            return

        width, height = surface.get_size()
        alpha_ratio = min(1.0, darkness / 168.0)

        if (
            self._star_overlay is None
            or self._star_overlay.get_size() != (width, height)
        ):
            self._star_overlay = pygame.Surface(
                (width, height),
                pygame.SRCALPHA,
            )

        overlay = self._star_overlay
        overlay.fill((0, 0, 0, 0))

        for x_ratio, y_ratio, size, brightness in self._stars:
            x = int(x_ratio * width)
            y = int(y_ratio * height)
            alpha = int(190 * brightness * alpha_ratio)
            pygame.draw.circle(overlay, (225, 230, 255, alpha), (x, y), size)

        surface.blit(overlay, (0, 0))

    def draw(self, surface, lights, darkness):
        if darkness <= 0:
            return

        self.draw_stars(surface, darkness)

        if (
            self._overlay is None
            or self._overlay.get_size() != surface.get_size()
        ):
            self._overlay = pygame.Surface(
                surface.get_size(),
                pygame.SRCALPHA,
            )

        overlay = self._overlay
        overlay.fill((3, 5, 14, darkness))

        for x, y, radius in lights:
            radius = int(radius)

            if radius <= 0:
                continue

            gradient = self._gradient(radius)
            gradient_radius = gradient.get_width() // 2
            overlay.blit(
                gradient,
                (
                    int(x - gradient_radius),
                    int(y - gradient_radius),
                ),
                special_flags=pygame.BLEND_RGBA_MIN,
            )

        surface.blit(overlay, (0, 0))
