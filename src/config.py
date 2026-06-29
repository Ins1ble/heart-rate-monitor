"""Конфигурационные параметры приложения"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class RecordingState(Enum):
    IDLE = "IDLE"
    RECORDING = "RECORDING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


@dataclass
class HRVConfig:
    """Конфигурация анализа ВСР в кардиоциклах"""
    window_rr_count: int = 30
    min_rr_for_sdnn: int = 5
    min_rr_for_stress: int = 30
    min_rr_for_spectrum: int = 20
    min_rr_for_rmssd: int = 2


@dataclass
class AppConfig:
    """Конфигурация приложения"""
    port: str = 'COM6'  # Порт по умолчанию
    baud_rate: int = 115200
    max_points: int = 250
    update_interval: int = 50
    stress_calc_interval: float = 2.0
    spectrum_calc_interval: float = 1.5  # Как в вашем коде
    auto_detect_ports: bool = True  # Автоматический поиск портов
    baud_rates: List[int] = None  # Список бодрейтов для тестирования

    def __post_init__(self):
        if self.baud_rates is None:
            self.baud_rates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]