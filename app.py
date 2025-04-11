from telethon import TelegramClient
from telethon.tl.types import User, Channel, Chat
import asyncio
from utils import save_dialog, save_channel, get_entity_name, fetch_dialogs, fetch_user_info
from index import generate_index
from info import get_full_account_info

async def main_menu(client):
    
    me = await client.get_me()
    user_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "Не указано"
    username = f"@{me.username}" if me.username else "отсутствует"
    user_id = f"{me.id}"

    while True:
        print("\n********************************")
        print("*DumpTGbyWorpli_V.11.2*")
        print("********************************")
        print("\nПодключенный аккаунт:")
        print(f"Имя: {user_name}")
        print(f"Username: {username}")
        print(f"ID: {user_id}\n")
        print("Выберите действие:\n")
        print("1 - Дамп одного диалога")
        print("2 - Дамп всех личных диалогов")
        print("3 - Дамп канала")
        print("4 - Дамп избранного (Saved Messages)")
        print("5 - Полная информация об аккаунте")
        print("0 - Выход")
        choice = input("\nВаш выбор: ")

        if choice == '0':
            print("\nЗавершение работы...")
            break

        elif choice == '1':
            target = input("\nВведите username без @: ")
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
            await generate_index(client, user, all_dialogs)
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

        elif choice == '4':
            try:
                saved_messages = await client.get_entity("me")
                result = await save_dialog(client, saved_messages)
                print(f"\nДиалог 'Избранное' сохранён: {result['path']}")
            except Exception as e:
                print(f"\nОшибка: {str(e)}")

        elif choice == '5':
            await get_full_account_info(client)

        else:
            print("\nНекорректный выбор!")

async def main():
    api_id = 
    api_hash = ''  
    
    async with TelegramClient(
        'session_name',
        api_id,
        api_hash,
        device_model='DumpTGbyWorpli',
        system_version='11.2',
        app_version='11.2'
    ) as client:
        await client.start()
        await main_menu(client)

if __name__ == '__main__':
    asyncio.run(main())
