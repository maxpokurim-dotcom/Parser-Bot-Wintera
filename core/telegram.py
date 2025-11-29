"""
Telegram core functions with ReplyKeyboard support
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

def tg_request(method: str, data: dict) -> dict:
    """Make request to Telegram core"""
    token = os.getenv('BOT_TOKEN', '')
    try:
        resp = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=data, timeout=10)
        if resp.ok:
            return resp.json()
        logger.error(f"Telegram core error: {resp.status_code} - {resp.text}")
        return {}
    except Exception as e:
        logger.error(f"Telegram core error in {method}: {e}")
        return {}

def send_message(chat_id: int, text: str, keyboard: dict = None, parse_mode: str = 'HTML') -> bool:
    """Send message with optional keyboard"""
    data = {
        'chat_id': chat_id, 
        'text': text[:4096], 
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    }
    if keyboard:
        data['reply_markup'] = keyboard
    result = tg_request('sendMessage', data)
    return bool(result.get('ok'))

def edit_message(chat_id: int, message_id: int, text: str, keyboard: dict = None) -> bool:
    """Edit message with optional inline keyboard"""
    data = {
        'chat_id': chat_id, 
        'message_id': message_id, 
        'text': text[:4096], 
        'parse_mode': 'HTML'
    }
    if keyboard:
        data['reply_markup'] = keyboard
    result = tg_request('editMessageText', data)
    return bool(result.get('ok'))

def delete_message(chat_id: int, message_id: int) -> bool:
    """Delete message"""
    result = tg_request('deleteMessage', {'chat_id': chat_id, 'message_id': message_id})
    return bool(result.get('ok'))

def answer_callback(callback_id: str, text: str = None) -> bool:
    """Answer callback query"""
    data = {'callback_query_id': callback_id}
    if text:
        data['text'] = text
    return bool(tg_request('answerCallbackQuery', data))

def send_document(chat_id: int, content: bytes, filename: str, caption: str = None, keyboard: dict = None) -> bool:
    """Send document"""
    token = os.getenv('BOT_TOKEN', '')
    try:
        files = {'document': (filename, content, 'text/csv')}
        data = {'chat_id': chat_id}
        if caption:
            data['caption'] = caption
        if keyboard:
            import json
            data['reply_markup'] = json.dumps(keyboard)
        requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data=data, files=files, timeout=30)
        return True
    except Exception as e:
        logger.error(f"Document send error: {e}")
        return False

def send_media(chat_id: int, media_type: str, file_id: str, caption: str = None, keyboard: dict = None) -> bool:
    """Send media file"""
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
        if keyboard:
            data['reply_markup'] = keyboard
        requests.post(f"https://api.telegram.org/bot{token}/{method}", json=data, timeout=30)
        return True
    except Exception as e:
        logger.error(f"Media send error: {e}")
        return False
