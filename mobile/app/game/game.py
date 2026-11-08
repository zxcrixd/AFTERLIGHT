"""Main game loop and integration of all survival systems."""

import random

import pygame

from settings import (
    GAME_TITLE,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    BACKGROUND_COLOR,
)

from game import save as save_module
from game.camera import Camera
from game.crafting import can_craft, craft
from game.enemy import Zombie
from game.hud import HUD
from game.input_map import event_key
from game.items import ITEMS
from game.lighting import DayNightCycle, Lighting
from game.localization import tr
from game.menu import Menu
from game.mods import ModManager
from game.overlays import GameOverOverlay, InventoryOverlay, PauseOverlay
from game.particles import ParticleSystem
from game.paths import resource_path
from game.physics import Physics
from game.player import Player
from game.resources import ResourceManager
from game.structures import Campfire
from game.touch import TouchControls, is_mobile
from game.ui import GREEN, MUTED, ORANGE, RED, TEXT, YELLOW, NotificationManager
from game.world import World


SOUNDS_FOLDER = resource_path("assets", "sounds", "effects")

SOUND_FILES = {
    "hurt": "sfx_hurt.ogg",
    "jump": "sfx_jump.ogg",
    "select": "sfx_select.ogg",
    "throw": "sfx_throw.ogg",
}

ITEM_COLORS = {
    "wood": (126, 86, 52),
    "stone": (132, 138, 144),
    "fiber": (91, 168, 98),
    "bone": (232, 228, 210),
    "berry": (204, 52, 72),
    "mushroom": (191, 75, 59),
    "torch": (248, 165, 63),
    "campfire": (245, 134, 46),
    "bandage": (226, 221, 210),
}


class Game:
    def __init__(self):
        pygame.init()

        # Create the window before loading images so convert() works.
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT)
        )

        self.mobile = is_mobile()
        self.menu = Menu()
        self.fullscreen = self.menu.settings["fullscreen"] or self.mobile

        if self.fullscreen or self.mobile:
            self.screen = self.create_screen()

        pygame.display.set_caption(GAME_TITLE)

        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "menu"
        self.rng = random.Random()

        # World and entities
        self.world = World()
        self.spawn_x = 0
        self.spawn_y = self.world.get_surface_y(0) - 64

        self.player = Player(self.spawn_x, self.spawn_y)
        self.camera = Camera(
            self.screen.get_width(),
            self.screen.get_height(),
        )
        self.physics = Physics()

        self.resources = ResourceManager(self.world)
        self.particles = ParticleSystem()
        self.daynight = DayNightCycle()
        self.lighting = Lighting()

        self.campfires = []
        self.zombies = []
        self.zombie_spawn_timer = 15.0
        self.kills = 0

        self.interaction_prompt = None
        self.harvest_cooldown = 0.0
        self._last_day = self.daynight.day

        # UI
        self.notifications = NotificationManager()
        self.hud = HUD(self)
        self.inventory_ui = InventoryOverlay(self)
        self.pause_ui = PauseOverlay(self)
        self.gameover_ui = GameOverOverlay(self)
        self.touch = TouchControls(self)

        self.menu.has_save = save_module.has_save()

        # Audio
        self.sfx = {}
        self.music_path = resource_path(
            "assets",
            "sounds",
            "music",
            "menumusic.ogg",
        )
        self.load_sounds()
        self.load_music()

        # Python mods are loaded last so every game system exists by then.
        self.mods = ModManager()
        self.mods.attach(self)
        self.mods.load_all()
        self._mods_notified = False

    # -- properties ------------------------------------------------------
    @property
    def language(self):
        return self.menu.settings["language"]

    # -- screen / audio --------------------------------------------------
    def create_screen(self):
        if self.mobile:
            # Keep the desktop logical resolution and let SDL scale it to the
            # device screen.  Drawing at native phone resolutions is much
            # slower, and this keeps every overlay laid out as designed.
            try:
                return pygame.display.set_mode(
                    (SCREEN_WIDTH, SCREEN_HEIGHT),
                    pygame.FULLSCREEN | pygame.SCALED,
                )
            except (pygame.error, NotImplementedError):
                return pygame.display.set_mode(
                    (0, 0),
                    pygame.FULLSCREEN,
                )

        if self.fullscreen:
            return pygame.display.set_mode(
                (0, 0),
                pygame.FULLSCREEN,
            )

        return pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT)
        )

    def load_sounds(self):
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init()
            except pygame.error as error:
                print(f"Audio initialization error: {error}")
                return

        for name, filename in SOUND_FILES.items():
            path = SOUNDS_FOLDER / filename

            if not path.exists():
                continue

            try:
                self.sfx[name] = pygame.mixer.Sound(str(path))
            except pygame.error as error:
                print(f"Sound loading error ({filename}): {error}")

    def play_sound(self, name, scale=1.0):
        sound = self.sfx.get(name)

        if sound is None or pygame.mixer.get_init() is None:
            return

        try:
            sound.set_volume(
                max(0.0, min(1.0, self.menu.settings["sfx_volume"] * scale))
            )
            sound.play()
        except pygame.error:
            pass

    def load_music(self):
        if pygame.mixer.get_init() is None:
            return

        if not self.music_path.exists():
            print(f"Music not found: {self.music_path}")
            return

        try:
            pygame.mixer.music.load(
                str(self.music_path)
            )

            pygame.mixer.music.set_volume(
                self.menu.settings["music_volume"]
            )

            pygame.mixer.music.play(-1)

        except pygame.error as error:
            print(f"Music loading error: {error}")

    def apply_settings(self):
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(
                self.menu.settings["music_volume"]
            )

    def toggle_fullscreen(self):
        if self.mobile:
            # Phones and tablets are always fullscreen.
            self.fullscreen = True
            return

        self.fullscreen = self.menu.settings["fullscreen"]

        self.screen = self.create_screen()

        self.camera.width = self.screen.get_width()
        self.camera.height = self.screen.get_height()

    # -- run management --------------------------------------------------
    def new_game(self, notify_mods=True, seed=None):
        if seed is None:
            seed = random.SystemRandom().randrange(1, 2_000_000_000)

        # Each run gets its own world.  The seed is saved so continuing a
        # game rebuilds exactly the same terrain and resources.
        self.world = World(int(seed))
        self.spawn_x = 0
        self.spawn_y = self.world.get_surface_y(0) - 64

        self.player = Player(self.spawn_x, self.spawn_y)
        self.touch.release_all()
        self.player.damage_hook = self._modify_player_damage
        self.camera = Camera(
            self.screen.get_width(),
            self.screen.get_height(),
        )
        self.physics = Physics()

        self.resources = ResourceManager(self.world)
        self.particles.clear()
        self.daynight = DayNightCycle()
        self.campfires = []
        self.zombies = []
        self.zombie_spawn_timer = 15.0
        self.kills = 0
        self.interaction_prompt = None
        self.harvest_cooldown = 0.0
        self._last_day = 1

        self.notifications.clear()
        self.mods.save_data = {}

        # A tiny starter kit so the crafting menu is immediately useful.
        self.player.inventory.add("wood", 2)
        self.player.inventory.add("fiber", 1)
        self.player.inventory.add("berry", 2)

        self.notifications.add(
            tr(self.language, "welcome"),
            color=YELLOW,
            duration=3.5,
        )
        self.notifications.add(
            tr(self.language, "survival_tip"),
            color=MUTED,
            duration=4.5,
        )
        self.notifications.add(
            tr(self.language, "world_seed", seed=self.world.seed),
            color=MUTED,
            duration=4.0,
        )

        self.state = "game"
        self.menu.has_save = save_module.has_save()
        self.world.set_background("day")

        if notify_mods:
            self.mods.emit("game_start", game=self)
            self._notify_mods_once()

    def continue_game(self):
        data = save_module.load_game()

        if data is None:
            self.new_game()
            return

        try:
            seed = int(data.get("world_seed", self.world.seed))
        except (TypeError, ValueError):
            seed = self.world.seed

        self.new_game(notify_mods=False, seed=seed)

        player_data = data.get("player", {})
        inventory_data = player_data.get("inventory", [])

        try:
            x = float(player_data.get("x", self.spawn_x))
            y = float(player_data.get("y", self.spawn_y))
        except (TypeError, ValueError):
            x, y = self.spawn_x, self.spawn_y

        self.player.position.update(x, y)
        self.player.rect.x = round(x)
        self.player.rect.y = round(y)

        self.player.health = max(
            1.0,
            min(self.player.max_health, float(player_data.get("health", self.player.max_health))),
        )
        self.player.hunger = max(
            0.0,
            min(self.player.max_hunger, float(player_data.get("hunger", self.player.max_hunger))),
        )
        self.player.stamina = max(
            0.0,
            min(self.player.max_stamina, float(player_data.get("stamina", self.player.max_stamina))),
        )

        self.player.inventory.load_list(inventory_data)

        try:
            selected = int(player_data.get("selected", 0))
        except (TypeError, ValueError):
            selected = 0

        self.player.inventory.select(selected)

        try:
            self.daynight.time_of_day = float(data.get("time_of_day", 0.32)) % 1.0
            self.daynight.day = max(1, int(data.get("day", 1)))
            self.kills = max(0, int(data.get("kills", 0)))
        except (TypeError, ValueError):
            pass

        self._last_day = self.daynight.day

        campfire_data = data.get("campfires", [])

        if isinstance(campfire_data, list):
            for entry in campfire_data:
                if not isinstance(entry, dict):
                    continue

                try:
                    self.campfires.append(
                        Campfire(
                            float(entry.get("x", 0)),
                            float(entry.get("y", self.world.get_surface_y(0))),
                        )
                    )
                except (TypeError, ValueError):
                    continue

        self.camera.base_offset.x = max(
            0.0,
            self.player.position.x + self.player.rect.width / 2 - self.camera.width / 2,
        )
        self.camera.offset.x = self.camera.base_offset.x

        self.notifications.clear()
        self.notifications.add(
            tr(self.language, "loaded"),
            color=GREEN,
            duration=2.8,
        )

        self.state = "game"

        self.mods.import_save_data(data.get("mods"))
        self.mods.emit("load", game=self, data=data)
        self.mods.emit("game_start", game=self)
        self._notify_mods_once()

    def save_current_game(self):
        if save_module.save_game(self):
            self.notifications.add(
                tr(self.language, "saved"),
                color=GREEN,
                duration=2.4,
            )
            self.menu.has_save = True
            self.play_sound("select", 0.8)
            return True

        self.notifications.add(
            tr(self.language, "save_failed"),
            color=RED,
            duration=3.0,
        )
        return False

    def _modify_player_damage(self, player, amount, source):
        for result in self.mods.emit(
            "player_damage",
            game=self,
            player=player,
            amount=amount,
            source=source,
        ):
            if isinstance(result, (int, float)):
                amount = float(result)

        return max(0.0, amount)

    def _notify_mods_once(self):
        if self._mods_notified:
            return

        self._mods_notified = True

        if self.mods.mod_count:
            self.notifications.add(
                tr(self.language, "mods_count", count=self.mods.mod_count),
                color=MUTED,
                duration=3.0,
            )

        for mod_id, _error in self.mods.errors[:3]:
            self.notifications.add(
                tr(self.language, "mod_error", name=mod_id),
                color=RED,
                duration=4.0,
            )

    def game_over(self):
        if self.state != "game":
            return

        self.state = "game_over"
        self.touch.release_all()
        self.player.pressed_keys.clear()
        self.notifications.clear()
        self.play_sound("hurt", 1.0)
        self.camera.shake(10, 0.4)
        self.menu.has_save = save_module.has_save()
        self.mods.emit("game_over", game=self)

    # -- event handling --------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                self.running = False
                continue

            if self.state == "menu":
                action = self.menu.handle_event(event)

                if action in ("play", "new"):
                    self.new_game()

                elif action == "continue":
                    self.continue_game()

                elif action == "quit":
                    self.running = False

                elif action == "fullscreen":
                    self.toggle_fullscreen()

                continue

            # Touch controls translate finger presses into the same player
            # state the keyboard uses.  They also swallow the synthetic mouse
            # events SDL generates from touches so a tap cannot attack twice.
            if self.touch.handle_event(event):
                continue

            # Keep key releases in sync even while an overlay is open.
            if event.type in (pygame.KEYUP,):
                self.player.handle_event(event)

            if self.state == "game":
                self.handle_game_event(event)

            elif self.state == "inventory":
                if event.type == pygame.KEYDOWN and event_key(event) in (
                    pygame.K_ESCAPE,
                    pygame.K_i,
                    pygame.K_TAB,
                ):
                    self.close_overlay()
                    continue

                self.inventory_ui.handle_event(event)

            elif self.state == "paused":
                action = self.pause_ui.handle_event(event)

                if action == "resume":
                    self.close_overlay()
                elif action == "save":
                    self.save_current_game()
                elif action == "menu":
                    self.save_current_game()
                    self.state = "menu"
                    self.menu.screen_name = "main"
                    self.menu.has_save = save_module.has_save()
                    self.player.pressed_keys.clear()
                elif action == "quit":
                    self.running = False

            elif self.state == "game_over":
                if event.type == pygame.KEYDOWN and event_key(event) in (
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    self.new_game()
                    continue

                if event.type == pygame.KEYDOWN and event_key(event) == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.menu.screen_name = "main"
                    self.menu.has_save = save_module.has_save()
                    continue

                action = self.gameover_ui.handle_event(event)

                if action == "restart":
                    self.new_game()
                elif action == "menu":
                    self.state = "menu"
                    self.menu.screen_name = "main"
                    self.menu.has_save = save_module.has_save()

    def handle_game_event(self, event):
        self.player.handle_event(event)

        if event.type == pygame.KEYDOWN:
            key = event_key(event)

            if any(self.mods.emit("key", game=self, key=key)):
                return

            if key == pygame.K_ESCAPE:
                self.open_overlay("paused")
                return

            if key in (pygame.K_i, pygame.K_TAB):
                self.open_overlay("inventory")
                return

            if key == pygame.K_F11:
                self.menu.settings["fullscreen"] = not self.menu.settings["fullscreen"]
                self.menu.save_settings()
                self.toggle_fullscreen()
                return

            if pygame.K_1 <= key <= pygame.K_6:
                self.player.inventory.select(key - pygame.K_1)
                self.play_sound("select", 0.6)
                return

            if key == pygame.K_e:
                self.try_interact()
                return

            if key == pygame.K_f:
                self.player_attack()
                return

            if key == pygame.K_SPACE and self.player.on_ground:
                self.play_sound("jump", 0.8)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.player_attack()

    def open_overlay(self, state):
        self.state = state
        self.touch.release_all()
        self.player.pressed_keys.clear()
        self.play_sound("select", 0.7)

    def close_overlay(self):
        self.state = "game"
        self.touch.release_all()
        self.player.pressed_keys.clear()
        self.play_sound("select", 0.6)

    # -- gameplay actions ------------------------------------------------
    def player_attack(self):
        if not self.player.start_attack():
            return

        self.play_sound("throw", 0.75)

        damage, reach, item_id = self.player.equipped_weapon()

        for result in self.mods.emit(
            "attack",
            game=self,
            player=self.player,
            damage=damage,
            reach=reach,
            item_id=item_id,
        ):
            if isinstance(result, (int, float)):
                damage = float(result)

        if self.player.facing_right:
            hitbox = pygame.Rect(
                self.player.rect.right - 8,
                self.player.rect.top - 12,
                int(reach),
                self.player.rect.height + 24,
            )
            direction = 1
        else:
            hitbox = pygame.Rect(
                self.player.rect.left - int(reach) + 8,
                self.player.rect.top - 12,
                int(reach),
                self.player.rect.height + 24,
            )
            direction = -1

        hit_any = False

        for zombie in self.zombies:
            if zombie.dead or not hitbox.colliderect(zombie.rect):
                continue

            zombie.take_damage(damage, direction)
            hit_any = True

            self.particles.add_burst(
                zombie.rect.center,
                (142, 205, 104),
                count=10,
                speed=185,
                gravity=480,
            )

        if hit_any:
            self.camera.shake(5, 0.18)
            self.play_sound("hurt", 0.45)

    def try_interact(self):
        nearest = self.resources.get_nearest(self.player)

        if any(
            self.mods.emit(
                "interact",
                game=self,
                player=self.player,
                nearest=nearest,
            )
        ):
            return

        if nearest is not None:
            self.harvest_node(nearest)
            return

        selected_id = self.player.inventory.selected_item
        item = ITEMS.get(selected_id)

        if item is None:
            return

        if item.category == "consumable":
            self.use_item(item)
        elif item.id == "campfire":
            self.place_campfire()

    def use_item(self, item):
        useful = (
            (item.heal > 0 and self.player.health < self.player.max_health)
            or (item.hunger > 0 and self.player.hunger < self.player.max_hunger)
        )

        if not useful:
            self.notifications.add(
                tr(self.language, "already_full"),
                color=MUTED,
                duration=1.8,
            )
            return

        if not self.player.inventory.remove(item.id, 1):
            return

        self.player.heal(item.heal)
        self.player.feed(item.hunger)

        self.particles.add_burst(
            (
                self.player.rect.centerx,
                self.player.rect.centery,
            ),
            (120, 220, 130),
            count=12,
            speed=120,
            gravity=120,
        )
        self.play_sound("select", 0.7)
        self.notifications.add(
            tr(self.language, "item_used", name=item.name(self.language)),
            color=GREEN,
            duration=1.8,
        )
        self.mods.emit("item_use", game=self, player=self.player, item=item)

    def place_campfire(self):
        player_x = self.player.rect.centerx
        tile_x = int(player_x // self.world.tile_size)
        ground_y = self.world.get_surface_y(tile_x)

        for campfire in self.campfires:
            if abs(campfire.x - player_x) < 130:
                self.notifications.add(
                    tr(self.language, "campfire_here"),
                    color=ORANGE,
                    duration=2.0,
                )
                return

        if not self.player.inventory.remove("campfire", 1):
            return

        self.campfires.append(Campfire(player_x, ground_y))
        self.particles.add_burst(
            (player_x, ground_y - 20),
            (245, 142, 55),
            count=20,
            speed=150,
            gravity=90,
        )
        self.play_sound("select", 0.9)
        self.notifications.add(
            tr(self.language, "campfire_placed"),
            color=ORANGE,
            duration=2.4,
        )

    def harvest_node(self, node):
        if self.harvest_cooldown > 0:
            return

        self.harvest_cooldown = 0.32

        result = node.harvest(self.player, self.rng)

        if result is None:
            return

        drops, depleted = result

        for hook_result in self.mods.emit(
            "harvest",
            game=self,
            node=node,
            player=self.player,
            drops=drops,
            depleted=depleted,
        ):
            if isinstance(hook_result, list):
                drops = hook_result

        for item_id, count in drops:
            leftover = self.player.inventory.add(item_id, count)
            gained = count - leftover
            item = ITEMS.get(item_id)

            if gained > 0 and item is not None:
                self.notifications.add(
                    tr(
                        self.language,
                        "got_item",
                        count=gained,
                        name=item.name(self.language),
                    ),
                    color=GREEN,
                    duration=1.7,
                )

        color = {
            "tree": (101, 166, 92),
            "rock": (146, 152, 158),
            "bush": (109, 190, 108),
            "mushroom": (190, 82, 65),
        }.get(node.kind, (170, 170, 170))

        self.particles.add_burst(
            (node.x, node.interaction_y),
            color,
            count=12,
            speed=165,
            gravity=520,
        )
        self.camera.shake(2.5, 0.12)
        self.play_sound("select", 0.45)

        if depleted:
            self.notifications.add(
                tr(
                    self.language,
                    "node_depleted",
                    name=tr(self.language, node.data["name_key"]),
                ),
                color=MUTED,
                duration=2.0,
            )

    def craft_recipe(self, recipe):
        if not can_craft(self.player.inventory, recipe):
            self.notifications.add(
                tr(self.language, "not_enough"),
                color=RED,
                duration=2.0,
            )
            self.play_sound("hurt", 0.3)
            return

        if not craft(self.player.inventory, recipe):
            self.notifications.add(
                tr(self.language, "inventory_full"),
                color=RED,
                duration=2.2,
            )
            return

        item = ITEMS.get(recipe.result)

        if item is not None:
            self.notifications.add(
                tr(self.language, "crafted", name=item.name(self.language)),
                color=GREEN,
                duration=2.4,
            )

            if item.category in ("weapon", "tool", "light", "placeable"):
                for index in range(6):
                    if self.player.inventory.slots[index].item_id == item.id:
                        self.player.inventory.select(index)
                        break

        self.particles.add_burst(
            (
                self.player.rect.centerx,
                self.player.rect.centery,
            ),
            (247, 214, 100),
            count=18,
            speed=145,
            gravity=70,
        )
        self.play_sound("select", 1.0)
        self.mods.emit("craft", game=self, recipe=recipe, item=item)

    # -- spawning / updating --------------------------------------------
    def spawn_zombie(self):
        alive = sum(1 for zombie in self.zombies if not zombie.dead)

        if alive >= (7 if self.daynight.is_night else 3):
            return

        player_x = self.player.position.x

        spawn_distance = random.randint(420, 700)

        # Never spawn a zombie directly on top of the player at the left edge.
        if random.choice((True, False)) and player_x - spawn_distance >= 0:
            spawn_x = player_x - spawn_distance
        else:
            spawn_x = player_x + spawn_distance

        difficulty = 1.0 + min(0.8, (self.daynight.day - 1) * 0.08)

        zombie = Zombie(
            spawn_x,
            self.world,
            night=self.daynight.is_night,
            difficulty=difficulty,
        )

        self.zombies.append(zombie)

    def update_zombies(self, delta_time):
        self.zombie_spawn_timer -= delta_time

        if self.zombie_spawn_timer <= 0:
            self.spawn_zombie()

            base_interval = 6.0 if self.daynight.is_night else 11.0
            self.zombie_spawn_timer = base_interval * random.uniform(0.8, 1.2)

        for zombie in self.zombies:
            zombie.update(self.player, delta_time)

            if zombie.dead and not zombie.drops_rolled:
                drops = zombie.roll_drops()

                for hook_result in self.mods.emit(
                    "enemy_death",
                    game=self,
                    zombie=zombie,
                    drops=drops,
                ):
                    if isinstance(hook_result, list):
                        drops = hook_result

                self.kills += 1
                self.camera.shake(6, 0.2)
                self.play_sound("hurt", 0.35)

                for item_id, count in drops:
                    leftover = self.player.inventory.add(item_id, count)
                    gained = count - leftover
                    item = ITEMS.get(item_id)

                    if gained > 0 and item is not None:
                        self.notifications.add(
                            tr(
                                self.language,
                                "got_item",
                                count=gained,
                                name=item.name(self.language),
                            ),
                            color=GREEN,
                            duration=1.6,
                        )

                self.particles.add_burst(
                    zombie.rect.center,
                    (95, 175, 92),
                    count=18,
                    speed=200,
                    gravity=500,
                )

        self.zombies = [
            zombie
            for zombie in self.zombies
            if not (zombie.dead and zombie.death_timer <= 0)
        ]

    def get_interaction_prompt(self, nearest):
        if nearest is not None:
            return nearest.prompt(self.language)

        item = ITEMS.get(self.player.inventory.selected_item)

        if item is None:
            return None

        if item.category == "consumable":
            return tr(
                self.language,
                "prompt_eat",
                name=item.name(self.language),
            )

        if item.id == "campfire":
            return tr(
                self.language,
                "prompt_place",
                name=item.name(self.language),
            )

        return None

    def update(self, delta_time):
        self.apply_settings()
        self.notifications.update(delta_time)

        if self.state != "game":
            return

        self.harvest_cooldown = max(0.0, self.harvest_cooldown - delta_time)

        # Player movement and physics
        self.player.handle_movement(delta_time)

        self.physics.update(
            self.player,
            self.world,
            delta_time,
        )

        self.player.update_stats(delta_time)

        # Day / night
        self.daynight.update(delta_time)
        self.world.set_background("night" if self.daynight.is_night else "day")

        if self.daynight.day != self._last_day:
            self._last_day = self.daynight.day
            self.notifications.add(
                tr(self.language, "level_up", day=self.daynight.day),
                color=YELLOW,
                duration=3.0,
            )

        # Resources and campfires
        nearest = self.resources.update(
            delta_time,
            self.player,
            self.camera,
            self.screen.get_width(),
        )

        for campfire in self.campfires:
            campfire.update(delta_time)
            heal = campfire.heal_amount(self.player)

            if heal > 0:
                self.player.heal(heal * delta_time)

        # Held gather key
        if pygame.K_e in self.player.pressed_keys and self.harvest_cooldown <= 0:
            if nearest is not None:
                self.harvest_node(nearest)

        self.interaction_prompt = self.get_interaction_prompt(nearest)

        # Enemies
        self.update_zombies(delta_time)

        # Effects
        self.particles.update(delta_time)
        self.camera.update(self.player, delta_time)

        self.mods.emit("update", game=self, delta_time=delta_time)

        if not self.player.is_alive:
            self.game_over()

    # -- drawing ---------------------------------------------------------
    def get_lights(self):
        lights = []
        darkness = self.daynight.darkness

        if darkness <= 0:
            return lights, darkness

        player_center = self.camera.apply(self.player.rect).center

        radius = 150
        selected = ITEMS.get(self.player.inventory.selected_item)

        if selected is not None and selected.light > 0:
            radius = selected.light

        lights.append(
            (
                player_center[0],
                player_center[1],
                radius,
            )
        )

        for campfire in self.campfires:
            x, y, light_radius = campfire.light()
            lights.append(
                (
                    x - self.camera.offset.x,
                    y - self.camera.offset.y,
                    light_radius,
                )
            )

        return lights, darkness

    def draw_game(self, delta_time):
        self.screen.fill(BACKGROUND_COLOR)

        self.world.draw(self.screen, self.camera)

        nearest = self.resources.get_nearest(self.player)
        self.resources.draw(self.screen, self.camera, nearest)

        for campfire in self.campfires:
            campfire.draw(self.screen, self.camera)

        for zombie in self.zombies:
            zombie.draw(
                self.screen,
                self.camera,
                delta_time,
            )

        self.player.draw(
            self.screen,
            self.camera,
            delta_time,
        )

        self.particles.draw(self.screen, self.camera)

        lights, darkness = self.get_lights()
        self.lighting.draw(self.screen, lights, darkness)

        self.hud.draw(self.screen, delta_time)

        if self.state == "game":
            self.touch.draw(self.screen)

        if self.state == "inventory":
            self.inventory_ui.draw(self.screen)
        elif self.state == "paused":
            self.pause_ui.draw(self.screen)
        elif self.state == "game_over":
            self.gameover_ui.draw(self.screen)

        self.mods.emit("draw", game=self, surface=self.screen)

    def draw(self, delta_time):
        if self.state == "menu":
            self.menu.draw(self.screen)
        else:
            self.draw_game(delta_time)

        pygame.display.flip()

    def run(self):
        try:
            while self.running:
                delta_time = (
                    self.clock.tick(FPS) / 1000.0
                )

                delta_time = min(
                    delta_time,
                    0.05,
                )

                self.handle_events()
                self.update(delta_time)
                self.draw(delta_time)

        finally:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()

            self.mods.shutdown()
            pygame.quit()
