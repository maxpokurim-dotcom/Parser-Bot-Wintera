# api/tags.py
"""
Tags and blacklist handlers
"""
import re
import logging
from api.db import DB
from api.telegram import edit_message, send_message
from api.keyboards import kb_main, kb_cancel, kb_tags_menu, kb_blacklist

logger = logging.getLogger(__name__)

def handle_tags_cb(chat_id: int, msg_id: int, user_id: int, data: str):
    if data == 'menu:tags':
        tags = DB.get_audience_tags(user_id)
        if not tags:
            txt = "🏷 <b>Теги</b>\nУ вас пока нет тегов."
        else:
            txt = f"🏷 <b>Ваши теги ({len(tags)})</b>\n"
            for t in tags:
                txt += f"• {t['name']}\n"
        edit_message(chat_id, msg_id, txt, kb_tags_menu(tags))

    elif data == 'tag:create':
        DB.set_user_state(user_id, 'waiting_tag_name')
        edit_message(chat_id, msg_id,
            "🏷 <b>Создание тега</b>\n"
            "Введите название тега (макс. 30 символов):", kb_cancel())

    elif data.startswith('tag:delete:'):
        tag_id = int(data.split(':')[2])
        logger.info(f"Deleting tag {tag_id} for user {user_id}")
        result = DB.delete_audience_tag(tag_id)
        logger.info(f"Delete result: {result}")
        
        tags = DB.get_audience_tags(user_id)
        if not tags:
            txt = "✅ Тег удалён\n\n🏷 <b>Теги</b>\nУ вас пока нет тегов."
        else:
            txt = f"✅ Тег удалён\n\n🏷 <b>Ваши теги ({len(tags)})</b>\n"
            for t in tags:
                txt += f"• {t['name']}\n"
        edit_message(chat_id, msg_id, txt, kb_tags_menu(tags))


def handle_blacklist_cb(chat_id: int, msg_id: int, user_id: int, data: str):
    if data == 'menu:blacklist':
        blacklist = DB.get_blacklist(user_id)
        count = len(blacklist)
        txt = f"🚫 <b>Чёрный список ({count})</b>\n"
        if blacklist:
            for b in blacklist[:10]:
                display = f"@{b['username']}" if b.get('username') else str(b.get('tg_user_id', '?'))
                txt += f"• {display}\n"
            if count > 10:
                txt += f"\n<i>... и ещё {count - 10}</i>"
        else:
            txt += "Список пуст"
        edit_message(chat_id, msg_id, txt, kb_blacklist(blacklist))

    elif data == 'blacklist:add':
        DB.set_user_state(user_id, 'waiting_blacklist_input')
        edit_message(chat_id, msg_id,
            "🚫 <b>Добавление в чёрный список</b>\n"
            "Введите @username или ID пользователя:", kb_cancel())

    elif data.startswith('blacklist:remove:'):
        bl_id = int(data.split(':')[2])
        logger.info(f"Removing from blacklist {bl_id} for user {user_id}")
        result = DB.remove_from_blacklist(bl_id)
        logger.info(f"Remove result: {result}")
        
        blacklist = DB.get_blacklist(user_id)
        count = len(blacklist)
        txt = f"✅ Удалено из чёрного списка\n\n🚫 <b>Чёрный список ({count})</b>\n"
        if blacklist:
            for b in blacklist[:10]:
                display = f"@{b['username']}" if b.get('username') else str(b.get('tg_user_id', '?'))
                txt += f"• {display}\n"
        else:
            txt += "Список пуст"
        edit_message(chat_id, msg_id, txt, kb_blacklist(blacklist))


def handle_tags_state(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Returns True if state was handled"""
    
    if state == 'waiting_tag_name':
        name = text.strip()
        if len(name) > 30:
            send_message(chat_id, "❌ Максимум 30 символов", kb_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите название тега:", kb_cancel())
            return True
        tag = DB.create_audience_tag(user_id, name)
        DB.clear_user_state(user_id)
        if tag:
            send_message(chat_id, f"✅ Тег «{name}» создан!", kb_main())
        else:
            send_message(chat_id, "❌ Ошибка создания тега", kb_main())
        return True

    if state == 'waiting_blacklist_input':
        username, tg_id = None, None
        text_clean = text.strip()
        if text_clean.isdigit():
            tg_id = int(text_clean)
        else:
            m = re.search(r'@?([a-zA-Z][a-zA-Z0-9_]{3,30})', text_clean)
            if m:
                username = m.group(1)
        if not username and not tg_id:
            send_message(chat_id, "❌ Введите @username или ID пользователя", kb_cancel())
            return True
        result = DB.add_to_blacklist(user_id, tg_user_id=tg_id, username=username)
        DB.clear_user_state(user_id)
        display = f"@{username}" if username else str(tg_id)
        if result:
            send_message(chat_id, f"✅ {display} добавлен в чёрный список", kb_main())
        else:
            send_message(chat_id, "❌ Ошибка добавления", kb_main())
        return True

    return False