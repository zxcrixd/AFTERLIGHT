
import json

import pygame

from game.paths import data_folder, resource_path
from game.save import has_save


SAVE_FOLDER = data_folder()
SETTINGS_FILE = SAVE_FOLDER / "settings.json"

BACKGROUND_FOLDER = resource_path(
    "assets",
    "images",
    "backgrounds",
)


DEFAULT_SETTINGS = {
    "language": "ru",
    "music_volume": 0.35,
    "sfx_volume": 0.7,
    "fullscreen": False,
}


TEXT = {
    "ru": {
        "title": "AFTERLIGHT",
        "play": "ИГРАТЬ",
        "settings": "НАСТРОЙКИ",
        "exit": "ВЫХОД",
        "language": "ЯЗЫК",
        "russian": "РУССКИЙ",
        "english": "АНГЛИЙСКИЙ",
        "music": "ГРОМКОСТЬ МУЗЫКИ",
        "sfx": "ГРОМКОСТЬ ЗВУКОВ",
        "fullscreen": "ПОЛНОЭКРАННЫЙ РЕЖИМ",
        "on": "ВКЛ.",
        "off": "ВЫКЛ.",
        "controls": "УПРАВЛЕНИЕ",
        "back": "НАЗАД",
        "controls_title": "УПРАВЛЕНИЕ",
        "move": "Движение — A / D или стрелки",
        "jump": "Прыжок — ПРОБЕЛ",
        "crouch": "Пригнуться — C",
        "sprint": "Бег — SHIFT",
        "attack": "Атака — F / ЛКМ",
        "interact": "Действие и сбор — E",
        "inventory_key": "Инвентарь и крафт — I / TAB",
        "pause_key": "Пауза — ESC",
        "hotbar_key": "Хотбар — 1…6",
        "volume": "Громкость",
        "continue": "ПРОДОЛЖИТЬ",
        "new_game": "НОВАЯ ИГРА",
        "subtitle": "ВЫЖИВАНИЕ В СУМЕРКАХ",
        "footer": "Собирайте ресурсы · крафтите · выживайте",
        "survival_tip": "Ночью зомби злее. Скрафтите факел и оружие.",
    },
    "en": {
        "title": "AFTERLIGHT",
        "play": "PLAY",
        "settings": "SETTINGS",
        "exit": "EXIT",
        "language": "LANGUAGE",
        "russian": "RUSSIAN",
        "english": "ENGLISH",
        "music": "MUSIC VOLUME",
        "sfx": "SOUND EFFECTS VOLUME",
        "fullscreen": "FULLSCREEN",
        "on": "ON",
        "off": "OFF",
        "controls": "CONTROLS",
        "back": "BACK",
        "controls_title": "CONTROLS",
        "move": "Movement — A / D or arrows",
        "jump": "Jump — SPACE",
        "crouch": "Crouch — C",
        "sprint": "Sprint — SHIFT",
        "attack": "Attack — F / LMB",
        "interact": "Interact and gather — E",
        "inventory_key": "Inventory and crafting — I / TAB",
        "pause_key": "Pause — ESC",
        "hotbar_key": "Hotbar — 1…6",
        "volume": "Volume",
        "continue": "CONTINUE",
        "new_game": "NEW GAME",
        "subtitle": "SURVIVAL IN THE AFTERLIGHT",
        "footer": "Gather · craft · survive",
        "survival_tip": "Zombies are stronger at night. Craft a torch and a weapon.",
    },
}


class Menu:
    def __init__(self):
        self.settings = self.load_settings()

        self.screen_name = "main"
        self.buttons = {}
        self.has_save = has_save()

        self.background = self.load_background()

        self.title_font = pygame.font.Font(None, 100)
        self.button_font = pygame.font.Font(None, 46)
        self.small_font = pygame.font.Font(None, 30)

        self.action = None
        self.dragging_slider = None

    def load_settings(self):
        SAVE_FOLDER.mkdir(parents=True, exist_ok=True)

        settings = DEFAULT_SETTINGS.copy()

        if SETTINGS_FILE.exists():
            try:
                with SETTINGS_FILE.open(
                    "r",
                    encoding="utf-8",
                ) as file:
                    saved = json.load(file)

                if isinstance(saved, dict):
                    settings.update(saved)

            except (OSError, json.JSONDecodeError):
                print("Could not load settings. Using defaults.")

        if settings.get("language") not in ("ru", "en"):
            settings["language"] = "ru"

        for key in ("music_volume", "sfx_volume"):
            try:
                settings[key] = max(
                    0.0,
                    min(1.0, float(settings[key])),
                )
            except (ValueError, TypeError):
                settings[key] = DEFAULT_SETTINGS[key]

        settings["fullscreen"] = bool(
            settings.get("fullscreen", False)
        )

        return settings

    def save_settings(self):
        SAVE_FOLDER.mkdir(parents=True, exist_ok=True)

        try:
            with SETTINGS_FILE.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    self.settings,
                    file,
                    ensure_ascii=False,
                    indent=4,
                )

        except OSError as error:
            print(f"Could not save settings: {error}")

    def load_background(self):
        candidates = [
            "background_color_night_trees.png",
            "background_color_trees.png",
        ]

        for filename in candidates:
            path = BACKGROUND_FOLDER / filename

            if not path.exists():
                continue

            try:
                return pygame.image.load(
                    str(path)
                ).convert()

            except pygame.error as error:
                print(f"Menu background error: {error}")

        print("Menu background not found.")
        return None

    def text(self, key):
        language = self.settings["language"]
        return TEXT[language].get(key, key)

    def set_language(self, language):
        if language in ("ru", "en"):
            self.settings["language"] = language
            self.save_settings()

    def draw_background(self, surface):
        width, height = surface.get_size()

        if self.background is None:
            surface.fill((12, 16, 24))
            return

        image = self.background

        scale = max(
            width / image.get_width(),
            height / image.get_height(),
        )

        new_size = (
            int(image.get_width() * scale),
            int(image.get_height() * scale),
        )

        scaled = pygame.transform.scale(
            image,
            new_size,
        )

        x = (width - new_size[0]) // 2
        y = (height - new_size[1]) // 2

        surface.blit(scaled, (x, y))

        overlay = pygame.Surface(
            (width, height),
            pygame.SRCALPHA,
        )

        overlay.fill((5, 8, 15, 128))
        surface.blit(overlay, (0, 0))

    def draw_text(
        self,
        surface,
        text,
        font,
        position,
        color=(240, 240, 240),
        center=True,
    ):
        rendered = font.render(
            text,
            True,
            color,
        )

        rect = rendered.get_rect()

        if center:
            rect.center = position
        else:
            rect.topleft = position

        surface.blit(rendered, rect)

        return rect

    def draw_button(
        self,
        surface,
        key,
        label,
        center,
        size=(340, 58),
    ):
        mouse_position = pygame.mouse.get_pos()

        rect = pygame.Rect(
            0,
            0,
            size[0],
            size[1],
        )

        rect.center = center

        hovered = rect.collidepoint(mouse_position)

        background = (
            (130, 25, 35)
            if hovered
            else (35, 35, 43)
        )

        border = (
            (235, 55, 65)
            if hovered
            else (105, 35, 43)
        )

        pygame.draw.rect(
            surface,
            background,
            rect,
            border_radius=8,
        )

        pygame.draw.rect(
            surface,
            border,
            rect,
            width=2,
            border_radius=8,
        )

        self.draw_text(
            surface,
            label,
            self.button_font,
            rect.center,
        )

        self.buttons[key] = rect

    def draw_slider(
        self,
        surface,
        key,
        label,
        value,
        center_y,
    ):
        width = surface.get_width()

        self.draw_text(
            surface,
            f"{label}: {round(value * 100)}%",
            self.small_font,
            (width // 2, center_y - 25),
        )

        slider_width = 340

        track = pygame.Rect(
            width // 2 - slider_width // 2,
            center_y + 5,
            slider_width,
            10,
        )

        pygame.draw.rect(
            surface,
            (65, 65, 75),
            track,
            border_radius=5,
        )

        fill = pygame.Rect(
            track.x,
            track.y,
            int(track.width * value),
            track.height,
        )

        pygame.draw.rect(
            surface,
            (190, 35, 48),
            fill,
            border_radius=5,
        )

        knob_x = track.x + int(
            track.width * value
        )

        pygame.draw.circle(
            surface,
            (245, 245, 245),
            (knob_x, track.centery),
            11,
        )

        self.buttons[key] = track

    def draw(self, surface):
        self.draw_background(surface)

        width, height = surface.get_size()

        self.buttons.clear()

        if self.screen_name == "main":
            glow = pygame.Surface((560, 190), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (130, 18, 30, 42), glow.get_rect())
            surface.blit(
                glow,
                glow.get_rect(center=(width // 2, int(height * 0.16))),
            )

            self.draw_text(
                surface,
                self.text("title"),
                self.title_font,
                (width // 2, int(height * 0.16)),
                (220, 45, 55),
            )

            self.draw_text(
                surface,
                self.text("subtitle"),
                self.small_font,
                (width // 2, int(height * 0.235)),
                (154, 160, 178),
            )

            pygame.draw.line(
                surface,
                (150, 35, 44),
                (width // 2 - 130, int(height * 0.275)),
                (width // 2 + 130, int(height * 0.275)),
                2,
            )
        else:
            self.draw_text(
                surface,
                self.text("title"),
                self.title_font,
                (width // 2, int(height * 0.08)),
                (220, 45, 55),
            )

        if self.screen_name == "main":
            if self.has_save:
                self.draw_button(
                    surface,
                    "continue",
                    self.text("continue"),
                    (width // 2, int(height * 0.41)),
                )

                self.draw_button(
                    surface,
                    "new",
                    self.text("new_game"),
                    (width // 2, int(height * 0.51)),
                )

                self.draw_button(
                    surface,
                    "settings",
                    self.text("settings"),
                    (width // 2, int(height * 0.61)),
                )

                self.draw_button(
                    surface,
                    "exit",
                    self.text("exit"),
                    (width // 2, int(height * 0.71)),
                )
            else:
                self.draw_button(
                    surface,
                    "play",
                    self.text("play"),
                    (width // 2, int(height * 0.45)),
                )

                self.draw_button(
                    surface,
                    "settings",
                    self.text("settings"),
                    (width // 2, int(height * 0.56)),
                )

                self.draw_button(
                    surface,
                    "exit",
                    self.text("exit"),
                    (width // 2, int(height * 0.67)),
                )

            self.draw_text(
                surface,
                self.text("footer"),
                self.small_font,
                (width // 2, height - 34),
                (120, 126, 145),
            )

        elif self.screen_name == "settings":
            self.draw_text(
                surface,
                self.text("settings"),
                self.button_font,
                (width // 2, int(height * 0.18)),
                (220, 45, 55),
            )

            self.draw_slider(
                surface,
                "music",
                self.text("music"),
                self.settings["music_volume"],
                int(height * 0.35),
            )

            self.draw_slider(
                surface,
                "sfx",
                self.text("sfx"),
                self.settings["sfx_volume"],
                int(height * 0.46),
            )

            language_label = (
                self.text("russian")
                if self.settings["language"] == "ru"
                else self.text("english")
            )

            self.draw_button(
                surface,
                "language",
                f"{self.text('language')}: {language_label}",
                (width // 2, int(height * 0.58)),
            )

            fullscreen_label = (
                self.text("on")
                if self.settings["fullscreen"]
                else self.text("off")
            )

            self.draw_button(
                surface,
                "fullscreen",
                f"{self.text('fullscreen')}: {fullscreen_label}",
                (width // 2, int(height * 0.68)),
            )

            self.draw_button(
                surface,
                "controls",
                self.text("controls"),
                (width // 2, int(height * 0.78)),
            )

            self.draw_button(
                surface,
                "back",
                self.text("back"),
                (width // 2, int(height * 0.90)),
                (220, 48),
            )

        elif self.screen_name == "controls":
            self.draw_text(
                surface,
                self.text("controls_title"),
                self.button_font,
                (width // 2, int(height * 0.17)),
                (220, 45, 55),
            )

            lines = (
                "move",
                "jump",
                "crouch",
                "sprint",
                "attack",
                "interact",
                "inventory_key",
                "pause_key",
                "hotbar_key",
            )

            for index, key in enumerate(lines):
                self.draw_text(
                    surface,
                    self.text(key),
                    self.small_font,
                    (
                        width // 2,
                        int(height * 0.29) + index * 38,
                    ),
                )

            self.draw_button(
                surface,
                "back",
                self.text("back"),
                (width // 2, int(height * 0.83)),
            )

    def change_slider(self, key, mouse_x):
        track = self.buttons.get(key)

        if track is None:
            return

        value = (
            mouse_x - track.x
        ) / track.width

        value = max(0.0, min(1.0, value))

        self.settings[f"{key}_volume"] = value

        self.save_settings()

    def handle_event(self, event):
        self.action = None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button != 1:
                return None

            mouse_position = event.pos

            for key in ("music", "sfx"):
                track = self.buttons.get(key)

                if track and track.inflate(0, 24).collidepoint(
                    mouse_position
                ):
                    self.dragging_slider = key
                    self.change_slider(key, mouse_position[0])
                    return None

            for key, rect in self.buttons.items():
                if not rect.collidepoint(mouse_position):
                    continue

                if key == "play":
                    self.action = "new"

                elif key == "new":
                    self.action = "new"

                elif key == "continue":
                    self.action = "continue"

                elif key == "exit":
                    self.action = "quit"

                elif key == "settings":
                    self.screen_name = "settings"

                elif key == "back":
                    if self.screen_name == "controls":
                        self.screen_name = "settings"
                    else:
                        self.screen_name = "main"

                elif key == "controls":
                    self.screen_name = "controls"

                elif key == "language":
                    new_language = (
                        "en"
                        if self.settings["language"] == "ru"
                        else "ru"
                    )

                    self.set_language(new_language)

                elif key == "fullscreen":
                    self.settings["fullscreen"] = (
                        not self.settings["fullscreen"]
                    )

                    self.save_settings()
                    self.action = "fullscreen"

                break

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging_slider = None

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_slider:
                self.change_slider(
                    self.dragging_slider,
                    event.pos[0],
                )

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.screen_name == "controls":
                    self.screen_name = "settings"
                elif self.screen_name == "settings":
                    self.screen_name = "main"
                else:
                    self.action = "quit"

        return self.action
