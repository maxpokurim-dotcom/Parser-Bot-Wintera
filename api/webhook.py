# api/webhook.py
"""
Telegram Bot Webhook - Entry Point
Routes all updates to appropriate handlers
"""
import json
import logging
from http.server import BaseHTTPRequestHandler

from api.db import DB
from api.telegram import send_message, answer_callback, edit_message
from api.keyboards import kb_main, kb_cancel

# Import handlers
from api.parsing import handle_parsing_cb, handle_parsing_state
from api.audiences import handle_audience_cb, handle_audience_state
from api.templates import handle_template_cb, handle_template_state, handle_template_media
from api.accounts import handle_account_cb, handle_account_state
from api.mailing import handle_mailing_cb, handle_mailing_state
from api.settings import handle_settings_cb, handle_settings_state
from api.stats import handle_stats_cb
from api.tags import handle_tags_cb, handle_blacklist_cb, handle_tags_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== MESSAGE HANDLER ====================
def handle_message(message: dict):
    chat_id = message.get('chat', {}).get('id')
    user_id = message.get('from', {}).get('id')
    if not chat_id or not user_id:
        return

    state_data = DB.get_user_state(user_id)
    state = state_data.get('state', '') if state_data else ''
    saved = state_data.get('data', {}) if state_data else {}

    text = message.get('text', '')
    
    # Commands
    if text == '/start':
        DB.clear_user_state(user_id)
        send_message(chat_id,
            "👋 <b>Добро пожаловать!</b>\n"
            "Я бот для парсинга аудитории и рассылки.\n"
            "<b>Возможности:</b>\n"
            "• 🔍 Парсинг из чатов\n"
            "• 💬 Парсинг комментариев\n"
            "• 📤 Массовая рассылка с несколькими аккаунтами\n"
            "• 📁 Организация аккаунтов по папкам\n"
            "Выберите действие 👇", kb_main())
        return

    if text == '/menu':
        DB.clear_user_state(user_id)
        send_message(chat_id, "📋 <b>Главное меню</b>", kb_main())
        return

    if text == '/cancel':
        DB.clear_user_state(user_id)
        send_message(chat_id, "❌ Действие отменено\n📋 <b>Главное меню</b>", kb_main())
        return

    if text == '/stats':
        stats = DB.get_user_stats(user_id)
        send_message(chat_id,
            f"📈 <b>Статистика</b>\n"
            f"📊 Аудитории: <b>{stats['audiences']}</b>\n"
            f"📄 Шаблоны: <b>{stats['templates']}</b>\n"
            f"👤 Аккаунты: <b>{stats['accounts']}</b>\n"
            f"✅ Отправлено: <b>{stats['total_sent']}</b>", kb_main())
        return

    # Handle media for template creation
    if state == 'waiting_template_text':
        if handle_template_media(chat_id, user_id, message, state, saved):
            return

    # Handle text states
    if state:
        # Try each state handler
        if handle_parsing_state(chat_id, user_id, text, state, saved):
            return
        if handle_audience_state(chat_id, user_id, text, state, saved):
            return
        if handle_template_state(chat_id, user_id, text, state, saved, message):
            return
        if handle_account_state(chat_id, user_id, text, state, saved):
            return
        if handle_mailing_state(chat_id, user_id, text, state, saved):
            return
        if handle_settings_state(chat_id, user_id, text, state, saved):
            return
        if handle_tags_state(chat_id, user_id, text, state, saved):
            return
        
        # Unknown state
        DB.clear_user_state(user_id)
        send_message(chat_id, "📋 <b>Главное меню</b>\nВыберите действие:", kb_main())
    else:
        send_message(chat_id, "📋 <b>Главное меню</b>\nВыберите действие:", kb_main())


# ==================== CALLBACK HANDLER ====================
def handle_callback(callback: dict):
    cb_id = callback.get('id')
    data = callback.get('data', '')
    msg = callback.get('message', {})
    chat_id = msg.get('chat', {}).get('id')
    msg_id = msg.get('message_id')
    user_id = callback.get('from', {}).get('id')

    if not chat_id:
        return

    answer_callback(cb_id)

    state_data = DB.get_user_state(user_id)
    saved = state_data.get('data', {}) if state_data else {}

    # Main menu / Cancel
    if data in ['menu:main', 'nav:main', 'action:cancel']:
        DB.clear_user_state(user_id)
        edit_message(chat_id, msg_id, "📋 <b>Главное меню</b>\nВыберите действие:", kb_main())
        return

    if data == 'noop':
        return

    # Route to appropriate handler
    if data.startswith('menu:parsing') or data.startswith('parse_'):
        handle_parsing_cb(chat_id, msg_id, user_id, data, saved)
    elif data.startswith('menu:audiences') or data.startswith('audience:'):
        handle_audience_cb(chat_id, msg_id, user_id, data, saved)
    elif data.startswith('menu:templates') or data.startswith('template:') or data.startswith('folder:') or data.startswith('template_create:') or data.startswith('template_move:'):
        handle_template_cb(chat_id, msg_id, user_id, data, saved)
    elif data.startswith('menu:accounts') or data.startswith('account:') or data.startswith('acc_folder:'):
        handle_account_cb(chat_id, msg_id, user_id, data, saved)
    elif data.startswith('menu:mailing') or data.startswith('mailing:') or data.startswith('scheduled:') or data.startswith('campaign:'):
        handle_mailing_cb(chat_id, msg_id, user_id, data, saved)
    elif data.startswith('menu:settings') or data.startswith('settings:'):
        handle_settings_cb(chat_id, msg_id, user_id, data)
    elif data.startswith('menu:stats') or data.startswith('stats:'):
        handle_stats_cb(chat_id, msg_id, user_id, data)
    elif data.startswith('menu:tags') or data.startswith('tag:'):
        handle_tags_cb(chat_id, msg_id, user_id, data)
    elif data.startswith('menu:blacklist') or data.startswith('blacklist:'):
        handle_blacklist_cb(chat_id, msg_id, user_id, data)


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
            'version': '2.1.0'
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
            elif 'edited_message' in update:
                pass
            
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