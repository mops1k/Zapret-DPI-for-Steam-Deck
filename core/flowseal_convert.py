"""Конвертер стратегий Flowseal (.bat для Windows) в формат Zapret DPI Manager.

Источник стратегий проекта — репозиторий Flowseal/zapret-discord-youtube
(https://github.com/Flowseal/zapret-discord-youtube). Там лежат .bat-файлы,
которые запускают winws.exe с набором аргументов. Менеджер использует тот же
набор аргументов для nfqws, но в виде plain-text файла: одна строка — одно
правило (заканчивается на --new, кроме последнего).

Модуль лежит в core/, потому что в релизные архивы попадают только
main.py/core/ui/files/ico/utils/zapret — каталог tools/ туда не входит,
а конвертация нужна и на стороне пользователя (обновление стратегий без
полного обновления приложения).

Конвертация механическая:
  * берётся командная строка после winws.exe, переносы «^» склеиваются;
  * выбрасываются --wf-tcp/--wf-udp (starter.sh сам собирает порты из --filter-*);
  * пути %LISTS%/%BIN% заменяются плейсхолдерами {list_general}/{tlsgoogle}/…,
    которые раскрывает zapret/system/starter.sh;
  * сохраняются доработки менеджера: --ipset={ipset_all_user} рядом с
    --ipset={ipset_all}, а ACTIVE_DISCORD_UDP.bin/ACTIVE_GAME_UDP.bin
    (их готовит service.bat) маппятся на существующий {dbankcloud};
  * проверяется, что не осталось %-путей, кавычек, «^» и неизвестных
    плейсхолдеров (неизвестные означают, что стратегия несовместима с
    локальным starter.sh).
"""

from __future__ import annotations

import re
from pathlib import Path

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

# .bin Flowseal, которые нужны стратегиям (скачиваются при обновлении стратегий).
FLOWSEAL_BIN_FILES = (
    "quic_initial_4pda_to.bin",
    "quic_initial_5ka_ru.bin",
    "quic_initial_rutube_ru.bin",
    "quic_initial_steamcommunity_com.bin",
    "quic_initial_tencent_com.bin",
    "quic_initial_www_google_com.bin",
    "stun.bin",
    "stun2.bin",
    "tls_clienthello_4pda_to.bin",
    "tls_clienthello_5ka_ru.bin",
    "tls_clienthello_max_ru.bin",
    "tls_clienthello_sochi_park.bin",
    "tls_clienthello_www_google_com.bin",
    "tls_clienthello_www_sferum_ru.bin",
)

# Списки Flowseal, которые можно мержить (без *_user.txt и без backup-файлов).
FLOWSEAL_LIST_FILES = (
    "list-general.txt",
    "list-exclude.txt",
    "list-google.txt",
    "ipset-all.txt",
    "ipset-exclude.txt",
)


def package_root() -> Path:
    """Корень пакета менеджера: core/ лежит в его корне и в репозитории, и на клиенте."""
    return Path(__file__).resolve().parents[1]


def starter_path(root: Path | None = None) -> Path:
    """Путь к starter.sh, плейсхолдеры которого считаются поддерживаемыми."""
    return (root or package_root()) / "zapret" / "system" / "starter.sh"


def starter_placeholders(starter: Path | None = None) -> set[str]:
    """Плейсхолдеры, которые раскрывает starter.sh (по тексту самого скрипта)."""
    path = starter or starter_path()
    if not path.is_file():
        return set()
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"\\\{([A-Za-z0-9_]+)\\\}", text))


def known_placeholders(starter: Path | None = None) -> set[str]:
    """Плейсхолдеры, допустимые в сконвертированной стратегии."""
    return starter_placeholders(starter) | {"GameFilter"}


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


def validate(
    rules: list[str],
    name: str = "",
    known: set[str] | None = None,
    starter: Path | None = None,
) -> list[str]:
    """Возвращает список проблем в сконвертированной стратегии."""
    problems: list[str] = []
    if not rules:
        problems.append("пустой результат")
        return problems
    allowed = known if known is not None else known_placeholders(starter)
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
        if p not in allowed
    }
    if unknown:
        problems.append(f"неизвестные плейсхолдеры: {', '.join(sorted(unknown))}")
    for rule in rules:
        if not rule.startswith("--"):
            problems.append(f"строка не начинается с --: {rule[:60]}")
    return problems


def convert_bat_text(
    bat_text: str,
    known: set[str] | None = None,
    starter: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Текст .bat -> (правила, проблемы)."""
    rules = convert_command(extract_command(bat_text))
    return rules, validate(rules, known=known, starter=starter)


def collect(src_dir: Path, starter: Path | None = None) -> dict[str, list[str]]:
    """Все известные .bat из каталога -> {имя стратегии: правила} (без валидации)."""
    result: dict[str, list[str]] = {}
    for bat in sorted(Path(src_dir).glob("*.bat")):
        if bat.stem not in NAME_MAP:
            continue
        rules = convert_command(
            extract_command(bat.read_text(encoding="utf-8", errors="replace"))
        )
        result[NAME_MAP[bat.stem]] = rules
    return result
