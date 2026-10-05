# -*- coding: utf-8 -*-
"""Менеджер темы Material 3 для всего приложения.

Единая точка доступа к токенам: цветам, шрифтам, отступам, радиусам и
ttk-стилям. Режим (тёмный/светлый) хранится в ``utils/theme.txt`` рядом с
остальными настройками менеджера. Проект «Zapret DPI Manager»
© Aleksandr Kvintilyanov.
"""
from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import color_utils as cu
from .fonts import get_font_resolver
from .tokens import (
    BOLD_ROLES,
    DURATION,
    ELEVATION_SURFACE,
    RADII,
    SPACING,
    STATE_OPACITY,
    TYPE_ALIASES,
    TYPE_SCALE,
    on_role,
    scheme_for,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_DIR = PROJECT_ROOT / "utils"
SETTINGS_FILE = SETTINGS_DIR / "theme.txt"

VALID_MODES = ("dark", "light")
DEFAULT_MODE = "dark"

#: Имя шрифта по умолчанию, если резолвер ничего не нашёл.
_FALLBACK_FAMILY = "TkDefaultFont"


def detect_scale(root: Optional[tk.Misc]) -> float:
    """Коэффициент логического масштаба интерфейса (1.0 при неудаче)."""
    if root is None:
        return 1.0
    try:
        from core.tk_scale_lab_helpers import logical_ui_scale

        value = float(logical_ui_scale(root))
    except Exception:
        return 1.0
    if 0.5 <= value <= 4.0:
        return value
    return 1.0


class ThemeManager:
    """Токены и применение темы M3 к Tk/ttk."""

    def __init__(self) -> None:
        self._mode: str = DEFAULT_MODE
        self._root: Optional[tk.Misc] = None
        self._scale: float = 1.0
        self._listeners: List[Callable[[str], None]] = []
        self._families: Dict[str, str] = {}
        self._ttk_configured = False

    # -- состояние ----------------------------------------------------------

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_dark(self) -> bool:
        return self._mode == "dark"

    @property
    def scale(self) -> float:
        return self._scale

    @property
    def settings_path(self) -> Path:
        return SETTINGS_FILE

    @property
    def scheme(self) -> Dict[str, str]:
        return scheme_for(self._mode)

    # -- масштабирование ----------------------------------------------------

    def px(self, value: float) -> int:
        """dp -> пиксели с учётом логического масштаба."""
        return int(round(float(value) * self._scale))

    def space(self, step: str = "md") -> int:
        """Отступ по имени шага (xs, sm, md, lg, xl, xxl)."""
        return self.px(SPACING.get(step, SPACING["md"]))

    def radius(self, name: str = "md") -> int:
        """Радиус скругления по имени (none, xs, sm, md, lg, xl, full)."""
        return self.px(RADII.get(name, RADII["md"]))

    def duration(self, name: str = "medium") -> int:
        return int(DURATION.get(name, DURATION["medium"]))

    # -- цвета --------------------------------------------------------------

    def color(self, role: str, fallback: str = "#000000") -> str:
        """Цвет роли текущей схемы."""
        value = self.scheme.get(role)
        if value:
            return value
        # Роль могла быть передана как готовый hex.
        if isinstance(role, str) and role.startswith("#"):
            return role
        return fallback

    def on(self, role: str) -> str:
        """Контрастный цвет для роли-контейнера."""
        return self.color(on_role(role))

    def state(self, role: str, state: str = "hover") -> str:
        """Цвет state layer: контент поверх контейнера с прозрачностью M3."""
        opacity = STATE_OPACITY.get(state, STATE_OPACITY["hover"])
        return cu.state_layer(self.color(role), self.on(role), opacity)

    def blend(self, foreground: str, background: str, alpha: float) -> str:
        return cu.blend(foreground, background, alpha)

    def mix(self, color_a: str, color_b: str, t: float) -> str:
        return cu.mix(color_a, color_b, t)

    def readable_on(self, background: str) -> str:
        return cu.readable_on(background, self.color("on_surface"), self.color("on_primary"))

    def elevation(self, level: int = 1) -> str:
        """Роль поверхности для уровня elevation (0…5)."""
        return self.color(ELEVATION_SURFACE.get(int(level), ELEVATION_SURFACE[1]))

    def disabled_content(self, role: str = "on_surface") -> str:
        return cu.blend(
            self.color(role),
            self.color("surface"),
            STATE_OPACITY["disabled_content"],
        )

    def disabled_container(self, role: str = "on_surface") -> str:
        return cu.blend(
            self.color(role),
            self.color("surface"),
            STATE_OPACITY["disabled_container"],
        )

    # -- шрифты -------------------------------------------------------------

    def font(
        self,
        role: str = "body_medium",
        weight: Optional[str] = None,
        mono: bool = False,
        family_kind: Optional[str] = None,
    ) -> tuple:
        """Кортеж шрифта Tk для типографической роли.

        role — имя роли M3 или синоним (title, body, label…); если передан
        готовый кортеж шрифта, он возвращается как есть.
        weight — 'normal'/'bold'; по умолчанию роль решает сама.
        mono — моноширинное семейство (логи, отчёты).
        family_kind — явное семейство: sans/display/mono/emoji.
        """
        if isinstance(role, (tuple, list)):
            return tuple(role)
        key = TYPE_ALIASES.get(role, role)
        size_pt, _line = TYPE_SCALE.get(key, TYPE_SCALE["body_medium"])
        if weight is None:
            weight = "bold" if key in BOLD_ROLES else "normal"
        kind = family_kind or ("mono" if mono else ("display" if key.startswith("display") else "sans"))
        size = max(8, int(round(size_pt * self._scale)))
        return get_font_resolver().tuple_for(self._root, size, weight, kind)

    def line_height(self, role: str = "body_medium") -> int:
        key = TYPE_ALIASES.get(role, role)
        return self.px(TYPE_SCALE.get(key, TYPE_SCALE["body_medium"])[1])

    def text(
        self,
        role: str = "body_medium",
        weight: Optional[str] = None,
        mono: bool = False,
        bg_role: str = "surface",
        fg_role: str = "on_surface",
    ) -> Dict[str, object]:
        """Готовые аргументы для tk.Label/tk.Text: font, bg, fg.

        role — имя роли M3 или готовый кортеж шрифта (тогда он используется
        без изменений) — компоненты часто передают сюда уже собранный шрифт.

        Пример::

            tk.Label(parent, text="Готово", **theme.text("title_medium"))
        """
        font_value = tuple(role) if isinstance(role, (tuple, list)) else self.font(role, weight=weight, mono=mono)
        return {
            "font": font_value,
            "bg": self.color(bg_role),
            "fg": self.color(fg_role),
        }

    def family(self, kind: str = "sans") -> str:
        if not self._families:
            self._families = get_font_resolver().resolve(self._root)
        return self._families.get(kind, _FALLBACK_FAMILY)

    # -- подписки -----------------------------------------------------------

    def subscribe(self, callback: Callable[[str], None]) -> None:
        """Подписка на смену темы: callback(mode)."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[str], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self) -> None:
        for callback in list(self._listeners):
            try:
                callback(self._mode)
            except Exception as exc:  # подписчик не должен ломать смену темы
                print(f"Тема: ошибка подписчика {callback!r}: {exc}")

    # -- жизненный цикл -----------------------------------------------------

    def attach(self, root: tk.Misc) -> None:
        """Привязывает менеджер к корневому окну и применяет тему."""
        self._root = root
        self._scale = detect_scale(root)
        self._families = get_font_resolver().resolve(root)
        self.apply(root)

    def apply(self, root: Optional[tk.Misc] = None) -> None:
        """Применяет текущую схему к корневому окну и ttk-стилям."""
        target = root or self._root
        if target is None:
            return
        self._root = target
        try:
            target.configure(bg=self.color("surface"))
        except tk.TclError:
            pass
        self._apply_tk_defaults(target)
        self._apply_ttk(target)
        self._ttk_configured = True

    def set_mode(self, mode: str, save: bool = True, notify: bool = True) -> str:
        """Переключает режим темы; возвращает фактический режим."""
        normalized = str(mode).strip().lower()
        if normalized not in VALID_MODES:
            normalized = DEFAULT_MODE
        changed = normalized != self._mode
        self._mode = normalized
        if save:
            self.save()
        if changed or notify:
            self.apply()
            if notify:
                self._notify()
        return self._mode

    def toggle_mode(self) -> str:
        """Переключает тёмную/светлую тему."""
        return self.set_mode("light" if self._mode == "dark" else "dark")

    def load(self) -> str:
        """Читает режим из utils/theme.txt (или из ZAPRET_THEME)."""
        env_mode = os.environ.get("ZAPRET_THEME", "").strip().lower()
        if env_mode in VALID_MODES:
            self._mode = env_mode
            return self._mode
        try:
            raw = SETTINGS_FILE.read_text(encoding="utf-8").strip().lower()
        except OSError:
            self._mode = DEFAULT_MODE
            return self._mode
        self._mode = raw if raw in VALID_MODES else DEFAULT_MODE
        return self._mode

    def save(self) -> bool:
        """Сохраняет режим в utils/theme.txt."""
        try:
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(self._mode + "\n", encoding="utf-8")
            return True
        except OSError as exc:
            print(f"Тема: не удалось сохранить режим: {exc}")
            return False

    # -- применение к классическим виджетам --------------------------------

    def _apply_tk_defaults(self, root: tk.Misc) -> None:
        """Дефолты для tk-виджетов без явных цветов (Listbox, Text, Menu…)."""
        surface = self.color("surface")
        on_surface = self.color("on_surface")
        container = self.color("surface_container")
        primary = self.color("primary")
        on_primary = self.color("on_primary")
        outline = self.color("outline_variant")
        defaults = {
            "*Background": surface,
            "*Foreground": on_surface,
            "*Font": self.font("body_medium"),
            "*Listbox.background": self.color("surface_container_low"),
            "*Listbox.foreground": on_surface,
            "*Listbox.selectBackground": self.color("primary_container"),
            "*Listbox.selectForeground": self.color("on_primary_container"),
            "*Listbox.highlightThickness": 0,
            "*Listbox.borderWidth": 0,
            "*Text.background": self.color("surface_container_low"),
            "*Text.foreground": on_surface,
            "*Text.insertBackground": primary,
            "*Text.selectBackground": self.color("primary_container"),
            "*Text.selectForeground": self.color("on_primary_container"),
            "*Text.borderWidth": 0,
            "*Entry.background": self.color("surface_container_highest"),
            "*Entry.foreground": on_surface,
            "*Entry.insertBackground": primary,
            "*Entry.selectBackground": self.color("primary_container"),
            "*Entry.selectForeground": self.color("on_primary_container"),
            "*Menu.background": container,
            "*Menu.foreground": on_surface,
            "*Menu.activeBackground": self.color("secondary_container"),
            "*Menu.activeForeground": self.color("on_secondary_container"),
            "*Menu.borderWidth": 0,
            "*Menu.relief": "flat",
            "*Canvas.background": surface,
            "*Canvas.highlightThickness": 0,
            "*Scrollbar.background": self.color("surface_container_highest"),
            "*Scrollbar.troughColor": surface,
            "*Scrollbar.borderWidth": 0,
            "*Scrollbar.highlightThickness": 0,
            "*Toplevel.background": surface,
            "*selectBackground": self.color("primary_container"),
            "*selectForeground": self.color("on_primary_container"),
            "*highlightBackground": outline,
            "*highlightColor": primary,
            "*Button.font": self.font("label_large"),
            "*Label.font": self.font("body_medium"),
        }
        for pattern, value in defaults.items():
            try:
                root.option_add(pattern, value)
            except tk.TclError:
                continue
        # Кнопки по умолчанию: тональная поверхность.
        for pattern, value in {
            "*Button.background": self.color("secondary_container"),
            "*Button.foreground": self.color("on_secondary_container"),
            "*Button.activeBackground": self.state("secondary_container", "press"),
            "*Button.activeForeground": self.color("on_secondary_container"),
            "*Button.relief": "flat",
            "*Button.borderWidth": 0,
            "*Button.highlightThickness": 0,
        }.items():
            try:
                root.option_add(pattern, value)
            except tk.TclError:
                continue
        _ = on_primary  # роль используется компонентами, оставлена для явности

    # -- применение к ttk ---------------------------------------------------

    def _apply_ttk(self, root: tk.Misc) -> None:
        try:
            from tkinter import ttk
        except ImportError:  # pragma: no cover - tkinter всегда с ttk
            return
        try:
            style = ttk.Style(root)
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            return

        surface = self.color("surface")
        on_surface = self.color("on_surface")
        on_variant = self.color("on_surface_variant")
        container_low = self.color("surface_container_low")
        container = self.color("surface_container")
        container_high = self.color("surface_container_high")
        container_highest = self.color("surface_container_highest")
        primary = self.color("primary")
        on_primary = self.color("on_primary")
        primary_container = self.color("primary_container")
        on_primary_container = self.color("on_primary_container")
        secondary_container = self.color("secondary_container")
        on_secondary_container = self.color("on_secondary_container")
        outline = self.color("outline")
        outline_variant = self.color("outline_variant")
        error = self.color("error")

        body = self.font("body_medium")
        label = self.font("label_large")
        title = self.font("title_medium")

        def configure(name: str, **options) -> None:
            try:
                style.configure(name, **options)
            except tk.TclError:
                pass

        def map_style(name: str, **options) -> None:
            try:
                style.map(name, **options)
            except tk.TclError:
                pass

        configure("TFrame", background=surface, borderwidth=0)
        configure("Card.TFrame", background=container_low, relief="flat", borderwidth=0)
        configure("CardHigh.TFrame", background=container, relief="flat", borderwidth=0)
        configure("Surface.TFrame", background=container, borderwidth=0)

        configure("TLabel", background=surface, foreground=on_surface, font=body)
        configure("Card.TLabel", background=container_low, foreground=on_surface, font=body)
        configure("CardHigh.TLabel", background=container, foreground=on_surface, font=body)
        configure("Title.TLabel", background=surface, foreground=on_surface, font=title)
        configure("Subtitle.TLabel", background=surface, foreground=on_variant, font=body)
        configure("Primary.TLabel", background=surface, foreground=primary, font=label)
        configure("Error.TLabel", background=surface, foreground=error, font=label)

        configure(
            "TButton",
            background=secondary_container,
            foreground=on_secondary_container,
            font=label,
            borderwidth=0,
            focusthickness=0,
            relief="flat",
            padding=(self.px(16), self.px(10)),
        )
        map_style(
            "TButton",
            background=[
                ("disabled", self.disabled_container("on_surface")),
                ("pressed", self.state("secondary_container", "press")),
                ("active", self.state("secondary_container", "hover")),
            ],
            foreground=[("disabled", self.disabled_content("on_surface"))],
        )
        configure(
            "Primary.TButton",
            background=primary,
            foreground=on_primary,
            font=label,
            borderwidth=0,
            relief="flat",
            padding=(self.px(16), self.px(10)),
        )
        map_style(
            "Primary.TButton",
            background=[
                ("disabled", self.disabled_container("on_surface")),
                ("pressed", self.state("primary", "press")),
                ("active", self.state("primary", "hover")),
            ],
            foreground=[("disabled", self.disabled_content("on_surface"))],
        )
        configure(
            "Tonal.TButton",
            background=primary_container,
            foreground=on_primary_container,
            font=label,
            borderwidth=0,
            relief="flat",
            padding=(self.px(16), self.px(10)),
        )
        map_style(
            "Tonal.TButton",
            background=[
                ("disabled", self.disabled_container("on_surface")),
                ("pressed", self.state("primary_container", "press")),
                ("active", self.state("primary_container", "hover")),
            ],
        )

        configure(
            "TEntry",
            fieldbackground=container_highest,
            background=container_highest,
            foreground=on_surface,
            insertcolor=primary,
            bordercolor=outline_variant,
            lightcolor=outline_variant,
            darkcolor=outline_variant,
            borderwidth=0,
            padding=(self.px(10), self.px(8)),
        )
        map_style(
            "TEntry",
            bordercolor=[("focus", primary)],
            lightcolor=[("focus", primary)],
            darkcolor=[("focus", primary)],
            fieldbackground=[("disabled", container)],
        )
        configure(
            "TCombobox",
            fieldbackground=container_high,
            background=container_high,
            foreground=on_surface,
            arrowcolor=on_variant,
            bordercolor=outline_variant,
            lightcolor=outline_variant,
            darkcolor=outline_variant,
            borderwidth=0,
            padding=(self.px(8), self.px(6)),
        )
        map_style(
            "TCombobox",
            fieldbackground=[("readonly", container_high), ("disabled", container)],
            bordercolor=[("focus", primary)],
            arrowcolor=[("active", primary)],
        )
        configure(
            "TSpinbox",
            fieldbackground=container_highest,
            background=container_highest,
            foreground=on_surface,
            arrowcolor=on_variant,
            bordercolor=outline_variant,
            borderwidth=0,
        )

        row_height = self.px(28)
        configure(
            "Treeview",
            background=container_low,
            fieldbackground=container_low,
            foreground=on_surface,
            bordercolor=outline_variant,
            borderwidth=0,
            rowheight=row_height,
            font=body,
        )
        map_style(
            "Treeview",
            background=[("selected", primary_container)],
            foreground=[("selected", on_primary_container)],
        )
        configure(
            "Treeview.Heading",
            background=container_high,
            foreground=on_surface,
            font=label,
            relief="flat",
            borderwidth=0,
            padding=(self.px(8), self.px(6)),
        )
        map_style(
            "Treeview.Heading",
            background=[("active", self.state("surface_container_high", "hover"))],
        )

        configure("TNotebook", background=surface, borderwidth=0, tabmargins=(0, self.px(6), 0, 0))
        configure(
            "TNotebook.Tab",
            background=container,
            foreground=on_variant,
            font=label,
            padding=(self.px(16), self.px(8)),
            borderwidth=0,
        )
        map_style(
            "TNotebook.Tab",
            background=[("selected", container_high)],
            foreground=[("selected", primary)],
            expand=[("selected", (0, 0, 0, 0))],
        )

        configure(
            "TProgressbar",
            background=primary,
            troughcolor=container_highest,
            bordercolor=container_highest,
            lightcolor=primary,
            darkcolor=primary,
            borderwidth=0,
            thickness=self.px(8),
        )
        configure(
            "TScrollbar",
            background=container_highest,
            troughcolor=surface,
            bordercolor=surface,
            arrowcolor=on_variant,
            relief="flat",
            borderwidth=0,
        )
        map_style(
            "TScrollbar",
            background=[("active", outline), ("pressed", primary)],
        )

        for widget in ("TCheckbutton", "TRadiobutton"):
            configure(
                widget,
                background=surface,
                foreground=on_surface,
                font=body,
                focuscolor=primary,
                indicatorcolor=container_highest,
                bordercolor=outline,
                padding=(self.px(4), self.px(4)),
            )
            map_style(
                widget,
                background=[("active", surface)],
                foreground=[("disabled", self.disabled_content("on_surface"))],
                indicatorcolor=[("selected", primary), ("disabled", container_high)],
            )

        configure(
            "TScale",
            background=surface,
            troughcolor=container_highest,
            bordercolor=surface,
            lightcolor=primary,
            darkcolor=primary,
        )
        configure("TSeparator", background=outline_variant)
        configure(
            "TLabelframe",
            background=surface,
            bordercolor=outline_variant,
            borderwidth=1,
            relief="solid",
        )
        configure(
            "TLabelframe.Label",
            background=surface,
            foreground=primary,
            font=label,
        )

    # -- диагностика --------------------------------------------------------

    def describe(self) -> str:
        """Краткая строка о текущей теме (для логов и отчётов)."""
        return (
            f"theme={self._mode} scale={self._scale:.2f} "
            f"font={self.family('sans')} mono={self.family('mono')}"
        )


_manager = ThemeManager()
_manager.load()


def get_theme() -> ThemeManager:
    """Общий менеджер темы."""
    return _manager


#: Удобный алиас для импорта: ``from ui.theme import theme``.
theme = _manager
