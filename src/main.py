"""Главный файл запуска приложения"""
import warnings
warnings.filterwarnings('ignore')

from config import AppConfig, HRVConfig
from ui.main_window import HRVMonitor


def main():
    """Основная функция запуска"""
    # Конфигурация
    app_config = AppConfig(
        port='COM6',  # Порт по умолчанию
        baud_rate=115200,
        max_points=250,
        update_interval=50
    )

    hrv_config = HRVConfig(
        window_rr_count=30,
        min_rr_for_sdnn=5,
        min_rr_for_stress=30,
        min_rr_for_spectrum=20,
        min_rr_for_rmssd=2
    )

    # Создание и запуск приложения
    try:
        app = HRVMonitor(app_config, hrv_config)
        app.run()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()