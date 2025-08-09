import logging
import time
from typing import Optional, Callable
from pathlib import Path
from .voice_engine import VoiceEngine
from modules.audio_controller import AudioController
from core.mode_manager import ModeManager
import json
from config import config

class Assistant:
    def __init__(self, config: dict):
        self.config = config
        self.name = config["name"]
        self._setup_logging()
        
        self.voice = VoiceEngine(config)
        self.audio = AudioController()
        self.modes = ModeManager(Path("data") / "modes.json")
        
        self._setup_logging()
        self.logger.info(f"Ассистент {self.name} готов к работе!")
        
        
    def _validate_config(self, config: dict):
        required = ["name", "log_file", "sounds_path"]
        for key in required:
            if key not in config:
                raise ValueError(f"Отсутствует обязательный параметр: {key}")
                 
    def _setup_logging(self):
        self.logger = logging.getLogger(self.name)
        log_file = self.config["paths"]["logs"]
        file_handler = logging.FileHandler(log_file)
        formater = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
        file_handler.setFormatter(formater)
        
    def play_safe(self, sound_name: str, max_duration: float = 5.0) -> bool:
        try:
            if not hasattr(self.voice, "play"):
                raise AttributeError("Голосовой движок не инициализирован!")
            start_time = time.time()
            self.voice.play(sound_name)
            while self.voice.is_playing():
                if time.time() - start_time > max_duration:
                    self.voice.stop_all()
                    self.logger.warning(f"Таймаут при воспроизведении звука: {sound_name}")
                    return False
                time.sleep(0.5)
            return True
        except Exception as e:
            self.loggeer.error(f"Ошибка воспроизведения {sound_name}: {e}")
            return False
        
    def run_command(self, command: str) -> bool:
        command = command.lower().strip()
        self.logger.info(f"Обработка команды: {command}")
        try:
            if not command:
                return True
            if any(w in command for w in ["привет сайори", "старт сайори", "здорова сайори"]):
                self.greet
            elif "громче" in command:
                self.volume_up()
            elif "тише" in command:
                self.volume_down()
            elif "установи громкость" in command:
                self._handle_volume_set(command)
            elif "сайори выключи пк" in command:
                self.shutdown()
                return False
            elif "сайори включи игровой режим" in command:
                self.set_mode("игровой")
            elif "сайори включи рабочий режим" in command:
                self.set_mode("рабочий")
            else:
                self.play_safe("Неивестная команда!")
        except Exception as e:
            self.logger.error(f"Ошибка команды:{e}")
            self.play_safe("errors/error_1")
        return True
    
    def _handle_volume_set(self, command: str):
        try:
            level = int("".join(filter(str.isdigit, command)))
            self.set_volume(level)
        except (ValueError, TypeError):
            self.logger.error("Неверный формат уровня громкости!")
            self.play_safe("error")

        
    def greet(self):
        """Приветствие при запуске"""
        self.logger.info("Запуск приветствия")
        
        # Последовательное воспроизведение с контролем времени
        success = self.play_safe("system/start_pc", max_duration=10)  # Длинное приветствие
        time.sleep(0.3)  # Короткая пауза между звуками
        
        if success:
            self.play_safe("system/sys_ready", max_duration=5)  # Короткий звук готовности
        
        self.logger.info("Приветствие завершено")
        
    def shutdown(self):
        """Завершение работы ассистента"""
        self.logger.info("Начало завершения работы")
        self.play_safe("pc_turn", max_duration=3)
        self.logger.info("Ассистент выключен")
        
    def volume_up(self, step=10):
        new_volume = self.audio.volume_up(step)
        self.logger.info(f"Громкость увеличена до {new_volume}%")
        self.play_safe("volume_up", max_duration=2)
        return new_volume
        
    def volume_down(self, step=10):
        new_volume = self.audio.volume_down(step)
        self.logger.info(f"Громкость уменьшена до {new_volume}%")
        self.play_safe("volume_down", max_duration=2)
        return new_volume
        
    def set_volume(self, level):
        level = max(0, min(100, level))
        current = self.audio.get_volume()
        self.audio.set_volume(level)
        
        self.logger.info(f"Громкость изменена с {current}% на {level}%")
    
        sound = "volume_up" if level > current else "volume_down"
        self.play_safe(sound, max_duration=2)
        
    def load_commands(self):
        with open(config["paths"]["commands_config"]) as f:
            self.commands = json.load(f)
        for category in self.commands["voice_commands"].values():
            for phrase, cmd in category.items():
                self.voice_recognizer.register_command(
                    phrase,
                    lambda: self._execute_command(cmd)
                )
                
    def check_system_health(self) -> str:
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            
            if cpu > 90 or ram > 90:
                return "critical"
            elif cpu > 70 or ram > 70:
                return "warning"
            return "normal"
        except ImportError:
            self.logger.warning("psutil не установлен, мониторинг отключен")
            return "unknown"
        
