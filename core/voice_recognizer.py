import sys
import logging
from pathlib import Path
import speech_recognition as sr
from typing import Optional

# Добавляем корень проекта в пути импорта
sys.path.append(str(Path(__file__).parent.parent))

try:
    import config as cfg
except ImportError:
    raise ImportError("Не найден config.py в корне проекта!")

class VoiceRecognizer:
    def __init__(self, config: dict):
        """
        Инициализация распознавателя голоса.
        
        :param config: Конфиг из config.py (разделы 'microphone' и 'language')
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.recognizer = sr.Recognizer()
        self.microphone = self._init_microphone()
        self._calibrate()

    def _init_microphone(self) -> Optional[sr.Microphone]:
        """Настройка микрофона с учетом конфига"""
        try:
            device_index = self.config["microphone"].get("device_index")
            sample_rate = self.config["audio"].get("sample_rate", 44100)
            return sr.Microphone(
                device_index=device_index,
                sample_rate=sample_rate
            )
        except Exception as e:
            self.logger.error(f"Ошибка инициализации микрофона: {e}")
            return None

    def _calibrate(self):
        """Калибровка уровня фонового шума"""
        if not self.microphone:
            return
            
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(
                    source, 
                    duration=self.config["microphone"].get("calibration_duration", 1.0)
                )
            self.logger.info("Микрофон откалиброван")
        except Exception as e:
            self.logger.error(f"Ошибка калибровки: {e}")

    def listen(self) -> Optional[str]:
        """
        Слушает микрофон и возвращает распознанный текст.
        Возвращает None при таймауте или ошибке.
        """
        if not self.microphone:
            self.logger.warning("Микрофон не доступен")
            return None

        try:
            with self.microphone as source:
                self.logger.debug("Ожидание голосовой команды...")
                audio = self.recognizer.listen(
                    source,
                    timeout=self.config["microphone"].get("timeout", 3),
                    phrase_time_limit=self.config["microphone"].get("phrase_limit", 5)
                )

            text = self.recognizer.recognize_google(
                audio, 
                language=self.config.get("language", "ru-RU")
            ).lower()
            
            self.logger.info(f"Распознано: {text}")
            return text

        except sr.WaitTimeoutError:
            self.logger.debug("Таймаут ожидания голоса")
            return None
        except sr.UnknownValueError:
            self.logger.debug("Речь не распознана")
            return None
        except Exception as e:
            self.logger.error(f"Ошибка распознавания: {e}")
            return None

if __name__ == "__main__":
    # Тестовый режим
    logging.basicConfig(level=logging.INFO)
    
    print("=== Тест голосового ввода ===")
    print("Говорите после звукового сигнала...")
    
    try:
        recognizer = VoiceRecognizer(cfg.config)
        while True:
            text = recognizer.listen()
            if text:
                print(f"> {text}")
            else:
                print("(команда не распознана)")
    except KeyboardInterrupt:
        print("\nТест завершен")
    except Exception as e:
        print(f"Ошибка: {e}")
    