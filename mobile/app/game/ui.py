"""Shared UI theme, widgets and notification toasts."""

import pygame


# Palette
TEXT = (238, 239, 244)
MUTED = (154, 160, 178)
DIM = (108, 113, 132)
ACCENT = (220, 48, 60)
ACCENT_LIGHT = (244, 93, 101)
GREEN = (105, 202, 126)
RED = (224, 66, 76)
YELLOW = (241, 199, 91)
ORANGE = (243, 149, 68)
BLUE = (95, 170, 226)
PANEL = (17, 19, 27)
PANEL_LIGHT = (28, 31, 43)
BORDER = (82, 88, 111)
SLOT = (33, 36, 49)
SLOT_HOVER = (51, 56, 74)
SHADOW = (5, 6, 10)

_font_cache = {}


def get_font(size, bold=False):
    key = (size, bold)

    if key in _font_cache:
        return _font_cache[key]

    try:
        font = pygame.font.SysFont("dejavusans,arial", size, bold=bold)
    except pygame.error:
        font = pygame.font.Font(None, size)

    _font_cache[key] = font
    return font


def draw_text(
    surface,
    text,
    size,
    position,
    color=TEXT,
    center=False,
    bold=False,
    shadow=False,
    alpha=255,
):
    font = get_font(size, bold)
    rendered = font.render(str(text), True, color)

    if alpha < 255:
        rendered.set_alpha(alpha)

    rect = rendered.get_rect()

    if center:
        rect.center = position
    else:
        rect.topleft = position

    if shadow:
        shadow_render = font.render(str(text), True, SHADOW)
        shadow_render.set_alpha(alpha)
        surface.blit(shadow_render, (rect.x + 2, rect.y + 2))

    surface.blit(rendered, rect)
    return rect


def draw_panel(
    surface,
    rect,
    color=PANEL,
    border=BORDER,
    radius=16,
    alpha=235,
    border_width=2,
):
    rect = pygame.Rect(rect)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)

    pygame.draw.rect(
        panel,
        (*color, alpha),
        panel.get_rect(),
        border_radius=radius,
    )

    if border is not None:
        pygame.draw.rect(
            panel,
            (*border, min(255, alpha)),
            panel.get_rect(),
            width=border_width,
            border_radius=radius,
        )

    surface.blit(panel, rect.topleft)
    return rect


def draw_bar(surface, rect, ratio, color, background=(38, 41, 54), border=None):
    rect = pygame.Rect(rect)
    ratio = max(0.0, min(1.0, ratio))

    pygame.draw.rect(surface, background, rect, border_radius=rect.height // 2)

    if ratio > 0:
        fill = pygame.Rect(
            rect.x,
            rect.y,
            max(rect.height, int(rect.width * ratio)),
            rect.height,
        )
        pygame.draw.rect(surface, color, fill, border_radius=rect.height // 2)

        highlight = pygame.Rect(
            fill.x + 3,
            fill.y + 2,
            max(0, fill.width - 6),
            max(1, fill.height // 3),
        )
        if highlight.width > 2:
            lighter = tuple(min(255, channel + 35) for channel in color)
            pygame.draw.rect(
                surface,
                lighter,
                highlight,
                border_radius=highlight.height // 2,
            )

    if border is not None:
        pygame.draw.rect(
            surface,
            border,
            rect,
            width=1,
            border_radius=rect.height // 2,
        )


class UIButton:
    def __init__(self, key, label, rect, primary=False):
        self.key = key
        self.label = label
        self.rect = pygame.Rect(rect)
        self.primary = primary

    def hovered(self, mouse_position):
        return self.rect.collidepoint(mouse_position)

    def draw(self, surface, mouse_position, font_size=25):
        hover = self.hovered(mouse_position)

        if self.primary:
            background = ACCENT if hover else (166, 36, 47)
            border = ACCENT_LIGHT if hover else (210, 64, 73)
        else:
            background = SLOT_HOVER if hover else PANEL_LIGHT
            border = BORDER if hover else (60, 65, 84)

        pygame.draw.rect(
            surface,
            background,
            self.rect,
            border_radius=10,
        )
        pygame.draw.rect(
            surface,
            border,
            self.rect,
            width=2,
            border_radius=10,
        )

        draw_text(
            surface,
            self.label,
            font_size,
            self.rect.center,
            TEXT,
            center=True,
            bold=self.primary,
        )


class NotificationManager:
    def __init__(self):
        self.notifications = []
        self.max_visible = 5

    def clear(self):
        self.notifications.clear()

    def add(self, text, color=TEXT, duration=2.2, icon=None):
        for notification in self.notifications:
            if notification["text"] == text and notification["life"] > 0.6:
                notification["life"] = duration
                notification["max_life"] = duration
                notification["color"] = color
                return

        self.notifications.append(
            {
                "text": text,
                "color": color,
                "life": duration,
                "max_life": duration,
                "icon": icon,
            }
        )

        if len(self.notifications) > self.max_visible:
            self.notifications.pop(0)

    def update(self, delta_time):
        for notification in self.notifications:
            notification["life"] -= delta_time

        self.notifications = [
            notification
            for notification in self.notifications
            if notification["life"] > 0
        ]

    def draw(self, surface, center_x, top_y):
        y = top_y

        for notification in self.notifications:
            life = notification["life"]
            max_life = notification["max_life"]
            fade_in = min(1.0, (max_life - life) / 0.18)
            fade_out = min(1.0, life / 0.45)
            alpha = int(255 * min(fade_in, fade_out))

            font = get_font(22, True)
            rendered = font.render(notification["text"], True, notification["color"])
            width = rendered.get_width() + 34
            height = 38
            rect = pygame.Rect(0, 0, width, height)
            rect.center = (center_x, y + height // 2)

            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                panel,
                (12, 14, 20, int(210 * min(fade_in, fade_out))),
                panel.get_rect(),
                border_radius=10,
            )
            pygame.draw.rect(
                panel,
                (*notification["color"], int(190 * min(fade_in, fade_out))),
                panel.get_rect(),
                width=2,
                border_radius=10,
            )
            surface.blit(panel, rect.topleft)

            rendered.set_alpha(alpha)
            surface.blit(rendered, rendered.get_rect(center=rect.center))

            y += height + 7


def draw_icon_box(surface, rect, item_id, count=0, selected=False, hovered=False):
    """Draw a slot with an item icon and stack count."""
    from game.items import get_icon

    rect = pygame.Rect(rect)

    background = SLOT_HOVER if hovered else SLOT

    pygame.draw.rect(surface, background, rect, border_radius=9)

    if selected:
        pygame.draw.rect(surface, ACCENT, rect, width=3, border_radius=9)
        pygame.draw.rect(surface, (255, 145, 145), rect.inflate(-8, -8), width=1, border_radius=6)
    else:
        pygame.draw.rect(surface, (55, 60, 78), rect, width=1, border_radius=9)

    if item_id:
        icon_size = max(20, rect.width - 16)
        icon = get_icon(item_id, icon_size)
        surface.blit(icon, icon.get_rect(center=(rect.centerx, rect.centery - 2)))

        if count > 1:
            font = get_font(18, True)
            rendered = font.render(str(count), True, TEXT)
            shadow = font.render(str(count), True, SHADOW)

            position = (
                rect.right - rendered.get_width() - 5,
                rect.bottom - rendered.get_height() - 3,
            )

            surface.blit(shadow, (position[0] + 1, position[1] + 1))
            surface.blit(rendered, position)
