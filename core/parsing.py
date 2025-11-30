"""
Parsing handlers - chats and comments
Extended v2.0 with keyword filtering
"""
import re
import logging
from core.db import DB
from core.telegram import send_message
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back_cancel,
    kb_parse_msg_limit, kb_parse_filter_yn, kb_parse_confirm,
    kb_comments_range, kb_min_length, kb_keyword_filter, kb_keyword_match_mode
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK

logger = logging.getLogger(__name__)


# ==================== CHAT PARSING ====================

def start_chat_parsing(chat_id: int, user_id: int):
    """Start chat parsing flow"""
    # Check if system is paused
    if DB.is_system_paused(user_id):
        send_message(chat_id,
            "🚨 <b>Система приостановлена</b>\n\n"
            "Используйте /resume для возобновления работы.",
            kb_main_menu()
        )
        return
    
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
        elif state == 'parse_chat:keyword_ask':
            DB.set_user_state(user_id, 'parse_chat:exclude_bots', saved)
            send_message(chat_id, "🤖 Исключить ботов?", kb_parse_filter_yn())
        elif state == 'parse_chat:keyword_input':
            DB.set_user_state(user_id, 'parse_chat:keyword_ask', saved)
            send_message(chat_id,
                "🔑 <b>Фильтр по ключевым словам</b>\n\n"
                "Хотите собирать только тех, кто упоминал определённые слова в сообщениях?",
                kb_keyword_filter()
            )
        elif state == 'parse_chat:keyword_mode':
            DB.set_user_state(user_id, 'parse_chat:keyword_input', saved)
            send_message(chat_id,
                "🔑 <b>Введите ключевые слова</b>\n\n"
                "Через запятую, например:\n"
                "<code>купить, цена, заказать, доставка</code>",
                kb_back_cancel()
            )
        elif state == 'parse_chat:confirm':
            DB.set_user_state(user_id, 'parse_chat:keyword_ask', saved)
            send_message(chat_id,
                "🔑 <b>Фильтр по ключевым словам</b>\n\n"
                "Хотите собирать только тех, кто упоминал определённые слова?",
                kb_keyword_filter()
            )
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
        DB.set_user_state(user_id, 'parse_chat:keyword_ask', saved)
        
        send_message(chat_id,
            "🔑 <b>Фильтр по ключевым словам</b>\n\n"
            "Хотите собирать только тех, кто упоминал определённые слова в сообщениях?\n\n"
            "Это полезно для сбора целевой аудитории по интересам.",
            kb_keyword_filter()
        )
        return True
    
    # State: ask about keyword filter
    if state == 'parse_chat:keyword_ask':
        if text == '✅ Да, добавить':
            DB.set_user_state(user_id, 'parse_chat:keyword_input', saved)
            send_message(chat_id,
                "🔑 <b>Введите ключевые слова</b>\n\n"
                "Через запятую, например:\n"
                "<code>купить, цена, заказать, доставка</code>\n\n"
                "Будут собраны только те, чьи сообщения содержат эти слова.",
                kb_back_cancel()
            )
            return True
        
        if text == '❌ Нет, пропустить':
            # Skip keyword filter, go to confirm
            saved['keyword_filter'] = None
            saved['keyword_match_mode'] = None
            _show_chat_confirm(chat_id, user_id, saved)
            return True
        
        send_message(chat_id, "❌ Выберите вариант", kb_keyword_filter())
        return True
    
    # State: keyword input
    if state == 'parse_chat:keyword_input':
        keywords = [kw.strip().lower() for kw in text.split(',') if kw.strip()]
        
        if not keywords:
            send_message(chat_id, "❌ Введите хотя бы одно ключевое слово:", kb_back_cancel())
            return True
        
        if len(keywords) > 50:
            send_message(chat_id, "❌ Максимум 50 ключевых слов:", kb_back_cancel())
            return True
        
        saved['keyword_filter'] = keywords
        DB.set_user_state(user_id, 'parse_chat:keyword_mode', saved)
        
        send_message(chat_id,
            f"✅ Ключевые слова ({len(keywords)}):\n"
            f"<code>{', '.join(keywords[:10])}</code>"
            f"{'...' if len(keywords) > 10 else ''}\n\n"
            "🔍 <b>Режим поиска:</b>\n"
            "• <b>Любое слово</b> — сообщение содержит хотя бы одно из слов\n"
            "• <b>Все слова</b> — сообщение содержит все указанные слова",
            kb_keyword_match_mode()
        )
        return True
    
    # State: keyword match mode
    if state == 'parse_chat:keyword_mode':
        if text == '🔍 Любое слово':
            saved['keyword_match_mode'] = 'any'
        elif text == '🔍 Все слова':
            saved['keyword_match_mode'] = 'all'
        else:
            send_message(chat_id, "❌ Выберите режим поиска", kb_keyword_match_mode())
            return True
        
        _show_chat_confirm(chat_id, user_id, saved)
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
            user_id=user_id,
            source_type='chat',
            source_link=saved.get('chat_link', ''),
            filters=filters,
            keyword_filter=saved.get('keyword_filter'),
            keyword_match_mode=saved.get('keyword_match_mode', 'any')
        )
        
        DB.clear_user_state(user_id)
        
        if source:
            kw_info = ""
            if saved.get('keyword_filter'):
                kw_info = f"\n🔑 Ключевые слова: {len(saved['keyword_filter'])} шт."
            
            send_message(chat_id,
                f"✅ <b>Задача создана!</b>\n\n"
                f"🆔 ID: <code>{source['id']}</code>\n"
                f"📊 Статус: ⏳ В очереди{kw_info}\n\n"
                f"Результат появится в разделе «📊 Аудитории».",
                kb_main_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания задачи", kb_main_menu())
        return True
    
    return False


def _show_chat_confirm(chat_id: int, user_id: int, saved: dict):
    """Show chat parsing confirmation"""
    DB.set_user_state(user_id, 'parse_chat:confirm', saved)
    
    kw_info = ""
    if saved.get('keyword_filter'):
        mode = 'любое' if saved.get('keyword_match_mode') == 'any' else 'все'
        kw_info = (
            f"\n\n🔑 <b>Ключевые слова:</b>\n"
            f"<code>{', '.join(saved['keyword_filter'][:5])}</code>"
            f"{'...' if len(saved['keyword_filter']) > 5 else ''}\n"
            f"🔍 Режим: <b>{mode}</b>"
        )
    
    send_message(chat_id,
        f"📋 <b>Подтверждение парсинга</b>\n\n"
        f"🔗 Чат: <b>{saved.get('chat_link')}</b>\n"
        f"📊 Лимит: <b>{saved.get('msg_limit')}</b> сообщений\n"
        f"👤 Только с username: <b>{'Да' if saved.get('only_username') else 'Нет'}</b>\n"
        f"📸 Только с фото: <b>{'Да' if saved.get('only_photo') else 'Нет'}</b>\n"
        f"🤖 Без ботов: <b>{'Да' if saved.get('exclude_bots') else 'Нет'}</b>"
        f"{kw_info}\n\n"
        "🚀 Запустить парсинг?",
        kb_parse_confirm()
    )


# ==================== COMMENTS PARSING ====================

def start_comments_parsing(chat_id: int, user_id: int):
    """Start comments parsing flow"""
    # Check if system is paused
    if DB.is_system_paused(user_id):
        send_message(chat_id,
            "🚨 <b>Система приостановлена</b>\n\n"
            "Используйте /resume для возобновления работы.",
            kb_main_menu()
        )
        return
    
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
        elif state == 'parse_comments:keyword_ask':
            DB.set_user_state(user_id, 'parse_comments:only_photo', saved)
            send_message(chat_id, "📸 Только с фото профиля?", kb_parse_filter_yn())
        elif state == 'parse_comments:keyword_input':
            DB.set_user_state(user_id, 'parse_comments:keyword_ask', saved)
            send_message(chat_id,
                "🔑 <b>Фильтр по ключевым словам</b>\n\n"
                "Хотите собирать только тех, кто упоминал определённые слова в комментариях?",
                kb_keyword_filter()
            )
        elif state == 'parse_comments:keyword_mode':
            DB.set_user_state(user_id, 'parse_comments:keyword_input', saved)
            send_message(chat_id, "🔑 Введите ключевые слова через запятую:", kb_back_cancel())
        elif state == 'parse_comments:confirm':
            DB.set_user_state(user_id, 'parse_comments:keyword_ask', saved)
            send_message(chat_id,
                "🔑 <b>Фильтр по ключевым словам</b>\n\n"
                "Хотите собирать только тех, кто упоминал определённые слова?",
                kb_keyword_filter()
            )
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
        DB.set_user_state(user_id, 'parse_comments:keyword_ask', saved)
        
        send_message(chat_id,
            "🔑 <b>Фильтр по ключевым словам</b>\n\n"
            "Хотите собирать только тех, кто упоминал определённые слова в комментариях?\n\n"
            "Это полезно для сбора целевой аудитории по интересам.",
            kb_keyword_filter()
        )
        return True
    
    # State: ask about keyword filter
    if state == 'parse_comments:keyword_ask':
        if text == '✅ Да, добавить':
            DB.set_user_state(user_id, 'parse_comments:keyword_input', saved)
            send_message(chat_id,
                "🔑 <b>Введите ключевые слова</b>\n\n"
                "Через запятую, например:\n"
                "<code>купить, цена, заказать, доставка</code>",
                kb_back_cancel()
            )
            return True
        
        if text == '❌ Нет, пропустить':
            saved['keyword_filter'] = None
            saved['keyword_match_mode'] = None
            _show_comments_confirm(chat_id, user_id, saved)
            return True
        
        send_message(chat_id, "❌ Выберите вариант", kb_keyword_filter())
        return True
    
    # State: keyword input
    if state == 'parse_comments:keyword_input':
        keywords = [kw.strip().lower() for kw in text.split(',') if kw.strip()]
        
        if not keywords:
            send_message(chat_id, "❌ Введите хотя бы одно ключевое слово:", kb_back_cancel())
            return True
        
        if len(keywords) > 50:
            send_message(chat_id, "❌ Максимум 50 ключевых слов:", kb_back_cancel())
            return True
        
        saved['keyword_filter'] = keywords
        DB.set_user_state(user_id, 'parse_comments:keyword_mode', saved)
        
        send_message(chat_id,
            f"✅ Ключевые слова ({len(keywords)}):\n"
            f"<code>{', '.join(keywords[:10])}</code>"
            f"{'...' if len(keywords) > 10 else ''}\n\n"
            "🔍 <b>Режим поиска:</b>",
            kb_keyword_match_mode()
        )
        return True
    
    # State: keyword match mode
    if state == 'parse_comments:keyword_mode':
        if text == '🔍 Любое слово':
            saved['keyword_match_mode'] = 'any'
        elif text == '🔍 Все слова':
            saved['keyword_match_mode'] = 'all'
        else:
            send_message(chat_id, "❌ Выберите режим поиска", kb_keyword_match_mode())
            return True
        
        _show_comments_confirm(chat_id, user_id, saved)
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
            user_id=user_id,
            source_type='comments',
            source_link=f"@{saved.get('channel', '')}",
            filters=filters,
            keyword_filter=saved.get('keyword_filter'),
            keyword_match_mode=saved.get('keyword_match_mode', 'any')
        )
        
        DB.clear_user_state(user_id)
        
        if source:
            kw_info = ""
            if saved.get('keyword_filter'):
                kw_info = f"\n🔑 Ключевые слова: {len(saved['keyword_filter'])} шт."
            
            send_message(chat_id,
                f"✅ <b>Задача создана!</b>\n\n"
                f"🆔 ID: <code>{source['id']}</code>\n"
                f"📊 Статус: ⏳ В очереди{kw_info}",
                kb_main_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания задачи", kb_main_menu())
        return True
    
    return False


def _show_comments_confirm(chat_id: int, user_id: int, saved: dict):
    """Show comments parsing confirmation"""
    DB.set_user_state(user_id, 'parse_comments:confirm', saved)
    
    pr = saved.get('post_range', {'start': 1, 'end': 20})
    
    kw_info = ""
    if saved.get('keyword_filter'):
        mode = 'любое' if saved.get('keyword_match_mode') == 'any' else 'все'
        kw_info = (
            f"\n\n🔑 <b>Ключевые слова:</b>\n"
            f"<code>{', '.join(saved['keyword_filter'][:5])}</code>"
            f"{'...' if len(saved['keyword_filter']) > 5 else ''}\n"
            f"🔍 Режим: <b>{mode}</b>"
        )
    
    send_message(chat_id,
        f"📋 <b>Подтверждение парсинга</b>\n\n"
        f"🔗 Канал: <b>@{saved.get('channel')}</b>\n"
        f"📊 Посты: <b>{pr['start']}-{pr['end']}</b>\n"
        f"📝 Мин. длина: <b>{saved.get('min_length', 0)}</b>\n"
        f"👤 Только с username: <b>{'Да' if saved.get('only_username') else 'Нет'}</b>\n"
        f"📸 Только с фото: <b>{'Да' if saved.get('only_photo') else 'Нет'}</b>"
        f"{kw_info}\n\n"
        "🚀 Запустить парсинг?",
        kb_parse_confirm()
    )
