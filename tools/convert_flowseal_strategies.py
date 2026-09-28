#!/usr/bin/env python3
"""Конвертер стратегий Flowseal (.bat для Windows) в формат Zapret DPI Manager.

Источник стратегий проекта — репозиторий Flowseal/zapret-discord-youtube
(https://github.com/Flowseal/zapret-discord-youtube). Здесь лежат .bat-файлы,
которые запускают winws.exe с набором аргументов. Менеджер использует тот же
набор аргументов для nfqws, но в виде plain-text файла: одна строка — одно
правило (заканчивается на --new, кроме последнего).

Скрипт делает механическую конвертацию:
  * берёт командную строку после winws.exe, склеивает переносы «^»;
  * выбрасывает --wf-tcp/--wf-udp (starter.sh сам собирает порты из --filter-*);
  * заменяет пути %LISTS%/%BIN% на плейсхолдеры {list_general}/{tlsgoogle}/…,
    которые раскрывает zapret/system/starter.sh;
  * сохраняет доработки менеджера: --ipset={ipset_all_user} рядом с
    --ipset={ipset_all}, а ACTIVE_DISCORD_UDP.bin/ACTIVE_GAME_UDP.bin
    (их готовит service.bat) маппятся на существующий {dbankcloud};
  * проверяет, что не осталось %-путей, кавычек, «^» и неизвестных
    плейсхолдеров.

Использование:
    python3 tools/convert_flowseal_strategies.py                # показать
    python3 tools/convert_flowseal_strategies.py --write        # записать
    python3 tools/convert_flowseal_strategies.py --check        # сверить с files/strategy
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = REPO_ROOT / ".dsh" / "tmp" / "flowseal" / "src"
DEFAULT_OUT = REPO_ROOT / "files" / "strategy"

# Имя .bat -> имя файла стратегии менеджера (без расширения).
NAME_MAP = {
    "general": "General",
    "general (ALT)": "General_ALT",
    "general (ALT2)": "General_ALT2",
    "general (ALT3)": "General_ALT3",
    "general (ALT4)": "General_ALT4",
    "general (ALT5)": "General_ALT5",
    "general (ALT6)": "General_ALT6",
    "general (ALT7)": "General_ALT7",
    "general (ALT8)": "General_ALT8",
    "general (ALT9)": "General_ALT9",
    "general (ALT10)": "General_ALT10",
    "general (ALT11)": "General_ALT11",
    "general (ALT12)": "General_ALT12",
    "general (ALT13)": "General_ALT13",
    "general (EXP)": "General_EXP",
    "general (FAKE TLS AUTO)": "General_Fake_TLS_auto",
    "general (FAKE TLS AUTO ALT)": "General_Fake_TLS_auto_ALT",
    "general (FAKE TLS AUTO ALT2)": "General_Fake_TLS_auto_ALT2",
    "general (FAKE TLS AUTO ALT3)": "General_Fake_TLS_auto_ALT3",
    "general (SIMPLE FAKE)": "General_Simple_Fake",
    "general (SIMPLE FAKE ALT)": "General_Simple_Fake_ALT",
    "general (SIMPLE FAKE ALT2)": "General_Simple_Fake_ALT2",
}

# Пути Flowseal -> плейсхолдеры starter.sh.
PATH_MAP = {
    '"%LISTS%list-general.txt"': "{list_general}",
    '"%LISTS%list-general-user.txt"': "{list_general_user}",
    '"%LISTS%list-exclude.txt"': "{list_exclude}",
    '"%LISTS%list-exclude-user.txt"': "{list_exclude_user}",
    '"%LISTS%ipset-exclude.txt"': "{ipset_exclude}",
    '"%LISTS%ipset-exclude-user.txt"': "{ipset_exclude_user}",
    '"%LISTS%ipset-all.txt"': "{ipset_all}",
    '"%LISTS%list-google.txt"': "{list_google}",
    '"%BIN%quic_initial_www_google_com.bin"': "{quicgoogle}",
    '"%BIN%tls_clienthello_www_google_com.bin"': "{tlsgoogle}",
    '"%BIN%tls_clienthello_4pda_to.bin"': "{tls4pda}",
    '"%BIN%tls_clienthello_max_ru.bin"': "{tlsmax}",
    '"%BIN%stun.bin"': "{stun}",
    '"%BIN%stun2.bin"': "{stun2}",
    '"%BIN%quic_initial_4pda_to.bin"': "{quic4pda}",
    '"%BIN%quic_initial_5ka_ru.bin"': "{quic5ka}",
    '"%BIN%quic_initial_rutube_ru.bin"': "{quicrutube}",
    '"%BIN%quic_initial_steamcommunity_com.bin"': "{quicsteam}",
    '"%BIN%quic_initial_tencent_com.bin"': "{quictencent}",
    '"%BIN%tls_clienthello_5ka_ru.bin"': "{tls5ka}",
    '"%BIN%tls_clienthello_sochi_park.bin"': "{tlssochi}",
    '"%BIN%tls_clienthello_www_sferum_ru.bin"': "{tlssferum}",
    # service.bat подкладывает «активные» бинарники; в менеджере это {dbankcloud}.
    '"%BIN%ACTIVE_DISCORD_UDP.bin"': "{dbankcloud}",
    '"%BIN%ACTIVE_GAME_UDP.bin"': "{dbankcloud}",
}

# Плейсхолдеры, которые умеет раскрывать zapret/system/starter.sh.
# Список вычисляется из самого starter.sh, чтобы не расходиться с ним.
def _starter_placeholders() -> set[str]:
    starter = REPO_ROOT / "zapret" / "system" / "starter.sh"
    if not starter.is_file():
        return set()
    text = starter.read_text(encoding="utf-8")
    return set(re.findall(r"\\\{([A-Za-z0-9_]+)\\\}", text))


KNOWN_PLACEHOLDERS = _starter_placeholders() | {"GameFilter"}


def extract_command(bat_text: str) -> str:
    """Собирает командную строку winws.exe из .bat, разворачивая переносы «^»."""
    parts: list[str] = []
    started = False
    for raw_line in bat_text.splitlines():
        if "winws.exe" in raw_line:
            started = True
            raw_line = raw_line.split("winws.exe", 1)[1]
        elif not started:
            continue
        line = raw_line.strip()
        if line.endswith("^"):
            line = line[:-1].rstrip()
        if line:
            parts.append(line)
    return " ".join(parts)


def convert_command(command: str) -> list[str]:
    """Команда winws.exe -> список правил (строк) для nfqws."""
    cmd = command.replace("^!", "!")  # cmd-экранирование «!» в fake-tls=! и т.п.
    cmd = re.sub(r"--wf-(?:tcp|udp)=\S+", "", cmd)
    for src, dst in PATH_MAP.items():
        cmd = cmd.replace(src, dst)
    # Остатки кавычек: от "%BIN%winws.exe" и прочих аргументов .bat.
    cmd = cmd.replace('"', "")
    cmd = cmd.replace("%GameFilterTCP%", "{GameFilter}")
    cmd = cmd.replace("%GameFilterUDP%", "{GameFilter}")

    # Доработка менеджера: пользовательский ipset идёт сразу за основным.
    cmd = cmd.replace("--ipset={ipset_all}", "--ipset={ipset_all} --ipset={ipset_all_user}")

    cmd = re.sub(r"\s+", " ", cmd).strip()

    chunks = [c.strip() for c in re.split(r"--new", cmd)]
    rules = [c for c in chunks if c]
    result: list[str] = []
    for index, rule in enumerate(rules):
        if index < len(rules) - 1:
            rule = f"{rule} --new"
        result.append(rule)
    return result


def validate(rules: list[str], name: str) -> list[str]:
    """Возвращает список проблем в сконвертированной стратегии."""
    problems: list[str] = []
    if not rules:
        problems.append("пустой результат")
        return problems
    joined = "\n".join(rules)
    for pattern, message in (
        (r"%[A-Za-z_]+%", "остался %-путь"),
        (r'"', "осталась кавычка"),
        (r"\^", "осталось cmd-экранирование ^"),
        (r"--wf-(?:tcp|udp)", "остался --wf-*"),
        (r"ACTIVE_[A-Z_]+\.bin", "остался ACTIVE_*.bin"),
    ):
        if re.search(pattern, joined):
            problems.append(message)
    unknown = {
        p for p in re.findall(r"\{([A-Za-z0-9_]+)\}", joined)
        if p not in KNOWN_PLACEHOLDERS
    }
    if unknown:
        problems.append(f"неизвестные плейсхолдеры: {', '.join(sorted(unknown))}")
    for rule in rules:
        if not rule.startswith("--"):
            problems.append(f"строка не начинается с --: {rule[:60]}")
    return problems


def collect(src_dir: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for bat in sorted(src_dir.glob("*.bat")):
        if bat.stem not in NAME_MAP:
            continue
        rules = convert_command(extract_command(bat.read_text(encoding="utf-8", errors="replace")))
        result[NAME_MAP[bat.stem]] = rules
    return result


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

    failed = False
    for name, rules in strategies.items():
        problems = validate(rules, name)
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
