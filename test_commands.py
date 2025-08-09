from core.assistant import Assistant
import config
import logging

# Включим логирование в консоль
logging.basicConfig(level=logging.INFO)

def main():
    print("\n=== Тест ассистента ===")
    assistant = Assistant(config.config)
    
    # Проверка загрузки команд
    print(f"\nЗагружено команд: {sum(len(c) for c in assistant.commands.values())}")
    
    # Тестовые команды
    test_commands = [
        "громкость 50",
        "активируй игровой режим",
        "несуществующая команда"
    ]
    
    for cmd in test_commands:
        print(f"\n> Команда: '{cmd}'")
        success = assistant.process_command(cmd)
        print(f"Результат: {'✅ Успешно' if success else '❌ Ошибка или команда не найдена'}")
    
    print("\nТест завершен!")

if __name__ == "__main__":
    main()