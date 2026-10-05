# -*- coding: utf-8 -*-
"""Тонкий скроллбар Material 3 для Canvas/Listbox/Text.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Callable, Optional

import tkinter as tk

from ui.theme import theme

from .base import draw_rounded_rect


class ThinScrollbar(tk.Canvas):
    """Скроллбар-«пилюля»: ползунок без стрелок, с перетаскиванием и колесом."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        command: Optional[Callable] = None,
        orientation: str = "vertical",
        thickness: int = 8,
        bg_role: str = "surface",
        **kwargs,
    ) -> None:
        self._orientation = orientation
        self._thickness = theme.px(thickness)
        if orientation == "vertical":
            super().__init__(
                master,
                width=self._thickness,
                highlightthickness=0,
                bd=0,
                bg=theme.color(bg_role),
                **kwargs,
            )
        else:
            super().__init__(
                master,
                height=self._thickness,
                highlightthickness=0,
                bd=0,
                bg=theme.color(bg_role),
                **kwargs,
            )
        self._command = command
        self._first = 0.0
        self._last = 1.0
        self._drag_offset = 0.0
        self._dragging = False
        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    # -- интерфейс Tk Scrollbar --------------------------------------------

    def set(self, first, last) -> None:
        """Вызывается прокручиваемым виджетом."""
        self._first = float(first)
        self._last = float(last)
        self._redraw()

    def get(self):
        return (self._first, self._last)

    # -- отрисовка ----------------------------------------------------------

    def _length(self) -> int:
        return self.winfo_height() if self._orientation == "vertical" else self.winfo_width()

    def _redraw(self) -> None:
        length = self._length()
        if length <= 1:
            return
        self.delete("all")
        thumb_start = self._first * length
        thumb_end = self._last * length
        if thumb_end - thumb_start < theme.px(24):
            thumb_end = min(length, thumb_start + theme.px(24))
        thumb = theme.color("outline")
        if self._orientation == "vertical":
            draw_rounded_rect(self, 0, thumb_start, self._thickness, thumb_end, self._thickness / 2, thumb)
        else:
            draw_rounded_rect(self, thumb_start, 0, thumb_end, self._thickness, self._thickness / 2, thumb)

    # -- взаимодействие -----------------------------------------------------

    def _on_press(self, event) -> None:
        length = self._length()
        if length <= 1:
            return
        pos = event.y if self._orientation == "vertical" else event.x
        thumb_start = self._first * length
        thumb_end = self._last * length
        if thumb_start <= pos <= thumb_end:
            self._dragging = True
            self._drag_offset = pos - thumb_start
        else:
            self._dragging = True
            self._drag_offset = (thumb_end - thumb_start) / 2
            self._scroll_to(pos - self._drag_offset, length)

    def _on_drag(self, event) -> None:
        if not self._dragging:
            return
        length = self._length()
        pos = event.y if self._orientation == "vertical" else event.x
        self._scroll_to(pos - self._drag_offset, length)

    def _on_release(self, _event=None) -> None:
        self._dragging = False

    def _scroll_to(self, offset: float, length: int) -> None:
        if self._command is None:
            return
        span = self._last - self._first
        ratio = max(0.0, min(1.0 - span, offset / max(1, length)))
        self._command("moveto", ratio)


def bind_mousewheel(widget: tk.Misc, handler: Callable[[int], None]) -> None:
    """Привязывает колесо мыши (X11: Button-4/5, Windows/macOS: MouseWheel)."""

    def on_wheel(event):
        if getattr(event, "num", None) == 4:
            handler(-1)
        elif getattr(event, "num", None) == 5:
            handler(1)
        else:
            handler(-1 if getattr(event, "delta", 0) > 0 else 1)

    widget.bind("<MouseWheel>", on_wheel, add="+")
    widget.bind("<Button-4>", on_wheel, add="+")
    widget.bind("<Button-5>", on_wheel, add="+")
