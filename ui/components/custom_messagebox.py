# -*- coding: utf-8 -*-
"""Диалоги приложения в стиле Material 3.

Публичный API прежний (show_info/show_error/show_warning/ask_yesno/
ask_yesnocancel), но окна рисуются компонентом MaterialDialog.
Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
from __future__ import annotations

from ui.components.material.dialog import MaterialDialog


def show_info(parent, title, message):
    """Показывает информационное сообщение в стиле приложения."""
    MaterialDialog(parent, title, message, kind="info", buttons=[("OK", True)]).run()
    return True


def show_error(parent, title, message):
    """Показывает сообщение об ошибке в стиле приложения."""
    MaterialDialog(parent, title, message, kind="error", buttons=[("OK", True)]).run()
    return True


def show_warning(parent, title, message):
    """Показывает предупреждение в стиле приложения."""
    MaterialDialog(parent, title, message, kind="warning", buttons=[("OK", True)]).run()
    return True


def ask_yesno(parent, title, message):
    """Диалог Да/Нет в стиле приложения; возвращает True/False."""
    result = MaterialDialog(
        parent,
        title,
        message,
        kind="question",
        buttons=[("Нет", False), ("Да", True)],
        default=True,
    ).run()
    return result is True


def ask_yesnocancel(parent, title, message):
    """Диалог Да/Нет/Отмена; возвращает True, False или None (отмена)."""
    return MaterialDialog(
        parent,
        title,
        message,
        kind="question",
        buttons=[("Отмена", None), ("Нет", False), ("Да", True)],
        default=True,
    ).run()
