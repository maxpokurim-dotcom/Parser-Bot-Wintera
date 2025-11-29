"""
Main menu and navigation handler
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
    msg = text or "📋 <b>Главное меню</b>\nВыберите действие:"
    send_message(chat_id, msg, kb_main_menu())

def handle_start(chat_id: int, user_id: int):
    """Handle /start command"""
    DB.clear_user_state(user_id)
    send_message(chat_id,
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Я бот для парсинга аудитории и рассылки в Telegram.\n\n"
        "<b>Возможности:</b>\n"
        "• 🔍 Парсинг пользователей из чатов\n"
        "• 💬 Парсинг авторов комментариев\n"
        "• 📤 Массовая рассылка\n"
        "• 👤 Управление несколькими аккаунтами\n\n"
        "Выберите действие в меню 👇",
        kb_main_menu()
    )

def handle_cancel(chat_id: int, user_id: int):
    """Handle cancel button"""
    show_main_menu(chat_id, user_id, "❌ Действие отменено\n\n📋 <b>Главное меню</b>")

def handle_back(chat_id: int, user_id: int, saved: dict):
    """Handle back button - return to previous state"""
    prev_state = saved.get('prev_state', '')
    
    if prev_state:
        # Return to previous state
        DB.set_user_state(user_id, prev_state, saved.get('prev_data', {}))
        # Will be handled by appropriate handler
        return prev_state
    else:
        # Return to main menu
        show_main_menu(chat_id, user_id)
        return None
