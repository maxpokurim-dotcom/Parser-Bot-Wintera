# VPS Worker для Telegram Bot

Серверная часть (backend) для Telegram бота, развёрнутого на Vercel. VPS Worker выполняет все тяжёлые операции:

- 📤 **Рассылка сообщений** — массовая отправка через несколько аккаунтов
- 🔍 **Парсинг аудитории** — сбор пользователей из каналов/чатов
- 🔐 **Авторизация аккаунтов** — автоматическая авторизация с SMS кодами
- 🤖 **Ботовод** — симуляция активности в каналах (реакции, комментарии)
- 🔥 **Прогрев аккаунтов** — постепенная подготовка к работе
- ⏰ **Планировщик** — отложенные и повторяющиеся задачи

## Архитектура

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Telegram User     │────▶│  Vercel Bot      │────▶│    Supabase     │
│                     │     │  (UI/Interface)  │     │    (Database)   │
└─────────────────────┘     └──────────────────┘     └────────┬────────┘
                                                              │
                                                              │ poll
                                                              ▼
                                                    ┌─────────────────┐
                                                    │   VPS Worker    │
                                                    │   (Backend)     │
                                                    ├─────────────────┤
                                                    │ • Auth Worker   │
                                                    │ • Mailing Worker│
                                                    │ • Parsing Worker│
                                                    │ • Herder Worker │
                                                    │ • Warmup Worker │
                                                    │ • Scheduler     │
                                                    └─────────────────┘
```

## Требования

- Ubuntu 24.04 (или другой Linux)
- Python 3.12+
- 1GB RAM минимум
- Доступ к Supabase (та же БД, что и у бота)

## Быстрая установка

```bash
# Скачать и распаковать
cd /tmp
git clone https://github.com/your-repo/vps_worker.git
cd vps_worker

# Установить
sudo bash install.sh

# Настроить
sudo nano /opt/vps_worker/.env

# Запустить
sudo systemctl start vps-worker
sudo systemctl status vps-worker
```

## Ручная установка

```bash
# 1. Установить зависимости
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip git

# 2. Создать директории
sudo mkdir -p /opt/vps_worker
sudo mkdir -p /var/log/vps_worker

# 3. Скопировать файлы
sudo cp -r * /opt/vps_worker/

# 4. Создать виртуальное окружение
cd /opt/vps_worker
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Настроить
cp .env.example .env
nano .env

# 6. Установить сервис
sudo cp vps-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vps-worker
sudo systemctl start vps-worker
```

## Конфигурация (.env)

```bash
# Supabase (обязательно - та же БД что и у бота на Vercel)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Telegram API (обязательно - получить на https://my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your-api-hash

# Бот для уведомлений
BOT_TOKEN=123456789:AABBccDDeeFFggHH
ADMIN_CHAT_ID=123456789

# Опционально
ONLINESIM_API_KEY=      # Для авто-создания аккаунтов
OPENAI_API_KEY=         # Для генерации контента
DEFAULT_PROXY=          # socks5://user:pass@host:port
```

## Управление сервисом

```bash
# Статус
sudo systemctl status vps-worker

# Запуск/Остановка/Перезапуск
sudo systemctl start vps-worker
sudo systemctl stop vps-worker
sudo systemctl restart vps-worker

# Логи
journalctl -u vps-worker -f
tail -f /var/log/vps_worker/worker.log
tail -f /opt/vps_worker/logs/vps_worker.log
```

## Структура проекта

```
vps_worker/
├── main.py                 # Главный файл
├── config.py               # Конфигурация
├── requirements.txt        # Python зависимости
├── .env.example           # Пример конфигурации
├── install.sh             # Скрипт установки
├── vps-worker.service     # Systemd сервис
│
├── services/              # Сервисы
│   ├── database.py        # Работа с Supabase
│   ├── notifier.py        # Уведомления админу
│   └── telegram_client.py # Telethon клиент
│
├── workers/               # Воркеры (фоновые задачи)
│   ├── auth_worker.py     # Авторизация аккаунтов
│   ├── mailing_worker.py  # Рассылка сообщений
│   ├── parsing_worker.py  # Парсинг аудитории
│   ├── herder_worker.py   # Ботовод
│   ├── warmup_worker.py   # Прогрев аккаунтов
│   └── scheduler_worker.py # Планировщик
│
├── utils/                 # Утилиты
│   ├── logger.py          # Логирование
│   └── helpers.py         # Вспомогательные функции
│
├── sessions/              # Сессии Telegram (авто-создаётся)
├── logs/                  # Логи (авто-создаётся)
└── data/                  # Данные (авто-создаётся)
```

## Как это работает

1. **Telegram бот на Vercel** принимает команды от пользователей и сохраняет задачи в Supabase
2. **VPS Worker** периодически проверяет БД на новые задачи
3. Воркеры выполняют задачи:
   - `AuthWorker` — авторизация новых аккаунтов
   - `MailingWorker` — отправка сообщений
   - `ParsingWorker` — парсинг аудитории
   - `HerderWorker` — симуляция активности
   - `WarmupWorker` — прогрев аккаунтов
   - `SchedulerWorker` — запуск отложенных задач
4. Результаты сохраняются в БД и отображаются в боте

## Безопасность

- Все сессии хранятся в `/opt/vps_worker/sessions/`
- `.env` файл доступен только root
- Сервис работает под пользователем www-data
- Поддержка прокси для каждого аккаунта

## Мониторинг

Worker отправляет уведомления в Telegram:
- 🟢 Запуск/остановка воркера
- 📤 Прогресс рассылок
- ⚠️ Ошибки и FloodWait
- ✅ Завершение задач

## Решение проблем

### Worker не запускается
```bash
# Проверить логи
journalctl -u vps-worker -n 50

# Проверить конфигурацию
cat /opt/vps_worker/.env

# Запустить вручную для отладки
cd /opt/vps_worker
source venv/bin/activate
python main.py
```

### Ошибки авторизации
- Проверьте TELEGRAM_API_ID и TELEGRAM_API_HASH
- Убедитесь что номер телефона корректный
- Проверьте нет ли бана на номер

### FloodWait
- Увеличьте задержки в настройках
- Используйте больше аккаунтов
- Уменьшите интенсивность рассылки

## Обновление

```bash
cd /tmp
git clone https://github.com/your-repo/vps_worker.git

# Остановить сервис
sudo systemctl stop vps-worker

# Обновить файлы (без .env и sessions)
sudo cp -r vps_worker/* /opt/vps_worker/
sudo rm -rf /opt/vps_worker/.git

# Обновить зависимости
cd /opt/vps_worker
source venv/bin/activate
pip install -r requirements.txt

# Запустить
sudo systemctl start vps-worker
```

## Лицензия

MIT License
