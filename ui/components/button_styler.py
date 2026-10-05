# -*- coding: utf-8 -*-
"""Кнопки приложения поверх Material 3.

Сохраняет прежний API (``create_hover_button``, ``apply_hover_effect``,
``uniform_button_width_for_font``), но рисует кнопки компонентами Material 3:
скругления, state layer, hover/press-анимация, поддержка тёмной и светлой темы.
Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

from ui.components.material.button import MaterialButton
from ui.theme import theme

#: Старые хардкод-цвета проекта — не должны перебивать токены темы.
_LEGACY_COLORS = {
    "#182030",
    "#15354d",
    "#1e4a6e",
    "#1e4a6a",
    "#0a84ff",
    "#ff3b30",
    "#ff9500",
    "#30d158",
    "#8e8e93",
    "white",
}


def uniform_button_width_for_font(master, font, *texts, pad_chars=2):
    """Ширина tk.Button в символах (width) по самой длинной строке; pad_chars — запас."""
    if not texts:
        return max(1, 1 + int(pad_chars))
    try:
        f = tkfont.Font(master=master, font=font)
        zero = f.measure("0")
        if zero < 1:
            zero = 1
        mw = 0
        for t in texts:
            if t is None:
                continue
            for line in str(t).split("\n"):
                mw = max(mw, f.measure(line))
        n = (mw + zero - 1) // zero + int(pad_chars)
        return max(1, n)
    except Exception:
        longest = 1
        for t in texts:
            if t is None:
                continue
            for line in str(t).split("\n"):
                longest = max(longest, len(line))
        return max(1, longest + int(pad_chars))


def _normalize_font(font):
    """Заменяет Arial/системный fallback на шрифт темы, сохраняя размер."""
    if not font:
        return None
    try:
        if isinstance(font, (tuple, list)) and font:
            family = str(font[0])
            size = font[1] if len(font) > 1 else None
            weight = font[2] if len(font) > 2 else "normal"
            if family.lower() in ("arial", "helvetica", "sans-serif", "tahoma"):
                if isinstance(size, int) and size > 0:
                    return (theme.family("sans"), max(8, int(round(size * theme.scale))), weight)
                return None
    except Exception:
        return None
    return font


def _pick_variant(kwargs: dict) -> str:
    """Вариант кнопки: явный, иначе по назначению (иконка/обычная)."""
    variant = kwargs.pop("variant", None)
    if variant:
        return variant
    text = str(kwargs.get("text") or "")
    if text and len(text.strip()) <= 2 and not any(ch.isalnum() for ch in text):
        return "icon"
    return "tonal"


def create_hover_button(parent, text, command, **kwargs) -> MaterialButton:
    """Создаёт кнопку Material 3 с эффектом наведения.

    Совместима с прежним вызовом: лишние параметры (bg, fg, bd, relief,
    highlightthickness, activebackground) принимаются и игнорируются, чтобы
    цвета задавала тема.
    """
    variant = _pick_variant(kwargs)
    font = _normalize_font(kwargs.pop("font", None))
    width = kwargs.pop("width", None)
    padx = kwargs.pop("padx", None)
    pady = kwargs.pop("pady", None)
    anchor = kwargs.pop("anchor", "center")
    state = kwargs.pop("state", "normal")
    cursor = kwargs.pop("cursor", "hand2")
    parent_role = kwargs.pop("parent_role", "surface")

    bg = kwargs.pop("bg", None)
    fg = kwargs.pop("fg", None)
    if isinstance(bg, str) and bg.lower() in _LEGACY_COLORS:
        bg = None
    if isinstance(fg, str) and fg.lower() in _LEGACY_COLORS:
        fg = None

    for ignored in ("bd", "relief", "highlightthickness", "activebackground",
                    "activeforeground", "justify", "wraplength", "height",
                    "takefocus", "overrelief", "disabledforeground"):
        kwargs.pop(ignored, None)

    button = MaterialButton(
        parent,
        text=text,
        command=command,
        variant=variant,
        font=font,
        width=width,
        padx=padx,
        pady=pady,
        anchor=anchor,
        state=state,
        cursor=cursor,
        bg=bg,
        fg=fg,
        parent_role=parent_role,
        **kwargs,
    )
    return button


def apply_hover_effect(button) -> None:
    """Совместимость: у кнопок Material 3 эффект наведения встроенный."""
    if isinstance(button, MaterialButton):
        return
    original_bg = button.cget("bg")
    hover_bg = theme.state("secondary_container", "hover")

    def on_enter(_event):
        button._bg_before_hover = button.cget("bg")
        button.config(bg=hover_bg)

    def on_leave(_event):
        button.config(bg=getattr(button, "_bg_before_hover", original_bg))

    button.bind("<Enter>", on_enter, add="+")
    button.bind("<Leave>", on_leave, add="+")
