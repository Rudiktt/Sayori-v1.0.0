from main import SayoriMain
import time

app = SayoriMain()

# Тестовые команды
test_commands = [
    "привет",
    "как дела",
    "включи рабочий режим",
    "громкость на 70",
    "пока"
]

for cmd in test_commands:
    print(f"\nТестируем: '{cmd}'")
    app.command_queue.put(("test", cmd))
    time.sleep(1)