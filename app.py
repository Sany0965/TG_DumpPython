from telethon import TelegramClient
from telethon.tl.types import User
import asyncio
from utils import save_dialog, get_entity_name, fetch_user_info, fetch_dialogs
from index import generate_index

async def main():
    api_id = 
    api_hash = ''
    
    async with TelegramClient(
        'session_name',
        api_id,
        api_hash,
        device_model='MonetExport',
        system_version='1.0',
        app_version='2.0'
    ) as client:
        await client.start()
        
        print("1 - Дамп одного диалога")
        print("2 - Дамп всех личных диалогов")
        choice = input("Выберите действие: ")
        
        if choice == '1':
            target = input("Введите username: ")
            entity = await client.get_entity(target)
            result = await save_dialog(client, entity)
            print(f"\nДиалог сохранён: {result['path']}")
            
        elif choice == '2':
            dialogs = []
            async for dialog in client.iter_dialogs():
                if isinstance(dialog.entity, User):
                    print(f"Обработка диалога с {get_entity_name(dialog.entity)}...")
                    try:
                        result = await save_dialog(client, dialog.entity)
                        dialogs.append(result)
                    except Exception as e:
                        print(f"Ошибка в диалоге {dialog.id}: {str(e)}")
            
            user = await fetch_user_info(client)
            all_dialogs = await fetch_dialogs(client)
            await generate_index(user, all_dialogs)
            print("Все личные диалоги сохранены!By @worpli")
            
        else:
            print("Некорректный выбор")

if __name__ == '__main__':
    asyncio.run(main())