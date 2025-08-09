import sys
import signal
import threading
from pathlib import Path
from core.assistant import Assistant
from core.voice_recognizer import VoiceRecognizer
import config as cfg
import logging

class SayoriMain:
    def __init__(self):
        self._setup_logging()
        self._init_components()
        self._register_signals()
        self._start_system()

    def _setup_logging(self):
        """Настройка системы логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(cfg.config["paths"]["logs"]),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("Main")

    def _init_components(self):
        """Инициализация всех компонентов"""
        self.logger.info("Инициализация компонентов...")
        try:
            self.assistant = Assistant(cfg.config)
            self.voice_recognizer = VoiceRecognizer(cfg.config)
            self.logger.info("Все компоненты загружены")
        except Exception as e:
            self.logger.critical(f"Ошибка инициализации: {e}")
            raise

    def _register_signals(self):
        """Обработка сигналов завершения"""
        signal.signal(signal.SIGINT, self._graceful_shutdown)
        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def _start_system(self):
        """Запуск основного цикла"""
        self.logger.info(f"Запуск Sayori v{cfg.config['version']}")
        try:
            # Запуск в отдельном потоке
            self.thread = threading.Thread(
                target=self._voice_loop,
                daemon=True
            )
            self.thread.start()
            self.thread.join()  # Основной поток ждёт завершения
        except Exception as e:
            self.logger.error(f"Ошибка в основном цикле: {e}")

    def _voice_loop(self):
        """Цикл обработки голосовых команд"""
        wake_word = cfg.config.get("metadata", {}).get("wake_word", "сайори")
        self.logger.info(f"Ожидаю команды с триггером '{wake_word}'...")
        
        while True:
            try:
                command = self.voice_recognizer.listen()
                if command and wake_word in command.lower():
                    clean_cmd = command.replace(wake_word, "").strip()
                    self.assistant.process_command(clean_cmd)
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Ошибка обработки команды: {e}")

    def _graceful_shutdown(self, signum, frame):
        """Корректное завершение работы"""
        self.logger.info("Получен сигнал завершения")
        self.assistant.shutdown()
        sys.exit(0)

if __name__ == "__main__":
    try:
        app = SayoriMain()
    except Exception as e:
        logging.critical(f"Критическая ошибка: {e}")
        sys.exit(1)