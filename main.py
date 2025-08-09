import signal
import sys
import threading
import time
from queue import Queue
from typing import NoReturn

from core.assistant import Assistant
from core.mode_manager import ModeManager
from core.voice_engine import VoiceEngine
from core.voice_recognizer import VoiceRecognizer
import config as cfg

class SayoriMain:
    def __init__(self):
        self.shutdown_flag = threading.Event()
        self.command_queue = Queue(maxsize=20)
        self.assistant = Assistant(cfg.config)
        
        signal.signal(signal.SIGINT, self.graceful_exit)
        signal.signal(signal.SIGTERM, self.graceful_exit)
        self.assistant.logger.info("Сайори v1.0 инициализирована...")
        
    def graceful_exit(self, signum:" int", frame) -> NoReturn:
        self.shutdown_flag.set()
        self.assistant.logger.warning(f"Выключение системы...")
        self.assistant.shutdown()
        sys.exit(0)
        
    def voice_control_loop(self):
        recognizer = VoiceRecognizer(cfg.config)
        recognizer.register_mode_command(self.assistant.modes.get_available_modes())
        
        while not self.shutdown_flag.is_set():
            try:
                command = recognizer.listen()
                if command:
                    self.command_queue.put(("voice", command))
            except Exception as e:
                self.assistant.logger.error(f"Ошибка распознавания голоса: {e}")
                
    def keyboard_input_loop(self):
        while not self.shutdown_flag.is_set():
            try:
                cmd = input("> ").strip
                if cmd.lower() in ["exit", "quit"]:
                    self.command_queue.put(("system", "shutdown"))
                else:
                    self.command_queue.put(("cli", cmd))
            except (EOFError, KeyboardInterrupt):
                self.command_queue.put(("system", "shutdown"))
            except Exception as e:
                self.assistant.logger.error(f"Ошибка ввода: {e}")
                
    def process_commands(self):
        while not self.shutdown_flag.is_set():
            try:
                if not self.command_queue.empty():
                    source, command = self.command_queue.get()
                    
                    if source == "system" and command == "shutdown":
                        self.graceful_exit(signal.SIGINT, None)
                        
                    success = self.assistant.process_command(source, command)
                    if not success and source == "voice":
                        self.assistant.play_safe("errors/error_2")
            except Exception as e:
                self.assistant.logger.error(f"Ошибка обработки команд: {e}")
                
    def system_monitor(self):
        while not self.shutdown_flag.is_set():
            try:
                if self.assistant.check_system_health() == "critical":
                    self.command_queue.put(("system", "emergency_save"))
                time.sleep(10)
            except Exception as e:
                self.assistant.logger.error(f"Ошибка мониторинга системы: {e}")
                
    def run(self):
        try:
            threads = [
                threading.Thread(target=self.voice_control_loop, daemon=True),
                threading.Thread(target=self.keyboard_input_loop, daemon=True),
                threading.Thread(target=self.process_commands, daemon=True),
                threading.Thread(target=self.system_monitor, daemon=True)
            ]
            
            for t in threads:
                t.start()
                
            self.assistant.greet()
            self.assistant.logger.info("Система запущена!")
            
            while not self.shutdown_flag.is_set():
                time.sleep(1)
                
        except Exception as e:
            self.assistant.logger.critical(f"Фатальная ошибка: {e}")
        finally:
            self.shutdown_flag.set()
            self.assistant.shutdown()
            
if __name__ == "__main__":
    app = SayoriMain()
    app.run()
            
                
                
        