"""Game Filter: индикатор, предупреждение, перезапуск службы."""
import os
import threading
import tkinter as tk

from ui.windows.gamefilter_window import GameFilterWindow, clear_active_game_preset_disk
from ui.windows.main.main_gamefilter_warning import show_game_filter_warning_dialog
from core.game_presets import get_active_preset_id, get_manager_dir
from core.game_filter_settings import (
    read_game_filter_protocol_mode,
    remove_game_filter_protocol_mode_file,
    write_game_filter_protocol_mode,
    GAMEFILTER_PROTOCOL_BOTH,
    GAMEFILTER_PROTOCOL_TCP,
    GAMEFILTER_PROTOCOL_UDP,
)
from ui.theme import theme


def _game_filter_protocol_label(mode: str) -> str:
    if mode == GAMEFILTER_PROTOCOL_TCP:
        return "только TCP"
    if mode == GAMEFILTER_PROTOCOL_UDP:
        return "только UDP"
    return "TCP и UDP"


class MainGameFilterMixin:
    def update_game_filter_indicator(self):
        """Обновляет цвет индикатора Game Filter"""
        active_preset = get_active_preset_id()
        if self.is_game_filter_enabled() or active_preset is not None:
            self.game_filter_indicator.config(fg=theme.color("success"))
        else:
            self.game_filter_indicator.config(fg=theme.color("error"))

    def is_game_filter_enabled(self):
        """Проверяет, включен ли Game Filter"""
        return os.path.exists(self.game_filter_file)

    def show_game_filter_tooltip(self, event=None):
        """Показывает всплывающее окошко со статусом Game Filter"""
        # Не показываем если уже есть
        if hasattr(self, 'game_filter_tooltip') and self.game_filter_tooltip:
            return

        # Определяем текст в зависимости от состояния
        if self.is_game_filter_enabled():
            mode = read_game_filter_protocol_mode()
            status_text = (
                "GameFilter включен\n"
                f"Подстановка {{GameFilter}}: {_game_filter_protocol_label(mode)}\n"
                "Нажмите для настроек / выключения"
            )
        else:
            status_text = "GameFilter выключен\nНажмите для включения"

        self.game_filter_tooltip = self._build_tooltip(
            self.game_filter_indicator, status_text, offset_x=-20
        )

    def hide_game_filter_tooltip(self, event=None):
        """Скрывает всплывающее окошко Game Filter"""
        if hasattr(self, 'game_filter_tooltip') and self.game_filter_tooltip:
            self.game_filter_tooltip.destroy()
            self.game_filter_tooltip = None

    def toggle_game_filter(self, event=None):
        """Открывает окно GameFilter при клике на иконку."""
        gamefilter_window = GameFilterWindow(self.root, self)
        gamefilter_window.run()

    def _show_game_filter_warning(self, protocol_mode: str = GAMEFILTER_PROTOCOL_BOTH):
        """Показывает предупреждение о Game Filter с адаптацией под Steam Deck"""
        show_game_filter_warning_dialog(self, protocol_mode)

    def _on_warning_accept(self, warning_window, protocol_mode: str = GAMEFILTER_PROTOCOL_BOTH):
        """Обработчик нажатия на кнопку 'Понятно, включить'"""
        warning_window.destroy()

        # Проверяем пароль sudo
        if not self.ensure_sudo_password():
            return

        # Выполняем включение Game Filter
        self._perform_game_filter_toggle(protocol_mode_for_enable=protocol_mode)

    def _perform_game_filter_toggle(self, protocol_mode_for_enable: str | None = None):
        """Выполняет фактическое переключение Game Filter"""
        try:
            # Получаем текущее состояние
            was_enabled = self.is_game_filter_enabled()
            had_preset = False

            if was_enabled:
                # Удаляем файл (выключаем)
                os.remove(self.game_filter_file)
                remove_game_filter_protocol_mode_file()
                new_icon = "⌨"
                status_message = "Game Filter выключен"
                print("🎮🔴 Game Filter выключен")
            else:
                # Отдельный GameFilter и пресет игры не используются одновременно
                had_preset = get_active_preset_id() is not None
                clear_active_game_preset_disk(get_manager_dir())
                if had_preset:
                    self.update_game_filter_indicator()

                # Создаем файл (включаем)
                # Сначала создаем директорию если не существует
                directory = os.path.dirname(self.game_filter_file)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)

                # Создаем файл
                with open(self.game_filter_file, 'w'):
                    pass  # Просто создаем пустой файл

                mode = protocol_mode_for_enable or GAMEFILTER_PROTOCOL_BOTH
                write_game_filter_protocol_mode(mode)

                new_icon = "⌨"
                status_message = (
                    f"Game Filter включен ({_game_filter_protocol_label(mode)})"
                )
                print(f"🎮🟢 Game Filter включен, режим: {mode}")

            # Меняем иконку
            self.game_filter_indicator.config(text=new_icon)

            # Обновляем всплывающую подсказку
            if hasattr(self, 'game_filter_tooltip') and self.game_filter_tooltip:
                self.hide_game_filter_tooltip()
                self.show_game_filter_tooltip()

            # Показываем одно сообщение: не перекрываем предупреждение о снятии пресета
            if had_preset:
                status_message = f"{status_message}; активный пресет игры снят"
            self.show_status_message(status_message, success=True)

            # Перезапускаем службу zapret
            self._restart_zapret_service(status_message)

        except Exception as e:
            error_msg = f"Ошибка переключения Game Filter: {e}"
            print(f"❌ {error_msg}")
            self.show_status_message(error_msg, error=True)

    def _restart_zapret_service(self, status_message):
        """Перезапускает службу zapret после изменения Game Filter"""
        if not self._begin_service_operation():
            return

        # Блокируем UI
        self.game_filter_indicator.config(state=tk.DISABLED)

        # Показываем анимацию загрузки (меняем цвет индикатора на предупреждающий)
        self.game_filter_indicator.config(fg=theme.color("warning"))
        self.show_status_message(f"{status_message}, перезапуск службы...")
        self.root.update()

        def restart_service_thread():
            try:
                # Запускаем перезапуск службы
                success, message = self.service_manager.restart_service()

                if success:
                    self._safe_after(lambda: self.show_status_message(
                        f"{status_message}, служба перезапущена", success=True))
                else:
                    self._safe_after(lambda m=message: self.show_status_message(
                        f"{status_message}, но служба не перезапущена: {m}", warning=True))

            except Exception as e:
                self._safe_after(lambda m=str(e): self.show_status_message(
                    f"Ошибка перезапуска службы: {m}", error=True))
            finally:
                # Восстанавливаем UI и обновляем индикатор
                self._safe_after(lambda: self.game_filter_indicator.config(state=tk.NORMAL))
                self._safe_after(self.update_game_filter_indicator)

                # Обновляем статус службы через 1 секунду
                self._safe_after(self.check_service_status, 1000)
                self._end_service_operation()

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=restart_service_thread, daemon=True)
        thread.start()

    def restart_zapret_after_preset(self, status_message):
        """Перезапускает службу zapret после изменения пресета (без изменения иконки GameFilter)."""
        if not self._begin_service_operation():
            return

        self.show_status_message(f"{status_message}, перезапуск службы...")
        self.root.update()

        def restart_thread():
            try:
                success, message = self.service_manager.restart_service()
                if success:
                    self._safe_after(lambda: self.show_status_message(
                        f"{status_message}, служба перезапущена", success=True))
                else:
                    self._safe_after(lambda m=message: self.show_status_message(
                        f"{status_message}, но служба не перезапущена: {m}", warning=True))
            except Exception as e:
                self._safe_after(lambda m=str(e): self.show_status_message(
                    f"Ошибка перезапуска службы: {m}", error=True))
            finally:
                self._safe_after(self.check_service_status, 1000)
                self._end_service_operation()

        thread = threading.Thread(target=restart_thread, daemon=True)
        thread.start()
