import os
import time
import re
from datetime import datetime
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument,
    DocumentAttributeVideo, DocumentAttributeAudio,
    MessageMediaGeo, MessageMediaWebPage
)
from telethon.utils import get_extension

CSS_STYLES = """
<style>
    :root {
        --background: #151e17;
        --my-message: #00e571;
        --their-message: #29332a;
        --text-dark: #FFFFFF;
        --text-light: #FFFFFF;
        --animation-duration: 0.3s;
    }
    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }
    body {
        font-family: 'Roboto', sans-serif;
        background: var(--background);
        padding: 20px;
        color: var(--text-light);
    }
    .container {
        max-width: 800px;
        margin: 0 auto;
    }
    .header {
        text-align: center;
        margin-bottom: 20px;
    }
    .avatar {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid var(--my-message);
        margin-bottom: 10px;
    }
    .channel-title {
        font-size: 24px;
        margin-bottom: 5px;
        color: var(--my-message);
    }
    .channel-meta {
        font-size: 14px;
        color: var(--text-light);
        opacity: 0.8;
        margin-bottom: 3px;
    }
    .messages {
        margin-top: 20px;
    }
    .message {
        display: flex;
        margin-bottom: 15px;
        opacity: 0;
        transform: translateY(20px);
        animation: fadeInUp var(--animation-duration) ease-out forwards;
    }
    @keyframes fadeInUp {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    .message.their {
        justify-content: flex-start;
        animation-delay: calc(var(--animation-duration) * 0.25);
    }
    .bubble {
        max-width: 100%;
        padding: 12px 16px;
        border-radius: 20px;
        background: var(--their-message);
        position: relative;
        word-wrap: break-word;
        overflow-wrap: break-word;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .bubble:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
    }
    .meta {
        display: flex;
        justify-content: space-between;
        font-size: 0.9em;
        margin-bottom: 8px;
    }
    .sender {
        font-weight: bold;
        margin-right: 10px;
    }
    .date {
        opacity: 0.8;
    }
    .post-text {
        font-size: 15px;
        margin-bottom: 8px;
        line-height: 1.4;
    }
    .post-text a {
        color: #0096FF;
        text-decoration: none;
    }
    .post-text a:hover {
        text-decoration: underline;
    }
    .post-text .hashtag {
        color: #0000FF;
    }
    blockquote {
        border-left: 4px solid #0096FF;
        padding-left: 10px;
        margin: 10px 0;
        font-style: italic;
        color: var(--text-light);
        background: rgba(0, 0, 0, 0.1);
    }
    .media-container {
        margin: 10px 0;
        border-radius: 12px;
        overflow: hidden;
    }
    video {
        width: 100%;
        max-width: 400px;
        border-radius: 12px;
    }
    audio {
        width: 100%;
        min-width: 250px;
    }
    img {
        max-width: 100%;
        height: auto;
        border-radius: 12px;
        margin: 5px;
    }
    .stats {
        font-size: 1em;
        margin-top: 6px;
        color: var(--text-light);
        display: flex;
        gap: 15px;
        align-items: center;
    }
    .stats span {
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .stats i {
        font-size: 1.1em;
    }
    .buttons {
        margin-top: 10px;
    }
    .button {
        display: inline-block;
        background: var(--my-message);
        color: #151e17;
        padding: 6px 12px;
        border-radius: 20px;
        text-decoration: none;
        font-size: 0.85em;
        margin-right: 6px;
    }
    @media (max-width: 600px) {
        .bubble {
            max-width: 85%;
        }
        .header {
            padding: 0 10px;
        }
    }
</style>
"""

def format_post_text(text):
    pattern_link = re.compile(r'([^]+)(https?://[^\s)]+)')
    text = pattern_link.sub(r'<a href="\2">\1</a>', text)
    text = re.sub(r'\*\*([^\*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(\B#[\w\d_]+)', r'<span class="hashtag">\1</span>', text)
    text = re.sub(r'(?m)^> (.+)$', r'<blockquote>\1</blockquote>', text)
    return text

async def generate_channel_html(channel_info, posts, output_path, media_dir, progress_callback=None):
    total_posts = len(posts)
    start_time = time.time()
    processed_grouped = set()
    async def update_progress(current):
        if progress_callback:
            percent = current / total_posts * 100
            elapsed = time.time() - start_time
            progress_callback(f"[{'▊' * int(percent//5)}{' ' * (20 - int(percent//5))}] {percent:.1f}% | Сообщений: {current}/{total_posts} | Время: {elapsed:.1f}с")
    subscribers = channel_info.get('participants_count') or 0
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{channel_info['title']} — Архив</title>
    <link href="https://fonts.googleapis.com/css?family=Roboto" rel="stylesheet">
    {CSS_STYLES}
    <script src="https://kit.fontawesome.com/a076d05399.js" crossorigin="anonymous"></script>
</head>
<body>
    <div class="container">
        <header class="header">
            <img class="avatar" src="{os.path.relpath(channel_info['avatar'], os.path.dirname(output_path))}" alt="Аватар">
            <h1 class="channel-title">{channel_info['title']}</h1>
            <p class="channel-meta">@{channel_info.get('username', 'unknown')}</p>
            <p class="channel-meta">{subscribers} подписчиков</p>
        </header>
        <div class="messages">
''')
        for post in reversed(posts):
            await update_progress(1)
            grouped_id = getattr(post, 'grouped_id', None)
            if grouped_id:
                if grouped_id in processed_grouped:
                    continue
                group = [p for p in posts if getattr(p, 'grouped_id', None) == grouped_id]
                processed_grouped.add(grouped_id)
                post_date = group[0].date.strftime('%d %B %Y')
                f.write(f'''
            <div class="message their">
                <div class="bubble">
                    <div class="meta">
                        <span class="sender">{channel_info['title']}</span>
                        <span class="date">{post_date}</span>
                    </div>
                ''')
                text = next((p.text for p in group if p.text), '')
                if text:
                    formatted_text = format_post_text(text)
                    formatted_text = formatted_text.replace("\n", "<br>")
                    f.write(f'<div class="post-text">{formatted_text}</div>')
                media_html = await process_grouped_media(group, media_dir)
                f.write(f'<div class="media-container">{media_html}</div>')
                f.write('</div></div>')
            else:
                post_date = post.date.strftime('%d %B %Y')
                f.write(f'''
            <div class="message their">
                <div class="bubble">
                    <div class="meta">
                        <span class="sender">{channel_info['title']}</span>
                        <span class="date">{post_date}</span>
                    </div>
                ''')
                if post.pinned:
                    f.write('<div class="pinned" style="font-size:0.8em; margin-bottom:6px;">📌 Закреплено</div>')
                if post.text:
                    formatted_text = format_post_text(post.text)
                    formatted_text = formatted_text.replace("\n", "<br>")
                    f.write(f'<div class="post-text">{formatted_text}</div>')
                if post.media and not isinstance(post.media, MessageMediaWebPage):
                    media_html = await process_post_media(post, media_dir)
                    f.write(f'<div class="media-container">{media_html}</div>')
                f.write('<div class="stats">')
                if post.views:
                    f.write(f'<span class="views"><i class="fas fa-eye"></i> {post.views}</span>')
                if post.reactions:
                    f.write('<span class="reactions">')
                    for reaction in post.reactions.results:
                        emoji = getattr(reaction.reaction, "emoticon", "❤️")
                        f.write(f'<span>{emoji} {reaction.count}</span>')
                    f.write('</span>')
                f.write('</div>')
                if post.reply_markup:
                    f.write('<div class="buttons">')
                    for row in post.reply_markup.rows:
                        for button in row.buttons:
                            if hasattr(button, "url"):
                                f.write(f'<a href="{button.url}" class="button">{button.text}</a>')
                    f.write('</div>')
                f.write('</div></div>')
        f.write('''
        </div>
        <footer style="text-align: center; margin-top: 20px; font-size: 0.9em; opacity: 0.7;">
            Powered by <a href="https://t.me/worpli" target="_blank" style="color: var(--my-message); text-decoration: none;">worpli</a>
        </footer>
    </div>
</body>
</html>
''')
    if progress_callback:
        progress_callback("Готово! Архив сохранен")
    return output_path

async def process_grouped_media(group, media_dir):
    html = '<div class="media">'
    for post in group:
        if post.media and not isinstance(post.media, MessageMediaWebPage):
            media = post.media
            if isinstance(media, MessageMediaPhoto):
                path, filename = await download_media(post, media_dir, 'photos')
                rel_path = os.path.join('media', 'photos', filename)
                html += f'<img src="{rel_path}" alt="Фото">'
            elif isinstance(media, MessageMediaDocument):
                doc = media.document
                attrs = {type(a): a for a in doc.attributes}
                if DocumentAttributeVideo in attrs:
                    path, filename = await download_media(post, media_dir, 'videos')
                    rel_path = os.path.join('media', 'videos', filename)
                    html += f'<video controls><source src="{rel_path}"></video>'
                elif DocumentAttributeAudio in attrs:
                    path, filename = await download_media(post, media_dir, 'audio')
                    rel_path = os.path.join('media', 'audio', filename)
                    html += f'<audio controls><source src="{rel_path}"></audio>'
                else:
                    path, filename = await download_media(post, media_dir, 'files')
                    rel_path = os.path.join('media', 'files', filename)
                    html += f'📎 <a href="{rel_path}" download>{filename}</a>'
            elif hasattr(media, 'geo'):
                geo = media.geo
                html += f'''
                <div class="geo">
                    📍 <a href="https://www.openstreetmap.org/?mlat={geo.lat}&mlon={geo.long}" target="_blank">
                        {geo.lat:.4f}, {geo.long:.4f}
                    </a>
                </div>'''
    html += '</div>'
    return html

async def process_post_media(post, media_dir):
    html = '<div class="media">'
    try:
        media = post.media
        if isinstance(media, MessageMediaPhoto):
            path, filename = await download_media(post, media_dir, 'photos')
            rel_path = os.path.join('media', 'photos', filename)
            html += f'<img src="{rel_path}" alt="Фото">'
        elif isinstance(media, MessageMediaDocument):
            doc = media.document
            attrs = {type(a): a for a in doc.attributes}
            if DocumentAttributeVideo in attrs:
                path, filename = await download_media(post, media_dir, 'videos')
                rel_path = os.path.join('media', 'videos', filename)
                html += f'<video controls><source src="{rel_path}"></video>'
            elif DocumentAttributeAudio in attrs:
                path, filename = await download_media(post, media_dir, 'audio')
                rel_path = os.path.join('media', 'audio', filename)
                html += f'<audio controls><source src="{rel_path}"></audio>'
            else:
                path, filename = await download_media(post, media_dir, 'files')
                rel_path = os.path.join('media', 'files', filename)
                html += f'📎 <a href="{rel_path}" download>{filename}</a>'
        elif hasattr(media, 'geo'):
            geo = media.geo
            html += f'''
            <div class="geo">
                📍 <a href="https://www.openstreetmap.org/?mlat={geo.lat}&mlon={geo.long}" target="_blank">
                    {geo.lat:.4f}, {geo.long:.4f}
                </a>
            </div>'''
    except Exception as e:
        html += f'<div style="color: red">[Ошибка медиа: {str(e)}]</div>'
    html += '</div>'
    return html

async def download_media(media_obj, base_dir, media_type):
    target_dir = os.path.join(base_dir, media_type)
    os.makedirs(target_dir, exist_ok=True)
    if isinstance(media_obj, MessageMediaDocument):
        doc = media_obj.document
        filename = getattr(doc, 'file_name', None)
        if filename:
            target_filename = filename
        else:
            ext = get_extension(media_obj) or 'bin'
            target_filename = f'post_{media_obj.id}.{ext}'
    else:
        ext = get_extension(media_obj) or 'bin'
        target_filename = f'post_{media_obj.id}.{ext}'
    path = os.path.join(target_dir, target_filename)
    if not os.path.exists(path):
        await media_obj.download_media(file=path)
    return path, target_filename
