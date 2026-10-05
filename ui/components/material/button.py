# -*- coding: utf-8 -*-
"""Кнопки Material 3 с совместимым с tk.Button API.

Поддерживаются варианты filled, tonal, elevated, outlined, text, icon, fab.
Кнопка — Canvas со скруглённым фоном, state layer и плавным hover/press,
но при этом сохраняет привычные методы ``config``/``cget``/``bind``.
Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

import tkinter as tk

from ui.theme import theme

from .base import draw_rounded_rect, measure_text

#: Роли фона и контента по варианту кнопки.
VARIANTS: Dict[str, Tuple[str, str, str]] = {
    # variant -> (fill_role, content_role, outline_role)
    "filled": ("primary", "on_primary", ""),
    "tonal": ("secondary_container", "on_secondary_container", ""),
    "elevated": ("surface_container_low", "primary", ""),
    "outlined": ("surface", "primary", "outline"),
    "text": ("surface", "primary", ""),
    "icon": ("surface", "on_surface_variant", ""),
    "fab": ("primary_container", "on_primary_container", ""),
}

_IGNORED_OPTIONS = {
    "bd",
    "relief",
    "highlightthickness",
    "activebackground",
    "activeforeground",
    "disabledforeground",
    "overrelief",
    "takefocus",
    "default",
    "offrelief",
    "indicatoron",
    "selectcolor",
    "troughcolor",
    "repeatdelay",
    "repeatinterval",
    "bitmap",
    "image",
    "compound",
    "underline",
    "wraplength",
    "justify",
    "height",
}


class MaterialButton(tk.Canvas):
    """Кнопка M3. Совместима с tk.Button по ключевым методам."""

    def __init__(
        self,
        master: tk.Misc,
        text: str = "",
        command: Optional[Callable] = None,
        *,
        variant: str = "tonal",
        icon: str = "",
        font=None,
        width: Optional[int] = None,
        padx: Optional[int] = None,
        pady: Optional[int] = None,
        radius: Optional[str] = None,
        anchor: str = "center",
        cursor: str = "hand2",
        state: str = "normal",
        bg: Optional[str] = None,
        fg: Optional[str] = None,
        parent_role: str = "surface",
        **kwargs,
    ) -> None:
        super().__init__(master, highlightthickness=0, bd=0, bg=theme.color(parent_role))
        self._variant = variant if variant in VARIANTS else "tonal"
        self._fill_role, self._content_role, self._outline_role = VARIANTS[self._variant]
        self._text = str(text)
        self._icon = str(icon)
        self._command = command
        self._font = font or theme.font("label_large")
        self._width_chars = width
        self._padx = theme.px(18) if padx is None else int(padx)
        self._pady = theme.px(10) if pady is None else int(pady)
        self._radius_name = radius or ("full" if self._variant in ("filled", "tonal", "outlined", "text") else "md")
        self._anchor = anchor
        self._parent_role = parent_role
        self._state = "normal" if str(state) != "disabled" else "disabled"
        self._explicit_fill = bg
        self._explicit_content = fg
        self._alpha = 0.0
        self._target_alpha = 0.0
        self._anim_job = None
        self._text_id: Optional[int] = None
        self._shape_id: Optional[int] = None
        self._pressed = False
        self.configure(cursor=cursor)

        self._apply_size()
        self.bind("<Configure>", lambda _e: self._redraw())
        self._bind_interactions()

    # -- совместимость с tk.Button -----------------------------------------

    def bind(self, sequence=None, func=None, add=None):  # noqa: D102 - API Tk
        interactive = {
            "<Enter>",
            "<Leave>",
            "<Button-1>",
            "<ButtonPress-1>",
            "<ButtonRelease-1>",
        }
        if sequence in interactive:
            add = "+"
        return super().bind(sequence, func, add)

    def configure(self, cnf=None, **kwargs):  # noqa: D102 - API Tk
        options = dict(cnf or {})
        options.update(kwargs)
        redraw = False
        resize = False
        for key, value in options.items():
            if key in ("text", "label"):
                self._text = "" if value is None else str(value)
                redraw = True
                resize = True
            elif key == "command":
                self._command = value
            elif key == "state":
                self._state = "disabled" if str(value) == "disabled" else "normal"
                redraw = True
            elif key == "bg" or key == "background":
                self._explicit_fill = value or None
                redraw = True
            elif key == "fg" or key == "foreground":
                self._explicit_content = value or None
                redraw = True
            elif key == "font":
                self._font = value
                redraw = True
                resize = True
            elif key == "width":
                self._width_chars = value
                resize = True
                redraw = True
            elif key == "height":
                try:
                    super().configure(height=value)
                except tk.TclError:
                    pass
                redraw = True
            elif key == "padx":
                self._padx = int(value)
                resize = True
                redraw = True
            elif key == "pady":
                self._pady = int(value)
                resize = True
                redraw = True
            elif key == "anchor":
                self._anchor = value
                redraw = True
            elif key in ("variant",):
                self._variant = value if value in VARIANTS else self._variant
                self._fill_role, self._content_role, self._outline_role = VARIANTS[self._variant]
                redraw = True
            elif key in ("icon",):
                self._icon = str(value)
                resize = True
                redraw = True
            elif key in _IGNORED_OPTIONS or key in ("cursor", "name", "class_"):
                try:
                    super().configure(**{key: value})
                except tk.TclError:
                    pass
            else:
                try:
                    super().configure(**{key: value})
                except tk.TclError:
                    pass
        if resize:
            self._apply_size()
        if redraw:
            self._redraw()
        return None

    config = configure

    def cget(self, key):  # noqa: D102 - API Tk
        if key in ("text", "label"):
            return self._text
        if key in ("bg", "background"):
            return self._current_fill()
        if key in ("fg", "foreground"):
            return self._current_content()
        if key == "state":
            return self._state
        if key == "font":
            return self._font
        if key == "command":
            return self._command
        if key == "width":
            return self._width_chars
        return super().cget(key)

    def invoke(self) -> None:
        """Программный клик (совместимость с tk.Button)."""
        if self._state != "disabled" and callable(self._command):
            self._command()

    def flash(self) -> None:  # pragma: no cover - заглушка совместимости
        self.invoke()

    # -- размеры и отрисовка -----------------------------------------------

    def _label(self) -> str:
        if self._icon and self._text:
            return f"{self._icon}  {self._text}"
        return self._icon or self._text

    def _apply_size(self) -> None:
        label = self._label() or " "
        text_w, text_h = measure_text(self, self._font, label)
        width = text_w + self._padx * 2
        height = text_h + self._pady * 2
        if self._width_chars:
            try:
                import tkinter.font as tkfont

                zero = tkfont.Font(master=self, font=self._font).measure("0") or 8
            except Exception:
                zero = 8
            width = max(width, int(self._width_chars) * zero + self._padx)
        try:
            super().configure(width=width, height=height)
        except tk.TclError:
            pass
        self._redraw()

    def _current_fill(self) -> str:
        if self._explicit_fill:
            base = self._explicit_fill
            content = self._explicit_content or theme.color("on_surface")
        else:
            base = theme.color(self._fill_role)
            content = theme.color(self._content_role)
        if self._state == "disabled":
            return theme.disabled_container(self._fill_role if not self._explicit_fill else "on_surface")
        if self._alpha <= 0:
            return base
        from ui.theme import color_utils as cu

        return cu.blend(content, base, self._alpha)

    def _current_content(self) -> str:
        if self._state == "disabled":
            return theme.disabled_content("on_surface")
        if self._explicit_content:
            return self._explicit_content
        return theme.color(self._content_role)

    def _redraw(self) -> None:
        try:
            width = self.winfo_width()
            height = self.winfo_height()
        except tk.TclError:
            return
        if width <= 1 or height <= 1:
            return
        self.delete("all")
        radius = theme.radius(self._radius_name)
        outline_role = self._outline_role
        outline = theme.color(outline_role) if outline_role else ""
        if self._variant == "outlined" and self._state == "disabled":
            outline = theme.disabled_content("on_surface")
        fill = self._current_fill()
        if self._variant == "text" and not self._explicit_fill and self._alpha <= 0:
            fill = theme.color(self._parent_role)
        self._shape_id = draw_rounded_rect(
            self,
            1,
            1,
            width - 1,
            height - 1,
            radius,
            fill,
            outline=outline,
            width=1 if outline else 0,
            tags="bg",
        )
        label = self._label()
        if not label.strip():
            return
        anchor = self._anchor
        if anchor in ("w", tk.W, "left"):
            x, text_anchor = self._padx, "w"
        elif anchor in ("e", tk.E, "right"):
            x, text_anchor = width - self._padx, "e"
        else:
            x, text_anchor = width / 2, "center"
        self._text_id = self.create_text(
            x,
            height / 2,
            text=label,
            fill=self._current_content(),
            font=self._font,
            anchor=text_anchor,
        )

    # -- интерактивность ----------------------------------------------------

    def _bind_interactions(self) -> None:
        super().bind("<Enter>", self._on_enter, "+")
        super().bind("<Leave>", self._on_leave, "+")
        super().bind("<ButtonPress-1>", self._on_press, "+")
        super().bind("<ButtonRelease-1>", self._on_release, "+")

    def _animate_to(self, target: float) -> None:
        self._target_alpha = target
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except (tk.TclError, ValueError):
                pass
            self._anim_job = None
        step = 0.16
        if abs(self._alpha - target) < 0.01:
            self._alpha = target
            self._redraw()
            return
        self._alpha += step if target > self._alpha else -step
        self._alpha = max(0.0, min(0.25, self._alpha))
        self._redraw()
        try:
            self._anim_job = self.after(16, self._animate_to, target)
        except tk.TclError:
            self._anim_job = None

    def _on_enter(self, _event=None) -> None:
        if self._state == "disabled":
            return
        self._animate_to(theme_state("hover"))

    def _on_leave(self, _event=None) -> None:
        self._pressed = False
        self._animate_to(0.0)

    def _on_press(self, _event=None) -> None:
        if self._state == "disabled":
            return
        self._pressed = True
        self._animate_to(theme_state("press"))

    def _on_release(self, _event=None) -> None:
        if self._state == "disabled" or not self._pressed:
            return
        self._pressed = False
        try:
            inside = 0 <= self.winfo_pointerx() - self.winfo_rootx() <= self.winfo_width()
        except tk.TclError:
            inside = False
        self._animate_to(theme_state("hover") if inside else 0.0)
        if inside and callable(self._command):
            self._command()


def theme_state(name: str) -> float:
    """Прозрачность state layer по имени (для анимации кнопки)."""
    from ui.theme.tokens import STATE_OPACITY

    return STATE_OPACITY.get(name, 0.08)


# --- фабрики ----------------------------------------------------------------


def filled_button(master: tk.Misc, text: str, command=None, **kwargs) -> MaterialButton:
    kwargs.setdefault("variant", "filled")
    return MaterialButton(master, text, command, **kwargs)


def tonal_button(master: tk.Misc, text: str, command=None, **kwargs) -> MaterialButton:
    kwargs.setdefault("variant", "tonal")
    return MaterialButton(master, text, command, **kwargs)


def outlined_button(master: tk.Misc, text: str, command=None, **kwargs) -> MaterialButton:
    kwargs.setdefault("variant", "outlined")
    return MaterialButton(master, text, command, **kwargs)


def text_button(master: tk.Misc, text: str, command=None, **kwargs) -> MaterialButton:
    kwargs.setdefault("variant", "text")
    return MaterialButton(master, text, command, **kwargs)


def icon_button(master: tk.Misc, icon: str, command=None, **kwargs) -> MaterialButton:
    kwargs.setdefault("variant", "icon")
    kwargs.setdefault("padx", 10)
    kwargs.setdefault("pady", 8)
    return MaterialButton(master, text="", command=command, icon=icon, **kwargs)


def fab(master: tk.Misc, icon: str, command=None, **kwargs) -> MaterialButton:
    kwargs.setdefault("variant", "fab")
    return MaterialButton(master, text="", command=command, icon=icon, **kwargs)
