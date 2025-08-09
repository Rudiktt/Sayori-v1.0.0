import json
import logging
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, Any, Dict
from core.voice_engine import VoiceEngine
from core.audio_controller import AudioController
from core.mode_manager import ModeManager
from core.voice_recognizer import VoiceRecognizer

class Assistant:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._setup_logging()
        self._init_components()
        self.commands = self._load_commands()
        self.logger.info("Сайори инициализирована!")
        
    def _setup_logging(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        handler = logging.FileHandler(self.config["paths"]["logs"])
        formater = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formater)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
    def _init_components(self):
        self.voice_engine = VoiceEngine(self.config)
        self.audio_controller = AudioController(
            max_volume=self.config["audio"]["max_volume"],
            min_volume=self.config["audio"]["min_volume"]
        )
        self.mode_manager = ModeManager(self.config["paths"]["modes_config"])
        self.voice_recognizer = VoiceRecognizer(self.config)
        
    def _load_commands(self) -> Dict[str, Dict]:
        try:
            with open(self.config["paths"]["commands_config"], "r", encoding="utf-8") as f:
                commands = json.load(f)
                
                if "voice_commands" not in commands:
                    raise ValueError("В конфигурации отсутствуют команды")
                self.logger.info(f"Загружено {sum(len(c) for c in commands['voice_commands'].values())} команд")
                return commands["voice_commands"]
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке команд: {e}")
            return {}
        
    def process_command(self, command: str) -> bool:
        try:
            command = command.lower().strip()
            self.logger.info(f"Обработка команды: {command}")
            for category in self.commands.values():
                for pattern, action in category.items():
                    if self._match_command(command, pattern):
                        return self._execute_action(action, command)
            self.say("Не поняла, что ты хочешь от меня :(")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка при обработке команды: {e}")
            return False
        
    def _match_command(self, pattern: str, command: str) -> bool:
        if pattern.lower() in command:
            return True
        
        if "alternatives" in self.commands.get(pattern, {}):
            for alt in self.commands[pattern]["alternatives"]:
                if alt in command:
                    return True
        return False
    
    def _execute_action(self, action: Dict, command: str) -> bool:
        action_type = action.get["action"]
        try:
            if action_type == "activate_mode":
                mode = action["params"]["mode"]
                self.say(f"Активирую режим: {mode}")
                
            elif action_type == "set_volume":
                level = int(action["params"]["level"])
                self.audio_controller.set_volume(level)
                self.say(f"Громкость установлена на {level}%")
                return True

            elif action_type == "launch":
                app = action["params"]["app"]
                subprocess.Popen(app, shell=True)
                self.say(f"Запускаю {app}")
                return True

            elif action_type == "open_url":
                url = action["params"]["url"]
                webbrowser.open(url)
                self.say("Открываю ссылку")
                return True

            elif action_type == "system":
                if action["params"]["command"] == "shutdown":
                    self.say("Выключаю систему")
                    return True
                
            self.logger.error(f"Неизвестный тип действия: {action_type}")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка при выполнении действия: {e}")
            self.say("Не могу выполнить команду")
            
    def say(self, text: str):
        try:
            self.voice_engine.synthesize(text)
            self.logger.info(f"Сказал: {text}")
        except Exception as e:
            self.logger.error(f"Ошибка синтеза речи: {e}")
            print(f"Сайори: {text}")
            
    def get_available_commands(self) -> Dict[str, list]:
        return {
            "Режимы": list(self.commands["управление режимами"].keys()),
            "Звук": list(self.commands["управление звуком"].keys()),
            "Система": list(self.commands["системные команды"].keys())
        }
        
    def run_voice_loop(self):
        try:
            while True:
                command = self.voice_recognizer.listen()
                if command and "сайори" in command:
                    self.process_command(command.replace("сайори", "").strip())
        except KeyboardInterrupt:
            self.logger.info("Сайори остановлена...")
    