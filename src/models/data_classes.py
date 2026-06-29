"""Классы данных"""
from dataclasses import dataclass
from typing import List, Tuple, Optional
from datetime import datetime


@dataclass
class RRArtifact:
    """Пометка артефактов RR интервалов"""
    positions: List[int]  # Позиции артефактов
    timestamps: List[float]  # Временные метки
    values: List[float]  # Значения артефактных RR


@dataclass
class SessionData:
    """Данные сессии записи"""
    timestamps: List[Tuple[float, float]]
    ppg_raw: List[Tuple[float, int]]
    rr_intervals: List[Tuple[float, float]]
    rr_valid: List[Tuple[float, int]]
    bpm: List[Tuple[float, int]]
    sdnn: List[Tuple[float, float]]
    stress_index: List[Tuple[float, float]]
    lf_hf: List[Tuple[float, float]]
    rmssd: List[Tuple[float, float]]
    rr_timestamps: List[Tuple[float, float]]