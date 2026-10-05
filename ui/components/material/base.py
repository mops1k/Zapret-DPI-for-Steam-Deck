# -*- coding: utf-8 -*-
"""Базовые примитивы Material 3 для Tk: скругления, измерение текста, панели.

Tk не умеет скругления, поэтому фон рисуется на Canvas полигоном со
сглаженными углами, а содержимое кладётся внутрь через ``create_window``.
Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence, Tuple

import tkinter as tk
import tkinter.font as tkfont

from ui.theme import theme

# --- геометрия --------------------------------------------------------------


def rounded_polygon_points(
    x1: float, y1: float, x2: float, y2: float, radius: float
) -> Sequence[float]:
    """Точки полигона со скруглёнными углами (для create_polygon smooth=True)."""
    r = max(0.0, min(float(radius), (x2 - x1) / 2, (y2 - y1) / 2))
    if r <= 0.5:
        return [x1, y1, x2, y1, x2, y2, x1, y2]
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


def draw_rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    fill: str,
    outline: str = "",
    width: int = 0,
    tags: str = "bg",
) -> int:
    """Рисует скруглённый прямоугольник и возвращает id элемента."""
    points = rounded_polygon_points(x1, y1, x2, y2, radius)
    return canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=max(8, int(radius)),
        fill=fill or "",
        outline=outline or "",
        width=width,
        tags=tags,
    )


def measure_text(widget: tk.Misc, font, text: str) -> Tuple[int, int]:
    """Ширина и высота текста в пикселях для указанного шрифта."""
    try:
        f = tkfont.Font(master=widget, font=font)
        lines = str(text).split("\n") or [""]
        width = max(f.measure(line) for line in lines)
        height = f.metrics("linespace") * len(lines)
        return int(width), int(height)
    except Exception:
        lines = str(text).split("\n") or [""]
        return max(1, max(len(line) for line in lines) * 8), 16 * len(lines)


def sync_canvas_bg(canvas: tk.Canvas, role: str = "surface") -> None:
    """Подкрашивает сам Canvas под цвет родителя, чтобы не было ореола."""
    try:
        canvas.configure(bg=theme.color(role), highlightthickness=0, bd=0)
    except tk.TclError:
        pass


# --- скруглённая поверхность ------------------------------------------------


class RoundedSurface(tk.Canvas):
    """Canvas со скруглённым фоном, поддерживающий state layer и границу.

    Это базис кнопок, карточек и полей: фон рисуется вручную, содержимое
    добавляется наследниками.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        radius: str = "md",
        fill_role: str = "surface_container",
        outline_role: str = "",
        parent_role: str = "surface",
        padding: Tuple[int, int] = (0, 0),
        width: Optional[int] = None,
        height: Optional[int] = None,
        autosize: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            highlightthickness=0,
            bd=0,
            bg=theme.color(parent_role),
            **kwargs,
        )
        self._radius_name = radius
        self._fill_role = fill_role
        self._outline_role = outline_role
        self._parent_role = parent_role
        self._padding = padding
        self._autosize = autosize
        self._shape_id: Optional[int] = None
        self._state_alpha: float = 0.0
        self._extra_items: list = []
        if width:
            self.configure(width=width)
        if height:
            self.configure(height=height)
        self.bind("<Configure>", self._on_configure)

    # -- свойства -----------------------------------------------------------

    @property
    def fill_role(self) -> str:
        return self._fill_role

    def set_fill_role(self, role: str, redraw: bool = True) -> None:
        self._fill_role = role
        if redraw:
            self._redraw()

    def set_outline_role(self, role: str, redraw: bool = True) -> None:
        self._outline_role = role
        if redraw:
            self._redraw()

    def set_radius(self, radius: str, redraw: bool = True) -> None:
        self._radius_name = radius
        if redraw:
            self._redraw()

    def set_state(self, state: str, redraw: bool = True) -> None:
        """state layer: 'hover', 'press', 'selected', 'none'."""
        from ui.theme.tokens import STATE_OPACITY

        self._state_alpha = STATE_OPACITY.get(state, 0.0) if state != "none" else 0.0
        if redraw:
            self._redraw()

    def refresh(self) -> None:
        """Перерисовка после смены темы."""
        sync_canvas_bg(self, self._parent_role)
        self._redraw()

    # -- отрисовка ----------------------------------------------------------

    def _current_fill(self) -> str:
        base = theme.color(self._fill_role)
        if self._state_alpha > 0:
            from ui.theme import color_utils as cu

            content = theme.on(self._fill_role) if self._fill_role in theme.scheme else theme.color("on_surface")
            return cu.blend(content, base, self._state_alpha)
        return base

    def _on_configure(self, _event=None) -> None:
        self._redraw()

    def _redraw(self) -> None:
        try:
            width = self.winfo_width()
            height = self.winfo_height()
        except tk.TclError:
            return
        if width <= 1 or height <= 1:
            return
        self.delete("bg")
        radius = theme.radius(self._radius_name)
        outline = theme.color(self._outline_role) if self._outline_role else ""
        self._shape_id = draw_rounded_rect(
            self,
            1,
            1,
            width - 1,
            height - 1,
            radius,
            self._current_fill(),
            outline=outline,
            width=1 if outline else 0,
        )
        self.tag_lower("bg")

    # -- удобства -----------------------------------------------------------

    def body_frame(self, bg_role: Optional[str] = None) -> tk.Frame:
        """Прозрачный Frame внутри поверхности (для содержимого)."""
        return tk.Frame(self, bg=theme.color(bg_role or self._fill_role))


class RoundedPanel(RoundedSurface):
    """Скруглённая панель-контейнер: содержимое живёт в ``self.body``."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        radius: str = "lg",
        fill_role: str = "surface_container_low",
        outline_role: str = "",
        parent_role: str = "surface",
        padding: Tuple[int, int] = (16, 16),
        autosize: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            radius=radius,
            fill_role=fill_role,
            outline_role=outline_role,
            parent_role=parent_role,
            padding=padding,
            autosize=autosize,
            **kwargs,
        )
        self._inner = tk.Frame(self, bg=theme.color(fill_role))
        self._window_id = self.create_window(
            padding[0], padding[1], anchor="nw", window=self._inner
        )
        if autosize:
            self._inner.bind("<Configure>", self._on_inner_configure, add="+")
            self.bind("<Configure>", self._on_panel_configure, add="+")

    @property
    def body(self) -> tk.Frame:
        """Контейнер для дочерних виджетов."""
        return self._inner

    def set_body_bg(self, role: str) -> None:
        try:
            self._inner.configure(bg=theme.color(role))
        except tk.TclError:
            pass

    def _on_inner_configure(self, _event=None) -> None:
        if not self._autosize:
            return
        try:
            needed_h = self._inner.winfo_reqheight() + self._padding[1] * 2
            current_h = self.winfo_height()
            if abs(needed_h - current_h) > 2:
                self.configure(height=needed_h)
        except tk.TclError:
            pass

    def _on_panel_configure(self, event=None) -> None:
        width = (event.width if event else self.winfo_width()) - self._padding[0] * 2
        try:
            self.itemconfigure(self._window_id, width=max(1, width))
        except tk.TclError:
            pass


# --- утилиты для содержимого ------------------------------------------------


def apply_state_bindings(
    widget: tk.Misc,
    surface: RoundedSurface,
    on_click: Optional[Callable] = None,
) -> None:
    """Навешивает hover/press state layer на поверхность и её содержимое."""

    def enter(_event=None):
        surface.set_state("hover")

    def leave(_event=None):
        surface.set_state("none")

    def press(_event=None):
        surface.set_state("press")

    def release(_event=None):
        surface.set_state("hover")

    for target in (surface, *surface.winfo_children()):
        target.bind("<Enter>", enter, add="+")
        target.bind("<Leave>", leave, add="+")
        target.bind("<ButtonPress-1>", press, add="+")
        target.bind("<ButtonRelease-1>", release, add="+")
        if on_click is not None:
            target.bind("<Button-1>", on_click, add="+")
