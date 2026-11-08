"""Placeable structures, currently campfires."""

import math

import pygame


class Campfire:
    HEAL_RADIUS = 130
    LIGHT_RADIUS = 300
    HEAL_PER_SECOND = 2.5

    def __init__(self, x, ground_y):
        self.x = float(x)
        self.ground_y = float(ground_y)
        self.anim_time = 0.0
        self.alive = True

    def update(self, delta_time):
        self.anim_time += delta_time

    def heal_amount(self, player):
        player_x = player.position.x + player.rect.width / 2
        distance = abs(player_x - self.x)

        if distance <= self.HEAL_RADIUS:
            return self.HEAL_PER_SECOND

        return 0.0

    def light(self):
        flicker = 12 * math.sin(self.anim_time * 8.5) + 5 * math.sin(self.anim_time * 21)
        return (self.x, self.ground_y - 30, self.LIGHT_RADIUS + flicker)

    def draw(self, surface, camera):
        x = round(self.x - camera.offset.x)
        y = round(self.ground_y - camera.offset.y)

        if x < -120 or x > surface.get_width() + 120:
            return

        pygame.draw.ellipse(surface, (27, 23, 20), (x - 36, y - 12, 72, 18))

        pygame.draw.line(surface, (79, 50, 30), (x - 28, y - 2), (x + 26, y - 16), 9)
        pygame.draw.line(surface, (105, 68, 40), (x - 26, y - 16), (x + 28, y - 2), 9)

        flicker = math.sin(self.anim_time * 13) * 4

        glow = pygame.Surface((120, 120), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 142, 55, 36), (60, 60), 58)
        surface.blit(glow, (x - 60, y - 70))

        pygame.draw.circle(surface, (221, 78, 32), (x, y - 26), int(20 + flicker))
        pygame.draw.circle(surface, (250, 139, 41), (x, y - 31), int(15 + flicker * 0.7))
        pygame.draw.circle(surface, (255, 220, 105), (x, y - 35), int(8 + flicker * 0.4))

        for index in range(3):
            ember_x = x + math.sin(self.anim_time * 4 + index * 2.1) * (10 + index * 5)
            ember_y = y - 50 - ((self.anim_time * 24 + index * 17) % 42)
            alpha = max(0, 210 - index * 45)
            ember = pygame.Surface((5, 5), pygame.SRCALPHA)
            pygame.draw.circle(ember, (255, 176, 70, alpha), (2, 2), 2)
            surface.blit(ember, (ember_x, ember_y))
