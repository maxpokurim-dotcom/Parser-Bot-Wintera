"""
Telegram Bot Webhook - Entry Point v3.0
With Herder, Factory, Content, Analytics modules
"""
import json
import logging
from http.server import BaseHTTPRequestHandler

from core.db import DB
from core.telegram import send_message, answer_callback
from core.keyboards import kb_main_menu

# Import handlers
from core.menu import (
    show_main_menu, handle_start, handle_cancel,
    handle_panic_stop, handle_resume, handle_help,
    BTN_PARSING_CHATS, BTN_COMMENTS, BTN_AUDIENCES, BTN_TEMPLATES,
    BTN_ACCOUNTS, BTN_MAILING, BTN_STATS, BTN_SETTINGS, 
    BTN_HERDER, BTN_FACTORY, BTN_CONTENT, BTN_ANALYTICS,
    BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU
)
from core.parsing import (
    start_chat_parsing, start_comments_parsing,
    handle_chat_parsing, handle_comments_parsing
)
from core.audiences import (
    show_audiences_menu, handle_audiences, handle_audiences_callback
)
from core.templates import (
    show_templates_menu, handle_templates, handle_templates_callback,
    handle_template_media
)
from core.accounts import (
    show_accounts_menu, handle_accounts, handle_accounts_callback
)
from core.mailing import (
    show_mailing_menu, handle_mailing, handle_mailing_callback
)
from core.settings import show_settings_menu, handle_settings, handle_settings_callback
from core.stats import show_stats_menu, handle_stats

# New modules
from core.herder import (
    show_herder_menu, handle_herder, handle_herder_callback
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== MESSAGE HANDLER ====================
def handle_message(message: dict):
    """Handle incoming message"""
    chat_id = message.get('chat', {}).get('id')
    user_id = message.get('from', {}).get('id')

    if not chat_id or not user_id:
        return

    text = message.get('text', '')

    # Get user state
    state_data = DB.get_user_state(user_id)
    state = state_data.get('state', '') if state_data else ''
    saved = state_data.get('data', {}) if state_data else {}

    # Commands
    if text == '/start':
        handle_start(chat_id, user_id)
        return

    if text == '/menu':
        show_main_menu(chat_id, user_id)
        return

    if text == '/cancel':
        handle_cancel(chat_id, user_id)
        return

    if text == '/stats':
        show_stats_menu(chat_id, user_id)
        return

    if text == '/help':
        handle_help(chat_id, user_id)
        return

    # Panic stop command
    if text == '/panic' or text == '/panic_stop':
        handle_panic_stop(chat_id, user_id)
        return

    # Resume command
    if text == '/resume':
        handle_resume(chat_id, user_id)
        return

    # Check if system is paused (for operations)
    if DB.is_system_paused(user_id):
        if text not in [BTN_STATS, '/stats', '/resume', '/help']:
            if state and not state.startswith('stats:'):
                send_message(chat_id,
                    "🚨 <b>Система приостановлена</b>\n\n"
                    "Используйте /resume для возобновления работы.",
                    kb_main_menu()
                )
                return

    # Main menu buttons (when no specific state)
    if not state or state.endswith(':menu') or state.endswith(':list'):
        if text == BTN_PARSING_CHATS:
            start_chat_parsing(chat_id, user_id)
            return
        
        if text == BTN_COMMENTS:
            start_comments_parsing(chat_id, user_id)
            return
        
        if text == BTN_AUDIENCES:
            show_audiences_menu(chat_id, user_id)
            return
        
        if text == BTN_TEMPLATES:
            show_templates_menu(chat_id, user_id)
            return
        
        if text == BTN_ACCOUNTS:
            show_accounts_menu(chat_id, user_id)
            return
        
        if text == BTN_MAILING:
            show_mailing_menu(chat_id, user_id)
            return
        
        if text == BTN_STATS or text == '📈 Статистика':
            show_stats_menu(chat_id, user_id)
            return
        
        if text == BTN_SETTINGS:
            show_settings_menu(chat_id, user_id)
            return
        
        # New modules
        if text == BTN_HERDER:
            show_herder_menu(chat_id, user_id)
            return
        
        if text == BTN_FACTORY:
            # Factory module (placeholder - will be implemented)
            show_factory_menu(chat_id, user_id)
            return
        
        if text == BTN_CONTENT:
            # Content module (placeholder - will be implemented)
            show_content_menu(chat_id, user_id)
            return
        
        if text == BTN_ANALYTICS:
            # Analytics module (placeholder - will be implemented)
            show_analytics_menu(chat_id, user_id)
            return

    # Handle media for template creation
    if state == 'templates:create_text':
        if handle_template_media(chat_id, user_id, message, state, saved):
            return

    # Route to appropriate handler based on state
    if state:
        # Herder handlers
        if state.startswith('herder:'):
            if handle_herder(chat_id, user_id, text, state, saved):
                return
        
        # Parsing handlers
        if state.startswith('parse_chat:'):
            if handle_chat_parsing(chat_id, user_id, text, state, saved):
                return
        
        if state.startswith('parse_comments:'):
            if handle_comments_parsing(chat_id, user_id, text, state, saved):
                return
        
        # Audiences handlers
        if state.startswith('audiences:'):
            if handle_audiences(chat_id, user_id, text, state, saved):
                return
        
        # Templates handlers
        if state.startswith('templates:'):
            if handle_templates(chat_id, user_id, text, state, saved):
                return
        
        # Accounts handlers
        if state.startswith('accounts:'):
            if handle_accounts(chat_id, user_id, text, state, saved):
                return
        
        # Mailing handlers
        if state.startswith('mailing:'):
            if handle_mailing(chat_id, user_id, text, state, saved):
                return
        
        # Settings handlers
        if state.startswith('settings:'):
            if handle_settings(chat_id, user_id, text, state, saved):
                return
        
        # Stats handlers
        if state.startswith('stats:'):
            if handle_stats(chat_id, user_id, text, state, saved):
                return
        
        # Factory handlers (placeholder)
        if state.startswith('factory:'):
            if handle_factory(chat_id, user_id, text, state, saved):
                return
        
        # Content handlers (placeholder)
        if state.startswith('content:'):
            if handle_content(chat_id, user_id, text, state, saved):
                return
        
        # Analytics handlers (placeholder)
        if state.startswith('analytics:'):
            if handle_analytics(chat_id, user_id, text, state, saved):
                return

    # Global cancel/back
    if text == BTN_CANCEL:
        handle_cancel(chat_id, user_id)
        return

    if text == BTN_BACK or text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return

    # Unknown command - show main menu
    show_main_menu(chat_id, user_id, "📋 <b>Главное меню</b>\nВыберите действие:")


# ==================== CALLBACK HANDLER ====================
def handle_callback(callback: dict):
    """Handle callback query (inline buttons)"""
    cb_id = callback.get('id')
    data = callback.get('data', '')
    msg = callback.get('message', {})
    chat_id = msg.get('chat', {}).get('id')
    msg_id = msg.get('message_id')
    user_id = callback.get('from', {}).get('id')

    if not chat_id:
        return

    answer_callback(cb_id)

    if data == 'noop':
        return

    # Herder callbacks
    if data.startswith('hsel') or data.startswith('hstrat:') or data.startswith('hass:') or \
       data.startswith('hch:') or data.startswith('hprof'):
        handle_herder_callback(chat_id, msg_id, user_id, data)
        return

    # Audience callbacks
    if data.startswith('aud:') or data.startswith('deltag:') or data.startswith('togtag:') or \
       data.startswith('delbl:') or data.startswith('togstop:') or data.startswith('delstop:'):
        handle_audiences_callback(chat_id, msg_id, user_id, data)
        return

    # Template callbacks
    if data.startswith('tpl:') or data.startswith('tfld:') or data.startswith('mvtpl:') or data.startswith('selfld:'):
        handle_templates_callback(chat_id, msg_id, user_id, data)
        return

    # Account callbacks
    if data.startswith('acc:') or data.startswith('afld:') or data.startswith('mvacc:'):
        handle_accounts_callback(chat_id, msg_id, user_id, data)
        return

    # Mailing callbacks
    if data.startswith('msrc:') or data.startswith('mtpl:') or data.startswith('macc:') or \
       data.startswith('cmp:') or data.startswith('schd:') or data.startswith('delschd:') or \
       data.startswith('task:') or data.startswith('deltask:'):
        handle_mailing_callback(chat_id, msg_id, user_id, data)
        return

    # Settings callbacks
    if data.startswith('set:'):
        handle_settings_callback(chat_id, msg_id, user_id, data)
        return

    # Factory callbacks (placeholder)
    if data.startswith('ftask:') or data.startswith('fwarm:'):
        handle_factory_callback(chat_id, msg_id, user_id, data)
        return

    # Analytics callbacks (placeholder)
    if data.startswith('arisk:') or data.startswith('aseg:'):
        handle_analytics_callback(chat_id, msg_id, user_id, data)
        return

    # Content callbacks (placeholder)
    if data.startswith('uch:') or data.startswith('gcont:'):
        handle_content_callback(chat_id, msg_id, user_id, data)
        return


# ==================== PLACEHOLDER HANDLERS ====================
# These will be implemented in separate modules

def show_factory_menu(chat_id: int, user_id: int):
    """Factory menu placeholder"""
    from core.keyboards import kb_factory_menu
    DB.set_user_state(user_id, 'factory:menu')
    send_message(chat_id,
        "🏭 <b>Фабрика аккаунтов</b>\n\n"
        "Создание и прогрев аккаунтов.\n\n"
        "⚠️ Модуль в разработке.\n"
        "Используйте «👤 Аккаунты» для ручного добавления.",
        kb_factory_menu()
    )


def handle_factory(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Factory handler placeholder"""
    if text == BTN_MAIN_MENU or text == BTN_BACK or text == '◀️ Главное меню':
        show_main_menu(chat_id, user_id)
        return True
    return False


def handle_factory_callback(chat_id: int, msg_id: int, user_id: int, data: str):
    """Factory callback placeholder"""
    pass


def show_content_menu(chat_id: int, user_id: int):
    """Content menu placeholder"""
    from core.keyboards import kb_content_menu
    DB.set_user_state(user_id, 'content:menu')
    send_message(chat_id,
        "📝 <b>Контент-менеджер</b>\n\n"
        "Генерация постов с помощью ИИ.\n\n"
        "⚠️ Модуль в разработке.\n"
        "Требуется настройка Yandex GPT API в настройках.",
        kb_content_menu()
    )


def handle_content(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Content handler placeholder"""
    if text == BTN_MAIN_MENU or text == BTN_BACK or text == '◀️ Главное меню':
        show_main_menu(chat_id, user_id)
        return True
    return False


def handle_content_callback(chat_id: int, msg_id: int, user_id: int, data: str):
    """Content callback placeholder"""
    pass


def show_analytics_menu(chat_id: int, user_id: int):
    """Analytics menu placeholder"""
    from core.keyboards import kb_analytics_menu
    DB.set_user_state(user_id, 'analytics:menu')
    
    # Get some basic stats
    stats = DB.get_dashboard_stats(user_id)
    
    send_message(chat_id,
        f"📈 <b>Аналитика и прогнозы</b>\n\n"
        f"<b>Быстрая статистика:</b>\n"
        f"├ Аккаунтов: {stats.get('accounts', 0)} ({stats.get('accounts_active', 0)} активных)\n"
        f"├ Отправлено: {stats.get('total_sent', 0)}\n"
        f"└ Успешность: {stats.get('success_rate', 0)}%\n\n"
        f"⚠️ Расширенная аналитика в разработке.",
        kb_analytics_menu()
    )


def handle_analytics(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Analytics handler placeholder"""
    if text == BTN_MAIN_MENU or text == BTN_BACK or text == '◀️ Главное меню':
        show_main_menu(chat_id, user_id)
        return True
    
    if text == '🔥 Heatmap активности':
        heatmap = DB.get_audience_heatmap(user_id)
        if heatmap:
            send_message(chat_id,
                "🔥 <b>Heatmap активности</b>\n\n"
                f"Данные на основе {heatmap.get('sample_size', 0)} пользователей.\n\n"
                "Лучшее время для рассылки определено.",
                kb_main_menu()
            )
        else:
            send_message(chat_id,
                "🔥 <b>Heatmap активности</b>\n\n"
                "Недостаточно данных для анализа.\n"
                "Выполните парсинг аудитории.",
                kb_main_menu()
            )
        return True
    
    if text == '⚠️ Прогноз рисков':
        predictions = DB.get_all_risk_predictions(user_id)
        high_risk = [p for p in predictions if p.get('prediction') and p['prediction'].get('risk_score', 0) > 0.7]
        
        if high_risk:
            send_message(chat_id,
                f"⚠️ <b>Аккаунты с высоким риском: {len(high_risk)}</b>\n\n"
                "Рекомендуется снизить нагрузку или приостановить.",
                kb_main_menu()
            )
        else:
            send_message(chat_id,
                "✅ <b>Прогноз рисков</b>\n\n"
                "Аккаунтов с высоким риском не обнаружено.",
                kb_main_menu()
            )
        return True
    
    return False


def handle_analytics_callback(chat_id: int, msg_id: int, user_id: int, data: str):
    """Analytics callback placeholder"""
    pass


# ==================== VERCEL HANDLER ====================
class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'message': 'Telegram Bot is running',
            'version': '3.0.0-herder',
            'modules': ['parsing', 'mailing', 'herder', 'factory', 'content', 'analytics']
        }).encode())

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True}).encode())
                return
            
            body = self.rfile.read(content_length)
            update = json.loads(body.decode('utf-8'))
            
            if 'message' in update:
                handle_message(update['message'])
            elif 'callback_query' in update:
                handle_callback(update['callback_query'])
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode())
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'error': 'invalid json'}).encode())
        
        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'error': str(e)}).encode())
