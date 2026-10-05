# -*- coding: utf-8 -*-
"""Цветовые преобразования для state layer и тональных поверхностей.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Dict, Tuple


def parse_hex(value: str) -> Tuple[int, int, int]:
    """'#RRGGBB' -> (r, g, b). Пустая строка — прозрачность (0, 0, 0)."""
    if not value:
        return (0, 0, 0)
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    if len(v) != 6:
        raise ValueError(f"Некорректный цвет: {value!r}")
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))


def to_hex(rgb: Tuple[int, int, int]) -> str:
    """(r, g, b) -> '#RRGGBB' с обрезкой диапазона."""
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def blend(foreground: str, background: str, alpha: float) -> str:
    """Накладывает foreground на background с прозрачностью alpha (0…1)."""
    fr, fg, fb = parse_hex(foreground)
    br, bg, bb = parse_hex(background)
    a = max(0.0, min(1.0, alpha))
    return to_hex((fr * a + br * (1 - a), fg * a + bg * (1 - a), fb * a + bb * (1 - a)))


def mix(color_a: str, color_b: str, t: float) -> str:
    """Линейная смесь двух цветов: t=0 -> color_a, t=1 -> color_b."""
    return blend(color_b, color_a, max(0.0, min(1.0, t)))


def lighten(color: str, amount: float) -> str:
    return blend("#FFFFFF", color, amount)


def darken(color: str, amount: float) -> str:
    return blend("#000000", color, amount)


def luminance(color: str) -> float:
    """Относительная яркость (0…1) по sRGB — для выбора контрастного текста."""
    r, g, b = (c / 255 for c in parse_hex(color))
    parts = []
    for c in (r, g, b):
        parts.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]


def readable_on(background: str, dark: str = "#171C1F", light: str = "#FFFFFF") -> str:
    """Возвращает тёмный или светлый цвет текста, читаемый на фоне."""
    return dark if luminance(background) > 0.5 else light


def state_layer(container: str, content: str, opacity: float) -> str:
    """Цвет state layer: контент поверх контейнера с заданной прозрачностью."""
    return blend(content, container, opacity)


def tonal_surfaces(base: str) -> Dict[str, str]:
    """Производные тональные поверхности от одного базового цвета."""
    return {
        "lowest": darken(base, 0.25),
        "low": lighten(base, 0.06),
        "base": base,
        "high": lighten(base, 0.10),
        "highest": lighten(base, 0.16),
    }
