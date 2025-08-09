import logging
import time
from pathlib import Path
from typing import Dict, Optional, Any
from core.voice_engine import VoiceEngine
from core.audio_controller import AudioController
from core.mode_manager import ModeManager
import json
import config as cfg
import subprocess


class Assistant:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._setup_logging()
        self._init_components()
        self.commands = self._load_commands()
        self.logger.info("Ассистент инициализирован (без озвучки)")
        
    def run_voice_loop(self):
        try:
            wake_word = self.config.get("metadata", {}).get("wake_word", "сайори")
            self.print(f"Ожидаю команду с триггером '{wake_word}'...")
        
            while True:
                command = self.voice_recognizer.listen()
                if command and wake_word in command:
                    clean_cmd = command.replace(wake_word, "").strip()
                    self.process_command(clean_cmd)
                
        except KeyboardInterrupt:
            self.logger.info("Остановка по запросу пользователя")
        except Exception as e:
            self.logger.critical(f"Сбой в голосовом цикле: {e}")
            raise
        
        
    def _setup_logging(self):
        """Настройка системы логирования"""
        self.logger = logging.getLogger(self.__class__.__name__)
        handler = logging.FileHandler(self.config["paths"]["logs"])
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _init_components(self):
        """Инициализация компонентов с обработкой ошибок"""
        try:
            self.voice_engine = VoiceEngine(self.config)  # Только для предзаписанных звуков
            self.audio = AudioController(
                max_volume=self.config["audio"].get("max_volume", 100),
                min_volume=self.config["audio"].get("min_volume", 0)
            )
            self.modes = ModeManager(self.config["paths"]["modes_config"])
            self.logger.info("Компоненты загружены")
        except Exception as e:
            self.logger.critical(f"Ошибка инициализации: {e}")
            raise

    def _load_commands(self) -> Dict[str, Any]:
        """Загрузка команд из JSON с проверкой ошибок"""
        try:
            with open(self.config["paths"]["commands_config"], "r", encoding="utf-8") as f:
                commands = json.load(f)
                if "voice_commands" not in commands:
                    raise ValueError("Отсутствует раздел voice_commands")
                return commands["voice_commands"]
        except Exception as e:
            self.logger.error(f"Ошибка загрузки команд: {e}")
            return {}



    def print(self, text: str):
        """Вывод текста в консоль (вместо озвучки)"""
        print(f"Сайори: {text}")
        self.logger.info(text)

    def get_available_commands(self) -> Dict[str, list]:
        """Список доступных команд для помощи"""
        return {
            category: list(commands.keys())
            for category, commands in self.commands.items()
        }

# Тест
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    try:
        assistant = Assistant(cfg.config)
        print("Доступные команды:", assistant.get_available_commands())
        
        # Тест обработки команд
        test_commands = [
            "активируй игровой режим",
            "громкость 50",
            "несуществующая команда"
        ]
        
        for cmd in test_commands:
            print(f"\nТест: '{cmd}'")
            assistant.process_command(cmd)
            
    except Exception as e:
        print(f"Ошибка теста: {e}", file=sys.stderr)
        
