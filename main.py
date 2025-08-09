import signal
import sys
import threading
import time
from queue import Queue
from typing import NoReturn
from core.assistant import Assistant
from core.voice_recognizer import VoiceRecognizer
import config as cfg

class SayoriMain:
    def __init__(self):
        self._setup_signals()
        self._init_components()
        self._start_threads()
        self._greet_user()

    def _setup_signals(self):
        """Обработка сигналов завершения"""
        self.shutdown_flag = threading.Event()
        signal.signal(signal.SIGINT, self.graceful_exit)
        signal.signal(signal.SIGTERM, self.graceful_exit)

    def _init_components(self):
        """Инициализация основных компонентов"""
        self.command_queue = Queue(maxsize=20)
        self.assistant = Assistant(cfg.config)
        self.voice_recognizer = VoiceRecognizer(cfg.config)
        
        # Загрузка команд и режимов
        self.assistant.load_commands()
        self.assistant.load_modes()

    def _start_threads(self):
        """Запуск рабочих потоков"""
        self.threads = [
            threading.Thread(target=self._voice_control_loop, daemon=True),
            threading.Thread(target=self._command_processing_loop, daemon=True),
            threading.Thread(target=self._system_monitor_loop, daemon=True)
        ]
        
        for thread in self.threads:
            thread.start()

    def _greet_user(self):
        """Приветствие пользователя"""
        self.assistant.say("Моя дорогая Сайори готова к работе!!!")
        print("\nДоступные режимы :)", list(self.assistant.modes.get_available_modes()))
        print("Главные команды :)", self.assistant.get_common_commands())

    def _voice_control_loop(self):
        """Цикл обработки голосовых команд"""
        while not self.shutdown_flag.is_set():
            try:
                command = self.voice_recognizer.listen()
                if command:
                    print(f"\n🎤 Услышала: {command}")
                    self.command_queue.put(("voice", command))
            except Exception as e:
                self.assistant.logger.error(f"Ошибка распознавания: {e}")

    def _command_processing_loop(self):
        """Цикл обработки команд из очереди"""
        while not self.shutdown_flag.is_set():
            try:
                if not self.command_queue.empty():
                    source, command = self.command_queue.get()
                    success = self.assistant.process_command(source, command)
                    
                    if not success:
                        self.assistant.say("Не удалось выполнить команду")
                        self.assistant.play_sound("errors/command_failed")
            except Exception as e:
                self.assistant.logger.error(f"Ошибка обработки: {e}")

    def _system_monitor_loop(self):
        """Мониторинг системы"""
        while not self.shutdown_flag.is_set():
            try:
                system_status = self.assistant.check_system_health()
                if system_status == "critical":
                    self.assistant.notify("Внимание: высокая нагрузка!")
                time.sleep(10)
            except Exception as e:
                self.assistant.logger.error(f"Ошибка мониторинга: {e}")

    def graceful_exit(self, signum, frame) -> NoReturn:
        """Корректное завершение работы"""
        self.shutdown_flag.set()
        self.assistant.say("Выключаю систему")
        self.assistant.shutdown()
        sys.exit(0)

if __name__ == "__main__":
    print("""
    ░██████╗░█████╗░██╗░░░██╗░█████╗░██████╗░██╗
    ██╔════╝██╔══██╗╚██╗░██╔╝██╔══██╗██╔══██╗██║
    ╚█████╗░███████║░╚████╔╝░██║░░██║██████╔╝██║
    ░╚═══██╗██╔══██║░░╚██╔╝░░██║░░██║██╔══██╗██║
    ██████╔╝██║░░██║░░░██║░░░╚█████╔╝██║░░██║██║
    ╚═════╝░╚═╝░░╚═╝░░░╚═╝░░░░╚════╝░╚═╝░░╚═╝╚═╝
    """)
    
    try:
        app = SayoriMain()
        while not app.shutdown_flag.is_set():
            time.sleep(1)
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)