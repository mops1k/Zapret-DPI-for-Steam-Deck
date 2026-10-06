#!/usr/bin/env python3
"""Проверка конвертера BB DPI (ciadpi) -> nfqws.

Прогоняет типовые строки стратегий из BB DPI (byedpi/ciadpi) через
core/bbdpi_convert.py и nfqws --dry-run, чтобы конвертер не выдавал
аргументы, которые движок не понимает.

Использование:
    python3 tools/check_bbdpi_convert.py
    python3 tools/check_bbdpi_convert.py --arch x86_64 --verbose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.bbdpi_convert import convert, dry_run  # noqa: E402

# Типовые строки из обсуждений byedpi и ByeByeDPI (короткий и длинный синтаксис).
SAMPLES = [
    "-s1 -d1 -r1+s -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1",
    "-s0 -o1 -d1 -r1+s -Ar -o1 -At -f-1 -r1+s -As",
    "-s1 -o1 -d1 -r1+s -a1 -At -f-1 -r1+s -a1",
    "--split 1 --disorder 3+s --mod-http=h,d --auto=torst --tlsrec 1+s",
    "--fake -1 --md5sig",
    "--disorder 1 --auto=torst --tlsrec 1+s",
    "--disorder 1 --fake -1 --ttl 8",
    "--split 1+s --fake -1 --ttl 8 --fake-sni=www.google.com",
    "--split 1:3:5 --hosts :youtube.com,discord.com --pf 443",
    "--disorder 1 --proto t,h --mod-http=h,d,r",
    "--oob 3+s --disorder 7",
    "-s1 -f-1 -t8 -S",
    "-U -a3 -f-1 -t5 -S",
    "--split 1 --disorder 7 --fake -1 --md5sig --auto=ssl_err --fake -1 --ttl 5",
    "--fake-data=':GET / HTTP/1.1' --split 1",
    "--split 1 --disorder 3 --ipset :203.0.113.0/24",
    "  --disorder   1   --fake  -1 ",
    "",
    "мусор без опций",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true", help="печатать предупреждения и неподдержанные опции")
    args = parser.parse_args()

    problems: list[str] = []
    converted = 0
    for sample in SAMPLES:
        result = convert(sample)
        if not sample.strip():
            if result.rules:
                problems.append(f"«{sample}»: пустая строка дала правила")
            continue
        if not result.rules:
            problems.append(f"«{sample}»: конвертер не выдал ни одной строки")
            continue
        converted += 1
        if args.verbose:
            print(f"ВХОД: {sample}")
            for rule in result.rules:
                print(f"  -> {rule}")
            for warning in result.warnings:
                print(f"  предупреждение: {warning}")
            for item in result.unsupported:
                print(f"  не перенесено: {item}")
        for problem in dry_run(result.rules, app_root=REPO_ROOT):
            problems.append(f"«{sample}»: {problem}")

    if problems:
        print(f"строк: {len(SAMPLES)}, сконвертировано: {converted}, проблем: {len(problems)}")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"строк: {len(SAMPLES)}, сконвертировано: {converted}, проблем нет (включая nfqws --dry-run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
