"""Фильтрация RR интервалов"""
from collections import deque
import numpy as np
from models.data_classes import RRArtifact


class RRFiltration:
    """Контекстная фильтрация RR интервалов с пометкой артефактов"""

    def __init__(self, window_size: int = 7, threshold: float = 0.3):
        self.window = deque(maxlen=window_size)
        self.threshold = threshold
        self.artifact_marker = RRArtifact(positions=[], timestamps=[], values=[])

    def validate_and_mark(self, rr_ms: float, timestamp: float, position: int) -> tuple:
        """
        Проверяет RR и возвращает (валидность, тип_артефакта)

        Returns:
            tuple: (is_valid: bool, artifact_type: str)
        """
        # Абсолютные физиологические границы
        if not 300 < rr_ms < 2000:
            self._mark_artifact(position, timestamp, rr_ms)
            return False, "abs_limit"

        if len(self.window) < 3:
            self.window.append(rr_ms)
            return True, "valid"

        median_rr = np.median(list(self.window))
        deviation = abs(rr_ms - median_rr) / median_rr

        if deviation > self.threshold:
            self._mark_artifact(position, timestamp, rr_ms)
            return False, "context_filter"

        self.window.append(rr_ms)
        return True, "valid"

    def _mark_artifact(self, position: int, timestamp: float, value: float):
        """Пометить артефакт"""
        self.artifact_marker.positions.append(position)
        self.artifact_marker.timestamps.append(timestamp)
        self.artifact_marker.values.append(value)

    def get_artifacts_in_window(self, window_size: int) -> list:
        """Возвращает артефакты в последнем окне"""
        if not self.artifact_marker.positions:
            return []

        recent_artifacts = []
        start_idx = max(0, len(self.artifact_marker.positions) - window_size)

        for i in range(start_idx, len(self.artifact_marker.positions)):
            recent_artifacts.append((
                self.artifact_marker.positions[i],
                self.artifact_marker.timestamps[i],
                self.artifact_marker.values[i]
            ))

        return recent_artifacts

    def reset(self):
        """Сброс фильтра"""
        self.window.clear()
        self.artifact_marker = RRArtifact(positions=[], timestamps=[], values=[])