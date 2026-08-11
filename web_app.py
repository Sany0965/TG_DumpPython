import argparse
import asyncio
import json
import re
import shutil
import socket
import tempfile
import time
import traceback
import uuid
import webbrowser
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from aiohttp import web
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.network.connection import (
    ConnectionTcpFull,
    ConnectionTcpMTProxyIntermediate,
    ConnectionTcpMTProxyRandomizedIntermediate,
)
from telethon.tl.functions.account import GetAuthorizationsRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import User

from index import generate_index
from info import get_full_account_info
from utils import (
    fetch_dialogs,
    fetch_user_info,
    get_entity_name,
    save_channel,
    save_dialog,
)

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"
RUNTIME.mkdir(exist_ok=True)
EXPORTS = ROOT.parent / "TG_DumpExports"
EXPORTS.mkdir(exist_ok=True)
AVATARS = RUNTIME / "avatars"
AVATARS.mkdir(exist_ok=True)
CONFIG_PATH = ROOT / "config.json"

# Незавершённые экспорты никогда не считаются архивами. Если приложение
# аварийно закрыли, остатки будут убраны при следующем запуске.
for stale_partial in EXPORTS.glob(".partial-*"):
    shutil.rmtree(stale_partial, ignore_errors=True)

DEFAULT_UI = {
    "theme": "monet",
    "effects": False,
    "compact": False,
    "avatars": True,
    "auto_refresh": True,
}
DEFAULT_PROXY = {
    "enabled": False,
    "type": "socks5",
    "host": "",
    "port": 0,
    "username": "",
    "password": "",
    "secret": "",
}


class State:
    def __init__(self):
        self.client = None
        self.phone = ""
        self.phone_code_hash = None
        self.task = None
        self.progress = 0
        self.stage = "Ожидание"
        self.logs = []
        self.result = None
        self.code_sent = False
        self.account = None
        self.auth_checked = False
        self.operation_logs = []
        self.operation_visible = False
        self.cancellable = False
        self.processed = 0
        self.total = 0
        self._progress_bucket = -1

    def log(self, text):
        from datetime import datetime

        line = f"[{datetime.now().strftime('%H:%M:%S')}] {text}"
        self.logs.append(line)
        self.logs = self.logs[-250:]
        print(line, flush=True)
        return line

    def operation_log(self, text):
        line = self.log(text)
        self.operation_logs.append(line)
        self.operation_logs = self.operation_logs[-40:]

    def begin_operation(self, stage):
        self.progress = 0
        self.processed = 0
        self.total = 0
        self.result = None
        self.stage = stage
        self.operation_logs = []
        self.operation_visible = True
        self.cancellable = True
        self._progress_bucket = -1
        self.operation_log(stage)

    def update_operation(self, percent, current=0, total=0, stage=None):
        self.progress = max(0, min(100, int(float(percent))))
        self.processed = int(current or 0)
        self.total = int(total or 0)
        if stage:
            self.stage = stage
        bucket = self.progress // 10
        if bucket > self._progress_bucket:
            self._progress_bucket = bucket
            count = f" · {self.processed}/{self.total}" if self.total else ""
            self.operation_log(f"{self.stage}: {self.progress}%{count}")

    def cancel_operation_ui(self):
        self.cancellable = False
        self.operation_visible = False
        self.operation_logs = []
        self.progress = 0
        self.processed = 0
        self.total = 0


S = State()


def read_config():
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_config(data):
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def ui_settings(config=None):
    config = config or read_config()
    return {**DEFAULT_UI, **config.get("ui", {})}


def proxy_settings(config=None):
    config = config or read_config()
    return {**DEFAULT_PROXY, **config.get("proxy", {})}


def public_settings():
    config = read_config()
    ui = ui_settings(config)
    proxy = proxy_settings(config)
    return {
        "ui": ui,
        "proxy": {
            "enabled": bool(proxy.get("enabled")),
            "type": proxy.get("type", "socks5"),
            "host": proxy.get("host", ""),
            "port": proxy.get("port", 0),
            "username": proxy.get("username", ""),
            "password_set": bool(proxy.get("password")),
            "secret_set": bool(proxy.get("secret")),
        },
        "exports_path": str(EXPORTS),
    }


def client_options(config):
    proxy = proxy_settings(config)
    options = {"connection": ConnectionTcpFull, "proxy": None}
    if not proxy.get("enabled"):
        return options

    host = str(proxy.get("host", "")).strip()
    port = int(proxy.get("port") or 0)
    if not host or not 1 <= port <= 65535:
        raise ValueError("У прокси неверный адрес или порт")

    if proxy.get("type") == "mtproxy":
        secret = str(proxy.get("secret", "")).strip()
        if not secret:
            raise ValueError("Для MTProxy нужен secret")
        options["proxy"] = (host, port, secret)
        options["connection"] = (
            ConnectionTcpMTProxyRandomizedIntermediate
            if secret.lower().startswith("dd")
            else ConnectionTcpMTProxyIntermediate
        )
    else:
        options["proxy"] = (
            "socks5",
            host,
            port,
            True,
            proxy.get("username") or None,
            proxy.get("password") or None,
        )
    return options


def parse_proxy_url(value):
    value = (value or "").strip()
    if not value:
        return None
    normalized = value
    if value.startswith("https://t.me/proxy") or value.startswith("http://t.me/proxy"):
        normalized = "tg://proxy?" + value.split("?", 1)[-1]
    parsed = urlparse(normalized)
    query = parse_qs(parsed.query)
    if parsed.scheme == "tg" and parsed.netloc == "proxy":
        return {
            "type": "mtproxy",
            "host": query.get("server", [""])[0],
            "port": int(query.get("port", [0])[0]),
            "secret": query.get("secret", [""])[0],
        }
    if parsed.scheme in {"socks5", "socks5h"}:
        return {
            "type": "socks5",
            "host": parsed.hostname or "",
            "port": parsed.port or 0,
            "username": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
        }
    raise ValueError("Поддерживаются socks5:// и ссылки tg://proxy / t.me/proxy")


def client_ready():
    return bool(S.client and S.client.is_connected())


async def refresh_account():
    if not client_ready() or not await S.client.is_user_authorized():
        S.account = None
        return None
    user = await S.client.get_me()
    S.account = {
        "id": user.id,
        "name": get_entity_name(user),
        "username": user.username or "",
        "phone": user.phone or "",
        "premium": bool(getattr(user, "premium", False)),
        "avatar": f"/api/avatar/{user.id}",
    }
    return S.account


async def ensure_client(api_id=None, api_hash=None):
    if client_ready():
        return S.client
    config = read_config()
    api_id = api_id or config.get("api_id")
    api_hash = api_hash or config.get("api_hash")
    if not api_id or not api_hash:
        raise ValueError("В config.json не настроены API ID и API Hash")
    network = client_options(config)
    S.client = TelegramClient(
        str(RUNTIME / "telegram"),
        int(api_id),
        api_hash,
        device_model=config.get("device_model", "Neuro TG Dump Web"),
        system_version=config.get("system_version", "Windows / Android"),
        app_version=config.get("app_version", "13.0"),
        lang_code=config.get("lang_code", "ru"),
        system_lang_code=config.get("system_lang_code", "ru-RU"),
        connection=network["connection"],
        proxy=network["proxy"],
        auto_reconnect=True,
        connection_retries=3,
        request_retries=3,
        retry_delay=1,
        timeout=15,
    )
    try:
        await S.client.connect()
    except Exception:
        S.client = None
        raise
    proxy = proxy_settings(config)
    suffix = f" через {proxy['type'].upper()}" if proxy.get("enabled") else ""
    S.log(f"Клиент Telegram подключён к MTProto{suffix}")
    return S.client


async def restore_session_once():
    if S.auth_checked:
        return
    S.auth_checked = True
    if not (RUNTIME / "telegram.session").exists():
        return
    try:
        client = await ensure_client()
        if await client.is_user_authorized():
            await refresh_account()
            S.stage = "Готово"
            S.log("Локальная сессия восстановлена")
    except Exception as error:
        S.log(f"Не удалось восстановить сессию: {error}")


async def authorized():
    await restore_session_once()
    return bool(S.account)


async def json_body(request):
    try:
        return await request.json()
    except Exception:
        return {}


async def page(_request):
    return web.FileResponse(ROOT / "web" / "index.html")


async def api_status(_request):
    await restore_session_once()
    config = read_config()
    return web.json_response(
        {
            "connected": client_ready(),
            "authorized": bool(S.account),
            "account": S.account,
            "busy": bool(S.task and not S.task.done()),
            "progress": S.progress,
            "stage": S.stage,
            "logs": S.logs[-60:],
            "operation_logs": S.operation_logs,
            "operation_visible": S.operation_visible,
            "cancellable": S.cancellable,
            "processed": S.processed,
            "total": S.total,
            "result": S.result,
            "configured": bool(config.get("api_id")),
            "code_sent": S.code_sent,
            "app": {
                "title": config.get("app_title", "Neuro"),
                "device": config.get("device_model", "Neuro TG Dump Web"),
                "version": config.get("app_version", "13.0"),
            },
        }
    )


async def api_send_code(request):
    data = await json_body(request)
    try:
        client = await ensure_client()
        S.phone = str(data.get("phone", "")).strip()
        if not S.phone:
            raise ValueError("Введи номер с кодом страны, например +79991234567")
        S.log(f"Запрос кода для {S.phone[:4]}***{S.phone[-2:]}")
        sent = await client.send_code_request(S.phone, force_sms=False)
        S.phone_code_hash = sent.phone_code_hash
        S.code_sent = True
        S.stage = "Код отправлен"
        delivery = type(sent.type).__name__.replace("SentCodeType", "")
        S.log(f"Код отправлен. Способ доставки: {delivery}")
        return web.json_response({"ok": True, "delivery": delivery})
    except PhoneNumberInvalidError:
        raise ValueError("Неверный номер телефона")
    except FloodWaitError as error:
        raise ValueError(f"Слишком много попыток. Подожди {error.seconds} секунд")


async def api_sign_in(request):
    data = await json_body(request)
    code = "".join(ch for ch in str(data.get("code", "")) if ch.isdigit())
    if not S.client or not S.phone_code_hash:
        raise ValueError("Сначала запроси новый код")
    try:
        await S.client.sign_in(S.phone, code, phone_code_hash=S.phone_code_hash)
    except SessionPasswordNeededError:
        S.log("Код принят — требуется пароль 2FA")
        return web.json_response({"ok": False, "password_required": True})
    except PhoneCodeInvalidError:
        raise ValueError("Неверный код. Используй самый свежий код Telegram")
    except PhoneCodeExpiredError:
        S.phone_code_hash = None
        S.code_sent = False
        raise ValueError("Код истёк — запроси новый")
    S.phone_code_hash = None
    S.code_sent = False
    await refresh_account()
    S.stage = "Готово"
    S.log("Авторизация выполнена, сессия сохранена")
    return web.json_response({"ok": True})


async def api_password(request):
    data = await json_body(request)
    try:
        await S.client.sign_in(password=data.get("password", ""))
    except PasswordHashInvalidError:
        raise ValueError("Неверный пароль 2FA")
    await refresh_account()
    S.stage = "Готово"
    S.log("Двухэтапная авторизация выполнена")
    return web.json_response({"ok": True})


async def api_reset_auth(_request):
    S.phone = ""
    S.phone_code_hash = None
    S.code_sent = False
    S.stage = "Ожидание нового номера"
    return web.json_response({"ok": True})


async def api_logout(_request):
    if S.client:
        await S.client.log_out()
        S.client = None
    S.account = None
    S.auth_checked = True
    S.stage = "Выход выполнен"
    S.log("Выполнен выход из аккаунта")
    return web.json_response({"ok": True})


async def api_import_session(request):
    reader = await request.multipart()
    upload = None
    while True:
        field = await reader.next()
        if field is None:
            break
        if field.name != "session":
            continue
        if not (field.filename or "").lower().endswith(".session"):
            raise ValueError("Нужен файл Telethon с расширением .session")
        data = bytearray()
        while True:
            chunk = await field.read_chunk()
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > 10 * 1024 * 1024:
                raise ValueError("Файл сессии слишком большой")
        upload = bytes(data)
    if not upload or len(upload) < 100:
        raise ValueError("Файл сессии пуст или повреждён")

    target = RUNTIME / "telegram.session"
    temp = RUNTIME / "import.session"
    temp.write_bytes(upload)
    if S.client:
        await S.client.disconnect()
        S.client = None
    backup = None
    if target.exists():
        backup = RUNTIME / f"telegram.backup-{int(time.time())}.session"
        shutil.copy2(target, backup)
    try:
        temp.replace(target)
        S.auth_checked = True
        client = await ensure_client()
        if not await client.is_user_authorized():
            raise ValueError("Эта сессия больше не авторизована в Telegram")
        await refresh_account()
        S.stage = "Готово"
        S.log(f"Сессия импортирована: {S.account['name']}")
        return web.json_response({"ok": True})
    except Exception:
        if S.client:
            await S.client.disconnect()
            S.client = None
        target.unlink(missing_ok=True)
        if backup and backup.exists():
            shutil.copy2(backup, target)
        S.account = None
        raise


async def api_profile(_request):
    if not await authorized():
        raise web.HTTPUnauthorized()
    user = await S.client.get_me()
    full = await S.client(GetFullUserRequest(user))
    auths = await S.client(GetAuthorizationsRequest())
    devices = [
        {
            "current": bool(item.current),
            "device": item.device_model or "Неизвестно",
            "platform": item.platform or "",
            "system": item.system_version or "",
            "app": item.app_name or "",
            "version": item.app_version or "",
            "ip": item.ip or "",
            "country": item.country or "",
        }
        for item in auths.authorizations
    ]
    return web.json_response(
        {
            **S.account,
            "bio": getattr(full.full_user, "about", "") or "",
            "verified": bool(getattr(user, "verified", False)),
            "devices": devices,
        }
    )


async def api_avatar(request):
    if not await authorized():
        raise web.HTTPUnauthorized()
    try:
        entity_id = int(request.match_info["entity_id"])
    except ValueError:
        raise web.HTTPBadRequest()
    path = AVATARS / f"{entity_id}.jpg"
    if not path.exists():
        try:
            entity = await S.client.get_entity(entity_id)
            saved = await S.client.download_profile_photo(entity, file=str(path))
            if not saved or not path.exists():
                raise FileNotFoundError()
        except Exception:
            raise web.HTTPNotFound()
    return web.FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})


def safe_export_path(relative):
    source = (EXPORTS / relative).resolve()
    root = EXPORTS.resolve()
    if source != root and root not in source.parents:
        raise web.HTTPForbidden()
    return source


async def api_download(request):
    if not await authorized():
        raise web.HTTPUnauthorized()
    source = safe_export_path(request.query.get("path", ""))
    if not source.is_file():
        raise web.HTTPNotFound()
    archive_name = source.stem + ".zip"
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False, dir=RUNTIME) as handle:
        temp = Path(handle.name)
    try:
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            if source.parent == EXPORTS and source.name == "index.html":
                for item in EXPORTS.rglob("*"):
                    if item.is_file():
                        archive.write(item, item.relative_to(EXPORTS))
            elif source.parent == EXPORTS:
                archive.write(source, source.name)
            else:
                for item in source.parent.rglob("*"):
                    if item.is_file():
                        archive.write(item, item.relative_to(source.parent))
        payload = temp.read_bytes()
    finally:
        temp.unlink(missing_ok=True)
    return web.Response(
        body=payload,
        content_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(archive_name)}",
            "Cache-Control": "no-store",
        },
    )


async def api_delete_export(request):
    if not await authorized():
        raise web.HTTPUnauthorized()
    data = await json_body(request)
    source = safe_export_path(str(data.get("path", "")))
    if not source.exists() or source == EXPORTS.resolve():
        raise web.HTTPNotFound()
    target = source if source.parent == EXPORTS else source.parent
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    S.log(f"Архив удалён: {source.name}")
    return web.json_response({"ok": True})


async def api_dialogs(_request):
    if not await authorized():
        raise web.HTTPUnauthorized()
    result = []
    async for dialog in S.client.iter_dialogs(limit=150):
        entity = dialog.entity
        result.append(
            {
                "id": dialog.id,
                "name": get_entity_name(entity),
                "username": getattr(entity, "username", None),
                "kind": (
                    "bot"
                    if isinstance(entity, User) and entity.bot
                    else "user"
                    if isinstance(entity, User)
                    else "channel"
                    if getattr(entity, "broadcast", False)
                    else "group"
                ),
                "avatar": f"/api/avatar/{entity.id}" if getattr(entity, "photo", None) else None,
            }
        )
    return web.json_response(result)


def safe_dump_name(value, fallback="Telegram dump"):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', ' ', str(value or ''))
    name = re.sub(r'\s+', ' ', name).strip(' .')[:80]
    if not name:
        name = fallback
    if name.upper() in {'CON','PRN','AUX','NUL','COM1','COM2','COM3','LPT1','LPT2','LPT3'}:
        name = '_' + name
    return name


def replace_path(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination) if destination.is_dir() else destination.unlink()
    source.replace(destination)


def publish_named_dump(temp_root, result, entity):
    source_dir = Path(result['path']).parent
    display_name = safe_dump_name(result.get('name') or get_entity_name(entity))
    entity_id = abs(int(getattr(entity, 'id', result.get('id', 0)) or 0))
    destination = EXPORTS / f"{display_name}_{entity_id}"
    replace_path(source_dir, destination)
    old_html = destination / Path(result['path']).name
    new_html = destination / f"{display_name}.html"
    if old_html != new_html:
        old_html.replace(new_html)
    shutil.rmtree(temp_root, ignore_errors=True)
    return new_html


def publish_full_dump(temp_root):
    for child in list(temp_root.iterdir()):
        replace_path(child, EXPORTS / child.name)
    shutil.rmtree(temp_root, ignore_errors=True)
    return EXPORTS / 'index.html'


async def run_export(kind, target=""):
    temp_root = EXPORTS / f".partial-{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)
    S.begin_operation("Подготовка экспорта")

    def progress(percent, current=0, total=0, stage="Обработка"):
        S.update_operation(percent, current, total, stage)

    try:
        if kind == "dialog":
            entity = await S.client.get_entity(target)
            S.operation_log(f"Диалог: {get_entity_name(entity)}")
            result = await save_dialog(
                S.client, entity, str(temp_root), progress_callback=progress)
            S.result = str(publish_named_dump(temp_root, result, entity))

        elif kind == "channel":
            entity = await S.client.get_entity(target)
            S.operation_log(f"Канал: {get_entity_name(entity)}")
            result = await save_channel(
                S.client, entity, str(temp_root), progress_callback=progress)
            S.result = str(publish_named_dump(temp_root, result, entity))

        elif kind == "saved":
            entity = await S.client.get_entity("me")
            S.operation_log("Диалог: Избранное")
            result = await save_dialog(
                S.client, entity, str(temp_root), progress_callback=progress)
            result['name'] = 'Избранное'
            S.result = str(publish_named_dump(temp_root, result, entity))

        elif kind == "all":
            S.stage = "Получение списка диалогов"
            dialogs = [dialog async for dialog in S.client.iter_dialogs()
                       if isinstance(dialog.entity, User)]
            total_dialogs = len(dialogs)
            for index, dialog in enumerate(dialogs):
                name = get_entity_name(dialog.entity)
                S.operation_log(f"Диалог {index + 1}/{total_dialogs}: {name}")

                def mapped(percent, current=0, total=0, stage="Обработка"):
                    overall = ((index + float(percent) / 100) / max(total_dialogs, 1)) * 96
                    S.update_operation(overall, index + 1, total_dialogs,
                                       f"{name}: {stage}")

                await save_dialog(S.client, dialog.entity, str(temp_root),
                                  progress_callback=mapped)
            S.update_operation(97, total_dialogs, total_dialogs, "Создание индекса")
            await generate_index(
                S.client,
                await fetch_user_info(S.client, str(temp_root)),
                await fetch_dialogs(S.client, str(temp_root)),
                str(temp_root),
            )
            S.result = str(publish_full_dump(temp_root))

        elif kind == "account":
            S.update_operation(10, 0, 0, "Сбор информации аккаунта")
            S.result = await get_full_account_info(S.client, str(temp_root))
            S.update_operation(95, 0, 0, "Публикация файла")
            source = Path(S.result)
            destination = EXPORTS / source.name
            replace_path(source, destination)
            shutil.rmtree(temp_root, ignore_errors=True)
            S.result = str(destination)

        S.update_operation(100, S.total, S.total, "Готово")
        S.cancellable = False
        S.operation_log(f"Готово: {S.result}")
    except asyncio.CancelledError:
        shutil.rmtree(temp_root, ignore_errors=True)
        S.stage = "Отменено"
        S.log("Операция отменена — временные файлы удалены")
        S.cancel_operation_ui()
    except Exception as error:
        shutil.rmtree(temp_root, ignore_errors=True)
        S.stage = "Ошибка"
        S.cancellable = False
        S.operation_log(f"{type(error).__name__}: {error}")
        traceback.print_exc()


async def api_export(request):
    if not await authorized():
        raise web.HTTPUnauthorized()
    if S.task and not S.task.done():
        raise web.HTTPConflict(text="Экспорт уже выполняется")
    data = await json_body(request)
    kind = data.get("kind")
    target = str(data.get("target", "")).strip()
    if kind not in {"dialog", "channel", "saved", "all", "account"}:
        raise ValueError("Неизвестный тип экспорта")
    if kind in {"dialog", "channel"} and not target:
        raise ValueError("Укажи username или ID")
    S.task = asyncio.create_task(run_export(kind, target))
    return web.json_response({"ok": True})


async def api_cancel(_request):
    if S.task and not S.task.done():
        S.cancellable = False
        S.stage = "Отмена…"
        S.task.cancel()
        try:
            await S.task
        except asyncio.CancelledError:
            pass
    return web.json_response({"ok": True})


async def api_files(_request):
    files = []
    for path in EXPORTS.rglob("*"):
        relative_path = path.relative_to(EXPORTS)
        if any(part.startswith(".partial-") for part in relative_path.parts):
            continue
        if path.is_file() and (path.suffix.lower() == ".html" or (path.parent == EXPORTS and path.name.startswith("account_info_") and path.suffix.lower() == ".txt")):
            relative = str(relative_path)
            files.append(
                {
                    "name": path.name,
                    "path": relative,
                    "size": path.stat().st_size,
                    "download": "/api/download?path=" + quote(relative),
                }
            )
    return web.json_response(sorted(files, key=lambda item: item["path"]))


async def api_get_settings(_request):
    return web.json_response(public_settings())


async def api_save_settings(request):
    data = await json_body(request)
    old_config = read_config()
    new_config = dict(old_config)

    incoming_ui = data.get("ui", {})
    theme = incoming_ui.get("theme", "monet")
    if theme not in {"monet", "graphite", "ocean"}:
        raise ValueError("Неизвестная тема")
    new_config["ui"] = {
        "theme": theme,
        "effects": bool(incoming_ui.get("effects")),
        "compact": bool(incoming_ui.get("compact")),
        "avatars": bool(incoming_ui.get("avatars", True)),
        "auto_refresh": bool(incoming_ui.get("auto_refresh", True)),
    }

    incoming_proxy = data.get("proxy", {})
    old_proxy = proxy_settings(old_config)
    parsed = parse_proxy_url(incoming_proxy.get("url", ""))
    if parsed:
        incoming_proxy = {**incoming_proxy, **parsed}
    enabled = bool(incoming_proxy.get("enabled"))
    proxy_type = incoming_proxy.get("type", "socks5")
    if proxy_type not in {"socks5", "mtproxy"}:
        raise ValueError("Поддерживаются SOCKS5 и MTProxy")
    host = str(incoming_proxy.get("host", "")).strip()
    port = int(incoming_proxy.get("port") or 0)
    if enabled and (not host or not 1 <= port <= 65535):
        raise ValueError("Укажи адрес и корректный порт прокси")
    password = incoming_proxy.get("password") or old_proxy.get("password", "")
    secret = incoming_proxy.get("secret") or old_proxy.get("secret", "")
    if enabled and proxy_type == "mtproxy" and not secret:
        raise ValueError("Для MTProxy нужен secret")
    new_config["proxy"] = {
        "enabled": enabled,
        "type": proxy_type,
        "host": host,
        "port": port,
        "username": str(incoming_proxy.get("username", "")).strip(),
        "password": password,
        "secret": secret,
    }

    proxy_changed = new_config.get("proxy") != old_proxy
    write_config(new_config)
    if proxy_changed:
        was_authorized = bool(S.account)
        if S.client:
            await S.client.disconnect()
            S.client = None
        S.account = None
        S.auth_checked = True
        try:
            client = await ensure_client()
            if was_authorized and await client.is_user_authorized():
                await refresh_account()
            S.log("Настройки прокси применены")
        except Exception as error:
            write_config(old_config)
            if S.client:
                await S.client.disconnect()
                S.client = None
            S.account = None
            try:
                client = await ensure_client()
                if was_authorized and await client.is_user_authorized():
                    await refresh_account()
            except Exception:
                pass
            raise ValueError(f"Не удалось подключиться через прокси: {error}")
    return web.json_response({"ok": True, **public_settings()})


@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as error:
        return web.json_response({"error": str(error)}, status=400)


async def cleanup(_app):
    if S.client:
        await S.client.disconnect()


def local_ip():
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        probe.close()
        return ip
    except Exception:
        return "127.0.0.1"


def make_app():
    app = web.Application(middlewares=[error_middleware], client_max_size=12 * 1024**2)
    app.router.add_get("/", page)
    app.router.add_static("/static", ROOT / "web" / "static")
    app.router.add_static("/exports", EXPORTS, show_index=True)
    app.router.add_get("/api/status", api_status)
    app.router.add_post("/api/auth/send-code", api_send_code)
    app.router.add_post("/api/auth/sign-in", api_sign_in)
    app.router.add_post("/api/auth/password", api_password)
    app.router.add_post("/api/auth/reset", api_reset_auth)
    app.router.add_post("/api/auth/logout", api_logout)
    app.router.add_post("/api/auth/import-session", api_import_session)
    app.router.add_get("/api/profile", api_profile)
    app.router.add_get("/api/avatar/{entity_id}", api_avatar)
    app.router.add_get("/api/dialogs", api_dialogs)
    app.router.add_post("/api/export", api_export)
    app.router.add_post("/api/cancel", api_cancel)
    app.router.add_get("/api/files", api_files)
    app.router.add_get("/api/download", api_download)
    app.router.add_post("/api/exports/delete", api_delete_export)
    app.router.add_get("/api/settings", api_get_settings)
    app.router.add_post("/api/settings", api_save_settings)
    app.on_cleanup.append(cleanup)
    return app


def free_port(host, preferred):
    check_host = "127.0.0.1" if host == "0.0.0.0" else host
    for port in range(preferred, preferred + 50):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((check_host, port))
            return port
        except OSError:
            pass
        finally:
            probe.close()
    raise RuntimeError(f"Не найден свободный порт начиная с {preferred}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    requested = args.port
    args.port = free_port(args.host, args.port)
    url = f"http://127.0.0.1:{args.port}"
    print("\n" + "=" * 52)
    if args.port != requested:
        print(f" Порт {requested} занят — выбран {args.port}")
    print(f" TG DUMP WEB запущен\n Открой: {url}")
    if args.host != "127.0.0.1":
        print(f" В локальной сети: http://{local_ip()}:{args.port}")
    print("=" * 52 + "\n")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    web.run_app(make_app(), host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
