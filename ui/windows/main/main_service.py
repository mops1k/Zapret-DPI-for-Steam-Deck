"""systemd/zapret: статус, переключение, sudo, статусная строка."""
import subprocess
import threading
import tkinter as tk

from core.app_logging import LOG_FILE_PATH
from ui.theme import theme


def _shorten_service_error_message(message: str, limit: int = 700) -> str:
    if len(message) <= limit:
        return message
    return message[: limit - 60].rstrip() + f"\n… Полный вывод: {LOG_FILE_PATH}"


class MainServiceMixin:
    def _safe_after(self, func, delay=0):
        """Планирует вызов в главном потоке, не падая на уничтоженном окне."""
        try:
            if self.root.winfo_exists():
                self.root.after(delay, func)
        except (tk.TclError, RuntimeError):
            pass

    def _begin_service_operation(self) -> bool:
        """Единый флаг «операция со службой идёт» — защита от гонок restart/toggle."""
        if getattr(self, "_service_busy", False):
            self.show_status_message("Операция со службой уже выполняется", warning=True)
            return False
        self._service_busy = True
        return True

    def _end_service_operation(self):
        self._service_busy = False

    def restart_zapret_service_properly(self, event=None):
        """Правильный перезапуск службы - использует тот же механизм что и другие кнопки"""
        if not self._begin_service_operation():
            return

        # 1. Проверяем пароль ЧЕРЕЗ ensure_sudo_password (как другие кнопки)
        if not self.ensure_sudo_password():
            self._end_service_operation()
            return  # Если пароль не получен - выходим

        # 2. Запускаем перезапуск
        self._perform_restart()

    def _perform_restart(self):
        """Выполняет перезапуск службы"""
        try:
            # Сначала блокируем UI
            self.restarting = True
            self.restart_icon.config(state=tk.DISABLED)

            # Показываем сообщение
            self.show_status_message("Перезапуск службы Zapret...")

            # Обновляем окно чтобы оно было видимым
            self.root.update_idletasks()
            self.root.update()

            # Запускаем в отдельном потоке
            thread = threading.Thread(target=self._restart_zapret_thread, daemon=True)
            thread.start()

        except Exception as e:
            print(f"Ошибка при запуске перезапуска: {e}")
            self.show_status_message(f"Ошибка: {str(e)}", error=True)
            self.restarting = False
            self._end_service_operation()
            self.restart_icon.config(state=tk.NORMAL)

    def _restart_zapret_thread(self):
        """Поток для перезапуска службы"""
        try:
            # Запускаем перезапуск службы
            success, message = self.service_manager.restart_service()

            if success:
                self._safe_after(lambda: self.show_status_message(
                    "Служба Zapret успешно перезапущена", success=True))
            else:
                self._safe_after(lambda m=message: self.show_status_message(
                    f"Ошибка: {_shorten_service_error_message(m)}", error=True))

        except Exception as e:
            self._safe_after(lambda m=str(e): self.show_status_message(
                f"Ошибка перезапуска службы: {m}", error=True))
        finally:
            # Восстанавливаем UI
            self._safe_after(lambda: self.restart_icon.config(state=tk.NORMAL))
            self.restarting = False
            self._end_service_operation()

            # Обновляем статус службы через 1 секунду
            self._safe_after(self.check_service_status, 1000)
    def ensure_sudo_password(self):
        """Проверяет доступность sudo -A: пароль вводит системный askpass."""
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return False

        from core.sudo_helper import sudo_available

        if not sudo_available():
            self.show_status_message(
                "sudo или askpass-хелпер (core/askpass.py) недоступны", error=True
            )
            return False
        return True


    def _set_service_indicator(self, role: str, text: str) -> None:
        """Красит индикатор статуса и подпись в карточке службы токенами темы."""
        color = theme.color(role)
        try:
            self.status_indicator.config(text="⬤", fg=color)
        except tk.TclError:
            pass
        label = getattr(self, "service_state_label", None)
        if label is not None:
            try:
                label.config(text=text, fg=theme.color("on_surface") if role == "success" else color)
            except tk.TclError:
                pass

    def check_service_status(self):
        """Проверяет статус службы Zapret"""
        try:
            # Проверяем статус службы
            result = subprocess.run(
                ["systemctl", "is-active", "zapret"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            status_output = result.stdout.strip()

            if result.returncode == 0 and status_output == "active":
                # Служба активна
                self.service_running = True
                self._set_service_indicator("success", "Служба активна")
            elif result.returncode in (3, 4) or status_output in ("inactive", "unknown"):
                # Служба неактивна или не существует
                self.service_running = False
                self._set_service_indicator("error", "Служба остановлена")
            else:
                # Неизвестный статус
                self.service_running = False
                self._set_service_indicator("warning", "Статус службы неизвестен")

            # Текст кнопки не переписываем, пока идёт операция пользователя,
            # иначе опрос каждые 5 с инвертирует действие (start/stop).
            if not getattr(self, "_service_busy", False):
                self.zapret_button.config(
                    text="Остановить Zapret DPI" if self.service_running else "Запустить Zapret DPI"
                )

            # Теперь проверяем автозапуск ОТДЕЛЬНО
            self.check_autostart_status()

        except Exception as e:
            print(f"Ошибка проверки статуса службы: {e}")
            self.service_running = False
            self._set_service_indicator("warning", "Статус службы неизвестен")
            # Все равно проверяем автозапуск
            self.check_autostart_status()

    def check_autostart_status(self):
        """Проверяет и обновляет статус автозапуска"""
        try:
            # Проверяем статус автозапуска
            result = subprocess.run(
                ["systemctl", "is-enabled", "zapret"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # systemctl is-enabled возвращает:
            # - 0: enabled (включен)
            # - 1: disabled (отключен)
            # - другие коды: ошибка или не существует

            if result.returncode == 0:
                # Автозапуск включен
                self.autostart_enabled = True
            elif result.returncode == 1:
                # Автозапуск отключен
                self.autostart_enabled = False
            else:
                # Неизвестный статус (служба может не существовать)
                self.autostart_enabled = False

            if not getattr(self, "_service_busy", False):
                self.autostart_button.config(
                    text="Отключить автозапуск" if self.autostart_enabled else "Включить автозапуск"
                )

        except Exception as e:
            print(f"Ошибка проверки автозапуска: {e}")
            self.autostart_enabled = False
            if not getattr(self, "_service_busy", False):
                self.autostart_button.config(text="Включить автозапуск")

    def schedule_status_update(self):
        """Периодически обновляет статус службы"""
        try:
            self.check_service_status()
        except Exception as e:
            print(f"Ошибка при обновлении статуса: {e}")
        finally:
            self._safe_after(self.schedule_status_update, 5000)  # Проверка каждые 5 секунд

    def toggle_zapret(self):
        """Переключает состояние Zapret (запуск/остановка)"""
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return

        if not self._begin_service_operation():
            return

        # Проверяем пароль sudo
        if not self.ensure_sudo_password():
            self._end_service_operation()
            return

        # Фиксируем намерение ДО потока: 5-секундный опрос не должен его переписать.
        self._pending_service_action = "stop" if self.service_running else "start"

        # Меняем состояние UI
        self.zapret_button.config(state=tk.DISABLED)
        if self._pending_service_action == "stop":
            self.zapret_button.config(text="Остановка...")
            self.show_status_message("Остановка службы...")
        else:
            self.zapret_button.config(text="Запуск...")
            self.show_status_message("Запуск службы...")
        self.root.update()

        # Запускаем операцию в отдельном потоке
        thread = threading.Thread(target=self._toggle_zapret_thread)
        thread.daemon = True
        thread.start()

    def _toggle_zapret_thread(self):
        """Поток для переключения состояния службы"""
        action = getattr(self, "_pending_service_action", "start")
        try:
            if action == "stop":
                # Останавливаем службу
                success, message = self.service_manager.stop_service()
                if success:
                    self._safe_after(lambda: self.show_status_message("Служба остановлена", success=True))
                else:
                    self._safe_after(lambda m=message: self.show_status_message(
                        f"Ошибка остановки: {m}", error=True))
            else:
                # Запускаем службу
                success, message = self.service_manager.start_service()
                if success:
                    self._safe_after(lambda: self.show_status_message("Служба запущена", success=True))
                else:
                    self._safe_after(lambda m=message: self.show_status_message(
                        f"Ошибка запуска: {_shorten_service_error_message(m)}",
                        error=True,
                    ))

            # Обновляем статус после операции
            self._safe_after(self.check_service_status, 1000)

        except Exception as e:
            self._safe_after(lambda m=str(e): self.show_status_message(f"Ошибка: {m}", error=True))
        finally:
            # Восстанавливаем кнопку
            self._pending_service_action = None
            self._safe_after(lambda: self.zapret_button.config(state=tk.NORMAL), 100)
            self._end_service_operation()

    def toggle_autostart(self):
        """Переключает автозапуск"""
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return

        if not self._begin_service_operation():
            return

        # Сначала проверяем текущий статус
        self.check_autostart_status()

        # Проверяем пароль sudo
        if not self.ensure_sudo_password():
            self._end_service_operation()
            return

        # Фиксируем намерение до потока
        self._pending_autostart_action = "disable" if self.autostart_enabled else "enable"

        # Меняем состояние UI
        self.autostart_button.config(state=tk.DISABLED)
        if self._pending_autostart_action == "disable":
            self.autostart_button.config(text="Отключение...")
            self.show_status_message("Отключение автозапуска...")
        else:
            self.autostart_button.config(text="Включение...")
            self.show_status_message("Включение автозапуска...")
        self.root.update()

        # Запускаем операцию в отдельном потоке
        thread = threading.Thread(target=self._toggle_autostart_thread)
        thread.daemon = True
        thread.start()

    def _toggle_autostart_thread(self):
        """Поток для переключения автозапуска"""
        action = getattr(self, "_pending_autostart_action", "enable")
        try:
            if action == "disable":
                # Отключаем автозапуск
                success, message = self.service_manager.disable_autostart()
                if success:
                    self._safe_after(lambda: self.show_status_message("Автозапуск отключен", success=True))
                    self.autostart_enabled = False
                else:
                    self._safe_after(lambda m=message: self.show_status_message(
                        f"Ошибка отключения: {m}", error=True))
            else:
                # Включаем автозапуск
                success, message = self.service_manager.enable_autostart()
                if success:
                    self._safe_after(lambda: self.show_status_message("Автозапуск включен", success=True))
                    self.autostart_enabled = True
                else:
                    self._safe_after(lambda m=message: self.show_status_message(
                        f"Ошибка включения: {m}", error=True))

            # Обновляем статус после операции
            self._safe_after(self.check_autostart_status, 1000)

        except Exception as e:
            self._safe_after(lambda m=str(e): self.show_status_message(f"Ошибка: {m}", error=True))
        finally:
            # Восстанавливаем кнопку и обновляем текст
            self._pending_autostart_action = None
            self._safe_after(lambda: self.autostart_button.config(state=tk.NORMAL), 100)
            self._safe_after(self.check_autostart_status, 150)
            self._end_service_operation()

    def show_status_message(self, message, success=False, warning=False, error=False):
        """Показывает сообщение в статусной строке"""
        self._safe_after(lambda: self._update_status_message(message, success, warning, error))

    def _update_status_message(self, message, success, warning, error):
        """Обновляет статусное сообщение в основном потоке"""
        self.status_message.config(text=message)

        if success:
            self.status_message.config(fg=theme.color("success"))
        elif warning:
            self.status_message.config(fg=theme.color("warning"))
        elif error:
            self.status_message.config(fg=theme.color("error"))
        else:
            self.status_message.config(fg=theme.color("on_surface_variant"))

        # Автоматически очищаем сообщение через 3 секунды (кроме ошибок).
        # Предыдущий таймер отменяем, иначе старое сообщение стирает новое.
        pending = getattr(self, "_status_clear_job", None)
        if pending is not None:
            try:
                self.root.after_cancel(pending)
            except (tk.TclError, ValueError):
                pass
            self._status_clear_job = None

        if message and not error:
            def _clear_status():
                self._status_clear_job = None
                try:
                    if self.root.winfo_exists():
                        self.status_message.config(text="")
                except tk.TclError:
                    pass

            try:
                self._status_clear_job = self.root.after(3000, _clear_status)
            except (tk.TclError, RuntimeError):
                pass
