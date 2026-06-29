"""Главное окно приложения"""
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import numpy as np
import time
import traceback
from typing import Dict

from config import AppConfig, HRVConfig
from models.recording import RecordingManager
from models.serial_reader import SerialReader, SerialConfig, SerialPortScanner
from analysis.rr_filter import RRFiltration
from analysis.hrv_analysis import HRVAnalyzer
from analysis.signal_processing import SignalProcessor
from ui.controls import ControlPanel
from ui.visualization import Visualization
from ui.extra_graphs import ExtraGraphsWindow


class HRVMonitor:
    """Основной класс монитора HRV"""

    def __init__(self, config: AppConfig, hrv_config: HRVConfig):
        self.config = config
        self.hrv_config = hrv_config

        # Менеджеры
        self.recording_manager = RecordingManager()
        self.rr_filter = RRFiltration()
        self.serial_reader = SerialReader(
            SerialConfig(port=config.port, baud_rate=config.baud_rate, timeout=0.01)
        )
        self.hrv_analyzer = HRVAnalyzer()
        self.signal_processor = SignalProcessor()

        # Данные
        self.signal_data = deque([512] * config.max_points, maxlen=config.max_points)
        self.rr_intervals = deque(maxlen=300)
        self.rr_timestamps = deque(maxlen=300)
        self.rr_valid_flags = deque(maxlen=300)
        self.hrv_data = deque(maxlen=80)

        # Текущие показатели
        self.current_bpm = 0
        self.current_rr = 0
        self.sdnn_value = 0
        self.stress_index = 0
        self.lf_hf_ratio = 1.0  # Начинаем с нейтрального значения
        self.rmssd_value = 0
        self.mean_rr = 0
        self.rr_range = 0
        self.rr_count = 0

        # Временные метки для оптимизации
        self.last_stress_calc_time = 0
        self.last_spectrum_calc_time = 0
        self.last_data_time = 0
        self.frame_count = 0

        # Тестовые данные
        self.test_counter = 0
        self.use_test_data = True  # По умолчанию тестовый режим

        # Инициализация UI
        self.visualization = Visualization(self.hrv_config)
        self.control_panel = ControlPanel(self.visualization.fig)
        self.extra_window = ExtraGraphsWindow(self.hrv_config)

        # Настройка callbacks
        self._setup_callbacks()

        # Настройка анимации
        self.animation = FuncAnimation(
            self.visualization.fig,
            self.update,
            interval=config.update_interval,
            cache_frame_data=False,
            blit=False
        )

        # Настройка layout
        self.visualization.adjust_layout()

        # Счетчики
        self.fps_counter = 0
        self.fps_time = time.time()
        self.data_count = 0

        print("📱 Инициализация HRVMonitor завершена")
        print("📡 Используется тестовый режим. Нажмите 'Сканировать порты' для подключения к датчику.")

    def _setup_callbacks(self):
        """Настройка callback-функций для кнопок"""
        self.control_panel.start_callback = self._on_start_recording
        self.control_panel.pause_callback = self._on_pause_recording
        self.control_panel.stop_callback = self._on_stop_recording
        self.control_panel.menu_callback = self._on_show_extra_graphs
        self.control_panel.connect_callback = self._on_connect_port
        self.control_panel.window_callback = self._on_window_size_changed
        self.control_panel.scan_ports_callback = self._on_scan_ports
        self.control_panel.port_select_callback = self._on_port_selected

    def _on_start_recording(self, event):
        """Обработка начала записи"""
        if self.serial_reader.is_connected or self.use_test_data:
            if self.recording_manager.start_recording():
                self.control_panel.update_button_states('RECORDING')
                self.visualization.update_state_text('RECORDING', '#3fb950')
                print("🎥 Начата запись данных")
        else:
            self.visualization.update_status_text('🔴 Сначала подключите датчик!', '#ff7b72')
            print("⚠️ Нельзя начать запись: порт не подключен")

    def _on_pause_recording(self, event):
        """Обработка паузы/продолжения записи"""
        if self.recording_manager.pause_recording():
            state = self.recording_manager.state.value
            self.control_panel.update_button_states(state)
            color = '#ffa657' if state == 'PAUSED' else '#3fb950'
            self.visualization.update_state_text(state, color)
            print(f"⏸ Состояние записи: {state}")

    def _on_stop_recording(self, event):
        """Обработка остановки записи"""
        if self.recording_manager.stop_recording():
            self.control_panel.update_button_states('STOPPED')
            self.visualization.update_state_text('STOPPED', '#ff7b72')
            print("⏹ Запись остановлена")

            # Пост-анализ автоматически откроется через RecordingManager.show_post_analysis()

    def _on_show_extra_graphs(self, event):
        """Показать дополнительные графики"""
        self.extra_window.open(
            list(self.rr_intervals),
            list(self.rr_timestamps),
            self.rr_filter.get_artifacts_in_window(50)
        )

    def _on_scan_ports(self, event):
        """Сканирование доступных портов"""
        print("🔍 Сканирование портов...")
        ports = self.serial_reader.scan_ports()

        if ports:
            self.control_panel.show_port_selection_dialog(ports)
        else:
            self.visualization.update_status_text('⚠️ Нет доступных портов', '#ffa657')
            print("⚠️ Не найдено доступных COM портов")

    def _on_port_selected(self, port_info: Dict[str, str]):
        """Обработка выбора порта"""
        print(f"🎯 Выбран порт: {port_info['port']}")
        self.visualization.update_status_text(f'📡 Подключение к {port_info["port"]}...', '#58a6ff')

        # Попытка подключения к выбранному порту
        if self._connect_to_port(port_info['port']):
            self.control_panel.update_connect_button(True, port_info['port'])
        else:
            self.visualization.update_status_text('❌ Не удалось подключиться', '#ff7b72')

    def _connect_to_port(self, port_name: str) -> bool:
        """Подключение к указанному порту"""
        if self.serial_reader.connect(port_name):
            self.use_test_data = False
            self.visualization.update_connection_status(True, port_name)
            self.visualization.update_status_text(f'✅ Подключено к {port_name}', '#3fb950')
            print(f"✅ Успешное подключение к {port_name}")

            # Сброс буфера и отправка тестовой команды
            self.serial_reader.send_command("START")
            return True
        else:
            self.use_test_data = True
            self.visualization.update_status_text('📡 Тестовый режим (ошибка подключения)', '#ffa657')
            print("❌ Ошибка подключения, остаемся в тестовом режиме")
            return False

    def _on_connect_port(self, event):
        """Подключение/отключение порта"""
        if self.serial_reader.is_connected:
            self.serial_reader.disconnect()
            self.use_test_data = True
            self.control_panel.update_connect_button(False)
            self.visualization.update_connection_status(False)
            self.visualization.update_status_text('📡 Тестовый режим', '#ffa657')
            print("🔌 Порт отключен, переключаюсь на тестовый режим")
        else:
            # Если порт уже выбран, подключаемся
            if hasattr(self.serial_reader, 'config') and self.serial_reader.config.port:
                if self._connect_to_port(self.serial_reader.config.port):
                    self.control_panel.update_connect_button(True, self.serial_reader.config.port)
            else:
                # Иначе сканируем порты
                self._on_scan_ports(event)

    def _on_window_size_changed(self, window_size: int):
        """Изменение размера окна ВСР"""
        self.hrv_config.window_rr_count = window_size
        print(f"📊 Размер окна ВСР изменен на {window_size} RR")

    def _generate_test_data(self):
        """Генерация тестовых данных"""
        import math

        self.test_counter += 1
        t = self.test_counter * 0.05

        # Реалистичный PPG сигнал
        heart_rate = 1.2  # Гц (72 уд/мин)
        respiration = 0.25  # Гц (15 дыханий/мин)
        noise_level = 8

        # Основные компоненты
        cardiac = 200 * math.sin(t * 2 * math.pi * heart_rate)
        respiratory = 30 * math.sin(t * 2 * math.pi * respiration)
        noise = np.random.normal(0, noise_level)

        # Базовый уровень с медленным дрейфом
        baseline = 512 + 50 * math.sin(t * 2 * math.pi * 0.02)

        signal_value = int(baseline + cardiac + respiratory + noise)
        signal_value = max(0, min(1023, signal_value))

        # Генерация RR интервалов каждые ~1 секунду
        if self.test_counter % 20 == 0:
            # Реалистичные вариации RR
            base_rr = 800  # 75 уд/мин
            variability = 50 * math.sin(t * 2 * math.pi * 0.1)  # 0.1 Гц вариабельность
            random_var = np.random.normal(0, 20)

            rr_value = base_rr + variability + random_var
            rr_value = max(300, min(1200, rr_value))

            return [
                ('PPG', signal_value, time.time()),
                ('RR', rr_value, time.time())
            ]

        return [('PPG', signal_value, time.time())]

    def _read_serial_data(self):
        """Чтение данных с последовательного порта"""
        try:
            if self.use_test_data:
                return self._generate_test_data()
            elif self.serial_reader.is_connected:
                data_points = self.serial_reader.read_data()

                if data_points and self.data_count < 10:
                    print(f"📥 Получено {len(data_points)} точек данных")

                return data_points
            else:
                return []

        except Exception as e:
            print(f"❌ Ошибка в _read_serial_data: {e}")
            return []

    def _process_data_points(self, data_points):
        """Обработка полученных точек данных"""
        for data_type, value, timestamp in data_points:
            self.last_data_time = time.time()

            if data_type == 'PPG':
                self.signal_data.append(value)

                if self.recording_manager.state.value == 'RECORDING' and self.frame_count % 3 == 0:
                    rec_time = timestamp - self.recording_manager.start_time
                    self.recording_manager.add_data_point('ppg_raw', value, rec_time)

            elif data_type == 'RR':
                position = len(self.rr_intervals)
                is_valid, artifact_type = self.rr_filter.validate_and_mark(value, timestamp, position)

                if is_valid:
                    self.current_rr = value
                    self.current_bpm = int(60000 / value) if value > 0 else 0
                    self.rr_intervals.append(value)
                    self.rr_timestamps.append(timestamp)
                    self.rr_valid_flags.append(True)
                    self.hrv_data.append(value)
                    self.rr_count = len(self.rr_intervals)

                    if self.recording_manager.state.value == 'RECORDING':
                        rec_time = timestamp - self.recording_manager.start_time
                        self.recording_manager.add_data_point('rr_intervals', value, rec_time)
                        self.recording_manager.add_data_point('rr_valid', 1, rec_time)
                        self.recording_manager.add_data_point('bpm', self.current_bpm, rec_time)

                else:
                    self.rr_intervals.append(value)
                    self.rr_timestamps.append(timestamp)
                    self.rr_valid_flags.append(False)
                    self.hrv_data.append(value)

                    if self.recording_manager.state.value == 'RECORDING':
                        rec_time = timestamp - self.recording_manager.start_time
                        self.recording_manager.add_data_point('rr_intervals', value, rec_time)
                        self.recording_manager.add_data_point('rr_valid', 0, rec_time)

    def _calculate_hrv_metrics(self, current_time: float):
        """Расчет всех метрик ВСР"""
        try:
            if len(self.rr_intervals) < 2:
                return

            valid_rr = []
            if len(self.rr_intervals) == len(self.rr_valid_flags):
                valid_rr = [rr for rr, valid in zip(self.rr_intervals, self.rr_valid_flags) if valid]

            if len(valid_rr) < self.hrv_config.min_rr_for_sdnn:
                valid_rr = list(self.rr_intervals)[-self.hrv_config.window_rr_count:]

            window_size = min(self.hrv_config.window_rr_count, len(valid_rr))
            windowed_rr = valid_rr[-window_size:] if window_size > 0 else valid_rr

            if len(windowed_rr) < 2:
                return

            # SDNN
            if len(windowed_rr) >= self.hrv_config.min_rr_for_sdnn:
                self.sdnn_value = self.hrv_analyzer.calculate_sdnn(windowed_rr)

                if self.recording_manager.state.value == 'RECORDING' and self.frame_count % 30 == 0:
                    rec_time = current_time - self.recording_manager.start_time
                    self.recording_manager.add_data_point('sdnn', self.sdnn_value, rec_time)

            # Стресс-индекс
            if (current_time - self.last_stress_calc_time > 2.0 and
                len(windowed_rr) >= self.hrv_config.min_rr_for_stress):
                self.stress_index = self.hrv_analyzer.calculate_stress_index(windowed_rr)
                self.last_stress_calc_time = current_time

                if self.recording_manager.state.value == 'RECORDING':
                    rec_time = current_time - self.recording_manager.start_time
                    self.recording_manager.add_data_point('stress_index', self.stress_index, rec_time)

            # Спектральный анализ LF/HF (исправленная формула из вашего кода)
            if (len(windowed_rr) >= self.hrv_config.min_rr_for_spectrum and
                current_time - self.last_spectrum_calc_time > 1.5):  # Интервал как в вашем коде

                self.lf_hf_ratio = self.hrv_analyzer.calculate_spectrum(windowed_rr)
                self.last_spectrum_calc_time = current_time

                if self.recording_manager.state.value == 'RECORDING':
                    rec_time = current_time - self.recording_manager.start_time
                    self.recording_manager.add_data_point('lf_hf', self.lf_hf_ratio, rec_time)

                # Отладочный вывод
                if abs(self.lf_hf_ratio - 1.0) > 0.1:  # Если значение отличается от нейтрального
                    print(f"📊 LF/HF баланс: {self.lf_hf_ratio:.2f}")

            # RMSSD
            if len(windowed_rr) >= self.hrv_config.min_rr_for_rmssd:
                self.rmssd_value = self.hrv_analyzer.calculate_rmssd(windowed_rr)

                if self.recording_manager.state.value == 'RECORDING' and self.frame_count % 30 == 0:
                    rec_time = current_time - self.recording_manager.start_time
                    self.recording_manager.add_data_point('rmssd', self.rmssd_value, rec_time)

            # Статистика RR
            if len(self.rr_intervals) > 0:
                recent_valid_rr = []
                for i in range(len(self.rr_intervals)):
                    if i < len(self.rr_valid_flags) and self.rr_valid_flags[i]:
                        recent_valid_rr.append(self.rr_intervals[i])

                if len(recent_valid_rr) > 0:
                    if len(recent_valid_rr) >= 50:
                        self.mean_rr = np.mean(recent_valid_rr[-50:])
                        self.rr_range = np.max(recent_valid_rr[-50:]) - np.min(recent_valid_rr[-50:])
                    else:
                        self.mean_rr = np.mean(recent_valid_rr)
                        self.rr_range = np.max(recent_valid_rr) - np.min(recent_valid_rr) if len(recent_valid_rr) >= 2 else 0

        except Exception as e:
            print(f"⚠️ Ошибка расчета метрик ВСР: {e}")

    def update(self, frame):
        """Основная функция обновления"""
        try:
            self.frame_count += 1
            current_time = time.time()

            # Обновление FPS
            self.fps_counter += 1
            if current_time - self.fps_time >= 1.0:
                fps = self.fps_counter / (current_time - self.fps_time)
                self.fps_counter = 0
                self.fps_time = current_time

                if self.frame_count % 60 == 0:
                    mode = "ТЕСТ" if self.use_test_data else "ДАЧИК"


            # Чтение и обработка данных
            data_points = self._read_serial_data()
            if data_points:
                self._process_data_points(data_points)

            # Расчет метрик ВСР
            if self.frame_count % 10 == 0:
                self._calculate_hrv_metrics(current_time)

            # Обновление графиков
            self.visualization.update_signal_plot(self.signal_data)

            if len(self.hrv_data) > 1:
                rr_valid_for_plot = []
                if len(self.rr_valid_flags) >= len(self.hrv_data):
                    rr_valid_for_plot = list(self.rr_valid_flags)[-len(self.hrv_data):]

                self.visualization.update_hrv_plot(
                    list(self.hrv_data),
                    rr_valid_for_plot
                )

            # Обновление информационной панели
            self.visualization.update_info_panel(
                bpm=self.current_bpm,
                rr=self.current_rr,
                sdnn=self.sdnn_value,
                stress=self.stress_index,
                lf_hf=self.lf_hf_ratio,
                rmssd=self.rmssd_value,
                rr_count=self.rr_count,
                mean_rr=self.mean_rr,
                rr_range=self.rr_range
            )

            # Проверка потери сигнала
            if (self.serial_reader.is_connected and
                time.time() - self.last_data_time > 10.0 and
                self.rr_count > 0):
                self.visualization.update_status_text('⚠️ Потеря сигнала с датчика', '#ffa657')

            # Обновление дополнительных графиков
            if (self.extra_window.window_open and
                self.frame_count % 20 == 0 and
                len(self.rr_intervals) > 5):
                self.extra_window.update(
                    list(self.rr_intervals),
                    list(self.rr_timestamps),
                    self.rr_filter.get_artifacts_in_window(50)
                )

        except Exception as e:
            print(f"❌ Ошибка в update: {e}")

        return self.visualization.get_artists()

    def run(self):
        """Запуск приложения"""
        print("\n" + "=" * 60)
        print("🚀 МОНИТОР HRV ЗАПУЩЕН")
        print("=" * 60)
        print(f"📊 Окно ВСР: {self.hrv_config.window_rr_count} RR интервалов")
        print(f"⚡ Интервал обновления: {self.config.update_interval} мс")
        print(f"🔌 Порт по умолчанию: {self.config.port}")
        print(f"📡 Бодрейт: {self.config.baud_rate}")
        print("👉 Нажмите 'Сканировать порты' для выбора порта")
        print("👉 Нажмите 'Подключить' для соединения с датчиком")
        print("👉 Нажмите 'Начать запись' для записи данных")
        print("👉 Нажмите 'Стоп' для остановки записи и просмотра анализа")
        print("=" * 60)

        try:
            plt.show()
        except Exception as e:
            print(f"❌ Ошибка при запуске интерфейса: {e}")
            traceback.print_exc()