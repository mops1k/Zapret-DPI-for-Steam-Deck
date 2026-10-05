import tkinter as tk

from core.dpi_utils import place_toplevel_centered_on_parent, safe_grab_set, wait_window_safely
from core.service_manager import ServiceManager
from core.strategy_data import STRATEGY_OPTIONS, load_strategy_names, save_strategy_names
from ui.components.material import ThinScrollbar, TopAppBar, filled_button, text_button
from ui.theme import theme

class CustomStrategyWindow:
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)

        # Используем данные из strategy_data.py
        self.strategy_options = STRATEGY_OPTIONS

        # Инициализируем переменные для радиокнопок
        self.strategy_vars = {}  # {category: StringVar}
        for category in self.strategy_options.keys():
            self.strategy_vars[category] = tk.StringVar(value="")  # По умолчанию ничего не выбрано

        # Инициализируем менеджер службы
        if ServiceManager:
            self.service_manager = ServiceManager()
        else:
            self.service_manager = None
            print("Предупреждение: ServiceManager не загружен")

        # Цвета статуса берём из текущей темы Material 3
        self.success_color = theme.color("success")
        self.warning_color = theme.color("warning")
        self.error_color = theme.color("error")
        self.default_status_color = theme.color("on_surface_variant")

        self.setup_window_properties()
        self.root.title("Сборка своей стратегии")
        self.setup_ui()
        self.load_saved_strategies()
        place_toplevel_centered_on_parent(
            self.root, self.parent, min_width=560, min_height=480, margin_width=8, margin_height=12
        )

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.configure(bg=theme.color("surface"))
        self.root.transient(self.parent)
        safe_grab_set(self.root)

    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = tk.Frame(self.root, bg=theme.color("surface"))
        main_frame.pack(fill=tk.BOTH, expand=True, padx=theme.space("lg"), pady=theme.space("lg"))

        self.app_bar = TopAppBar(
            main_frame,
            title="Сборка своей стратегии",
            subtitle="Выберите по одному варианту для каждой категории трафика",
            bg_role="surface",
        )
        self.app_bar.pack(fill=tk.X, pady=(0, theme.space("md")))

        content_frame = tk.Frame(main_frame, bg=theme.color("surface"))
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, theme.space("md")))

        # Левая колонка — категории трафика
        left_frame = tk.Frame(content_frame, bg=theme.color("surface_container_low"), width=theme.px(210))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, theme.space("md")))
        left_frame.pack_propagate(False)

        tk.Label(
            left_frame,
            text="Категории трафика:",
            anchor="w",
            **theme.text("label_large", bg_role="surface_container_low"),
        ).pack(fill=tk.X, padx=theme.space("sm"), pady=(theme.space("sm"), theme.space("xs")))

        categories_container = tk.Frame(left_frame, bg=theme.color("surface_container_low"))
        categories_container.pack(fill=tk.BOTH, expand=True, padx=theme.space("xs"), pady=(0, theme.space("sm")))

        self.categories_listbox = tk.Listbox(
            categories_container,
            bg=theme.color("surface_container_low"),
            fg=theme.color("on_surface"),
            selectbackground=theme.color("primary_container"),
            selectforeground=theme.color("on_primary_container"),
            font=theme.font("body_medium"),
            highlightthickness=0,
            borderwidth=0,
            relief=tk.FLAT,
            activestyle="none",
        )
        self.categories_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for category in self.strategy_options.keys():
            self.categories_listbox.insert(tk.END, category)

        self.categories_listbox.bind('<<ListboxSelect>>', self.on_category_select)

        # Правая колонка — варианты стратегий
        right_frame = tk.Frame(content_frame, bg=theme.color("surface"))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.category_title = tk.Label(
            right_frame,
            text="Выберите категорию",
            anchor="w",
            **theme.text("title_small"),
        )
        self.category_title.pack(fill=tk.X, pady=(0, theme.space("sm")))

        strategies_container = tk.Frame(right_frame, bg=theme.color("surface"))
        strategies_container.pack(fill=tk.BOTH, expand=True)

        strategies_scrollbar = ThinScrollbar(strategies_container, command=None)
        strategies_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.strategies_canvas = tk.Canvas(
            strategies_container,
            bg=theme.color("surface_container_low"),
            highlightthickness=0,
            borderwidth=0,
            yscrollcommand=strategies_scrollbar.set,
        )
        self.strategies_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        strategies_scrollbar._command = self.strategies_canvas.yview

        self.radiobuttons_frame = tk.Frame(self.strategies_canvas, bg=theme.color("surface_container_low"))
        self.canvas_window = self.strategies_canvas.create_window(
            (0, 0), window=self.radiobuttons_frame, anchor="nw"
        )

        self.strategies_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.strategies_canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.strategies_canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

        self.radiobuttons_frame.bind("<Configure>", self.on_frame_configure)
        self.strategies_canvas.bind("<Configure>", self.on_canvas_configure)

        self.radio_buttons = {}

        self.status_label = tk.Label(
            main_frame,
            text="",
            anchor="w",
            **theme.text("body_small", fg_role="on_surface_variant"),
        )
        self.status_label.pack(fill=tk.X, pady=(0, theme.space("sm")))

        buttons_frame = tk.Frame(main_frame, bg=theme.color("surface"))
        buttons_frame.pack(fill=tk.X)

        self.apply_button = filled_button(buttons_frame, "Применить", self.apply_strategies)
        self.apply_button.pack(side=tk.LEFT, padx=(0, theme.space("sm")))

        back_button = text_button(buttons_frame, "Назад", self.close_window)
        back_button.pack(side=tk.LEFT)

        if self.strategy_options:
            first_category = list(self.strategy_options.keys())[0]
            self.categories_listbox.selection_set(0)
            self.update_strategies_for_category(first_category)

        self.setup_radio_bindings()

    def on_canvas_configure(self, event):
        """Обновляет ширину фрейма при изменении размера canvas"""
        # Устанавливаем ширину фрейма равной ширине canvas
        self.strategies_canvas.itemconfig(self.canvas_window, width=event.width)

    def setup_radio_bindings(self):
        """Настраивает отслеживание изменений в радиокнопках"""
        for category, var in self.strategy_vars.items():
            var.trace_add('write', lambda *args, cat=category: self.on_strategy_change(cat))

    def on_strategy_change(self, category):
        """Обрабатывает изменение выбора стратегии в категории"""
        selected_strategy = self.strategy_vars[category].get()

        # Обновляем цвета всех радиокнопок в этой категории
        if category in self.strategy_options:
            for strategy_name in self.strategy_options[category].keys():
                radio_key = (category, strategy_name)
                if radio_key in self.radio_buttons:
                    radio_button = self.radio_buttons[radio_key]
                    # Устанавливаем цвет текста
                    if strategy_name == selected_strategy:
                        radio_button.config(fg=self.success_color)  # Зеленый для выбранного
                    else:
                        radio_button.config(fg=theme.color("on_surface"))

    def _on_mousewheel(self, event):
        """Обработка прокрутки колесом мыши (Windows/Mac)"""
        # Прокрутка вниз при положительном delta, вверх при отрицательном
        self.strategies_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        """Обработка прокрутки для Linux (Button-4/Button-5)"""
        if event.num == 4:
            # Button-4: прокрутка вверх
            self.strategies_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            # Button-5: прокрутка вниз
            self.strategies_canvas.yview_scroll(1, "units")

    def on_frame_configure(self, event):
        """Обновляет область прокрутки при изменении размера фрейма"""
        # Обновляем область прокрутки canvas
        self.strategies_canvas.configure(scrollregion=self.strategies_canvas.bbox("all"))

    def on_category_select(self, event):
        """Обрабатывает выбор категории из списка"""
        selection = self.categories_listbox.curselection()
        if selection:
            selected_category = self.categories_listbox.get(selection[0])
            self.update_strategies_for_category(selected_category)

    def update_strategies_for_category(self, category_name):
        """Обновляет радиокнопки для выбранной категории"""
        # Обновляем заголовок
        self.category_title.config(text=f"Стратегии для: {category_name}")

        # Очищаем предыдущие радиокнопки
        for widget in self.radiobuttons_frame.winfo_children():
            widget.destroy()

        # Очищаем словарь радиокнопок для этой категории
        keys_to_remove = [k for k in self.radio_buttons.keys() if k[0] == category_name]
        for key in keys_to_remove:
            del self.radio_buttons[key]

        strategies = self.strategy_options.get(category_name, {})

        if not strategies:
            # Если нет стратегий для этой категории
            no_strategies_label = tk.Label(
                self.radiobuttons_frame,
                text="Нет доступных стратегий для этой категории",
                **theme.text("body_medium", bg_role="surface_container_low", fg_role="on_surface_variant"),
            )
            no_strategies_label.pack(pady=theme.space("lg"))
            return

        # Создаем радиокнопки для каждого варианта стратегии
        for strategy_name in strategies.keys():
            # Фрейм для радиокнопки
            strategy_frame = tk.Frame(self.radiobuttons_frame, bg=theme.color("surface_container_low"))
            strategy_frame.pack(fill=tk.X, pady=theme.px(6), padx=theme.px(5))

            text_color = (
                self.success_color
                if self.strategy_vars[category_name].get() == strategy_name
                else theme.color("on_surface")
            )

            radiobutton = tk.Radiobutton(
                strategy_frame,
                text=strategy_name,
                variable=self.strategy_vars[category_name],
                value=strategy_name,
                bg=theme.color("surface_container_low"),
                fg=text_color,
                selectcolor=theme.color("primary"),
                activebackground=theme.color("surface_container_high"),
                activeforeground=theme.color("primary"),
                font=theme.font("body_medium"),
                anchor=tk.W,
                justify="left",
                highlightthickness=0,
                borderwidth=0,
                wraplength=theme.px(520),
                cursor='hand2'
            )
            radiobutton.pack(fill=tk.X, anchor=tk.W)

            # Сохраняем ссылку на радиокнопку
            self.radio_buttons[(category_name, strategy_name)] = radiobutton

            # Добавляем разделитель
            separator = tk.Frame(strategy_frame, height=1, bg=theme.color("outline_variant"))
            separator.pack(fill=tk.X, pady=(5, 0))

        # Обновляем прокрутку
        self.radiobuttons_frame.update_idletasks()
        self.strategies_canvas.configure(scrollregion=self.strategies_canvas.bbox("all"))

    def load_saved_strategies(self):
        """Загружает сохраненные стратегии из файла"""
        try:
            selected_strategies = load_strategy_names()

            # Устанавливаем выбранные стратегии в радиокнопки
            for category, strategy_name in selected_strategies.items():
                if category in self.strategy_vars:
                    self.strategy_vars[category].set(strategy_name)

        except Exception as e:
            print(f"Ошибка загрузки сохраненных стратегий: {e}")

    def ensure_sudo_password(self):
        """Проверяет доступность sudo -A: пароль вводит системный askpass."""
        if not self.service_manager:
            return False

        from core.sudo_helper import sudo_available

        if not sudo_available():
            self.status_label.config(
                text="sudo или askpass-хелпер недоступны", fg=self.error_color
            )
            return False
        return True

    def restart_service(self):
        """Перезапускает службу zapret"""
        if not self.service_manager:
            return False, "Менеджер службы не инициализирован"

        success, message = self.service_manager.restart_service()
        return success, message

    def apply_strategies(self):
        """Применяет выбранные стратегии, сохраняет их и перезапускает службу"""
        try:
            # Собираем все выбранные стратегии
            selected_strategies = {}
            has_any_selection = False
            has_valid_strategy = False

            for category, var in self.strategy_vars.items():
                if var.get():  # Если что-то выбрано
                    has_any_selection = True
                    selected_strategies[category] = var.get()
                    if var.get() != "Не выбирать":
                        has_valid_strategy = True

            # Проверяем, выбраны ли стратегии
            if not has_any_selection:
                self.status_label.config(text="Не выбрано ни одной стратегии", fg=self.warning_color)
                # Сброс состояния через 2 секунды
                self.root.after(2000, lambda: self.status_label.config(text="", fg=self.default_status_color))
                return

            # Меняем состояние UI
            self.root.config(cursor="watch")
            self.apply_button.config(state="disabled", text="Применение...")
            self.status_label.config(text="Сохранение стратегий...")
            self.root.update()

            # Сохраняем наименования в файл и команды в config.txt
            if not save_strategy_names(selected_strategies):
                self.status_label.config(text="Ошибка сохранения стратегий", fg=self.error_color)
                self.reset_ui_state()
                return

            print(f"Сохранено {len(selected_strategies)} стратегий")

            # Проверяем, есть ли хотя бы одна валидная стратегия (не "Не выбирать")
            if has_valid_strategy:
                # Проверяем возможность перезапуска службы
                if not self.service_manager:
                    self.status_label.config(
                        text="Стратегии сохранены. Перезапустите службу вручную",
                        fg=self.warning_color
                    )
                    # Сброс состояния через 3 секунды
                    self.root.after(3000, self.reset_ui_state)
                    return

                # Запрашиваем пароль sudo для перезапуска службы
                self.status_label.config(text="Запрос прав администратора...")
                self.root.update()

                if not self.ensure_sudo_password():
                    self.status_label.config(
                        text="Стратегии сохранены. Перезапустите службу вручную",
                        fg=self.warning_color
                    )
                    # Сброс состояния через 3 секунды
                    self.root.after(3000, self.reset_ui_state)
                    return

                # Перезапускаем службу
                self.status_label.config(text="Перезапуск службы...")
                self.apply_button.config(text="Перезапуск...")
                self.root.update()

                success, message = self.restart_service()

                if success:
                    self.status_label.config(
                        text=f"Сохранено {len(selected_strategies)} стратегий, служба перезапущена",
                        fg=self.success_color
                    )
                    # Ждем немного и закрываем окно
                    self.root.after(1500, self.close_window)
                else:
                    self.status_label.config(
                        text=f"Сохранено {len(selected_strategies)} стратегий, но служба не перезапущена",
                        fg=self.warning_color
                    )
                    # Сброс состояния через 3 секунды
                    self.root.after(3000, self.reset_ui_state)
            else:
                # Если выбраны только "Не выбирать" - очищаем стратегии
                self.status_label.config(
                    text="Все стратегии очищены",
                    fg=self.success_color
                )
                # Ждем немного и закрываем окно
                self.root.after(1500, self.close_window)

        except Exception as e:
            self.status_label.config(text=f"Ошибка: {str(e)}", fg=self.error_color)
            print(f"Ошибка применения стратегий: {e}")
            # Сброс состояния через 3 секунды
            self.root.after(3000, self.reset_ui_state)

    def reset_ui_state(self):
        """Восстанавливает состояние UI"""
        self.root.config(cursor="")
        self.apply_button.config(state="normal", text="Применить")
        self.status_label.config(text="", fg=self.default_status_color)

    def close_window(self):
        """Закрывает окно"""
        # Отвязываем события прокрутки перед закрытием
        self.strategies_canvas.unbind_all("<MouseWheel>")
        self.strategies_canvas.unbind_all("<Button-4>")
        self.strategies_canvas.unbind_all("<Button-5>")
        self.root.destroy()

    def run(self):
        """Запускает окно"""
        wait_window_safely(self.root)
