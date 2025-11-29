"""
Telegram core functions with ReplyKeyboard support
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '')

def tg_request(method: str, data: dict) -> dict:
    """Make request to Telegram core"""
    try:
        resp = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=data, timeout=10)
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
    try:
        files = {'document': (filename, content, 'text/csv')}
        data = {'chat_id': chat_id}
        if caption:
            data['caption'] = caption
        if keyboard:
            import json
            data['reply_markup'] = json.dumps(keyboard)
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument", data=data, files=files, timeout=30)
        return True
    except Exception as e:
        logger.error(f"Document send error: {e}")
        return False

def send_media(chat_id: int, media_type: str, file_id: str, caption: str = None, keyboard: dict = None) -> bool:
    """Send media file by file_id"""
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
        resp = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=data, timeout=30)
        return resp.ok
    except Exception as e:
        logger.error(f"Media send error: {e}")
        return False

def send_media_by_url(chat_id: int, media_type: str, media_url: str, caption: str = None, keyboard: dict = None) -> bool:
    """Send media file by URL"""
    method_map = {
        'photo': 'sendPhoto', 'video': 'sendVideo', 'document': 'sendDocument',
        'audio': 'sendAudio', 'voice': 'sendVoice'
    }
    method = method_map.get(media_type, 'sendDocument')
    try:
        data = {'chat_id': chat_id, media_type: media_url}
        if caption:
            data['caption'] = caption[:1024]
            data['parse_mode'] = 'HTML'
        if keyboard:
            data['reply_markup'] = keyboard
        resp = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=data, timeout=30)
        return resp.ok
    except Exception as e:
        logger.error(f"Media send by URL error: {e}")
        return False

def get_file_info(file_id: str) -> dict:
    """Get file info from Telegram"""
    result = tg_request('getFile', {'file_id': file_id})
    if result.get('ok'):
        return result.get('result', {})
    return {}

def download_file(file_path: str) -> bytes:
    """Download file from Telegram servers"""
    try:
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        resp = requests.get(url, timeout=60)
        if resp.ok:
            return resp.content
        logger.error(f"Failed to download file: {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"Download file error: {e}")
        return None

def download_telegram_file(file_id: str) -> tuple:
    """
    Download file from Telegram by file_id
    Returns: (file_content: bytes, file_extension: str) or (None, None)
    """
    try:
        # Get file info
        file_info = get_file_info(file_id)
        if not file_info:
            logger.error(f"Failed to get file info for {file_id}")
            return None, None
        
        file_path = file_info.get('file_path', '')
        if not file_path:
            logger.error(f"No file_path in file info")
            return None, None
        
        # Get extension
        ext = ''
        if '.' in file_path:
            ext = '.' + file_path.split('.')[-1].lower()
        
        # Download file
        content = download_file(file_path)
        if content:
            logger.info(f"Downloaded file: {len(content)} bytes, ext: {ext}")
            return content, ext
        
        return None, None
    except Exception as e:
        logger.error(f"download_telegram_file error: {e}")
        return None, None
