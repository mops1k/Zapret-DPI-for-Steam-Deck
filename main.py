#!/usr/bin/env python3
import os
import sys

# Добавляем текущую директорию в путь для импортов до импортов пакетов проекта
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from core.app_logging import get_error_logger, setup_error_logging

setup_error_logging()

from ui.windows.main_window import MainWindow


def _acquire_single_instance_lock():
    """Блокировка второго экземпляра: два процесса пишут config.txt и службу.

    Возвращает открытый файл (держит блокировку, пока жив процесс) или None.
    """
    try:
        import fcntl
        from pathlib import Path

        cache_dir = Path(
            os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
        ) / "zapret_dpi_manager"
        cache_dir.mkdir(parents=True, exist_ok=True)
        lock_file = open(cache_dir / "manager.lock", "w", encoding="utf-8")
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        return lock_file
    except OSError:
        return None
    except Exception as e:
        print(f"Не удалось создать блокировку экземпляра: {e}")
        return None


def _warn_already_running():
    """Сообщает, что менеджер уже запущен (диалог, если есть GUI)."""
    message = "Zapret DPI Manager уже запущен."
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Zapret DPI Manager", message)
        root.destroy()
    except Exception:
        print(message)


def main():
    """Точка входа в программу"""
    err_log = get_error_logger()

    lock = _acquire_single_instance_lock()
    if lock is None:
        _warn_already_running()
        sys.exit(0)

    try:
        app = MainWindow()
        app.run()
    except ImportError as e:
        err_log.exception("Ошибка импорта")
        print(f"Ошибка импорта: {e}")
        print("Убедитесь, что все модули установлены правильно.")
        sys.exit(1)
    except Exception as e:
        err_log.exception("Неизвестная ошибка при запуске")
        print(f"Неизвестная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
