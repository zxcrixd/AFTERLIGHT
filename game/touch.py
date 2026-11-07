"""Optional on-screen controls for phones and tablets.

Desktop builds keep using the keyboard and mouse.  The touch layer only
activates when the game runs on Android/iOS or when ``AFTERLIGHT_MOBILE=1``
is set, which makes it easy to preview the layout on a normal computer.

The controls inject the same state the keyboard uses (``pressed_keys`` and
``jump_requested``) and call the same gameplay methods as key presses, so
there is no second gameplay path to keep in sync.
"""

import os
import sys

import pygame

from game.ui import ACCENT, ACCENT_LIGHT, BORDER, PANEL, TEXT, draw_text


MOBILE_ENV = "AFTERLIGHT_MOBILE"


def is_mobile():
    """Return True when the touch UI should be enabled."""

    value = os.environ.get(MOBILE_ENV, "").strip().lower()

    if value in ("1", "true", "yes", "on"):
        return True

    return sys.platform in ("android", "ios")


class TouchControls:
    """Virtual d-pad and action buttons drawn over the game world."""

    def __init__(self, game):
        self.game = game
        self.enabled = is_mobile()

        # finger id -> action name
        self.fingers = {}
        self.buttons = {}
        self._layout_size = None

    # -- layout ----------------------------------------------------------
    def _build_layout(self, size):
        width, height = size
        scale = max(0.55, min(1.7, min(width, height) / 720.0))
        margin = 22 * scale
        base = 44 * scale

        def button(cx, cy, radius, label, font_scale=0.5):
            return {
                "center": (int(cx), int(cy)),
                "radius": int(radius),
                "label": label,
                "font_size": max(13, int(radius * font_scale * 2)),
            }

        self.buttons = {
            "left": button(
                margin + base,
                height - margin - base,
                base,
                "<",
            ),
            "right": button(
                margin + base * 3.15,
                height - margin - base,
                base,
                ">",
            ),
            "jump": button(
                width - margin - base * 1.45,
                height - margin - base * 1.45,
                base * 1.35,
                "JUMP",
                0.34,
            ),
            "attack": button(
                width - margin - base * 3.5,
                height - margin - base * 1.0,
                base * 0.95,
                "ATK",
                0.42,
            ),
            "interact": button(
                width - margin - base * 2.0,
                height - margin - base * 3.3,
                base * 0.95,
                "USE",
                0.42,
            ),
            "inventory": button(
                width - margin - base * 2.55,
                margin + base * 0.85,
                base * 0.85,
                "INV",
                0.4,
            ),
            "pause": button(
                width - margin - base * 0.8,
                margin + base * 0.85,
                base * 0.85,
                "II",
                0.45,
            ),
        }

        self._layout_size = size

    def _ensure_layout(self):
        size = self.game.screen.get_size()

        if size != self._layout_size:
            self._build_layout(size)

    def _button_at(self, point):
        self._ensure_layout()
        x, y = point

        for action, button in self.buttons.items():
            cx, cy = button["center"]
            radius = button["radius"]

            if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                return action

        return None

    # -- actions ---------------------------------------------------------
    def _press(self, action, finger_id):
        self.fingers[finger_id] = action
        player = getattr(self.game, "player", None)

        if player is None:
            return

        if action == "left":
            player.pressed_keys.add(pygame.K_a)
        elif action == "right":
            player.pressed_keys.add(pygame.K_d)
        elif action == "jump":
            player.jump_requested = True

            if player.on_ground:
                self.game.play_sound("jump", 0.8)
        elif action == "attack":
            self.game.player_attack()
        elif action == "interact":
            self.game.try_interact()
        elif action == "inventory":
            self.game.open_overlay("inventory")
        elif action == "pause":
            self.game.open_overlay("paused")

    def _release(self, finger_id):
        action = self.fingers.pop(finger_id, None)

        if action is None:
            return False

        player = getattr(self.game, "player", None)

        if player is not None:
            still_held = action in self.fingers.values()

            if not still_held and action == "left":
                player.pressed_keys.discard(pygame.K_a)
            elif not still_held and action == "right":
                player.pressed_keys.discard(pygame.K_d)

        return True

    def release_all(self):
        """Forget every held touch (used when an overlay opens)."""

        self.fingers.clear()
        player = getattr(self.game, "player", None)

        if player is not None:
            player.pressed_keys.discard(pygame.K_a)
            player.pressed_keys.discard(pygame.K_d)

    # -- events ----------------------------------------------------------
    def handle_event(self, event):
        if not self.enabled:
            return False

        state = getattr(self.game, "state", "menu")

        if event.type == pygame.FINGERUP:
            self._release(event.finger_id)
            return state == "game"

        if event.type == pygame.FINGERDOWN:
            if state != "game":
                return False

            self._ensure_layout()
            width, height = self.game.screen.get_size()
            action = self._button_at(
                (event.x * width, event.y * height)
            )

            if action is None:
                return False

            self._press(action, event.finger_id)
            return True

        if event.type == pygame.FINGERMOTION:
            return state == "game"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # SDL mirrors touches as mouse clicks.  Those must not trigger
            # an attack or press a button twice.
            if getattr(event, "touch", False) or self.fingers:
                return state == "game"

            if state != "game":
                return False

            action = self._button_at(event.pos)

            if action is None:
                return False

            self._press(action, "mouse")
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if getattr(event, "touch", False):
                return state == "game"

            if self._release("mouse"):
                return True

        return False

    # -- drawing ---------------------------------------------------------
    def draw(self, surface):
        if not self.enabled:
            return

        self._ensure_layout()
        pressed_actions = set(self.fingers.values())
        scale = max(0.55, min(1.7, min(surface.get_size()) / 720.0))

        for action, button in self.buttons.items():
            pressed = action in pressed_actions
            radius = button["radius"]
            size = radius * 2 + 6
            layer = pygame.Surface((size, size), pygame.SRCALPHA)
            center = (size // 2, size // 2)

            fill = (*ACCENT, 135) if pressed else (*PANEL, 120)
            border = (*ACCENT_LIGHT, 235) if pressed else (*BORDER, 185)

            pygame.draw.circle(layer, fill, center, radius)
            pygame.draw.circle(
                layer,
                border,
                center,
                radius,
                width=max(2, int(2 * scale)),
            )

            surface.blit(
                layer,
                (
                    button["center"][0] - size // 2,
                    button["center"][1] - size // 2,
                ),
            )

            draw_text(
                surface,
                button["label"],
                button["font_size"],
                button["center"],
                color=TEXT if not pressed else (255, 255, 255),
                center=True,
                bold=True,
            )
