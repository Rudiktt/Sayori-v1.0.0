import logging
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import pythoncom
import time
from typing import Optional, Tuple

class AudioController:
    def __init__(self, max_retries: int = 3, min_volume: int  = 0, max_volume: int = 100):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_retries = max(max_retries, 1)
        self.min_volume = min_volume
        self.max_volume = max_volume
        self.volume_interface = None
        self._initialize()

    def _initialize(self):
        #Инициализация с повторными попытками
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
                current_vol = self._safe_get_volume()
                self.logger.info(f"Аудио интерфейс инициализирован: {current_vol}%")
                return
                
            except Exception as e:
                self.logger.warning(f"Попытка {attempt}/{self.max_retries} не удалась: {str(e)}")
                time.sleep(1)
                
        self.logger.error("Не удалось инициализировать аудио интерфейс!")
        raise RuntimeError("Не удалось инициализировать аудио интерфейс!")

    def _safe_call(self, func, *args, default=None):
        """Безопасный вызов методов COM с переподключением"""
        try:
            if not self.volume_interface:
                self._initialize()
            return func(*args)
        except Exception as e:
            self.logger.error(f"Ошибка вызова {func.__name__}: {e}")
            self._initialize()  # Пытаемся восстановить соединение
            return default
        
    def _safe_get_volume(self) -> int:
        return self._safe_call(
            lambda: int(self.volume_interface.GetMasterVolumeLevelScalar() * 100),
            default=0
        )

    def set_volume(self, percent: int, smooth: bool = False, step: int = 5) -> bool:
        percent = max(self.min_volume, min(self.max_volume, percent))
        current = self._safe_get_volume()
        
        if smooth and abs(percent - current) > step:
            return self._fade_volume(current, percent, step)
        return self._safe_call(
            self.volume_interface.SetMasterVolumeLevelScalar,
            percent / 100.0, None,
            default=False
        )
        
    def _fade_volume(self, current: int, target: int, step: int) -> bool:
        step = abs(step) * (1 if target > current else -1)
        for vol in range(current, target, step):
            if not self._safe_call(
                self.volume_interface.SetMasterVolumeLevelScalar,
                vol / 100.0, None,
                default=False
            ):
                return False
            time.sleep(0.05)
        return True

    def get_volume(self) -> int:
        vol = self._safe_get_volume()
        return max(self.min_volume, min(self.max_volume, vol))

    def mute(self) -> int:
        prev_vol = self._safe_get_volume()
        success = self._safe_call(
            self.volume_interface.SetMute, 1, None,
            default=False
        )
        return (success, prev_vol if success else None)

    def unmute(self, restore_volume: Optional[int] = None) -> bool:
        if restore_volume is not None:
            self.set_volume(restore_volume)
            return self._safe_call(
                self.volume_interface.SetMute, 0, None,
                default=False
            )

    def toggle_mute(self) -> tuple[bool, Optional[int]]:
        is_muted = self._safe_call(
            self.volume_interface.GetMute,
            default=True
        )
        if is_muted:
            return (self.unmute(), None)
        else:
            return self.mute()
        
    def get_volume_range(self) -> Tuple[int, int]:
        return (self.min_volume, self.max_volume)

    def __del__(self):
        try:
            if hasattr(self, 'volume_interface') and self.volume_interface:
                self.volume_interface.Release()
            pythoncom.CoUninitialize()
        except Exception as e:
            self.logger.error(f"Ошибка при завершении: {e}")