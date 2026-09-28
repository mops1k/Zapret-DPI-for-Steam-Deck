import subprocess
import time

from core.app_logging import get_error_logger
from core.sudo_helper import run_sudo, sudo_available


class ServiceManager:
    """Управление systemd-службой zapret.

    Пароль sudo вводится системным askpass-хелпером (`sudo -A`), приложение
    пароль не хранит и не передаёт.
    """

    def _run_sudo(self, argv, timeout=30):
        """Выполняет команду через sudo -A. Возвращает (ok, вывод или ошибка)."""
        if not sudo_available():
            return False, "sudo или askpass-хелпер недоступны"
        code, out, err = run_sudo(argv, timeout=timeout)
        if code == 0:
            return True, (out or "").strip()
        parts = [p.strip() for p in (err, out) if (p or "").strip()]
        merged = "\n".join(parts) if parts else f"(код выхода {code}, вывод пуст)"
        return False, merged

    @staticmethod
    def _run(argv, timeout=5):
        """Выполняет команду без sudo (чтение статуса)."""
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, "Таймаут выполнения команды"
        except OSError as e:
            return False, str(e)
        if proc.returncode == 0:
            return True, (proc.stdout or "").strip()
        return False, (proc.stderr or proc.stdout or "").strip()

    def _collect_zapret_failure_context(self, max_chars=12000):
        """systemctl status и journalctl для диагностики конфига."""
        chunks = []
        for argv in (
            ["systemctl", "status", "zapret", "--no-pager", "-l"],
            ["journalctl", "-u", "zapret.service", "-n", "50", "--no-pager"],
        ):
            _ok, out = self._run_sudo(argv, timeout=15)
            text = (out or "").strip()
            if text:
                chunks.append(f"$ {' '.join(argv)}\n{text}")
        result = "\n\n".join(chunks)
        if len(result) > max_chars:
            result = result[: max_chars - 24] + "\n… [фрагмент усечён]"
        return result

    def _verify_zapret_active_after_operation(self):
        """После start/restart: ждём выхода из activating и проверяем active."""
        last_state = ""
        last_rc = None
        for _ in range(24):
            ok, out = self._run(["systemctl", "is-active", "zapret"], timeout=8)
            state = (out or "").strip()
            last_state = state
            last_rc = 0 if ok else 1
            if state == "active":
                return True, state
            if state == "activating":
                time.sleep(0.35)
                continue
            break

        ctx = self._collect_zapret_failure_context()
        head = f"служба не в состоянии active после запуска: {last_state!r} (код is-active: {last_rc})"
        full = f"{head}\n\n{ctx}" if ctx else head
        return False, full

    def _start_or_restart_zapret(self, op):
        """op: 'start' или 'restart'. Пишет подробности в лог при ошибке."""
        log = get_error_logger()
        ok, msg = self._run_sudo(["systemctl", op, "zapret"], timeout=30)
        if not ok:
            ctx = self._collect_zapret_failure_context()
            full = (msg or "systemctl вернул ошибку").strip()
            if ctx:
                full = f"{full}\n\n{ctx}"
            log.error("systemctl %s zapret:\n%s", op, full)
            return False, full

        time.sleep(0.5)
        verify_ok, verify_msg = self._verify_zapret_active_after_operation()
        if not verify_ok:
            log.error("zapret не активна после %s:\n%s", op, verify_msg)
            return False, verify_msg
        return True, msg or "OK"

    def start_service(self):
        """Запускает службу zapret"""
        return self._start_or_restart_zapret("start")

    def stop_service(self):
        """Останавливает службу zapret"""
        return self._run_sudo(["systemctl", "stop", "zapret"], timeout=30)

    def restart_service(self):
        """Перезапускает службу zapret"""
        return self._start_or_restart_zapret("restart")

    def enable_autostart(self):
        """Включает автозапуск службы zapret"""
        return self._run_sudo(["systemctl", "enable", "zapret"], timeout=30)

    def disable_autostart(self):
        """Отключает автозапуск службы zapret"""
        return self._run_sudo(["systemctl", "disable", "zapret"], timeout=30)

    def get_service_status(self):
        """Статус службы zapret (чтение, без sudo)."""
        ok, out = self._run(["systemctl", "is-active", "zapret"], timeout=5)
        status = (out or "").strip()
        if status in ["active", "inactive", "failed", "activating", "deactivating"]:
            return status
        if not ok:
            ok2, out2 = self._run_sudo(
                ["systemctl", "status", "zapret", "--no-pager"], timeout=15
            )
            if ok2:
                low = out2.lower()
                if "active (running)" in low:
                    return "active"
                if "inactive (dead)" in low:
                    return "inactive"
                if "failed" in low:
                    return "failed"
        return "unknown"

    def get_autostart_status(self):
        """Проверяет, включён ли автозапуск (чтение, без sudo)."""
        ok, out = self._run(["systemctl", "is-enabled", "zapret"], timeout=5)
        value = (out or "").strip().lower()
        if value == "enabled":
            return True
        if value == "disabled":
            return False
        ok2, out2 = self._run(["systemctl", "list-unit-files", "zapret.service"], timeout=5)
        return bool(ok2 and "enabled" in out2.lower())

    def check_service_exists(self):
        """Проверяет, существует ли юнит zapret.service."""
        ok, out = self._run(["systemctl", "list-unit-files", "zapret.service"], timeout=5)
        return bool(ok and "zapret.service" in out)
