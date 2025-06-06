import os
import re
import asyncio
import time
from info import fetch_bot_data, get_entity_name  
from utils import check_spam_block, get_stars_balance

async def generate_wallets_html(client):
    bots = [
        ("CryptoTestnetBot", "/wallet"),
        ("CryptoBot", "/wallet"),
        ("xrocket", "/wallet")
    ]
    wallet_entries = []
    total_balance = None
    total_real_balance = None
    currency_total = None
    for bot_username, command in bots:
        bot_data = await fetch_bot_data(client, bot_username, command)
        summary_line = ""
        for line in bot_data.splitlines():
            if line.startswith("≈"):
                summary_line = line.lstrip("≈").strip()
                break
        if not summary_line:
            summary_line = "0"
        if bot_username.lower() == "cryptotestnetbot":
            display_name = "Crypto Testnet Bot"
        elif bot_username.lower() == "cryptobot":
            display_name = "Cryptobot"
        elif bot_username.lower() == "xrocket":
            display_name = "Xrocket"
        else:
            display_name = bot_username
        match = re.search(r'([\d,]+\.\d+|[\d,]+)\s*([A-Za-z]+)', summary_line)
        if match:
            num_str = match.group(1)
            currency = match.group(2)
            try:
                value = float(num_str.replace(",", ""))
            except:
                value = 0.0
        else:
            value = 0.0
            currency = ""
        wallet_entries.append((display_name, summary_line, value, currency))
        if total_balance is None:
            total_balance = value
            currency_total = currency
        else:
            total_balance += value
        if bot_username.lower() != "cryptotestnetbot":
            if total_real_balance is None:
                total_real_balance = value
            else:
                total_real_balance += value
    html = '<h2>Крипто-кошельки</h2>'
    html += '<table style="width:100%; border-collapse: collapse; margin-bottom:20px;">'
    html += '<tr style="background: #2a2a2a;">'
    html += '<th style="padding: 8px; border: 1px solid #444; text-align:left;">Кошелёк</th>'
    html += '<th style="padding: 8px; border: 1px solid #444; text-align:left;">Баланс</th>'
    html += '</tr>'
    for name, summary, _, _ in wallet_entries:
        display_balance = summary if summary != "" else "0"
        html += f'<tr><td style="padding: 8px; border: 1px solid #444;">{name}</td>'
        html += f'<td style="padding: 8px; border: 1px solid #444;">{display_balance}</td></tr>'
    html += '<tr style="background: #2a2a2a;">'
    html += '<td style="padding: 8px; border: 1px solid #444; font-weight:bold;">Итого:</td>'
    if currency_total:
        html += f'<td style="padding: 8px; border: 1px solid #444; font-weight:bold;">{total_balance} {currency_total}; Реальные монеты: {total_real_balance if total_real_balance is not None else 0} {currency_total}</td>'
    else:
        html += '<td style="padding: 8px; border: 1px solid #444; font-weight:bold;">0</td>'
    html += '</tr>'
    html += '</table>'
    return html

async def generate_contacts_html(client):
    contacts = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if hasattr(entity, "contact") and entity.contact and not getattr(entity, "bot", False):
            contacts.append(entity)
    if not contacts:
        return "<p>Контакты не найдены</p>"
    
    html = '<h2>Контакты</h2>'
    html += '<table style="width:100%; border-collapse: collapse; margin-bottom:20px;">'
    html += '<tr style="background: #2a2a2a;">'
    html += '<th style="padding: 8px; border: 1px solid #444; text-align:left;">Имя</th>'
    html += '<th style="padding: 8px; border: 1px solid #444; text-align:left;">Username</th>'
    html += '<th style="padding: 8px; border: 1px solid #444; text-align:left;">Телефон</th>'
    html += '</tr>'
    for contact in contacts:
        name = get_entity_name(contact)
        username = f"@{contact.username}" if contact.username else "-"
        phone = contact.phone if getattr(contact, "phone", None) else "скрыт"
        html += f'<tr><td style="padding: 8px; border: 1px solid #444;">{name}</td>'
        html += f'<td style="padding: 8px; border: 1px solid #444;">{username}</td>'
        html += f'<td style="padding: 8px; border: 1px solid #444;">{phone}</td></tr>'
    html += '</table>'
    return html

async def generate_index(client, user, dialogs, output_dir="dialogs"):
    order = {
        'Пользователь': 0,
        'Избранное': 0,
        'Канал': 1,
        'Чат': 1,
        'Бот': 2,
        'Неизвестно': 3
    }
    dialogs_sorted = sorted(dialogs, key=lambda d: order.get(d.get("type", "Неизвестно"), 99))
    
    spam_status = await check_spam_block(client)
    stars_balance = await get_stars_balance(client)
    try:
        stars_display = stars_balance.amount + stars_balance.nanos / 1e9
    except Exception:
        stars_display = stars_balance

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html><html><head>')
        f.write('<meta charset="UTF-8">')
        f.write('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        f.write('<title>Архив диалогов</title>')
        f.write('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">')
        f.write('<style>')
        f.write('body { font-family: Arial, sans-serif; background-color: #121212; margin: 0; padding: 0; color: #fff; }')
        f.write('.container { max-width: 800px; margin: 40px auto; padding: 20px; background: #1e1e1e; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); position: relative; }')
        f.write('.user-info { display: flex; flex-wrap: wrap; align-items: center; margin-bottom: 20px; padding: 10px; background: #2a2a2a; border-radius: 8px; }')
        f.write('.avatar { width: 80px; height: 80px; border-radius: 50%; margin-right: 20px; object-fit: cover; }')
        f.write('.user-details { flex: 1; min-width: 200px; }')
        f.write('.user-details h2 { color: #00e571; margin-bottom: 10px; }')
        f.write('.user-field { display: flex; justify-content: space-between; margin-bottom: 8px; padding: 8px; background: #2f2f2f; border-radius: 5px; }')
        f.write('.user-field .label { color: #888; font-weight: bold; }')
        f.write('.user-field .value { color: #fff; }')
        f.write('.devices { margin-top: 10px; overflow-x: auto; }')
        f.write('.devices table { width: 100%; border-collapse: collapse; }')
        f.write('.devices th, .devices td { padding: 8px; text-align: left; border-bottom: 1px solid #444; font-size: 14px; word-break: break-all; }')
        f.write('.devices th { color: #00e571; }')
        f.write('@keyframes neon { 0%, 18%, 22%, 25%, 53%, 57%, 100% { text-shadow: 0 0 2px #00e571, 0 0 5px #00e571, 0 0 10px #00e571, 0 0 20px #00e571; } 20%, 24%, 55% { text-shadow: none; } }')
        f.write('h1 { color: #00e571; margin-bottom: 20px; text-align: center; font-size: 24px; animation: neon 1.5s infinite; }')
        f.write('.dialog { display: flex; align-items: center; background: #2a2a2a; border: 1px solid #00e571; border-radius: 8px; margin-bottom: 10px; padding: 12px; transition: transform 0.2s ease-in-out, background 0.3s; }')
        f.write('.dialog:hover { background: #00e571; transform: scale(1.05); }')
        f.write('.dialog-icon { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background: #00e571; color: #1e1e1e; font-size: 20px; font-weight: bold; border-radius: 50%; margin-right: 12px; overflow: hidden; }')
        f.write('.dialog-avatar { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }')
        f.write('.dialog a { text-decoration: none; color: #fff; font-size: 18px; flex: 1; transition: color 0.3s; }')
        f.write('.dialog:hover a { color: #1e1e1e; }')
        f.write('.dialog-type { font-size: 14px; color: #aaa; margin-left: 10px; }')
        f.write('.footer { text-align: center; margin-top: 20px; font-size: 14px; color: #888; }')
        f.write('.footer a { color: #00e571; text-decoration: none; font-weight: bold; }')
        f.write('.donate { margin-top: 20px; padding: 15px; background: #2a2a2a; border-radius: 5px; text-align: center; }')
        f.write('.donate a.button, .crypto-address { display: inline-block; background: linear-gradient(45deg, #00e571, #00b359); color: #1e1e1e; padding: 10px 20px; margin: 10px 5px; border-radius: 25px; text-decoration: none; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s, box-shadow 0.2s; }')
        f.write('.donate a.button:hover, .crypto-address:hover { transform: translateY(-3px); box-shadow: 0 6px 10px rgba(0,0,0,0.5); }')
        f.write('.crypto-address { cursor: pointer; }')
        f.write('.lightrope { text-align: center; white-space: nowrap; overflow: hidden; position: absolute; z-index: 1; margin: -15px 0 0 0; padding: 0; pointer-events: none; width: 100%; }')
        f.write('.lightrope li { position: relative; animation-fill-mode: both; animation-iteration-count: infinite; list-style: none; margin: 0; padding: 0; display: inline-block; width: 12px; height: 28px; border-radius: 50%; margin: 20px; background: #00f7a5; box-shadow: 0px 4.67px 24px 3px #00f7a5; animation-name: flash-1; animation-duration: 2s; }')
        f.write('.lightrope li:nth-child(2n+1) { background: cyan; box-shadow: 0px 4.67px 24px 3px rgba(0, 255, 255, 0.5); animation-name: flash-2; animation-duration: 0.4s; }')
        f.write('.lightrope li:nth-child(4n+2) { background: #f70094; box-shadow: 0px 4.67px 24px 3px #f70094; animation-name: flash-3; animation-duration: 1.1s; }')
        f.write('.lightrope li:nth-child(odd) { animation-duration: 1.8s; }')
        f.write('.lightrope li:nth-child(3n+1) { animation-duration: 1.4s; }')
        f.write('.lightrope li:before { content: ""; position: absolute; background: #222; width: 10px; height: 9.33px; border-radius: 3px; top: -4.67px; left: 1px; }')
        f.write('.lightrope li:after { content: ""; top: -14px; left: 9px; position: absolute; width: 52px; height: 18.67px; border-bottom: solid #222 2px; border-radius: 50%; }')
        f.write('.lightrope li:last-child:after { content: none; }')
        f.write('.lightrope li:first-child { margin-left: -40px; }')
        f.write('@keyframes flash-1 { 0%, 100% { background: #00e571; box-shadow: 0px 4.67px 24px 3px #00e571; } 50% { background: rgba(0, 247, 165, 0.4); box-shadow: 0px 4.67px 24px 3px rgba(0, 247, 165, 0.2); } }')
        f.write('@keyframes flash-2 { 0%, 100% { background: cyan; box-shadow: 0px 4.67px 24px 3px cyan; } 50% { background: rgba(0, 255, 255, 0.4); box-shadow: 0px 4.67px 24px 3px rgba(0, 255, 255, 0.2); } }')
        f.write('@keyframes flash-3 { 0%, 100% { background: #f70094; box-shadow: 0px 4.67px 24px 3px #f70094; } 50% { background: rgba(247, 0, 148, 0.4); box-shadow: 0px 4.67px 24px 3px rgba(247, 0, 148, 0.2); } }')
        f.write('@media (max-width: 480px) {')
        f.write('  .container { margin: 20px; padding: 15px; }')
        f.write('  .user-info { flex-direction: column; align-items: flex-start; }')
        f.write('  .avatar { margin-bottom: 10px; }')
        f.write('  .devices table { font-size: 12px; }')
        f.write('}')
        f.write('</style>')
        f.write('</head><body>')
        f.write('<header style="position: relative; padding: 20px 0;">')
        f.write('<ul class="lightrope">')
        f.write('<li></li><li></li><li></li><li></li><li></li><li></li><li></li><li></li><li></li><li></li><li></li>')
        f.write('</ul>')
        f.write('</header>')
        f.write('<div class="container">')
        f.write('<div class="user-info">')
        if user.get("avatar"):
            avatar_path = os.path.relpath(user["avatar"], start=output_dir)
        else:
            avatar_path = "default_avatar.jpg"
        f.write(f'<img src="{avatar_path}" alt="Avatar" class="avatar">')
        f.write('<div class="user-details">')
        f.write('<h2><i class="fas fa-user"></i> Информация о пользователе</h2>')
        f.write('<div class="user-field"><span class="label"><i class="fas fa-id-badge"></i> ID:</span> <span class="value">{}</span></div>'.format(user.get("id", "Неизвестно")))
        f.write('<div class="user-field"><span class="label"><i class="fas fa-user"></i> Username:</span> <span class="value">@{}</span></div>'.format(user.get("username", "Неизвестно")))
        f.write('<div class="user-field"><span class="label"><i class="fas fa-phone-alt"></i> Номер:</span> <span class="value">{}</span></div>'.format(user.get("phone", "Неизвестно")))
        f.write('<div class="user-field"><span class="label"><i class="fas fa-info-circle"></i> Био:</span> <span class="value">{}</span></div>'.format(user.get("bio", "—")))
        premium_text = "Да" if user.get("is_premium") else "Нет"
        f.write('<div class="user-field"><span class="label"><i class="fas fa-star"></i> Премиум:</span> <span class="value">{}</span></div>'.format(premium_text))
        f.write('<div class="user-field"><span class="label"><i class="fas fa-ban"></i> Спам-блок:</span> <span class="value">{}</span></div>'.format(spam_status))
        f.write('<div class="user-field"><span class="label"><i class="fas fa-star"></i> Telegram Stars:</span> <span class="value">{}</span></div>'.format(stars_display))
        f.write('</div>')
        f.write('</div>')
        if user.get("devices"):
            f.write('<div class="devices">')
            f.write('<h3><i class="fas fa-desktop"></i> Подключённые устройства</h3>')
            f.write('<table>')
            f.write('<tr><th>Модель</th><th>Платформа</th><th>Версия</th><th>IP</th></tr>')
            for dev in user["devices"]:
                f.write('<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(dev.get("device_model", ""), dev.get("platform", ""), dev.get("app_version", ""), dev.get("ip", "")))
            f.write('</table>')
            f.write('</div>')
        wallets_html = await generate_wallets_html(client)
        f.write(wallets_html)
        contacts_html = await generate_contacts_html(client)
        f.write(contacts_html)
        f.write('<h1>Архив диалогов</h1>')
        for dialog in dialogs_sorted:
            relative_path = dialog["path"] if dialog["path"].startswith("http") else os.path.relpath(dialog["path"], start=output_dir)
            if dialog.get("type") == "Канал" and dialog.get("avatar") and os.path.exists(dialog.get("avatar")):
                relative_avatar_path = os.path.relpath(dialog.get("avatar"), start=output_dir)
                icon_html = f'<img src="{relative_avatar_path}" alt="Avatar" class="dialog-avatar">'
            else:
                avatar_file_path = os.path.join(output_dir, str(dialog["id"]), "avatar.jpg")
                if os.path.exists(avatar_file_path):
                    relative_avatar_path = os.path.relpath(avatar_file_path, start=output_dir)
                    icon_html = f'<img src="{relative_avatar_path}" alt="Avatar" class="dialog-avatar">'
                else:
                    initial_letter = dialog["name"][0].upper() if dialog["name"] else "?"
                    icon_html = initial_letter
            f.write(f'''
            <div class="dialog">
                <div class="dialog-icon">{icon_html}</div>
                <a href="{relative_path}">{dialog["name"]}</a>
                <span class="dialog-type">{dialog.get("type", "")}</span>
            </div>
            ''')
        f.write('<div class="footer">')
        f.write('Powered by <a href="https://t.me/worpli" target="_blank">@worpli</a><br><br>')
        f.write('<div class="donate">')
        f.write('<strong>Донат разработчику:</strong><br>')
        f.write('<a href="http://t.me/send?start=IVVhIaubY95z" target="_blank" class="button">Cryptobot</a>')
        f.write('<a href="https://yoomoney.ru/fundraise/19ABTK01SMQ.250330" target="_blank" class="button">YooMoney</a><br><br>')
        f.write('<strong>Криптовалюта:</strong><br>')
        f.write('<div>Usdt trc20: <button class="crypto-address" onclick="copyToClipboard(\'TLgtHTc71iMyabvapjbUi6EMSvzMhvdy3Z\')">Копировать</button></div>')
        f.write('<div>TRX TRON: <button class="crypto-address" onclick="copyToClipboard(\'TLgtHTc71iMyabvapjbUi6EMSvzMhvdy3Z\')">Копировать</button></div>')
        f.write('<div>BTC BITCOIN: <button class="crypto-address" onclick="copyToClipboard(\'bc1q2e2numnedld458l8cvgsu6qzjnyqe64exsfm9c\')">Копировать</button></div>')
        f.write('</div>')
        f.write('</div>')
        f.write('<script>')
        f.write('function copyToClipboard(text) {')
        f.write('  navigator.clipboard.writeText(text).then(function() {')
        f.write('    alert("Скопировано: " + text);')
        f.write('  }, function(err) {')
        f.write('    alert("Ошибка копирования: " + err);')
        f.write('  });')
        f.write('}')
        f.write('</script>')
        f.write('</body></html>')
        print(f"Главная страница создана: {index_path}")