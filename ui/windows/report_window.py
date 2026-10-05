# -*- coding: utf-8 -*-
"""Окно отчёта тестирования стратегий в стиле Material 3.

Отчёт открывается собственным окном приложения, а не в браузере. Данные
берутся из JSON рядом с HTML (его пишет core/strategy_tester.generate_report);
для старых отчётов работает разбор HTML. Проект «Zapret DPI Manager»
© Aleksandr Kvintilyanov.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tkinter as tk
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.dpi_utils import fit_toplevel_to_content, place_toplevel_centered_on_parent, safe_grab_set, wait_window_safely
from ui.components.material import MaterialCard, MaterialChip, MaterialTable, TopAppBar
from ui.theme import theme

VERDICTS = {
    "working": ("Рабочая", "success"),
    "partial": ("Частичная", "warning"),
    "failed": ("Нерабочая", "error"),
    "unknown": ("Неизвестно", "on_surface_variant"),
}


@dataclass
class ReportData:
    """Загруженные данные отчёта."""

    path: Optional[Path] = None
    generated_at: str = ""
    mode: str = "standard"
    results: List[Dict] = field(default_factory=list)
    source: str = ""
    error: str = ""

    @property
    def counts(self) -> Dict[str, int]:
        counts = {"working": 0, "partial": 0, "failed": 0, "unknown": 0}
        for result in self.results:
            counts[classify(result, self.mode)[0]] += 1
        return counts


def classify(result: Dict, mode: str) -> tuple:
    """Вердикт стратегии: (ключ, подпись, роль темы)."""
    if result.get("error"):
        return ("failed", "Ошибка", "error")
    rate = float(result.get("success_rate", 0) or 0)
    youtube = result.get("youtube_passed")
    discord = result.get("discord_passed")

    if mode in ("YouTube/Discord", "mixed") or youtube is not None or discord is not None:
        if youtube is True and discord is True:
            return ("working", *VERDICTS["working"])
        if youtube is False and discord is False:
            return ("failed", *VERDICTS["failed"])
        if youtube is None and discord is None:
            return ("unknown", *VERDICTS["unknown"])
        return ("partial", *VERDICTS["partial"])
    if mode == "dpi":
        return ("working", *VERDICTS["working"]) if rate >= 60 else ("failed", *VERDICTS["failed"])
    if rate < 60:
        return ("failed", *VERDICTS["failed"])
    return ("working", *VERDICTS["working"])


def _reports_dir() -> Path:
    return Path(os.path.expanduser("~/Zapret_DPI_Manager")) / "utils" / "reports"


def find_latest_report(reports_dir: Optional[Path] = None) -> Optional[Path]:
    """Последний отчёт: сначала HTML, для него ищем JSON-данные."""
    directory = reports_dir or _reports_dir()
    if not directory.exists():
        return None
    html_files = list(directory.glob("*.html"))
    if not html_files:
        return None
    return max(html_files, key=lambda p: p.stat().st_mtime)


def load_report(report_path: Optional[Path]) -> ReportData:
    """Читает JSON-данные отчёта, при отсутствии — разбирает HTML."""
    if report_path is None:
        return ReportData(error="Отчёты не найдены")
    path = Path(report_path)
    if not path.exists():
        return ReportData(error=f"Файл отчёта не найден: {path.name}")

    json_path = path.with_suffix(".json")
    if json_path.exists():
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            return ReportData(
                path=path,
                generated_at=str(payload.get("generated_at", "")),
                mode=str(payload.get("mode", "standard")),
                results=list(payload.get("results", [])),
                source="json",
            )
        except (OSError, ValueError) as exc:
            return _parse_html_report(path, note=f"JSON повреждён: {exc}")

    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            html_name = payload.get("html_file", "")
            html_path = path.with_name(html_name) if html_name else path.with_suffix(".html")
            return ReportData(
                path=html_path,
                generated_at=str(payload.get("generated_at", "")),
                mode=str(payload.get("mode", "standard")),
                results=list(payload.get("results", [])),
                source="json",
            )
        except (OSError, ValueError) as exc:
            return ReportData(error=f"Не удалось прочитать данные отчёта: {exc}")

    return _parse_html_report(path)


def _parse_html_report(path: Path, note: str = "") -> ReportData:
    """Резервный разбор HTML-отчёта: имя стратегии, режим и процент."""
    try:
        html = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return ReportData(error=f"Не удалось прочитать отчёт: {exc}")

    card_re = re.compile(r'<div class="strategy-card">(.*?)</div>\s*</div>', re.S)
    name_re = re.compile(
        r'<div class="strategy-name">\s*(?:[^<]*?)\s*([^<]+?)\s*<span class="strategy-badge">(\w+)</span>',
        re.S,
    )
    rate_re = re.compile(r'([\d.]+)\s*%')
    results: List[Dict] = []
    for chunk in card_re.findall(html):
        name_match = name_re.search(chunk)
        name = name_match.group(1).strip() if name_match else "—"
        name = re.sub(r"^[^\w]+", "", name).strip() or "—"
        mode = name_match.group(2).lower() if name_match else "standard"
        if mode == "youtube/discord":
            mode = "YouTube/Discord"
        rate_match = rate_re.search(chunk)
        rate = float(rate_match.group(1)) if rate_match else 0.0
        results.append(
            {
                "name": name,
                "mode": mode,
                "success_rate": round(rate, 1),
                "youtube_passed": None,
                "discord_passed": None,
                "targets": [],
            }
        )

    generated = ""
    stamp_match = re.search(r"(\d{2}\.\d{2}\.\d{4}[^<]*)", html)
    if stamp_match:
        generated = stamp_match.group(1).strip()

    return ReportData(
        path=path,
        generated_at=generated,
        mode="standard",
        results=results,
        source="html",
        error=note or ("" if results else "В отчёте не найдено ни одной стратегии"),
    )


class ReportWindow:
    """Модальное окно с нативным отчётом тестирования."""

    def __init__(self, parent: tk.Misc, report_path: Optional[Path] = None) -> None:
        self.parent = parent
        self.report_path = Path(report_path) if report_path else find_latest_report()
        self.data = load_report(self.report_path)
        self._filter = "all"
        self._query = ""
        self._rows: List[Dict] = []
        self._selected_row: Optional[Dict] = None
        self._build()

    # -- построение окна ----------------------------------------------------

    def _build(self) -> None:
        t = theme
        self.window = tk.Toplevel(self.parent)
        self.window.title("Отчёт тестирования стратегий")
        self.window.configure(bg=t.color("surface"))
        try:
            self.window.transient(self.parent)
        except tk.TclError:
            pass

        root_frame = tk.Frame(self.window, bg=t.color("surface"))
        root_frame.pack(fill=tk.BOTH, expand=True, padx=t.space("xl"), pady=t.space("lg"))

        self.app_bar = TopAppBar(
            root_frame,
            title="Отчёт тестирования",
            subtitle=self._subtitle(),
            bg_role="surface",
            actions=[
                ("↻", self.reload, "Обновить отчёт"),
                ("🌐", self.open_in_browser, "Открыть HTML в браузере"),
                ("📁", self.open_reports_folder, "Открыть папку отчётов"),
            ],
        )
        self.app_bar.pack(fill=tk.X, pady=(0, t.space("lg")))

        if self.data.error:
            card = MaterialCard(root_frame, variant="filled", title="Отчёт недоступен")
            card.pack(fill=tk.X)
            tk.Label(
                card.content,
                text=self.data.error,
                anchor="w",
                justify="left",
                wraplength=t.px(560),
                **theme.text("body_medium", bg_role="surface_container_highest", fg_role="error"),
            ).pack(fill=tk.X)
            self.window.update_idletasks()
            self._finish_layout()
            return

        # Сводка
        summary = tk.Frame(root_frame, bg=t.color("surface"))
        summary.pack(fill=tk.X, pady=(0, t.space("md")))
        counts = self.data.counts
        stats = (
            ("Всего стратегий", len(self.data.results), "primary"),
            ("Рабочие", counts["working"], "success"),
            ("Частичные", counts["partial"], "warning"),
            ("Нерабочие", counts["failed"], "error"),
        )
        for index, (caption, value, role) in enumerate(stats):
            card = MaterialCard(summary, variant="elevated", padding=t.space("md"))
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0 if index == 0 else t.space("sm"), 0))
            tk.Label(
                card.content,
                text=str(value),
                anchor="w",
                **theme.text("headline_medium", bg_role="surface_container_low", fg_role=role),
            ).pack(fill=tk.X)
            tk.Label(
                card.content,
                text=caption,
                anchor="w",
                **theme.text("label_medium", bg_role="surface_container_low", fg_role="on_surface_variant"),
            ).pack(fill=tk.X)

        # Фильтры
        filters = tk.Frame(root_frame, bg=t.color("surface"))
        filters.pack(fill=tk.X, pady=(0, t.space("sm")))
        for key, label in (
            ("all", "Все"),
            ("working", "Рабочие"),
            ("partial", "Частичные"),
            ("failed", "Нерабочие"),
        ):
            chip = MaterialChip(
                filters,
                label,
                selected=(self._filter == key),
                command=lambda selected, k=key: self._set_filter(k, selected),
            )
            chip.pack(side=tk.LEFT, padx=(0, t.space("sm")))
            self._chips = getattr(self, "_chips", [])
            self._chips.append((key, chip))

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            filters,
            textvariable=self.search_var,
            font=t.font("body_medium"),
            bd=0,
            highlightthickness=1,
            highlightbackground=t.color("outline_variant"),
            highlightcolor=t.color("primary"),
            bg=t.color("surface_container_high"),
            fg=t.color("on_surface"),
            insertbackground=t.color("primary"),
            width=22,
        )
        search_entry.pack(side=tk.RIGHT, ipady=t.px(5), padx=(t.space("sm"), 0))
        self.search_var.trace_add("write", lambda *_: self._on_search())

        # Таблица
        table_card = MaterialCard(root_frame, variant="outlined", padding=t.space("sm"))
        table_card.pack(fill=tk.BOTH, expand=True)
        self.table = MaterialTable(
            table_card.content,
            [
                ("name", "Стратегия", 200),
                ("rate", "Успех", 80),
                ("youtube", "YouTube", 90),
                ("discord", "Discord", 90),
                ("verdict", "Вердикт", 130),
            ],
            height=10,
            bg_role="surface",
        )
        self.table.pack(fill=tk.BOTH, expand=True)
        self.table.add_tag("working", foreground="success")
        self.table.add_tag("partial", foreground="warning")
        self.table.add_tag("failed", foreground="error")
        self.table.bind_select(self._on_select)

        # Детали выбранной стратегии
        self.details_card = MaterialCard(
            root_frame, variant="elevated", title="Детали", subtitle="Выберите стратегию в таблице"
        )
        self.details_card.pack(fill=tk.BOTH, expand=True, pady=(t.space("md"), 0))
        self.details_text = tk.Text(
            self.details_card.content,
            height=7,
            wrap=tk.WORD,
            bg=t.color("surface_container_low"),
            fg=t.color("on_surface"),
            font=t.font("body_small", mono=True),
            highlightthickness=0,
            borderwidth=0,
            relief=tk.FLAT,
            padx=t.px(8),
            pady=t.px(6),
        )
        self.details_text.pack(fill=tk.BOTH, expand=True)
        self.details_text.config(state=tk.DISABLED)

        self.status_label = tk.Label(
            root_frame,
            text=self._source_note(),
            anchor="w",
            **theme.text("body_small", fg_role="on_surface_variant"),
        )
        self.status_label.pack(fill=tk.X, pady=(t.space("sm"), 0))

        self._refresh_table()
        self._finish_layout()

    def _finish_layout(self) -> None:
        self.window.update_idletasks()
        try:
            self.window.geometry("980x720")
            fit_toplevel_to_content(self.window, min_width=640, min_height=420, margin_width=16, margin_height=16)
            place_toplevel_centered_on_parent(self.window, self.parent)
        except tk.TclError:
            pass

    # -- данные -------------------------------------------------------------

    def _subtitle(self) -> str:
        if not self.data.path:
            return "Отчёты не найдены"
        parts = [self.data.path.name]
        if self.data.generated_at:
            parts.append(self.data.generated_at)
        parts.append(f"режим: {self.data.mode}")
        if self.data.source == "html":
            parts.append("данные из HTML")
        return " · ".join(parts)

    def _source_note(self) -> str:
        if self.data.source == "html":
            return (
                "Данные восстановлены из HTML (JSON рядом с отчётом отсутствует): "
                "доступны только имя стратегии и процент успеха."
            )
        return f"Источник данных: {self.data.path.name if self.data.path else '—'}"

    def _set_filter(self, key: str, selected: bool) -> None:
        self._filter = key if selected else "all"
        for chip_key, chip in getattr(self, "_chips", []):
            chip.set_selected(chip_key == self._filter)
        self._refresh_table()

    def _on_search(self) -> None:
        self._query = self.search_var.get().strip().lower()
        self._refresh_table()

    def _refresh_table(self) -> None:
        self.table.clear()
        self._rows = []
        for result in self.data.results:
            verdict_key, verdict_label, _role = classify(result, self.data.mode)
            if self._filter != "all" and verdict_key != self._filter:
                continue
            if self._query and self._query not in str(result.get("name", "")).lower():
                continue
            self._rows.append(result)
            self.table.insert(
                (
                    result.get("name", "—"),
                    f"{float(result.get('success_rate', 0) or 0):.1f}%",
                    _flag(result.get("youtube_passed")),
                    _flag(result.get("discord_passed")),
                    verdict_label,
                ),
                iid=str(len(self._rows) - 1),
                tags=(verdict_key,),
            )
        if self.status_label is not None:
            shown = len(self._rows)
            total = len(self.data.results)
            self.status_label.config(text=f"{self._source_note()}  •  показано {shown} из {total}")

    def _on_select(self, _event=None) -> None:
        iid = self.table.get_selected()
        if iid is None:
            return
        try:
            result = self._rows[int(iid)]
        except (ValueError, IndexError):
            return
        self._selected_row = result
        self._show_details(result)

    def _show_details(self, result: Dict) -> None:
        verdict_key, verdict_label, _role = classify(result, self.data.mode)
        lines = [
            f"Стратегия: {result.get('name', '—')}",
            f"Режим: {result.get('mode', self.data.mode)}    Вердикт: {verdict_label}",
            f"Успех: {float(result.get('success_rate', 0) or 0):.1f}%   "
            f"успешно: {result.get('successful', '—')}   "
            f"ошибок: {result.get('failed', '—')}   "
            f"блокировок: {result.get('blocked', '—')}",
            f"YouTube: {_flag(result.get('youtube_passed'))}    Discord: {_flag(result.get('discord_passed'))}",
        ]
        reason = result.get("critical_fail_reason") or ""
        if reason:
            lines.append(f"Причина: {reason}")
        targets = result.get("targets") or []
        if targets:
            lines.append("")
            lines.append("Цели:")
            for target in targets:
                mark = "✓" if target.get("success") else ("⊘" if target.get("blocked") else "✗")
                detail = target.get("details") or ""
                lines.append(f"  {mark} {target.get('name', '—')} {detail}".rstrip())
        else:
            lines.append("")
            lines.append("Детальные цели в этом отчёте недоступны.")

        try:
            self.details_text.config(state=tk.NORMAL)
            self.details_text.delete("1.0", tk.END)
            self.details_text.insert("1.0", "\n".join(lines))
            self.details_text.config(state=tk.DISABLED)
        except tk.TclError:
            pass

    # -- действия -----------------------------------------------------------

    def reload(self) -> None:
        """Перечитывает отчёт с диска."""
        self.report_path = find_latest_report() if not self.report_path else self.report_path
        self.data = load_report(self.report_path)
        try:
            self.app_bar.set_subtitle(self._subtitle())
        except tk.TclError:
            pass
        self._refresh_table()

    def open_in_browser(self) -> None:
        """Открывает HTML-версию отчёта в браузере (по явному действию)."""
        if self.data.path and self.data.path.exists():
            webbrowser.open(f"file://{self.data.path}")

    def open_reports_folder(self) -> None:
        """Открывает папку с отчётами в файловом менеджере."""
        directory = (self.data.path.parent if self.data.path else _reports_dir())
        try:
            subprocess.Popen(
                ["xdg-open", str(directory)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError):
            pass

    def run(self) -> None:
        """Показывает окно модально."""
        try:
            safe_grab_set(self.window)
            wait_window_safely(self.window, self.parent)
        except tk.TclError:
            pass


def _flag(value) -> str:
    if value is True:
        return "✓"
    if value is False:
        return "✗"
    return "—"


def show_report_window(parent: tk.Misc, report_path: Optional[Path] = None) -> None:
    """Удобная функция: открыть окно отчёта."""
    ReportWindow(parent, report_path).run()
