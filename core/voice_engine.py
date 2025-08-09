import os
import threading
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Set
import simpleaudio as sa

class VoiceEngine:
    def __init__(self, config: dict):
        self._setup_logging()
        self.sounds_root = Path(config.get('sounds_path', ''))
        self._validate_paths()
        
        self._current_play_obj: Optional[sa.PlayObject] = None
        self._playback_lock = threading.RLock()
        self._loaded_sounds: Dict[str, Path] = {}
        self._preload_sounds()
        
    def _setup_logging(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
    def _validate_paths(self):
        if not self.sounds_root.exists():
            self.logger.critical(f"Папка с звуками не найдена...: {self.sounds_root}")
            raise FileNotFoundError(f"Папка со звуками не найдена...: {self.sounds_root}")
        
    def _preload_sounds(self):
        try:
            sound_files = set()
            for ext in ['.wav', '.mp3', '.wave']:
                sound_files.update(self.sounds_root.rglob(f'*{ext}'))
            
            for file in sound_files:
                sound_id = str(file.relative_to(self.sounds_root)).replace("\\", "/")[:-4]
                self._loaded_sounds[sound_id] = file
                self.logger.debug(f"Загружен звук: {sound_id}")
            self.logger.info(f"Загружено {len(self._loaded_sounds)} звуков")
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке звуков: {e}")
            raise
    def play(self, sound_id: str, blocking: bool = False, timeout: float = 5.0) -> bool:
        with self._playback_lock:
            if sound_id not in self._loaded_sounds:
                self.logger.error(f"Звук не найден: {sound_id}")
                return False
            try:
                self._stop_current()
                wave_object = sa.WaveObject.from_wave_file(str(self._loaded_sounds[sound_id]))
                self._current_play_obj = wave_object.play()
                self.logger.info(f"Звук {sound_id} играет")
                
                if blocking:
                    return self._wait_for_end(timeout)
                return True
            except Exception as e:
                self.logger.error(f"Ошибка при воспроизведении звука {sound_id}: {e}")
                return False
            
    def _stop_current(self):
        if self._current_play_obj and self._current_play_obj.is_playing():
            self.logger.debug(f"Останавливаем текущий звук...")
            self._current_play_obj.stop()
            self._current_play_obj = None
            
    def _wait_for_end(self, timeout: float) -> bool:
        start = time.time()
        while self.is_playing():
            if time.time() - start > timeout:
                self.logger.warning(f"Таймаут воспроизведения ({timeout}) сек)")
                self._stop_current()
                return False
            time.sleep(0.05)
        return True
    
    def is_playing(self) -> bool:
        with self._playback_lock:
            return bool(
                self._current_play_obj and
                self._current_play_obj.is_playing()
            )
            
    def stop_all(self):
        with self._playback_lock:
            self._stop_current()
            self.logger.info("Звуков больше нет!")
            
    def get_loaded_sounds(self) -> Set[str]:
        return set(self.get_loaded_sounds.keys())
    
    def play_blocking(self, sound_id: str, timeout: float = 5.0) -> bool:
        return self.play(sound_id, blocking=True, timeout=timeout)