# -*- coding: utf-8 -*-
"""Индикаторы и обратная связь Material 3: прогресс, спиннер, snackbar, тултип.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Callable, Optional

import tkinter as tk

from ui.theme import theme

from .base import draw_rounded_rect


class LinearProgress(tk.Canvas):
    """Линейный прогресс M3: детерминированный и неопределённый."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        width: int = 240,
        bg_role: str = "surface",
        indeterminate: bool = False,
    ) -> None:
        super().__init__(
            master,
            height=theme.px(6),
            bg=theme.color(bg_role),
            highlightthickness=0,
            bd=0,
        )
        self._bg_role = bg_role
        self._value = 0.0
        self._indeterminate = indeterminate
        self._offset = 0.0
        self._job = None
        try:
            self.configure(width=theme.px(width))
        except tk.TclError:
            pass
        self.bind("<Configure>", lambda _e: self._redraw())
        if indeterminate:
            self.start()

    # -- API ----------------------------------------------------------------

    def set(self, value: float) -> None:
        """Значение 0…100."""
        self._value = max(0.0, min(100.0, float(value)))
        self._redraw()

    def start(self) -> None:
        self._indeterminate = True
        self._tick()

    def stop(self) -> None:
        self._indeterminate = False
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except (tk.TclError, ValueError):
                pass
            self._job = None
        self._redraw()

    # -- отрисовка ----------------------------------------------------------

    def _tick(self) -> None:
        if not self._indeterminate:
            return
        self._offset = (self._offset + 4) % 140
        self._redraw()
        try:
            self._job = self.after(24, self._tick)
        except tk.TclError:
            self._job = None

    def _redraw(self) -> None:
        try:
            width = self.winfo_width()
            height = self.winfo_height()
        except tk.TclError:
            return
        if width <= 1 or height <= 1:
            return
        self.delete("all")
        radius = height / 2
        draw_rounded_rect(self, 0, 0, width, height, radius, theme.color("surface_container_highest"))
        if self._indeterminate:
            seg = width * 0.35
            start = (self._offset / 140) * (width + seg) - seg
            draw_rounded_rect(
                self, max(0, start), 0, min(width, start + seg), height, radius, theme.color("primary")
            )
        else:
            filled = width * self._value / 100
            if filled > 1:
                draw_rounded_rect(self, 0, 0, filled, height, radius, theme.color("primary"))


class Spinner(tk.Canvas):
    """Круговой индикатор ожидания M3."""

    def __init__(self, master: tk.Misc, *, size: int = 32, bg_role: str = "surface") -> None:
        super().__init__(
            master,
            width=theme.px(size),
            height=theme.px(size),
            bg=theme.color(bg_role),
            highlightthickness=0,
            bd=0,
        )
        self._angle = 0
        self._job = None
        self.bind("<Configure>", lambda _e: self._redraw())
        self.start()

    def start(self) -> None:
        if self._job is None:
            self._tick()

    def stop(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except (tk.TclError, ValueError):
                pass
            self._job = None

    def _tick(self) -> None:
        self._angle = (self._angle + 20) % 360
        self._redraw()
        try:
            self._job = self.after(40, self._tick)
        except tk.TclError:
            self._job = None

    def _redraw(self) -> None:
        try:
            size = min(self.winfo_width(), self.winfo_height())
        except tk.TclError:
            return
        if size <= 1:
            return
        self.delete("all")
        pad = theme.px(3)
        self.create_arc(
            pad, pad, size - pad, size - pad,
            start=self._angle, extent=270,
            style=tk.ARC, width=theme.px(3),
            outline=theme.color("primary"),
        )


class Snackbar(tk.Frame):
    """Всплывающее сообщение внизу окна в стиле M3."""

    def __init__(self, master: tk.Misc, *, bg_role: str = "inverse_surface") -> None:
        super().__init__(master, bg=theme.color("surface"))
        self._bg_role = bg_role
        self._card = tk.Frame(self, bg=theme.color(bg_role))
        self._card.pack(fill=tk.X, padx=theme.space("md"), pady=theme.space("sm"))
        self._label = tk.Label(
            self._card,
            text="",
            anchor="w",
            justify="left",
            wraplength=theme.px(420),
            **theme.text("body_medium", bg_role=bg_role, fg_role="inverse_on_surface"),
        )
        self._label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=theme.space("md"), pady=theme.space("sm"))
        self._action: Optional[tk.Label] = None
        self._hide_job = None
        self._action_command: Optional[Callable] = None

    def show(
        self,
        message: str,
        *,
        role: Optional[str] = None,
        duration: int = 4000,
        action_text: str = "",
        action: Optional[Callable] = None,
    ) -> None:
        """Показывает сообщение; role перекрашивает карточку (error/success/…)."""
        card_role = role or self._bg_role
        self._card.configure(bg=theme.color(card_role))
        self._label.configure(
            text=message,
            bg=theme.color(card_role),
            fg=theme.color("on_" + card_role) if card_role in theme.scheme else theme.color("inverse_on_surface"),
        )
        if self._action is not None:
            self._action.destroy()
            self._action = None
        if action_text and action is not None:
            self._action_command = action
            self._action = tk.Label(
                self._card,
                text=action_text,
                cursor="hand2",
                **theme.text("label_large", bg_role=card_role, fg_role="inverse_primary"),
            )
            self._action.pack(side=tk.RIGHT, padx=theme.space("md"))
            self._action.bind("<Button-1>", lambda _e: self._run_action())
        self._cancel_hide()
        if duration > 0:
            try:
                self._hide_job = self.after(duration, self.hide)
            except tk.TclError:
                self._hide_job = None
        if not self.winfo_ismapped():
            self.pack(fill=tk.X, side=tk.BOTTOM)

    def hide(self) -> None:
        self._cancel_hide()
        try:
            self.pack_forget()
        except tk.TclError:
            pass

    def _run_action(self) -> None:
        if callable(self._action_command):
            self._action_command()
        self.hide()

    def _cancel_hide(self) -> None:
        if self._hide_job is not None:
            try:
                self.after_cancel(self._hide_job)
            except (tk.TclError, ValueError):
                pass
            self._hide_job = None


class Tooltip:
    """Всплывающая подсказка M3 для любого виджета."""

    def __init__(
        self,
        widget: tk.Misc,
        text: str,
        *,
        delay: int = 400,
        wraplength: int = 320,
        bg_role: str = "inverse_surface",
    ) -> None:
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength
        self.bg_role = bg_role
        self._tip: Optional[tk.Toplevel] = None
        self._job = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def set_text(self, text: str) -> None:
        self.text = text

    def _schedule(self, _event=None) -> None:
        self._cancel()
        try:
            self._job = self.widget.after(self.delay, self.show)
        except tk.TclError:
            self._job = None

    def _cancel(self) -> None:
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except (tk.TclError, ValueError):
                pass
            self._job = None

    def show(self) -> None:
        if self._tip is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + theme.px(6)
        except tk.TclError:
            return
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.configure(bg=theme.color(self.bg_role))
        label = tk.Label(
            tip,
            text=self.text,
            justify="left",
            wraplength=theme.px(self.wraplength),
            **theme.text("body_small", bg_role=self.bg_role, fg_role="inverse_on_surface"),
        )
        label.pack(padx=theme.space("md"), pady=theme.space("sm"))
        tip.update_idletasks()
        width = tip.winfo_width()
        try:
            tip.geometry(f"+{max(0, x - width // 2)}+{y}")
        except tk.TclError:
            pass
        self._tip = tip

    def hide(self, _event=None) -> None:
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None
