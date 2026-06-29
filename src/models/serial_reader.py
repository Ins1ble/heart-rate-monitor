"""
Чтение данных с последовательного порта
"""
import serial
import serial.tools.list_ports
import time
from typing import Optional, List, Tuple, Dict
import traceback
from dataclasses import dataclass


@dataclass
class SerialConfig:
    """Конфигурация последовательного порта"""
    port: str = 'COM6'
    baud_rate: int = 115200
    timeout: float = 0.01
    bytesize: int = 8
    parity: str = 'N'
    stopbits: int = 1


class SerialPortScanner:
    """Сканер доступных последовательных портов"""

    @staticmethod
    def get_available_ports() -> List[Dict[str, str]]:
        """
        Получение списка доступных COM портов

        Returns:
            Список словарей с информацией о портах
        """
        ports = []
        try:
            available_ports = serial.tools.list_ports.comports()

            for port_info in available_ports:
                port_data = {
                    'port': port_info.device,
                    'description': port_info.description,
                    'manufacturer': port_info.manufacturer if port_info.manufacturer else 'Unknown',
                    'hwid': port_info.hwid,
                }
                ports.append(port_data)

            # Сортируем порты по номеру (COM1, COM2, ...)
            ports.sort(key=lambda x: x['port'])

        except Exception as e:
            print(f"⚠️ Ошибка при сканировании портов: {e}")

        return ports


class SerialReader:
    """Чтение данных с последовательного порта Arduino"""

    def __init__(self, config: SerialConfig):
        self.config = config
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        self.last_read_time = 0

    def scan_ports(self) -> List[Dict[str, str]]:
        """Сканирование доступных портов"""
        print("🔍 Сканирование доступных COM портов...")
        ports = SerialPortScanner.get_available_ports()

        if not ports:
            print("⚠️ Не найдено ни одного COM порта")
        else:
            print(f"✅ Найдено {len(ports)} портов:")
            for i, port_info in enumerate(ports, 1):
                print(f"  {i}. {port_info['port']} - {port_info['description']}")

        return ports

    def connect(self, port_name: str = None, baud_rate: int = None) -> bool:
        """Подключение к последовательному порту"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.disconnect()

            # Используем переданные параметры или значения по умолчанию
            port_to_use = port_name or self.config.port
            baud_to_use = baud_rate or self.config.baud_rate

            print(f"🔌 Попытка подключения к {port_to_use} на {baud_to_use} бод...")

            self.serial_port = serial.Serial(
                port=port_to_use,
                baudrate=baud_to_use,
                bytesize=self.config.bytesize,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                timeout=self.config.timeout
            )

            time.sleep(2.0)  # Даем время на инициализацию
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            self.is_connected = True
            self.last_read_time = time.time()
            self.config.port = port_to_use  # Обновляем конфигурацию

            print(f"✅ Успешно подключено к {port_to_use} на {baud_to_use} бод")
            return True

        except Exception as e:
            print(f"❌ Ошибка подключения к {port_to_use}: {e}")
            self.serial_port = None
            self.is_connected = False
            return False

    def disconnect(self) -> bool:
        """Отключение от порта"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_port = None
            self.is_connected = False
            print("📴 Порт отключен")
            return True
        except Exception as e:
            print(f"❌ Ошибка при отключении порта: {e}")
            return False

    def read_data(self) -> List[Tuple[str, float, float]]:
        """
        Чтение данных с порта

        Returns:
            Список кортежей (тип_данных, значение, временная_метка)
        """
        if not self.serial_port or not self.serial_port.is_open:
            return []

        try:
            data_points = []

            # Проверяем сколько данных доступно
            bytes_to_read = self.serial_port.in_waiting
            if bytes_to_read == 0:
                return data_points

            # Читаем все доступные данные
            raw_bytes = self.serial_port.read(bytes_to_read)

            # Декодируем и разбираем строки
            try:
                raw_text = raw_bytes.decode('ascii', errors='ignore')
            except UnicodeDecodeError:
                raw_text = raw_bytes.decode('utf-8', errors='ignore')

            lines = raw_text.strip().split('\n')
            current_time = time.time()
            self.last_read_time = current_time

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Обработка RR интервалов
                if line.startswith('RR:'):
                    try:
                        rr_value = int(line[3:])
                        if 200 < rr_value < 2000:  # Физиологические границы
                            data_points.append(('RR', rr_value, current_time))
                    except ValueError:
                        continue

                # Обработка сигнала PPG
                elif line.isdigit() or (line.startswith('-') and line[1:].isdigit()):
                    try:
                        signal_value = int(line)
                        if 0 <= signal_value <= 1023:
                            data_points.append(('PPG', signal_value, current_time))
                    except ValueError:
                        continue

                # Обработка сигнала PPG с запятой
                elif ',' in line:
                    try:
                        parts = line.split(',')
                        if len(parts) >= 1:
                            signal_value = int(parts[0])
                            if 0 <= signal_value <= 1023:
                                data_points.append(('PPG', signal_value, current_time))
                    except ValueError:
                        continue

            return data_points

        except Exception as e:
            print(f"❌ Ошибка чтения с порта: {e}")
            return []

    def send_command(self, command: str) -> bool:
        """Отправка команды на Arduino"""
        if not self.serial_port or not self.serial_port.is_open:
            return False

        try:
            self.serial_port.write(f"{command}\n".encode())
            self.serial_port.flush()
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки команды: {e}")
            return False