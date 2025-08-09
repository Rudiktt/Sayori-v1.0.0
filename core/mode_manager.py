import json
import subprocess
import psutil
import time
import logging
from pathlib import Path
from typing import Dict, Optional, List
import webbrowser
from dataclasses import dataclass

@dataclass
class ModeAction:
    type: str
    target: Optional[str] = None
    args: Optional[str] = None
    delay: float = 0.0
    
class ModeManager:
    def __init__(self, config_path: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.modes = self._load_modes(config_path)
        self.current_mode = None
        self._setup_actions()
        
    def _load_modes(self, path: str) -> Dict:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                modes = json.load(f)
                
                for mode_name, config in modes.items():
                    if not isinstance(config.get("actions"), list):
                        raise ValueError(f"В режиме {mode_name} не указаны действия.")
                return modes
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке режимов: {e}")
            
    def _setup_actions(self):
        self._action_handlers = {
            'launch': self._launch_app,
            'kill': self._kill_process,
            'volume': self._set_volume,
            'launch_uri': self._launch_uri,
            'execute': self._execute_command,
            'display': self._adjust_display
        }
        
    def activate(self, mode_name: str) -> bool:
        if mode_name not in self.modes:
            self.logger.error(f"Режим '{mode_name}' не найден.")
            return False
        try:
            self.current_mode = mode_name
            mode_config = self.modes[mode_name]
            
            if "reqirements" in mode_config:
                self.check_requirements(mode_config["requirements"])
                
            for action_config in mode_config["actions"]:
                self._execute_action(action_config)
                time.sleep(action_config.get("delay", 0))
            self._handle_notifications(mode_config)
            self.logger.info(f"Активирован режим '{mode_name}'.")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при активации режима: {e}")
            return False
        
    def _execute_action(self, action: Dict):
        action_type = action["type"]
        handler = self._action_handlers.get(action_type)
        
        if not handler:
            raise ValueError(f"Неизвестный тип действия: {action_type}")
        handler(action)
        
    def _launch_app(self, action: Dict):
        app = action["target"]
        args = action.get("args", "").split()
        check_running = action.get("check_running", False)
        
        if check_running and self._is_process_running(app):
            self.logger.debug(f"Приложение {app} уже запущено.")
            return
        
        try:
            subprocess.Popen([app] + args, shell = True)
            self.logger.info(f"Запущенно: {app} {" ".join(args)}")
        except Exception as e:
            self.logger.error(f"Ошибка запуска приложения {app}: {e}")
            raise
        
    def _kill_process(self, action: Dict):
        
        target = action["target"]
        force = action.get("force", False)
        
        for proc in psutil.process_iter(["name"]):
            if proc.info["name"].lower() == target.lower():
                try:
                    proc.kill() if force else proc.terminate()
                    self.logger.info(f"Завершено: {target}")
                    return
                except Exception as e:
                    self.logger.error(f"Ошибка завершения процесса {target}: {e}")
                    raise
        self.logger.warning(f"Процесс {target} не найден.")
        
    def _set_volume(self, action: Dict):
        level = max(0, min(100, int(action["level"])))
        target = action.get("target", "system")
        smooth = action.get("smooth", False)
        self.audio_controller.set_volume(target, level, smooth)
        
    def _launch_uri(self, action: Dict):
        url = action["url"]
        fallback = action.get("fallback")
        
        if not webbrowser.open(url) and fallback:
            subprocess.Popen([fallback], shell=True)
            
        self.logger.info(f"Открыт URL: {url}")
        
    def _execute_command(self, action: Dict):
        cmd = action["command"]
        cwd = action.get("cwd")
        
        try:
            subprocess.run(cmd, cwd=cwd, shell=True, check=True)
            self.logger.info(f"Выполнено: {cmd}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ошибка выполнения команды: {e}")
            raise
        
    def _adjust_display(self, action: Dict):
        action_type = action["action"]
        if action_type == "dim":
            level = action["level"]
            print(f"Dimming display to {level}%")
            
    def _check_requirements(self, requirements: Dict):
        if "min_ram_gb" in requirements:
            ram_gb = psutil.virtual_memory().total / (1024 ** 3)
            if ram_gb < requirements["min_ram_gb"]:
                raise MemoryError(f"Недостаточно памяти. Ожидалось {requirements['min_ram_gb']} GB, но есть {ram_gb} GB.")
    
    def _handle_notifications(self, mode_config: Dict):
        if "notifications" not in mode_config:
            return
        
        notifications = mode_config["notifications"]
        if "start_sound" in notifications:
            sound = notifications["start_sound"]
            self.voice_engine.play(sound)
            
    def _is_process_running(self, name: str) -> bool:
        return any(p.info["name"].lower() == name.lower() 
              for p in psutil.process_iter(["name"]) if p.info["name"] is not None)
    
    def get_available_modes(self) -> List[str]:
        return list(self.modes.keys())