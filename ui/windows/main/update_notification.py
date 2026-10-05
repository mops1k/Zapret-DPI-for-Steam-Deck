"""Окно уведомления об обновлениях в стиле Material 3.

Показывает доступную версию, список изменений и кнопки «Обновиться» /
«Пропустить». Заметки релиза подгружаются в фоне. Проект «Zapret DPI Manager»
© Aleksandr Kvintilyanov.
"""
from __future__ import annotations

import threading
import tkinter as tk
from typing import Any, Protocol

from core.dpi_utils import center_toplevel_on_parent, fit_toplevel_to_content, safe_grab_set
from core.github_release import sanitize_text_for_display
from ui.components.material import filled_button, text_button
from ui.theme import theme


class UpdateNotificationHost(Protocol):
    root: tk.Misc

    def open_update_window(self, notification_window: tk.Toplevel) -> None: ...


def show_update_notification_dialog(
    host: UpdateNotificationHost,
    bundle_update_info: dict[str, Any] | None,
) -> None:
    """Показывает окно уведомления о доступном полном обновлении."""
    if not bundle_update_info:
        return

    t = theme
    window = tk.Toplevel(host.root)
    window.title("Доступно обновление")
    window.configure(bg=t.color("surface"))
    window.resizable(False, False)
    try:
        window.transient(host.root)
    except tk.TclError:
        pass

    card = tk.Frame(window, bg=t.color("surface_container_high"))
    card.pack(fill=tk.BOTH, expand=True, padx=t.space("lg"), pady=t.space("lg"))

    header = tk.Frame(card, bg=t.color("surface_container_high"))
    header.pack(fill=tk.X, padx=t.space("lg"), pady=(t.space("lg"), t.space("sm")))
    tk.Label(
        header,
        text="⬆",
        **theme.text("headline_small", bg_role="surface_container_high", fg_role="primary"),
    ).pack(side=tk.LEFT, padx=(0, t.space("md")))
    tk.Label(
        header,
        text="Доступно обновление",
        anchor="w",
        **theme.text("title_large", bg_role="surface_container_high"),
    ).pack(side=tk.LEFT)

    info = tk.Frame(card, bg=t.color("surface_container_high"))
    info.pack(fill=tk.X, padx=t.space("lg"))
    tk.Label(
        info,
        text="Рекомендуется обновиться: новые функции и исправления ошибок.",
        anchor="w",
        justify="left",
        wraplength=t.px(420),
        **theme.text("body_medium", bg_role="surface_container_high", fg_role="on_surface_variant"),
    ).pack(fill=tk.X, pady=(0, t.space("sm")))

    versions = tk.Frame(info, bg=t.color("surface_container_high"))
    versions.pack(fill=tk.X, pady=(0, t.space("md")))
    tk.Label(
        versions,
        text=f"Текущая версия: {bundle_update_info.get('current', '—')}",
        **theme.text("body_medium", bg_role="surface_container_high", fg_role="on_surface_variant"),
    ).pack(side=tk.LEFT)
    tk.Label(
        versions,
        text="  →  ",
        **theme.text("body_medium", bg_role="surface_container_high", fg_role="on_surface_variant"),
    ).pack(side=tk.LEFT)
    tk.Label(
        versions,
        text=f"Новая версия: {bundle_update_info.get('available', '—')}",
        **theme.text("title_small", bg_role="surface_container_high", fg_role="success"),
    ).pack(side=tk.LEFT)

    tk.Label(
        info,
        text="Список изменений:",
        anchor="w",
        **theme.text("label_large", bg_role="surface_container_high", fg_role="on_surface_variant"),
    ).pack(fill=tk.X, pady=(0, t.space("xs")))

    notes_frame = tk.Frame(info, bg=t.color("surface_container_high"))
    notes_frame.pack(fill=tk.BOTH, expand=True)
    notes = tk.Text(
        notes_frame,
        height=8,
        width=46,
        wrap=tk.WORD,
        bg=t.color("surface_container_lowest"),
        fg=t.color("on_surface"),
        font=t.font("body_small"),
        highlightthickness=0,
        borderwidth=0,
        relief=tk.FLAT,
        padx=t.px(10),
        pady=t.px(8),
        cursor="arrow",
    )
    notes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def set_notes(text: str) -> None:
        try:
            notes.config(state=tk.NORMAL)
            notes.delete("1.0", tk.END)
            notes.insert("1.0", sanitize_text_for_display(text))
            notes.config(state=tk.DISABLED)
        except tk.TclError:
            pass

    release_notes = sanitize_text_for_display(bundle_update_info.get("release_notes") or "")
    set_notes(release_notes or "Загрузка описания…")

    if not release_notes:
        available_version = bundle_update_info.get("available")

        def fetch_notes() -> None:
            loaded = ""
            try:
                from core.github_release import fetch_release_notes_for_version

                loaded = (fetch_release_notes_for_version(available_version) or "").strip()
            except Exception:
                loaded = ""
            if not loaded:
                loaded = "Описание релиза недоступно (релиз ещё не опубликован или нет сети)."
            else:
                stored = getattr(host, "_last_bundle_update_info", None)
                if isinstance(stored, dict):
                    stored["release_notes"] = loaded
            try:
                host.root.after(0, lambda value=loaded: set_notes(value))
            except tk.TclError:
                pass

        threading.Thread(target=fetch_notes, daemon=True).start()

    actions = tk.Frame(card, bg=t.color("surface_container_high"))
    actions.pack(fill=tk.X, padx=t.space("lg"), pady=t.space("lg"))

    def start_update() -> None:
        host.open_update_window(window)

    text_button(
        actions,
        "Пропустить",
        window.destroy,
        parent_role="surface_container_high",
    ).pack(side=tk.RIGHT)
    filled_button(
        actions,
        "Обновиться",
        start_update,
        parent_role="surface_container_high",
    ).pack(side=tk.RIGHT, padx=(0, t.space("sm")))

    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.update_idletasks()
    try:
        fit_toplevel_to_content(window, min_width=360, min_height=260, margin_width=8, margin_height=12)
        center_toplevel_on_parent(window, host.root)
    except tk.TclError:
        pass
    safe_grab_set(window)
