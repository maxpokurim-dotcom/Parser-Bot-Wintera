"""
Statistics handlers - Extended v2.0
With hourly stats, negative responses, account predictions
"""
import logging
from datetime import datetime
from core.db import DB
from core.telegram import send_message
from core.keyboards import (
    kb_main_menu, kb_stats_menu, kb_back,
    kb_inline_hourly_stats
)
from core.menu import show_main_menu, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_ERRORS = '📉 Ошибки за 7 дней'
BTN_TOP_AUDIENCES = '🏆 Топ аудиторий'
BTN_ACTIVE_MAILINGS = '📊 Активные рассылки'
BTN_HOURLY_STATS = '⏰ Статистика по часам'
BTN_NEGATIVE_RESPONSES = '🛡 Негативные ответы'


def show_stats_menu(chat_id: int, user_id: int):
    """Show statistics menu"""
    DB.set_user_state(user_id, 'stats:menu')
    
    stats = DB.get_user_stats(user_id)
    success_rate = stats.get('success_rate', 0)
    
    # Get best hours
    best_hours = DB.get_best_hours(user_id, limit=3)
    best_hours_str = ', '.join(f'{h}:00' for h in best_hours) if best_hours else 'нет данных'
    
    # Get current delay multiplier
    current_hour = datetime.utcnow().hour
    delay_mult = DB.get_delay_multiplier_for_hour(user_id, current_hour)
    delay_info = ""
    if delay_mult != 1.0:
        delay_info = f"\n⏱ Множитель задержки сейчас: <b>x{delay_mult:.1f}</b>"
    
    send_message(chat_id,
        f"📈 <b>Статистика</b>\n\n"
        f"📊 <b>Аудитории:</b> {stats['audiences']} (готовых: {stats['audiences_completed']})\n"
        f"📄 <b>Шаблоны:</b> {stats['templates']}\n"
        f"👤 <b>Аккаунты:</b> {stats['accounts']} (активных: {stats['accounts_active']})\n"
        f"📤 <b>Кампании:</b> {stats['campaigns']}\n\n"
        f"👥 <b>Всего спарсено:</b> {stats['total_parsed']}\n"
        f"✅ <b>Отправлено:</b> {stats['total_sent']}\n"
        f"❌ <b>Ошибок:</b> {stats['total_failed']}\n"
        f"📊 <b>Успешность:</b> {success_rate}%\n\n"
        f"⏰ <b>Лучшие часы:</b> {best_hours_str}{delay_info}",
        kb_stats_menu()
    )


def handle_stats(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle statistics states. Returns True if handled."""
    
    if text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return True
    
    if text == BTN_BACK:
        if state == 'stats:menu':
            show_main_menu(chat_id, user_id)
        else:
            show_stats_menu(chat_id, user_id)
        return True
    
    # Menu state
    if state == 'stats:menu':
        if text == BTN_ERRORS:
            show_error_stats(chat_id, user_id)
            return True
        if text == BTN_TOP_AUDIENCES:
            show_top_audiences(chat_id, user_id)
            return True
        if text == BTN_ACTIVE_MAILINGS:
            show_active_mailings_stats(chat_id, user_id)
            return True
        if text == BTN_HOURLY_STATS or text == '⏰ Статистика по часам':
            show_hourly_stats(chat_id, user_id)
            return True
        if text == BTN_NEGATIVE_RESPONSES or text == '🛡 Негативные ответы':
            show_negative_responses(chat_id, user_id)
            return True
    
    return False


def show_error_stats(chat_id: int, user_id: int):
    """Show error statistics"""
    DB.set_user_state(user_id, 'stats:errors')
    
    errors = DB.get_error_stats(user_id, days=7)
    
    if not errors:
        send_message(chat_id,
            "📉 <b>Ошибки за 7 дней</b>\n\n"
            "✅ Ошибок не обнаружено!\n\n"
            "Всё работ
