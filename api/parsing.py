# api/parsing.py
"""
Parsing handlers - chats and comments
"""
import re
from api.db import DB
from api.telegram import edit_message, send_message
from api.keyboards import kb_cancel, kb_main, kb_msg_limit, kb_yes_no, kb_confirm

def handle_parsing_cb(chat_id: int, msg_id: int, user_id: int, data: str, saved: dict):
    if data == 'menu:parsing_chats':
        DB.clear_user_state(user_id)
        DB.set_user_state(user_id, 'parse_chat_link')
        edit_message(chat_id, msg_id,
            "🔍 <b>Парсинг из чата</b>\n"
            "Отправьте ссылку на публичный чат:\n"
            "• <code>@chatname</code>\n"
            "• <code>t.me/chatname</code>", kb_cancel())

    elif data.startswith('parse_msg_limit:'):
        limit = int(data.split(':')[1])
        saved['msg_limit'] = limit
        DB.set_user_state(user_id, 'parse_chat_filter_username', saved)
        edit_message(chat_id, msg_id, f"✅ Лимит: <b>{limit}</b> сообщений\n👤 Собирать только с @username?", kb_yes_no('parse_chat_username'))

    elif data.startswith('parse_chat_username:'):
        saved['only_username'] = data.endswith(':yes')
        DB.set_user_state(user_id, 'parse_chat_filter_photo', saved)
        edit_message(chat_id, msg_id, "📸 Только с фото профиля?", kb_yes_no('parse_chat_photo'))

    elif data.startswith('parse_chat_photo:'):
        saved['only_photo'] = data.endswith(':yes')
        DB.set_user_state(user_id, 'parse_chat_filter_bots', saved)
        edit_message(chat_id, msg_id, "🤖 Исключить ботов?", kb_yes_no('parse_chat_bots'))

    elif data.startswith('parse_chat_bots:'):
        saved['exclude_bots'] = data.endswith(':yes')
        DB.set_user_state(user_id, 'parse_chat_confirm', saved)
        edit_message(chat_id, msg_id,
            f"📋 <b>Подтверждение парсинга</b>\n"
            f"🔗 Чат: <b>{saved.get('chat_link', 'N/A')}</b>\n"
            f"📊 Лимит: <b>{saved.get('msg_limit', 500)}</b> сообщений\n"
            f"👤 Только с username: <b>{'Да' if saved.get('only_username') else 'Нет'}</b>\n"
            f"📸 Только с фото: <b>{'Да' if saved.get('only_photo') else 'Нет'}</b>\n"
            f"🤖 Без ботов: <b>{'Да' if saved.get('exclude_bots') else 'Нет'}</b>\n"
            "🚀 Запустить парсинг?", kb_confirm('parse_chat'))

    elif data == 'parse_chat:confirm':
        source = DB.create_audience_source(user_id, 'chat', saved.get('chat_link', ''), saved)
        DB.clear_user_state(user_id)
        if source:
            edit_message(chat_id, msg_id,
                f"✅ <b>Задача создана!</b>\n"
                f"🆔 ID: <code>{source['id']}</code>\n"
                f"📊 Статус: ⏳ В очереди\n"
                f"Отслеживайте в разделе «📊 Аудитории»", kb_main())
        else:
            edit_message(chat_id, msg_id, "❌ Ошибка создания задачи", kb_main())

    elif data == 'parse_chat:cancel':
        DB.clear_user_state(user_id)
        edit_message(chat_id, msg_id, "❌ Парсинг отменён", kb_main())

    elif data == 'menu:parsing_comments':
        DB.clear_user_state(user_id)
        DB.set_user_state(user_id, 'parse_comments_channel')
        edit_message(chat_id, msg_id,
            "💬 <b>Парсинг комментариев</b>\n"
            "Отправьте ссылку на канал:\n"
            "• <code>@channel</code>\n"
            "• <code>t.me/channel</code>", kb_cancel())

    elif data.startswith('parse_comments_username:'):
        saved['only_username'] = data.endswith(':yes')
        DB.set_user_state(user_id, 'parse_comments_filter_photo', saved)
        edit_message(chat_id, msg_id, "📸 Только с фото профиля?", kb_yes_no('parse_comments_photo'))

    elif data.startswith('parse_comments_photo:'):
        saved['only_photo'] = data.endswith(':yes')
        DB.set_user_state(user_id, 'parse_comments_confirm', saved)
        pr = saved.get('post_range', {'start': 1, 'end': 20})
        edit_message(chat_id, msg_id,
            f"📋 <b>Подтверждение парсинга</b>\n"
            f"🔗 Канал: <b>@{saved.get('channel', 'N/A')}</b>\n"
            f"📊 Посты: <b>{pr.get('start', 1)}-{pr.get('end', 20)}</b>\n"
            f"📝 Мин. длина: <b>{saved.get('min_length', 0)}</b>\n"
            f"👤 Только с username: <b>{'Да' if saved.get('only_username') else 'Нет'}</b>\n"
            f"📸 Только с фото: <b>{'Да' if saved.get('only_photo') else 'Нет'}</b>\n"
            "🚀 Запустить парсинг?", kb_confirm('parse_comments'))

    elif data == 'parse_comments:confirm':
        source = DB.create_audience_source(user_id, 'comments', f"@{saved.get('channel', '')}", saved)
        DB.clear_user_state(user_id)
        if source:
            edit_message(chat_id, msg_id,
                f"✅ <b>Задача создана!</b>\n"
                f"🆔 ID: <code>{source['id']}</code>\n"
                f"📊 Статус: ⏳ В очереди", kb_main())
        else:
            edit_message(chat_id, msg_id, "❌ Ошибка создания задачи", kb_main())

    elif data == 'parse_comments:cancel':
        DB.clear_user_state(user_id)
        edit_message(chat_id, msg_id, "❌ Парсинг отменён", kb_main())


def handle_parsing_state(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Returns True if state was handled"""
    
    if state == 'parse_chat_link':
        match = re.search(r'(?:https?://)?(?:t\.me/)?@?([a-zA-Z][a-zA-Z0-9_]{3,30})', text)
        if match:
            DB.set_user_state(user_id, 'parse_chat_msg_limit', {'chat_link': f'@{match.group(1)}'})
            send_message(chat_id, f"✅ Чат: <code>@{match.group(1)}</code>\n📊 Выберите лимит сообщений:", kb_msg_limit())
        else:
            send_message(chat_id, "❌ Неверный формат. Отправьте @chatname или t.me/chatname", kb_cancel())
        return True

    if state == 'parse_comments_channel':
        match = re.search(r'(?:https?://)?(?:t\.me/)?@?([a-zA-Z][a-zA-Z0-9_]{3,30})', text)
        if match:
            DB.set_user_state(user_id, 'parse_comments_range', {'channel': match.group(1)})
            send_message(chat_id, f"✅ Канал: <code>@{match.group(1)}</code>\n📊 Введите диапазон постов (например: 1-20):", kb_cancel())
        else:
            send_message(chat_id, "❌ Неверный формат. Отправьте @channel или t.me/channel", kb_cancel())
        return True

    if state == 'parse_comments_range':
        match = re.match(r'^(\d+)\s*[-—]\s*(\d+)$', text.strip())
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            if start > end:
                start, end = end, start
            if end - start > 100:
                send_message(chat_id, "⚠️ Максимум 100 постов. Введите меньший диапазон:", kb_cancel())
                return True
            saved['post_range'] = {'start': start, 'end': end}
            DB.set_user_state(user_id, 'parse_comments_min_length', saved)
            send_message(chat_id, f"✅ Посты: {start}-{end}\n📝 Введите минимальную длину комментария (0 = все):", kb_cancel())
        else:
            send_message(chat_id, "❌ Неверный формат. Пример: <code>1-20</code>", kb_cancel())
        return True

    if state == 'parse_comments_min_length':
        try:
            min_len = max(0, int(text.strip()))
            saved['min_length'] = min_len
            DB.set_user_state(user_id, 'parse_comments_filter_username', saved)
            send_message(chat_id, f"✅ Мин. длина: {min_len}\n👤 Собирать только с @username?", kb_yes_no('parse_comments_username'))
        except ValueError:
            send_message(chat_id, "❌ Введите число", kb_cancel())
        return True

    return False