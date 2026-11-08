
import pygame


class Physics:
    def __init__(self):
        self.gravity = 1500
        self.max_fall_speed = 900
        self.jump_power = 620

    def update(self, player, world, delta_time):
        # Прыжок
        if player.jump_requested:
            if player.on_ground:
                player.velocity_y = -self.jump_power
                player.on_ground = False

            player.jump_requested = False

        # Горизонтальные столкновения
        self.resolve_horizontal(player, world)

        # Гравитация
        player.velocity_y += self.gravity * delta_time
        player.velocity_y = min(
            player.velocity_y,
            self.max_fall_speed,
        )

        # Вертикальное перемещение
        player.position.y += (
            player.velocity_y * delta_time
        )

        player.rect.y = round(player.position.y)
        player.on_ground = False

        # Вертикальные столкновения
        if player.velocity_y >= 0:
            self.resolve_vertical(player, world)

    def resolve_horizontal(self, player, world):
        if player.velocity_x == 0:
            return

        tile_size = world.tile_size

        first_column = player.rect.left // tile_size
        last_column = player.rect.right // tile_size

        first_row = player.rect.top // tile_size
        last_row = (player.rect.bottom - 1) // tile_size

        for tile_x in range(first_column, last_column + 1):
            for tile_y in range(first_row, last_row + 1):
                if not world.is_solid(tile_x, tile_y):
                    continue

                tile_rect = pygame.Rect(
                    tile_x * tile_size,
                    tile_y * tile_size,
                    tile_size,
                    tile_size,
                )

                if player.rect.colliderect(tile_rect):
                    if player.velocity_x > 0:
                        player.rect.right = tile_rect.left
                    else:
                        player.rect.left = tile_rect.right

                    player.position.x = player.rect.x

    def resolve_vertical(self, player, world):
        tile_size = world.tile_size

        first_column = player.rect.left // tile_size
        last_column = (player.rect.right - 1) // tile_size

        first_row = player.rect.top // tile_size
        last_row = player.rect.bottom // tile_size

        for tile_x in range(first_column, last_column + 1):
            for tile_y in range(first_row, last_row + 1):
                if not world.is_solid(tile_x, tile_y):
                    continue

                tile_rect = pygame.Rect(
                    tile_x * tile_size,
                    tile_y * tile_size,
                    tile_size,
                    tile_size,
                )

                if player.rect.colliderect(tile_rect):
                    player.rect.bottom = tile_rect.top
                    player.position.y = player.rect.y
                    player.velocity_y = 0
                    player.on_ground = True
                    return
