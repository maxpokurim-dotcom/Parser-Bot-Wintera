# api/telegram.py
"""
Telegram API functions
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

def tg_request(method: str, data: dict) -> bool:
    token = os.getenv('BOT_TOKEN', '')
    try:
        resp = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=data, timeout=10)
        return resp.ok
    except Exception as e:
        logger.error(f"Telegram API error in {method}: {e}")
        return False

def send_message(chat_id: int, text: str, keyboard: dict = None) -> bool:
    data = {'chat_id': chat_id, 'text': text[:4096], 'parse_mode': 'HTML', 'disable_web_page_preview': True}
    if keyboard:
        data['reply_markup'] = keyboard
    return tg_request('sendMessage', data)

def edit_message(chat_id: int, message_id: int, text: str, keyboard: dict = None) -> bool:
    data = {'chat_id': chat_id, 'message_id': message_id, 'text': text[:4096], 'parse_mode': 'HTML'}
    if keyboard:
        data['reply_markup'] = keyboard
    return tg_request('editMessageText', data)

def answer_callback(callback_id: str) -> bool:
    return tg_request('answerCallbackQuery', {'callback_query_id': callback_id})

def send_document(chat_id: int, content: bytes, filename: str, caption: str = None) -> bool:
    token = os.getenv('BOT_TOKEN', '')
    try:
        files = {'document': (filename, content, 'text/csv')}
        data = {'chat_id': chat_id}
        if caption:
            data['caption'] = caption
        requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data=data, files=files, timeout=30)
        return True
    except Exception as e:
        logger.error(f"Document send error: {e}")
        return False

def send_media(chat_id: int, media_type: str, file_id: str, caption: str = None) -> bool:
    token = os.getenv('BOT_TOKEN', '')
    method_map = {
        'photo': 'sendPhoto', 'video': 'sendVideo', 'document': 'sendDocument',
        'audio': 'sendAudio', 'voice': 'sendVoice'
    }
    method = method_map.get(media_type, 'sendDocument')
    try:
        data = {'chat_id': chat_id, media_type: file_id}
        if caption:
            data['caption'] = caption[:1024]
            data['parse_mode'] = 'HTML'
        requests.post(f"https://api.telegram.org/bot{token}/{method}", json=data, timeout=30)
        return True
    except Exception as e:
        logger.error(f"Media send error: {e}")
        return False