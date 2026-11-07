"""Layout-independent keyboard input.

pygame reports ``event.key`` using the active keyboard layout.  With a
non-Latin layout (for example Russian) pressing the physical ``D`` key
produces a Cyrillic keysym, so checks such as ``pygame.K_d`` fail and the
character cannot move.  ``event.scancode`` always describes the physical
key, so we translate it to the matching US-layout key constant.
"""

import pygame


SCANCODE_TO_KEY = {}

for _letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    SCANCODE_TO_KEY[getattr(pygame, f"KSCAN_{_letter}")] = getattr(
        pygame, f"K_{_letter.lower()}"
    )

for _digit in "0123456789":
    SCANCODE_TO_KEY[getattr(pygame, f"KSCAN_{_digit}")] = getattr(
        pygame, f"K_{_digit}"
    )

for _name in (
    "SPACE",
    "TAB",
    "RETURN",
    "ESCAPE",
    "BACKSPACE",
    "LSHIFT",
    "RSHIFT",
    "LCTRL",
    "RCTRL",
    "LALT",
    "RALT",
    "LEFT",
    "RIGHT",
    "UP",
    "DOWN",
    "F11",
):
    _scancode = getattr(pygame, f"KSCAN_{_name}", None)
    _key = getattr(pygame, f"K_{_name}", None)

    if _scancode is not None and _key is not None:
        SCANCODE_TO_KEY[_scancode] = _key


def event_key(event):
    """Return a layout-independent pygame key constant for a key event."""

    scancode = getattr(event, "scancode", None)

    if scancode in SCANCODE_TO_KEY:
        return SCANCODE_TO_KEY[scancode]

    return getattr(event, "key", None)
