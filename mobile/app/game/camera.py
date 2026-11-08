"""Smooth horizontal camera with a small screen shake effect."""

import random

import pygame


class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.base_offset = pygame.Vector2(0, 0)
        self.offset = pygame.Vector2(0, 0)
        self.smoothing = 8.0

        self.shake_strength = 0.0
        self.shake_timer = 0.0

    def shake(self, strength=7.0, duration=0.24):
        self.shake_strength = max(self.shake_strength, strength)
        self.shake_timer = max(self.shake_timer, duration)

    def update(self, target, delta_time=1 / 60):
        target_x = (
            target.position.x
            + target.rect.width / 2
        )

        desired_x = target_x - self.width / 2

        factor = min(
            1.0,
            self.smoothing * delta_time,
        )

        self.base_offset.x += (
            desired_x - self.base_offset.x
        ) * factor

        self.base_offset.x = max(
            0,
            self.base_offset.x,
        )

        self.base_offset.y = 0

        if self.shake_timer > 0:
            self.shake_timer -= delta_time
            self.shake_strength *= max(0.0, 1.0 - delta_time * 9.0)

            if self.shake_timer <= 0:
                self.shake_strength = 0.0
        else:
            self.shake_strength = 0.0

        shake_x = random.uniform(-self.shake_strength, self.shake_strength)
        shake_y = random.uniform(-self.shake_strength, self.shake_strength)

        self.offset.x = self.base_offset.x + shake_x
        self.offset.y = self.base_offset.y + shake_y

    def apply(self, rect):
        return pygame.Rect(
            round(rect.x - self.offset.x),
            round(rect.y - self.offset.y),
            rect.width,
            rect.height,
        )
