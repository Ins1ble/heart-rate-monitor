"""
Окно дополнительных графиков
"""
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
from typing import List, Optional, Tuple
from config import HRVConfig


class ExtraGraphsWindow:
    """Управление окном дополнительных графиков"""

    def __init__(self, hrv_config: HRVConfig):
        self.hrv_config = hrv_config
        self.window_open = False
        self.fig = None
        self.axes = []
        self.lines = []
        self.scatters = []
        self.hist_bars = None
        self.hist_bin_edges = None
        self.max_points = 200
        self.artifact_scatter = None

    def open(self, rr_intervals: List[float] = None,
             rr_timestamps: List[float] = None,
             artifacts: List[Tuple[int, float, float]] = None):
        """
        Открытие окна дополнительных графиков

        Args:
            rr_intervals: Список RR интервалов
            rr_timestamps: Список временных меток
            artifacts: Список артефактов (позиция, время, значение)
        """
        if self.fig is not None:
            try:
                if plt.fignum_exists(self.fig.number):
                    self.fig.canvas.manager.window.raise_()
                    return
            except:
                self._reset_state()

        self._create_window()

        if rr_intervals:
            self.update(rr_intervals, rr_timestamps or [], artifacts or [])

    def _create_window(self):
        """Создание окна и графиков"""
        self.fig = plt.figure(figsize=(14, 8), facecolor='#0d1117')
        self.fig.suptitle(
            f'Дополнительные графики HRV анализа (Окно: {self.hrv_config.window_rr_count} RR)',
            color='white', fontsize=16, fontweight='bold'
        )

        # Создание осей
        self.axes = [
            plt.subplot(221),  # Гистограмма
            plt.subplot(222),  # Poincare plot
            plt.subplot(223),  # SDNN timeline
            plt.subplot(224)  # RMSSD timeline
        ]

        # Настройка осей
        for ax in self.axes:
            ax.set_facecolor('#161b22')
            ax.grid(True, alpha=0.15, color='#30363d', linestyle='-', linewidth=0.5)
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')

        # Инициализация графиков
        self._init_histogram(self.axes[0])
        self._init_poincare(self.axes[1])
        self._init_sdnn_timeline(self.axes[2])
        self._init_rmssd_timeline(self.axes[3])

        plt.tight_layout()
        self.fig.canvas.mpl_connect('close_event', lambda event: self._on_close())
        self.window_open = True

        plt.show(block=False)

    def _init_histogram(self, ax):
        """Инициализация гистограммы RR интервалов"""
        ax.set_title('Гистограмма RR интервалов', color='white', fontsize=12)
        ax.set_xlabel('RR (мс)', color='white')
        ax.set_ylabel('Частота', color='white')

        n_bins = 20
        self.hist_bin_edges = np.linspace(400, 1200, n_bins + 1)
        heights = np.zeros(n_bins)
        bars = ax.bar(self.hist_bin_edges[:-1], heights,
                      width=np.diff(self.hist_bin_edges),
                      color='#58a6ff', edgecolor='white', alpha=0.7)

        self.hist_bars = bars

    def _init_poincare(self, ax):
        """Инициализация графика Пуанкаре"""
        ax.set_title('Poincaré Plot (RRₙ vs RRₙ₊₁)', color='white', fontsize=12)
        ax.set_xlabel('RRₙ (мс)', color='white')
        ax.set_ylabel('RRₙ₊₁ (мс)', color='white')

        # Линия равенства
        min_val, max_val = 400, 1200
        ax.plot([min_val, max_val], [min_val, max_val],
                '--', color='#8b949e', alpha=0.5, linewidth=1)

        # Скаттер для валидных точек
        valid_scatter = ax.scatter([], [], c='#ff7b72', alpha=0.6, s=25,
                                   edgecolors='white', linewidths=0.5)
        self.scatters.append(valid_scatter)

        # Скаттер для артефактов
        artifact_scatter = ax.scatter([], [], c='#ff6b6b', alpha=0.8, s=40,
                                      edgecolors='white', linewidths=1, marker='x')
        self.scatters.append(artifact_scatter)

    def _init_sdnn_timeline(self, ax):
        """Инициализация графика SDNN"""
        ax.set_title(f'SDNN (скользящее окно {self.hrv_config.window_rr_count} RR)',
                     color='white', fontsize=12)
        ax.set_xlabel('Время (RR интервалы)', color='white')
        ax.set_ylabel('SDNN (мс)', color='white')

        line, = ax.plot([], [], '#3fb950', linewidth=2)
        self.lines.append(line)

    def _init_rmssd_timeline(self, ax):
        """Инициализация графика RMSSD"""
        ax.set_title(f'RMSSD (скользящее окно {self.hrv_config.window_rr_count} RR)',
                     color='white', fontsize=12)
        ax.set_xlabel('Время (RR интервалы)', color='white')
        ax.set_ylabel('RMSSD (мс)', color='white')

        line, = ax.plot([], [], '#d2a8ff', linewidth=2)
        self.lines.append(line)

    def update(self, rr_intervals: List[float],
               rr_timestamps: List[float],
               artifacts: List[Tuple[int, float, float]] = None):
        """
        Обновление всех графиков

        Args:
            rr_intervals: Список RR интервалов
            rr_timestamps: Список временных меток
            artifacts: Список артефактов
        """
        if not self._is_window_open():
            return

        if len(rr_intervals) < 2:
            return

        try:
            self._update_histogram(rr_intervals)
            self._update_poincare(rr_intervals, artifacts)
            self._update_sdnn_timeline(rr_intervals)
            self._update_rmssd_timeline(rr_intervals)

            if self.fig:
                self.fig.canvas.draw_idle()

        except Exception as e:
            print(f"Ошибка обновления графиков: {e}")
            if not self._is_window_open():
                self._reset_state()

    def _is_window_open(self) -> bool:
        """Проверка, открыто ли окно"""
        if not self.window_open or self.fig is None:
            return False
        try:
            return plt.fignum_exists(self.fig.number)
        except:
            return False

    def _update_histogram(self, rr_intervals: List[float]):
        """Обновление гистограммы"""
        if len(rr_intervals) < 5 or self.hist_bars is None:
            return

        hist, _ = np.histogram(rr_intervals, bins=self.hist_bin_edges)
        for bar, height in zip(self.hist_bars, hist):
            bar.set_height(height)

        self.axes[0].relim()
        self.axes[0].autoscale_view(scalex=False)

    def _update_poincare(self, rr_intervals: List[float],
                         artifacts: List[Tuple[int, float, float]] = None):
        """Обновление графика Пуанкаре"""
        if len(rr_intervals) < 3 or len(self.scatters) < 2:
            return

        n_points = min(len(rr_intervals) - 1, self.max_points)
        rr_array = np.array(rr_intervals[-n_points - 1:])

        x_data = rr_array[:-1]
        y_data = rr_array[1:]

        if len(x_data) > 0 and len(y_data) > 0:
            # Обновление валидных точек
            self.scatters[0].set_offsets(np.column_stack([x_data, y_data]))

            # Обновление артефактов
            if artifacts and len(artifacts) > 0:
                artifact_x = []
                artifact_y = []

                for pos, ts, val in artifacts[-self.max_points:]:
                    if pos < len(rr_intervals) - 1:
                        artifact_x.append(rr_intervals[pos])
                        if pos + 1 < len(rr_intervals):
                            artifact_y.append(rr_intervals[pos + 1])

                if artifact_x and artifact_y:
                    self.scatters[1].set_offsets(np.column_stack([artifact_x, artifact_y]))
                else:
                    self.scatters[1].set_offsets(np.empty((0, 2)))

            self.axes[1].relim()
            self.axes[1].autoscale_view()

    def _update_sdnn_timeline(self, rr_intervals: List[float]):
        """Обновление графика SDNN"""
        if len(rr_intervals) < self.hrv_config.window_rr_count or len(self.lines) < 1:
            return

        sdnn_values = []
        from analysis.hrv_analysis import HRVAnalyzer

        for i in range(self.hrv_config.window_rr_count, len(rr_intervals)):
            window = rr_intervals[i - self.hrv_config.window_rr_count:i]
            if len(window) >= self.hrv_config.min_rr_for_sdnn:
                sdnn_values.append(HRVAnalyzer.calculate_sdnn(window))

        if sdnn_values:
            x_data = list(range(len(sdnn_values)))
            self.lines[0].set_data(x_data, sdnn_values)
            self.axes[2].relim()
            self.axes[2].autoscale_view()

    def _update_rmssd_timeline(self, rr_intervals: List[float]):
        """Обновление графика RMSSD"""
        if len(rr_intervals) < self.hrv_config.window_rr_count or len(self.lines) < 2:
            return

        rmssd_values = []
        from analysis.hrv_analysis import HRVAnalyzer

        for i in range(self.hrv_config.window_rr_count, len(rr_intervals)):
            window = rr_intervals[i - self.hrv_config.window_rr_count:i]
            if len(window) >= self.hrv_config.min_rr_for_rmssd:
                rmssd_values.append(HRVAnalyzer.calculate_rmssd(window))

        if rmssd_values:
            x_data = list(range(len(rmssd_values)))
            self.lines[1].set_data(x_data, rmssd_values)
            self.axes[3].relim()
            self.axes[3].autoscale_view()

    def _on_close(self):
        """Обработка закрытия окна"""
        self._reset_state()

    def _reset_state(self):
        """Сброс состояния окна"""
        self.window_open = False
        self.fig = None
        self.axes = []
        self.lines = []
        self.scatters = []
        self.hist_bars = None
        self.hist_bin_edges = None
        self.artifact_scatter = None

    def close(self):
        """Закрытие окна"""
        if self._is_window_open():
            plt.close(self.fig)
        self._reset_state()