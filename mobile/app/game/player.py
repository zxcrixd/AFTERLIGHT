"""The player character: movement, survival stats, combat and animation."""

import math
from pathlib import Path

import pygame

from game.input_map import event_key
from game.items import FIST_DAMAGE, FIST_REACH, ITEMS, Inventory
from settings import PLAYER_SPEED


class Player:
    def __init__(self, x, y):
        self.position = pygame.Vector2(x, y)

        self.width = 48
        self.height = 64
        self.crouch_height = 40

        self.speed = PLAYER_SPEED
        self.crouch_speed = PLAYER_SPEED * 0.5
        self.sprint_multiplier = 1.48

        self.velocity_x = 0
        self.velocity_y = 0

        self.on_ground = False
        self.facing_right = True
        self.is_crouching = False
        self.sprinting = False

        self.rect = pygame.Rect(
            x, y, self.width, self.height
        )

        self.color = (190, 35, 45)
        self.pressed_keys = set()

        # Survival stats
        self.max_health = 100.0
        self.health = self.max_health
        self.max_hunger = 100.0
        self.hunger = self.max_hunger
        self.max_stamina = 100.0
        self.stamina = self.max_stamina

        self.hunger_drain = 0.4
        self.starvation_damage = 2.6
        self.stamina_drain = 27.0
        self.stamina_regen = 19.0
        self.health_regen = 0.35

        # Combat
        self.attack_timer = 0.0
        self.attack_duration = 0.28
        self.attack_cooldown_timer = 0.0
        self.attack_cooldown = 0.42
        self.invulnerable_timer = 0.0
        self.hurt_flash = 0.0
        self.damage_hook = None

        self.animation_time = 0
        self.animation_speed = 0.5
        self.current_animation = "idle"

        self.jump_requested = False

        self.inventory = Inventory()

        self.player_folder = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "images"
            / "player"
        )

        self.sprites = {}
        self.crouch_sprite = None

        self.load_sprites()

    # -- sprites ---------------------------------------------------------
    def load_image(self, filename, size=None):
        path = self.player_folder / filename

        if not path.exists():
            return None

        try:
            image = pygame.image.load(
                str(path)
            ).convert_alpha()

            if size is not None:
                image = pygame.transform.scale(
                    image,
                    size,
                )

            return image

        except pygame.error as error:
            print(f"Player sprite error: {error}")
            return None

    def load_sprites(self):
        files = {
            "idle": ["character_beige_idle.png"],
            "walk": [
                "character_beige_walk_a.png",
                "character_beige_walk_b.png",
            ],
            "jump": ["character_beige_jump.png"],
        }

        for animation, filenames in files.items():
            self.sprites[animation] = []

            for filename in filenames:
                image = self.load_image(
                    filename,
                    (self.width, self.height),
                )

                if image is not None:
                    self.sprites[animation].append(image)

        self.crouch_sprite = self.load_image(
            "character_beige_duck.png",
            (self.width, self.crouch_height),
        )

        if self.crouch_sprite is None:
            idle_frames = self.sprites.get("idle", [])

            if idle_frames:
                self.crouch_sprite = pygame.transform.scale(
                    idle_frames[0],
                    (self.width, self.crouch_height),
                )

    # -- input -----------------------------------------------------------
    def handle_event(self, event):
        key = event_key(event)

        if event.type == pygame.KEYDOWN:
            self.pressed_keys.add(key)

            if key == pygame.K_SPACE:
                self.jump_requested = True

        elif event.type == pygame.KEYUP:
            self.pressed_keys.discard(key)

    def get_direction(self):
        direction = 0

        if (
            pygame.K_a in self.pressed_keys
            or pygame.K_LEFT in self.pressed_keys
        ):
            direction -= 1

        if (
            pygame.K_d in self.pressed_keys
            or pygame.K_RIGHT in self.pressed_keys
        ):
            direction += 1

        if direction:
            self.facing_right = direction > 0

        return direction

    def update_crouch(self):
        should_crouch = (
            pygame.K_c in self.pressed_keys
            and self.on_ground
        )

        if should_crouch == self.is_crouching:
            return

        bottom = self.rect.bottom

        self.is_crouching = should_crouch

        if self.is_crouching:
            self.rect.height = self.crouch_height
        else:
            self.rect.height = self.height

        self.rect.bottom = bottom
        self.position.y = self.rect.y

    # -- movement --------------------------------------------------------
    def handle_movement(self, delta_time):
        self.update_crouch()

        direction = self.get_direction()
        moving = direction != 0

        wants_sprint = (
            (pygame.K_LSHIFT in self.pressed_keys or pygame.K_RSHIFT in self.pressed_keys)
            and moving
            and not self.is_crouching
            and self.stamina > 1.0
        )

        self.sprinting = wants_sprint

        current_speed = (
            self.crouch_speed
            if self.is_crouching
            else self.speed
        )

        if self.sprinting:
            current_speed *= self.sprint_multiplier

        if self.stamina <= 0:
            current_speed *= 0.72

        self.velocity_x = direction * current_speed

        self.position.x += (
            self.velocity_x * delta_time
        )

        # The world starts at x = 0; keep the player inside the visible map.
        self.position.x = max(0.0, self.position.x)
        self.rect.x = round(self.position.x)

        self.update_animation(direction)

    def update_stats(self, delta_time):
        self.attack_timer = max(0.0, self.attack_timer - delta_time)
        self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - delta_time)
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - delta_time)
        self.hurt_flash = max(0.0, self.hurt_flash - delta_time)

        self.hunger -= self.hunger_drain * delta_time

        if self.hunger <= 0:
            self.hunger = 0
            self.health -= self.starvation_damage * delta_time
        elif self.hunger > 65 and 0 < self.health < self.max_health:
            self.health += self.health_regen * delta_time

        if self.sprinting:
            self.stamina -= self.stamina_drain * delta_time
        else:
            self.stamina += self.stamina_regen * delta_time

        self.stamina = max(0.0, min(self.max_stamina, self.stamina))
        self.health = max(0.0, min(self.max_health, self.health))

    def update_animation(self, direction):
        if self.is_crouching:
            animation = "crouch"
        elif not self.on_ground:
            animation = "jump"
        elif direction:
            animation = "walk"
        else:
            animation = "idle"

        if animation != self.current_animation:
            self.current_animation = animation
            self.animation_time = 0

    # -- survival / combat ----------------------------------------------
    @property
    def is_alive(self):
        return self.health > 0

    def equipped_weapon(self):
        item = ITEMS.get(self.inventory.selected_item)

        if item is not None and item.damage > 0:
            return item.damage, item.reach, item.id

        return FIST_DAMAGE, FIST_REACH, ""

    def can_attack(self):
        return self.is_alive and self.attack_cooldown_timer <= 0

    def start_attack(self):
        if not self.can_attack():
            return False

        self.attack_timer = self.attack_duration
        self.attack_cooldown_timer = self.attack_cooldown
        self.stamina = max(0.0, self.stamina - 4.0)
        return True

    def take_damage(self, amount, source="unknown"):
        if self.invulnerable_timer > 0 or not self.is_alive:
            return False

        if self.damage_hook is not None:
            amount = self.damage_hook(self, amount, source)

        self.health = max(0.0, self.health - max(0.0, amount))
        self.invulnerable_timer = 0.9
        self.hurt_flash = 0.42
        return True

    def heal(self, amount):
        before = self.health
        self.health = min(self.max_health, self.health + amount)
        return self.health - before

    def feed(self, amount):
        before = self.hunger
        self.hunger = min(self.max_hunger, self.hunger + amount)
        return self.hunger - before

    # -- drawing ---------------------------------------------------------
    def draw(self, surface, camera, delta_time=1 / 60):
        self.animation_time += delta_time

        screen_rect = camera.apply(self.rect)

        image = None

        if self.is_crouching and self.crouch_sprite is not None:
            image = self.crouch_sprite
        else:
            frames = self.sprites.get(
                self.current_animation,
                [],
            )

            if frames:
                frame_index = 0

                if len(frames) > 1:
                    frame_index = int(
                        self.animation_time / self.animation_speed
                    ) % len(frames)

                image = frames[frame_index]

        if image is not None:
            if not self.facing_right:
                image = pygame.transform.flip(
                    image,
                    True,
                    False,
                )

            if self.hurt_flash > 0:
                image = image.copy()
                image.fill((120, 20, 20, 0), special_flags=pygame.BLEND_RGBA_ADD)

            # Blink while invulnerable.
            if self.invulnerable_timer > 0 and int(self.invulnerable_timer * 14) % 2 == 0:
                image = image.copy()
                image.set_alpha(130)

            surface.blit(
                image,
                screen_rect.topleft,
            )

        else:
            pygame.draw.rect(
                surface,
                self.color,
                screen_rect,
            )

        if self.attack_timer > 0:
            self.draw_attack(surface, screen_rect)

    def draw_attack(self, surface, screen_rect):
        _, reach, item_id = self.equipped_weapon()

        progress = 1.0 - self.attack_timer / self.attack_duration
        center = (
            screen_rect.centerx + (screen_rect.width // 2 if self.facing_right else -screen_rect.width // 2),
            screen_rect.centery,
        )

        color = (255, 244, 203)

        if item_id in ("stone_spear", "bone_spear"):
            color = (206, 226, 255)
        elif item_id in ("stone_axe", "stone_pickaxe"):
            color = (224, 224, 228)

        slash = pygame.Surface((int(reach * 2.4), int(reach * 2.4)), pygame.SRCALPHA)
        local_center = (slash.get_width() // 2, slash.get_height() // 2)

        start_angle = -0.95 + progress * 0.7
        end_angle = start_angle + 1.25

        if not self.facing_right:
            start_angle = math.pi - end_angle
            end_angle = math.pi - (-0.95 + progress * 0.7)

        rect = pygame.Rect(0, 0, int(reach * 1.9), int(reach * 1.9))
        rect.center = local_center

        alpha = int(210 * (1.0 - progress))
        pygame.draw.arc(
            slash,
            (*color, alpha),
            rect,
            start_angle,
            end_angle,
            5,
        )
        surface.blit(slash, (center[0] - local_center[0], center[1] - local_center[1]))
