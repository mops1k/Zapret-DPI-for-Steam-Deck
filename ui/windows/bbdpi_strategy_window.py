"""Окно «Стратегия из BB DPI» (Material 3).

Вставленную строку пользовательской стратегии BB DPI (движок ciadpi,
hufrea/byedpi) конвертер переводит в аргументы nfqws, проверяет через
``nfqws --dry-run`` и сохраняет как готовую стратегию менеджера.

Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path

from core.bbdpi_convert import convert, dry_run, safe_strategy_name
from core.dpi_utils import place_toplevel_centered_on_parent, safe_grab_set, wait_window_safely
from core.game_presets import reapply_active_preset_to_config
from core.service_manager import ServiceManager
from ui.components.custom_messagebox import show_error, show_warning
from ui.components.material import (
    MaterialCheckbox,
    MaterialDialog,
    MaterialTextField,
    TopAppBar,
    filled_button,
    text_button,
    tonal_button,
)
from ui.theme import theme

APP_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NAME = "BBDI_Custom"


class BBDpiStrategyWindow:
    """Окно ввода строки BB DPI и применения результата."""

    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.result = None
        self.service_manager = ServiceManager()

        self.success_color = theme.color("success")
        self.warning_color = theme.color("warning")
        self.error_color = theme.color("error")
        self.default_status_color = theme.color("on_surface_variant")

        self.setup_window_properties()
        self.root.title("Стратегия из BB DPI")
        self.setup_ui()
        place_toplevel_centered_on_parent(
            self.root, self.parent, min_width=680, min_height=560, margin_width=8, margin_height=12
        )

    def setup_window_properties(self):
        """Настройка свойств окна."""
        self.root.configure(bg=theme.color("surface"))
        self.root.transient(self.parent)
        safe_grab_set(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)

    def _text_block(self, master, height: int) -> tk.Text:
        """Прокручиваемое поле предпросмотра в стиле темы."""
        block = tk.Text(
            master,
            height=height,
            wrap="word",
            bg=theme.color("surface_container_low"),
            fg=theme.color("on_surface"),
            insertbackground=theme.color("on_surface"),
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            font=theme.font("body_small", mono=True),
            padx=theme.space("sm"),
            pady=theme.space("sm"),
        )
        block.configure(state="disabled")
        return block

    @staticmethod
    def _set_text(block: tk.Text, text: str) -> None:
        """Записывает текст в заблокированное поле."""
        block.configure(state="normal")
        block.delete("1.0", tk.END)
        block.insert("1.0", text)
        block.configure(state="disabled")

    def setup_ui(self):
        """Настройка интерфейса."""
        t = theme
        main_frame = tk.Frame(self.root, bg=t.color("surface"))
        main_frame.pack(fill=tk.BOTH, expand=True, padx=t.space("lg"), pady=t.space("lg"))

        self.app_bar = TopAppBar(
            main_frame,
            title="Стратегия из BB DPI",
            subtitle="Вставьте строку стратегии из BB DPI — приложение переведёт её в параметры nfqws",
            bg_role="surface",
        )
        self.app_bar.pack(fill=tk.X, pady=(0, t.space("md")))

        self.command_var = tk.StringVar()
        self.command_field = MaterialTextField(
            main_frame,
            label="Строка стратегии BB DPI",
            textvariable=self.command_var,
            placeholder="-s1 -d1 -f-1 -t8 -S",
            width=60,
            on_return=self.convert_command,
        )
        self.command_field.pack(fill=tk.X, pady=(0, t.space("sm")))

        self.name_var = tk.StringVar(value=DEFAULT_NAME)
        self.name_field = MaterialTextField(
            main_frame,
            label="Имя стратегии",
            textvariable=self.name_var,
            placeholder=DEFAULT_NAME,
            width=30,
        )
        self.name_field.pack(fill=tk.X, pady=(0, t.space("sm")))

        self.hostlist_var = tk.BooleanVar(value=False)
        self.hostlist_check = MaterialCheckbox(
            main_frame,
            "Ограничить нашим списком доменов (list-general + list-exclude)",
            variable=self.hostlist_var,
            command=lambda _value: self.convert_command(),
        )
        self.hostlist_check.pack(anchor="w", pady=(0, t.space("sm")))

        buttons_frame = tk.Frame(main_frame, bg=t.color("surface"))
        buttons_frame.pack(fill=tk.X, pady=(0, t.space("md")))

        self.convert_button = filled_button(buttons_frame, "Преобразовать", self.convert_command)
        self.convert_button.pack(side=tk.LEFT, padx=(0, t.space("sm")))

        self.apply_button = tonal_button(buttons_frame, "Сохранить и применить", self.apply_strategy)
        self.apply_button.pack(side=tk.LEFT, padx=(0, t.space("sm")))

        self.back_button = text_button(buttons_frame, "Назад", self.close_window)
        self.back_button.pack(side=tk.LEFT)

        tk.Label(
            main_frame,
            text="Результат для nfqws:",
            anchor="w",
            **theme.text("label_large"),
        ).pack(fill=tk.X, pady=(0, t.space("xs")))
        self.preview_text = self._text_block(main_frame, height=6)
        self.preview_text.pack(fill=tk.BOTH, expand=True, pady=(0, t.space("sm")))

        tk.Label(
            main_frame,
            text="Замечания:",
            anchor="w",
            **theme.text("label_large"),
        ).pack(fill=tk.X, pady=(0, t.space("xs")))
        self.warnings_text = self._text_block(main_frame, height=6)
        self.warnings_text.pack(fill=tk.BOTH, expand=True, pady=(0, t.space("sm")))

        self.status_label = tk.Label(
            main_frame,
            text="",
            anchor="w",
            wraplength=t.px(600),
            **theme.text("body_small", fg_role="on_surface_variant"),
        )
        self.status_label.pack(fill=tk.X)

    def _set_status(self, text: str, color: str | None = None) -> None:
        """Обновляет статусную строку."""
        self.status_label.config(text=text, fg=color or self.default_status_color)

    def convert_command(self, _event=None):
        """Разбирает строку BB DPI и показывает результат с проверкой nfqws."""
        command = self.command_var.get().strip()
        if not command:
            self.result = None
            self._set_text(self.preview_text, "")
            self._set_text(self.warnings_text, "Введите строку стратегии из BB DPI")
            self._set_status("Строка не введена", self.warning_color)
            return

        self.result = convert(command, use_hostlist=self.hostlist_var.get())
        self._set_text(self.preview_text, self.result.text or "(пусто)")

        notes = [f"Не перенесено: {item}" for item in self.result.unsupported]
        notes += [f"Предупреждение: {item}" for item in self.result.warnings]
        self._set_text(self.warnings_text, "\n".join(notes) if notes else "Замечаний нет")

        if not self.result.ok:
            self._set_status("Не удалось разобрать строку", self.error_color)
            return

        problems = dry_run(self.result.rules, app_root=APP_ROOT)
        if problems:
            self._set_status("Проверка nfqws не пройдена: " + problems[0], self.error_color)
        else:
            self._set_status(
                f"Проверка nfqws пройдена, строк для config.txt: {len(self.result.rules)}",
                self.success_color,
            )

    def _ensure_sudo(self) -> bool:
        """Проверяет доступность sudo -A (пароль вводит системный askpass)."""
        from core.sudo_helper import sudo_available

        if not sudo_available():
            self._set_status("sudo или askpass-хелпер недоступны", self.error_color)
            return False
        return True

    def apply_strategy(self):
        """Сохраняет сконвертированную стратегию и перезапускает службу."""
        if self.result is None or not self.result.ok:
            self.convert_command()
        if self.result is None or not self.result.ok:
            show_error(self.root, "Ошибка", "Сначала преобразуйте строку стратегии")
            return

        problems = dry_run(self.result.rules, app_root=APP_ROOT)
        if problems:
            show_error(self.root, "Ошибка", "nfqws не принимает результат:\n" + "\n".join(problems))
            return

        if self.result.unsupported:
            dialog = MaterialDialog(
                self.root,
                "Не всё перенесено",
                f"Опций BB DPI без аналога в nfqws: {len(self.result.unsupported)}. "
                "Они не будут применены. Продолжить?",
                kind="question",
                detail="\n".join(self.result.unsupported),
                buttons=[("Нет", False), ("Да", True)],
                default=True,
            )
            if dialog.run() is not True:
                return

        manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        if not os.path.isdir(manager_dir):
            show_error(self.root, "Ошибка", f"Не найден каталог менеджера: {manager_dir}")
            return

        if not self._ensure_sudo():
            show_warning(self.root, "Отменено", "Для применения стратегии требуется пароль sudo")
            return

        self.root.config(cursor="watch")
        self.apply_button.config(state="disabled", text="Применение...")
        self._set_status("Сохранение стратегии...")
        self.root.update()

        try:
            name = safe_strategy_name(self.name_var.get())
            self.name_var.set(name)
            strategy_dir = os.path.join(manager_dir, "files", "strategy")
            os.makedirs(strategy_dir, exist_ok=True)
            os.makedirs(os.path.join(manager_dir, "utils"), exist_ok=True)

            content = self.result.text + "\n"
            with open(os.path.join(strategy_dir, name), "w", encoding="utf-8") as handle:
                handle.write(content)
            with open(os.path.join(manager_dir, "utils", "name_strategy.txt"), "w", encoding="utf-8") as handle:
                handle.write(name)
            with open(os.path.join(manager_dir, "config.txt"), "w", encoding="utf-8") as handle:
                handle.write(content)
            reapply_active_preset_to_config(manager_dir)

            self._set_status("Перезапуск службы...")
            self.apply_button.config(text="Перезапуск...")
            self.root.update()

            success, message = self.service_manager.restart_service()
            if success:
                self._set_status(f"Стратегия «{name}» применена, служба перезапущена", self.success_color)
                self.root.after(1500, self.close_window)
            else:
                self._set_status(f"Стратегия сохранена, но служба не перезапущена: {message}", self.warning_color)
                self._reset_ui_state()
        except Exception as error:  # noqa: BLE001 — показываем любую ошибку записи в UI
            self._set_status(f"Ошибка: {error}", self.error_color)
            print(f"Ошибка применения стратегии BB DPI: {error}")
            self._reset_ui_state()

    def _reset_ui_state(self):
        """Возвращает кнопки в рабочее состояние."""
        self.root.config(cursor="")
        self.apply_button.config(state="normal", text="Сохранить и применить")

    def close_window(self):
        """Закрывает окно."""
        self.root.destroy()

    def run(self):
        """Запускает окно."""
        wait_window_safely(self.root)
