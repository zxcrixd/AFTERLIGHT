# Моды AFTERLIGHT

Игра поддерживает моды на Python. Мод — это папка с `mod.py` (и необязательным `mod.json`) или одиночный `.py`-файл внутри папки `mods/`.

> ⚠️ Моды выполняют обычный Python-код с полными правами. Устанавливайте только те моды, которым доверяете.

## Структура

```
mods/
  my_mod/
    mod.json      # необязательно, но удобно
    mod.py        # обязателен
```

`mod.json`:

```json
{
  "id": "my_mod",
  "name": "My Mod",
  "version": "1.0.0",
  "author": "You",
  "description": "What this mod adds",
  "api_version": 1,
  "enabled": true
}
```

`mod.py` должен определить функцию `setup(api)`. Необязательная `teardown(api)` вызывается при выходе из игры.

```python
def setup(api):
    api.register_item(
        "my_item",
        "Мой предмет",
        "My Item",
        category="material",
        description_ru="Описание",
        description_en="Description",
    )

def teardown(api):
    api.log("bye")
```

## Быстрый старт

1. Скопируйте папку `mods/example_mod` в `mods/my_mod`.
2. Поменяйте `id` в `mod.json` и содержимое `mod.py`.
3. Запустите игру. Загруженные моды показываются в паузе, а ошибки — в консоли и уведомлением.

## API

Все методы вызываются у объекта `api`, который передаётся в `setup(api)`.

### Предметы

```python
api.register_item(
    item_id,
    name_ru,
    name_en,
    *,
    category="material",   # material / tool / weapon / consumable / placeable / light
    max_stack=99,
    damage=0.0,
    reach=0.0,
    heal=0.0,
    hunger=0.0,
    light=0.0,
    tool="",               # "axe", "pickaxe" или свой идентификатор
    description_ru="",
    description_en="",
    icon=None,             # callable(surface) или путь к PNG
    override=False,
)
```

`icon` — функция, которая рисует на поверхности 64×64 с прозрачностью:

```python
def draw_icon(surface):
    pygame.draw.circle(surface, (255, 120, 40), (32, 32), 24)
```

Можно передать путь к картинке: `icon="mods/my_mod/icon.png"`.

### Рецепты

```python
api.register_recipe(
    recipe_id,
    result_item_id,
    amount,
    {"wood": 2, "stone": 1},
    "Название",
    "Name",
    description_ru="...",
    description_en="...",
    override=False,
)
```

Если рецептов станет больше, чем помещается в окно крафта, список прокручивается колесом мыши.

### Ресурсы мира

```python
api.register_resource(
    kind,
    "Название",
    "Name",
    "E — добыть: {name}",
    "E — mine: {name}",
    *,
    hits=3,
    respawn=60.0,
    weight=0,              # > 0 — ресурс спавнится в мире
    height=60,
    interaction_height=None,
    drops=None,            # drops(node, player, rng) -> [(item_id, count), ...]
    draw=None,             # draw(surface, x, ground_y)
    draw_stump=None,       # draw_stump(surface, x, ground_y)
    color=(120, 130, 140),
    stump_color=(74, 78, 84),
    override=False,
)
```

Пример:

```python
def crystal_drops(node, player, rng):
    return [("crystal", rng.randint(1, 2))]

def draw_crystal(surface, x, ground_y):
    pygame.draw.circle(surface, (90, 210, 250), (int(x), int(ground_y - 20)), 18)

api.register_resource(
    "crystal_cluster",
    "Кристаллы", "Crystal Cluster",
    "E — добыть: {name}", "E — mine: {name}",
    weight=8,
    drops=crystal_drops,
    draw=draw_crystal,
)
```

### Локализация

```python
api.add_strings("ru", {"my_key": "Моя строка"})
api.add_strings("en", {"my_key": "My string"})
```

Или сразу для двух языков:

```python
api.add_strings({
    "ru": {"my_key": "Моя строка"},
    "en": {"my_key": "My string"},
})
```

### События

```python
api.on("event_name", callback)
api.off("event_name", callback)
api.on_key(pygame.K_m, lambda game: ...)
```

| Событие | Аргументы | Что можно вернуть |
| --- | --- | --- |
| `mods_loaded` | `game` | — |
| `game_start` | `game` | — |
| `game_over` | `game` | — |
| `update` | `game`, `delta_time` | — |
| `draw` | `game`, `surface` | — |
| `key` | `game`, `key` | `True`, чтобы «съесть» клавишу |
| `attack` | `game`, `player`, `damage`, `reach`, `item_id` | новое значение урона |
| `player_damage` | `game`, `player`, `amount`, `source` | новое значение урона |
| `interact` | `game`, `player`, `nearest` | `True`, чтобы отменить стандартное действие |
| `harvest` | `game`, `node`, `player`, `drops`, `depleted` | новый список дропа |
| `item_use` | `game`, `player`, `item` | — |
| `craft` | `game`, `recipe`, `item` | — |
| `enemy_death` | `game`, `zombie`, `drops` | новый список дропа |
| `save` | `game`, `data` | можно изменить `data` перед записью |
| `load` | `game`, `data` | — |
| `shutdown` | `game` | — |

Пример уменьшения урона:

```python
def on_damage(game, player, amount, source):
    return amount * 0.8

api.on("player_damage", on_damage)
```

### Данные в сохранении

```python
api.set_save_data("mined", 12)
value = api.get_save_data("mined", 0)
```

Значение должно быть JSON-сериализуемым. Данные автоматически попадают в `saves/game.json` в раздел `mods`.

### Утилиты

```python
api.log("text")                      # вывод в консоль с префиксом мода
api.notify("Текст", color=(120, 220, 255), duration=2.0)
api.give("wood", 5)                  # выдать предмет игроку
api.game                             # объект Game (доступен после старта)
api.items                            # реестр ITEMS
api.recipes                          # список RECIPES
api.strings                          # таблицы локализации
```

## Ошибки

- Ошибка в `setup` помечает мод как сломанный, но не роняет игру.
- Ошибка в хуке перехватывается, печатается один раз и не спамит консоль.
- Проверить статус модов можно в консоли и в окне паузы.

## Ограничения

- Моды загружаются один раз при запуске игры; после установки/изменения мода перезапустите игру.
- API пока не умеет добавлять новых зомби и структуры. Для сложной логики используйте события `update`, `draw`, `key`, `interact` и собственные объекты.
- Моды не изолированы: это обычный Python-код.
