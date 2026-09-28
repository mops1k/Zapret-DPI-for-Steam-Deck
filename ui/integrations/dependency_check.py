"""Проверка зависимостей при старте с UI приложения."""
from __future__ import annotations

import tkinter as tk

from core.dependency_checker import DependencyChecker
from ui.components.custom_messagebox import show_info as custom_show_info


def run_dependency_check(root_window: tk.Misc | None = None) -> bool:
    """Поведение как у прежнего вызова core.run_dependency_check(root)."""

    def _show(title: str, message: str) -> None:
        if root_window:
            custom_show_info(root_window, title, message)
        else:
            print(f"{title}: {message}")

    # Пароль sudo вводит системный askpass (sudo -A), провайдер пароля не нужен.
    checker = DependencyChecker(
        root_window,
        show_info_fn=_show,
        sudo_password_provider=None,
    )
    return checker.check_and_install_dependencies()
