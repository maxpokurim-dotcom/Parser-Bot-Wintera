"""
Statistics handlers
Static menu version
"""
import logging
from core.db import DB
from core.telegram import send_message
from core.keyboards import kb_main_menu, kb_stats_menu, kb_back
from core.menu import show_main_menu, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_ERRORS = '📉 Ошибки за 7 дней'
BTN_TOP_AUDIENCES = '🏆 Топ аудиторий'
BTN_ACTIVE_MAILINGS = '📊 Активные рассылки'


def show_stats_menu(chat_id: int, user_id: int):
    """Show statistics menu"""
    DB.set_user_state(user_id, 'stats:menu')
    
    stats = DB.get_user_stats(user_id)
    success_rate = stats.get('success_rate', 0)
    
    send_message(chat_id,
        f"📈 <b>Статистика</b>\n\n"
        f"📊 <b>Аудитории:</b> {stats['audiences']} (готовых: {stats['audiences_completed']})\n"
        f"📄 <b>Шаблоны:</b> {stats['templates']}\n"
        f"👤 <b>Аккаунты:</b> {stats['accounts']} (активных: {stats['accounts_active']})\n"
        f"📤 <b>Кампании:</b> {stats['campaigns']}\n\n"
        f"👥 <b>Всего спарсено:</b> {stats['total_parsed']}\n"
        f"✅ <b>Отправлено:</b> {stats['total_sent']}\n"
        f"❌ <b>Ошибок:</b> {stats['total_failed']}\n"
        f"📊 <b>Успешность:</b> {success_rate}%",
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
    
    return False


def show_error_stats(chat_id: int, user_id: int):
    """Show error statistics"""
    DB.set_user_state(user_id, 'stats:errors')
    
    errors = DB.get_error_stats(user_id, days=7)
    
    if not errors:
        send_message(chat_id,
            "📉 <b>Ошибки за 7 дней</b>\n\n"
            "✅ Ошибок не обнаружено!\n\n"
            "Всё работает отлично.",
            kb_back()
        )
    else:
        txt = "📉 <b>Ошибки за 7 дней</b>\n\n"
        
        # Sort by count
        sorted_errors = sorted(errors.items(), key=lambda x: -x[1])
        
        for err_type, count in sorted_errors:
            # Human-readable error names
            err_names = {
                'parsing_error': '🔍 Ошибки парсинга',
                'mailing_error': '📤 Ошибки рассылки',
                'auth_error': '🔐 Ошибки авторизации',
                'flood_wait': '⏰ FloodWait',
                'peer_flood': '🚫 PeerFlood',
                'privacy_restricted': '🔒 Приватность',
                'user_blocked': '🚫 Блокировки'
            }
            name = err_names.get(err_type, err_type)
            txt += f"• {name}: <b>{count}</b>\n"
        
        txt += "\n<i>Детали в логах VPS</i>"
        send_message(chat_id, txt, kb_back())


def show_top_audiences(chat_id: int, user_id: int):
    """Show top audiences by size"""
    DB.set_user_state(user_id, 'stats:top')
    
    sources = DB.get_audience_sources(user_id, status='completed')
    sources_sorted = sorted(sources, key=lambda x: x.get('parsed_count', 0), reverse=True)[:10]
    
    if not sources_sorted:
        send_message(chat_id,
            "🏆 <b>Топ аудиторий</b>\n\n"
            "Нет готовых аудиторий.\n\n"
            "Создайте аудиторию через парсинг!",
            kb_back()
        )
    else:
        txt = "🏆 <b>Топ аудиторий по размеру</b>\n\n"
        
        for i, s in enumerate(sources_sorted, 1):
            link = s['source_link']
            if len(link) > 25:
                link = link[:22] + '...'
            
            stats = DB.get_audience_stats(s['id'])
            total = s.get('parsed_count', 0)
            sent = stats.get('sent', 0)
            remaining = stats.get('remaining', 0)
            
            emoji = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
            
            txt += f"{emoji} {link}\n"
            txt += f"   👥 {total} | ✅ {sent} | ⏳ {remaining}\n\n"
        
        send_message(chat_id, txt, kb_back())


def show_active_mailings_stats(chat_id: int, user_id: int):
    """Show active mailings statistics"""
    DB.set_user_state(user_id, 'stats:mailings')
    
    campaigns = DB.get_active_campaigns(user_id)
    
    if not campaigns:
        send_message(chat_id,
            "📊 <b>Активные рассылки</b>\n\n"
            "Нет активных рассылок.\n\n"
            "Создайте рассылку в разделе «📤 Рассылка».",
            kb_back()
        )
    else:
        txt = f"📊 <b>Активные рассылки ({len(campaigns)})</b>\n\n"
        
        total_sent = 0
        total_failed = 0
        total_remaining = 0
        
        for c in campaigns:
            status_emoji = {
                'pending': '⏳',
                'running': '🔄',
                'paused': '⏸'
            }.get(c['status'], '❓')
            
            sent = c.get('sent_count', 0)
            failed = c.get('failed_count', 0)
            total = c.get('total_count', 0)
            remaining = total - sent - failed
            
            total_sent += sent
            total_failed += failed
            total_remaining += remaining
            
            progress = int(sent / total * 100) if total > 0 else 0
            
            txt += f"{status_emoji} <b>#{c['id']}</b>\n"
            txt += f"   ✅ {sent} | ❌ {failed} | ⏳ {remaining}\n"
            txt += f"   📊 Прогресс: {progress}%\n\n"
        
        txt += f"<b>Итого:</b>\n"
        txt += f"✅ Отправлено: {total_sent}\n"
        txt += f"❌ Ошибок: {total_failed}\n"
        txt += f"⏳ Осталось: {total_remaining}"
        
        send_message(chat_id, txt, kb_back())
