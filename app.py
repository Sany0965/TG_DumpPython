from telethon import TelegramClient
from telethon.tl.types import User
import asyncio
import os
from utils import save_dialog, get_entity_name, fetch_user_info, fetch_dialogs, save_channel
from index import generate_index

async def main():
    api_id = 
    api_hash = ''  
    
    async with TelegramClient(
        'session_name',
        api_id,
        api_hash,
        device_model='DumpTGbyWorpli',
        system_version='13.0',
        app_version='9.1.0'
    ) as client:
        await client.start()
        
        print("\n1 - Дамп одного диалога")
        print("2 - Дамп всех личных диалогов")
        print("3 - Дамп канала")
        choice = input("Выберите действие: ")
        
        if choice == '1':
            target = input("Введите username без @.")
            try:
                entity = await client.get_entity(target)
                result = await save_dialog(client, entity)
                print(f"\nДиалог сохранён: {result['path']}")
            except Exception as e:
                print(f"\nОшибка: {str(e)}")

        elif choice == '2':
            dialogs = []
            async for dialog in client.iter_dialogs():
                if isinstance(dialog.entity, User):
                    print(f"\nОбработка диалога с {get_entity_name(dialog.entity)}...")
                    try:
                        result = await save_dialog(client, dialog.entity)
                        dialogs.append(result)
                    except Exception as e:
                        print(f"Ошибка в диалоге {dialog.id}: {str(e)}")
            
            user = await fetch_user_info(client)
            all_dialogs = await fetch_dialogs(client)
            await generate_index(user, all_dialogs)
            print("\nВсе личные диалоги сохранены! By @worpli")

        elif choice == '3':
            target = input("\nВведите username канала: ")
            try:
                entity = await client.get_entity(target)
                if getattr(entity, 'broadcast', False):
                    result = await save_channel(client, entity)
                    print(f"\nКанал сохранён: {result['path']}")
                    print("Закрепленные посты, реакции и медиа включены в архив!")
                else:
                    print("\nЭто не канал! Используйте команду для диалогов.")
            except Exception as e:
                print(f"\nОшибка: {str(e)}")

        else:
            print("\nНекорректный выбор!")

if __name__ == '__main__':
    asyncio.run(main())