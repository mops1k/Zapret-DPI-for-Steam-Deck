# -*- coding: utf-8 -*-
"""Поля ввода и выпадающие списки Material 3.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence

import tkinter as tk

from ui.theme import theme

from .base import RoundedSurface


class MaterialTextField(tk.Frame):
    """Текстовое поле M3 (outlined/filled) с подписью и подсказкой.

    Настоящий ``tk.Entry`` доступен как ``self.entry``; методы get/insert/
    delete/config проксируются на него, поэтому поле совместимо со старым кодом.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        label: str = "",
        textvariable: Optional[tk.Variable] = None,
        show: Optional[str] = None,
        placeholder: str = "",
        width: int = 30,
        variant: str = "outlined",
        bg_role: str = "surface",
        font=None,
        on_change: Optional[Callable[[str], None]] = None,
        on_return: Optional[Callable] = None,
        justify: str = "left",
        state: str = "normal",
    ) -> None:
        super().__init__(master, bg=theme.color(bg_role))
        self._bg_role = bg_role
        self._variant = variant
        self._placeholder = placeholder
        self._showing_placeholder = False
        self._on_change = on_change
        self._entry_font = font or theme.font("body_medium")

        self._label: Optional[tk.Label] = None
        if label:
            self._label = tk.Label(self, text=label, anchor="w", **theme.text("label_medium", bg_role=bg_role, fg_role="on_surface_variant"))
            self._label.pack(fill=tk.X, pady=(0, theme.px(4)))

        self._box = RoundedSurface(
            self,
            radius="sm",
            fill_role="surface_container_high" if variant == "filled" else "surface",
            outline_role="" if variant == "filled" else "outline",
            parent_role=bg_role,
            autosize=False,
        )
        self._box.pack(fill=tk.X)

        self._var = textvariable
        self.entry = tk.Entry(
            self._box,
            textvariable=textvariable,
            show=show or "",
            font=self._entry_font,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            bg=theme.color("surface_container_high" if variant == "filled" else "surface"),
            fg=theme.color("on_surface"),
            insertbackground=theme.color("primary"),
            justify=justify,
            width=width,
            state=state,
        )
        self._pad = theme.px(12)
        self._entry_height = theme.px(30)
        self._window_id = self._box.create_window(self._pad, self._entry_height / 2 + theme.px(6), anchor="w", window=self.entry)
        self._box.configure(height=self._entry_height + theme.px(12))

        self._box.bind("<Configure>", self._resize_entry, add="+")
        self._box.bind("<Button-1>", lambda _e: self.entry.focus_set(), add="+")
        self.entry.bind("<FocusIn>", lambda _e: self._set_focus(True), add="+")
        self.entry.bind("<FocusOut>", lambda _e: self._set_focus(False), add="+")
        if on_change is not None:
            self.entry.bind("<KeyRelease>", lambda _e: on_change(self.entry.get()), add="+")
        if on_return is not None:
            self.entry.bind("<Return>", on_return, add="+")
        if placeholder:
            self._install_placeholder()

    # -- проксирование API Entry -------------------------------------------

    def get(self) -> str:
        if self._showing_placeholder:
            return ""
        return self.entry.get()

    def insert(self, index, text: str):
        self._clear_placeholder()
        return self.entry.insert(index, text)

    def delete(self, first, last=None):
        return self.entry.delete(first, last)

    def bind(self, sequence=None, func=None, add=None):  # noqa: D102 - API Tk
        return super().bind(sequence, func, add)

    def configure(self, cnf=None, **kwargs):  # noqa: D102 - API Tk
        entry_keys = {
            "textvariable", "show", "state", "justify", "foreground", "background",
            "insertbackground", "selectbackground", "selectforeground", "font", "width",
            "validate", "validatecommand", "invalidcommand",
        }
        entry_options = {k: v for k, v in (cnf or {}).items() if k in entry_keys}
        entry_options.update({k: v for k, v in kwargs.items() if k in entry_keys})
        if entry_options:
            self.entry.configure(**entry_options)
            if "font" in entry_options:
                self._entry_font = entry_options["font"]
        super_options = {k: v for k, v in kwargs.items() if k not in entry_keys}
        if super_options or (cnf and any(k not in entry_keys for k in cnf)):
            super().configure(**super_options)
        return None

    config = configure

    def cget(self, key):  # noqa: D102 - API Tk
        try:
            return self.entry.cget(key)
        except tk.TclError:
            return super().cget(key)

    def focus_set(self):  # noqa: D102 - API Tk
        self.entry.focus_set()

    def select_range(self, start, end):  # noqa: D102 - API Tk
        self.entry.select_range(start, end)

    def icursor(self, index):  # noqa: D102 - API Tk
        self.entry.icursor(index)

    def set_enabled(self, enabled: bool) -> None:
        self.entry.configure(state="normal" if enabled else "disabled")
        self._box.set_fill_role(
            ("surface_container_high" if self._variant == "filled" else "surface")
            if enabled
            else "surface_container_low"
        )

    # -- внутреннее ---------------------------------------------------------

    def _resize_entry(self, event=None) -> None:
        width = (event.width if event else self._box.winfo_width()) - self._pad * 2
        try:
            self._box.itemconfigure(self._window_id, width=max(theme.px(40), width))
        except tk.TclError:
            pass

    def _set_focus(self, focused: bool) -> None:
        if self._variant == "filled":
            return
        self._box.set_outline_role("primary" if focused else "outline")

    def _install_placeholder(self) -> None:
        def show_placeholder(*_args):
            if not self.entry.get():
                self._showing_placeholder = True
                self.entry.configure(fg=theme.color("on_surface_variant"))
                self.entry.insert(0, self._placeholder)

        def hide_placeholder(*_args):
            if self._showing_placeholder:
                self._showing_placeholder = False
                self.entry.delete(0, tk.END)
                self.entry.configure(fg=theme.color("on_surface"))

        show_placeholder()
        self.entry.bind("<FocusIn>", hide_placeholder, add="+")
        self.entry.bind("<FocusOut>", lambda _e: show_placeholder(), add="+")

    def _clear_placeholder(self) -> None:
        if self._showing_placeholder:
            self._showing_placeholder = False
            self.entry.delete(0, tk.END)
            self.entry.configure(fg=theme.color("on_surface"))


class MaterialDropdown(tk.Frame):
    """Выпадающий список M3 на базе tk.Menu."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        values: Sequence[str] = (),
        value: str = "",
        label: str = "",
        width: int = 24,
        bg_role: str = "surface",
        command: Optional[Callable[[str], None]] = None,
        font=None,
    ) -> None:
        super().__init__(master, bg=theme.color(bg_role))
        self._values = list(values)
        self._value = value or (self._values[0] if self._values else "")
        self._command = command
        self._bg_role = bg_role
        self._font = font or theme.font("body_medium")

        self._label: Optional[tk.Label] = None
        if label:
            self._label = tk.Label(self, text=label, anchor="w", **theme.text("label_medium", bg_role=bg_role, fg_role="on_surface_variant"))
            self._label.pack(fill=tk.X, pady=(0, theme.px(4)))

        self._button = RoundedSurface(
            self,
            radius="sm",
            fill_role="surface_container_high",
            outline_role="outline",
            parent_role=bg_role,
            autosize=False,
        )
        self._button.configure(height=theme.px(40), width=theme.px(60))
        self._button.pack(fill=tk.X)
        self._text = tk.Label(
            self._button,
            text=self._value or "—",
            anchor="w",
            **theme.text("body_medium", bg_role="surface_container_high"),
        )
        self._arrow = tk.Label(
            self._button,
            text="▾",
            **theme.text("body_medium", bg_role="surface_container_high", fg_role="on_surface_variant"),
        )
        self._text_window = self._button.create_window(theme.px(12), theme.px(20), anchor="w", window=self._text)
        self._arrow_window = self._button.create_window(theme.px(0), theme.px(20), anchor="e", window=self._arrow)
        self._button.bind("<Configure>", self._resize, add="+")
        for widget in (self._button, self._text, self._arrow):
            widget.bind("<Button-1>", self._open_menu, add="+")
            widget.bind("<Enter>", lambda _e: self._button.set_state("hover"), add="+")
            widget.bind("<Leave>", lambda _e: self._button.set_state("none"), add="+")
        self._menu: Optional[tk.Menu] = None

    # -- API ----------------------------------------------------------------

    def get(self) -> str:
        return self._value

    def set(self, value: str, notify: bool = False) -> None:
        self._value = value
        self._text.configure(text=value or "—")
        if notify and callable(self._command):
            self._command(self._value)

    def set_values(self, values: Sequence[str]) -> None:
        self._values = list(values)
        if self._value not in self._values:
            self.set(self._values[0] if self._values else "", notify=False)

    def _resize(self, event=None) -> None:
        width = (event.width if event else self._button.winfo_width()) - theme.px(28)
        try:
            self._button.itemconfigure(self._text_window, width=max(theme.px(40), width))
            self._button.itemconfigure(self._arrow_window, width=theme.px(28))
            self._button.coords(self._arrow_window, (event.width if event else self._button.winfo_width()) - theme.px(6), theme.px(20))
        except tk.TclError:
            pass

    def _open_menu(self, _event=None) -> None:
        if self._menu is not None:
            self._menu.destroy()
        self._menu = tk.Menu(
            self,
            tearoff=0,
            bg=theme.color("surface_container"),
            fg=theme.color("on_surface"),
            activebackground=theme.color("secondary_container"),
            activeforeground=theme.color("on_secondary_container"),
            bd=0,
            font=self._font,
        )
        for item in self._values:
            self._menu.add_command(label=item, command=lambda v=item: self.set(v, notify=True))
        try:
            self._menu.tk_popup(self._button.winfo_rootx(), self._button.winfo_rooty() + self._button.winfo_height())
        finally:
            self._menu.grab_release()


def search_field(master: tk.Misc, *, placeholder: str = "Поиск", on_change=None, bg_role: str = "surface", width: int = 28) -> MaterialTextField:
    """Поле поиска с иконкой и подсказкой."""
    field = MaterialTextField(
        master,
        placeholder=f"🔍  {placeholder}",
        on_change=on_change,
        bg_role=bg_role,
        width=width,
    )
    return field
