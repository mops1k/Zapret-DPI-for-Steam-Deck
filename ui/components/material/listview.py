# -*- coding: utf-8 -*-
"""Списки и таблицы Material 3.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import ttk

from ui.theme import theme

from .scroll import ThinScrollbar, bind_mousewheel


class MaterialListItem(tk.Frame):
    """Строка списка: иконка, заголовок, подпись и правый слот."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        *,
        subtitle: str = "",
        icon: str = "",
        bg_role: str = "surface_container_low",
        selected: bool = False,
        command: Optional[Callable] = None,
        padding: Optional[int] = None,
    ) -> None:
        super().__init__(master, bg=theme.color(bg_role))
        self._bg_role = bg_role
        self._base_bg = theme.color(bg_role)
        self._selected = selected
        self._command = command
        pad = theme.space("md") if padding is None else int(padding)
        self._pad = pad

        row = tk.Frame(self, bg=self._base_bg)
        row.pack(fill=tk.X, padx=pad, pady=theme.px(6))

        self._icon_label: Optional[tk.Label] = None
        if icon:
            self._icon_label = tk.Label(row, text=icon, **theme.text("title_medium", bg_role=bg_role, fg_role="on_surface_variant"))
            self._icon_label.pack(side=tk.LEFT, padx=(0, theme.space("md")))

        text_frame = tk.Frame(row, bg=self._base_bg)
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._title = tk.Label(text_frame, text=text, anchor="w", **theme.text("body_large", bg_role=bg_role))
        self._title.pack(fill=tk.X)
        self._subtitle: Optional[tk.Label] = None
        if subtitle:
            self._subtitle = tk.Label(
                text_frame,
                text=subtitle,
                anchor="w",
                justify="left",
                **theme.text("body_small", bg_role=bg_role, fg_role="on_surface_variant"),
            )
            self._subtitle.pack(fill=tk.X)

        self.trailing = tk.Frame(row, bg=self._base_bg)
        self.trailing.pack(side=tk.RIGHT)

        self._interactive = [self, row, text_frame, self._title]
        if self._icon_label is not None:
            self._interactive.append(self._icon_label)
        if self._subtitle is not None:
            self._interactive.append(self._subtitle)
        for widget in self._interactive:
            widget.bind("<Enter>", self._on_enter, add="+")
            widget.bind("<Leave>", self._on_leave, add="+")
            if command is not None:
                widget.bind("<Button-1>", lambda _e: command(), add="+")
                widget.configure(cursor="hand2")
        if self._selected:
            self._apply_bg(theme.color("secondary_container"))

    # -- API ----------------------------------------------------------------

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self._apply_bg(
            theme.color("secondary_container") if self._selected else self._base_bg
        )

    @property
    def selected(self) -> bool:
        return self._selected

    def set_text(self, text: str) -> None:
        self._title.configure(text=text)

    def set_subtitle(self, text: str) -> None:
        if self._subtitle is None:
            return
        self._subtitle.configure(text=text)

    def set_trailing(self, widget: tk.Widget) -> None:
        """Кладёт виджет в правый слот строки."""
        widget.pack(in_=self.trailing, side=tk.RIGHT)

    # -- внутреннее ---------------------------------------------------------

    def _apply_bg(self, color: str) -> None:
        self.configure(bg=color)
        for widget in self.winfo_children():
            widget.configure(bg=color)
            for child in widget.winfo_children():
                try:
                    if isinstance(child, tk.Label):
                        child.configure(bg=color)
                    else:
                        child.configure(bg=color)
                except tk.TclError:
                    continue
        if self._selected:
            fg = theme.color("on_secondary_container")
            self._title.configure(fg=fg)
            if self._subtitle is not None:
                self._subtitle.configure(fg=fg)
            if self._icon_label is not None:
                self._icon_label.configure(fg=fg)
        else:
            self._title.configure(fg=theme.color("on_surface"))
            if self._subtitle is not None:
                self._subtitle.configure(fg=theme.color("on_surface_variant"))
            if self._icon_label is not None:
                self._icon_label.configure(fg=theme.color("on_surface_variant"))

    def _on_enter(self, _event=None) -> None:
        if not self._selected:
            self._apply_bg(theme.state("surface_container_low", "hover"))

    def _on_leave(self, _event=None) -> None:
        if not self._selected:
            self._apply_bg(self._base_bg)


class MaterialList(tk.Frame):
    """Прокручиваемый список строк M3 с тонким скроллбаром."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        bg_role: str = "surface",
        item_bg_role: str = "surface_container_low",
        height: int = 240,
        **kwargs,
    ) -> None:
        super().__init__(master, bg=theme.color(bg_role), **kwargs)
        self._bg_role = bg_role
        self._item_bg_role = item_bg_role
        self._canvas = tk.Canvas(
            self,
            bg=theme.color(bg_role),
            highlightthickness=0,
            bd=0,
            height=theme.px(height),
        )
        self._scrollbar = ThinScrollbar(self, command=self._canvas.yview, bg_role=bg_role)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._inner = tk.Frame(self._canvas, bg=theme.color(bg_role))
        self._window_id = self._canvas.create_window(0, 0, anchor="nw", window=self._inner)
        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        bind_mousewheel(self._canvas, lambda step: self._canvas.yview_scroll(step, "units"))
        bind_mousewheel(self._inner, lambda step: self._canvas.yview_scroll(step, "units"))
        self.items: List[MaterialListItem] = []

    # -- API ----------------------------------------------------------------

    def add_item(self, text: str, **kwargs) -> MaterialListItem:
        kwargs.setdefault("bg_role", self._item_bg_role)
        item = MaterialListItem(self._inner, text, **kwargs)
        item.pack(fill=tk.X, pady=(0, 1))
        self.items.append(item)
        return item

    def add_widget(self, widget: tk.Widget) -> tk.Widget:
        widget.pack(in_=self._inner, fill=tk.X, pady=(0, 1))
        return widget

    def clear(self) -> None:
        for item in self.items:
            item.destroy()
        self.items.clear()

    def refresh(self) -> None:
        """Перекраска после смены темы."""
        self.configure(bg=theme.color(self._bg_role))
        self._canvas.configure(bg=theme.color(self._bg_role))
        self._inner.configure(bg=theme.color(self._bg_role))
        for item in self.items:
            item.configure(bg=theme.color(self._item_bg_role))

    # -- внутреннее ---------------------------------------------------------

    def _on_inner_configure(self, _event=None) -> None:
        try:
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        except tk.TclError:
            pass

    def _on_canvas_configure(self, event) -> None:
        try:
            self._canvas.itemconfigure(self._window_id, width=event.width)
        except tk.TclError:
            pass


class MaterialTable(tk.Frame):
    """Таблица M3 на ttk.Treeview с тонким скроллбаром и тегами строк."""

    def __init__(
        self,
        master: tk.Misc,
        columns: Sequence[Tuple[str, str, int]],
        *,
        height: int = 10,
        bg_role: str = "surface",
        selectmode: str = "browse",
        show: str = "headings",
        **kwargs,
    ) -> None:
        super().__init__(master, bg=theme.color(bg_role), **kwargs)
        self._bg_role = bg_role
        self._columns = list(columns)
        keys = [key for key, _heading, _width in self._columns]
        self.tree = ttk.Treeview(
            self,
            columns=keys,
            show=show,
            height=height,
            selectmode=selectmode,
            style="Treeview",
        )
        for key, heading, width in self._columns:
            self.tree.heading(key, text=heading, anchor="w")
            self.tree.column(key, width=theme.px(width), anchor="w", stretch=True)
        self._scrollbar = ThinScrollbar(self, command=self.tree.yview, bg_role=bg_role)
        self.tree.configure(yscrollcommand=self._scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # -- API ----------------------------------------------------------------

    def clear(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)

    def insert(self, values: Sequence, iid: Optional[str] = None, tags: Sequence[str] = (), index: str = "end") -> str:
        if iid is None:
            return self.tree.insert("", index, values=tuple(values), tags=tuple(tags))
        return self.tree.insert("", index, iid=iid, values=tuple(values), tags=tuple(tags))

    def set(self, iid: str, column: str, value) -> None:
        self.tree.set(iid, column, value)

    def get_selected(self) -> Optional[str]:
        selection = self.tree.selection()
        return selection[0] if selection else None

    def get_selected_values(self) -> Optional[tuple]:
        iid = self.get_selected()
        if iid is None:
            return None
        return tuple(self.tree.item(iid, "values"))

    def add_tag(self, name: str, *, foreground: Optional[str] = None, background: Optional[str] = None, font=None) -> None:
        """Настраивает цвет строки по тегу (например, вердикт стратегии)."""
        options = {}
        if foreground:
            options["foreground"] = theme.color(foreground) if not foreground.startswith("#") else foreground
        if background:
            options["background"] = theme.color(background) if not background.startswith("#") else background
        if font is not None:
            options["font"] = font
        self.tree.tag_configure(name, **options)

    def bind_select(self, handler: Callable) -> None:
        self.tree.bind("<<TreeviewSelect>>", handler, add="+")

    def bind_double_click(self, handler: Callable) -> None:
        self.tree.bind("<Double-1>", handler, add="+")

    def refresh(self) -> None:
        self.configure(bg=theme.color(self._bg_role))
