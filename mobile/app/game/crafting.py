"""Crafting recipes and helper functions."""

from dataclasses import dataclass

from game.items import ITEMS


@dataclass(frozen=True)
class Recipe:
    id: str
    result: str
    amount: int
    ingredients: dict
    name_ru: str
    name_en: str
    description_ru: str = ""
    description_en: str = ""

    def name(self, language="ru"):
        return self.name_ru if language == "ru" else self.name_en

    def description(self, language="ru"):
        return self.description_ru if language == "ru" else self.description_en


RECIPES = [
    Recipe(
        "torch", "torch", 1, {"wood": 1, "fiber": 1},
        "Факел", "Torch",
        "Освещает путь ночью.", "Lights the way at night.",
    ),
    Recipe(
        "bandage", "bandage", 1, {"fiber": 3, "berry": 1},
        "Бинт", "Bandage",
        "Восстанавливает 35 здоровья.", "Restores 35 health.",
    ),
    Recipe(
        "wooden_sword", "wooden_sword", 1, {"wood": 3, "fiber": 2},
        "Деревянный меч", "Wooden Sword",
        "Базовое оружие ближнего боя.", "A basic melee weapon.",
    ),
    Recipe(
        "stone_axe", "stone_axe", 1, {"wood": 2, "stone": 3, "fiber": 1},
        "Каменный топор", "Stone Axe",
        "Больше древесины с каждого дерева.", "More wood from every tree.",
    ),
    Recipe(
        "stone_pickaxe", "stone_pickaxe", 1, {"wood": 2, "stone": 3, "fiber": 1},
        "Каменная кирка", "Stone Pickaxe",
        "Больше камня с валунов.", "More stone from boulders.",
    ),
    Recipe(
        "stone_spear", "stone_spear", 1, {"wood": 3, "stone": 2, "fiber": 2},
        "Каменное копьё", "Stone Spear",
        "Длинная и злая. Идеально против зомби.", "Long and mean. Great against zombies.",
    ),
    Recipe(
        "campfire", "campfire", 1, {"wood": 6, "stone": 5},
        "Лагерный костёр", "Campfire",
        "Освещает и лечит рядом.", "Lights and heals nearby.",
    ),
    Recipe(
        "bone_spear", "bone_spear", 1, {"wood": 2, "bone": 3, "fiber": 2},
        "Костяное копьё", "Bone Spear",
        "Самое сильное оружие в игре.", "The strongest weapon in the game.",
    ),
]


def get_recipe(recipe_id):
    for recipe in RECIPES:
        if recipe.id == recipe_id:
            return recipe

    return None


def format_cost(recipe, language="ru"):
    """Return a human readable ingredient list."""
    parts = []

    for item_id, amount in recipe.ingredients.items():
        item = ITEMS.get(item_id)
        name = item.name(language) if item else item_id
        parts.append(f"{name} ×{amount}")

    return ", ".join(parts)


def can_craft(inventory, recipe):
    return inventory.has(recipe.ingredients)


def craft(inventory, recipe):
    """Try to craft a recipe. Returns True when an item was produced."""
    if not can_craft(inventory, recipe):
        return False

    # Consume first: that may free a slot for the crafted item.
    inventory.consume(recipe.ingredients)
    leftover = inventory.add(recipe.result, recipe.amount)

    if leftover > 0:
        # Roll everything back if the result did not fit.
        inventory.remove(recipe.result, recipe.amount - leftover)

        for item_id, amount in recipe.ingredients.items():
            inventory.add(item_id, amount)

        return False

    return True
