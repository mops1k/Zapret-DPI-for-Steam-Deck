#!/usr/bin/env python3
"""Проверка стратегий Zapret DPI Manager.

Что делает:
  1) сверяет плейсхолдеры {…} в files/strategy с теми, что раскрывает
     zapret/system/starter.sh, и проверяет, что файлы для них существуют;
  2) проверяет формат строк (начинаются с --, --new только в конце строки);
  3) с --dry-run прогоняет каждую строку через nfqws --dry-run, чтобы
     убедиться, что бинарник понимает все опции.

Использование:
    python3 tools/validate_strategies.py
    python3 tools/validate_strategies.py --dry-run --arch x86_64
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STRATEGY_DIR = REPO_ROOT / "files" / "strategy"
STARTER = REPO_ROOT / "zapret" / "system" / "starter.sh"

# Плейсхолдер -> файл, на который его меняет starter.sh (для --dry-run).
PLACEHOLDER_FILES = {
    "list_general": "files/lists/list-general.txt",
    "list_general_user": "files/lists/list-general_user.txt",
    "list_exclude": "files/lists/list-exclude.txt",
    "list_exclude_user": "files/lists/list-exclude_user.txt",
    "ipset_all": "files/lists/ipset-all.txt",
    "ipset_all_user": "files/lists/ipset-all_user.txt",
    "ipset_exclude": "files/lists/ipset-exclude.txt",
    "ipset_exclude_user": "files/lists/ipset-exclude_user.txt",
    "list_google": "files/lists/list-google.txt",
    "gw": "files/lists/gw.txt",
    "other": "files/lists/other.txt",
    "quicgoogle": "files/bin/quic_initial_www_google_com.bin",
    "tlsgoogle": "files/bin/tls_clienthello_www_google_com.bin",
    "tls4pda": "files/bin/tls_clienthello_4pda_to.bin",
    "tlsmax": "files/bin/tls_clienthello_max_ru.bin",
    "stun": "files/bin/stun.bin",
    "stun2": "files/bin/stun2.bin",
    "tlssochi": "files/bin/tls_clienthello_sochi_park.bin",
    "quic4pda": "files/bin/quic_initial_4pda_to.bin",
    "dbankcloud": "files/bin/quic_initial_dbankcloud_ru.bin",
    "GameFilter": None,  # подставляется портами, файла нет
}


def starter_placeholders() -> set[str]:
    text = STARTER.read_text(encoding="utf-8")
    return set(re.findall(r"\\\{([A-Za-z0-9_]+)\\\}", text))


def check_placeholders() -> list[str]:
    problems: list[str] = []
    supported = starter_placeholders()
    used: dict[str, set[str]] = {}
    for strategy in sorted(STRATEGY_DIR.iterdir()):
        if not strategy.is_file():
            continue
        found = set(re.findall(r"\{([A-Za-z0-9_]+)\}", strategy.read_text(encoding="utf-8")))
        for name in found:
            used.setdefault(name, set()).add(strategy.name)
    for name, files in sorted(used.items()):
        if name not in supported:
            problems.append(f"плейсхолдер {{{name}}} не раскрывается starter.sh (используется в: {', '.join(sorted(files))})")
        elif name in PLACEHOLDER_FILES and PLACEHOLDER_FILES[name] is not None:
            if not (REPO_ROOT / PLACEHOLDER_FILES[name]).is_file():
                problems.append(f"нет файла для {{{name}}}: {PLACEHOLDER_FILES[name]}")
    return problems


def check_format() -> list[str]:
    problems: list[str] = []
    for strategy in sorted(STRATEGY_DIR.iterdir()):
        if not strategy.is_file():
            continue
        lines = [line for line in strategy.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            problems.append(f"{strategy.name}: пустой файл")
            continue
        for index, line in enumerate(lines, start=1):
            if not line.startswith("--"):
                problems.append(f"{strategy.name}:{index}: строка не начинается с --")
            if "--new" in line and not line.endswith("--new"):
                problems.append(f"{strategy.name}:{index}: --new не в конце строки")
            if "\r" in line:
                problems.append(f"{strategy.name}:{index}: CR в строке")
    return problems


def dry_run(arch: str) -> list[str]:
    binary = REPO_ROOT / "zapret" / "bins" / arch / "nfqws"
    if not binary.is_file():
        return [f"нет бинарника {binary}"]
    problems: list[str] = []
    for strategy in sorted(STRATEGY_DIR.iterdir()):
        if not strategy.is_file():
            continue
        for index, line in enumerate(strategy.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            args = line
            for name, rel in PLACEHOLDER_FILES.items():
                args = args.replace("{" + name + "}", str(REPO_ROOT / rel) if rel else "12")
            proc = subprocess.run(
                [str(binary), "--dry-run", "--qnum=200", *args.split()],
                capture_output=True, text=True, timeout=20,
            )
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout).strip().splitlines()
                problems.append(f"{strategy.name}:{index}: nfqws --dry-run код {proc.returncode}: {err[-1] if err else ''}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="прогнать строки через nfqws --dry-run")
    parser.add_argument("--arch", default="x86_64", help="архитектура nfqws для --dry-run (по умолчанию x86_64)")
    args = parser.parse_args()

    problems = check_placeholders() + check_format()
    if args.dry_run:
        problems += dry_run(args.arch)

    total = len([p for p in STRATEGY_DIR.iterdir() if p.is_file()])
    if problems:
        print(f"стратегий: {total}, проблем: {len(problems)}")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"стратегий: {total}, проблем нет" + (" (включая nfqws --dry-run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
