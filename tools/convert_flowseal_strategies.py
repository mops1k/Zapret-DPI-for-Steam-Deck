#!/usr/bin/env python3
"""Конвертер стратегий Flowseal (.bat) в формат Zapret DPI Manager (CLI).

Вся логика конвертации живёт в core/flowseal_convert.py — модуль попадает
в релизные архивы и используется при обновлении стратегий на стороне
пользователя. Этот скрипт нужен для CI и ручных проверок:

    python3 tools/convert_flowseal_strategies.py                # показать
    python3 tools/convert_flowseal_strategies.py --write        # записать
    python3 tools/convert_flowseal_strategies.py --check        # сверить с files/strategy
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from core.flowseal_convert import (  # noqa: E402
    collect,
    known_placeholders,
    starter_path,
    validate,
)

# Исходные .bat Flowseal лежат в репозитории, чтобы проверка работала и в CI
# (локальный .dsh/ в git не попадает). Переопределяется ключом --src.
DEFAULT_SRC = REPO_ROOT / "tools" / "flowseal_src"
DEFAULT_OUT = REPO_ROOT / "files" / "strategy"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC, help="каталог с .bat Flowseal")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="каталог files/strategy")
    parser.add_argument("--write", action="store_true", help="записать файлы стратегий")
    parser.add_argument("--check", action="store_true", help="сравнить с текущими файлами стратегий")
    args = parser.parse_args()

    if not args.src.is_dir():
        print(f"нет каталога с .bat: {args.src}", file=sys.stderr)
        return 2

    strategies = collect(args.src)
    if not strategies:
        print(f"в {args.src} не найдено ни одного .bat стратегии", file=sys.stderr)
        return 2

    allowed = known_placeholders(starter_path())
    failed = False
    for name, rules in strategies.items():
        problems = validate(rules, name, known=allowed)
        status = "OK" if not problems else "ОШИБКА: " + "; ".join(problems)
        if problems:
            failed = True
        target = args.out / name
        marker = ""
        if args.check:
            if target.exists():
                old = [line for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
                marker = " = совпадает" if old == rules else " ≠ отличается"
            else:
                marker = " (новый файл)"
        print(f"{name:32} {len(rules):2} правил  {status}{marker}")
        if args.write and not problems:
            target.write_text("\n".join(rules) + "\n", encoding="utf-8")

    if args.write and not failed:
        print(f"\nзаписано {len(strategies)} файлов в {args.out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
