"""Full screen overlays: inventory/crafting, pause and game over."""

import pygame

from game.crafting import RECIPES, can_craft, format_cost
from game.items import ITEMS, get_icon
from game.localization import tr
from game.ui import (
    ACCENT,
    ACCENT_LIGHT,
    BORDER,
    GREEN,
    MUTED,
    ORANGE,
    PANEL,
    SLOT_HOVER,
    TEXT,
    UIButton,
    draw_icon_box,
    draw_panel,
    draw_text,
    get_font,
)


def _screen_size(game):
    return game.screen.get_size()


class InventoryOverlay:
    def __init__(self, game):
        self.game = game
        self.panel_rect = pygame.Rect(0, 0, 10, 10)
        self.slot_rects = []
        self.recipe_rects = []
        self.close_rect = pygame.Rect(0, 0, 10, 10)
        self.hovered_slot = None
        self.hovered_recipe = None
        self.recipe_scroll = 0
        self.max_visible_recipes = 8

    # -- layout ----------------------------------------------------------
    def _layout(self):
        width, height = _screen_size(self.game)

        panel_width = min(1140, width - 60)
        panel_height = min(650, height - 50)
        self.panel_rect = pygame.Rect(
            (width - panel_width) // 2,
            (height - panel_height) // 2,
            panel_width,
            panel_height,
        )

        slot_size = 60
        gap = 8
        grid_x = self.panel_rect.x + 30
        grid_y = self.panel_rect.y + 92

        self.slot_rects = []

        for index in range(24):
            column = index % 6
            row = index // 6
            self.slot_rects.append(
                pygame.Rect(
                    grid_x + column * (slot_size + gap),
                    grid_y + row * (slot_size + gap),
                    slot_size,
                    slot_size,
                )
            )

        recipes_x = self.panel_rect.x + 490
        recipes_y = self.panel_rect.y + 92
        recipes_width = self.panel_rect.right - recipes_x - 30

        self.max_visible_recipes = max(
            1,
            (self.panel_rect.bottom - recipes_y - 64) // 64,
        )

        max_scroll = max(0, len(RECIPES) - self.max_visible_recipes)
        self.recipe_scroll = min(max(0, self.recipe_scroll), max_scroll)

        self.recipe_rects = []

        for index in range(
            self.recipe_scroll,
            min(len(RECIPES), self.recipe_scroll + self.max_visible_recipes),
        ):
            row = index - self.recipe_scroll
            self.recipe_rects.append(
                pygame.Rect(
                    recipes_x,
                    recipes_y + row * 64,
                    recipes_width,
                    56,
                )
            )

        self.close_rect = pygame.Rect(
            self.panel_rect.right - 142,
            self.panel_rect.bottom - 48,
            112,
            34,
        )

    # -- input -----------------------------------------------------------
    def handle_event(self, event):
        self._layout()

        if event.type == pygame.MOUSEWHEEL:
            if self.panel_rect.collidepoint(pygame.mouse.get_pos()):
                max_scroll = max(0, len(RECIPES) - self.max_visible_recipes)
                self.recipe_scroll = min(
                    max_scroll,
                    max(0, self.recipe_scroll - event.y),
                )
                return True

            return False

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        mouse = event.pos

        if self.close_rect.collidepoint(mouse):
            self.game.close_overlay()
            return True

        for index, rect in enumerate(self.slot_rects):
            if not rect.collidepoint(mouse):
                continue

            inventory = self.game.player.inventory

            if index < inventory.HOTBAR_SIZE:
                inventory.select(index)
                self.game.play_sound("select")
            else:
                if inventory.swap_with_selected(index):
                    self.game.play_sound("select")

            return True

        for index, rect in enumerate(self.recipe_rects):
            if not rect.collidepoint(mouse):
                continue

            recipe_index = self.recipe_scroll + index

            if recipe_index < len(RECIPES):
                self.game.craft_recipe(RECIPES[recipe_index])

            return True

        return False

    # -- drawing ---------------------------------------------------------
    def _draw_item_info(self, surface, rect, item_id):
        draw_panel(
            surface,
            rect,
            color=(23, 26, 36),
            border=(58, 63, 82),
            radius=12,
            alpha=220,
        )

        if not item_id or item_id not in ITEMS:
            draw_text(
                surface,
                tr(self.game.language, "nothing_selected"),
                18,
                (rect.x + 18, rect.y + 18),
                MUTED,
            )
            return

        item = ITEMS[item_id]
        icon = get_icon(item_id, 54)
        surface.blit(icon, (rect.x + 16, rect.y + 14))

        draw_text(
            surface,
            item.name(self.game.language),
            23,
            (rect.x + 82, rect.y + 14),
            TEXT,
            bold=True,
        )

        category_key = f"category_{item.category}"
        draw_text(
            surface,
            tr(self.game.language, category_key),
            15,
            (rect.x + 82, rect.y + 42),
            ACCENT_LIGHT,
        )

        description = item.description_ru if self.game.language == "ru" else item.description_en
        description_font = get_font(16)
        words = description.split()
        lines = []
        current = ""

        for word in words:
            candidate = (current + " " + word).strip()

            if description_font.size(candidate)[0] > rect.width - 36:
                if current:
                    lines.append(current)
                current = word
            else:
                current = candidate

        if current:
            lines.append(current)

        for index, line in enumerate(lines[:3]):
            draw_text(
                surface,
                line,
                16,
                (rect.x + 18, rect.y + 76 + index * 21),
                (200, 203, 216),
            )

        stats = []

        if item.damage:
            stats.append(f"DMG {int(item.damage)}")
        if item.heal:
            stats.append(f"HP +{int(item.heal)}")
        if item.hunger:
            stats.append(f"FOOD +{int(item.hunger)}")
        if item.light:
            stats.append(f"LIGHT {int(item.light)}")
        if item.tool:
            stats.append(item.tool.upper())

        if stats:
            stats_text = "   ".join(stats)
            stats_font = get_font(15, True)
            rendered = stats_font.render(stats_text, True, ORANGE)
            surface.blit(
                rendered,
                (rect.right - 18 - rendered.get_width(), rect.y + 16),
            )

    def draw(self, surface):
        self._layout()
        mouse = pygame.mouse.get_pos()
        language = self.game.language
        inventory = self.game.player.inventory

        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((4, 5, 9, 172))
        surface.blit(shade, (0, 0))

        draw_panel(
            surface,
            self.panel_rect,
            color=PANEL,
            border=BORDER,
            radius=18,
            alpha=246,
        )

        draw_text(
            surface,
            tr(language, "inventory_title"),
            34,
            (self.panel_rect.x + 30, self.panel_rect.y + 24),
            TEXT,
            bold=True,
        )

        draw_text(
            surface,
            tr(language, "inventory"),
            21,
            (self.panel_rect.x + 30, self.panel_rect.y + 66),
            ACCENT_LIGHT,
            bold=True,
        )
        draw_text(
            surface,
            tr(language, "crafting"),
            21,
            (self.panel_rect.x + 490, self.panel_rect.y + 66),
            ACCENT_LIGHT,
            bold=True,
        )

        # Inventory grid
        self.hovered_slot = None

        for index, rect in enumerate(self.slot_rects):
            slot = inventory.slots[index]
            hovered = rect.collidepoint(mouse)

            if hovered:
                self.hovered_slot = index

            draw_icon_box(
                surface,
                rect,
                slot.item_id if not slot.empty else "",
                slot.count,
                selected=(index == inventory.selected),
                hovered=hovered,
            )

            if index < inventory.HOTBAR_SIZE:
                draw_text(
                    surface,
                    str(index + 1),
                    13,
                    (rect.x + 5, rect.y + 2),
                    MUTED,
                    bold=True,
                )

        info_rect = pygame.Rect(
            self.panel_rect.x + 30,
            self.panel_rect.y + 360,
            412,
            170,
        )

        info_item = inventory.selected_item

        if self.hovered_slot is not None:
            hovered_slot = inventory.slots[self.hovered_slot]
            if not hovered_slot.empty:
                info_item = hovered_slot.item_id

        self._draw_item_info(surface, info_rect, info_item)

        draw_text(
            surface,
            tr(language, "inventory_hint"),
            15,
            (self.panel_rect.x + 30, info_rect.bottom + 12),
            MUTED,
        )

        # Recipes
        self.hovered_recipe = None
        visible_recipes = RECIPES[
            self.recipe_scroll : self.recipe_scroll + self.max_visible_recipes
        ]

        for index, recipe in enumerate(visible_recipes):
            rect = self.recipe_rects[index]
            affordable = can_craft(inventory, recipe)
            hovered = rect.collidepoint(mouse)

            if hovered:
                self.hovered_recipe = index

            if hovered:
                pygame.draw.rect(surface, SLOT_HOVER, rect, border_radius=10)
            else:
                pygame.draw.rect(surface, (26, 29, 40), rect, border_radius=10)

            pygame.draw.rect(
                surface,
                (54, 59, 77) if affordable else (44, 47, 60),
                rect,
                width=1,
                border_radius=10,
            )

            icon = get_icon(recipe.result, 44)
            surface.blit(icon, (rect.x + 8, rect.y + 6))

            draw_text(
                surface,
                recipe.name(language),
                19,
                (rect.x + 60, rect.y + 5),
                TEXT if affordable else (176, 179, 192),
                bold=True,
            )

            draw_text(
                surface,
                format_cost(recipe, language),
                14,
                (rect.x + 60, rect.y + 31),
                GREEN if affordable else (198, 102, 108),
            )

            button_rect = pygame.Rect(rect.right - 112, rect.y + 11, 100, 34)
            button_hovered = button_rect.collidepoint(mouse)

            if affordable:
                color = ACCENT if button_hovered else (144, 35, 45)
                border = ACCENT_LIGHT
            else:
                color = (47, 49, 60)
                border = (65, 68, 82)

            pygame.draw.rect(surface, color, button_rect, border_radius=8)
            pygame.draw.rect(surface, border, button_rect, width=1, border_radius=8)
            draw_text(
                surface,
                tr(language, "craft"),
                15,
                button_rect.center,
                TEXT if affordable else (124, 127, 140),
                center=True,
                bold=True,
            )

        draw_text(
            surface,
            tr(language, "recipe_hint"),
            15,
            (self.panel_rect.x + 490, self.panel_rect.bottom - 42),
            MUTED,
        )

        if len(RECIPES) > self.max_visible_recipes:
            first = self.recipe_scroll + 1
            last = min(
                len(RECIPES),
                self.recipe_scroll + self.max_visible_recipes,
            )
            draw_text(
                surface,
                tr(
                    language,
                    "recipe_scroll_hint",
                    first=first,
                    last=last,
                    total=len(RECIPES),
                ),
                14,
                (self.panel_rect.right - 200, self.panel_rect.bottom - 42),
                MUTED,
            )

        # Close button
        close_hovered = self.close_rect.collidepoint(mouse)
        pygame.draw.rect(
            surface,
            SLOT_HOVER if close_hovered else (34, 37, 49),
            self.close_rect,
            border_radius=8,
        )
        pygame.draw.rect(
            surface,
            BORDER,
            self.close_rect,
            width=1,
            border_radius=8,
        )
        draw_text(
            surface,
            tr(language, "close"),
            16,
            self.close_rect.center,
            TEXT,
            center=True,
            bold=True,
        )


class PauseOverlay:
    def __init__(self, game):
        self.game = game
        self.panel_rect = pygame.Rect(0, 0, 420, 430)
        self.buttons = []

    def _layout(self):
        width, height = _screen_size(self.game)
        self.panel_rect = pygame.Rect(0, 0, 420, 430)
        self.panel_rect.center = (width // 2, height // 2)

        language = self.game.language
        labels = (
            ("resume", tr(language, "resume"), True),
            ("save", tr(language, "save"), False),
            ("menu", tr(language, "main_menu"), False),
            ("quit", tr(language, "exit_game"), False),
        )

        self.buttons = []

        for index, (key, label, primary) in enumerate(labels):
            self.buttons.append(
                UIButton(
                    key,
                    label,
                    pygame.Rect(
                        self.panel_rect.x + 50,
                        self.panel_rect.y + 118 + index * 64,
                        self.panel_rect.width - 100,
                        50,
                    ),
                    primary=primary,
                )
            )

    def handle_event(self, event):
        self._layout()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "resume"

            if event.key == pygame.K_s:
                return "save"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.hovered(event.pos):
                    return button.key

        return None

    def draw(self, surface):
        self._layout()
        mouse = pygame.mouse.get_pos()
        language = self.game.language

        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((4, 5, 9, 178))
        surface.blit(shade, (0, 0))

        draw_panel(surface, self.panel_rect, alpha=246, radius=18)

        draw_text(
            surface,
            tr(language, "paused"),
            38,
            (self.panel_rect.centerx, self.panel_rect.y + 50),
            ACCENT_LIGHT,
            center=True,
            bold=True,
        )

        for button in self.buttons:
            button.draw(surface, mouse, font_size=23)

        draw_text(
            surface,
            tr(
                language,
                "seed_short",
                seed=getattr(self.game.world, "seed", "?"),
            ),
            14,
            (self.panel_rect.centerx, self.panel_rect.bottom - 68),
            MUTED,
            center=True,
        )

        if self.game.mods.mod_count:
            draw_text(
                surface,
                tr(
                    language,
                    "mods_count",
                    count=self.game.mods.mod_count,
                ),
                14,
                (self.panel_rect.centerx, self.panel_rect.bottom - 46),
                MUTED,
                center=True,
            )

        draw_text(
            surface,
            tr(language, "pause_hint"),
            15,
            (self.panel_rect.centerx, self.panel_rect.bottom - 24),
            MUTED,
            center=True,
        )


class GameOverOverlay:
    def __init__(self, game):
        self.game = game
        self.panel_rect = pygame.Rect(0, 0, 560, 420)
        self.buttons = []

    def _layout(self):
        width, height = _screen_size(self.game)
        self.panel_rect = pygame.Rect(0, 0, 560, 420)
        self.panel_rect.center = (width // 2, height // 2)

        language = self.game.language

        self.buttons = [
            UIButton(
                "restart",
                tr(language, "restart"),
                pygame.Rect(self.panel_rect.x + 60, self.panel_rect.y + 286, 210, 52),
                primary=True,
            ),
            UIButton(
                "menu",
                tr(language, "to_menu"),
                pygame.Rect(self.panel_rect.x + 290, self.panel_rect.y + 286, 210, 52),
            ),
        ]

    def handle_event(self, event):
        self._layout()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.hovered(event.pos):
                    return button.key

        return None

    def draw(self, surface):
        self._layout()
        mouse = pygame.mouse.get_pos()
        language = self.game.language

        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((22, 4, 7, 185))
        surface.blit(shade, (0, 0))

        draw_panel(
            surface,
            self.panel_rect,
            color=(20, 14, 18),
            border=(120, 38, 48),
            alpha=248,
            radius=18,
        )

        draw_text(
            surface,
            tr(language, "game_over"),
            52,
            (self.panel_rect.centerx, self.panel_rect.y + 72),
            (236, 63, 73),
            center=True,
            bold=True,
            shadow=True,
        )

        draw_text(
            surface,
            tr(language, "survived", days=self.game.daynight.day),
            23,
            (self.panel_rect.centerx, self.panel_rect.y + 146),
            TEXT,
            center=True,
        )

        draw_text(
            surface,
            tr(language, "final_kills", kills=self.game.kills),
            23,
            (self.panel_rect.centerx, self.panel_rect.y + 182),
            TEXT,
            center=True,
        )

        draw_text(
            surface,
            tr(language, "death_hint"),
            17,
            (self.panel_rect.centerx, self.panel_rect.y + 232),
            MUTED,
            center=True,
        )

        for button in self.buttons:
            button.draw(surface, mouse, font_size=22)
