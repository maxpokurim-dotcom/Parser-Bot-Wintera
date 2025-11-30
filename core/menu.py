"""
Main menu and navigation handler - Extended v2.0
With Panic Stop command
"""
import logging
from core.db import DB
from core.telegram import send_message
from core.keyboards import kb_main_menu

logger = logging.getLogger(__name__)

# Button text constants for matching
BTN_PARSING_CHATS = '🔍 Парсинг чатов'
BTN_COMMENTS = '💬 Комментарии'
BTN_AUDIENCES = '📊 Аудитории'
BTN_TEMPLATES = '📄 Шаблоны'
BTN_ACCOUNTS = '👤 Аккаунты'
BTN_MAILING = '📤 Рассылка'
BTN_STATS = '📈 Статистика'
BTN_SETTINGS = '⚙️ Настройки'
BTN_CANCEL = '❌ Отмена'
BTN_BACK = '◀️ Назад'
BTN_MAIN_MENU = '◀️ Главное меню'


def show_main_menu(chat_id: int, user_id: int, text: str = None):
    """Show main menu"""
    DB.clear_user_state(user_id)
    
    # Проверяем статус системы
    if DB.is_system_paused(user_id):
        status = DB.get_system_status(user_id)
        reason = status.get('pause_reason', 'Неизвестно')
        msg = (
            f"🚨 <b>СИСТЕМА ПРИОСТАНОВЛЕНА</b>\n\n"
            f"Причина: {reason}\n\n"
            f"Для возобновления используйте /resume\n\n"
            f"{'─' * 20}\n\n"
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
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Я бот для парсинга аудитории и рассылки в Telegram.\n\n"
        "<b>Возможности:</b>\n"
        "• 🔍 Парсинг пользователей из чатов\n"
        "• 💬 Парсинг авторов комментариев\n"
        "• 🔑 Парсинг по ключевым словам\n"
        "• 📤 Умная рассылка с адаптивными задержками\n"
        "• 👤 Управление несколькими аккаунтами\n"
        "• 🛡 Автоматическая защита от банов\n\n"
        "<b>Команды:</b>\n"
        "/menu — главное меню\n"
        "/stats — статистика\n"
        "/panic — экстренная остановка\n"
        "/resume — возобновить работу\n\n"
        "Выберите действие в меню 👇",
        kb_main_menu()
    )


def handle_cancel(chat_id: int, user_id: int):
    """Handle cancel button"""
    show_main_menu(chat_id, user_id, "❌ Действие отменено\n\n📋 <b>Главное меню</b>")


def handle_panic_stop(chat_id: int, user_id: int):
    """Handle /panic command - emergency stop"""
    # Приостанавливаем все кампании
    DB.pause_all_campaigns(user_id, reason='Panic stop')
    
    # Устанавливаем флаг паузы
    DB.set_panic_stop(user_id, reason='Manual panic stop via /panic')
    
    send_message(chat_id,
        "🚨 <b>ЭКСТРЕННАЯ ОСТАНОВКА АКТИВИРОВАНА</b>\n\n"
        "✅ Все рассылки приостановлены\n"
        "✅ Все задачи парсинга остановлены\n"
        "✅ Воркеры получили сигнал остановки\n\n"
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
        "✅ <b>Работа возобновлена</b>\n\n"
        "Система снова активна.\n"
        "Приостановленные рассылки можно возобновить вручную в разделе «📤 Рассылка».",
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
