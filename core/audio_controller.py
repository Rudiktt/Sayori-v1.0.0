import logging
import pythoncom
import time
from typing import Optional, Tuple
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import platform
import psutil
from threading import Thread

class AudioController:
    def __init__(self, config: dict, max_retries: int = 3):
        """
        Улучшенный контроллер громкости с плавным изменением.
        
        :param config: Конфигурация из config.py (раздел 'audio')
        :param max_retries: Максимальное количество попыток инициализации
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config.get("audio", {})
        self.max_retries = max(1, max_retries)
        self.min_volume = self.config.get("min_volume", 0)
        self.max_volume = self.config.get("max_volume", 100)
        self.default_volume = self.config.get("default_volume", 50)
        self.volume_step = self.config.get("volume_step", 10)
        self.volume_interface = None
        self._current_volume = self.default_volume
        self._prev_unmuted_volume = self.default_volume
        self._smooth_thread = None
        self._initialize()
        self.logger.info(f"AudioController готов. Текущая громкость: {self._current_volume}%")

    def _initialize(self) -> bool:
        """Инициализация интерфейса громкости с повторными попытками"""
        # Проверка ОС: только Windows
        if platform.system() != "Windows":
            self.logger.error("AudioController поддерживает только Windows")
            return False

        for attempt in range(1, self.max_retries + 1):
            try:
                pythoncom.CoInitialize()
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_,
                    CLSCTX_ALL,
                    None
                )
                self.volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                self._current_volume = self._get_volume()
                self._prev_unmuted_volume = self._current_volume
                self.logger.info(f"Аудиоинтерфейс инициализирован (попытка {attempt})")
                return True
            except Exception as e:
                self.logger.warning(f"Попытка {attempt}/{self.max_retries} не удалась: {str(e)}")
                time.sleep(1)
                
        self.logger.error("Не удалось инициализировать аудиоинтерфейс!")
        return False

    def _get_volume(self) -> int:
        """Получение текущей громкости с обработкой ошибок"""
        if not self.volume_interface:
            return self._current_volume

        try:
            vol = self.volume_interface.GetMasterVolumeLevelScalar()
            return max(self.min_volume, min(self.max_volume, int(vol * 100)))
        except Exception as e:
            self.logger.error(f"Ошибка получения громкости: {e}")
            return self._current_volume

    def set_volume(self, percent: int, smooth: bool = False, duration: float = 1.0) -> bool:
        """
        Установка громкости с возможностью плавного изменения
        
        :param percent: Уровень громкости (0-100)
        :param smooth: Плавное изменение
        :param duration: Длительность изменения в секундах
        :return: Успешность операции
        """
        percent = max(self.min_volume, min(self.max_volume, percent))
        
        if not self.volume_interface:
            self.logger.warning("Интерфейс громкости не инициализирован!")
            return False

        # Остановка предыдущего плавного изменения
        if self._smooth_thread and self._smooth_thread.is_alive():
            self._smooth_thread.join(timeout=0.1)
            
        if smooth and duration > 0:
            # Запуск в отдельном потоке для неблокирующего выполнения
            self._smooth_thread = Thread(
                target=self._set_volume_smoothly,
                args=(percent, duration),
                daemon=True
            )
            self._smooth_thread.start()
            return True
        else:
            return self._set_volume_internal(percent)

    def _set_volume_smoothly(self, target_volume: int, duration: float):
        """Плавное изменение громкости"""
        current_vol = self._get_volume()
        steps = int(duration / 0.05)  # Шаги по 50мс
        if steps < 1:
            steps = 1
            
        step_value = (target_volume - current_vol) / steps
        for i in range(steps):
            new_vol = int(current_vol + step_value * (i + 1))
            self._set_volume_internal(new_vol)
            time.sleep(0.05)
            
        # Финализация точного значения
        self._set_volume_internal(target_volume)

    def _set_volume_internal(self, percent: int) -> bool:
        """Внутренняя установка громкости без проверок"""
        try:
            self.volume_interface.SetMasterVolumeLevelScalar(percent / 100.0, None)
            self._current_volume = percent
            self.logger.debug(f"Громкость установлена на {percent}%")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка установки громкости: {e}")
            return False

    def volume_up(self, step: Optional[int] = None) -> int:
        """Увеличить громкость с указанным шагом"""
        step_val = step or self.volume_step
        new_vol = min(self.max_volume, self._get_volume() + step_val)
        self.set_volume(new_vol)
        return new_vol

    def volume_down(self, step: Optional[int] = None) -> int:
        """Уменьшить громкость с указанным шагом"""
        step_val = step or self.volume_step
        new_vol = max(self.min_volume, self._get_volume() - step_val)
        self.set_volume(new_vol)
        return new_vol

    def mute(self) -> Tuple[bool, Optional[int]]:
        """Отключить звук"""
        if not self.volume_interface:
            return (False, None)

        try:
            self._prev_unmuted_volume = self._get_volume()
            self.volume_interface.SetMute(1, None)
            self.logger.info("Звук отключен")
            return (True, self._prev_unmuted_volume)
        except Exception as e:
            self.logger.error(f"Ошибка отключения звука: {e}")
            return (False, None)

    def unmute(self, restore_volume: Optional[int] = None) -> bool:
        """Включить звук"""
        if not self.volume_interface:
            return False

        try:
            self.volume_interface.SetMute(0, None)
            if restore_volume is not None:
                self.set_volume(restore_volume)
            self.logger.info("Звук включен")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка включения звука: {e}")
            return False

    def toggle_mute(self) -> Tuple[bool, Optional[int]]:
        """Переключить режим 'Mute'"""
        if not self.volume_interface:
            return (False, None)

        try:
            is_muted = self.volume_interface.GetMute()
            if is_muted:
                success = self.unmute(self._prev_unmuted_volume)
                return (success, None)
            else:
                return self.mute()
        except Exception as e:
            self.logger.error(f"Ошибка переключения звука: {e}")
            return (False, None)

    def get_current_volume(self) -> int:
        """Получить текущий уровень громкости"""
        return self._current_volume

    def __del__(self):
        """Корректное освобождение ресурсов"""
        try:
            if self.volume_interface:
                self.volume_interface.Release()
            pythoncom.CoUninitialize()
        except Exception as e:
            self.logger.error(f"Ошибка при завершении: {e}")

if __name__ == "__main__":
    # Расширенное тестирование
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=== Расширенное тестирование AudioController ===")
    
    # Тестовый конфиг
    test_config = {
        "audio": {
            "min_volume": 0,
            "max_volume": 100,
            "default_volume": 50,
            "volume_step": 5
        }
    }
    
    controller = AudioController(test_config)
    print(f"\nТекущая громкость: {controller.get_current_volume()}%")
    
    print("\nТест плавного увеличения громкости (2 секунды):")
    controller.set_volume(80, smooth=True, duration=2.0)
    time.sleep(2.5)
    print(f"Результат: {controller.get_current_volume()}%")
    
    print("\nТест плавного уменьшения громкости (1.5 секунды):")
    controller.set_volume(30, smooth=True, duration=1.5)
    time.sleep(2)
    print(f"Результат: {controller.get_current_volume()}%")
    
    print("\nТест увеличения громкости с шагом по умолчанию:")
    controller.volume_up()
    print(f"Результат: {controller.get_current_volume()}%")
    
    print("\nТест уменьшения громкости с шагом по умолчанию:")
    controller.volume_down()
    print(f"Результат: {controller.get_current_volume()}%")
    
    print("\nТест Mute/Unmute:")
    print("Отключаем звук...")
    success, prev_vol = controller.mute()
    print(f"Результат: {'Успешно' if success else 'Ошибка'}, Предыдущая громкость: {prev_vol}%")
    
    time.sleep(1)
    print("Включаем звук...")
    success = controller.unmute(prev_vol)
    print(f"Результат: {'Успешно' if success else 'Ошибка'}")
    print(f"Текущая громкость: {controller.get_current_volume()}%")
    
    print("\nТест завершен!")