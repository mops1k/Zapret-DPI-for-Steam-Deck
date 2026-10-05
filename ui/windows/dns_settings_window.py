#!/usr/bin/env python3
import tkinter as tk
import subprocess
import re
from ui.components.custom_messagebox import show_info, show_error
from ui.components.button_styler import create_hover_button
from core.sudo_helper import run_sudo
from core.dpi_utils import place_toplevel_centered_on_parent, wait_window_safely
from ui.theme import theme

class DNSSettingsWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None

        # DNS серверы
        self.dns_servers = {
            "Автоматический": "",
            "Cloudflare": "1.1.1.1 1.0.0.1",
            "Google": "8.8.8.8 8.8.4.4",
            "Dns.SB": "185.222.222.222 45.11.45.11",
            "Quad9": "9.9.9.9 149.112.112.112",
            "AdGuard": "94.140.14.14 94.140.15.15",
            "Xbox DNS": "111.88.96.50 111.88.96.51",
            "GeoHide DNS": "45.155.204.190 37.230.192.51",
            "DNS Mafioznik.xyz": "103.27.157.38 103.27.157.100",
            "Comss DNS": "83.220.169.155 212.109.195.93"
        }

        # Переменные для чекбоксов
        self.dns_vars = {}
        for dns_name in self.dns_servers.keys():
            self.dns_vars[dns_name] = tk.BooleanVar(value=False)

        # Переменные для пользовательских DNS
        self.custom_primary_var = tk.StringVar()
        self.custom_secondary_var = tk.StringVar()

        # Текущее активное подключение и его устройство
        self.active_connection = None
        self.active_device = None
        self._prev_dns = None

    def create_hover_button(self, parent, text, command, **kwargs):
        """Создает кнопку в стиле главного меню с эффектом наведения"""
        return create_hover_button(parent, text, command, **kwargs)

    def find_active_wifi(self):
        """Находит активное подключение и его устройство (DEVICE)."""
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'NAME,DEVICE,TYPE', 'connection', 'show', '--active'],
                capture_output=True,
                text=True,
                timeout=10,
            )

            self.active_device = None
            if result.returncode == 0:
                lines = [line for line in result.stdout.strip().split('\n') if line]

                # 1) Предпочитаем Wi-Fi
                for line in lines:
                    parts = line.split(':')
                    name = parts[0] if parts else ''
                    device = parts[1] if len(parts) > 1 else ''
                    conn_type = parts[2] if len(parts) > 2 else ''
                    if name and device and conn_type == 'wifi':
                        self.active_connection = name
                        self.active_device = device
                        return self.active_connection

                # 2) Иначе — любое активное подключение с устройством
                for line in lines:
                    parts = line.split(':')
                    name = parts[0] if parts else ''
                    device = parts[1] if len(parts) > 1 else ''
                    if name and device:
                        self.active_connection = name
                        self.active_device = device
                        return self.active_connection

            return None

        except Exception as e:
            print(f"Ошибка поиска активного подключения: {e}")
            return None

    def _resolve_device(self) -> str:
        """Устройство для resolvectl: реальный DEVICE из nmcli (fallback wlan0)."""
        return self.active_device or 'wlan0'

    def _read_conn_dns(self):
        """Сохраняет текущие DNS-настройки соединения для отката."""
        if not self.active_connection:
            return None
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-g', 'ipv4.dns,ipv4.ignore-auto-dns,ipv6.dns,ipv6.ignore-auto-dns',
                 'connection', 'show', self.active_connection],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
        except Exception as e:
            print(f"Не удалось сохранить текущие DNS: {e}")
        return None

    def _restore_conn_dns(self) -> bool:
        """Возвращает прежние DNS-настройки соединения (откат)."""
        if not self._prev_dns or not self.active_connection:
            return False
        try:
            dns4, ignore4, dns6, ignore6 = (list(self._prev_dns) + [''] * 4)[:4]
            args = ['nmcli', 'connection', 'modify', self.active_connection]
            if dns4:
                args += ['ipv4.dns', dns4]
            if ignore4:
                args += ['ipv4.ignore-auto-dns', ignore4]
            if dns6:
                args += ['ipv6.dns', dns6]
            if ignore6:
                args += ['ipv6.ignore-auto-dns', ignore6]
            code, _out, _err = run_sudo(args, timeout=60)
            return code == 0
        except Exception as e:
            print(f"Ошибка отката DNS: {e}")
            return False

    def _unbind_wheel(self):
        """Снимает глобальную привязку <MouseWheel> (иначе скролл ломается в других окнах)."""
        try:
            if self.window is not None:
                self.window.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass

    def get_current_dns_settings(self):
        """Получить текущие настройки DNS из resolvectl"""
        try:
            result = subprocess.run(
                ['resolvectl', 'status', self._resolve_device()],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                output = result.stdout
                dns_servers = []

                # Ищем строки с DNS серверами
                for line in output.split('\n'):
                    line = line.strip()
                    if 'DNS Servers:' in line:
                        # Извлекаем DNS серверы
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            servers = parts[1].strip()
                            if servers:
                                dns_servers = servers.split()
                                break

                # Формируем строку как в нашем формате (например: "8.8.8.8 8.8.4.4")
                current_dns = ' '.join(dns_servers) if dns_servers else ''

                # Проверяем, использует ли система автоматические DNS
                is_auto_dns = False
                for line in output.split('\n'):
                    if 'Protocols:' in line and '+DefaultRoute' in line:
                        is_auto_dns = True
                        break

                return {
                    'current_dns': current_dns,
                    'is_auto_dns': is_auto_dns
                }

        except Exception as e:
            print(f"Ошибка получения настроек DNS: {e}")

        return None

    def validate_ip_address(self, ip_str):
        """Проверяет корректность IP адреса"""
        if not ip_str:
            return True, ""  # Пустая строка допустима для дополнительного DNS

        # Паттерн для IPv4
        ipv4_pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

        if re.match(ipv4_pattern, ip_str):
            return True, ""
        else:
            return False, "Некорректный формат IP адреса"


    def reset_to_auto(self):
        """Сбросить на автоматические DNS (пароль вводит системный askpass)."""
        if not self.active_connection:
            show_error(self.window, "Ошибка", "Не найдено активное подключение")
            return False

        try:
            # Сохраняем прежние настройки DNS для отката
            self._prev_dns = self._read_conn_dns()

            # 1. Включить получение DNS от DHCP
            code, _out, err = run_sudo([
                'nmcli', 'connection', 'modify',
                self.active_connection,
                'ipv4.ignore-auto-dns', 'no',
                'ipv6.ignore-auto-dns', 'no'
            ], timeout=60)

            if code != 0:
                show_error(self.window, "Ошибка", f"Не удалось изменить настройки DHCP:\n{err}")
                return False

            # 2. Очистить статические DNS
            run_sudo(
                ['nmcli', 'connection', 'modify', self.active_connection, 'ipv4.dns', ''],
                timeout=60,
            )
            run_sudo(
                ['nmcli', 'connection', 'modify', self.active_connection, 'ipv6.dns', ''],
                timeout=60,
            )

            # 3. Переподключить
            run_sudo(['nmcli', 'connection', 'down', self.active_connection], timeout=60)
            code, _out, err = run_sudo(
                ['nmcli', 'connection', 'up', self.active_connection], timeout=90
            )

            if code != 0:
                self._restore_conn_dns()
                run_sudo(['nmcli', 'connection', 'up', self.active_connection], timeout=90)
                show_error(
                    self.window, "Ошибка",
                    f"Не удалось подключиться:\n{err}\nПрежние настройки DNS восстановлены.",
                )
                return False

            # 4. Сбросить через resolvectl
            run_sudo(['resolvectl', 'revert', self._resolve_device()], timeout=30)
            run_sudo(['resolvectl', 'default-route', self._resolve_device(), 'yes'], timeout=30)

            return True

        except Exception as e:
            show_error(self.window, "Ошибка", f"Ошибка при сбросе DNS: {e}")
            return False

    def set_custom_dns(self, dns_servers):
        """Установить кастомные DNS (пароль вводит системный askpass)."""
        if not self.active_connection:
            show_error(self.window, "Ошибка", "Не найдено активное подключение")
            return False

        try:
            # Сохраняем прежние настройки DNS для отката
            self._prev_dns = self._read_conn_dns()

            # 1. Установить кастомные DNS через nmcli
            code, _out, err = run_sudo([
                'nmcli', 'connection', 'modify',
                self.active_connection,
                'ipv4.dns', dns_servers,
                'ipv4.ignore-auto-dns', 'yes'
            ], timeout=60)

            if code != 0:
                show_error(self.window, "Ошибка", f"Не удалось установить DNS настройки:\n{err}")
                return False

            # 2. Переподключить соединение (ошибки down игнорируем — оно могло быть отключено)
            run_sudo(['nmcli', 'connection', 'down', self.active_connection], timeout=60)

            # 3. Включить соединение
            code, _out, err = run_sudo(
                ['nmcli', 'connection', 'up', self.active_connection], timeout=90
            )

            if code != 0:
                self._restore_conn_dns()
                run_sudo(['nmcli', 'connection', 'up', self.active_connection], timeout=90)
                show_error(
                    self.window, "Ошибка",
                    f"Не удалось подключиться:\n{err}\nПрежние настройки DNS восстановлены.",
                )
                return False

            # 4. Установить через resolvectl для текущей сессии (ошибки некритичны)
            servers_list = dns_servers.split()
            run_sudo(['resolvectl', 'dns', self._resolve_device()] + servers_list, timeout=30)

            # 5. Отключить автоматический маршрут
            run_sudo(['resolvectl', 'default-route', self._resolve_device(), 'false'], timeout=30)

            return True

        except Exception as e:
            show_error(self.window, "Ошибка", f"Ошибка при установке DNS: {e}")
            return False

    def on_dns_selected(self, selected_dns):
        """Обработчик выбора DNS"""
        # Снимаем все остальные чекбоксы
        for dns_name, var in self.dns_vars.items():
            if dns_name != selected_dns:
                var.set(False)

    def apply_dns_settings(self):
        """Применить выбранные настройки DNS"""
        # Проверяем активное подключение
        self.find_active_wifi()
        if not self.active_connection:
            show_error(
                self.window,
                "Ошибка",
                "Не найдено активное подключение Wi-Fi. Убедитесь, что Wi-Fi включен.",
            )
            return

        # Получаем значения из полей ввода
        custom_primary = self.custom_primary_var.get().strip()
        custom_secondary = self.custom_secondary_var.get().strip()

        # Проверяем, является ли текст примером
        def is_example_text(text):
            return text.startswith("Пример:")

        # Определяем, используется ли пользовательский DNS
        using_custom_dns = (custom_primary and not is_example_text(custom_primary))

        # Определяем, какой DNS выбран через чекбоксы
        selected_dns = None
        for dns_name, var in self.dns_vars.items():
            if dns_name == "Автоматический":
                continue  # Игнорируем "Автоматический" как пресет
            if var.get():
                selected_dns = dns_name
                break

        # Если используется пользовательский DNS
        if using_custom_dns:
            print(f"Используется пользовательский DNS: основной={custom_primary}, дополнительный={custom_secondary}")

            # Проверяем основной DNS
            is_valid, error_msg = self.validate_ip_address(custom_primary)
            if not is_valid:
                show_error(self.window, "Ошибка",
                        f"Некорректный основной DNS: {error_msg}")
                return

            # Проверяем дополнительный DNS, если он введен и не является примером
            if custom_secondary and not is_example_text(custom_secondary):
                is_valid, error_msg = self.validate_ip_address(custom_secondary)
                if not is_valid:
                    show_error(self.window, "Ошибка",
                            f"Некорректный дополнительный DNS: {error_msg}")
                    return

            # Формируем строку DNS серверов
            if custom_secondary and not is_example_text(custom_secondary):
                dns_servers = f"{custom_primary} {custom_secondary}"
            else:
                dns_servers = custom_primary

            # Если есть выбранный чекбокс - сбрасываем его
            if selected_dns:
                print(f"Чекбокс '{selected_dns}' игнорируется, так как введен пользовательский DNS")
                self.dns_vars[selected_dns].set(False)

            # Пользовательский DNS всегда имеет приоритет
            if self.set_custom_dns(dns_servers):
                show_info(
                    self.window,
                    "Успех",
                    (
                        f"Пользовательские DNS успешно применены. "
                        f"Подключение: {self.active_connection}. DNS: {dns_servers}"
                    ),
                )
                # Закрываем окно после успешного применения
                self.window.destroy()

        # Если используется чекбокс (пресет)
        elif selected_dns:
            dns_servers = self.dns_servers[selected_dns]
            print(f"Используется пресет DNS: {selected_dns}")

            if self.set_custom_dns(dns_servers):
                # Показываем сообщение и ждем, пока пользователь нажмет OK
                show_info(
                    self.window,
                    "Успех",
                    (
                        f"Пользовательские DNS успешно применены. "
                        f"Подключение: {self.active_connection}. DNS: {dns_servers}"
                    ),
                )
                # Закрываем окно после того, как пользователь нажал OK
                self.window.destroy()

        # Если выбрано "Автоматический" (сброс)
        elif self.dns_vars["Автоматический"].get():
            print("Выбран сброс на автоматические DNS")

            if self.reset_to_auto():
                show_info(
                    self.window,
                    "Успех",
                    (
                        f"DNS сброшены на автоматические (DHCP). "
                        f"Подключение: {self.active_connection}"
                    ),
                )
                # Закрываем окно после успешного применения
                self.window.destroy()

        # Если ничего не выбрано
        else:
            # Проверяем, если пользователь пытался ввести DNS, но оставил пример
            if custom_primary and is_example_text(custom_primary):
                show_error(
                    self.window,
                    "Ошибка",
                    (
                        "Введите реальный DNS адрес в поле «Основной» "
                        "или выберите один из предложенных DNS серверов."
                    ),
                )
            else:
                show_error(self.window, "Ошибка", "Не выбран ни один DNS сервер")
            return

    def create_dns_group(self, parent, group_name, dns_list):
        """Создает группу чекбоксов DNS"""
        group_frame = tk.Frame(parent, bg=theme.color('surface'))
        group_frame.pack(fill=tk.X, pady=(8, 0))

        # Заголовок группы
        title_label = tk.Label(
            group_frame,
            text=group_name,
            font=theme.font('title_small'),
            fg=theme.color('primary'),
            bg=theme.color('surface')
        )
        title_label.pack(anchor=tk.W, pady=(0, 0))

        # Создаем чекбоксы
        for dns_name in dns_list:
            if dns_name in self.dns_vars:
                # Используем Frame с grid для выравнивания в две колонки
                check_frame = tk.Frame(group_frame, bg=theme.color('surface'))
                check_frame.pack(fill=tk.X, pady=1)

                # Настраиваем grid для двух колонок
                check_frame.columnconfigure(0, weight=1)  # Колонка для чекбокса
                check_frame.columnconfigure(1, weight=0)  # Колонка для DNS адресов

                check = tk.Checkbutton(
                    check_frame,
                    text=dns_name,
                    variable=self.dns_vars[dns_name],
                    font=theme.font('body_small'),
                    fg=theme.color('on_surface'),
                    bg=theme.color('surface'),
                    selectcolor=theme.color('surface'),
                    activebackground=theme.color('surface_container_high'),
                    activeforeground=theme.color('primary'),
                    highlightthickness=0,
                    cursor='hand2',
                    command=lambda dn=dns_name: self.on_dns_selected(dn)
                )
                check.grid(row=0, column=0, sticky=tk.W)

                # Подпись с адресами
                if dns_name in self.dns_servers and self.dns_servers[dns_name]:
                    # Разбиваем DNS адреса на строки для красивого отображения
                    dns_values = self.dns_servers[dns_name].split()
                    if len(dns_values) == 2:
                        # Один адрес - отображаем красиво
                        addr_text = f"{dns_values[0]:<15}"
                    else:
                        # Один или более адресов
                        addr_text = self.dns_servers[dns_name]

                    addr_label = tk.Label(
                        check_frame,
                        text=addr_text,
                        font=theme.font('body_small', mono=True),  # monospace для равного отступа
                        fg=theme.color('on_surface'),
                        bg=theme.color('surface'),
                        anchor=tk.W
                    )
                    addr_label.grid(row=0, column=1, sticky=tk.W, padx=(20, 0))

        return group_frame

    def create_window(self):
        """Создает окно настроек DNS"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Настройки DNS")
        self.window.configure(bg=theme.color('surface'))
        # Снимаем глобальную привязку колеса при закрытии окна
        self.window.bind("<Destroy>", lambda _e: self._unbind_wheel(), add="+")

        # Основной фрейм
        main_frame = tk.Frame(self.window, bg=theme.color('surface'))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas для прокрутки
        canvas = tk.Canvas(main_frame, bg=theme.color('surface'), highlightthickness=0)
        scrollable_frame = tk.Frame(canvas, bg=theme.color('surface'))

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        _canvas_inner_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_canvas_configure(event):
            cw = int(event.width)
            if cw > 0:
                canvas.itemconfig(_canvas_inner_id, width=cw)

        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Привязываем колесико мыши
        def on_mouse_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mouse_wheel)
        scrollable_frame.bind("<MouseWheel>", on_mouse_wheel)

        # Внутренний фрейм с отступами
        inner_frame = tk.Frame(scrollable_frame, bg=theme.color('surface'), padx=20, pady=20)
        inner_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(
            inner_frame,
            text="Настройки DNS",
            font=theme.font('title_large'),
            fg=theme.color('on_surface'),
            bg=theme.color('surface')
        )
        title_label.pack(anchor=tk.CENTER, pady=(0, 15))

        # Информация о текущем подключении
        self.find_active_wifi()
        conn_info = f"Текущее подключение: {self.active_connection if self.active_connection else 'Не найдено'}"

        conn_label = tk.Label(
            inner_frame,
            text=conn_info,
            font=theme.font('body_small'),
            fg=theme.color('on_surface_variant'),
            bg=theme.color('surface')
        )
        conn_label.pack(anchor=tk.W)

        # ========== ГРУППЫ DNS ==========

        # Автоматический
        self.create_dns_group(inner_frame, "Автоматический", ["Автоматический"])

        # Популярные
        self.create_dns_group(inner_frame, "Популярные",
                            ["Cloudflare", "Google", "Dns.SB"])

        # Безопасные
        self.create_dns_group(inner_frame, "Безопасные",
                            ["Quad9", "AdGuard"])

        # Для работы с ИИ
        self.create_dns_group(inner_frame, "Для работы с ИИ",
                            ["Xbox DNS", "GeoHide DNS", "DNS Mafioznik.xyz", "Comss DNS"])

        # Пользовательский DNS
        custom_group = tk.Frame(inner_frame, bg=theme.color('surface'))
        custom_group.pack(fill=tk.X, pady=(8, 0))

        custom_title = tk.Label(
            custom_group,
            text="Пользовательский DNS",
            font=theme.font('title_small'),
            fg=theme.color('primary'),
            bg=theme.color('surface')
        )
        custom_title.pack(anchor=tk.W, pady=(0, 0))

        # Фрейм для полей ввода
        input_frame = tk.Frame(custom_group, bg=theme.color('surface'))
        input_frame.pack(fill=tk.X)

        # Основной DNS
        primary_frame = tk.Frame(input_frame, bg=theme.color('surface'))
        primary_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        primary_label = tk.Label(
            primary_frame,
            text="Основной:",
            font=theme.font('body_small'),
            fg=theme.color('on_surface'),
            bg=theme.color('surface')
        )
        primary_label.pack(anchor=tk.W, pady=(0, 5))

        self.custom_primary_var = tk.StringVar()
        self.primary_entry = tk.Entry(
            primary_frame,
            textvariable=self.custom_primary_var,
            font=theme.font('body_small'),
            bg=theme.color('surface_container_lowest'),
            fg=theme.color('on_surface_variant'),  # Серый цвет по умолчанию для примера
            insertbackground=theme.color('primary'),
            highlightthickness=0,
            width=20
        )
        self.primary_entry.pack(fill=tk.X)

        # Функции для обработки примеров
        def setup_entry_with_example(entry, var, example_text):
            """Настраивает поле ввода с примером"""
            var.set(example_text)

            def on_focus_in(event):
                current_text = var.get()
                if current_text == example_text:
                    entry.delete(0, tk.END)
                    entry.config(fg=theme.color('on_surface'))

            def on_focus_out(event):
                current_text = var.get().strip()
                if not current_text:
                    var.set(example_text)
                    entry.config(fg=theme.color('on_surface_variant'))

            entry.bind('<FocusIn>', on_focus_in)
            entry.bind('<FocusOut>', on_focus_out)

        # Настраиваем поле основного DNS с примером
        setup_entry_with_example(self.primary_entry, self.custom_primary_var, "Пример: 8.8.8.8")

        # Дополнительный DNS
        secondary_frame = tk.Frame(input_frame, bg=theme.color('surface'))
        secondary_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        secondary_label = tk.Label(
            secondary_frame,
            text="Дополнительный:",
            font=theme.font('body_small'),
            fg=theme.color('on_surface'),
            bg=theme.color('surface')
        )
        secondary_label.pack(anchor=tk.W, pady=(0, 5))

        self.custom_secondary_var = tk.StringVar()
        self.secondary_entry = tk.Entry(
            secondary_frame,
            textvariable=self.custom_secondary_var,
            font=theme.font('body_small'),
            bg=theme.color('surface_container_lowest'),
            fg=theme.color('on_surface_variant'),  # Серый цвет по умолчанию для примера
            insertbackground=theme.color('primary'),
            highlightthickness=0,
            width=20
        )
        self.secondary_entry.pack(fill=tk.X)

        # Настраиваем поле дополнительного DNS с примером
        setup_entry_with_example(self.secondary_entry, self.custom_secondary_var, "Пример: 8.8.4.4")

        # ========== КНОПКИ ==========
        buttons_frame = tk.Frame(inner_frame, bg=theme.color('surface'))
        buttons_frame.pack(fill=tk.X, pady=(20, 0))

        buttons_center_frame = tk.Frame(buttons_frame, bg=theme.color('surface'))
        buttons_center_frame.pack()


        # Стиль кнопок
        button_style = {
            'font': theme.font('label_large'),
            'bg': theme.color('secondary_container'),
            'fg': theme.color('on_surface'),
            'bd': 0,
            'padx': 20,
            'pady': 8,
            'width': 12,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопка "Применить"
        apply_btn = self.create_hover_button(
            buttons_center_frame,
            text="Применить",
            command=self.apply_dns_settings,
            **button_style
        )
        apply_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Кнопка "Назад"
        back_btn = self.create_hover_button(
            buttons_center_frame,
            text="Назад",
            command=self.window.destroy,
            **button_style
        )
        back_btn.pack(side=tk.LEFT)

        # Загружаем текущие настройки DNS
        self.load_current_settings()

        # У Toplevel с Canvas winfo_reqheight() окна занижен (канва не «тянет» высоту контента),
        # fit_toplevel_to_content даёт низкое окно (~400 px). Размер клиентской области считаем
        # по scrollable_frame — как у service_unlock с fixed_content_size в dpi_utils.
        min_w, min_h = 340, 400
        margin_w, margin_h = 8, 12
        try:
            self.window.update_idletasks()
        except tk.TclError:
            pass
        try:
            measure_w = max(min_w, int(scrollable_frame.winfo_reqwidth()))
            canvas.itemconfig(_canvas_inner_id, width=measure_w)
            self.window.update_idletasks()
            iw = int(scrollable_frame.winfo_reqwidth())
            ih = int(scrollable_frame.winfo_reqheight())
        except tk.TclError:
            iw, ih = min_w, min_h
        sw = max(1, int(self.window.winfo_screenwidth()))
        sh = max(1, int(self.window.winfo_screenheight()))
        cw = max(min_w, iw)
        fw = min(sw, max(min_w, cw + margin_w))
        fh = min(sh, max(min_h, ih + margin_h))
        try:
            self.window.minsize(min_w, min_h)
            self.window.resizable(True, True)
        except tk.TclError:
            pass
        place_toplevel_centered_on_parent(
            self.window,
            self.parent,
            min_width=min_w,
            min_height=min_h,
            margin_width=margin_w,
            margin_height=margin_h,
            fixed_content_size=(fw, fh),
            immediate=True,
        )
        return self.window

    def set_entry_text_with_color(self, entry_widget, text_var, text):
        """Устанавливает текст в поле ввода с правильным цветом"""
        if text == "Пример: 8.8.8.8" or text == "Пример: 8.8.4.4":
            text_var.set(text)
            entry_widget.config(fg=theme.color('on_surface_variant'))  # Серый для примера
        elif text:
            text_var.set(text)
            entry_widget.config(fg=theme.color('on_surface'))    # Белый для реальных данных
        else:
            # Если текст пустой, устанавливаем пример
            if text_var == self.custom_primary_var:
                default_example = "Пример: 8.8.8.8"
            else:
                default_example = "Пример: 8.8.4.4"

            text_var.set(default_example)
            entry_widget.config(fg=theme.color('on_surface_variant'))

    def get_current_dns_servers(self):
        """Получить текущие DNS серверы из resolvectl"""
        try:
            result = subprocess.run(
                ['resolvectl', 'status', self._resolve_device()],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                output = result.stdout
                print(f"Вывод resolvectl:\n{output}")

                # Ищем строку с DNS серверами
                for line in output.split('\n'):
                    line = line.strip()
                    if line.startswith('DNS Servers:'):
                        # Извлекаем DNS серверы
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            servers = parts[1].strip()
                            print(f"Найдены DNS серверы: '{servers}'")
                            return servers

            print("DNS серверы не найдены или resolvectl вернул ошибку")
            return ""  # Пустая строка, если DNS не найдены

        except Exception as e:
            print(f"Ошибка получения DNS: {e}")
            return ""

    def load_current_settings(self):
        """Загружает текущие настройки DNS и устанавливает соответствующий чекбокс"""
        try:
            # Получаем текущие DNS серверы
            current_dns = self.get_current_dns_servers().strip()

            print(f"Текущие DNS: '{current_dns}'")

            # Сначала очищаем все чекбоксы
            for dns_name, var in self.dns_vars.items():
                var.set(False)

            # Очищаем поля ввода, устанавливая примеры
            self.set_entry_text_with_color(self.primary_entry, self.custom_primary_var, "")
            self.set_entry_text_with_color(self.secondary_entry, self.custom_secondary_var, "")

            # Если есть DNS - ищем совпадение с пресетами
            if current_dns:
                for dns_name, dns_value in self.dns_servers.items():
                    if dns_name == "Автоматический":
                        continue  # Пропускаем "Автоматический"

                    if dns_value and current_dns == dns_value:
                        print(f"Найден пресет: {dns_name} = {dns_value}")
                        self.dns_vars[dns_name].set(True)
                        break
            else:
                # Если DNS пустые - оставляем все чекбоксы снятыми
                print("Нет DNS серверов")

        except Exception as e:
            print(f"Ошибка загрузки текущих настроек: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """Запускает окно настроек DNS"""
        self.create_window()
        wait_window_safely(self.window)
