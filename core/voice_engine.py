import logging
import time
from pathlib import Path
from typing import Dict, Optional
import simpleaudio as sa
import sys
from pathlib import Path

# Добавляем корень проекта в пути поиска модулей
sys.path.append(str(Path(__file__).parent.parent))
import config

class VoiceEngine:
    def __init__(self, config: dict):
        """
        Инициализация голосового движка.
        
        :param config: Конфигурация из config.py
        """
        self._setup_logging()
        self.sounds_root = Path(config["paths"]["sounds"])
        self._loaded_sounds: Dict[str, Path] = {}
        self._current_play_obj: Optional[sa.PlayObject] = None
        self._preload_sounds()
        self.logger.info("Голосовой движок инициализирован")

    def _setup_logging(self):
        """Настройка системы логирования"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        
        # Вывод логов в консоль для удобства отладки
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    def _preload_sounds(self):
        """Предварительная загрузка всех звуковых файлов"""
        try:
            # Создаем папку sounds, если её нет
            self.sounds_root.mkdir(exist_ok=True, parents=True)
            
            # Ищем только .wav файлы
            sound_files = list(self.sounds_root.rglob("*.wav"))
            
            if not sound_files:
                self.logger.warning(f"В папке {self.sounds_root} не найдено .wav файлов")
                return

            for file in sound_files:
                # Создаем ID звука (относительный путь без расширения)
                sound_id = str(file.relative_to(self.sounds_root)).replace("\\", "/")[:-4]
                self._loaded_sounds[sound_id] = file
                self.logger.debug(f"Загружен звук: {sound_id}")

            self.logger.info(f"Успешно загружено {len(self._loaded_sounds)} звуков")

        except Exception as e:
            self.logger.error(f"Ошибка при загрузке звуков: {e}")
            raise

    def play(self, sound_id: str, blocking: bool = False) -> bool:
        """
        Воспроизведение звука
        
        :param sound_id: Идентификатор звука (например "system/start")
        :param blocking: Блокировать ли выполнение пока звук не закончится
        :return: Успешность воспроизведения
        """
        if sound_id not in self._loaded_sounds:
            self.logger.error(f"Звук '{sound_id}' не найден")
            return False

        try:
            self.stop()  # Останавливаем текущее воспроизведение
            
            wave_obj = sa.WaveObject.from_wave_file(str(self._loaded_sounds[sound_id]))
            self._current_play_obj = wave_obj.play()
            self.logger.info(f"Воспроизводится звук: {sound_id}")

            if blocking:
                while self.is_playing():
                    time.sleep(0.1)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения звука {sound_id}: {e}")
            return False

    def stop(self):
        """Остановка текущего воспроизведения"""
        if self._current_play_obj and self._current_play_obj.is_playing():
            self._current_play_obj.stop()
            self._current_play_obj = None
            self.logger.debug("Воспроизведение остановлено")

    def is_playing(self) -> bool:
        """Проверка, идет ли воспроизведение"""
        return self._current_play_obj is not None and self._current_play_obj.is_playing()

    def get_loaded_sounds(self) -> list:
        """Получить список загруженных звуков"""
        return list(self._loaded_sounds.keys())


if __name__ == "__main__":
    # Тестовый запуск
    print("\nТестирование VoiceEngine...")
    try:
        engine = VoiceEngine(config.config)
        print(f"Загружены звуки: {engine.get_loaded_sounds()}")
        
        # Тест воспроизведения (если есть звуки)
        if engine.get_loaded_sounds():
            test_sound = engine.get_loaded_sounds()[0]  # Берем первый доступный звук
            print(f"\nТестируем воспроизведение: {test_sound}")
            engine.play(test_sound, blocking=True)
            print("Тест завершен успешно!")
        else:
            print("Нет звуков для тестирования. Добавьте .wav файлы в папку sounds/")
            
    except Exception as e:
        print(f"Ошибка при тестировании: {e}")