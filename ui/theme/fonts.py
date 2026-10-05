# -*- coding: utf-8 -*-
"""Подбор шрифтов с fallback под Linux/SteamOS.

Inter в поставке SteamOS отсутствует, поэтому цепочка кандидатов проверяется
по фактическому списку семейств Tk. Проект «Zapret DPI Manager»
© Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence

import tkinter as tk
import tkinter.font as tkfont

SANS_CANDIDATES: Sequence[str] = (
    "Inter",
    "Noto Sans",
    "Cantarell",
    "DejaVu Sans",
    "Liberation Sans",
    "Arial",
    "Helvetica",
)

DISPLAY_CANDIDATES: Sequence[str] = (
    "Inter Display",
    "Noto Sans Display",
    "Noto Sans",
    "Cantarell",
    "DejaVu Sans",
    "Liberation Sans",
    "Arial",
)

MONO_CANDIDATES: Sequence[str] = (
    "JetBrains Mono",
    "Noto Sans Mono",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Courier New",
    "monospace",
)

EMOJI_CANDIDATES: Sequence[str] = (
    "Noto Color Emoji",
    "Noto Emoji",
    "Symbola",
    "DejaVu Sans",
)

FALLBACKS: Dict[str, str] = {
    "sans": "TkDefaultFont",
    "display": "TkDefaultFont",
    "mono": "TkFixedFont",
    "emoji": "TkDefaultFont",
}


class FontResolver:
    """Определяет доступные семейства шрифтов и собирает кортежи для Tk."""

    def __init__(self) -> None:
        self._families: Optional[frozenset] = None
        self._resolved: Dict[str, str] = {}
        self._cache: Dict[tuple, tuple] = {}

    # -- определение доступных семейств ------------------------------------

    def _available(self, master: Optional[tk.Misc]) -> frozenset:
        if self._families is not None:
            return self._families
        names: set = set()
        if master is not None:
            try:
                names = {str(n) for n in tkfont.families(master)}
            except (tk.TclError, RuntimeError):
                names = set()
        if not names:
            try:
                names = {str(n) for n in tkfont.families()}
            except (tk.TclError, RuntimeError):
                names = set()
        self._families = frozenset(names)
        return self._families

    def invalidate(self) -> None:
        """Сбрасывает кэш (например, после смены DPI/темы оформления ОС)."""
        self._families = None
        self._resolved.clear()
        self._cache.clear()

    def _pick(self, master: Optional[tk.Misc], candidates: Sequence[str], fallback_key: str) -> str:
        cached = self._resolved.get(fallback_key)
        if cached:
            return cached
        available = self._available(master)
        chosen = ""
        if available:
            lowered = {name.lower(): name for name in available}
            for candidate in candidates:
                real = lowered.get(candidate.lower())
                if real:
                    chosen = real
                    break
        if not chosen:
            chosen = FALLBACKS.get(fallback_key, "TkDefaultFont")
        self._resolved[fallback_key] = chosen
        return chosen

    # -- публичный API ------------------------------------------------------

    def resolve(self, master: Optional[tk.Misc] = None) -> Dict[str, str]:
        """Словарь семейств: sans, display, mono, emoji."""
        return {
            "sans": self._pick(master, SANS_CANDIDATES, "sans"),
            "display": self._pick(master, DISPLAY_CANDIDATES, "display"),
            "mono": self._pick(master, MONO_CANDIDATES, "mono"),
            "emoji": self._pick(master, EMOJI_CANDIDATES, "emoji"),
        }

    def family(self, master: Optional[tk.Misc], kind: str = "sans") -> str:
        return self.resolve(master).get(kind, self.resolve(master)["sans"])

    def tuple_for(
        self,
        master: Optional[tk.Misc],
        size: int,
        weight: str = "normal",
        kind: str = "sans",
    ) -> tuple:
        """Кортеж шрифта Tk: (family, size[, weight])."""
        family = self.family(master, kind)
        key = (family, int(size), weight)
        cached = self._cache.get(key)
        if cached is None:
            cached = (family, int(size)) if weight == "normal" else (family, int(size), weight)
            self._cache[key] = cached
        return cached


_resolver = FontResolver()


def get_font_resolver() -> FontResolver:
    """Общий резолвер шрифтов для всего приложения."""
    return _resolver
