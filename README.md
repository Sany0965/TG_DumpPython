
# Telegram Dialog Exporter 📂 UPDATE 8.0

Экспортируйте свои диалоги из Telegram в стильные HTML-архивы с медиафайлами и удобной навигацией!

**Скрипт создан [@worpli](https://t.me/worpli)** 🚀

## Возможности ✨
- 📌 **Дамп отдельных диалогов** или **всех личных чатов**
- 🎨 Автоматическая генерация красивого индекса:
  - Информация о вашем аккаунте (аватар, био, подключенные устройства)
  - Сортировка диалогов по типам (Пользователи, Каналы, Чаты)
- 🌈 Стильные анимации и адаптивный дизайн
- 📂 Сохранение медиа:
  - Фото/Видео/Аудио/Стикеры/Файлы
  - Геолокации (ссылки на OpenStreetMap)
- 🔒 Локальное хранение данных (все файлы остаются на вашем устройстве)

## Что сохраняется? 📁
- **Диалоги с пользователями и ботами**: Полностью сохраняются все сообщения, медиафайлы и пересланные сообщения.
- **Каналы**: Сохраняются только ссылки на каналы, посты не экспортируются.
- **Информация о подключенных устройствах**: Отображаются все устройства, с которых выполнен вход в аккаунт (модель, платформа, IP-адрес).

## Пример интерфейса 
### Главная страница
[Главная страница](https://TransFiles.ru/ey1y9)

### Пример диалога
[Пример диалога](https://TransFiles.ru/ey1y9)

**PS: Это скриншоты v.5, сейчас выглядит по другому**

## Установка 🛠️

### Скачайте файлы
1. Нажмите на кнопку **Code** вверху страницы репозитория.
2. Выберите **Download ZIP**
3. ЛИБО же перейдите в Релизы по этой ссылке https://github.com/Sany0965/TG_DumpPython/releases

### Установите зависимости
Убедитесь, что у вас установлен Python 3.7 или выше, затем выполните:
```bash
pip install telethon
```

### Настройка API
1. Получите API ID и Hash:
   - Зарегистрируйте приложение на [my.telegram.org](https://my.telegram.org/apps)
2. Заполните данные в `app.py`:
```python
api_id = 1234567       # Ваш API ID
api_hash = 'ваш_api_hash'  # Ваш API Hash
```

## Использование 🚀
Запустите скрипт и следуйте инструкциям:
```bash
python app.py
```

**Доступные опции:**
1. **Экспорт одного диалога** - введите username контакта
2. **Экспорт всех личных диалогов** - автоматическая обработка всех чатов
3. **Экспорт данных канала** - сохранение истории постов канала

Результаты сохраняются в папку `dialogs/`. Откройте `index.html` для просмотра архива.

## Особенности разработки 💡
- Модульная структура (отдельные файлы для логики, стилей и генерации)
- Асинхронная обработка сообщений
- Прогресс-бар для отслеживания процесса
- Обработка ошибок при скачивании медиа
- Кастомные User-Agent заголовки для клиента Telegram

## Ограничения ⚠️
- Требуется активная сессия Telegram
- Нет поддержки секретных чатов
- Ограничения API Telegram (скорость/лимиты запросов)
- Каналы сохраняются только в виде ссылок, посты не экспортируются
