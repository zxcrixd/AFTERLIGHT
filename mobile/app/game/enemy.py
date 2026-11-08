"""Zombie enemies with health, attacks, drops and death animation."""

import random

import pygame

from game.paths import resource_path


ENEMIES_FOLDER = resource_path("assets", "images", "enemies")


class Zombie:
    def __init__(self, x, world, night=False, difficulty=1.0):
        self.position = pygame.Vector2(x, 0)

        self.width = 48
        self.height = 56

        self.speed = (101 if night else 82) * difficulty
        self.stop_distance = 38

        self.velocity_x = 0
        self.facing_right = False

        self.world = world

        self.rect = pygame.Rect(
            round(x),
            0,
            self.width,
            self.height,
        )

        self.max_health = 58 if night else 42
        self.health = self.max_health
        self.attack_damage = 13 if night else 10
        self.attack_range = 58
        self.attack_cooldown = 1.15
        self.attack_timer = random.uniform(0.2, 0.8)

        self.dead = False
        self.death_timer = 0.0
        self.death_duration = 0.55
        self.drops_rolled = False

        self.hit_flash = 0.0
        self.knockback_timer = 0.0

        self.animation_time = 0
        self.animation_speed = 0.25
        self.current_animation = "idle"

        self.sprites = {
            "idle": [],
            "walk": [],
            "hit": [],
        }

        self.color = (75, 135, 65)
        self.night = night

        self.load_sprites()
        self.update_ground_position()

    def load_image(self, filename):
        path = ENEMIES_FOLDER / filename

        if not path.exists():
            print(f"Zombie sprite not found: {filename}")
            return None

        try:
            image = pygame.image.load(
                str(path)
            ).convert_alpha()

            return pygame.transform.scale(
                image,
                (self.width, self.height),
            )

        except pygame.error as error:
            print(f"Zombie sprite error: {error}")
            return None

    def load_first(self, filenames):
        for filename in filenames:
            if (ENEMIES_FOLDER / filename).exists():
                return self.load_image(filename)

        return None

    def load_sprites(self):
        idle = self.load_first(
            ("zombie_green_idle.png", "character_green_idle.png")
        )

        walk_a = self.load_first(
            ("zombie_green_walk_a.png", "character_green_walk_a.png")
        )

        walk_b = self.load_first(
            ("zombie_green_walk_b.png", "character_green_walk_b.png")
        )

        hit = self.load_first(
            ("zombie_green_hit.png", "character_green_hit.png")
        )

        if idle is not None:
            self.sprites["idle"] = [idle]

        self.sprites["walk"] = [
            frame
            for frame in (walk_a, walk_b)
            if frame is not None
        ]

        if hit is not None:
            self.sprites["hit"] = [hit]

        if not self.sprites["idle"] and self.sprites["walk"]:
            self.sprites["idle"] = [
                self.sprites["walk"][0]
            ]

        if not self.sprites["walk"] and self.sprites["idle"]:
            self.sprites["walk"] = [
                self.sprites["idle"][0]
            ]

    def set_animation(self, animation):
        if animation == self.current_animation:
            return

        self.current_animation = animation
        self.animation_time = 0

    def update_ground_position(self):
        center_x = self.position.x + self.width / 2

        tile_x = int(
            center_x // self.world.tile_size
        )

        surface_y = self.world.get_surface_y(tile_x)

        self.position.y = surface_y - self.height

        self.rect.x = round(self.position.x)
        self.rect.y = round(self.position.y)

    def take_damage(self, amount, direction=0):
        if self.dead:
            return False

        self.health -= amount
        self.hit_flash = 0.24
        self.knockback_timer = 0.2
        self.velocity_x = (1 if direction >= 0 else -1) * 230

        if self.health <= 0:
            self.health = 0
            self.dead = True
            self.death_timer = self.death_duration

        return True

    def roll_drops(self):
        if self.drops_rolled:
            return []

        self.drops_rolled = True
        drops = [("fiber", random.randint(1, 2))]

        if random.random() < 0.65:
            drops.append(("bone", random.randint(1, 2)))

        if self.night and random.random() < 0.25:
            drops.append(("berry", 1))

        return drops

    def update(self, player, delta_time):
        self.animation_time += delta_time
        self.attack_timer = max(0.0, self.attack_timer - delta_time)
        self.hit_flash = max(0.0, self.hit_flash - delta_time)

        if self.dead:
            self.death_timer = max(0.0, self.death_timer - delta_time)
            return

        if self.knockback_timer > 0:
            self.knockback_timer -= delta_time
            self.position.x += self.velocity_x * delta_time
            self.update_ground_position()
            self.set_animation("hit")
            return

        player_center = (
            player.position.x + player.rect.width / 2
        )

        zombie_center = (
            self.position.x + self.width / 2
        )

        distance = player_center - zombie_center
        absolute_distance = abs(distance)

        if absolute_distance > self.stop_distance:
            self.velocity_x = (
                self.speed
                if distance > 0
                else -self.speed
            )

            self.facing_right = distance > 0

            self.position.x += (
                self.velocity_x * delta_time
            )

            self.set_animation("walk")

        else:
            self.velocity_x = 0
            self.facing_right = distance > 0
            self.set_animation("idle")

        if (
            absolute_distance <= self.attack_range
            and self.attack_timer <= 0
            and player.is_alive
        ):
            if player.take_damage(self.attack_damage, source="zombie"):
                self.attack_timer = self.attack_cooldown

        self.update_ground_position()

    def draw(self, surface, camera, delta_time=1 / 60):
        screen_rect = camera.apply(self.rect)

        if self.dead:
            frames = self.sprites.get("hit", []) or self.sprites.get("idle", [])

            if frames:
                image = frames[0].copy()
                image.set_alpha(int(255 * max(0.0, self.death_timer / self.death_duration)))
                surface.blit(image, screen_rect.topleft)

            return

        frames = self.sprites.get(
            self.current_animation,
            [],
        )

        if not frames:
            frames = self.sprites.get("idle", [])

        if frames:
            frame_index = 0

            if len(frames) > 1:
                frame_index = int(
                    self.animation_time / self.animation_speed
                ) % len(frames)

            image = frames[frame_index]

            if not self.facing_right:
                image = pygame.transform.flip(
                    image,
                    True,
                    False,
                )

            if self.hit_flash > 0:
                image = image.copy()
                image.fill((150, 30, 30, 0), special_flags=pygame.BLEND_RGBA_ADD)

            surface.blit(
                image,
                screen_rect.topleft,
            )

        else:
            pygame.draw.rect(
                surface,
                self.color,
                screen_rect,
                border_radius=8,
            )

            eye_y = screen_rect.y + 15

            pygame.draw.circle(
                surface,
                (220, 60, 55),
                (screen_rect.x + 14, eye_y),
                4,
            )

            pygame.draw.circle(
                surface,
                (220, 60, 55),
                (screen_rect.x + 32, eye_y),
                4,
            )

        if self.health < self.max_health:
            bar = pygame.Rect(screen_rect.x + 4, screen_rect.y - 10, screen_rect.width - 8, 6)
            pygame.draw.rect(surface, (34, 18, 20), bar, border_radius=3)
            fill = pygame.Rect(bar.x, bar.y, int(bar.width * (self.health / self.max_health)), bar.height)
            pygame.draw.rect(surface, (213, 52, 62), fill, border_radius=3)
