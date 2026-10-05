# -*- coding: utf-8 -*-
"""Верхняя панель приложения (top app bar) Material 3.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence, Tuple

import tkinter as tk

from ui.theme import theme

from .button import MaterialButton
from .feedback import Tooltip


class TopAppBar(tk.Frame):
    """Панель с заголовком, ведущими иконками и действиями справа."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        title: str = "",
        subtitle: str = "",
        bg_role: str = "surface",
        leading: Optional[Sequence[Tuple[str, Callable, str]]] = None,
        actions: Optional[Sequence[Tuple[str, Callable, str]]] = None,
        show_title: bool = True,
    ) -> None:
        super().__init__(master, bg=theme.color(bg_role))
        self._bg_role = bg_role
        self._leading_frame = tk.Frame(self, bg=theme.color(bg_role))
        self._leading_frame.pack(side=tk.LEFT)
        self._title_frame = tk.Frame(self, bg=theme.color(bg_role))
        self._title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._actions_frame = tk.Frame(self, bg=theme.color(bg_role))
        self._actions_frame.pack(side=tk.RIGHT)

        self._title_label: Optional[tk.Label] = None
        self._subtitle_label: Optional[tk.Label] = None
        if show_title:
            self._title_label = tk.Label(
                self._title_frame,
                text=title,
                anchor="w",
                **theme.text("title_large", bg_role=bg_role),
            )
            self._title_label.pack(fill=tk.X)
        if subtitle:
            self._subtitle_label = tk.Label(
                self._title_frame,
                text=subtitle,
                anchor="w",
                **theme.text("body_small", bg_role=bg_role, fg_role="on_surface_variant"),
            )
            self._subtitle_label.pack(fill=tk.X)

        for icon, command, tip in leading or ():
            self.add_leading(icon, command, tip)
        for icon, command, tip in actions or ():
            self.add_action(icon, command, tip)

    # -- API ----------------------------------------------------------------

    @property
    def leading(self) -> tk.Frame:
        """Контейнер ведущих виджетов (слева от заголовка)."""
        return self._leading_frame

    @property
    def actions(self) -> tk.Frame:
        """Контейнер действий (справа)."""
        return self._actions_frame

    def add_leading_widget(self, widget: tk.Widget, padx=(0, 4)) -> tk.Widget:
        widget.pack(in_=self._leading_frame, side=tk.LEFT, padx=padx)
        return widget

    def add_action_widget(self, widget: tk.Widget, padx=(4, 0)) -> tk.Widget:
        widget.pack(in_=self._actions_frame, side=tk.RIGHT, padx=padx)
        return widget

    def set_title(self, text: str) -> None:
        if self._title_label is not None:
            self._title_label.configure(text=text)

    def set_subtitle(self, text: str) -> None:
        if self._subtitle_label is not None:
            self._subtitle_label.configure(text=text)

    def add_leading(self, icon: str, command: Callable, tooltip: str = "") -> MaterialButton:
        button = MaterialButton(
            self._leading_frame,
            text="",
            icon=icon,
            command=command,
            variant="icon",
            parent_role=self._bg_role,
            padx=theme.px(10),
            pady=theme.px(8),
        )
        button.pack(side=tk.LEFT, padx=(0, theme.px(4)))
        if tooltip:
            Tooltip(button, tooltip)
        return button

    def add_action(self, icon: str, command: Callable, tooltip: str = "") -> MaterialButton:
        button = MaterialButton(
            self._actions_frame,
            text="",
            icon=icon,
            command=command,
            variant="icon",
            parent_role=self._bg_role,
            padx=theme.px(10),
            pady=theme.px(8),
        )
        button.pack(side=tk.RIGHT, padx=(theme.px(4), 0))
        if tooltip:
            Tooltip(button, tooltip)
        return button

    def add_widget(self, widget: tk.Widget, side: str = "right") -> tk.Widget:
        widget.pack(in_=self._actions_frame, side=side, padx=(theme.px(4), 0))
        return widget

    def refresh(self) -> None:
        for frame in (self, self._leading_frame, self._title_frame, self._actions_frame):
            frame.configure(bg=theme.color(self._bg_role))
        if self._title_label is not None:
            self._title_label.configure(bg=theme.color(self._bg_role), fg=theme.color("on_surface"))
        if self._subtitle_label is not None:
            self._subtitle_label.configure(
                bg=theme.color(self._bg_role), fg=theme.color("on_surface_variant")
            )


def toolbar(
    master: tk.Misc,
    *,
    bg_role: str = "surface",
    items: Sequence[Tuple[str, str, Callable]] = (),
) -> tk.Frame:
    """Ряд текстовых кнопок (вторичные действия экрана)."""
    frame = tk.Frame(master, bg=theme.color(bg_role))
    for text, _icon, command in items:
        button = MaterialButton(
            frame,
            text=text,
            command=command,
            variant="text",
            parent_role=bg_role,
            padx=theme.px(12),
            pady=theme.px(8),
        )
        button.pack(side=tk.LEFT, padx=(0, theme.px(4)))
    return frame
