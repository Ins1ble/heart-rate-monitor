"""
Кнопки управления и интерфейс
"""
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from typing import Callable, List, Dict, Optional
import tkinter as tk
from tkinter import ttk
import threading


class ControlButton:
    """Кнопка управления с настройками"""

    def __init__(self, ax, label, color, hover_color, callback):
        self.ax = ax
        self.label = label
        self.color = color
        self.hover_color = hover_color
        self.callback = callback
        self.button = None
        self._create_button()

    def _create_button(self):
        """Создание кнопки"""
        self.button = Button(self.ax, self.label,
                           color=self.color,
                           hovercolor=self.hover_color)
        self.button.on_clicked(self.callback)

    def update_color(self, new_color):
        """Обновление цвета кнопки"""
        self.color = new_color
        self.button.color = new_color
        if hasattr(self.button, 'ax'):
            plt.draw()

    def set_enabled(self, enabled: bool):
        """Включение/отключение кнопки"""
        self.button.active = enabled
        if enabled:
            self.button.color = self.color
        else:
            self.button.color = '#6e7681'

    def update_text(self, new_text: str):
        """Обновление текста кнопки"""
        self.button.label.set_text(new_text)
        plt.draw()


class PortSelectionDialog:
    """Диалоговое окно выбора порта"""

    def __init__(self, ports: List[Dict[str, str]], callback: Callable):
        self.ports = ports
        self.callback = callback
        self.selected_port = None
        self.dialog = None

        self._create_dialog()

    def _create_dialog(self):
        """Создание диалогового окна"""
        self.dialog = tk.Tk()
        self.dialog.title("Выбор COM порта")
        self.dialog.geometry("500x300")
        self.dialog.configure(bg='#f0f0f0')

        # Заголовок
        title_label = tk.Label(
            self.dialog,
            text="Выберите порт для подключения:",
            font=("Arial", 12, "bold"),
            bg='#f0f0f0',
            fg='#333333'
        )
        title_label.pack(pady=10)

        # Список портов
        frame = tk.Frame(self.dialog, bg='#f0f0f0')
        frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Заголовки колонок
        headers_frame = tk.Frame(frame, bg='#e0e0e0', height=30)
        headers_frame.pack(fill='x', pady=(0, 5))
        headers_frame.pack_propagate(False)

        tk.Label(
            headers_frame,
            text="Порт",
            font=("Arial", 10, "bold"),
            bg='#e0e0e0',
            fg='#333333',
            width=15
        ).pack(side='left', padx=5)

        tk.Label(
            headers_frame,
            text="Описание",
            font=("Arial", 10, "bold"),
            bg='#e0e0e0',
            fg='#333333',
            width=40
        ).pack(side='left', padx=5)

        # Список портов в прокручиваемой области
        listbox_frame = tk.Frame(frame, bg='white')
        listbox_frame.pack(fill='both', expand=True)

        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side='right', fill='y')

        self.port_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10),
            bg='white',
            fg='#333333',
            selectbackground='#3fb950',
            selectforeground='white',
            height=8
        )
        self.port_listbox.pack(side='left', fill='both', expand=True)

        scrollbar.config(command=self.port_listbox.yview)

        # Заполнение списка портов
        for port_info in self.ports:
            display_text = f"{port_info['port']:15} {port_info['description']}"
            self.port_listbox.insert(tk.END, display_text)

        if not self.ports:
            self.port_listbox.insert(tk.END, "Нет доступных портов")
            self.port_listbox.config(state='disabled')

        # Кнопки
        buttons_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        buttons_frame.pack(pady=10)

        tk.Button(
            buttons_frame,
            text="Подключиться",
            command=self._on_select,
            bg='#3fb950',
            fg='white',
            font=("Arial", 10, "bold"),
            padx=20,
            pady=5,
            activebackground='#2ea043',
            activeforeground='white'
        ).pack(side='left', padx=10)

        tk.Button(
            buttons_frame,
            text="Отмена",
            command=self._on_cancel,
            bg='#ff7b72',
            fg='white',
            font=("Arial", 10, "bold"),
            padx=20,
            pady=5,
            activebackground='#ff6b6b',
            activeforeground='white'
        ).pack(side='left', padx=10)

        # Обработка двойного клика
        self.port_listbox.bind('<Double-Button-1>', lambda e: self._on_select())

        # Центрирование окна
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

    def _on_select(self):
        """Обработка выбора порта"""
        if self.ports and self.port_listbox.curselection():
            selected_index = self.port_listbox.curselection()[0]
            if selected_index < len(self.ports):
                self.selected_port = self.ports[selected_index]
                if self.callback:
                    self.callback(self.selected_port)

        self.dialog.destroy()

    def _on_cancel(self):
        """Обработка отмены"""
        self.dialog.destroy()

    def show(self):
        """Показать диалоговое окно"""
        self.dialog.mainloop()


class ControlPanel:
    """Панель управления приложением"""

    def __init__(self, fig, window_rr_options: List[int] = None):
        self.fig = fig
        self.window_rr_options = window_rr_options or [20, 30, 50, 100]

        # Позиции кнопок
        self.button_positions = self._calculate_button_positions()

        # Создание кнопок
        self.buttons = {}
        self._create_buttons()

        # Текущая конфигурация
        self.current_window_rr = 30
        self.available_ports = []

    def _calculate_button_positions(self):
        """Расчет позиций кнопок"""
        return {
            'scan_ports': [0.08, 0.95, 0.15, 0.035],  # Новая кнопка сканирования
            'start': [0.25, 0.95, 0.12, 0.035],
            'pause': [0.39, 0.95, 0.10, 0.035],
            'stop': [0.51, 0.95, 0.08, 0.035],
            'menu': [0.61, 0.95, 0.08, 0.035],
            'connect': [0.85, 0.95, 0.12, 0.035],
            # Кнопки выбора окна ВСР
            '20rr': [0.71, 0.95, 0.04, 0.035],
            '30rr': [0.76, 0.95, 0.04, 0.035],
            '50rr': [0.81, 0.95, 0.04, 0.035],
            '100rr': [0.86, 0.95, 0.04, 0.035],
        }

    def _create_buttons(self):
        """Создание всех кнопок"""
        # Кнопка сканирования портов
        self.buttons['scan_ports'] = ControlButton(
            plt.axes(self.button_positions['scan_ports']),
            '🔍 Сканировать порты',
            '#58a6ff',
            '#2ea043',
            self._on_scan_ports_clicked
        )

        # Основные кнопки управления
        self.buttons['start'] = ControlButton(
            plt.axes(self.button_positions['start']),
            '▶ Начать запись',
            '#3fb950',
            '#2ea043',
            self._on_start_clicked
        )

        self.buttons['pause'] = ControlButton(
            plt.axes(self.button_positions['pause']),
            '⏸ Пауза',
            '#6e7681',
            '#8b949e',
            self._on_pause_clicked
        )

        self.buttons['stop'] = ControlButton(
            plt.axes(self.button_positions['stop']),
            '⏹ Стоп',
            '#6e7681',
            '#8b949e',
            self._on_stop_clicked
        )

        self.buttons['menu'] = ControlButton(
            plt.axes(self.button_positions['menu']),
            '⋮ Графики',
            '#6e7681',
            '#8b949e',
            self._on_menu_clicked
        )

        # Кнопки выбора окна ВСР
        self.buttons['20rr'] = ControlButton(
            plt.axes(self.button_positions['20rr']),
            '20RR',
            '#6e7681',
            '#8b949e',
            lambda event: self._on_window_clicked(20)
        )

        self.buttons['30rr'] = ControlButton(
            plt.axes(self.button_positions['30rr']),
            '30RR',
            '#3fb950',
            '#2ea043',
            lambda event: self._on_window_clicked(30)
        )

        self.buttons['50rr'] = ControlButton(
            plt.axes(self.button_positions['50rr']),
            '50RR',
            '#6e7681',
            '#8b949e',
            lambda event: self._on_window_clicked(50)
        )

        self.buttons['100rr'] = ControlButton(
            plt.axes(self.button_positions['100rr']),
            '100RR',
            '#6e7681',
            '#8b949e',
            lambda event: self._on_window_clicked(100)
        )

        # Кнопка подключения
        self.buttons['connect'] = ControlButton(
            plt.axes(self.button_positions['connect']),
            '🔌 Подключить',
            '#ff7b72',
            '#ff6b6b',
            self._on_connect_clicked
        )

        # Callbacks (будут установлены извне)
        self.start_callback = None
        self.pause_callback = None
        self.stop_callback = None
        self.menu_callback = None
        self.connect_callback = None
        self.window_callback = None
        self.scan_ports_callback = None
        self.port_select_callback = None

    def _on_scan_ports_clicked(self, event):
        """Обработка нажатия кнопки 'Сканировать порты'"""
        if self.scan_ports_callback:
            self.scan_ports_callback(event)

    def _on_start_clicked(self, event):
        """Обработка нажатия кнопки 'Начать запись'"""
        if self.start_callback:
            self.start_callback(event)

    def _on_pause_clicked(self, event):
        """Обработка нажатия кнопки 'Пауза'"""
        if self.pause_callback:
            self.pause_callback(event)

    def _on_stop_clicked(self, event):
        """Обработка нажатия кнопки 'Стоп'"""
        if self.stop_callback:
            self.stop_callback(event)

    def _on_menu_clicked(self, event):
        """Обработка нажатия кнопки 'Графики'"""
        if self.menu_callback:
            self.menu_callback(event)

    def _on_connect_clicked(self, event):
        """Обработка нажатия кнопки 'Подключить'"""
        if self.connect_callback:
            self.connect_callback(event)

    def _on_window_clicked(self, window_size: int):
        """Обработка нажатия кнопки выбора окна ВСР"""
        self.current_window_rr = window_size
        self._update_window_buttons()

        if self.window_callback:
            self.window_callback(window_size)

    def show_port_selection_dialog(self, ports: List[Dict[str, str]]):
        """Показать диалоговое окно выбора порта"""
        self.available_ports = ports

        # Запускаем в отдельном потоке, чтобы не блокировать основной
        def show_dialog():
            dialog = PortSelectionDialog(ports, self._on_port_selected)
            dialog.show()

        thread = threading.Thread(target=show_dialog)
        thread.daemon = True
        thread.start()

    def _on_port_selected(self, port_info: Dict[str, str]):
        """Обработка выбора порта"""
        if self.port_select_callback:
            self.port_select_callback(port_info)

    def _update_window_buttons(self):
        """Обновление цветов кнопок выбора окна ВСР"""
        for size in self.window_rr_options:
            btn_name = f'{size}rr'
            if btn_name in self.buttons:
                if size == self.current_window_rr:
                    self.buttons[btn_name].update_color('#3fb950')
                else:
                    self.buttons[btn_name].update_color('#6e7681')

        plt.draw()

    def update_button_states(self, recording_state: str):
        """
        Обновление состояний кнопок в зависимости от состояния записи

        Args:
            recording_state: Состояние записи ('IDLE', 'RECORDING', 'PAUSED', 'STOPPED')
        """
        colors = {
            'IDLE': {
                'scan_ports': '#58a6ff',
                'start': '#3fb950',
                'pause': '#6e7681',
                'stop': '#6e7681',
                'connect': '#ff7b72'
            },
            'RECORDING': {
                'scan_ports': '#58a6ff',
                'start': '#ff7b72',
                'pause': '#ffa657',
                'stop': '#3fb950',
                'connect': '#6e7681'
            },
            'PAUSED': {
                'scan_ports': '#58a6ff',
                'start': '#ff7b72',
                'pause': '#3fb950',
                'stop': '#3fb950',
                'connect': '#6e7681'
            },
            'STOPPED': {
                'scan_ports': '#58a6ff',
                'start': '#3fb950',
                'pause': '#6e7681',
                'stop': '#ff7b72',
                'connect': '#ff7b72'
            }
        }

        state_colors = colors.get(recording_state, colors['IDLE'])

        for btn_name, color in state_colors.items():
            if btn_name in self.buttons:
                self.buttons[btn_name].update_color(color)

        # Обновление текста кнопки паузы
        if recording_state == 'PAUSED':
            self.buttons['pause'].update_text('▶ Продолжить')
        else:
            self.buttons['pause'].update_text('⏸ Пауза')

        plt.draw()

    def update_connect_button(self, is_connected: bool, port_name: str = None):
        """Обновление кнопки подключения"""
        if is_connected and port_name:
            self.buttons['connect'].update_text(f'🔌 Откл. {port_name}')
            self.buttons['connect'].update_color('#3fb950')
        else:
            self.buttons['connect'].update_text('🔌 Подключить')
            self.buttons['connect'].update_color('#ff7b72')

        plt.draw()