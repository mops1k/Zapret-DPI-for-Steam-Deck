"""Единая обёртка запуска команд через sudo с системным askpass (`sudo -A`).

Приложение не хранит и не передаёт пароль: sudo сам вызывает SUDO_ASKPASS
(core/askpass.py), который показывает системный диалог. Кэширование пароля —
только системное (timestamp sudo), приложение к нему доступа не имеет.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ASKPASS_PATH = Path(__file__).resolve().with_name("askpass.py")


def askpass_env() -> dict:
    """Окружение с SUDO_ASKPASS (нужен и sudo, и самому хелперу)."""
    env = os.environ.copy()
    env["SUDO_ASKPASS"] = str(ASKPASS_PATH)
    return env


def sudo_available() -> bool:
    """Есть ли sudo и сам хелпер (без него sudo -A не сможет спросить пароль)."""
    return bool(shutil.which("sudo")) and ASKPASS_PATH.is_file()


def cache_file() -> Path:
    """Файл запомненного пароля (0600, владелец — пользователь)."""
    from core.askpass import CACHE_FILE

    return CACHE_FILE


def has_cached_password() -> bool:
    return cache_file().is_file()


def forget_cached_password() -> bool:
    """Удаляет запомненный пароль. True — файл был и удалён."""
    try:
        cache_file().unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


_AUTH_FAIL_MARKERS = (
    "incorrect password",
    "sorry, try again",
    "authentication failure",
    "неверный пароль",
)


def _drop_cache_on_auth_failure(stderr: str) -> None:
    low = (stderr or "").lower()
    if any(marker in low for marker in _AUTH_FAIL_MARKERS):
        forget_cached_password()


def run_sudo(argv, timeout: float = 60, capture: bool = True):
    """Выполняет `sudo -A <argv>`.

    Возвращает (returncode, stdout, stderr); при таймауте/ошибке запуска —
    код 1 и текст причины в stderr.
    """
    cmd = ["sudo", "-A", *[str(arg) for arg in argv]]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            env=askpass_env(),
        )
    except subprocess.TimeoutExpired:
        return 1, "", "Таймаут выполнения команды"
    except OSError as e:
        return 1, "", str(e)
    if proc.returncode != 0:
        _drop_cache_on_auth_failure(proc.stderr or "")
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def popen_sudo(argv, **kwargs):
    """Popen для потоковых задач: `sudo -A <argv>` с тем же окружением."""
    cmd = ["sudo", "-A", *[str(arg) for arg in argv]]
    kwargs.setdefault("env", askpass_env())
    return subprocess.Popen(cmd, **kwargs)


def check_sudo() -> bool:
    """Проверяет, что sudo -A действительно работает (пароль спрашивает хелпер)."""
    if not sudo_available():
        return False
    code, _, _ = run_sudo(["true"], timeout=300)
    return code == 0
