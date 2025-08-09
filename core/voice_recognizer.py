import speech_recognition as sr
import logging
import time
from typing import Optional, List

class VoiceRecognizer:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.recognizer = sr.Recognizer()
        
        # Настройки распознавателя
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.energy_threshold = config["audio"]["energy_threshold"]
        self.recognizer.pause_threshold = 0.8
        
        # Инициализация микрофона
        self.microphone = self._initialize_microphone()
        self._test_microphone()

    def _initialize_microphone(self) -> sr.Microphone:
        """Автоматический подбор рабочего микрофона"""
        available_mics = self._get_microphone_list()
        if not available_mics:
            raise RuntimeError("Микрофоны не обнаружены")

        # Пробуем микрофон из конфига
        for device_index in [self.config["microphone"]["device_index"], *range(len(available_mics))]:
            try:
                mic = sr.Microphone(
                    device_index=device_index,
                    sample_rate=self.config["audio"]["sample_rate"]
                )
                self.logger.info(f"Пробуем микрофон #{device_index}: {available_mics[device_index]}")
                return mic
            except Exception as e:
                self.logger.warning(f"Микрофон #{device_index} недоступен: {str(e)}")
                continue

        raise RuntimeError("Ни один микрофон не работает")

    def _get_microphone_list(self) -> List[str]:
        """Получает список микрофонов с обработкой ошибок"""
        try:
            return sr.Microphone.list_microphone_names()
        except Exception as e:
            self.logger.error(f"Ошибка получения списка микрофонов: {str(e)}")
            return []

    def _test_microphone(self):
        #Тестирование микрофона
        for attempt in range(3):
            try:
                with self.microphone as source:
                    self.logger.info(f"Калибровка (попытка {attempt+1})...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=2)
                    print("✅ Микрофон готов к использованию")
                    return True
            except Exception as e:
                self.logger.warning(f"Ошибка калибровки: {str(e)}")
                time.sleep(1)
        
        print("⚠️ Микрофон не отвечает, попробуйте:")
        print("1. Проверить подключение микрофона")
        print("2. Дать разрешение на доступ")
        print("3. Выбрать другой микрофон в настройках")
        return False

    def listen(self) -> Optional[str]:
    #Распознавание
        try:
            with self.microphone as source:
                print("\n🔊 Говорите сейчас...", end='', flush=True)
                audio = self.recognizer.listen(
                    source,
                    timeout=self.config["microphone"]["timeout"],
                    phrase_time_limit=5
                )
            
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            print(f"\r🎤 Распознано: {text}")
            return text.lower()
            
        except sr.WaitTimeoutError:
            print("\r⌛ Таймаут ожидания...", end='')
            return None
        except sr.UnknownValueError:
            print("\r❌ Речь не распознана", end='')
            return None
        except Exception as e:
            self.logger.error(f"Ошибка: {str(e)}")
            return None

    def get_microphone_info(self) -> str:
        #Инфа о микрофоне (текущем)
        mics = sr.Microphone.list_microphone_names()
        return f"Используется микрофон #{self.microphone.device_index}: {mics[self.microphone.device_index]}"
    
    def register_mode_command(self, modes: list):
        self.mode_commands = {
            "активируй режим": modes,
            "включи режим": modes,
            "переключи в режим": modes
        }
        self.logger.info(f"Зарегистрировано режимов: {len(modes)}")