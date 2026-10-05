# -*- coding: utf-8 -*-
"""Модальные диалоги Material 3.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

import tkinter as tk

from core.dpi_utils import place_toplevel_centered_on_parent, safe_grab_set, wait_window_safely
from ui.theme import theme

from .button import MaterialButton

#: Вид диалога -> (роль иконки, глиф).
KINDS = {
    "info": ("primary", "🛈"),
    "success": ("success", "✓"),
    "warning": ("warning", "⚠"),
    "error": ("error", "✕"),
    "question": ("primary", "❓"),
}


class MaterialDialog(tk.Toplevel):
    """Диалог M3: иконка, заголовок, текст, ряд кнопок.

    ``run()`` показывает окно модально и возвращает значение нажатой кнопки.
    """

    def __init__(
        self,
        parent: Optional[tk.Misc],
        title: str,
        message: str,
        *,
        kind: str = "info",
        buttons: Optional[Sequence[Tuple[str, object]]] = None,
        default: Optional[object] = None,
        detail: str = "",
        width: int = 420,
        wraplength: int = 380,
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        self._parent = parent
        self._result: Optional[object] = None
        self._buttons_spec: List[Tuple[str, object]] = list(
            buttons or [("Понятно", True)]
        )
        self._default = default if default is not None else self._buttons_spec[-1][1]
        self._kind = kind if kind in KINDS else "info"

        self.title(title)
        self.configure(bg=theme.color("surface"))
        self.resizable(False, False)
        self.transient(parent) if parent is not None else None

        card = tk.Frame(self, bg=theme.color("surface_container_high"))
        card.pack(fill=tk.BOTH, expand=True, padx=theme.space("lg"), pady=theme.space("lg"))

        header = tk.Frame(card, bg=theme.color("surface_container_high"))
        header.pack(fill=tk.X, padx=theme.space("lg"), pady=(theme.space("lg"), theme.space("sm")))

        role, glyph = KINDS[self._kind]
        icon = tk.Label(
            header,
            text=glyph,
            **theme.text("headline_small", bg_role="surface_container_high", fg_role=role),
        )
        icon.pack(side=tk.LEFT, padx=(0, theme.space("md")))

        title_label = tk.Label(
            header,
            text=title,
            anchor="w",
            justify="left",
            wraplength=theme.px(width - 120),
            **theme.text("title_large", bg_role="surface_container_high"),
        )
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        body = tk.Frame(card, bg=theme.color("surface_container_high"))
        body.pack(fill=tk.BOTH, expand=True, padx=theme.space("lg"))
        message_label = tk.Label(
            body,
            text=message,
            anchor="w",
            justify="left",
            wraplength=theme.px(wraplength),
            **theme.text("body_medium", bg_role="surface_container_high"),
        )
        message_label.pack(fill=tk.X)
        if detail:
            detail_label = tk.Label(
                body,
                text=detail,
                anchor="w",
                justify="left",
                wraplength=theme.px(wraplength),
                **theme.text("body_small", bg_role="surface_container_high", fg_role="on_surface_variant"),
            )
            detail_label.pack(fill=tk.X, pady=(theme.space("sm"), 0))

        actions = tk.Frame(card, bg=theme.color("surface_container_high"))
        actions.pack(fill=tk.X, padx=theme.space("lg"), pady=theme.space("lg"))
        for index, (label, value) in enumerate(self._buttons_spec):
            is_primary = value == self._default
            variant = "filled" if is_primary else "text"
            button = MaterialButton(
                actions,
                text=label,
                command=lambda v=value: self._finish(v),
                variant=variant,
                parent_role="surface_container_high",
            )
            button.pack(side=tk.RIGHT, padx=(theme.space("sm"), 0) if index else 0)

        self.bind("<Escape>", lambda _e: self._finish(None))
        self.protocol("WM_DELETE_WINDOW", lambda: self._finish(None))
        self.update_idletasks()
        try:
            place_toplevel_centered_on_parent(self, parent)
        except Exception:
            pass

    # -- управление ---------------------------------------------------------

    def _finish(self, value: Optional[object]) -> None:
        self._result = value
        try:
            self.destroy()
        except tk.TclError:
            pass

    def run(self) -> Optional[object]:
        """Показывает диалог модально и возвращает выбор пользователя."""
        try:
            self.deiconify()
            safe_grab_set(self)
            self.focus_set()
            wait_window_safely(self, self._parent)
        except tk.TclError:
            pass
        return self._result


# --- удобные обёртки --------------------------------------------------------


def show_message(
    parent: Optional[tk.Misc],
    title: str,
    message: str,
    *,
    kind: str = "info",
    detail: str = "",
    wraplength: int = 380,
) -> None:
    MaterialDialog(parent, title, message, kind=kind, detail=detail, wraplength=wraplength).run()


def ask_yes_no(
    parent: Optional[tk.Misc],
    title: str,
    message: str,
    *,
    kind: str = "question",
    yes_text: str = "Да",
    no_text: str = "Нет",
) -> bool:
    dialog = MaterialDialog(
        parent,
        title,
        message,
        kind=kind,
        buttons=[(no_text, False), (yes_text, True)],
        default=True,
    )
    return dialog.run() is True


def ask_yes_no_cancel(
    parent: Optional[tk.Misc],
    title: str,
    message: str,
    *,
    yes_text: str = "Да",
    no_text: str = "Нет",
    cancel_text: str = "Отмена",
) -> Optional[bool]:
    dialog = MaterialDialog(
        parent,
        title,
        message,
        kind="question",
        buttons=[(cancel_text, None), (no_text, False), (yes_text, True)],
        default=True,
    )
    return dialog.run()


def choose_from_list(
    parent: Optional[tk.Misc],
    title: str,
    message: str,
    options: Sequence[Tuple[str, object]],
) -> Optional[object]:
    """Диалог выбора из нескольких вариантов (для решений пользователя)."""
    dialog = MaterialDialog(parent, title, message, kind="question", buttons=options, default=options[0][1])
    return dialog.run()
