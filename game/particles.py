"""Tiny particle system used for hits, gathering and crafting feedback."""

import math
import random

import pygame


class Particle:
    __slots__ = ("position", "velocity", "life", "max_life", "color", "size", "gravity")

    def __init__(self, position, velocity, life, color, size, gravity):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def clear(self):
        self.particles.clear()

    def add_burst(self, position, color, count=12, speed=150, gravity=520, size=(2, 5), life=(0.35, 0.8)):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            magnitude = random.uniform(speed * 0.25, speed)
            velocity = (
                math.cos(angle) * magnitude,
                math.sin(angle) * magnitude - speed * 0.25,
            )
            self.particles.append(
                Particle(
                    position,
                    velocity,
                    random.uniform(*life),
                    color,
                    random.randint(size[0], size[1]),
                    gravity,
                )
            )

    def add_text_pop(self, position, text, color=(255, 235, 160)):
        """Spawn a small floating text particle (drawn as a plus/cross)."""
        self.particles.append(
            Particle(position, (0, -55), 0.85, color, 4, -20)
        )

    def update(self, delta_time):
        alive = []

        for particle in self.particles:
            particle.life -= delta_time

            if particle.life <= 0:
                continue

            particle.velocity.y += particle.gravity * delta_time
            particle.position.x += particle.velocity.x * delta_time
            particle.position.y += particle.velocity.y * delta_time
            alive.append(particle)

        self.particles = alive

    def draw(self, surface, camera):
        for particle in self.particles:
            ratio = max(0.0, particle.life / particle.max_life)
            alpha = int(255 * ratio)
            size = max(1, int(particle.size * (0.4 + ratio * 0.6)))

            x = int(particle.position.x - camera.offset.x)
            y = int(particle.position.y - camera.offset.y)

            if x < -20 or x > surface.get_width() + 20:
                continue

            dot = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(dot, (*particle.color, alpha), (size, size), size)
            surface.blit(dot, (x - size, y - size))
