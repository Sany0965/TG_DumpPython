import os
import time
import re
import mimetypes
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument,
    DocumentAttributeVideo, DocumentAttributeAudio,
    DocumentAttributeSticker, MessageMediaGeo,
    User, Channel, MessageMediaWebPage,         
    MessageReplyHeader, ReplyInlineMarkup       
)
from telethon.tl.functions.account import GetAuthorizationsRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.utils import get_extension        
from channel import generate_channel_html       
import css
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon import functions, types
from telethon.tl.types import MessageMediaContact

async def process_media(client, message, media_dir):
    media = message.media
    html = '<div class="media">'
    try:
        if isinstance(media, MessageMediaPhoto):
            path, filename = await download_file(client, message, media_dir, 'photos')
            rel_path = os.path.join("media", 'photos', filename)
            html += f'<img src="{rel_path}" alt="{filename}">'
        
        elif isinstance(media, MessageMediaDocument):
            doc = media.document
            attrs = {type(a): a for a in doc.attributes}
            mime_type = doc.mime_type or ''
            if DocumentAttributeVideo in attrs:
                path, filename = await download_file(client, message, media_dir, 'videos')
                rel_path = os.path.join("media", 'videos', filename)
                html += f'''
                <video controls>
                    <source src="{rel_path}" type="{mime_type}">
                    Ваш браузер не поддерживает видео
                </video>'''
            elif DocumentAttributeAudio in attrs:
                path, filename = await download_file(client, message, media_dir, 'audio')
                rel_path = os.path.join("media", 'audio', filename)
                html += f'''
                <audio controls>
                    <source src="{rel_path}" type="{mime_type}">
                    Ваш браузер не поддерживает аудио
                </audio>'''
            elif DocumentAttributeSticker in attrs:
                path, filename = await download_file(client, message, media_dir, 'stickers')
                rel_path = os.path.join("media", 'stickers', filename)
                html += f'<img src="{rel_path}" class="sticker" alt="Стикер">'
            else:
                path, filename = await download_file(client, message, media_dir, 'files')
                rel_path = os.path.join("media", 'files', filename)
                html += f'''
                <div class="file-card">
                    📎 <a href="{rel_path}" download="{filename}">{filename}</a>
                </div>'''
        
        elif isinstance(media, MessageMediaGeo):
            geo = media.geo
            html += f'''
            <div class="geo">
                📍 <a href="https://www.openstreetmap.org/?mlat={geo.lat}&mlon={geo.long}" target="_blank">
                   {geo.lat:.4f}, {geo.long:.4f}
                </a>
            </div>'''
        
        elif isinstance(media, MessageMediaContact):
            contact = media
            first_name = contact.first_name or ""
            last_name = contact.last_name or ""
            phone_number = contact.phone_number or "Не указан"
            user_id = f"@{contact.user_id}" if hasattr(contact, "user_id") and contact.user_id else "Нет username"
            full_name = f"{first_name} {last_name}".strip()
            contact_display = f'''
            <div class="contact-card">
                <strong>👤 Контакт:</strong> {full_name if full_name else "Неизвестный"}<br>
                <strong>📞 Телефон:</strong> {phone_number}<br>
                <strong>🔗 Telegram:</strong> {user_id}
            </div>'''
            html += contact_display

    except Exception as e:
        html += f'<div class="error">[Ошибка: {str(e)}]</div>'
    html += '</div>'
    return html

async def get_stars_balance(client):
    try:
        result = await client(functions.payments.GetStarsStatusRequest(
            peer=types.InputPeerSelf()
        ))
        
        return result.balance
    except Exception as e:
        print("Ошибка при получении баланса Stars:", e)
        return 0

async def save_dialog(client, entity, output_dir="dialogs"):
    dialog_id = entity.id
    dialog_dir = os.path.join(output_dir, str(dialog_id))
    media_dir = os.path.join(dialog_dir, "media")
    os.makedirs(media_dir, exist_ok=True)
    os.makedirs(dialog_dir, exist_ok=True)
    
    if getattr(entity, 'photo', None):
        avatar_path = os.path.join(dialog_dir, "avatar.jpg")
        await client.download_profile_photo(entity, file=avatar_path)
    
    html_filename = os.path.join(dialog_dir, f"dialog_{dialog_id}.html")
    os.makedirs(os.path.dirname(html_filename), exist_ok=True)
    
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html><html><head>')
        f.write('<meta charset="UTF-8">')
        f.write('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        f.write(f'<title>Диалог с {get_entity_name(entity)}</title>')
        f.write(css.CSS_STYLES)
        f.write('</head><body><div class="container">')
        
        messages = []
        async for message in client.iter_messages(entity, reverse=True, limit=None):
            messages.append(message)
        
        total_messages = len(messages)
        for i, message in enumerate(messages):
            percentage = int((i + 1) * 100 / total_messages)
            print(f"\rОбработка диалога с {get_entity_name(entity)}: {percentage}%", end="")
            
            sender = await message.get_sender()
            is_me = message.sender_id == (await client.get_me()).id
            message_class = "my" if is_me else "their"
            sender_name = "Я" if is_me else f"{get_entity_name(sender)}"
            
            forward_info = ""
            if message.fwd_from:
                origin = await get_forward_origin(client, message.fwd_from)
                forward_info = f'<div class="forward">↩️ Переслано от {origin}</div>'
            
            message_html = f'''
            <div class="message {message_class}">
                <div class="bubble">
                    {forward_info}
                    <div class="meta">
                        <span class="sender">{sender_name}</span>
                        <span class="date">{message.date.strftime('%d.%m.%Y %H:%M')}</span>
                    </div>'''
            
            if message.text:
                text = re.sub(r'\n', '<br>', message.text)
                message_html += f'<div class="text">{text}</div>'
            
            if message.media:
                media_html = await process_media(client, message, media_dir)
                message_html += media_html
            
            if hasattr(message, "reply_markup") and message.reply_markup:
                try:
                    inline_buttons_html = '<div class="inline-buttons">'
                    for row in message.reply_markup.rows:
                        inline_buttons_html += '<div class="inline-buttons-row">'
                        for button in row.buttons:
                            if hasattr(button, "url") and button.url:
                                inline_buttons_html += (
                                    f'<a class="inline-button" href="{button.url}" target="_blank">'
                                    f'{button.text}</a>'
                                )
                            else:
                                inline_buttons_html += f'<span class="inline-button">{button.text}</span>'
                        inline_buttons_html += '</div>'
                    inline_buttons_html += '</div>'
                    message_html += inline_buttons_html
                except Exception as e:
                    message_html += f'<div class="error">[Ошибка обработки инлайн-кнопок: {str(e)}]</div>'
            
            if hasattr(message, "reactions") and message.reactions:
                try:
                    reaction_html = '<div class="reactions">'
                    if hasattr(message.reactions, "results") and message.reactions.results:
                        for reaction in message.reactions.results:
                            reaction_str = getattr(reaction.reaction, 'emoticon', None) \
                                if hasattr(reaction.reaction, 'emoticon') \
                                else str(reaction.reaction)
                            reaction_html += f'<span class="reaction">{reaction_str} {reaction.count}</span> '
                    reaction_html += '</div>'
                    message_html += reaction_html
                except Exception as e:
                    message_html += f'<div class="error">[Ошибка обработки реакций: {str(e)}]</div>'
            
            message_html += '</div></div>'
            f.write(message_html)
        
        print()
        
        f.write('</div></body></html>')
    
    return {
        'id': dialog_id,
        'name': get_entity_name(entity),
        'path': html_filename
    }



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
        print(f"Ошибка проверки спам-блока: {str(e)}")
        return "Неизвестно"


async def get_forward_origin(client, fwd_from):
    try:
        if fwd_from.from_id:
            orig_sender = await client.get_entity(fwd_from.from_id)
            return get_entity_name(orig_sender)
        elif fwd_from.from_name:
            return fwd_from.from_name
    except:
        return "Unknown"
    return "Unknown"

def get_entity_name(entity):
    if isinstance(entity, User):
        return f"{entity.first_name} {entity.last_name or ''}".strip()
    return getattr(entity, 'title', 'Без названия')

async def process_media(client, message, media_dir):
    media = message.media
    html = '<div class="media">'
    try:
        if isinstance(media, MessageMediaPhoto):
            path, filename = await download_file(client, message, media_dir, 'photos')
            rel_path = os.path.join("media", 'photos', filename)
            html += f'<img src="{rel_path}" alt="{filename}">'
        
        elif isinstance(media, MessageMediaDocument):
            doc = media.document
            attrs = {type(a): a for a in doc.attributes}
            mime_type = doc.mime_type or ''
            if DocumentAttributeVideo in attrs:
                path, filename = await download_file(client, message, media_dir, 'videos')
                rel_path = os.path.join("media", 'videos', filename)
                html += f'''
                <video controls>
                    <source src="{rel_path}" type="{mime_type}">
                    Ваш браузер не поддерживает видео
                </video>'''
            elif DocumentAttributeAudio in attrs:
                path, filename = await download_file(client, message, media_dir, 'audio')
                rel_path = os.path.join("media", 'audio', filename)
                html += f'''
                <audio controls>
                    <source src="{rel_path}" type="{mime_type}">
                    Ваш браузер не поддерживает аудио
                </audio>'''
            elif DocumentAttributeSticker in attrs:
                path, filename = await download_file(client, message, media_dir, 'stickers')
                rel_path = os.path.join("media", 'stickers', filename)
                html += f'<img src="{rel_path}" class="sticker" alt="Стикер">'
            else:
                path, filename = await download_file(client, message, media_dir, 'files')
                rel_path = os.path.join("media", 'files', filename)
                html += f'''
                <div class="file-card">
                    📎 <a href="{rel_path}" download="{filename}">{filename}</a>
                </div>'''

        elif isinstance(media, MessageMediaGeo):
            geo = media.geo
            html += f'''
            <div class="geo">
                📍 <a href="https://www.openstreetmap.org/?mlat={geo.lat}&mlon={geo.long}" target="_blank">
                   {geo.lat:.4f}, {geo.long:.4f}
                </a>
            </div>'''

        elif isinstance(media, MessageMediaContact):
            contact = media
            first_name = contact.first_name or ""
            last_name = contact.last_name or ""
            phone_number = contact.phone_number or "Не указан"
            user_id = f"@{contact.user_id}" if contact.user_id else "Нет username"

            full_name = f"{first_name} {last_name}".strip()
            contact_display = f'''
            <div class="contact-card">
                <strong>👤 Контакт:</strong> {full_name if full_name else "Неизвестный"}<br>
                <strong>📞 Телефон:</strong> {phone_number}<br>
                <strong>🔗 Telegram:</strong> {user_id}
            </div>'''
            html += contact_display

    except Exception as e:
        html += f'<div class="error">[Ошибка: {str(e)}]</div>'
    html += '</div>'
    return html


async def save_channel(client, entity, output_dir="dialogs/channels"):
    try:
        channel_dir = os.path.join(output_dir, str(entity.id))
        media_dir = os.path.join(channel_dir, "media")
        os.makedirs(channel_dir, exist_ok=True)
        os.makedirs(media_dir, exist_ok=True)

        total_messages = (await client.get_messages(entity, limit=0)).total
        processed = 0
        start_time = time.time()

        def update_progress():
            nonlocal processed
            percent = (processed / total_messages) * 100
            elapsed = time.time() - start_time
            print(
                f"\rОбработка: [{'#' * int(percent//2)}{' ' * (50 - int(percent//2))}] "
                f"{percent:.1f}% | Сообщений: {processed}/{total_messages} | "
                f"Время: {elapsed:.1f}с", end='', flush=True)

        avatar_path = os.path.join(channel_dir, "avatar.jpg")
        try:
            await client.download_profile_photo(entity, file=avatar_path)
        except Exception as e:
            print(f"\nОшибка аватарки: {str(e)}")
            avatar_path = None

        try:
            full = await client(GetFullChannelRequest(entity))
            participants_count = full.full_chat.participants_count
        except Exception as e:
            print(f"\nОшибка получения полной информации о канале: {str(e)}")
            participants_count = getattr(entity, 'participants_count', 0)

        channel_info = {
            'id': entity.id,
            'title': entity.title,
            'username': getattr(entity, 'username', None),
            'participants_count': participants_count,
            'description': getattr(entity, 'about', ''),
            'avatar': avatar_path
        }

        posts = []
        async for message in client.iter_messages(entity, limit=None):
            posts.append(message)
            processed += 1
            if processed % 10 == 0 or processed == total_messages:
                update_progress()

        print("\nГенерация HTML...")
        html_path = os.path.join(channel_dir, f"channel_{entity.id}.html")
        await generate_channel_html(
            channel_info=channel_info,
            posts=posts,
            output_path=html_path,
            media_dir=media_dir,
            progress_callback=lambda p: print(f"\rСохранение медиа: {p}%", end='')
        )

        print(f"\nКанал сохранен: {html_path}")
        return {
            'id': entity.id,
            'name': channel_info['title'],
            'type': 'Канал',
            'path': html_path,
            'avatar': avatar_path
        }

    except Exception as e:
        print(f"\nКритическая ошибка: {str(e)}")
        raise

async def download_file(client, message, base_dir, media_type):
    filename = f'file_{message.id}'
    file_ext = 'bin'
    if message.media:
        if isinstance(message.media, MessageMediaPhoto):
            file_ext = 'jpg'
        elif isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            doc_name = getattr(doc, 'name', None)
            if doc_name:
                filename = doc_name.rsplit('.', 1)[0]
                if '.' in doc_name:
                    file_ext = doc_name.split('.')[-1].lower()
            if doc.mime_type:
                ext_from_mime = mimetypes.guess_extension(doc.mime_type)
                if ext_from_mime:
                    file_ext = ext_from_mime.lstrip('.')
            if media_type == 'audio':
                file_ext = 'ogg'
            elif media_type == 'stickers':
                file_ext = 'webp'
            elif media_type == 'videos':
                file_ext = 'mp4'
    safe_filename = f"{filename}.{file_ext}"
    target_dir = os.path.join(base_dir, media_type)
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, safe_filename)
    if not os.path.exists(path):
        await message.download_media(file=path)
    return path, safe_filename

async def fetch_user_info(client):
    os.makedirs("dialogs", exist_ok=True)
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
    bio = getattr(full, 'about', None)
    if bio is None and hasattr(full, 'full_user'):
        bio = getattr(full.full_user, 'about', '')
    if bio is None:
        bio = ''
    user_info = {
        'id': me.id,
        'username': me.username,
        'phone': me.phone,
        'bio': bio,
        'is_premium': getattr(me, 'is_premium', False),
        'avatar': None,
        'devices': devices
    }
    if me.photo:
        avatar_path = os.path.join("dialogs", "avatar.jpg")
        user_info['avatar'] = await client.download_profile_photo(me, file=avatar_path)
    return user_info



async def fetch_dialogs(client):
    dialogs = []
    all_dialogs = []
    async for dialog in client.iter_dialogs():
        all_dialogs.append(dialog)
    total_channels = sum(1 for dialog in all_dialogs if dialog.is_channel)
    channel_count = 0
    for dialog in all_dialogs:
        if dialog.is_channel:
            channel_count += 1
            type_label = 'Канал'
            username = getattr(dialog.entity, 'username', None)
            if username:
                path = f"https://t.me/{username}"
            else:
                path = "#"
            channels_dir = os.path.join("dialogs", "channels")
            os.makedirs(channels_dir, exist_ok=True)
            avatar_path = None
            if getattr(dialog.entity, 'photo', None):
                avatar_path = os.path.join(channels_dir, f"{dialog.id}.jpg")
                try:
                    await client.download_profile_photo(dialog.entity, file=avatar_path)
                    print(f"Скачивание аватарок канала {channel_count}/{total_channels}")
                except Exception as e:
                    print(f"Ошибка при загрузке аватарки для канала {dialog.id}: {e}")
                    avatar_path = None
            dialogs.append({
                'id': dialog.id,
                'name': dialog.name,
                'type': type_label,
                'path': path,
                'avatar': avatar_path
            })
            continue
        elif dialog.is_user:
            type_label = 'Бот' if getattr(dialog.entity, 'bot', False) else 'Пользователь'
        elif dialog.is_group:
            type_label = 'Чат'
        else:
            type_label = 'Неизвестно'
        path = os.path.join("dialogs", str(dialog.id), f"dialog_{dialog.id}.html")
        dialogs.append({
            'id': dialog.id,
            'name': dialog.name,
            'type': type_label,
            'path': path
        })
    return dialogs

if __name__ == "__main__":
    import asyncio
    from telethon import TelegramClient

    api_id = YOUR_API_ID
    api_hash = 'YOUR_API_HASH'
    session_name = 'session'
    client = TelegramClient(session_name, api_id, api_hash)
    async def main_wrapper():
        await client.start()
        user = await fetch_user_info(client)
        print("Информация о пользователе:")
        print(user)
        dialogs = await fetch_dialogs(client)
        print("Список диалогов:")
        for d in dialogs:
            print(d)
    asyncio.get_event_loop().run_until_complete(main_wrapper())