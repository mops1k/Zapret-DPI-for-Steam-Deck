# -*- coding: utf-8 -*-
"""Тема Material 3: токены, шрифты и менеджер применения.

Использование::

    from ui.theme import theme

    frame = tk.Frame(root, bg=theme.color("surface"))
    label = tk.Label(root, text="Готово", **theme.text("title_medium"))

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from . import color_utils
from .fonts import get_font_resolver
from .manager import (
    DEFAULT_MODE,
    PROJECT_ROOT,
    SETTINGS_FILE,
    VALID_MODES,
    ThemeManager,
    get_theme,
    theme,
)
from .tokens import (
    BOLD_ROLES,
    DARK_SCHEME,
    DURATION,
    ELEVATION_SURFACE,
    LIGHT_SCHEME,
    RADII,
    SCHEMES,
    SPACING,
    STATE_OPACITY,
    TYPE_ALIASES,
    TYPE_SCALE,
)

__all__ = [
    "BOLD_ROLES",
    "DARK_SCHEME",
    "DEFAULT_MODE",
    "DURATION",
    "ELEVATION_SURFACE",
    "LIGHT_SCHEME",
    "PROJECT_ROOT",
    "RADII",
    "SCHEMES",
    "SETTINGS_FILE",
    "SPACING",
    "STATE_OPACITY",
    "TYPE_ALIASES",
    "TYPE_SCALE",
    "ThemeManager",
    "VALID_MODES",
    "color_utils",
    "get_font_resolver",
    "get_theme",
    "theme",
]
