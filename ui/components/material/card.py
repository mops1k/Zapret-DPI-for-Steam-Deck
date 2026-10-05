# -*- coding: utf-8 -*-
"""Карточки Material 3: elevated, filled, outlined.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Optional

import tkinter as tk

from ui.theme import theme

from .base import RoundedPanel

#: Вариант карточки -> (роль фона, роль границы).
CARD_VARIANTS = {
    "elevated": ("surface_container_low", ""),
    "filled": ("surface_container_highest", ""),
    "outlined": ("surface", "outline_variant"),
    "plain": ("surface", ""),
}


class MaterialCard(RoundedPanel):
    """Карточка с необязательными заголовком, подзаголовком и зоной действий."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        variant: str = "elevated",
        title: str = "",
        subtitle: str = "",
        padding: Optional[int] = None,
        radius: str = "lg",
        parent_role: str = "surface",
        **kwargs,
    ) -> None:
        fill_role, outline_role = CARD_VARIANTS.get(variant, CARD_VARIANTS["elevated"])
        pad = theme.space("lg") if padding is None else int(padding)
        super().__init__(
            master,
            radius=radius,
            fill_role=fill_role,
            outline_role=outline_role,
            parent_role=parent_role,
            padding=(pad, pad),
            **kwargs,
        )
        self._fill_role = fill_role
        self._title = title
        self._subtitle = subtitle
        self._header: Optional[tk.Frame] = None
        self._title_label: Optional[tk.Label] = None
        self._subtitle_label: Optional[tk.Label] = None
        self._actions: Optional[tk.Frame] = None
        if title or subtitle:
            self._build_header()

    # -- структура ----------------------------------------------------------

    def _build_header(self) -> None:
        self._header = tk.Frame(self.body, bg=theme.color(self._fill_role))
        self._header.pack(fill=tk.X, pady=(0, theme.space("sm")))
        if self._title:
            self._title_label = tk.Label(
                self._header,
                text=self._title,
                anchor="w",
                justify="left",
                **theme.text("title_medium", bg_role=self._fill_role),
            )
            self._title_label.pack(fill=tk.X)
        if self._subtitle:
            self._subtitle_label = tk.Label(
                self._header,
                text=self._subtitle,
                anchor="w",
                justify="left",
                wraplength=theme.px(420),
                **theme.text("body_small", bg_role=self._fill_role, fg_role="on_surface_variant"),
            )
            self._subtitle_label.pack(fill=tk.X, pady=(theme.px(2), 0))

    def set_title(self, text: str) -> None:
        self._title = text
        if self._title_label is not None:
            self._title_label.configure(text=text)

    def set_subtitle(self, text: str) -> None:
        self._subtitle = text
        if self._subtitle_label is not None:
            self._subtitle_label.configure(text=text)

    @property
    def content(self) -> tk.Frame:
        """Контейнер содержимого карточки (под заголовком)."""
        return self.body

    def action_row(self) -> tk.Frame:
        """Контейнер для кнопок в нижней части карточки."""
        if self._actions is None:
            self._actions = tk.Frame(self.body, bg=theme.color(self._fill_role))
            self._actions.pack(fill=tk.X, pady=(theme.space("md"), 0))
        return self._actions


def section_label(master: tk.Misc, text: str, bg_role: str = "surface") -> tk.Label:
    """Подпись раздела (label-large, приглушённая)."""
    return tk.Label(
        master,
        text=text,
        anchor="w",
        **theme.text("label_large", bg_role=bg_role, fg_role="on_surface_variant"),
    )
