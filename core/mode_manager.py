import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
import psutil
from dataclasses import dataclass

@dataclass
class ModeAction:
    type: str  # launch/kill/volume/script
    target: Optional[str] = None
    args: Optional[str] = None
    delay: float = 0.0

class ModeManager:
    def __init__(self, config_path: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.modes = self._load_modes(config_path)
        self.current_mode = None
        self._setup_action_handlers()

    def _load_modes(self, path: str) -> Dict:
        """Загрузка режимов из JSON с проверкой ошибок"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                modes = json.load(f)
                
            # Базовая валидация
            for mode_name, config in modes.items():
                if not isinstance(config.get("actions"), list):
                    self.logger.error(f"Режим '{mode_name}': отсутствуют actions")
                    modes.pop(mode_name)  # Пропускаем битый режим

            return modes

        except Exception as e:
            self.logger.error(f"Ошибка загрузки режимов: {e}")
            return {}  # Возвращаем пустой словарь вместо падения

    def _setup_action_handlers(self):
        """Действия, которые сейчас поддерживаются"""
        self._action_handlers = {
            'launch': self._launch_app,
            'kill': self._kill_process,
            'volume': self._set_volume,
            'script': self._run_script
        }

    def activate(self, mode_name: str) -> bool:
        """Активация режима с обработкой ошибок"""
        if mode_name not in self.modes:
            self.logger.error(f"Режим '{mode_name}' не найден")
            return False

        try:
            self.current_mode = mode_name
            actions = self.modes[mode_name].get("actions", [])
            
            for action_config in actions:
                self._execute_action(action_config)
                time.sleep(action_config.get("delay", 0.1))  # Задержка между действиями

            self.logger.info(f"Активирован режим: {mode_name}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка активации режима: {e}")
            return False

    def _execute_action(self, action: Dict):
        """Выполнение одного действия"""
        action_type = action.get("type")
        handler = self._action_handlers.get(action_type)
        
        if not handler:
            self.logger.warning(f"Неизвестный тип действия: {action_type}")
            return

        try:
            handler(action)
        except Exception as e:
            self.logger.error(f"Ошибка выполнения действия {action_type}: {e}")

    def _launch_app(self, action: Dict):
        """Запуск приложения"""
        app = action["target"]
        args = action.get("args", "").split()
        
        if action.get("check_running") and self._is_process_running(app):
            self.logger.debug(f"Приложение уже запущено: {app}")
            return

        try:
            subprocess.Popen([app] + args, shell=True)
            self.logger.info(f"Запущено: {app} {' '.join(args)}")
        except Exception as e:
            self.logger.error(f"Ошибка запуска {app}: {e}")
            raise

    def _kill_process(self, action: Dict):
        """Завершение процесса"""
        target = action["target"]
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and target.lower() in proc.info['name'].lower():
                try:
                    proc.kill() if action.get("force") else proc.terminate()
                    self.logger.info(f"Завершён процесс: {target}")
                    return
                except Exception as e:
                    self.logger.error(f"Ошибка завершения {target}: {e}")
                    raise

        self.logger.warning(f"Процесс не найден: {target}")

    def _set_volume(self, action: Dict):
        """Заглушка для установки громкости (реализуется через AudioController позже)"""
        level = action.get("level", 50)
        self.logger.info(f"[ЗАГЛУШКА] Установка громкости на {level}%")

    def _run_script(self, action: Dict):
        """Запуск BAT/CMD скрипта"""
        script_path = Path(action["path"])
        if not script_path.exists():
            raise FileNotFoundError(f"Скрипт {script_path} не найден")
        
        try:
            subprocess.run(str(script_path), shell=True, check=True)
            self.logger.info(f"Выполнен скрипт: {script_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Скрипт завершился с ошибкой: {e}")
            raise

    def _is_process_running(self, name: str) -> bool:
        """Проверка, работает ли процесс"""
        return any(
            p.info['name'] and name.lower() in p.info['name'].lower()
            for p in psutil.process_iter(['name'])
        )

    def get_available_modes(self) -> List[str]:
        """Список доступных режимов"""
        return list(self.modes.keys())

# Тест
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Тестирование ModeManager...")
    manager = ModeManager("data/modes.json")  # Убедитесь, что файл существует!
    
    print("\nДоступные режимы:", manager.get_available_modes())
    
    if manager.get_available_modes():
        test_mode = manager.get_available_modes()[0]
        print(f"\nАктивируем режим: {test_mode}")
        if manager.activate(test_mode):
            print("✅ Режим активирован!")
        else:
            print("❌ Ошибка активации")
    else:
        print("Нет доступных режимов. Проверьте modes.json")