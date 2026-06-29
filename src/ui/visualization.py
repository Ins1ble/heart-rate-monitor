"""
Визуализация данных и графиков
"""
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
from typing import List, Optional, Tuple
from config import HRVConfig


class Visualization:
    """Класс для визуализации данных HRV"""

    def __init__(self, hrv_config: HRVConfig):
        self.hrv_config = hrv_config
        self.fig = None
        self.axes = {}
        self.lines = {}
        self.scatters = {}
        self.texts = {}

        self._setup_figure()
        self._setup_signal_plot()
        self._setup_hrv_plot()
        self._setup_info_panel()
        self._setup_annotations()

    def _setup_figure(self):
        """Настройка основной фигуры"""
        plt.style.use('dark_background')
        self.fig = plt.figure(figsize=(16, 13))
        self.fig.patch.set_facecolor('#0d1117')

    def _setup_signal_plot(self):
        """Настройка графика PPG сигнала"""
        self.axes['signal'] = plt.subplot2grid((14, 1), (1, 0), rowspan=4)
        ax = self.axes['signal']

        # Настройка внешнего вида
        ax.set_facecolor('#161b22')
        ax.grid(True, alpha=0.15, color='#30363d', linestyle='-', linewidth=0.5)
        ax.tick_params(colors='white', labelsize=10)
        ax.set_ylim(0, 1024)
        ax.set_xlim(0, 250)
        ax.set_ylabel('Амплитуда PPG (ед.)', color='white',
                      fontsize=13, fontweight='bold', labelpad=15)

        # Линия сигнала
        self.lines['signal'], = ax.plot([], [], '#58a6ff', linewidth=1.8, alpha=0.95,
                                        label='Сырой PPG сигнал', antialiased=True)
        ax.legend(loc='upper right', facecolor='#161b22', edgecolor='#30363d',
                  labelcolor='white', fontsize=11, framealpha=0.9)

    def _setup_hrv_plot(self):
        """Настройка графика ВСР"""
        self.axes['hrv'] = plt.subplot2grid((14, 1), (6, 0), rowspan=3)
        ax = self.axes['hrv']

        # Настройка внешнего вида
        ax.set_facecolor('#161b22')
        ax.grid(True, alpha=0.15, color='#30363d', linestyle='-', linewidth=0.5)
        ax.tick_params(colors='white', labelsize=10)
        ax.set_ylabel('RR интервал (мс)', color='#58a6ff',
                      fontsize=12, fontweight='bold', labelpad=10)
        ax.set_xlabel('Номер сердечного цикла', color='#8b949e', fontsize=11)
        ax.set_ylim(400, 1200)
        ax.set_xlim(0, 80)

        # Линия RR интервалов
        self.lines['hrv'], = ax.plot([], [], '#ff7b72', linewidth=2.2, alpha=0.95,
                                     label='RR интервалы', zorder=3, antialiased=True)

        # Скаттер для точек
        self.scatters['hrv'] = ax.scatter([], [], c='#ff7b72', s=25, alpha=0.8,
                                          edgecolors='white', linewidths=0.5, zorder=4)

        # Скаттер для артефактов
        self.scatters['artifacts'] = ax.scatter([], [], c='#ff6b6b', s=60, alpha=0.9,
                                                edgecolors='white', linewidths=1,
                                                marker='x', zorder=5, label='Артефакты')

        # Линия среднего значения
        self.lines['hrv_avg'], = ax.plot([], [], '#c9d1d9', linewidth=1.5, alpha=0.7,
                                         linestyle='--', label='Среднее', zorder=2)

        ax.legend(loc='upper right', facecolor='#161b22', edgecolor='#30363d',
                  labelcolor='white', fontsize=10, framealpha=0.9)

    def _setup_info_panel(self):
        """Настройка информационной панели"""
        self.axes['info'] = plt.subplot2grid((14, 1), (10, 0), rowspan=4)
        ax = self.axes['info']
        ax.set_facecolor('#0d1117')
        ax.axis('off')

    def _setup_annotations(self):
        """Настройка текстовых аннотаций"""
        # Индикатор подключения
        self.texts['connection'] = self.axes['signal'].text(
            0.85, 0.04, '🔴 ПОРТ НЕ ПОДКЛЮЧЕН',
            transform=self.axes['signal'].transAxes, fontsize=10,
            color='#ff7b72', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22',
                      edgecolor='#ff7b72', alpha=0.8, linewidth=1.2)
        )

        # Индикатор ЧСС
        self.texts['bpm_large'] = self.axes['signal'].text(
            0.02, 0.96, '--', transform=self.axes['signal'].transAxes,
            fontsize=48, fontweight='bold', color='#58a6ff',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#161b22',
                      edgecolor='#58a6ff', alpha=0.9, linewidth=2)
        )

        # Метка ЧСС
        self.texts['bpm_label'] = self.axes['signal'].text(
            0.02, 0.86, 'ЧСС', transform=self.axes['signal'].transAxes,
            fontsize=14, color='#8b949e', fontweight='bold'
        )

        # Статус
        self.texts['status'] = self.axes['signal'].text(
            0.02, 0.04, '⚪ Ожидание подключения датчика...',
            transform=self.axes['signal'].transAxes, fontsize=11,
            color='#8b949e', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', alpha=0.8)
        )

        # Состояние записи
        self.texts['state'] = self.axes['info'].text(
            0.02, 1.0, 'Состояние: IDLE', transform=self.axes['info'].transAxes,
            fontsize=11, color='#8b949e', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', alpha=0.8)
        )

        # Создание таблицы показателей
        self._create_info_table()

    def _create_info_table(self):
        """Создание таблицы с показателями"""
        # Позиции колонок
        col1_x = 0.05  # Левая колонка - названия
        col2_x = 0.32  # Центральная колонка - значения
        col3_x = 0.58  # Правая колонка - названия
        col4_x = 0.85  # Правая колонка - значения

        row_height = 0.13
        start_y = 0.88

        # Основные показатели
        self.axes['info'].text(col1_x, 0.8, 'ОСНОВНЫЕ ПОКАЗАТЕЛИ:',
                               fontsize=14, color='#8b949e',
                               transform=self.axes['info'].transAxes, fontweight='bold')

        # ЧСС
        self.texts['bpm_label'] = self.axes['info'].text(
            col1_x, start_y - row_height * 1.3, 'ЧСС:',
            fontsize=13, color='#c9d1d9',
            transform=self.axes['info'].transAxes, fontweight='bold',
            verticalalignment='top'
        )

        self.texts['bpm_value'] = self.axes['info'].text(
            col2_x, start_y - row_height * 1.3, '--',
            fontsize=22, fontweight='bold', color='#58a6ff',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        # RR интервал
        self.texts['rr_label'] = self.axes['info'].text(
            col1_x, start_y - row_height * 2.6, 'RR интервал:',
            fontsize=13, color='#c9d1d9',
            transform=self.axes['info'].transAxes, fontweight='bold',
            verticalalignment='top'
        )

        self.texts['rr_value'] = self.axes['info'].text(
            col2_x, start_y - row_height * 2.6, '--',
            fontsize=22, fontweight='bold', color='#ff7b72',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        # Показатели ВСР
        self.axes['info'].text(col3_x, start_y, 'ПОКАЗАТЕЛИ ВСР:',
                               fontsize=14, color='#8b949e',
                               transform=self.axes['info'].transAxes, fontweight='bold',
                               verticalalignment='top')

        # SDNN
        self.texts['sdnn_label'] = self.axes['info'].text(
            col3_x, start_y - row_height * 1.3, 'SDNN:',
            fontsize=13, color='#c9d1d9',
            transform=self.axes['info'].transAxes, fontweight='bold',
            verticalalignment='top'
        )

        self.texts['sdnn_value'] = self.axes['info'].text(
            col4_x, start_y - row_height * 1.3, '--',
            fontsize=22, fontweight='bold', color='#3fb950',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        # Стресс-индекс
        self.texts['stress_label'] = self.axes['info'].text(
            col3_x, start_y - row_height * 2.6, 'Стресс-индекс:',
            fontsize=13, color='#c9d1d9',
            transform=self.axes['info'].transAxes, fontweight='bold',
            verticalalignment='top'
        )

        self.texts['stress_value'] = self.axes['info'].text(
            col4_x, start_y - row_height * 2.6, '--',
            fontsize=22, fontweight='bold', color='#ff7b72',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        # Разделительная линия
        self.axes['info'].axhline(y=start_y - row_height * 4.2, xmin=0.02, xmax=0.98,
                                  color='#30363d', linewidth=1.0, alpha=0.6)

        # Вторая строка таблицы
        second_start_y = start_y - row_height * 4.5

        # Спектральный анализ
        self.axes['info'].text(col1_x, second_start_y, 'СПЕКТРАЛЬНЫЙ АНАЛИЗ:',
                               fontsize=14, color='#8b949e',
                               transform=self.axes['info'].transAxes, fontweight='bold',
                               verticalalignment='top')

        # LF/HF баланс
        self.texts['spectrum_label'] = self.axes['info'].text(
            col1_x, second_start_y - row_height * 1.3, 'LF/HF баланс:',
            fontsize=13, color='#c9d1d9',
            transform=self.axes['info'].transAxes, fontweight='bold',
            verticalalignment='top'
        )

        self.texts['spectrum_value'] = self.axes['info'].text(
            col2_x, second_start_y - row_height * 1.3, '--',
            fontsize=22, fontweight='bold', color='#d2a8ff',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        # RMSSD
        self.texts['rmssd_label'] = self.axes['info'].text(
            col1_x, second_start_y - row_height * 2.8, 'RMSSD:',
            fontsize=13, color='#c9d1d9',
            transform=self.axes['info'].transAxes, fontweight='bold',
            verticalalignment='top'
        )

        self.texts['rmssd_value'] = self.axes['info'].text(
            col2_x, second_start_y - row_height * 2.7, '--',
            fontsize=22, fontweight='bold', color='#d2a8ff',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        self.texts['rmssd_unit'] = self.axes['info'].text(
            col2_x + 0.1, second_start_y - row_height * 3.0, 'мс',
            fontsize=14, color='#8b949e',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        # Статистика
        self.axes['info'].text(col3_x, second_start_y, 'СТАТИСТИКА:',
                               fontsize=14, color='#8b949e',
                               transform=self.axes['info'].transAxes, fontweight='bold',
                               verticalalignment='top')

        # Количество RR
        self.texts['rr_count_label'] = self.axes['info'].text(
            col3_x, second_start_y - row_height * 1.3, 'Записей RR:',
            fontsize=13, color='#c9d1d9',
            transform=self.axes['info'].transAxes, fontweight='bold',
            verticalalignment='top'
        )

        self.texts['rr_count'] = self.axes['info'].text(
            col4_x, second_start_y - row_height * 1.1, '0',
            fontsize=18, fontweight='bold', color='#ff7b72',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        # Среднее RR
        self.texts['mean_rr_label'] = self.axes['info'].text(
            col3_x, second_start_y - row_height * 2.5, 'Среднее RR:',
            fontsize=13, color='#c9d1d9',
            transform=self.axes['info'].transAxes, fontweight='bold',
            verticalalignment='top'
        )

        self.texts['mean_rr'] = self.axes['info'].text(
            col4_x, second_start_y - row_height * 2.4, '--',
            fontsize=18, fontweight='bold', color='#58a6ff',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        self.texts['mean_rr_unit'] = self.axes['info'].text(
            col4_x + 0.14, second_start_y - row_height * 2.4, 'мс',
            fontsize=14, color='#8b949e',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        # Диапазон RR
        self.texts['rr_range_label'] = self.axes['info'].text(
            col3_x, second_start_y - row_height * 3.8, 'Диапазон RR:',
            fontsize=13, color='#c9d1d9',
            transform=self.axes['info'].transAxes, fontweight='bold',
            verticalalignment='top'
        )

        self.texts['rr_range'] = self.axes['info'].text(
            col4_x, second_start_y - row_height * 3.6, '--',
            fontsize=18, fontweight='bold', color='#ff7b72',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

        self.texts['rr_range_unit'] = self.axes['info'].text(
            col4_x + 0.14, second_start_y - row_height * 3.7, 'мс',
            fontsize=14, color='#8b949e',
            transform=self.axes['info'].transAxes, verticalalignment='top'
        )

    def update_signal_plot(self, signal_data: deque):
        """Обновление графика сигнала"""
        if len(signal_data) > 0:
            x_data = list(range(len(signal_data)))
            self.lines['signal'].set_data(x_data, list(signal_data))

            # Автомасштабирование по Y
            if len(signal_data) > 10:
                y_min = max(0, min(signal_data) * 0.95)
                y_max = min(1024, max(signal_data) * 1.05)
                if y_max - y_min > 50:
                    self.axes['signal'].set_ylim(y_min, y_max)

    def update_hrv_plot(self, hrv_data: List[float], rr_valid_flags: List[bool] = None):
        """Обновление графика ВСР"""
        if len(hrv_data) > 1:
            x_data = list(range(1, len(hrv_data) + 1))
            y_data = list(hrv_data)

            self.lines['hrv'].set_data(x_data, y_data)
            self.scatters['hrv'].set_offsets(np.column_stack([x_data, y_data]))

            # Отображение артефактов
            if rr_valid_flags and len(rr_valid_flags) == len(hrv_data):
                artifact_positions = []
                artifact_values = []

                for i, (rr_val, valid) in enumerate(zip(hrv_data, rr_valid_flags)):
                    if not valid and i < len(x_data) and i < len(y_data):
                        artifact_positions.append(x_data[i])
                        artifact_values.append(y_data[i])

                if artifact_positions:
                    self.scatters['artifacts'].set_offsets(
                        np.column_stack([artifact_positions, artifact_values])
                    )
                else:
                    self.scatters['artifacts'].set_offsets(np.empty((0, 2)))

            # Линия среднего
            if len(hrv_data) >= 3:
                mean_value = np.mean(y_data)
                self.lines['hrv_avg'].set_data([x_data[0], x_data[-1]], [mean_value, mean_value])

                # Автомасштабирование
                if len(y_data) >= 5:
                    y_min = max(400, min(y_data) * 0.9)
                    y_max = min(1200, max(y_data) * 1.1)

                    if y_max - y_min > 50:
                        self.axes['hrv'].set_ylim(y_min, y_max)

                    # Обновление видимой области по X
                    if len(hrv_data) > 80:
                        self.axes['hrv'].set_xlim(len(hrv_data) - 80, len(hrv_data))

    def update_info_panel(self, **kwargs):
        """Обновление информационной панели"""
        # Обновление основных показателей
        if 'bpm' in kwargs:
            bpm = kwargs['bpm']
            self.texts['bpm_large'].set_text(f'{bpm}')
            self.texts['bpm_value'].set_text(f'{bpm}')

            # Цвет в зависимости от ЧСС
            if bpm < 60:
                color = '#58a6ff'
            elif bpm < 100:
                color = '#3fb950'
            elif bpm < 130:
                color = '#ff7b72'
            else:
                color = '#ff7b72'

            self.texts['bpm_large'].set_color(color)
            self.texts['bpm_value'].set_color(color)

        if 'rr' in kwargs:
            rr_val = kwargs['rr']
            self.texts['rr_value'].set_text(f'{rr_val:.0f}')

        if 'sdnn' in kwargs:
            sdnn = kwargs['sdnn']
            self.texts['sdnn_value'].set_text(f'{sdnn:.1f}')

            # Цвет в зависимости от SDNN
            if sdnn < 20:
                color = '#ff7b72'
            elif sdnn < 50:
                color = '#3fb950'
            else:
                color = '#58a6ff'

            self.texts['sdnn_value'].set_color(color)

        if 'stress' in kwargs:
            stress = kwargs['stress']
            # Добавим текстовый элемент для стресс-индекса если его нет
            if 'stress_value' not in self.texts:
                self.texts['stress_value'] = self.axes['info'].text(
                    0.85, 0.88 - 0.13 * 2.6, '--',
                    fontsize=22, fontweight='bold', color='#ff7b72',
                    transform=self.axes['info'].transAxes, verticalalignment='top'
                )
            self.texts['stress_value'].set_text(f'{stress:.0f}')

            # Цвет в зависимости от стресс-индекса
            if stress < 50:
                color = '#3fb950'
            elif stress < 150:
                color = '#ff7b72'
            else:
                color = '#ff7b72'

            self.texts['stress_value'].set_color(color)

        if 'lf_hf' in kwargs:
            lf_hf = kwargs['lf_hf']
            self.texts['spectrum_value'].set_text(f'{lf_hf:.2f}')

            # Цвет в зависимости от LF/HF
            if lf_hf < 0.5:
                color = '#58a6ff'
            elif lf_hf < 2.0:
                color = '#3fb950'
            else:
                color = '#ff7b72'

            self.texts['spectrum_value'].set_color(color)

        if 'rmssd' in kwargs:
            rmssd = kwargs['rmssd']
            self.texts['rmssd_value'].set_text(f'{rmssd:.1f}')

            # Цвет в зависимости от RMSSD
            if rmssd < 20:
                color = '#ff7b72'
            elif rmssd < 50:
                color = '#3fb950'
            else:
                color = '#58a6ff'

            self.texts['rmssd_value'].set_color(color)

        if 'rr_count' in kwargs:
            self.texts['rr_count'].set_text(f'{kwargs["rr_count"]}')

        if 'mean_rr' in kwargs:
            mean_rr = kwargs['mean_rr']
            self.texts['mean_rr'].set_text(f'{mean_rr:.0f}')

        if 'rr_range' in kwargs:
            rr_range = kwargs['rr_range']
            self.texts['rr_range'].set_text(f'{rr_range:.0f}')

    def update_connection_status(self, is_connected: bool, port: str = None):
        """Обновление индикатора подключения"""
        if is_connected:
            self.texts['connection'].set_text('🟢 ПОРТ ПОДКЛЮЧЕН')
            self.texts['connection'].set_color('#3fb950')
            self.texts['connection'].set_bbox(dict(
                boxstyle='round,pad=0.3', facecolor='#161b22',
                edgecolor='#3fb950', alpha=0.8, linewidth=1.2
            ))
        else:
            self.texts['connection'].set_text('🔴 ПОРТ НЕ ПОДКЛЮЧЕН')
            self.texts['connection'].set_color('#ff7b72')
            self.texts['connection'].set_bbox(dict(
                boxstyle='round,pad=0.3', facecolor='#161b22',
                edgecolor='#ff7b72', alpha=0.8, linewidth=1.2
            ))

    def update_status_text(self, text: str, color: str = '#8b949e'):
        """Обновление текста статуса"""
        self.texts['status'].set_text(text)
        self.texts['status'].set_color(color)

    def update_state_text(self, state: str, color: str = '#8b949e'):
        """Обновление текста состояния записи"""
        self.texts['state'].set_text(f'Состояние: {state}')
        self.texts['state'].set_color(color)

    def get_artists(self):
        """Получение всех художников для анимации"""
        return [
            self.lines['signal'],
            self.lines['hrv'],
            self.scatters['hrv'],
            self.scatters['artifacts'],
            self.lines['hrv_avg']
        ]

    def adjust_layout(self):
        """Корректировка расположения элементов"""
        plt.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.07, hspace=0.5)

    def draw(self):
        """Перерисовка фигуры"""
        if self.fig:
            self.fig.canvas.draw_idle()