"""Всплывающие подсказки главного окна в стиле Material 3."""
from __future__ import annotations

import tkinter as tk

from ui.theme import theme


class MainTooltipsMixin:
    """Подсказки статуса службы, GameFilter и иконок панели."""

    # -- статус службы ------------------------------------------------------

    def _status_text(self) -> str:
        """Текст статуса по флагу службы, а не по цвету индикатора."""
        if getattr(self, "service_running", False):
            return "Статус службы: активен"
        return "Статус службы: неактивен"

    def show_status_tooltip(self, event=None):
        """Показывает подсказку о статусе службы."""
        if self.status_tooltip:
            return
        self.status_tooltip = self._build_tooltip(
            self.status_indicator, self._status_text(), offset_x=-20
        )

    def hide_status_tooltip(self, event=None):
        """Скрывает подсказку статуса службы."""
        if self.status_tooltip:
            self._destroy_tooltip(self.status_tooltip)
            self.status_tooltip = None

    # -- произвольные иконки ------------------------------------------------

    def show_icon_tooltip(self, event, description):
        """Показывает подсказку для иконки, из которой пришло событие."""
        if getattr(self, "icon_tooltip", None):
            self.hide_icon_tooltip()
        widget = event.widget
        self.icon_tooltip = self._build_tooltip(widget, description, offset_x=-20)

    def hide_icon_tooltip(self, event=None):
        """Скрывает подсказку иконки."""
        if getattr(self, "icon_tooltip", None):
            self._destroy_tooltip(self.icon_tooltip)
            self.icon_tooltip = None

    # -- построение ---------------------------------------------------------

    def _build_tooltip(self, anchor_widget, text: str, *, offset_x: int = 0) -> tk.Toplevel:
        """Создаёт подсказку M3 под указанным виджетом."""
        try:
            x = anchor_widget.winfo_rootx() + offset_x
            y = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + theme.px(6)
        except tk.TclError:
            x = y = 0

        tip = tk.Toplevel(self.root)
        tip.wm_overrideredirect(True)
        tip.configure(bg=theme.color("inverse_surface"))
        label = tk.Label(
            tip,
            text=text,
            justify=tk.LEFT,
            padx=theme.px(12),
            pady=theme.px(8),
            **theme.text("body_small", bg_role="inverse_surface", fg_role="inverse_on_surface"),
        )
        label.pack()
        try:
            tip.geometry(f"+{max(0, x)}+{max(0, y)}")
        except tk.TclError:
            pass
        return tip

    @staticmethod
    def _destroy_tooltip(tooltip: tk.Toplevel) -> None:
        try:
            tooltip.destroy()
        except tk.TclError:
            pass
