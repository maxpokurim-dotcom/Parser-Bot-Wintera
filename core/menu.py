"""
Main menu and navigation handler - Restructured v1.0
Simplified into 4 logical sections:
1. 📥 Исходящие действия (Parsing, Mailing, Content)
2. 🤖 Управление аккаунтами (Accounts, Factory, Herder)
3. 📊 Аналитика и данные (Audiences, Templates, Analytics)
4. ⚙️ Настройки
"""
import logging
from core.db import DB
from core.telegram import send_message
from core.keyboards import kb_main_menu, kb_outbound_menu, kb_accounts_menu, kb_analytics_menu
logger = logging.getLogger(__name__)

# Button text constants for matching
BTN_OUTBOUND = '📥 Исходящие действия'
BTN_ACCOUNTS_HUB = '🤖 Управление аккаунтами'
BTN_ANALYTICS_DATA = '📊 Аналитика и данные'
BTN_SETTINGS = '⚙️ Настройки'

# Navigation
BTN_CANCEL = '❌ Отмена'
BTN_BACK = '◀️ Назад'
BTN_MAIN_MENU = '◀️ Главное меню'
BTN_SKIP = '⏭ Пропустить'

def show_main_menu(chat_id: int, user_id: int, text: str = None):
    """Show main menu"""
    DB.clear_user_state(user_id)
    # Проверяем статус системы
    if DB.is_system_paused(user_id):
        status = DB.get_system_status(user_id)
        reason = status.get('pause_reason', 'Неизвестно')
        msg = (
            f"🚨 <b>СИСТЕМА ПРИОСТАНОВЛЕНА</b>\n"
            f"Причина: {reason}\n"
            f"Для возобновления используйте /resume\n"
            f"{'─' * 20}\n"
        )
        msg += text or "📋 <b>Главное меню</b>\nВыберите действие:"
    else:
        msg = text or "📋 <b>Главное меню</b>\nВыберите действие:"
    send_message(chat_id, msg, kb_main_menu())

def handle_start(chat_id: int, user_id: int):
    """Handle /start command"""
    DB.clear_user_state(user_id)
    # Инициализируем дефолтные стоп-триггеры
    DB.get_stop_triggers(user_id)
    send_message(chat_id,
        "👋 <b>Добро пожаловать!</b>\n"
        "Я бот для парсинга, рассылки и автоматизации в Telegram.\n"
        "<b>🔥 Основные возможности:</b>\n"
        "• 🔍 Парсинг пользователей из чатов\n"
        "• 💬 Парсинг авторов комментариев\n"
        "• 📤 Умная рассылка с адаптивными задержками\n"
        "• 👤 Управление несколькими аккаунтами\n"
        "<b>🤖 Новые модули:</b>\n"
        "• 🤖 <b>Ботовод</b> — симуляция живой активности\n"
        "• 🏭 <b>Фабрика</b> — создание и прогрев аккаунтов\n"
        "• 📝 <b>Контент</b> — генерация постов с ИИ\n"
        "• 📈 <b>Аналитика</b> — прогнозы и оптимизация\n"
        "<b>Команды:</b>\n"
        "/menu — главное меню\n"
        "/stats — статистика\n"
        "/panic — экстренная остановка\n"
        "/resume — возобновить работу\n"
        "Выберите действие в меню 👇",
        kb_main_menu()
    )

def handle_cancel(chat_id: int, user_id: int):
    """Handle cancel button"""
    show_main_menu(chat_id, user_id, "❌ Действие отменено\n📋 <b>Главное меню</b>")

def handle_panic_stop(chat_id: int, user_id: int):
    """Handle /panic command - emergency stop"""
    # Приостанавливаем все кампании
    DB.pause_all_campaigns(user_id, reason='Panic stop')
    # Приостанавливаем все задания ботовода
    assignments = DB.get_herder_assignments(user_id, status='active')
    for a in assignments:
        DB.pause_herder_assignment(a['id'])
    # Устанавливаем флаг паузы
    DB.set_panic_stop(user_id, reason='Manual panic stop via /panic')
    send_message(chat_id,
        "🚨 <b>ЭКСТРЕННАЯ ОСТАНОВКА АКТИВИРОВАНА</b>\n"
        "✅ Все рассылки приостановлены\n"
        "✅ Все задания ботовода приостановлены\n"
        "✅ Все задачи парсинга остановлены\n"
        "✅ Воркеры получили сигнал остановки\n"
        "Для возобновления работы используйте /resume",
        kb_main_menu()
    )

def handle_resume(chat_id: int, user_id: int):
    """Handle /resume command - resume after panic stop"""
    if not DB.is_system_paused(user_id):
        send_message(chat_id,
            "ℹ️ Система не была приостановлена.",
            kb_main_menu()
        )
        return
    DB.clear_panic_stop(user_id)
    send_message(chat_id,
        "✅ <b>Работа возобновлена</b>\n"
        "Система снова активна.\n"
        "Приостановленные рассылки и задания ботовода\n"
        "можно возобновить вручную в соответствующих разделах.",
        kb_main_menu()
    )

def handle_back(chat_id: int, user_id: int, saved: dict):
    """Handle back button - return to previous state"""
    prev_state = saved.get('prev_state', '')
    if prev_state:
        DB.set_user_state(user_id, prev_state, saved.get('prev_data', {}))
        return prev_state
    else:
        show_main_menu(chat_id, user_id)
        return None

def handle_help(chat_id: int, user_id: int):
    """Handle /help command"""
    send_message(chat_id,
        "📚 <b>Справка по боту</b>\n"
        "<b>Основные команды:</b>\n"
        "/start — начать работу\n"
        "/menu — главное меню\n"
        "/stats — статистика\n"
        "/panic — экстренная остановка всего\n"
        "/resume — возобновить после паники\n"
        "/help — эта справка\n"
        "<b>Модули:</b>\n"
        "📥 <b>Исходящие действия</b>\n"
        "   • 🔍 <b>Парсинг</b> — сбор аудитории\n"
        "   • 📤 <b>Рассылка</b> — отправка сообщений\n"
        "   • 📝 <b>Контент</b> — ИИ-генерация постов\n"
        "🤖 <b>Управление аккаунтами</b>\n"
        "   • 👤 <b>Аккаунты</b> — статус и надёжность\n"
        "   • 🏭 <b>Фабрика</b> — создание и прогрев\n"
        "   • 🤖 <b>Ботовод</b> — симуляция активности\n"
        "📊 <b>Аналитика и данные</b>\n"
        "   • 👥 <b>Аудитории</b> — управление базой\n"
        "   • 📄 <b>Шаблоны</b> — заготовки сообщений\n"
        "   • 📈 <b>Аналитика</b> — Heatmap и риски\n"
        "⚙️ <b>Настройки</b>\n"
        "   • Настройки рассылки, поведения, API",
        kb_main_menu()
    )

def show_quick_stats(chat_id: int, user_id: int):
    """Show quick dashboard stats"""
    stats = DB.get_dashboard_stats(user_id)
    msg = (
        "📊 <b>Быстрая статистика</b>\n"
        f"👥 Аудиторий: <b>{stats['audiences']}</b> ({stats['audiences_completed']} готовы)\n"
        f"📄 Шаблонов: <b>{stats['templates']}</b>\n"
        f"👤 Аккаунтов: <b>{stats['accounts']}</b> ({stats['accounts_active']} активны)\n"
        f"📤 Кампаний: <b>{stats['campaigns']}</b>\n"
        f"📈 Отправлено: <b>{stats['total_sent']}</b>\n"
        f"✅ Успешность: <b>{stats['success_rate']}%</b>\n"
        f"🤖 <b>Ботовод:</b>\n"
        f"   Активных заданий: {stats.get('herder_active_assignments', 0)}\n"
        f"   Каналов: {stats.get('monitored_channels', 0)}\n"
        f"   Действий: {stats.get('herder_actions', 0)}\n"
        f"🏭 <b>Прогрев:</b>\n"
        f"   В процессе: {stats.get('warmup_in_progress', 0)}\n"
        f"   Готовы: {stats.get('warmup_completed', 0)}\n"
    )
    if stats.get('high_risk_accounts', 0) > 0:
        msg += f"⚠️ <b>Внимание:</b> {stats['high_risk_accounts']} аккаунтов с высоким риском!"
    send_message(chat_id, msg, kb_main_menu())
