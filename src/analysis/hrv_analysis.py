"""Анализ ВСР"""
import numpy as np
from scipy import signal as sp_signal
from typing import List
from scipy.interpolate import interp1d


class HRVAnalyzer:
    """Анализатор вариабельности сердечного ритма"""

    @staticmethod
    def calculate_sdnn(rr_intervals: List[float]) -> float:
        """Среднеквадратичное отклонение RR интервалов"""
        if len(rr_intervals) < 2:
            return 0

        try:
            rr_array = np.array(rr_intervals, dtype=np.float32)
            sdnn_val = np.std(rr_array, ddof=1)

            # Ограничение физиологических границ
            return np.clip(sdnn_val, 10, 300)
        except:
            return 0

    @staticmethod
    def calculate_stress_index(rr_intervals: List[float], min_rr_count: int = 30) -> float:
        """Индекс напряжения по Баевскому"""
        if len(rr_intervals) < min_rr_count:
            return 0

        try:
            rr_array = np.array(rr_intervals, dtype=np.float32)

            # Гистограмма для нахождения моды
            hist, bin_edges = np.histogram(rr_array, bins=20)
            mode_idx = np.argmax(hist)
            Mo = (bin_edges[mode_idx] + bin_edges[mode_idx + 1]) / 2

            # Амплитуда моды
            bin_width = bin_edges[1] - bin_edges[0]
            mode_start = bin_edges[mode_idx]
            mode_end = bin_edges[mode_idx + 1]
            mode_count = np.sum((rr_array >= mode_start) & (rr_array < mode_end))
            AMo = (mode_count / len(rr_array)) * 100

            # Вариационный размах
            ΔX = np.max(rr_array) - np.min(rr_array)

            # Защита от деления на ноль
            if ΔX < 20:
                ΔX = 20
            if Mo < 300:
                Mo = 300

            SI = AMo / (2.0 * Mo * ΔX / 1000.0)

            return np.clip(SI, 10, 400)

        except Exception:
            return 0

    @staticmethod
    def calculate_rmssd(rr_intervals: List[float]) -> float:
        """RMSSD - квадратный корень из среднего квадрата разностей"""
        if len(rr_intervals) < 2:
            return 0

        try:
            rr_array = np.array(rr_intervals, dtype=np.float32)
            differences = np.diff(rr_array)
            rmssd_val = np.sqrt(np.mean(differences ** 2))
            return min(rmssd_val, 200.0)
        except:
            return 0

    @staticmethod
    def get_statistics(rr_intervals: List[float]) -> dict:
        """Базовая статистика RR интервалов"""
        if not rr_intervals:
            return {
                'mean': 0,
                'min': 0,
                'max': 0,
                'range': 0,
                'count': 0
            }

        rr_array = np.array(rr_intervals)

        return {
            'mean': float(np.mean(rr_array)),
            'min': float(np.min(rr_array)),
            'max': float(np.max(rr_array)),
            'range': float(np.max(rr_array) - np.min(rr_array)),
            'count': len(rr_array)
        }

    @staticmethod
    def calculate_spectrum(rr_intervals: List[float], min_rr_for_spectrum: int = 20) -> float:
        """Спектральный анализ LF/HF

        Args:
            rr_intervals: Список RR интервалов в миллисекундах
            min_rr_for_spectrum: Минимальное количество RR для анализа

        Returns:
            LF/HF соотношение
        """
        if len(rr_intervals) < min_rr_for_spectrum:
            return 1.0

        try:
            # Конвертируем RR интервалы в секунды (как в вашем коде)
            rr_array = np.array(rr_intervals, dtype=np.float64) / 1000.0

            # Создаем временную ось
            t = np.cumsum(rr_array)
            t -= t[0]  # Начинаем с 0

            # Нужна достаточно длинная запись
            if t[-1] < 10:  # Меньше 10 секунд
                return 1.0

            # Передискретизация до 4 Гц (как в вашем коде)
            fs = 4.0
            t_new = np.arange(0, t[-1], 1.0 / fs)

            if len(t_new) < 64:  # Слишком мало точек
                return 1.0

            # Интерполяция
            rr_new = np.interp(t_new, t, rr_array)

            # Расчет PSD методом Велча (как в вашем коде)
            freqs, psd = sp_signal.welch(rr_new, fs=fs, nperseg=min(256, len(rr_new)))

            # Определение диапазонов (как в вашем коде)
            lf_mask = (freqs >= 0.04) & (freqs <= 0.15)   # Low frequency: 0.04-0.15 Гц
            hf_mask = (freqs >= 0.15) & (freqs <= 0.40)   # High frequency: 0.15-0.40 Гц

            if np.sum(lf_mask) == 0 or np.sum(hf_mask) == 0:
                return 1.0

            # Интеграция мощности в диапазонах (как в вашем коде)
            lf_power = np.trapz(psd[lf_mask], freqs[lf_mask])
            hf_power = np.trapz(psd[hf_mask], freqs[hf_mask])

            if hf_power > 0:
                ratio = lf_power / hf_power
                # Ограничиваем физиологически разумными значениями (как в вашем коде)
                if ratio < 0.1:
                    return 0.1
                elif ratio > 5.0:
                    return 5.0
                return float(ratio)

            return 1.0

        except Exception as e:
            print(f"Ошибка спектрального анализа: {e}")
            return 1.0