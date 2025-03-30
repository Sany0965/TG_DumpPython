import os
import time
import re
from datetime import datetime
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument,
    DocumentAttributeVideo, DocumentAttributeAudio,
    DocumentAttributeFilename,
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
    .comments {
        margin-top: 10px;
        border-top: 1px solid var(--text-light);
        padding-top: 10px;
    }
    .comment {
        margin-bottom: 8px;
        padding: 8px;
        background: var(--their-message);
        border-radius: 10px;
    }
    .comment-sender {
        font-weight: bold;
        margin-right: 5px;
    }
    .comment-date {
        font-size: 0.8em;
        opacity: 0.7;
    }
    .comment-text {
        margin-top: 4px;
        line-height: 1.4;
    }
    @media (max-width: 600px) {
        .bubble {
            max-width: 85%;
        }
        .header {
            padding: 0 10px;
        }
    }
    /* Стили для кнопок доната и криптовалюты */
    .donate {
        margin-top: 20px;
        padding: 15px;
        background: #2a2a2a;
        border-radius: 5px;
        text-align: center;
    }
    .donate a.button, .crypto-address {
        display: inline-block;
        background: linear-gradient(45deg, #00e571, #00b359);
        color: #151e17;
        padding: 10px 20px;
        margin: 10px 5px;
        border-radius: 25px;
        text-decoration: none;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .donate a.button:hover, .crypto-address:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 10px rgba(0,0,0,0.5);
    }
    .crypto-address {
        cursor: pointer;
        border: none;
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

def format_comments_html(comments):
    html = '<div class="comments">'
    for comment in comments:
        comment_date = comment.date.strftime('%d %B %Y %H:%M') if hasattr(comment, 'date') else ''
        sender = getattr(comment, 'sender', 'Аноним')
        formatted_text = format_post_text(comment.text)
        formatted_text = formatted_text.replace("\n", "<br>")
        html += f'''
        <div class="comment">
            <div><span class="comment-sender">{sender}</span> <span class="comment-date">{comment_date}</span></div>
            <div class="comment-text">{formatted_text}</div>
        </div>
        '''
    html += '</div>'
    return html

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
            <p class="channel-meta">ID: {channel_info['id']}</p>
            <p class="channel-meta">Описание: {channel_info['description']}</p>
            <p class="channel-meta">Ссылка: <a href="{channel_info.get('link', '#')}">{channel_info.get('link', 'Нет ссылки')}</a></p>
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
                if hasattr(group[0], 'comments') and group[0].comments:
                    comments_html = format_comments_html(group[0].comments)
                    f.write(comments_html)
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
                if getattr(post, 'pinned', False):
                    f.write('<div class="pinned" style="font-size:0.8em; margin-bottom:6px;">📌 Закреплено</div>')
                if post.text:
                    formatted_text = format_post_text(post.text)
                    formatted_text = formatted_text.replace("\n", "<br>")
                    f.write(f'<div class="post-text">{formatted_text}</div>')
                if post.media and not isinstance(post.media, MessageMediaWebPage):
                    media_html = await process_post_media(post, media_dir)
                    f.write(f'<div class="media-container">{media_html}</div>')
                f.write('<div class="stats">')
                if getattr(post, 'views', None):
                    f.write(f'<span class="views"><i class="fas fa-eye"></i> {post.views}</span>')
                if getattr(post, 'reactions', None):
                    f.write('<span class="reactions">')
                    for reaction in post.reactions.results:
                        emoji = getattr(reaction.reaction, "emoticon", "❤️")
                        f.write(f'<span>{emoji} {reaction.count}</span>')
                    f.write('</span>')
                f.write('</div>')
                if getattr(post, 'reply_markup', None):
                    f.write('<div class="buttons">')
                    for row in post.reply_markup.rows:
                        for button in row.buttons:
                            if hasattr(button, "url"):
                                f.write(f'<a href="{button.url}" class="button">{button.text}</a>')
                    f.write('</div>')
                if hasattr(post, 'comments') and post.comments:
                    comments_html = format_comments_html(post.comments)
                    f.write(comments_html)
                f.write('</div></div>')
        f.write('''
        </div>
        <!-- Блок с кнопками доната и криптовалюты -->
        <div class="donate">
            <strong>Донат разработчику:</strong><br>
            <a href="http://t.me/send?start=IVVhIaubY95z" target="_blank" class="button">Cryptobot</a>
            <a href="https://yoomoney.ru/fundraise/19ABTK01SMQ.250330" target="_blank" class="button">YooMoney</a><br><br>
            <strong>Криптовалюта:</strong><br>
            <div>Usdt trc20: <button class="crypto-address" onclick="copyToClipboard('TLgtHTc71iMyabvapjbUi6EMSvzMhvdy3Z')">Копировать</button></div>
            <div>TRX TRON: <button class="crypto-address" onclick="copyToClipboard('TLgtHTc71iMyabvapjbUi6EMSvzMhvdy3Z')">Копировать</button></div>
            <div>BTC BITCOIN: <button class="crypto-address" onclick="copyToClipboard('bc1q2e2numnedld458l8cvgsu6qzjnyqe64exsfm9c')">Копировать</button></div>
        </div>
        <footer style="text-align: center; margin-top: 20px; font-size: 0.9em; opacity: 0.7;">
            Powered by <a href="https://t.me/worpli" target="_blank" style="color: var(--my-message); text-decoration: none;">worpli</a>
        </footer>
    </div>
    <script>
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(function() {
                alert("Скопировано: " + text);
            }, function(err) {
                alert("Ошибка копирования: " + err);
            });
        }
    </script>
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

async def download_media(post, base_dir, media_type):
    filename = f'post_{post.id}'
    ext = get_extension(post.media) or 'bin'

    if isinstance(post.media, MessageMediaDocument) and post.media.document:
        doc = post.media.document
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                ext = os.path.splitext(attr.file_name)[1]  
                filename = os.path.splitext(attr.file_name)[0]  
                break

    filename = f"{filename}{ext}" 
    target_dir = os.path.join(base_dir, media_type)
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, filename)

    if not os.path.exists(path):
        await post.download_media(file=path)

    return path, filename