import logging
from pathlib import Path
from typing import Dict, Any

# Настройка логгера для конфига
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Config")

BASE_DIR = Path(__file__).parent.absolute()

# Критически важные директории
ESSENTIAL_DIRS = [
    "sounds/system",
    "sounds/errors",
    "sounds/modes",
    "sounds/volume",
    "data"
]

# Автосоздание всех нужных папок
for dir_name in ESSENTIAL_DIRS:
    dir_path = BASE_DIR / dir_name
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Директория {dir_path} проверена")
    except Exception as e:
        logger.error(f"Ошибка создания директории {dir_path}: {e}")

config: Dict[str, Any] = {
    "name": "Sayori",
    "version": "1.0",
    "paths": {
        "sounds": str(BASE_DIR / "sounds"),
        "logs": str(BASE_DIR / "logs" / "assistant.log"),
        "commands_config": str(BASE_DIR / "data" / "commands.json"),
        "modes_config": str(BASE_DIR / "data" / "modes.json")    
    },
    "audio": {
        "default_volume": 70,
        "volume_step": 10,
        "sample_rate": 44100
    },
    "microphone": {
        "device_index": None,
        "timeout": 3,
        "calibration_duration": 1.0
    },
    "language": "ru-RU",
    "metadata": {
        "wake_word": "сайори",
        "author": "Rudiktt"
    }
}

def validate_config(cfg: Dict) -> bool:
    """Упрощенная валидация конфигурации"""
    required = [
        ("paths.sounds", str),
        ("paths.commands_config", str),
        ("paths.modes_config", str),
        ("microphone.timeout", (int, float)),
        ("metadata.wake_word", str)
    ]
    
    for path, typ in required:
        keys = path.split(".")
        val = cfg
        try:
            for key in keys:
                val = val[key]
            if not isinstance(val, typ):
                raise TypeError(f"Параметр {path} должен быть типа {typ}")
        except KeyError:
            raise KeyError(f"Отсутствует обязательный параметр: {path}")
    
    # Проверка существования файлов (только предупреждение)
    for key in ["commands_config", "modes_config"]:
        file_path = Path(cfg["paths"][key])
        if not file_path.exists():
            logger.warning(f"⚠️ Файл конфигурации не найден: {file_path}")
        else:
            logger.info(f"Файл конфигурации найден: {file_path}")
    
    return True

if __name__ == "__main__":
    try:
        validate_config(config)
        logger.info("✅ Конфигурация успешно валидирована")
        
        # Вывод основных параметров
        print("\nОсновные параметры конфигурации:")
        print(f"- Язык: {config['language']}")
        print(f"- Триггерное слово: {config['metadata']['wake_word']}")
        print(f"- Путь к звукам: {config['paths']['sounds']}")
        print(f"- Путь к логам: {config['paths']['logs']}")
        
    except Exception as e:
        logger.critical(f"❌ Ошибка валидации конфига: {e}")