import os
from pathlib import Path
from typing import Dict, Any

BASE_DIR = Path(__file__).parent.absolute()
SOUNDS_DIR = BASE_DIR / "sounds"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"

LOGS_DIR.mkdir(exist_ok=True)

config: Dict[str, Any] = {
    "name": "Sayori",
    "version": "1.0",
    "paths": {
        "sounds": str(SOUNDS_DIR),
        "models": str(MODELS_DIR / "vosk-model-small-ru"),
        "logs": str(LOGS_DIR / "assistant.log"),
        "commands_config": str(BASE_DIR / "data" / "commands.json"),
        "modes_config": str(BASE_DIR / "data" / "modes.json")    
    },
    
    "audio": {
        "default_volume": 70,
        "volume_step": 10,
        "energy_threshold": 4000,
        "sample_rate": 44100
    },
    
    "microphone": {
        "device_index": 0,
        "chunk_size": 1024,
        "timeout": 3.0,
        "device_index": None,
        "sample_rate": 44100
    }
}

def validate_config(cfg: Dict) -> bool:
    required_paths = [
        (cfg["paths"]["sounds"], "Папка со звуками"),
        (cfg["paths"]["models"], "Папка с моделями Vosk"),
        (Path(cfg["paths"]["logs"]).parent, "Папка для логов")
    ]
    
    for path, desc in required_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"{desc} не найдена: {path}")
    return True
