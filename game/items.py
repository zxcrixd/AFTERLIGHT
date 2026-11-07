"""Item definitions, procedural icons and the player inventory."""

from dataclasses import dataclass, field
from pathlib import Path
import hashlib

import pygame


@dataclass(frozen=True)
class ItemDef:
    id: str
    name_ru: str
    name_en: str
    category: str = "material"
    max_stack: int = 99
    damage: float = 0.0
    reach: float = 0.0
    heal: float = 0.0
    hunger: float = 0.0
    light: float = 0.0
    tool: str = ""
    description_ru: str = ""
    description_en: str = ""

    def name(self, language="ru"):
        return self.name_ru if language == "ru" else self.name_en


ITEMS = {
    "wood": ItemDef(
        "wood", "Древесина", "Wood", "material",
        description_ru="Прочная древесина. Основа любого крафта.",
        description_en="Sturdy wood. The basis of most crafting.",
    ),
    "stone": ItemDef(
        "stone", "Камень", "Stone", "material",
        description_ru="Крепкий камень для инструментов и построек.",
        description_en="Solid stone for tools and structures.",
    ),
    "fiber": ItemDef(
        "fiber", "Волокно", "Fiber", "material",
        description_ru="Растительные волокна. Связывают всё вместе.",
        description_en="Plant fibers. They hold everything together.",
    ),
    "bone": ItemDef(
        "bone", "Кость", "Bone", "material",
        description_ru="Остаётся после зомби. Хорошо для наконечников.",
        description_en="Left behind by zombies. Good for tips.",
    ),
    "berry": ItemDef(
        "berry", "Ягоды", "Berries", "consumable",
        max_stack=30, hunger=14, heal=2,
        description_ru="Сладкие лесные ягоды. Утоляют голод.",
        description_en="Sweet forest berries. Restore hunger.",
    ),
    "mushroom": ItemDef(
        "mushroom", "Гриб", "Mushroom", "consumable",
        max_stack=30, hunger=20, heal=5,
        description_ru="Съедобный гриб. Немного лечит.",
        description_en="An edible mushroom. Heals a little.",
    ),
    "bandage": ItemDef(
        "bandage", "Бинт", "Bandage", "consumable",
        max_stack=20, heal=35,
        description_ru="Останавливает кровь и восстанавливает здоровье.",
        description_en="Stops bleeding and restores health.",
    ),
    "torch": ItemDef(
        "torch", "Факел", "Torch", "light",
        max_stack=10, light=330, damage=5, reach=40,
        description_ru="Освещает путь ночью. Выберите его в хотбаре.",
        description_en="Lights the way at night. Select it in the hotbar.",
    ),
    "campfire": ItemDef(
        "campfire", "Лагерный костёр", "Campfire", "placeable",
        max_stack=10, light=280,
        description_ru="Ставится на землю и лечит рядом стоящих.",
        description_en="Placed on the ground, heals nearby survivors.",
    ),
    "wooden_sword": ItemDef(
        "wooden_sword", "Деревянный меч", "Wooden Sword", "weapon",
        max_stack=1, damage=18, reach=58,
        description_ru="Простое оружие. Лучше, чем кулаки.",
        description_en="A simple weapon. Better than fists.",
    ),
    "stone_axe": ItemDef(
        "stone_axe", "Каменный топор", "Stone Axe", "tool",
        max_stack=1, damage=14, reach=52, tool="axe",
        description_ru="Валит деревья быстрее и даёт больше древесины.",
        description_en="Fells trees faster and yields more wood.",
    ),
    "stone_pickaxe": ItemDef(
        "stone_pickaxe", "Каменная кирка", "Stone Pickaxe", "tool",
        max_stack=1, damage=11, reach=52, tool="pickaxe",
        description_ru="Добывает больше камня из валунов.",
        description_en="Yields more stone from boulders.",
    ),
    "stone_spear": ItemDef(
        "stone_spear", "Каменное копьё", "Stone Spear", "weapon",
        max_stack=1, damage=28, reach=82,
        description_ru="Длинное копьё. Держит зомби на расстоянии.",
        description_en="A long spear. Keeps zombies at a distance.",
    ),
    "bone_spear": ItemDef(
        "bone_spear", "Костяное копьё", "Bone Spear", "weapon",
        max_stack=1, damage=38, reach=86,
        description_ru="Оружие из костей зомби. Бьёт очень больно.",
        description_en="A weapon made of zombie bones. Hits hard.",
    ),
}

FIST_DAMAGE = 7
FIST_REACH = 36


def item_name(item_id, language="ru"):
    item = ITEMS.get(item_id)

    if item is None:
        return item_id

    return item.name(language)


def item_category(item_id, language="ru"):
    item = ITEMS.get(item_id)
    return item.category if item else "material"


# ---------------------------------------------------------------------------
# Procedural icons
# ---------------------------------------------------------------------------

_icon_cache = {}
_custom_icons = {}


def register_item_icon(item_id, icon):
    """Register a custom icon for an item.

    ``icon`` may be a callable that draws on a 64x64 RGBA surface, or a
    path to an image file.  Passing ``None`` restores the default icon.
    """

    if icon is None:
        _custom_icons.pop(item_id, None)
    else:
        _custom_icons[item_id] = icon

    clear_icon_cache(item_id)


def clear_icon_cache(item_id=None):
    """Drop cached icons so changed content is redrawn."""

    if item_id is None:
        _icon_cache.clear()
        return

    for key in [key for key in _icon_cache if key[0] == item_id]:
        _icon_cache.pop(key, None)


def _fallback_icon(surface, item_id):
    """Draw a readable placeholder for items without a dedicated icon."""

    digest = hashlib.md5(item_id.encode("utf-8")).digest()
    color = (
        80 + digest[0] % 120,
        80 + digest[1] % 120,
        80 + digest[2] % 120,
    )
    dark = tuple(max(0, channel - 45) for channel in color)

    pygame.draw.rect(surface, dark, (10, 10, 44, 44), border_radius=10)
    pygame.draw.rect(surface, color, (14, 14, 36, 36), border_radius=8)

    item = ITEMS.get(item_id)
    label = "?"

    if item is not None:
        label = (item.name_en or item.name_ru or "?")[:1].upper()

    try:
        font = pygame.font.Font(None, 40)
        rendered = font.render(label, True, (245, 244, 238))
        surface.blit(
            rendered,
            (
                32 - rendered.get_width() // 2,
                32 - rendered.get_height() // 2,
            ),
        )
    except pygame.error:
        pass


def _log(surface):
    pygame.draw.rect(surface, (92, 61, 38), (7, 23, 50, 18), border_radius=7)
    pygame.draw.rect(surface, (124, 84, 51), (10, 26, 44, 9), border_radius=5)
    pygame.draw.circle(surface, (166, 121, 77), (55, 32), 9)
    pygame.draw.circle(surface, (112, 76, 46), (55, 32), 5)
    pygame.draw.line(surface, (72, 47, 29), (18, 30), (43, 30), 2)


def _stone(surface):
    points = [(14, 43), (8, 30), (20, 15), (41, 12), (55, 26), (50, 43), (34, 50)]
    pygame.draw.polygon(surface, (111, 117, 122), points)
    pygame.draw.polygon(surface, (147, 154, 158), [(20, 15), (41, 12), (47, 25), (26, 30)])
    pygame.draw.polygon(surface, (78, 83, 88), [(14, 43), (34, 50), (50, 43), (45, 35)])
    pygame.draw.line(surface, (60, 65, 69), (28, 34), (38, 44), 2)


def _fiber(surface):
    green = (84, 160, 92)
    light = (128, 201, 111)
    pygame.draw.lines(surface, green, False, [(18, 51), (26, 32), (22, 14)], 4)
    pygame.draw.lines(surface, light, False, [(30, 52), (32, 30), (42, 15)], 4)
    pygame.draw.lines(surface, green, False, [(40, 51), (42, 34), (52, 22)], 4)
    pygame.draw.line(surface, (63, 121, 68), (15, 44), (51, 42), 3)


def _berry(surface):
    pygame.draw.circle(surface, (196, 42, 62), (25, 35), 12)
    pygame.draw.circle(surface, (224, 62, 78), (40, 42), 11)
    pygame.draw.circle(surface, (168, 31, 52), (34, 24), 10)
    pygame.draw.circle(surface, (255, 168, 173), (22, 31), 3)
    pygame.draw.circle(surface, (255, 168, 173), (37, 38), 3)
    pygame.draw.lines(surface, (75, 142, 75), False, [(32, 16), (40, 8), (48, 12)], 3)


def _mushroom(surface):
    pygame.draw.rect(surface, (220, 205, 175), (26, 32, 13, 21), border_radius=4)
    pygame.draw.ellipse(surface, (176, 58, 47), (9, 12, 47, 27))
    pygame.draw.ellipse(surface, (213, 88, 68), (15, 16, 34, 15))
    pygame.draw.circle(surface, (242, 219, 198), (24, 23), 4)
    pygame.draw.circle(surface, (242, 219, 198), (42, 27), 3)


def _bone(surface):
    pygame.draw.line(surface, (229, 225, 209), (19, 44), (46, 18), 8)
    pygame.draw.circle(surface, (241, 238, 224), (16, 47), 7)
    pygame.draw.circle(surface, (241, 238, 224), (23, 40), 7)
    pygame.draw.circle(surface, (241, 238, 224), (49, 15), 7)
    pygame.draw.circle(surface, (241, 238, 224), (42, 22), 7)


def _torch(surface):
    pygame.draw.rect(surface, (94, 62, 37), (28, 26, 9, 29), border_radius=3)
    pygame.draw.rect(surface, (137, 93, 54), (30, 26, 5, 29), border_radius=2)
    pygame.draw.circle(surface, (255, 151, 47), (32, 20), 11)
    pygame.draw.circle(surface, (255, 207, 75), (32, 19), 7)
    pygame.draw.circle(surface, (255, 247, 190), (32, 17), 3)


def _campfire(surface):
    pygame.draw.line(surface, (92, 58, 34), (12, 50), (52, 38), 7)
    pygame.draw.line(surface, (114, 74, 43), (14, 39), (50, 50), 7)
    pygame.draw.circle(surface, (225, 88, 38), (32, 32), 14)
    pygame.draw.circle(surface, (255, 153, 48), (32, 29), 10)
    pygame.draw.circle(surface, (255, 224, 105), (32, 26), 5)


def _sword(surface):
    pygame.draw.polygon(surface, (181, 189, 196), [(30, 7), (38, 15), (26, 42), (20, 36)])
    pygame.draw.line(surface, (226, 232, 236), (33, 11), (23, 37), 2)
    pygame.draw.line(surface, (94, 62, 37), (18, 39), (30, 51), 7)
    pygame.draw.line(surface, (209, 170, 88), (14, 44), (29, 29), 4)


def _axe(surface):
    pygame.draw.line(surface, (116, 77, 44), (20, 52), (39, 13), 7)
    pygame.draw.polygon(surface, (135, 142, 148), [(37, 8), (55, 16), (50, 32), (34, 25)])
    pygame.draw.line(surface, (204, 210, 214), (39, 12), (50, 17), 3)


def _pickaxe(surface):
    pygame.draw.line(surface, (116, 77, 44), (20, 52), (38, 16), 7)
    pygame.draw.lines(surface, (139, 146, 151), False, [(13, 22), (31, 11), (54, 19)], 8)
    pygame.draw.line(surface, (210, 216, 220), (17, 22), (31, 14), 3)


def _spear(surface):
    pygame.draw.line(surface, (116, 77, 44), (15, 52), (44, 17), 6)
    pygame.draw.polygon(surface, (158, 166, 172), [(44, 17), (54, 7), (49, 24)])
    pygame.draw.line(surface, (218, 224, 228), (47, 15), (52, 10), 2)


def _bone_spear(surface):
    pygame.draw.line(surface, (116, 77, 44), (15, 52), (43, 18), 6)
    pygame.draw.polygon(surface, (238, 235, 219), [(42, 19), (54, 5), (49, 25)])
    pygame.draw.circle(surface, (248, 246, 234), (51, 8), 5)


def _bandage(surface):
    pygame.draw.ellipse(surface, (232, 229, 218), (13, 17, 38, 30))
    pygame.draw.ellipse(surface, (196, 192, 180), (18, 22, 28, 20))
    pygame.draw.rect(surface, (196, 52, 59), (28, 22, 8, 20), border_radius=2)
    pygame.draw.rect(surface, (196, 52, 59), (22, 28, 20, 8), border_radius=2)


_ICON_DRAWERS = {
    "wood": _log,
    "stone": _stone,
    "fiber": _fiber,
    "bone": _bone,
    "berry": _berry,
    "mushroom": _mushroom,
    "torch": _torch,
    "campfire": _campfire,
    "wooden_sword": _sword,
    "stone_axe": _axe,
    "stone_pickaxe": _pickaxe,
    "stone_spear": _spear,
    "bone_spear": _bone_spear,
    "bandage": _bandage,
}


def get_icon(item_id, size=48):
    """Return a cached, transparent icon surface for an item."""
    key = (item_id, size)

    if key in _icon_cache:
        return _icon_cache[key]

    surface = pygame.Surface((64, 64), pygame.SRCALPHA)
    custom = _custom_icons.get(item_id)

    if callable(custom):
        try:
            custom(surface)
        except Exception as error:
            print(f"Custom icon error for {item_id}: {error}")
            _fallback_icon(surface, item_id)
    elif custom:
        try:
            image = pygame.image.load(str(Path(custom))).convert_alpha()
            surface = pygame.transform.smoothscale(image, (64, 64))
        except (pygame.error, OSError) as error:
            print(f"Custom icon file error for {item_id}: {error}")
            _fallback_icon(surface, item_id)
    else:
        drawer = _ICON_DRAWERS.get(item_id)

        if drawer is not None:
            drawer(surface)
        else:
            _fallback_icon(surface, item_id)

    if size != 64:
        surface = pygame.transform.smoothscale(surface, (size, size))

    _icon_cache[key] = surface
    return surface


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

@dataclass
class Slot:
    item_id: str = ""
    count: int = 0

    @property
    def empty(self):
        return not self.item_id or self.count <= 0

    def clear(self):
        self.item_id = ""
        self.count = 0


class Inventory:
    """A slot based inventory. The first six slots are the hotbar."""

    HOTBAR_SIZE = 6

    def __init__(self, size=24):
        self.size = max(size, self.HOTBAR_SIZE)
        self.slots = [Slot() for _ in range(self.size)]
        self.selected = 0

    # -- queries ---------------------------------------------------------
    def count(self, item_id):
        return sum(
            slot.count
            for slot in self.slots
            if slot.item_id == item_id
        )

    def has(self, requirements):
        return all(
            self.count(item_id) >= amount
            for item_id, amount in requirements.items()
        )

    @property
    def selected_slot(self):
        return self.slots[self.selected]

    @property
    def selected_item(self):
        slot = self.selected_slot
        return slot.item_id if not slot.empty else ""

    def select(self, index):
        if 0 <= index < self.HOTBAR_SIZE:
            self.selected = index

    def first_free_slot(self):
        for index, slot in enumerate(self.slots):
            if slot.empty:
                return index

        return None

    # -- mutations -------------------------------------------------------
    def add(self, item_id, count=1):
        item = ITEMS.get(item_id)

        if item is None or count <= 0:
            return 0

        remaining = count

        # Fill existing stacks first.
        for slot in self.slots:
            if remaining <= 0:
                break

            if slot.item_id == item_id and slot.count < item.max_stack:
                space = item.max_stack - slot.count
                moved = min(space, remaining)
                slot.count += moved
                remaining -= moved

        # Then use empty slots.
        for slot in self.slots:
            if remaining <= 0:
                break

            if slot.empty:
                moved = min(item.max_stack, remaining)
                slot.item_id = item_id
                slot.count = moved
                remaining -= moved

        return remaining

    def remove(self, item_id, count=1):
        if self.count(item_id) < count:
            return False

        remaining = count

        for slot in reversed(self.slots):
            if remaining <= 0:
                break

            if slot.item_id != item_id:
                continue

            moved = min(slot.count, remaining)
            slot.count -= moved
            remaining -= moved

            if slot.count <= 0:
                slot.clear()

        return True

    def consume(self, requirements):
        if not self.has(requirements):
            return False

        for item_id, amount in requirements.items():
            self.remove(item_id, amount)

        return True

    def swap_with_selected(self, index):
        """Swap an inventory slot with the currently selected hotbar slot."""
        if index == self.selected or not (0 <= index < self.size):
            return False

        self.slots[index], self.slots[self.selected] = (
            self.slots[self.selected],
            self.slots[index],
        )
        return True

    def selected_tool(self):
        item = ITEMS.get(self.selected_item)
        return item.tool if item else ""

    def to_list(self):
        return [
            {"id": slot.item_id, "count": slot.count}
            for slot in self.slots
            if not slot.empty
        ]

    def load_list(self, entries):
        self.slots = [Slot() for _ in range(self.size)]
        self.selected = 0

        if not isinstance(entries, list):
            return

        for entry in entries[: self.size]:
            if not isinstance(entry, dict):
                continue

            item_id = entry.get("id")
            count = entry.get("count", 0)

            if item_id not in ITEMS:
                continue

            try:
                count = int(count)
            except (TypeError, ValueError):
                continue

            if count > 0:
                self.add(item_id, count)
