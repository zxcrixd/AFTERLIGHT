"""In-game HUD: hearts, bars, clock, hotbar and interaction prompts."""

import math

import pygame

from game.items import FIST_DAMAGE, FIST_REACH, ITEMS, get_icon
from game.localization import tr
from game.paths import resource_path
from game.ui import ACCENT, BLUE, MUTED, ORANGE, PANEL, TEXT


TILES_FOLDER = resource_path("assets", "images", "tiles")


class HUD:
    def __init__(self, game):
        self.game = game
        self.heart_full = self._load_heart("hud_heart.png")
        self.heart_half = self._load_heart("hud_heart_half.png")
        self.heart_empty = self._load_heart("hud_heart_empty.png")
        self.pulse = 0.0

    def _load_heart(self, filename):
        path = TILES_FOLDER / filename

        if not path.exists():
            return None

        try:
            image = pygame.image.load(str(path)).convert_alpha()
            return pygame.transform.smoothscale(image, (27, 27))
        except pygame.error:
            return None

    # -- pieces ----------------------------------------------------------
    def draw_hearts(self, surface, x, y, health, max_health=100):
        hearts = 10
        per_heart = max_health / hearts

        for index in range(hearts):
            value = health - index * per_heart

            if value >= per_heart:
                image = self.heart_full
            elif value >= per_heart / 2:
                image = self.heart_half
            else:
                image = self.heart_empty

            position = (x + index * 29, y)

            if image is not None:
                surface.blit(image, position)
            else:
                color = ACCENT if value >= per_heart / 2 else (60, 42, 48)
                pygame.draw.circle(surface, color, (position[0] + 13, position[1] + 13), 11)

    def draw_stat_bar(self, surface, x, y, width, label, value, maximum, color):
        ratio = max(0.0, min(1.0, value / maximum))

        from game.ui import draw_bar, draw_text, get_font

        draw_text(surface, label, 16, (x, y), MUTED, bold=True)

        rendered = get_font(16, True).render(f"{int(round(value))}", True, TEXT)
        surface.blit(rendered, (x + width - rendered.get_width(), y))

        draw_bar(
            surface,
            pygame.Rect(x, y + 20, width, 10),
            ratio,
            color,
            background=(38, 41, 54),
            border=(58, 62, 80),
        )

    def draw_clock(self, surface, width):
        from game.ui import draw_panel, draw_text

        cycle = self.game.daynight
        panel = pygame.Rect(width - 292, 16, 274, 92)
        draw_panel(surface, panel, alpha=205, radius=14)

        icon_center = (panel.x + 38, panel.y + 36)

        if cycle.is_night:
            pygame.draw.circle(surface, (222, 226, 240), icon_center, 13)
            pygame.draw.circle(surface, PANEL, (icon_center[0] + 6, icon_center[1] - 4), 12)
            pygame.draw.circle(surface, (222, 226, 240), (icon_center[0] + 15, icon_center[1] - 15), 2)
        else:
            pygame.draw.circle(surface, (248, 205, 89), icon_center, 12)

            for index in range(8):
                angle = index * math.tau / 8
                start = (
                    icon_center[0] + math.cos(angle) * 16,
                    icon_center[1] + math.sin(angle) * 16,
                )
                end = (
                    icon_center[0] + math.cos(angle) * 21,
                    icon_center[1] + math.sin(angle) * 21,
                )
                pygame.draw.line(surface, (248, 205, 89), start, end, 2)

        draw_text(
            surface,
            cycle.clock_text,
            28,
            (panel.x + 64, panel.y + 16),
            TEXT,
            bold=True,
        )
        draw_text(
            surface,
            f"{tr(self.game.language, 'day', day=cycle.day)}  ·  {cycle.phase_name(self.game.language)}",
            17,
            (panel.x + 66, panel.y + 51),
            MUTED,
        )
        draw_text(
            surface,
            tr(self.game.language, "kills", kills=self.game.kills),
            16,
            (panel.x + 18, panel.y + 70),
            (236, 140, 140),
        )

    def draw_hotbar(self, surface, width, height):
        from game.ui import draw_icon_box, draw_panel, draw_text

        inventory = self.game.player.inventory
        size = 60
        gap = 8
        total_width = size * 6 + gap * 5
        start_x = (width - total_width) // 2
        y = height - size - 22

        draw_panel(
            surface,
            pygame.Rect(start_x - 10, y - 10, total_width + 20, size + 20),
            alpha=200,
            radius=14,
        )

        for index in range(6):
            slot = inventory.slots[index]
            rect = pygame.Rect(start_x + index * (size + gap), y, size, size)

            draw_icon_box(
                surface,
                rect,
                slot.item_id if not slot.empty else "",
                slot.count,
                selected=(index == inventory.selected),
            )

            draw_text(
                surface,
                str(index + 1),
                14,
                (rect.x + 5, rect.y + 2),
                MUTED,
                bold=True,
            )

        selected_item = ITEMS.get(inventory.selected_item)
        item_label = (
            selected_item.name(self.game.language)
            if selected_item
            else ("Кулаки" if self.game.language == "ru" else "Fists")
        )
        draw_text(
            surface,
            item_label,
            20,
            (width // 2, y - 32),
            TEXT,
            center=True,
            bold=True,
            shadow=True,
        )

    def draw_prompt(self, surface, width, height):
        from game.ui import draw_panel, draw_text

        prompt = self.game.interaction_prompt

        if not prompt:
            return

        y = height - 112
        font_size = 20
        from game.ui import get_font

        font = get_font(font_size, True)
        rendered = font.render(prompt, True, (255, 238, 186))
        rect = rendered.get_rect(center=(width // 2, y))
        panel_rect = rect.inflate(28, 14)

        draw_panel(
            surface,
            panel_rect,
            color=(24, 24, 30),
            border=(150, 124, 66),
            radius=10,
            alpha=218,
        )
        surface.blit(rendered, rect)

    def draw_hurt_overlay(self, surface):
        player = self.game.player
        width, height = surface.get_size()

        if player.hurt_flash > 0:
            alpha = int(110 * min(1.0, player.hurt_flash / 0.4))
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((180, 20, 30, alpha))
            surface.blit(overlay, (0, 0))

        if player.health <= 30 and player.health > 0:
            self.pulse += 0.05
            alpha = int(35 + 20 * math.sin(self.pulse))
            border = 26
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.rect(
                overlay,
                (170, 18, 30, alpha),
                overlay.get_rect(),
                width=border,
                border_radius=18,
            )
            surface.blit(overlay, (0, 0))

    def draw(self, surface, delta_time):
        width, height = surface.get_size()
        player = self.game.player
        language = self.game.language

        from game.ui import draw_panel, draw_text

        # Stats panel
        panel = pygame.Rect(16, 16, 366, 132)
        draw_panel(surface, panel, alpha=205, radius=14)

        self.draw_hearts(surface, panel.x + 18, panel.y + 14, player.health, player.max_health)

        from game.ui import get_font

        health_text = f"{int(round(player.health))}/{int(player.max_health)}"
        rendered = get_font(16, True).render(health_text, True, MUTED)
        surface.blit(rendered, (panel.right - 18 - rendered.get_width(), panel.y + 16))

        self.draw_stat_bar(
            surface,
            panel.x + 18,
            panel.y + 52,
            300,
            tr(language, "hunger"),
            player.hunger,
            player.max_hunger,
            ORANGE,
        )
        self.draw_stat_bar(
            surface,
            panel.x + 18,
            panel.y + 94,
            300,
            tr(language, "stamina"),
            player.stamina,
            player.max_stamina,
            BLUE,
        )

        self.draw_clock(surface, width)
        self.draw_hotbar(surface, width, height)
        self.draw_prompt(surface, width, height)

        draw_text(
            surface,
            tr(language, "controls_hint"),
            16,
            (18, height - 26),
            (137, 142, 159),
        )

        self.game.notifications.draw(surface, width // 2, 118)
        self.draw_hurt_overlay(surface)
