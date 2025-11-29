"""
Audience management handlers
Static menu version
"""
import logging
from core.db import DB
from core.telegram import send_message, send_document, answer_callback
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel,
    kb_audiences_menu, kb_audience_actions, kb_audience_tags,
    kb_blacklist_menu, kb_confirm_delete,
    kb_inline_audiences, kb_inline_tags, kb_inline_audience_tags, kb_inline_blacklist
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_AUD_LIST = '📋 Список аудиторий'
BTN_AUD_TAGS = '🏷 Теги'
BTN_AUD_BLACKLIST = '🚫 Чёрный список'
BTN_AUD_SEARCH = '🔍 Поиск'
BTN_AUD_EXPORT = '📤 Экспорт'
BTN_AUD_DELETE = '🗑 Удалить'
BTN_AUD_BACK_LIST = '◀️ К списку'
BTN_CREATE_TAG = '➕ Создать тег'
BTN_ADD = '➕ Добавить'
BTN_LIST = '📋 Список'
BTN_CONFIRM_DELETE = '🗑 Да, удалить'


def show_audiences_menu(chat_id: int, user_id: int):
    """Show audiences menu"""
    DB.set_user_state(user_id, 'audiences:menu')
    sources = DB.get_audience_sources(user_id)
    total = sum(s.get('parsed_count', 0) for s in sources)
    completed = sum(1 for s in sources if s.get('status') == 'completed')
    
    send_message(chat_id,
        f"📊 <b>Аудитории</b>\n\n"
        f"📁 Всего: <b>{len(sources)}</b>\n"
        f"✅ Готовых: <b>{completed}</b>\n"
        f"👥 Пользователей: <b>{total}</b>",
        kb_audiences_menu()
    )


def handle_audiences(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle audience states. Returns True if handled."""
    
    # Cancel/Back handling
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Действие отменено")
        return True
    
    if text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return True
    
    if text == BTN_BACK:
        if state in ['audiences:menu', 'audiences:list']:
            show_main_menu(chat_id, user_id)
        elif state.startswith('audiences:view'):
            show_audience_list(chat_id, user_id)
        elif state in ['audiences:tags', 'audiences:blacklist']:
            show_audiences_menu(chat_id, user_id)
        elif state.startswith('audiences:'):
            show_audiences_menu(chat_id, user_id)
        else:
            show_main_menu(chat_id, user_id)
        return True
    
    if text == BTN_AUD_BACK_LIST:
        show_audience_list(chat_id, user_id)
        return True
    
    # Menu state
    if state == 'audiences:menu':
        if text == BTN_AUD_LIST:
            show_audience_list(chat_id, user_id)
            return True
        if text == BTN_AUD_TAGS:
            show_tags_menu(chat_id, user_id)
            return True
        if text == BTN_AUD_BLACKLIST:
            show_blacklist_menu(chat_id, user_id)
            return True
    
    # View audience state
    if state.startswith('audiences:view:'):
        source_id = int(state.split(':')[2])
        
        if text == BTN_AUD_SEARCH:
            DB.set_user_state(user_id, f'audiences:search:{source_id}')
            send_message(chat_id, "🔍 Введите @username или имя для поиска:", kb_back_cancel())
            return True
        
        if text == BTN_AUD_EXPORT:
            export_audience(chat_id, user_id, source_id)
            return True
        
        if text == BTN_AUD_TAGS:
            show_audience_tags(chat_id, user_id, source_id)
            return True
        
        if text == BTN_AUD_DELETE:
            DB.set_user_state(user_id, f'audiences:delete:{source_id}')
            send_message(chat_id,
                "🗑 <b>Удалить аудиторию?</b>\n\n"
                "⚠️ Все пользователи будут удалены безвозвратно.",
                kb_confirm_delete()
            )
            return True
    
    # Search state
    if state.startswith('audiences:search:'):
        source_id = int(state.split(':')[2])
        results = DB.search_in_audience(source_id, text.strip(), limit=20)
        
        if not results:
            send_message(chat_id, f"🔍 По запросу «{text}» ничего не найдено", kb_audience_actions())
        else:
            txt = f"🔍 <b>Найдено ({len(results)}):</b>\n\n"
            for u in results[:10]:
                un = f"@{u['username']}" if u.get('username') else "—"
                st = "✅" if u.get('sent') else "⏳"
                name = u.get('first_name', '') or ''
                txt += f"{st} {un} | {name}\n"
            send_message(chat_id, txt, kb_audience_actions())
        
        DB.set_user_state(user_id, f'audiences:view:{source_id}')
        return True
    
    # Delete confirm state
    if state.startswith('audiences:delete:'):
        source_id = int(state.split(':')[2])
        
        if text == BTN_CONFIRM_DELETE:
            DB.delete_audience_source(source_id)
            DB.clear_user_state(user_id)
            send_message(chat_id, "✅ Аудитория удалена", kb_audiences_menu())
            show_audience_list(chat_id, user_id)
            return True
        
        if text == BTN_CANCEL:
            show_audience_view(chat_id, user_id, source_id)
            return True
    
    # Tags menu
    if state == 'audiences:tags':
        if text == BTN_CREATE_TAG:
            DB.set_user_state(user_id, 'audiences:create_tag')
            send_message(chat_id, "🏷 Введите название тега (макс. 30 символов):", kb_back_cancel())
            return True
    
    # Create tag state
    if state == 'audiences:create_tag':
        name = text.strip()
        if len(name) > 30:
            send_message(chat_id, "❌ Максимум 30 символов", kb_back_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите название тега:", kb_back_cancel())
            return True
        
        tag = DB.create_audience_tag(user_id, name)
        if tag:
            send_message(chat_id, f"✅ Тег «{name}» создан!", kb_audience_tags())
        else:
            send_message(chat_id, "❌ Ошибка создания тега", kb_audience_tags())
        show_tags_menu(chat_id, user_id)
        return True
    
    # Blacklist menu
    if state == 'audiences:blacklist':
        if text == BTN_ADD:
            DB.set_user_state(user_id, 'audiences:blacklist_add')
            send_message(chat_id, "🚫 Введите @username или ID пользователя:", kb_back_cancel())
            return True
        if text == BTN_LIST:
            show_blacklist_list(chat_id, user_id)
            return True
    
    # Add to blacklist
    if state == 'audiences:blacklist_add':
        import re
        username, tg_id = None, None
        text_clean = text.strip()
        
        if text_clean.isdigit():
            tg_id = int(text_clean)
        else:
            m = re.search(r'@?([a-zA-Z][a-zA-Z0-9_]{3,30})', text_clean)
            if m:
                username = m.group(1)
        
        if not username and not tg_id:
            send_message(chat_id, "❌ Введите @username или ID", kb_back_cancel())
            return True
        
        result = DB.add_to_blacklist(user_id, tg_user_id=tg_id, username=username)
        display = f"@{username}" if username else str(tg_id)
        
        if result:
            send_message(chat_id, f"✅ {display} добавлен в чёрный список", kb_blacklist_menu())
        else:
            send_message(chat_id, "❌ Ошибка добавления", kb_blacklist_menu())
        
        DB.set_user_state(user_id, 'audiences:blacklist')
        return True
    
    return False


def handle_audiences_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle audience inline callbacks"""
    
    # Audience selection
    if data.startswith('aud:'):
        source_id = int(data.split(':')[1])
        show_audience_view(chat_id, user_id, source_id)
        return True
    
    # Tag deletion
    if data.startswith('deltag:'):
        tag_id = int(data.split(':')[1])
        DB.delete_audience_tag(tag_id)
        show_tags_menu(chat_id, user_id)
        return True
    
    # Toggle tag on audience
    if data.startswith('togtag:'):
        parts = data.split(':')
        source_id, tag_name = int(parts[1]), parts[2]
        source = DB.get_audience_source(source_id)
        if source:
            current = source.get('tags') or []
            if tag_name in current:
                DB.remove_tag_from_source(source_id, tag_name)
            else:
                DB.add_tag_to_source(source_id, tag_name)
        show_audience_tags(chat_id, user_id, source_id)
        return True
    
    # Blacklist deletion
    if data.startswith('delbl:'):
        bl_id = int(data.split(':')[1])
        DB.remove_from_blacklist(bl_id)
        show_blacklist_list(chat_id, user_id)
        return True
    
    return False


def show_audience_list(chat_id: int, user_id: int):
    """Show audience list"""
    sources = DB.get_audience_sources(user_id)
    DB.set_user_state(user_id, 'audiences:list')
    
    if not sources:
        send_message(chat_id,
            "📊 <b>Список аудиторий</b>\n\n"
            "У вас пока нет аудиторий.\n"
            "Создайте через парсинг!",
            kb_audiences_menu()
        )
    else:
        send_message(chat_id,
            "📊 <b>Выберите аудиторию:</b>",
            kb_inline_audiences(sources)
        )
        send_message(chat_id, "👆 Выберите аудиторию выше или:", kb_audiences_menu())


def show_audience_view(chat_id: int, user_id: int, source_id: int):
    """Show audience details"""
    source = DB.get_audience_source(source_id)
    if not source:
        send_message(chat_id, "❌ Аудитория не найдена", kb_audiences_menu())
        return
    
    DB.set_user_state(user_id, f'audiences:view:{source_id}')
    
    stats = DB.get_audience_stats(source_id)
    status_map = {
        'pending': '⏳ В очереди',
        'running': '🔄 Выполняется',
        'completed': '✅ Готово',
        'failed': '❌ Ошибка'
    }
    tags_str = ', '.join(source.get('tags', [])) or 'нет'
    
    send_message(chat_id,
        f"📊 <b>Аудитория #{source_id}</b>\n\n"
        f"🔗 Источник: {source['source_link']}\n"
        f"📈 Статус: {status_map.get(source['status'], source['status'])}\n"
        f"🏷 Теги: {tags_str}\n\n"
        f"<b>👥 Статистика:</b>\n"
        f"├ Всего: <b>{stats['total']}</b>\n"
        f"├ Отправлено: <b>{stats['sent']}</b>\n"
        f"└ Осталось: <b>{stats['remaining']}</b>",
        kb_audience_actions()
    )


def export_audience(chat_id: int, user_id: int, source_id: int):
    """Export audience to CSV"""
    users = DB.get_audience_with_filters(source_id, limit=5000)
    
    if not users:
        send_message(chat_id, "❌ Аудитория пуста", kb_audience_actions())
        return
    
    csv_lines = ["username,first_name,last_name,sent"]
    for u in users:
        un = u.get('username', '') or ''
        fn = (u.get('first_name', '') or '').replace(',', ' ')
        ln = (u.get('last_name', '') or '').replace(',', ' ')
        st = 'yes' if u.get('sent') else 'no'
        csv_lines.append(f"{un},{fn},{ln},{st}")
    
    csv_content = '\n'.join(csv_lines)
    send_document(chat_id, csv_content.encode('utf-8'), 
                  f"audience_{source_id}.csv", "📤 Экспорт аудитории",
                  kb_audience_actions())


def show_audience_tags(chat_id: int, user_id: int, source_id: int):
    """Show tags for audience"""
    tags = DB.get_audience_tags(user_id)
    source = DB.get_audience_source(source_id)
    current = source.get('tags', []) if source else []
    
    DB.set_user_state(user_id, f'audiences:view:{source_id}')
    
    if not tags:
        send_message(chat_id,
            "🏷 <b>Теги аудитории</b>\n\n"
            "У вас нет тегов. Создайте в разделе «🏷 Теги».",
            kb_audience_actions()
        )
    else:
        send_message(chat_id,
            f"🏷 <b>Теги аудитории</b>\n"
            f"Текущие: {', '.join(current) or 'нет'}\n\n"
            "Нажмите для добавления/удаления:",
            kb_inline_audience_tags(tags, source_id, current)
        )


def show_tags_menu(chat_id: int, user_id: int):
    """Show tags management"""
    tags = DB.get_audience_tags(user_id)
    DB.set_user_state(user_id, 'audiences:tags')
    
    if not tags:
        send_message(chat_id, "🏷 <b>Теги</b>\n\nУ вас пока нет тегов.", kb_audience_tags())
    else:
        send_message(chat_id, f"🏷 <b>Ваши теги ({len(tags)}):</b>", kb_inline_tags(tags))
        send_message(chat_id, "👆 Нажмите 🗑 для удаления или:", kb_audience_tags())


def show_blacklist_menu(chat_id: int, user_id: int):
    """Show blacklist menu"""
    blacklist = DB.get_blacklist_items(user_id)
    DB.set_user_state(user_id, 'audiences:blacklist')
    
    send_message(chat_id,
        f"🚫 <b>Чёрный список</b>\n\n"
        f"Записей: <b>{len(blacklist)}</b>\n\n"
        "Пользователи из этого списка не будут получать рассылку.",
        kb_blacklist_menu()
    )


def show_blacklist_list(chat_id: int, user_id: int):
    """Show blacklist items"""
    items = DB.get_blacklist_items(user_id)
    
    if not items:
        send_message(chat_id, "🚫 <b>Чёрный список пуст</b>", kb_blacklist_menu())
    else:
        send_message(chat_id, "🚫 <b>Чёрный список:</b>", kb_inline_blacklist(items))
        send_message(chat_id, "👆 Нажмите ✖️ для удаления", kb_blacklist_menu())
