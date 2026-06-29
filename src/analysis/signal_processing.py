"""Обработка сигналов PPG и RR"""
import numpy as np
from scipy import signal as sp_signal
from typing import List, Tuple, Optional
from collections import deque


class SignalProcessor:
    """Процессор сигналов PPG и RR интервалов"""

    @staticmethod
    def detect_r_peaks(ppg_signal: List[int], sampling_rate: float = 100) -> List[int]:
        """
        Детекция R-пиков в сигнале PPG

        Args:
            ppg_signal: Сырой сигнал PPG
            sampling_rate: Частота дискретизации в Гц

        Returns:
            Список позиций R-пиков в отсчетах
        """
        if len(ppg_signal) < 10:
            return []

        try:
            # Преобразование сигнала
            signal = np.array(ppg_signal, dtype=np.float32)

            # Базовый детектор на основе производной
            derivative = np.diff(signal)

            # Поиск локальных максимумов
            peaks, _ = sp_signal.find_peaks(
                signal,
                distance=sampling_rate * 0.3,  # Минимум 0.3 секунды между пиками
                prominence=np.std(signal) * 0.5,
                height=np.mean(signal) + np.std(signal) * 0.2
            )

            return peaks.tolist()

        except Exception as e:
            print(f"Ошибка детекции R-пиков: {e}")
            return []

    @staticmethod
    def calculate_rr_intervals_from_peaks(peak_positions: List[int],
                                          sampling_rate: float = 100) -> List[float]:
        """
        Расчет RR интервалов из позиций R-пиков

        Args:
            peak_positions: Позиции R-пиков в отсчетах
            sampling_rate: Частота дискретизации в Гц

        Returns:
            Список RR интервалов в миллисекундах
        """
        if len(peak_positions) < 2:
            return []

        rr_intervals = []
        for i in range(1, len(peak_positions)):
            # Разница в отсчетах -> время в мс
            rr_ms = ((peak_positions[i] - peak_positions[i - 1]) / sampling_rate) * 1000
            rr_intervals.append(rr_ms)

        return rr_intervals

    @staticmethod
    def filter_ppg_signal(raw_signal: List[int],
                          filter_type: str = 'bandpass',
                          lowcut: float = 0.5,
                          highcut: float = 8.0,
                          sampling_rate: float = 100) -> np.ndarray:
        """
        Фильтрация сигнала PPG

        Args:
            raw_signal: Сырой сигнал
            filter_type: Тип фильтра ('bandpass', 'lowpass', 'highpass')
            lowcut: Нижняя частота среза (Гц)
            highcut: Верхняя частота среза (Гц)
            sampling_rate: Частота дискретизации

        Returns:
            Отфильтрованный сигнал
        """
        if len(raw_signal) < 10:
            return np.array(raw_signal)

        try:
            signal = np.array(raw_signal, dtype=np.float32)

            if filter_type == 'bandpass':
                # Полосовой фильтр Баттерворта
                nyquist = 0.5 * sampling_rate
                low = lowcut / nyquist
                high = highcut / nyquist
                b, a = sp_signal.butter(2, [low, high], btype='band')
                filtered = sp_signal.filtfilt(b, a, signal)

            elif filter_type == 'lowpass':
                # ФНЧ для удаления шума
                nyquist = 0.5 * sampling_rate
                cutoff = highcut / nyquist
                b, a = sp_signal.butter(2, cutoff, btype='low')
                filtered = sp_signal.filtfilt(b, a, signal)

            elif filter_type == 'highpass':
                # ФВЧ для удаления baseline drift
                nyquist = 0.5 * sampling_rate
                cutoff = lowcut / nyquist
                b, a = sp_signal.butter(2, cutoff, btype='high')
                filtered = sp_signal.filtfilt(b, a, signal)

            else:
                filtered = signal

            return filtered

        except Exception as e:
            print(f"Ошибка фильтрации сигнала: {e}")
            return np.array(raw_signal)

    @staticmethod
    def remove_baseline_wander(signal: List[int],
                               sampling_rate: float = 100) -> np.ndarray:
        """
        Удаление baseline wander из сигнала PPG

        Args:
            signal: Входной сигнал
            sampling_rate: Частота дискретизации

        Returns:
            Сигнал без baseline wander
        """
        if len(signal) < 50:
            return np.array(signal)

        try:
            sig = np.array(signal, dtype=np.float32)

            # Метод: вычитание скользящего среднего
            window_size = int(sampling_rate * 2)  # 2 секунды
            if window_size < 5:
                window_size = 5

            # Вычисление скользящего среднего
            baseline = np.convolve(sig, np.ones(window_size) / window_size, mode='same')

            # Вычитание baseline
            corrected = sig - baseline

            return corrected

        except Exception as e:
            print(f"Ошибка удаления baseline: {e}")
            return np.array(signal)

    @staticmethod
    def normalize_signal(signal: List[int]) -> np.ndarray:
        """
        Нормализация сигнала к диапазону 0-1023

        Args:
            signal: Входной сигнал

        Returns:
            Нормализованный сигнал
        """
        if not signal:
            return np.array([])

        try:
            sig = np.array(signal, dtype=np.float32)

            # Удаление выбросов
            q25, q75 = np.percentile(sig, [25, 75])
            iqr = q75 - q25
            lower_bound = q25 - 1.5 * iqr
            upper_bound = q75 + 1.5 * iqr

            # Мягкое ограничение
            sig = np.clip(sig, lower_bound, upper_bound)

            # Min-max нормализация
            sig_min = np.min(sig)
            sig_max = np.max(sig)

            if sig_max - sig_min > 0:
                normalized = (sig - sig_min) / (sig_max - sig_min) * 1023
            else:
                normalized = sig

            return normalized.astype(np.int32)

        except Exception as e:
            print(f"Ошибка нормализации: {e}")
            return np.array(signal)

    @staticmethod
    def calculate_signal_quality(signal: List[int]) -> float:
        """
        Оценка качества сигнала (0-1, где 1 - лучшее качество)

        Args:
            signal: Сигнал для оценки

        Returns:
            Оценка качества от 0 до 1
        """
        if len(signal) < 10:
            return 0.0

        try:
            sig = np.array(signal, dtype=np.float32)

            # 1. Отношение сигнал/шум (SNR)
            mean_val = np.mean(sig)
            std_val = np.std(sig)

            if std_val > 0:
                snr = mean_val / std_val
                snr_score = min(snr / 5.0, 1.0)  # Нормализация
            else:
                snr_score = 0.0

            # 2. Амплитуда сигнала
            amplitude = np.max(sig) - np.min(sig)
            amp_score = min(amplitude / 300.0, 1.0)

            # 3. Стабильность сигнала
            if len(signal) >= 50:
                recent_std = np.std(sig[-50:])
                overall_std = np.std(sig)
                if overall_std > 0:
                    stability = 1.0 - (recent_std / overall_std)
                    stability_score = max(min(stability, 1.0), 0.0)
                else:
                    stability_score = 0.0
            else:
                stability_score = 0.5

            # Общая оценка качества
            quality_score = (snr_score * 0.4 + amp_score * 0.4 + stability_score * 0.2)

            return max(min(quality_score, 1.0), 0.0)

        except Exception as e:
            print(f"Ошибка оценки качества сигнала: {e}")
            return 0.0