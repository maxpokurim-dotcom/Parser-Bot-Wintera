# 📋 Полная инструкция по установке VPS Worker

## Шаг 1: Получение файлов

### Вариант A: Скачать через Git (рекомендуется)

Создайте новый репозиторий на GitHub и загрузите туда папку `vps_worker`.

На VPS:
```bash
cd /root
git clone https://github.com/YOUR_USERNAME/telegram-worker.git
cd telegram-worker
```

### Вариант B: Загрузить через SFTP

1. Скачайте папку `vps_worker` из Cursor на свой компьютер
2. Используйте FileZilla или WinSCP для загрузки на VPS в `/root/telegram-worker`

### Вариант C: Копировать через SCP

```bash
# На локальном компьютере
scp -r /path/to/vps_worker root@YOUR_VPS_IP:/root/telegram-worker
```

---

## Шаг 2: Подключение к VPS

```bash
ssh root@YOUR_VPS_IP
```

---

## Шаг 3: Обновление системы

```bash
apt update && apt upgrade -y
```

---

## Шаг 4: Установка Python 3.12

```bash
# Проверить текущую версию
python3 --version

# Установить Python 3.12
apt install -y python3.12 python3.12-venv python3-pip

# Проверить
python3.12 --version
```

---

## Шаг 5: Создание структуры папок

```bash
# Перейти в папку проекта
cd /root/telegram-worker

# Создать необходимые директории
mkdir -p sessions logs data

# Установить права
chmod +x install.sh main.py
```

---

## Шаг 6: Создание виртуального окружения

```bash
# Создать venv
python3.12 -m venv venv

# Активировать
source venv/bin/activate

# Убедиться что активировано (должен быть префикс (venv))
which python
# Ожидаемый вывод: /root/telegram-worker/venv/bin/python
```

---

## Шаг 7: Установка зависимостей

```bash
# Обновить pip
pip install --upgrade pip

# Установить все зависимости
pip install -r requirements.txt

# Проверить установку Telethon
python -c "import telethon; print('Telethon OK:', telethon.__version__)"
```

---

## Шаг 8: Настройка конфигурации

```bash
# Создать .env из примера
cp .env.example .env

# Открыть для редактирования
nano .env
```

### Заполните обязательные поля:

```bash
# ===== SUPABASE (обязательно) =====
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx

# ===== TELEGRAM API (обязательно) =====
# Получить на https://my.telegram.org/apps
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef

# ===== БОТ ДЛЯ УВЕДОМЛЕНИЙ =====
BOT_TOKEN=123456789:AABBccDDeeFFggHHiiJJkkLLmmNNooP
ADMIN_CHAT_ID=123456789

# ===== YANDEX GPT (рекомендуется) =====
YANDEX_CLOUD_FOLDER_ID=b1gxxxxxxxxxx
YANDEX_CLOUD_API_KEY=AQVNxxxxxxxxxxxxx
YANDEX_GPT_MODEL=yandexgpt-lite

# ===== OPENAI (альтернатива) =====
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini

# ===== ONLINESIM (для авто-создания аккаунтов) =====
ONLINESIM_API_KEY=xxxxxxxxxxxxxxxx
ONLINESIM_DEFAULT_COUNTRY=ru
```

Сохранить: `Ctrl+O`, `Enter`, `Ctrl+X`

---

## Шаг 9: Тестирование подключений

```bash
# Убедиться что venv активирован
source venv/bin/activate

# Запустить тест
python test_connection.py
```

Ожидаемый вывод:
```
✅ PASS: Environment
✅ PASS: Config
✅ PASS: Supabase
✅ PASS: Telegram API
✅ PASS: Notifier
✅ PASS: YandexGPT
✅ PASS: OpenAI
✅ PASS: OnlineSim
```

---

## Шаг 10: Тестовый запуск

```bash
# Запустить вручную для проверки
python main.py
```

Ожидаемый вывод:
```
==================================================
VPS Worker starting...
Poll interval: 10s
Max concurrent tasks: 5
==================================================
Starting auth_worker (interval: 5s)
Starting mailing_worker (interval: 10s)
Starting parsing_worker (interval: 30s)
...
```

Остановить: `Ctrl+C`

---

## Шаг 11: Настройка systemd сервиса

```bash
# Создать systemd unit файл
cat > /etc/systemd/system/telegram-worker.service << 'EOF'
[Unit]
Description=Telegram Worker Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-worker
Environment="PATH=/root/telegram-worker/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/root/telegram-worker/venv/bin/python /root/telegram-worker/main.py
Restart=always
RestartSec=10
StandardOutput=append:/root/telegram-worker/logs/worker.log
StandardError=append:/root/telegram-worker/logs/error.log

[Install]
WantedBy=multi-user.target
EOF
```

---

## Шаг 12: Запуск сервиса

```bash
# Перезагрузить systemd
systemctl daemon-reload

# Включить автозапуск
systemctl enable telegram-worker

# Запустить
systemctl start telegram-worker

# Проверить статус
systemctl status telegram-worker
```

Ожидаемый вывод:
```
● telegram-worker.service - Telegram Worker Service
     Loaded: loaded (/etc/systemd/system/telegram-worker.service; enabled)
     Active: active (running) since ...
```

---

## Шаг 13: Мониторинг логов

```bash
# Реал-тайм логи
tail -f /root/telegram-worker/logs/worker.log

# Последние 100 строк
tail -100 /root/telegram-worker/logs/worker.log

# Ошибки
tail -f /root/telegram-worker/logs/error.log

# Через journalctl
journalctl -u telegram-worker -f
```

---

## 🔧 Команды управления

```bash
# Статус
systemctl status telegram-worker

# Запуск
systemctl start telegram-worker

# Остановка
systemctl stop telegram-worker

# Перезапуск
systemctl restart telegram-worker

# Логи
journalctl -u telegram-worker -f

# Логи за последний час
journalctl -u telegram-worker --since "1 hour ago"
```

---

## 🔄 Обновление

```bash
# Остановить сервис
systemctl stop telegram-worker

# Обновить файлы (git pull или scp)
cd /root/telegram-worker
git pull  # если используете git

# Обновить зависимости
source venv/bin/activate
pip install -r requirements.txt

# Запустить
systemctl start telegram-worker
```

---

## ⚠️ Решение проблем

### Сервис не запускается
```bash
# Проверить логи
journalctl -u telegram-worker -n 50

# Проверить права
ls -la /root/telegram-worker/

# Проверить .env
cat /root/telegram-worker/.env
```

### Ошибка "Module not found"
```bash
# Переустановить зависимости
cd /root/telegram-worker
source venv/bin/activate
pip install -r requirements.txt
```

### Ошибка подключения к Supabase
```bash
# Проверить URL и ключи в .env
# Убедиться что нет лишних пробелов
```

### FloodWait ошибки
- Увеличьте MAILING_DELAY_MIN и MAILING_DELAY_MAX в .env
- Используйте больше аккаунтов
- Включите FLOOD_PROTECTION=true

---

## 📊 Структура файлов после установки

```
/root/telegram-worker/
├── main.py              # Главный файл
├── config.py            # Конфигурация
├── .env                 # ← ВАШИ КЛЮЧИ (секретный!)
├── requirements.txt     # Зависимости
├── venv/                # Виртуальное окружение
├── sessions/            # Сессии Telegram
├── logs/                # Логи
│   ├── worker.log
│   └── error.log
├── data/                # Данные
├── services/            # Сервисы
├── workers/             # Воркеры
└── utils/               # Утилиты
```

---

## ✅ Чек-лист готовности

- [ ] Python 3.12 установлен
- [ ] Виртуальное окружение создано
- [ ] Зависимости установлены
- [ ] .env заполнен
- [ ] Тест подключений пройден
- [ ] Systemd сервис создан
- [ ] Сервис запущен и работает
- [ ] Логи пишутся
