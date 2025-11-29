"""
Parsing handlers - chats and comments
Static menu version
"""
import re
import logging
from core.db import DB
from core.telegram import send_message
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back_cancel,
    kb_parse_msg_limit, kb_parse_filter_yn, kb_parse_confirm,
    kb_comments_range, kb_min_length
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK

logger = logging.getLogger(__name__)

# ==================== CHAT PARSING ====================

def start_chat_parsing(chat_id: int, user_id: int):
    """Start chat parsing flow"""
    # Check if user has active account
    account = DB.get_any_active_account(user_id)
    if not account:
        send_message(chat_id,
            "❌ <b>Нет активных аккаунтов</b>\n\n"
            "Для парсинга нужен хотя бы один авторизованный аккаунт.\n"
            "Добавьте аккаунт в разделе «👤 Аккаунты».",
            kb_main_menu()
        )
        return
    
    DB.set_user_state(user_id, 'parse_chat:link', {'account_id': account['id']})
    send_message(chat_id,
        "🔍 <b>Парсинг из чата</b>\n\n"
        "Отправьте ссылку на публичный чат:\n"
        "• <code>@chatname</code>\n"
        "• <code>https://t.me/chatname</code>\n\n"
        f"📱 Аккаунт для парсинга: <code>{account['phone'][:4]}***{account['phone'][-2:]}</code>",
        kb_cancel()
    )

def handle_chat_parsing(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle chat parsing states. Returns True if handled."""
    
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Парсинг отменён")
        return True
    
    if text == BTN_BACK:
        # Go back one step
        if state == 'parse_chat:link':
            show_main_menu(chat_id, user_id)
        elif state == 'parse_chat:limit':
            DB.set_user_state(user_id, 'parse_chat:link', saved)
            send_message(chat_id, "🔗 Отправьте ссылку на чат:", kb_cancel())
        elif state == 'parse_chat:custom_limit':
            DB.set_user_state(user_id, 'parse_chat:limit', saved)
            send_message(chat_id, "📊 Выберите лимит сообщений:", kb_parse_msg_limit())
        elif state == 'parse_chat:only_username':
            DB.set_user_state(user_id, 'parse_chat:limit', saved)
            send_message(chat_id, "📊 Выберите лимит сообщений:", kb_parse_msg_limit())
        elif state == 'parse_chat:only_photo':
            DB.set_user_state(user_id, 'parse_chat:only_username', saved)
            send_message(chat_id, "👤 Собирать только пользователей с @username?", kb_parse_filter_yn())
        elif state == 'parse_chat:exclude_bots':
            DB.set_user_state(user_id, 'parse_chat:only_photo', saved)
            send_message(chat_id, "📸 Собирать только с фото профиля?", kb_parse_filter_yn())
        elif state == 'parse_chat:confirm':
            DB.set_user_state(user_id, 'parse_chat:exclude_bots', saved)
            send_message(chat_id, "🤖 Исключить ботов?", kb_parse_filter_yn())
        return True
    
    # State: waiting for chat link
    if state == 'parse_chat:link':
        match = re.search(r'(?:https?://)?(?:t\.me/)?@?([a-zA-Z][a-zA-Z0-9_]{3,30})', text)
        if not match:
            send_message(chat_id, "❌ Неверный формат. Отправьте @chatname или t.me/chatname", kb_cancel())
            return True
        
        saved['chat_link'] = f'@{match.group(1)}'
        DB.set_user_state(user_id, 'parse_chat:limit', saved)
        send_message(chat_id,
            f"✅ Чат: <code>{saved['chat_link']}</code>\n\n"
            "📊 Выберите лимит сообщений для анализа:",
            kb_parse_msg_limit()
        )
        return True
    
    # State: waiting for message limit
    if state == 'parse_chat:limit':
        if text == '📝 Свой лимит':
            DB.set_user_state(user_id, 'parse_chat:custom_limit', saved)
            send_message(chat_id, "📝 Введите свой лимит (от 10 до 10000):", kb_back_cancel())
            return True
        
        try:
            limit = int(text)
            if limit not in [100, 500, 1000, 2000, 5000]:
                raise ValueError()
        except:
            send_message(chat_id, "❌ Выберите лимит из предложенных или нажмите «📝 Свой лимит»", kb_parse_msg_limit())
            return True
        
        saved['msg_limit'] = limit
        DB.set_user_state(user_id, 'parse_chat:only_username', saved)
        send_message(chat_id,
            f"✅ Лимит: <b>{limit}</b> сообщений\n\n"
            "👤 Собирать только пользователей с @username?",
            kb_parse_filter_yn()
        )
        return True
    
    # State: custom limit input
    if state == 'parse_chat:custom_limit':
        try:
            limit = int(text)
            if limit < 10 or limit > 10000:
                raise ValueError()
        except:
            send_message(chat_id, "❌ Введите число от 10 до 10000:", kb_back_cancel())
            return True
        
        saved['msg_limit'] = limit
        DB.set_user_state(user_id, 'parse_chat:only_username', saved)
        send_message(chat_id,
            f"✅ Лимит: <b>{limit}</b> сообщений\n\n"
            "👤 Собирать только пользователей с @username?",
            kb_parse_filter_yn()
        )
        return True
    
    # State: only username filter
    if state == 'parse_chat:only_username':
        if text not in ['✅ Да', '❌ Нет']:
            send_message(chat_id, "❌ Выберите «Да» или «Нет»", kb_parse_filter_yn())
            return True
        
        saved['only_username'] = (text == '✅ Да')
        DB.set_user_state(user_id, 'parse_chat:only_photo', saved)
        send_message(chat_id, "📸 Собирать только с фото профиля?", kb_parse_filter_yn())
        return True
    
    # State: only photo filter
    if state == 'parse_chat:only_photo':
        if text not in ['✅ Да', '❌ Нет']:
            send_message(chat_id, "❌ Выберите «Да» или «Нет»", kb_parse_filter_yn())
            return True
        
        saved['only_photo'] = (text == '✅ Да')
        DB.set_user_state(user_id, 'parse_chat:exclude_bots', saved)
        send_message(chat_id, "🤖 Исключить ботов?", kb_parse_filter_yn())
        return True
    
    # State: exclude bots filter
    if state == 'parse_chat:exclude_bots':
        if text not in ['✅ Да', '❌ Нет']:
            send_message(chat_id, "❌ Выберите «Да» или «Нет»", kb_parse_filter_yn())
            return True
        
        saved['exclude_bots'] = (text == '✅ Да')
        DB.set_user_state(user_id, 'parse_chat:confirm', saved)
        
        send_message(chat_id,
            f"📋 <b>Подтверждение парсинга</b>\n\n"
            f"🔗 Чат: <b>{saved.get('chat_link')}</b>\n"
            f"📊 Лимит: <b>{saved.get('msg_limit')}</b> сообщений\n"
            f"👤 Только с username: <b>{'Да' if saved.get('only_username') else 'Нет'}</b>\n"
            f"📸 Только с фото: <b>{'Да' if saved.get('only_photo') else 'Нет'}</b>\n"
            f"🤖 Без ботов: <b>{'Да' if saved.get('exclude_bots') else 'Нет'}</b>\n\n"
            "🚀 Запустить парсинг?",
            kb_parse_confirm()
        )
        return True
    
    # State: confirm parsing
    if state == 'parse_chat:confirm':
        if text != '🚀 Запустить парсинг':
            send_message(chat_id, "❌ Нажмите «🚀 Запустить парсинг» или «Назад»", kb_parse_confirm())
            return True
        
        # Create parsing task
        filters = {
            'msg_limit': saved.get('msg_limit', 500),
            'only_username': saved.get('only_username', True),
            'only_photo': saved.get('only_photo', False),
            'exclude_bots': saved.get('exclude_bots', True),
            'exclude_duplicates': True
        }
        
        source = DB.create_audience_source(
            user_id, 'chat', saved.get('chat_link', ''), filters
        )
        
        DB.clear_user_state(user_id)
        
        if source:
            send_message(chat_id,
                f"✅ <b>Задача создана!</b>\n\n"
                f"🆔 ID: <code>{source['id']}</code>\n"
                f"📊 Статус: ⏳ В очереди\n\n"
                f"Результат появится в разделе «📊 Аудитории».",
                kb_main_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания задачи", kb_main_menu())
        return True
    
    return False


# ==================== COMMENTS PARSING ====================

def start_comments_parsing(chat_id: int, user_id: int):
    """Start comments parsing flow"""
    account = DB.get_any_active_account(user_id)
    if not account:
        send_message(chat_id,
            "❌ <b>Нет активных аккаунтов</b>\n\n"
            "Для парсинга нужен хотя бы один авторизованный аккаунт.",
            kb_main_menu()
        )
        return
    
    DB.set_user_state(user_id, 'parse_comments:channel', {'account_id': account['id']})
    send_message(chat_id,
        "💬 <b>Парсинг комментариев</b>\n\n"
        "Отправьте ссылку на канал:\n"
        "• <code>@channel</code>\n"
        "• <code>https://t.me/channel</code>\n\n"
        f"📱 Аккаунт: <code>{account['phone'][:4]}***{account['phone'][-2:]}</code>",
        kb_cancel()
    )

def handle_comments_parsing(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle comments parsing states. Returns True if handled."""
    
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Парсинг отменён")
        return True
    
    if text == BTN_BACK:
        if state == 'parse_comments:channel':
            show_main_menu(chat_id, user_id)
        elif state == 'parse_comments:range':
            DB.set_user_state(user_id, 'parse_comments:channel', saved)
            send_message(chat_id, "🔗 Отправьте ссылку на канал:", kb_cancel())
        elif state == 'parse_comments:custom_range':
            DB.set_user_state(user_id, 'parse_comments:range', saved)
            send_message(chat_id, "📊 Выберите диапазон постов:", kb_comments_range())
        elif state == 'parse_comments:min_length':
            DB.set_user_state(user_id, 'parse_comments:range', saved)
            send_message(chat_id, "📊 Выберите диапазон постов:", kb_comments_range())
        elif state == 'parse_comments:custom_min_length':
            DB.set_user_state(user_id, 'parse_comments:min_length', saved)
            send_message(chat_id, "📝 Минимальная длина комментария:", kb_min_length())
        elif state == 'parse_comments:only_username':
            DB.set_user_state(user_id, 'parse_comments:min_length', saved)
            send_message(chat_id, "📝 Минимальная длина комментария:", kb_min_length())
        elif state == 'parse_comments:only_photo':
            DB.set_user_state(user_id, 'parse_comments:only_username', saved)
            send_message(chat_id, "👤 Только с @username?", kb_parse_filter_yn())
        elif state == 'parse_comments:confirm':
            DB.set_user_state(user_id, 'parse_comments:only_photo', saved)
            send_message(chat_id, "📸 Только с фото профиля?", kb_parse_filter_yn())
        return True
    
    # State: waiting for channel
    if state == 'parse_comments:channel':
        match = re.search(r'(?:https?://)?(?:t\.me/)?@?([a-zA-Z][a-zA-Z0-9_]{3,30})', text)
        if not match:
            send_message(chat_id, "❌ Неверный формат. Отправьте @channel или t.me/channel", kb_cancel())
            return True
        
        saved['channel'] = match.group(1)
        DB.set_user_state(user_id, 'parse_comments:range', saved)
        send_message(chat_id,
            f"✅ Канал: <code>@{saved['channel']}</code>\n\n"
            "📊 Выберите диапазон постов:",
            kb_comments_range()
        )
        return True
    
    # State: post range
    if state == 'parse_comments:range':
        if text == '📝 Свой диапазон':
            DB.set_user_state(user_id, 'parse_comments:custom_range', saved)
            send_message(chat_id, "📝 Введите диапазон (например: 1-50):", kb_back_cancel())
            return True
        
        ranges = {'1-10': (1, 10), '1-20': (1, 20), '1-50': (1, 50)}
        if text not in ranges:
            send_message(chat_id, "❌ Выберите диапазон из предложенных", kb_comments_range())
            return True
        
        saved['post_range'] = {'start': ranges[text][0], 'end': ranges[text][1]}
        DB.set_user_state(user_id, 'parse_comments:min_length', saved)
        send_message(chat_id,
            f"✅ Посты: <b>{text}</b>\n\n"
            "📝 Минимальная длина комментария (символов):",
            kb_min_length()
        )
        return True
    
    # State: custom range
    if state == 'parse_comments:custom_range':
        match = re.match(r'^(\d+)\s*[-—]\s*(\d+)$', text.strip())
        if not match:
            send_message(chat_id, "❌ Неверный формат. Пример: 1-50", kb_back_cancel())
            return True
        
        start, end = int(match.group(1)), int(match.group(2))
        if start > end:
            start, end = end, start
        if end - start > 100:
            send_message(chat_id, "⚠️ Максимум 100 постов. Введите меньший диапазон:", kb_back_cancel())
            return True
        
        saved['post_range'] = {'start': start, 'end': end}
        DB.set_user_state(user_id, 'parse_comments:min_length', saved)
        send_message(chat_id,
            f"✅ Посты: <b>{start}-{end}</b>\n\n"
            "📝 Минимальная длина комментария:",
            kb_min_length()
        )
        return True
    
    # State: min length
    if state == 'parse_comments:min_length':
        if text == '📝 Свой':
            DB.set_user_state(user_id, 'parse_comments:custom_min_length', saved)
            send_message(chat_id, "📝 Введите минимальную длину (0-1000):", kb_back_cancel())
            return True
        
        lengths = {'0 (все)': 0, '10': 10, '50': 50, '100': 100}
        if text not in lengths:
            send_message(chat_id, "❌ Выберите из предложенных вариантов", kb_min_length())
            return True
        
        saved['min_length'] = lengths[text]
        DB.set_user_state(user_id, 'parse_comments:only_username', saved)
        send_message(chat_id, "👤 Собирать только с @username?", kb_parse_filter_yn())
        return True
    
    # State: custom min length
    if state == 'parse_comments:custom_min_length':
        try:
            min_len = int(text)
            if min_len < 0 or min_len > 1000:
                raise ValueError()
        except:
            send_message(chat_id, "❌ Введите число от 0 до 1000:", kb_back_cancel())
            return True
        
        saved['min_length'] = min_len
        DB.set_user_state(user_id, 'parse_comments:only_username', saved)
        send_message(chat_id, "👤 Собирать только с @username?", kb_parse_filter_yn())
        return True
    
    # State: only username
    if state == 'parse_comments:only_username':
        if text not in ['✅ Да', '❌ Нет']:
            send_message(chat_id, "❌ Выберите «Да» или «Нет»", kb_parse_filter_yn())
            return True
        
        saved['only_username'] = (text == '✅ Да')
        DB.set_user_state(user_id, 'parse_comments:only_photo', saved)
        send_message(chat_id, "📸 Собирать только с фото профиля?", kb_parse_filter_yn())
        return True
    
    # State: only photo
    if state == 'parse_comments:only_photo':
        if text not in ['✅ Да', '❌ Нет']:
            send_message(chat_id, "❌ Выберите «Да» или «Нет»", kb_parse_filter_yn())
            return True
        
        saved['only_photo'] = (text == '✅ Да')
        DB.set_user_state(user_id, 'parse_comments:confirm', saved)
        
        pr = saved.get('post_range', {'start': 1, 'end': 20})
        send_message(chat_id,
            f"📋 <b>Подтверждение парсинга</b>\n\n"
            f"🔗 Канал: <b>@{saved.get('channel')}</b>\n"
            f"📊 Посты: <b>{pr['start']}-{pr['end']}</b>\n"
            f"📝 Мин. длина: <b>{saved.get('min_length', 0)}</b>\n"
            f"👤 Только с username: <b>{'Да' if saved.get('only_username') else 'Нет'}</b>\n"
            f"📸 Только с фото: <b>{'Да' if saved.get('only_photo') else 'Нет'}</b>\n\n"
            "🚀 Запустить парсинг?",
            kb_parse_confirm()
        )
        return True
    
    # State: confirm
    if state == 'parse_comments:confirm':
        if text != '🚀 Запустить парсинг':
            send_message(chat_id, "❌ Нажмите «🚀 Запустить парсинг» или «Назад»", kb_parse_confirm())
            return True
        
        filters = {
            'post_range': saved.get('post_range', {'start': 1, 'end': 20}),
            'min_length': saved.get('min_length', 0),
            'only_username': saved.get('only_username', True),
            'only_photo': saved.get('only_photo', False),
            'exclude_duplicates': True
        }
        
        source = DB.create_audience_source(
            user_id, 'comments', f"@{saved.get('channel', '')}", filters
        )
        
        DB.clear_user_state(user_id)
        
        if source:
            send_message(chat_id,
                f"✅ <b>Задача создана!</b>\n\n"
                f"🆔 ID: <code>{source['id']}</code>\n"
                f"📊 Статус: ⏳ В очереди",
                kb_main_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания задачи", kb_main_menu())
        return True
    
    return False
