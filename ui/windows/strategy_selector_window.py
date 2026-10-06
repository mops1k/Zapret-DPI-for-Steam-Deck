"""Окна выбора стратегий (Material 3).

Три окна: автоподбор, выбор стратегий для теста и меню «Сменить стратегию».
Проект «Zapret DPI Manager» © Aleksandr Kvintilyanov.
"""
import os
import tkinter as tk

from core.dpi_utils import place_toplevel_centered_on_parent, safe_grab_set, wait_window_safely
from core.strategy_data import natural_sort_key
from ui.components.custom_messagebox import show_error
from ui.components.material import (
    MaterialButton,
    MaterialCheckbox,
    MaterialDivider,
    TopAppBar,
    filled_button,
    text_button,
)
from ui.theme import theme
from ui.windows.strategy_window import StrategyWindow
from ui.windows.custom_strategy_window import CustomStrategyWindow
from ui.windows.bbdpi_strategy_window import BBDpiStrategyWindow
from ui.windows.strategy_tester_window import StrategyTesterWindow


class AutoSelectionWindow:
    """Окно автоподбора стратегий"""

    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()
        self.root.title("Автоподбор стратегий")

        self.setup_ui()
        place_toplevel_centered_on_parent(
            self.root, self.parent, min_width=220, min_height=200, margin_width=8, margin_height=12
        )

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.configure(bg=theme.color("surface"))
        self.root.transient(self.parent)
        safe_grab_set(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.go_back)

    def setup_ui(self):
        """Настройка интерфейса"""
        t = theme
        main_frame = tk.Frame(self.root, bg=t.color("surface"))
        main_frame.pack(fill=tk.BOTH, expand=True, padx=t.space("lg"), pady=t.space("lg"))

        self.app_bar = TopAppBar(
            main_frame,
            title="Автоподбор стратегий",
            subtitle="Перебор всех или выбранных стратегий",
            bg_role="surface",
        )
        self.app_bar.pack(fill=tk.X, pady=(0, t.space("md")))

        all_button = filled_button(main_frame, "Тестировать все стратегии", self.test_all_strategies)
        all_button.pack(fill=tk.X, pady=(0, t.space("sm")))

        select_button = MaterialButton(
            main_frame,
            text="Выбрать стратегии для теста",
            command=self.show_strategy_selection,
            variant="tonal",
        )
        select_button.pack(fill=tk.X, pady=(0, t.space("sm")))

        back_button = text_button(main_frame, "Назад", self.go_back)
        back_button.pack(fill=tk.X)

    def test_all_strategies(self):
        """Запускает тестирование всех стратегий"""
        self.on_close()
        try:
            tester_window = StrategyTesterWindow(self.parent)
            tester_window.run()
        except Exception as e:
            print(f"Ошибка открытия тестировщика: {e}")
            show_error(self.root, "Ошибка", f"Не удалось открыть тестировщика: {str(e)}")

    def show_strategy_selection(self):
        """Показывает отдельное окно выбора стратегий"""
        self.on_close()
        selection_window = StrategySelectionWindow(self.parent)
        selection_window.run()

    def on_close(self):
        """Закрывает окно"""
        self.root.destroy()

    def go_back(self):
        """Возвращает к окну «Сменить стратегию»"""
        self.on_close()
        StrategySelectorWindow(self.parent).run()

    def run(self):
        """Запускает окно"""
        wait_window_safely(self.root)


class StrategySelectionWindow:
    """Окно выбора стратегий для тестирования"""

    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()

        self.selected_strategies = []
        self.strategy_vars = {}
        self.strategy_items = []

        self.setup_ui()
        self.load_strategies()
        place_toplevel_centered_on_parent(
            self.root, self.parent, min_width=640, min_height=300, margin_width=8, margin_height=12
        )

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.title("Выбор стратегий для тестирования")
        self.root.configure(bg=theme.color("surface"))
        self.root.transient(self.parent)
        safe_grab_set(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.go_back)

    def setup_ui(self):
        """Настройка интерфейса"""
        t = theme
        main_frame = tk.Frame(self.root, bg=theme.color("surface"))
        main_frame.pack(fill=tk.BOTH, expand=True, padx=theme.space("lg"), pady=theme.space("lg"))

        self.app_bar = TopAppBar(
            main_frame,
            title="Выберите стратегии для тестирования",
            subtitle="Пустой выбор — тестировать все стратегии",
            bg_role="surface",
        )
        self.app_bar.pack(fill=tk.X, pady=(0, t.space("md")))

        list_frame = tk.Frame(main_frame, bg=t.color("surface_container_low"))
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, t.space("md")))

        columns_container = tk.Frame(list_frame, bg=t.color("surface_container_low"))
        columns_container.pack(fill=tk.BOTH, expand=True, padx=t.space("sm"), pady=t.space("sm"))

        self.column_frames = []
        for i in range(3):
            column_frame = tk.Frame(columns_container, bg=t.color("surface_container_low"))
            column_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=t.space("sm"))
            self.column_frames.append(column_frame)

            if i < 2:
                separator = tk.Frame(columns_container, width=1, bg=t.color("outline_variant"))
                separator.pack(side=tk.LEFT, fill=tk.Y, padx=t.space("xs"))

        control_frame = tk.Frame(main_frame, bg=t.color("surface"))
        control_frame.pack(fill=tk.X)

        self.status_label = tk.Label(
            control_frame,
            text="Выберите стратегии для тестирования",
            anchor="w",
            **theme.text("body_small", fg_role="on_surface_variant"),
        )
        self.status_label.pack(fill=tk.X, pady=(0, t.space("sm")))

        buttons_frame = tk.Frame(control_frame, bg=t.color("surface"))
        buttons_frame.pack(fill=tk.X)

        apply_button = filled_button(buttons_frame, "Запустить подбор", self.apply_selection)
        apply_button.pack(side=tk.LEFT, padx=(0, t.space("sm")))

        back_button = text_button(buttons_frame, "Назад", self.go_back)
        back_button.pack(side=tk.LEFT)

    def load_strategies(self):
        """Загружает список стратегий из папки"""
        t = theme
        try:
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager/files")
            strategy_dir = os.path.join(manager_dir, "strategy")

            if not os.path.exists(strategy_dir):
                os.makedirs(strategy_dir)
                print(f"Создана папка для стратегий: {strategy_dir}")

            if os.path.exists(strategy_dir):
                strategy_files = [
                    f for f in os.listdir(strategy_dir)
                    if os.path.isfile(os.path.join(strategy_dir, f))
                ]

                sorted_files = []
                for file in sorted(strategy_files, key=natural_sort_key):
                    if not file.startswith('.'):
                        sorted_files.append(file)

                self.strategy_items = sorted_files

                if not self.strategy_items:
                    for column_frame in self.column_frames:
                        tk.Label(
                            column_frame,
                            text="Стратегии не найдены",
                            **theme.text("body_medium", bg_role="surface_container_low"),
                        ).pack(pady=t.space("lg"))
                else:
                    items_per_column = (len(self.strategy_items) + 2) // 3

                    for i, strategy in enumerate(self.strategy_items):
                        col_index = i // items_per_column
                        if col_index < 3:
                            column_frame = self.column_frames[col_index]

                            var = tk.BooleanVar(value=False)
                            self.strategy_vars[strategy] = var

                            checkbox = MaterialCheckbox(
                                column_frame,
                                strategy,
                                variable=var,
                                command=lambda _value: self.update_selection_status(),
                                bg_role="surface_container_low",
                                font=theme.font("body_medium"),
                            )
                            checkbox.pack(anchor='w', pady=theme.px(1))

                    print(f"Загружено {len(self.strategy_items)} стратегий")
                    self.update_selection_status()

        except Exception as e:
            print(f"Ошибка загрузки стратегий: {e}")
            tk.Label(
                self.column_frames[0],
                text=f"Ошибка: {str(e)}",
                **theme.text("body_medium", bg_role="surface_container_low", fg_role="error"),
            ).pack(pady=t.space("lg"))

    def update_selection_status(self):
        """Обновляет статусную строку выбора"""
        if self.strategy_vars:
            selected_count = sum(1 for var in self.strategy_vars.values() if var.get())

            if selected_count == 0:
                self.status_label.config(
                    text="Выберите стратегии для тестирования или оставьте все пустым для теста всех стратегий",
                    fg=theme.color("on_surface_variant"),
                )
            else:
                self.status_label.config(
                    text=f"Выбрано стратегий: {selected_count} из {len(self.strategy_items)}",
                    fg=theme.color("primary"),
                )

    def apply_selection(self):
        """Применяет выбранные стратегии и открывает тестировщик"""
        selected_strategies = []
        if self.strategy_vars:
            selected_strategies = [
                strategy for strategy, var in self.strategy_vars.items()
                if var.get()
            ]

        if not selected_strategies and self.strategy_items:
            selected_strategies = self.strategy_items.copy()
            print(f"Не выбрано конкретных стратегий. Будет протестировано все: {len(selected_strategies)} стратегий")
        else:
            print(f"Выбрано стратегий для тестирования: {len(selected_strategies)}")

        self.on_close()

        try:
            tester_window = StrategyTesterWindow(self.parent, strategies_to_test=selected_strategies)
            tester_window.run()
        except Exception as e:
            print(f"Ошибка открытия тестировщика: {e}")
            show_error(self.root, "Ошибка", f"Не удалось открыть тестировщик: {str(e)}")

    def on_close(self):
        """Закрывает окно"""
        self.root.destroy()

    def go_back(self):
        """Возвращает к окну «Автоподбор стратегий»"""
        self.on_close()
        AutoSelectionWindow(self.parent).run()

    def run(self):
        """Запускает окно"""
        wait_window_safely(self.root)


class StrategySelectorWindow:
    """Меню «Сменить стратегию»"""

    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()
        self.root.title("Выбор типа стратегии")

        self.setup_ui()
        place_toplevel_centered_on_parent(
            self.root, self.parent, min_width=240, min_height=260, margin_width=8, margin_height=12
        )

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.configure(bg=theme.color("surface"))
        self.root.transient(self.parent)
        safe_grab_set(self.root)

    def setup_ui(self):
        """Настройка интерфейса"""
        t = theme
        main_frame = tk.Frame(self.root, bg=t.color("surface"))
        main_frame.pack(fill=tk.BOTH, expand=True, padx=t.space("lg"), pady=t.space("lg"))

        self.app_bar = TopAppBar(
            main_frame,
            title="Сменить стратегию",
            subtitle="Автоподбор, готовая стратегия, свой пресет или строка BB DPI",
            bg_role="surface",
        )
        self.app_bar.pack(fill=tk.X, pady=(0, t.space("md")))

        test_button = filled_button(main_frame, "Автоподбор стратегии", self.show_autoselect_menu)
        test_button.pack(fill=tk.X, pady=(0, t.space("sm")))

        ready_button = MaterialButton(
            main_frame,
            text="Выбрать готовую стратегию",
            command=self.open_ready_strategies,
            variant="tonal",
        )
        ready_button.pack(fill=tk.X, pady=(0, t.space("sm")))

        custom_button = MaterialButton(
            main_frame,
            text="Собрать свой пресет",
            command=self.open_custom_strategy,
            variant="outlined",
        )
        custom_button.pack(fill=tk.X, pady=(0, t.space("sm")))

        bbdpi_button = MaterialButton(
            main_frame,
            text="Стратегия из BB DPI",
            command=self.open_bbdpi_strategy,
            variant="outlined",
        )
        bbdpi_button.pack(fill=tk.X, pady=(0, t.space("sm")))

        MaterialDivider(main_frame).pack(fill=tk.X, pady=t.space("sm"))

        back_button = text_button(main_frame, "Назад", self.close_window)
        back_button.pack(fill=tk.X)

    def show_autoselect_menu(self):
        """Показывает отдельное окно автоподбора"""
        self.close_window()
        autoselect_window = AutoSelectionWindow(self.parent)
        autoselect_window.run()

    def open_ready_strategies(self):
        """Открывает окно готовых стратегий"""
        self.close_window()
        strategy_window = StrategyWindow(self.parent)
        strategy_window.run()

    def open_custom_strategy(self):
        """Открывает окно сборки своей стратегии"""
        self.close_window()
        custom_window = CustomStrategyWindow(self.parent)
        custom_window.run()

    def open_bbdpi_strategy(self):
        """Открывает окно конвертации строки стратегии BB DPI"""
        self.close_window()
        bbdpi_window = BBDpiStrategyWindow(self.parent)
        bbdpi_window.run()

    def close_window(self):
        """Закрывает окно"""
        self.root.destroy()

    def run(self):
        """Запускает окно"""
        wait_window_safely(self.root)
