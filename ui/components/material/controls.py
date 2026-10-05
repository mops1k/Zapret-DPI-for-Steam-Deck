# -*- coding: utf-8 -*-
"""Элементы управления Material 3: switch, checkbox, radio, chip, slider.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Callable, Optional

import tkinter as tk

from ui.theme import theme

from .base import RoundedSurface, draw_rounded_rect


class _TogglableBase(tk.Frame):
    """Общая часть переключателей: кликабельная подпись и canvas-индикатор."""

    def __init__(self, master: tk.Misc, text: str = "", bg_role: str = "surface", **kwargs) -> None:
        super().__init__(master, bg=theme.color(bg_role), **kwargs)
        self._bg_role = bg_role
        self._enabled = True
        self._text = text

    def set_enabled(self, enabled: bool) -> None:
        """Включает/выключает элемент (disabled приглушает цвета)."""
        self._enabled = bool(enabled)
        self._refresh_enabled()
        self._redraw()

    def _refresh_enabled(self) -> None:  # pragma: no cover - переопределяется
        pass

    def _redraw(self) -> None:  # pragma: no cover - переопределяется
        pass


class MaterialSwitch(_TogglableBase):
    """Переключатель M3: дорожка + кружок с анимацией сдвига."""

    WIDTH_DP = 46
    HEIGHT_DP = 26
    KNOB_DP = 18

    def __init__(
        self,
        master: tk.Misc,
        text: str = "",
        *,
        variable: Optional[tk.Variable] = None,
        value: bool = False,
        command: Optional[Callable[[bool], None]] = None,
        bg_role: str = "surface",
        font=None,
    ) -> None:
        super().__init__(master, text, bg_role)
        self._command = command
        self._on = bool(value)
        self._variable = variable
        self._pos = 1.0 if self._on else 0.0
        self._anim_job = None

        self._canvas = tk.Canvas(
            self,
            width=theme.px(self.WIDTH_DP),
            height=theme.px(self.HEIGHT_DP),
            bg=theme.color(bg_role),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._canvas.pack(side=tk.LEFT)
        self._label: Optional[tk.Label] = None
        if text:
            self._label = tk.Label(
                self,
                text=text,
                **theme.text(font or "body_medium", bg_role=bg_role),
            )
            self._label.configure(cursor="hand2")
            self._label.pack(side=tk.LEFT, padx=(theme.space("sm"), 0))

        for target in (self._canvas, self._label):
            if target is None:
                continue
            target.bind("<Button-1>", self._on_click)
        if self._variable is not None:
            try:
                self._on = bool(self._variable.get())
                self._pos = 1.0 if self._on else 0.0
            except tk.TclError:
                pass
        self._canvas.bind("<Configure>", lambda _e: self._redraw())
        self._redraw()

    # -- API ----------------------------------------------------------------

    def get(self) -> bool:
        return self._on

    def set(self, value: bool, notify: bool = False) -> None:
        self._on = bool(value)
        self._animate_to(1.0 if self._on else 0.0)
        if self._variable is not None:
            try:
                self._variable.set(self._on)
            except tk.TclError:
                pass
        if notify and callable(self._command):
            self._command(self._on)

    def toggle(self) -> None:
        self.set(not self._on, notify=True)

    @property
    def variable(self) -> Optional[tk.Variable]:
        return self._variable

    # -- отрисовка ----------------------------------------------------------

    def _on_click(self, _event=None) -> None:
        if not self._enabled:
            return
        self.toggle()

    def _refresh_enabled(self) -> None:
        for widget in (self._canvas, self._label):
            if widget is None:
                continue
            try:
                widget.configure(cursor="hand2" if self._enabled else "arrow")
            except tk.TclError:
                pass

    def _animate_to(self, target: float) -> None:
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except (tk.TclError, ValueError):
                pass
            self._anim_job = None
        step = 0.2
        if abs(self._pos - target) < 0.02:
            self._pos = target
            self._redraw()
            return
        self._pos += step if target > self._pos else -step
        self._pos = max(0.0, min(1.0, self._pos))
        self._redraw()
        try:
            self._anim_job = self.after(16, self._animate_to, target)
        except tk.TclError:
            self._anim_job = None

    def _redraw(self) -> None:
        try:
            width = self._canvas.winfo_width()
            height = self._canvas.winfo_height()
        except tk.TclError:
            return
        if width <= 1 or height <= 1:
            return
        self._canvas.delete("all")
        on = self._pos > 0.5
        if not self._enabled:
            track = theme.disabled_container("on_surface")
            knob = theme.disabled_content("on_surface")
        else:
            track = theme.color("primary") if on else theme.color("surface_container_highest")
            knob = theme.color("on_primary") if on else theme.color("outline")
        draw_rounded_rect(
            self._canvas, 1, 1, width - 1, height - 1, height / 2, track, outline=""
        )
        if not on and self._enabled:
            draw_rounded_rect(
                self._canvas, 1, 1, width - 1, height - 1, height / 2,
                theme.color("surface_container_highest"), outline=theme.color("outline"), width=1,
            )
        knob_d = theme.px(self.KNOB_DP) + (theme.px(6) if on else 0)
        margin = (height - knob_d) / 2
        travel = width - knob_d - margin * 2
        cx = margin + knob_d / 2 + travel * self._pos
        r = knob_d / 2
        self._canvas.create_oval(cx - r, height / 2 - r, cx + r, height / 2 + r, fill=knob, outline="")


class MaterialCheckbox(_TogglableBase):
    """Флажок M3 со скруглённым квадратом и галочкой."""

    SIZE_DP = 20

    def __init__(
        self,
        master: tk.Misc,
        text: str = "",
        *,
        variable: Optional[tk.Variable] = None,
        value: bool = False,
        command: Optional[Callable[[bool], None]] = None,
        bg_role: str = "surface",
        font=None,
    ) -> None:
        super().__init__(master, text, bg_role)
        self._command = command
        self._checked = bool(value)
        self._variable = variable
        self._canvas = tk.Canvas(
            self,
            width=theme.px(self.SIZE_DP),
            height=theme.px(self.SIZE_DP),
            bg=theme.color(bg_role),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._canvas.pack(side=tk.LEFT, pady=theme.px(2))
        self._label: Optional[tk.Label] = None
        if text:
            self._label = tk.Label(
                self,
                text=text,
                justify="left",
                anchor="w",
                **theme.text(font or "body_medium", bg_role=bg_role),
            )
            self._label.configure(cursor="hand2")
            self._label.pack(side=tk.LEFT, padx=(theme.space("sm"), 0))
        for target in (self._canvas, self._label):
            if target is None:
                continue
            target.bind("<Button-1>", self._on_click)
        if self._variable is not None:
            try:
                self._checked = bool(self._variable.get())
            except tk.TclError:
                pass
        self._canvas.bind("<Configure>", lambda _e: self._redraw())
        self._redraw()

    def get(self) -> bool:
        return self._checked

    def set(self, value: bool, notify: bool = False) -> None:
        self._checked = bool(value)
        if self._variable is not None:
            try:
                self._variable.set(self._checked)
            except tk.TclError:
                pass
        self._redraw()
        if notify and callable(self._command):
            self._command(self._checked)

    def toggle(self) -> None:
        self.set(not self._checked, notify=True)

    def _on_click(self, _event=None) -> None:
        if self._enabled:
            self.toggle()

    def _refresh_enabled(self) -> None:
        for widget in (self._canvas, self._label):
            if widget is None:
                continue
            try:
                widget.configure(cursor="hand2" if self._enabled else "arrow")
            except tk.TclError:
                pass

    def _redraw(self) -> None:
        try:
            size = self._canvas.winfo_width()
        except tk.TclError:
            return
        if size <= 1:
            return
        self._canvas.delete("all")
        if not self._enabled:
            fill = theme.disabled_container("on_surface")
            outline = theme.disabled_content("on_surface")
            mark = theme.disabled_content("on_surface")
        elif self._checked:
            fill, outline, mark = theme.color("primary"), "", theme.color("on_primary")
        else:
            fill, outline, mark = theme.color("surface"), theme.color("outline"), ""
        draw_rounded_rect(self._canvas, 1, 1, size - 1, size - 1, theme.radius("xs"), fill, outline, 1 if outline else 0)
        if self._checked:
            self._canvas.create_text(
                size / 2, size / 2, text="✓", fill=mark, font=theme.font("label_large", weight="bold")
            )


class MaterialRadio(_TogglableBase):
    """Радиокнопка M3."""

    SIZE_DP = 20

    def __init__(
        self,
        master: tk.Misc,
        text: str = "",
        *,
        variable: Optional[tk.Variable] = None,
        value=None,
        command: Optional[Callable] = None,
        bg_role: str = "surface",
        font=None,
    ) -> None:
        super().__init__(master, text, bg_role)
        self._command = command
        self._value = value
        self._variable = variable
        self._canvas = tk.Canvas(
            self,
            width=theme.px(self.SIZE_DP),
            height=theme.px(self.SIZE_DP),
            bg=theme.color(bg_role),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._canvas.pack(side=tk.LEFT, pady=theme.px(2))
        self._label: Optional[tk.Label] = None
        if text:
            self._label = tk.Label(
                self,
                text=text,
                anchor="w",
                **theme.text(font or "body_medium", bg_role=bg_role),
            )
            self._label.configure(cursor="hand2")
            self._label.pack(side=tk.LEFT, padx=(theme.space("sm"), 0))
        for target in (self._canvas, self._label):
            if target is None:
                continue
            target.bind("<Button-1>", self._on_click)
        if self._variable is not None:
            self._trace = self._variable.trace_add("write", lambda *_: self._redraw())
        self._canvas.bind("<Configure>", lambda _e: self._redraw())
        self._redraw()

    def get(self):
        return self._variable.get() if self._variable is not None else self._value

    def set(self, notify: bool = True) -> None:
        if self._variable is not None:
            try:
                self._variable.set(self._value)
            except tk.TclError:
                pass
        self._redraw()
        if notify and callable(self._command):
            self._command(self._value)

    select = set

    def _on_click(self, _event=None) -> None:
        if self._enabled:
            self.set()

    def _refresh_enabled(self) -> None:
        for widget in (self._canvas, self._label):
            if widget is None:
                continue
            try:
                widget.configure(cursor="hand2" if self._enabled else "arrow")
            except tk.TclError:
                pass

    def _is_selected(self) -> bool:
        if self._variable is None:
            return False
        try:
            return self._variable.get() == self._value
        except tk.TclError:
            return False

    def _redraw(self) -> None:
        try:
            size = self._canvas.winfo_width()
        except tk.TclError:
            return
        if size <= 1:
            return
        self._canvas.delete("all")
        selected = self._is_selected()
        if not self._enabled:
            outline = theme.disabled_content("on_surface")
            fill = theme.disabled_content("on_surface")
        elif selected:
            outline, fill = theme.color("primary"), theme.color("primary")
        else:
            outline, fill = theme.color("outline"), ""
        r = size / 2 - 1
        self._canvas.create_oval(1, 1, size - 1, size - 1, outline=outline, width=2, fill=fill)
        if selected:
            inner = size * 0.28
            self._canvas.create_oval(
                size / 2 - inner, size / 2 - inner, size / 2 + inner, size / 2 + inner,
                fill=theme.color("on_primary"), outline="",
            )


class MaterialChip(RoundedSurface):
    """Чип M3 (filter/assist): скруглённая «таблетка» с текстом."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        *,
        selected: bool = False,
        command: Optional[Callable[[bool], None]] = None,
        icon: str = "",
        parent_role: str = "surface",
        **kwargs,
    ) -> None:
        fill_role = "secondary_container" if selected else parent_role
        super().__init__(
            master,
            radius="full",
            fill_role=fill_role,
            outline_role="" if selected else "outline_variant",
            parent_role=parent_role,
            **kwargs,
        )
        self._selected = bool(selected)
        self._command = command
        self._icon = icon
        label = f"{icon}  {text}" if icon else text
        self._label = tk.Label(
            self,
            text=label,
            cursor="hand2",
            **theme.text("label_large", bg_role=fill_role, fg_role="on_secondary_container" if selected else "on_surface_variant"),
        )
        self._label.pack(padx=theme.space("md"), pady=theme.space("sm") // 2)
        self._label.bind("<Button-1>", self._on_click)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda _e: self.set_state("hover"), add="+")
        self.bind("<Leave>", lambda _e: self.set_state("none"), add="+")

    @property
    def selected(self) -> bool:
        return self._selected

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self.set_fill_role("secondary_container" if self._selected else self._parent_role)
        self.set_outline_role("" if self._selected else "outline_variant")
        self._label.configure(
            bg=theme.color("secondary_container" if self._selected else self._parent_role),
            fg=theme.color("on_secondary_container" if self._selected else "on_surface_variant"),
        )

    def _on_click(self, _event=None) -> None:
        self.set_selected(not self._selected)
        if callable(self._command):
            self._command(self._selected)


class MaterialDivider(tk.Frame):
    """Горизонтальный разделитель M3."""

    def __init__(self, master: tk.Misc, bg_role: str = "surface", inset: int = 0) -> None:
        super().__init__(master, bg=theme.color(bg_role), height=1)
        self._line = tk.Frame(self, bg=theme.color("outline_variant"), height=1)
        self._line.pack(fill=tk.X, padx=inset)


class MaterialBadge(tk.Label):
    """Небольшой бейдж-счётчик или статус."""

    def __init__(self, master: tk.Misc, text: str, role: str = "error", bg_role: str = "surface") -> None:
        super().__init__(
            master,
            text=text,
            **theme.text("label_small", bg_role=role, fg_role="on_" + role if role != "surface" else "on_surface"),
        )
        self.configure(padx=theme.px(8), pady=theme.px(2))
        self._role = role

    def set_text(self, text: str) -> None:
        self.configure(text=text)


class MaterialSlider(tk.Canvas):
    """Слайдер M3 с перетаскиванием и поддержкой tk.Variable."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        from_: float = 0,
        to: float = 100,
        value: Optional[float] = None,
        variable: Optional[tk.Variable] = None,
        command: Optional[Callable[[float], None]] = None,
        width: int = 220,
        bg_role: str = "surface",
    ) -> None:
        super().__init__(
            master,
            width=theme.px(width),
            height=theme.px(28),
            bg=theme.color(bg_role),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._from = float(from_)
        self._to = float(to)
        self._command = command
        self._variable = variable
        self._value = float(value if value is not None else from_)
        if variable is not None:
            try:
                self._value = float(variable.get())
            except (tk.TclError, TypeError, ValueError):
                pass
        self.bind("<Button-1>", self._on_drag)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Configure>", lambda _e: self._redraw())
        self._redraw()

    # -- API ----------------------------------------------------------------

    def get(self) -> float:
        return self._value

    def set(self, value: float, notify: bool = False) -> None:
        self._value = max(self._from, min(self._to, float(value)))
        if self._variable is not None:
            try:
                self._variable.set(int(self._value) if float(self._value).is_integer() else self._value)
            except tk.TclError:
                pass
        self._redraw()
        if notify and callable(self._command):
            self._command(self._value)

    # -- отрисовка ----------------------------------------------------------

    def _ratio(self) -> float:
        span = self._to - self._from
        return 0.0 if span <= 0 else (self._value - self._from) / span

    def _on_drag(self, event) -> None:
        try:
            width = self.winfo_width()
        except tk.TclError:
            return
        if width <= 1:
            return
        ratio = max(0.0, min(1.0, (event.x - theme.px(10)) / max(1, width - theme.px(20))))
        self.set(self._from + ratio * (self._to - self._from), notify=True)

    def _redraw(self) -> None:
        try:
            width = self.winfo_width()
            height = self.winfo_height()
        except tk.TclError:
            return
        if width <= 1 or height <= 1:
            return
        self.delete("all")
        pad = theme.px(10)
        track_h = theme.px(4)
        y = height / 2
        draw_rounded_rect(self, pad, y - track_h / 2, width - pad, y + track_h / 2, track_h / 2, theme.color("surface_container_highest"))
        knob_x = pad + (width - pad * 2) * self._ratio()
        draw_rounded_rect(self, pad, y - track_h / 2, knob_x, y + track_h / 2, track_h / 2, theme.color("primary"))
        r = theme.px(9)
        self.create_oval(knob_x - r, y - r, knob_x + r, y + r, fill=theme.color("primary"), outline="")
