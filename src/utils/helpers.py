"""
Вспомогательные функции
"""
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import pickle
import csv
import os


def save_session_data(data: Dict[str, Any], filename: str) -> bool:
    """
    Сохранение данных сессии в файл

    Args:
        data: Данные для сохранения
        filename: Имя файла

    Returns:
        True если успешно, False в противном случае
    """
    try:
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
        return True
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")
        return False


def load_session_data(filename: str) -> Optional[Dict[str, Any]]:
    """
    Загрузка данных сессии из файла

    Args:
        filename: Имя файла

    Returns:
        Данные или None в случае ошибки
    """
    try:
        with open(filename, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        return None


def export_to_csv(data: Dict[str, List[Tuple[float, Any]]],
                  filename: str,
                  metadata: Dict[str, Any] = None) -> bool:
    """
    Экспорт данных в CSV файл

    Args:
        data: Данные для экспорта
        filename: Имя CSV файла
        metadata: Метаданные

    Returns:
        True если успешно, False в противном случае
    """
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Запись метаданных
            if metadata:
                writer.writerow([f'# Метаданные сессии: {metadata.get("session_name", "Unknown")}'])
                writer.writerow([f'# Дата: {metadata.get("date", datetime.now().isoformat())}'])
                writer.writerow([f'# Длительность: {metadata.get("duration", 0):.1f} сек'])
                writer.writerow([])

            # Определение всех временных меток
            all_timestamps = set()
            for key in data.keys():
                if data[key]:
                    timestamps, _ = zip(*data[key])
                    all_timestamps.update(timestamps)

            # Сортировка временных меток
            sorted_timestamps = sorted(all_timestamps)

            # Заголовок
            headers = ['Time_s'] + list(data.keys())
            writer.writerow(headers)

            # Данные
            for timestamp in sorted_timestamps:
                row = [f"{timestamp:.3f}"]
                for key in data.keys():
                    # Поиск ближайшего значения для этой временной метки
                    value = None
                    if data[key]:
                        for t, v in data[key]:
                            if abs(t - timestamp) < 0.01:  # Допуск 10 мс
                                value = v
                                break

                    if value is not None:
                        if isinstance(value, float):
                            row.append(f"{value:.3f}")
                        else:
                            row.append(str(value))
                    else:
                        row.append("")

                writer.writerow(row)

        print(f"✅ Данные экспортированы в {filename}")
        return True

    except Exception as e:
        print(f"❌ Ошибка экспорта в CSV: {e}")
        return False


def calculate_moving_average(data: List[float], window_size: int = 5) -> List[float]:
    """
    Вычисление скользящего среднего

    Args:
        data: Входные данные
        window_size: Размер окна

    Returns:
        Список скользящих средних
    """
    if len(data) < window_size:
        return data

    return [np.mean(data[max(0, i - window_size + 1):i + 1])
            for i in range(len(data))]


def interpolate_missing_values(data: List[float],
                               missing_indices: List[int]) -> List[float]:
    """
    Интерполяция пропущенных значений

    Args:
        data: Исходные данные с пропусками
        missing_indices: Индексы пропущенных значений

    Returns:
        Данные с интерполированными значениями
    """
    if not missing_indices:
        return data.copy()

    result = data.copy()

    for idx in missing_indices:
        if 0 < idx < len(data) - 1:
            # Линейная интерполяция между соседними значениями
            result[idx] = (result[idx - 1] + result[idx + 1]) / 2

    return result


def find_outliers(data: List[float],
                  method: str = 'iqr',
                  threshold: float = 1.5) -> Tuple[List[int], List[float]]:
    """
    Поиск выбросов в данных

    Args:
        data: Входные данные
        method: Метод обнаружения ('iqr' или 'zscore')
        threshold: Пороговое значение

    Returns:
        Кортеж (индексы_выбросов, значения_выбросов)
    """
    if len(data) < 3:
        return [], []

    data_array = np.array(data)

    if method == 'iqr':
        # Метод межквартильного размаха
        q25, q75 = np.percentile(data_array, [25, 75])
        iqr = q75 - q25
        lower_bound = q25 - threshold * iqr
        upper_bound = q75 + threshold * iqr

        outlier_indices = np.where((data_array < lower_bound) | (data_array > upper_bound))[0]

    elif method == 'zscore':
        # Метод Z-score
        mean = np.mean(data_array)
        std = np.std(data_array)

        if std > 0:
            z_scores = np.abs((data_array - mean) / std)
            outlier_indices = np.where(z_scores > threshold)[0]
        else:
            outlier_indices = []

    else:
        outlier_indices = []

    outlier_values = [data[i] for i in outlier_indices]

    return outlier_indices.tolist(), outlier_values


def calculate_confidence_interval(data: List[float],
                                  confidence: float = 0.95) -> Tuple[float, float]:
    """
    Расчет доверительного интервала

    Args:
        data: Входные данные
        confidence: Уровень доверия (0.95 для 95%)

    Returns:
        Кортеж (нижняя_граница, верхняя_граница)
    """
    if len(data) < 2:
        return 0, 0

    try:
        from scipy import stats

        data_array = np.array(data)
        mean = np.mean(data_array)
        std_err = stats.sem(data_array)

        # Степени свободы
        dof = len(data_array) - 1

        # Критическое значение t-распределения
        t_crit = stats.t.ppf((1 + confidence) / 2, dof)

        margin_of_error = t_crit * std_err

        return float(mean - margin_of_error), float(mean + margin_of_error)

    except Exception:
        # Простой метод, если scipy недоступен
        mean = np.mean(data)
        std = np.std(data)

        if len(data) >= 30:
            # Для больших выборок используем Z-статистику
            z_score = 1.96  # для 95% доверительного интервала
        else:
            # Для малых выборок используем t-статистику
            z_score = 2.045  # для 95% и 30 степеней свободы

        margin_of_error = z_score * std / np.sqrt(len(data))

        return float(mean - margin_of_error), float(mean + margin_of_error)


def format_time_duration(seconds: float) -> str:
    """
    Форматирование длительности времени

    Args:
        seconds: Время в секундах

    Returns:
        Отформатированная строка
    """
    if seconds < 60:
        return f"{seconds:.1f} сек"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} мин"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} час"


def get_file_size_info(filename: str) -> Dict[str, Any]:
    """
    Получение информации о размере файла

    Args:
        filename: Имя файла

    Returns:
        Словарь с информацией о файле
    """
    try:
        if os.path.exists(filename):
            size_bytes = os.path.getsize(filename)

            # Конвертация в удобные единицы
            if size_bytes < 1024:
                size_str = f"{size_bytes} Б"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} КБ"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.2f} МБ"

            return {
                'exists': True,
                'size_bytes': size_bytes,
                'size_human': size_str,
                'modified': datetime.fromtimestamp(os.path.getmtime(filename)).isoformat()
            }
        else:
            return {'exists': False}

    except Exception as e:
        return {'exists': False, 'error': str(e)}


def create_session_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Создание сводки по сессии

    Args:
        data: Данные сессии

    Returns:
        Словарь со сводкой
    """
    summary = {
        'total_duration': 0,
        'data_points': {},
        'statistics': {}
    }

    if 'data' in data and isinstance(data['data'], dict):
        # Подсчет количества точек данных
        for key, values in data['data'].items():
            if values:
                summary['data_points'][key] = len(values)

                # Базовая статистика для числовых данных
                if values and isinstance(values[0], tuple) and len(values[0]) == 2:
                    _, vals = zip(*values)
                    if isinstance(vals[0], (int, float)):
                        vals_array = np.array(vals)
                        summary['statistics'][key] = {
                            'mean': float(np.mean(vals_array)),
                            'std': float(np.std(vals_array)),
                            'min': float(np.min(vals_array)),
                            'max': float(np.max(vals_array)),
                            'median': float(np.median(vals_array))
                        }

    if 'metadata' in data:
        summary['total_duration'] = data['metadata'].get('duration', 0)
        summary['start_time'] = data['metadata'].get('start_time')
        summary['end_time'] = data['metadata'].get('saved_at')

    return summary


def print_session_summary(summary: Dict[str, Any]):
    """
    Вывод сводки по сессии в консоль

    Args:
        summary: Сводка сессии
    """
    print("\n" + "=" * 60)
    print("📊 СВОДКА СЕССИИ")
    print("=" * 60)

    if summary.get('total_duration'):
        print(f"⏱  Длительность: {format_time_duration(summary['total_duration'])}")

    if summary.get('data_points'):
        print(f"📈 Количество точек данных:")
        for key, count in summary['data_points'].items():
            print(f"   - {key}: {count}")

    if summary.get('statistics'):
        print(f"📊 Статистика:")
        for key, stats in summary['statistics'].items():
            print(f"   {key}:")
            print(f"     Среднее: {stats['mean']:.2f}")
            print(f"     Стандартное отклонение: {stats['std']:.2f}")
            print(f"     Диапазон: {stats['min']:.2f} - {stats['max']:.2f}")

    print("=" * 60)