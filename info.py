from telethon.tl.types import User, Channel, Chat
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.account import GetAuthorizationsRequest
import os
from datetime import datetime
import asyncio
import time
import re

async def get_full_account_info(client, output_dir="dialogs"):
    info = []
    user = await fetch_user_info(client)
    spam_status = await check_spam_block(client)
    info.append("\n=== Основная информация ===")
    info.append(f"ID: {user['id']}")
    info.append(f"Username: @{user['username']}")
    info.append(f"Телефон: {user['phone']}")
    info.append(f"Био: {user['bio']}")
    info.append(f"Премиум: {'Да' if user['is_premium'] else 'Нет'}")
    info.append(f"СпамБлок: { 'Нет' if spam_status == 'Нет' else 'Да' if spam_status == 'Да' else 'Неизвестно'}")

    info.append("\n=== Устройства ===")
    if user['devices']:
        info.append(f"{'Модель':<20} | {'Платформа':<12} | {'Версия':<10} | {'IP':<15}")
        info.append("-" * 65)
        for dev in user['devices']:
            info.append(f"{dev['device_model']:<20} | {dev['platform']:<12} | {dev['app_version']:<10} | {dev['ip']:<15}")
    else:
        info.append("Нет данных об устройствах")

    info.append("\n=== Крипто-кошельки ===")
    bots = [
        ("CryptoTestnetBot", "/wallet"),
        ("CryptoBot", "/wallet"),
        ("xrocket", "/wallet")
    ]
    for bot_username, command in bots:
        bot_data = await fetch_bot_data(client, bot_username, command)
        info.append(f"\n🔹 @{bot_username}:")
        info.append(bot_data.replace("≈", "≈"))

    info.append("\n=== Статистика диалогов ===")
    stats = {
        'Каналы': 0,
        'Чаты': 0,
        'Группы': 0,
        'Пользователи': 0,
        'Боты': 0,
        'Избранное': 1,
        'Неизвестно': 0
    }

    contacts = []
    async for dialog in client.iter_dialogs():
        if dialog.name == 'Избранное':
            stats['Избранное'] += 1
        elif dialog.is_channel:
            stats['Каналы'] += 1
        elif dialog.is_group:
            stats['Группы'] += 1
        elif isinstance(dialog.entity, Chat):
            stats['Чаты'] += 1
        elif isinstance(dialog.entity, User):
            if dialog.entity.bot:
                stats['Боты'] += 1
            else:
                stats['Пользователи'] += 1
                if dialog.entity.contact:
                    contacts.append(dialog.entity)
        else:
            stats['Неизвестно'] += 1

    info.append(f"{'Тип':<12} | {'Количество':<10}")
    info.append("-" * 23)
    for k, v in stats.items():
        info.append(f"{k:<12} | {v:<10}")

    info.append("\n=== Взаимные Контакты ===")
    if contacts:
        info.append(f"{'Имя':<25} | {'Username':<15} | {'Телефон':<12}")
        info.append("-" * 60)
        for contact in contacts:
            phone = getattr(contact, 'phone', 'скрыт')
            info.append(f"{get_entity_name(contact):<25} | @{contact.username or '-':<15} | {phone:<12}")
    else:
        info.append("Контакты не найдены")

    info.append("\n\nPowered by @worpli")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"account_info_{timestamp}.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(info))
    print("\n".join(info))
    print(f"\nИнформация сохранена в файл: {filename}")
    return filename

async def fetch_bot_data(client, bot_username, command):
    try:
        bot = await client.get_entity(bot_username)
        await client.send_message(bot, command)
        start_time = time.time()
        response = ""
        while time.time() - start_time < 5:
            async for message in client.iter_messages(bot, limit=2):
                if message.out:
                    continue
                if message.date.timestamp() > start_time:
                    response = await _filter_crypto_data(message.text)
                    return response
            await asyncio.sleep(1)
        return response
    except Exception as e:
        return f"Ошибка: {str(e)}"

async def _filter_crypto_data(text):
    positive_wallets = []
    total_line = ""
    header = "👛 Кошелёк"
    amount_pattern = re.compile(r'([0-9]{1,3}(?:[ ,.\d]{3})*(?:\.\d+)?)\s*([A-Za-z]{3,})')
    md_link_pattern = re.compile(r'?\*?(\*?)([^\*]+)\*??[^)]+')
    for line in text.split('\n'):
        original_line = line.strip()
        if not original_line:
            continue
        if original_line.startswith("🔹"):
            continue
        if original_line.startswith('≈'):
            total_line = original_line
            continue
        if ':' in original_line:
            parts = original_line.split(':', 1)
            wallet_name_raw = parts[0].strip()
            wallet_name = md_link_pattern.sub(r'\2', wallet_name_raw)
            wallet_name = wallet_name.replace('*', '').strip()
            wallet_rest = parts[1].strip()
            m = amount_pattern.search(wallet_rest)
            if m:
                try:
                    amount = float(m.group(1).replace(',', '').replace(' ', ''))
                    if amount > 0:
                        positive_wallets.append(f"{wallet_name}: {wallet_rest}")
                except ValueError:
                    continue
    if positive_wallets:
        result = [header, ""]
        result.extend(positive_wallets)
        if total_line:
            result.extend(["", total_line])
        return "\n".join(result)
    else:
        return "Нет активных балансов"

async def fetch_user_info(client):
    me = await client.get_me()
    try:
        result = await client(GetAuthorizationsRequest())
        auths = result.authorizations
    except Exception:
        auths = []
    devices = []
    for auth in auths:
        devices.append({
            'device_model': auth.device_model,
            'platform': auth.platform,
            'app_version': auth.app_version,
            'ip': auth.ip
        })
    full = await client(GetFullUserRequest(me))
    bio = getattr(full, 'about', None) or ''
    user_info = {
        'id': me.id,
        'username': me.username or '',
        'phone': me.phone or '',
        'bio': bio,
        'is_premium': getattr(me, 'is_premium', False),
        'devices': devices
    }
    return user_info

def get_entity_name(entity):
    if isinstance(entity, User):
        return f"{entity.first_name} {entity.last_name or ''}".strip()
    return getattr(entity, 'title', 'Без названия')

async def check_spam_block(client):
    try:
        spam_bot = await client.get_entity('SpamBot')
        await client.send_message(spam_bot, '/start')
        start_time = time.time()
        response_text = ""
        while time.time() - start_time < 10:
            async for message in client.iter_messages(spam_bot, limit=1):
                if not message.out:
                    response_text = message.text
                    break
            if response_text:
                break
            await asyncio.sleep(1)
        safe_phrases = [
            "Ваш аккаунт свободен от каких-либо ограничений",
            "Good news, no limits are currently applied to your account"
        ]
        if any(phrase in response_text for phrase in safe_phrases):
            return "Нет"
        return "Да"
    except Exception as e:
        error_message = str(e)
        if "You blocked this user" in error_message:
            return "Неизвестно"
        print(f"Ошибка проверки спам-блока: {error_message}")
        return "Неизвестно"