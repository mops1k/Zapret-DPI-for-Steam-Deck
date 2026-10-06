# -*- coding: utf-8 -*-
"""Модальные диалоги Material 3.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import List, Optional, Sequence, Tuple

from core.dpi_utils import place_toplevel_centered_on_parent, safe_grab_set, wait_window_safely
from ui.theme import theme

from .button import MaterialButton
from .scroll import ThinScrollbar, bind_mousewheel

#: Вид диалога -> (роль иконки, глиф).
KINDS = {
    "info": ("primary", "🛈"),
    "success": ("success", "✓"),
    "warning": ("warning", "⚠"),
    "error": ("error", "✕"),
    "question": ("primary", "❓"),
}


def _text_block(
    parent: tk.Misc,
    text: str,
    *,
    font_role: str,
    fg_role: str,
    bg_role: str,
    wraplength: int,
    max_lines: int,
    pady: int = 0,
) -> tk.Frame:
    """Текстовый блок диалога: автовысота, при переполнении — прокрутка.

    Длинные сообщения (например, список неперенесённых опций) больше не
    растягивают диалог: текст ограничен по высоте, ряд кнопок остаётся
    видимым, а содержимое прокручивается колесом или ползунком.
    """
    font = tkfont.Font(font=theme.font(font_role))
    char_width = max(1, font.measure("0"))
    columns = max(24, int(wraplength / char_width))

    container = tk.Frame(parent, bg=theme.color(bg_role))
    container.pack(fill=tk.X, pady=pady)
    widget = tk.Text(
        container,
        wrap="word",
        width=columns,
        height=1,
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=0,
        bg=theme.color(bg_role),
        fg=theme.color(fg_role),
        font=font,
        padx=0,
        pady=0,
        cursor="arrow",
        spacing1=0,
        spacing2=0,
        spacing3=0,
    )
    widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
    widget.insert("1.0", text)
    widget.configure(state="disabled")
    # Оценка числа строк: диалог ещё скрыт, поэтому Tk не знает ширину виджета
    # и подсчёт displaylines даёт мусор — считаем по длине абзацев.
    total = 0
    for paragraph in text.split("\n"):
        total += max(1, -(-len(paragraph) // columns))
    if total > max_lines:
        widget.configure(height=max_lines)
        scrollbar = ThinScrollbar(container, command=widget.yview, bg_role=bg_role)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(theme.space("xs"), 0))
        widget.configure(yscrollcommand=scrollbar.set)
        bind_mousewheel(widget, lambda step: widget.yview_scroll(step, "units"))
    else:
        widget.configure(height=max(total, 1))
    return container


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

        # Длинный текст — шире окно и ограниченная высота блока сообщения,
        # иначе ряд кнопок уезжает за нижнюю границу экрана.
        if len(message) > 160 or len(detail) > 160:
            width = max(width, 480)
            wraplength = max(wraplength, 440)
        try:
            screen_height = self.winfo_screenheight()
        except tk.TclError:
            screen_height = 800
        line_height = max(1, tkfont.Font(font=theme.font("body_medium")).metrics("linespace"))
        max_lines = max(6, min(14, int((screen_height * 0.35) / line_height)))

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
        body.pack(fill=tk.X, padx=theme.space("lg"))
        _text_block(
            body,
            message,
            font_role="body_medium",
            fg_role="on_surface",
            bg_role="surface_container_high",
            wraplength=wraplength,
            max_lines=max_lines,
        )
        if detail:
            _text_block(
                body,
                detail,
                font_role="body_small",
                fg_role="on_surface_variant",
                bg_role="surface_container_high",
                wraplength=wraplength,
                max_lines=max(3, max_lines // 2),
                pady=(theme.space("sm"), 0),
            )

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
