"""Менеджер записи данных"""
import time
import pickle
import csv
from datetime import datetime
from typing import Dict, Any, Optional
import traceback
import numpy as np
import matplotlib.pyplot as plt

from config import RecordingState


class RecordingManager:
    def __init__(self):
        self.state = RecordingState.IDLE
        self.start_time = None
        self.current_file = None
        self.session_data = self._init_session_data()
        self.post_analysis_window = None  # Окно пост-анализа

    def _init_session_data(self) -> Dict[str, list]:
        """Инициализация структуры данных сессии"""
        return {
            'timestamps': [],
            'ppg_raw': [],
            'rr_intervals': [],
            'rr_valid': [],
            'bpm': [],
            'sdnn': [],
            'stress_index': [],
            'lf_hf': [],
            'rmssd': [],
            'rr_timestamps': [],
            'signal_quality': []  # Добавлено для совместимости с вашим кодом
        }

    def start_recording(self) -> bool:
        """Начать запись"""
        self.state = RecordingState.RECORDING
        self.start_time = time.time()
        self.session_data = self._init_session_data()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_file = f"hrv_session_{timestamp}.pkl"
        print(f"🎥 Начата запись сессии: {self.current_file}")
        return True

    def pause_recording(self) -> bool:
        """Поставить на паузу/возобновить запись"""
        if self.state == RecordingState.RECORDING:
            self.state = RecordingState.PAUSED
            print("⏸ Запись приостановлена")
            return True
        elif self.state == RecordingState.PAUSED:
            self.state = RecordingState.RECORDING
            print("▶ Запись возобновлена")
            return True
        return False

    def stop_recording(self) -> bool:
        """Остановить запись"""
        if self.state in [RecordingState.RECORDING, RecordingState.PAUSED]:
            self.state = RecordingState.STOPPED
            if self.save_to_file():
                print(f"⏹ Запись остановлена, сохранено: {self.current_file}")
            else:
                print(f"⏹ Запись остановлена, но были ошибки сохранения")

            # Показать пост-анализ
            self.show_post_analysis()

            return True
        return False

    def add_data_point(self, data_type: str, value: Any, timestamp: float = None):
        """Добавить точку данных"""
        if self.state != RecordingState.RECORDING:
            return

        if timestamp is None:
            timestamp = time.time() - self.start_time

        if data_type in self.session_data:
            self.session_data[data_type].append((timestamp, value))
        else:
            print(f"⚠️ Предупреждение: неизвестный тип данных '{data_type}'")

    def save_to_file(self) -> bool:
        """Сохранение данных в файлы"""
        try:
            # Сохранение в pickle
            metadata = {
                'start_time': self.start_time,
                'duration': time.time() - self.start_time,
                'saved_at': datetime.now().isoformat(),
                'hrv_config': {  # Добавлено для совместимости с вашим кодом
                    'window_rr_count': 30,
                    'min_rr_for_sdnn': 5,
                    'min_rr_for_stress': 30,
                    'min_rr_for_spectrum': 20,
                    'min_rr_for_rmssd': 2
                },
                'sample_count': {k: len(v) for k, v in self.session_data.items()}
            }

            with open(self.current_file, 'wb') as f:
                pickle.dump({
                    'metadata': metadata,
                    'data': self.session_data
                }, f)

            print(f"✅ Pickle сохранен: {self.current_file}")

            # Сохранение в CSV
            csv_file = self.current_file.replace('.pkl', '.csv')
            return self._save_csv(csv_file)

        except Exception as e:
            print(f"❌ Ошибка сохранения pickle: {e}")
            traceback.print_exc()
            return False

    def _save_csv(self, filename: str) -> bool:
        """Сохранение данных в CSV"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Заголовок как в вашем коде
                writer.writerow(['# HRV DATA WITH SIGNAL QUALITY AND ARTIFACT MARKERS'])
                writer.writerow([f'# Session: {self.current_file}'])
                writer.writerow([f'# HRV Window: {30} RR intervals'])  # Фиксированное значение для совместимости
                writer.writerow(['#'])

                writer.writerow([
                    'Time_s',
                    'RR_ms',
                    'RR_Valid',
                    'BPM',
                    'Signal_Quality',
                    'SDNN_ms',
                    'Stress_Index',
                    'LF_HF_Ratio',
                    'RMSSD_ms'
                ])

                if self.session_data['rr_intervals']:
                    n_points = len(self.session_data['rr_intervals'])
                    for i in range(n_points):
                        row = self._prepare_csv_row(i)
                        writer.writerow(row)

            print(f"✅ CSV saved: {filename}")
            return True

        except Exception as e:
            print(f"❌ CSV save error: {e}")
            return False

    def _prepare_csv_row(self, index: int) -> list:
        """Подготовка строки данных для CSV"""
        timestamp = self._get_timestamp(index)
        rr_val = self.session_data['rr_intervals'][index][1]
        rr_valid = self._get_rr_valid(index)
        bpm = self._calculate_bpm(rr_val)

        # Получение метрик ВСР
        sdnn_val = self._get_nearest_value('sdnn', timestamp)
        stress_val = self._get_nearest_value('stress_index', timestamp)
        lfhf_val = self._get_nearest_value('lf_hf', timestamp)
        rmssd_val = self._get_nearest_value('rmssd', timestamp)
        quality_val = self._get_nearest_value('signal_quality', timestamp)

        return [
            f"{timestamp:.2f}",
            f"{rr_val:.0f}",
            f"{rr_valid}",
            f"{bpm:.0f}" if bpm else "",
            quality_val if quality_val is not None else "",
            f"{sdnn_val:.1f}" if sdnn_val is not None else "",
            f"{stress_val:.0f}" if stress_val is not None else "",
            f"{lfhf_val:.2f}" if lfhf_val is not None else "",
            f"{rmssd_val:.1f}" if rmssd_val is not None else ""
        ]

    def _get_timestamp(self, index: int) -> float:
        """Получить временную метку"""
        if index < len(self.session_data['rr_timestamps']):
            return self.session_data['rr_timestamps'][index][1]
        return 0

    def _get_rr_valid(self, index: int) -> int:
        """Получить флаг валидности RR"""
        if index < len(self.session_data['rr_valid']):
            return self.session_data['rr_valid'][index][1]
        return 1

    def _calculate_bpm(self, rr_val: float) -> float:
        """Рассчитать ЧСС"""
        return 60000 / rr_val if rr_val > 0 else 0

    def _get_nearest_value(self, metric: str, target_time: float, max_diff: float = 2.0) -> Optional[Any]:
        """Получить ближайшее значение метрики по времени"""
        if metric not in self.session_data or not self.session_data[metric]:
            return None

        nearest = None
        min_diff = float('inf')

        for t, v in self.session_data[metric]:
            diff = abs(t - target_time)
            if diff < min_diff and diff < max_diff:
                min_diff = diff
                nearest = v

        return nearest

    def show_post_analysis(self):
        """Показать окно пост-анализа записанных данных"""
        if not self.session_data['bpm']:
            print("⚠️ Нет данных для анализа")
            return

        print("📊 Открытие окна пост-анализа...")

        # Закрыть предыдущее окно, если оно открыто
        if self.post_analysis_window and plt.fignum_exists(self.post_analysis_window.number):
            plt.close(self.post_analysis_window)

        # Создаем новое окно для пост-анализа
        self.post_analysis_window = plt.figure(figsize=(14, 10), facecolor='#0d1117')
        self.post_analysis_window.suptitle('Пост-анализ записи', color='white', fontsize=16, fontweight='bold')

        # График 1: ЧСС за сессию
        ax1 = plt.subplot(311)
        if self.session_data['bpm']:
            timestamps, bpm_values = zip(*self.session_data['bpm'])
            ax1.plot(timestamps, bpm_values, '#58a6ff', linewidth=2, alpha=0.8)
            ax1.fill_between(timestamps, bpm_values, alpha=0.2, color='#58a6ff')
            ax1.set_ylabel('ЧСС (уд/мин)', color='white', fontsize=12)
            ax1.set_title('ЧСС за сессию', color='white', fontsize=14)
            ax1.grid(True, alpha=0.2, color='#30363d')
            ax1.set_facecolor('#161b22')
            ax1.tick_params(colors='white')

        # График 2: RR интервалы с артефактами
        ax2 = plt.subplot(312)
        if self.session_data['rr_intervals']:
            timestamps_rr, rr_values = zip(*self.session_data['rr_intervals'])

            # Получаем флаги валидности
            rr_valid = []
            if self.session_data['rr_valid']:
                _, valid_flags = zip(*self.session_data['rr_valid'])
                rr_valid = valid_flags

            if rr_valid and len(rr_valid) == len(rr_values):
                # Разделяем валидные и невалидные RR
                valid_x = [t for t, v in zip(timestamps_rr, rr_valid) if v]
                valid_y = [v for t, v in zip(timestamps_rr, rr_values) if t in valid_x]

                invalid_x = [t for t, v in zip(timestamps_rr, rr_valid) if not v]
                invalid_y = [v for t, v in zip(timestamps_rr, rr_values) if t in invalid_x]

                # Рисуем валидные RR
                ax2.plot(valid_x, valid_y, '#ff7b72', linewidth=2, alpha=0.8, label='Валидные RR')

                # Рисуем артефакты
                if invalid_x:
                    ax2.scatter(invalid_x, invalid_y, c='#ff6b6b', s=40, alpha=0.9,
                              edgecolors='white', linewidths=1, marker='x', label='Артефакты')
            else:
                # Если нет информации о валидности, рисуем все точки
                ax2.plot(timestamps_rr, rr_values, '#ff7b72', linewidth=2, alpha=0.8, label='RR интервалы')

            ax2.set_ylabel('RR (мс)', color='white', fontsize=12)
            ax2.set_title('RR интервалы с пометкой артефактов', color='white', fontsize=14)
            ax2.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='white')
            ax2.grid(True, alpha=0.2, color='#30363d')
            ax2.set_facecolor('#161b22')
            ax2.tick_params(colors='white')

        # График 3: SDNN за сессию
        ax3 = plt.subplot(313)
        if self.session_data['sdnn']:
            timestamps_sdnn, sdnn_values = zip(*self.session_data['sdnn'])
            ax3.plot(timestamps_sdnn, sdnn_values, '#3fb950', linewidth=2, alpha=0.8)
            ax3.set_ylabel('SDNN (мс)', color='white', fontsize=12)
            ax3.set_xlabel('Время (сек)', color='white', fontsize=12)
            ax3.set_title('SDNN за сессию', color='white', fontsize=14)
            ax3.grid(True, alpha=0.2, color='#30363d')
            ax3.set_facecolor('#161b22')
            ax3.tick_params(colors='white')

        plt.tight_layout()

        # Статистика сессии
        if self.session_data['bpm']:
            _, bpm_vals = zip(*self.session_data['bpm'])
            avg_bpm = np.mean(bpm_vals) if bpm_vals else 0
            max_bpm = np.max(bpm_vals) if bpm_vals else 0
            min_bpm = np.min(bpm_vals) if bpm_vals else 0

            print("\n" + "=" * 60)
            print("📊 СТАТИСТИКА СЕССИИ")
            print("=" * 60)
            print(f"📈 Количество точек ЧСС: {len(self.session_data['bpm'])}")
            print(f"📈 Количество RR интервалов: {len(self.session_data['rr_intervals'])}")
            print(f"💓 Средняя ЧСС: {avg_bpm:.1f} уд/мин")
            print(f"📊 Диапазон ЧСС: {min_bpm:.0f}-{max_bpm:.0f} уд/мин")

            if self.session_data['sdnn']:
                _, sdnn_vals = zip(*self.session_data['sdnn'])
                avg_sdnn = np.mean(sdnn_vals) if sdnn_vals else 0
                print(f"📈 Средний SDNN: {avg_sdnn:.1f} мс")

            print("=" * 60)

        # Показать окно
        plt.show(block=False)
        print("✅ Окно пост-анализа открыто")