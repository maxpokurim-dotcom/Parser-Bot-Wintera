"""
Audience management handlers - Extended v2.0
With stop triggers integration and keyword filter display
"""
import logging
from core.db import DB
from core.telegram import send_message, send_document, answer_callback
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel,
    kb_audiences_menu, kb_audience_actions, kb_audience_tags,
    kb_blacklist_menu, kb_confirm_delete, kb_stop_triggers_menu,
    kb_inline_audiences, kb_inline_tags, kb_inline_audience_tags, 
    kb_inline_blacklist, kb_inline_stop_triggers
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
BTN_STOP_WORDS = '🛡 Стоп-слова'
BTN_CONFIRM_DELETE = '🗑 Да, удалить'


def show_audiences_menu(chat_id: int, user_id: int):
    """Show audiences menu with comprehensive description"""
    DB.set_user_state(user_id, 'audiences:menu')
    sources = DB.get_audience_sources(user_id)
    total = sum(s.get('parsed_count', 0) for s in sources)
    completed = sum(1 for s in sources if s.get('status') == 'completed')
    with_keywords = sum(1 for s in sources if s.get('keyword_filter'))
    
    blacklist_count = len(DB.get_blacklist(user_id))
    
    send_message(chat_id,
        f"📊 <b>Управление аудиториями</b>\n\n"
        f"<i>Работа с собранными контактами из каналов,\n"
        f"групп и парсинга. Теги, фильтрация, экспорт.</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📈 СТАТИСТИКА</b>\n"
        f"├ Источников: <b>{len(sources)}</b>\n"
        f"├ Готовых: <b>{completed}</b>\n"
        f"├ С ключевыми словами: <b>{with_keywords}</b>\n"
        f"├ Всего контактов: <b>{total}</b>\n"
        f"└ В чёрном списке: <b>{blacklist_count}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>🛠 Возможности:</b>\n"
        f"• <b>Список</b> — все собранные аудитории\n"
        f"• <b>Теги</b> — категоризация контактов\n"
        f"• <b>Чёрный список</b> — исключённые контакты\n"
        f"• <b>Поиск</b> — найти конкретный контакт\n"
        f"• <b>Экспорт</b> — выгрузка в файл\n\n"
        f"💡 <i>Используйте теги для сегментации\n"
        f"и таргетированных рассылок</i>",
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
        elif state in ['audiences:tags', 'audiences:blacklist', 'audiences:stop_triggers']:
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
        
        if text == BTN_AUD_TAGS or text == '🏷 Теги':
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
        if text == BTN_STOP_WORDS or text == '🛡 Стоп-слова':
            show_stop_triggers_menu(chat_id, user_id)
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
        
        result = DB.add_to_blacklist(user_id, tg_user_id=tg_id, username=username, source='manual')
        display = f"@{username}" if username else str(tg_id)
        
        if result:
            send_message(chat_id, f"✅ {display} добавлен в чёрный список", kb_blacklist_menu())
        else:
            send_message(chat_id, "❌ Ошибка добавления", kb_blacklist_menu())
        
        DB.set_user_state(user_id, 'audiences:blacklist')
        return True
    
    # Stop triggers menu (also handled in settings, but accessible from blacklist)
    if state == 'audiences:stop_triggers':
        if text == '➕ Добавить слово':
            DB.set_user_state(user_id, 'audiences:add_stop_word')
            send_message(chat_id,
                "🛡 <b>Добавление стоп-слова</b>\n\n"
                "Введите слово или фразу.\n"
                "При получении сообщения с этим словом пользователь будет добавлен в чёрный список.",
                kb_back_cancel()
            )
            return True
        if text == '📋 Список слов':
            show_stop_triggers_list(chat_id, user_id)
            return True
    
    # Add stop word
    if state == 'audiences:add_stop_word':
        word = text.strip().lower()
        if len(word) < 2:
            send_message(chat_id, "❌ Слово должно быть минимум 2 символа", kb_back_cancel())
            return True
        if len(word) > 100:
            send_message(chat_id, "❌ Максимум 100 символов", kb_back_cancel())
            return True
        
        result = DB.add_stop_trigger(user_id, word)
        if result:
            send_message(chat_id, f"✅ Стоп-слово «{word}» добавлено", kb_stop_triggers_menu())
        else:
            send_message(chat_id, "❌ Ошибка добавления", kb_stop_triggers_menu())
        DB.set_user_state(user_id, 'audiences:stop_triggers')
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
    
    # Stop trigger toggle
    if data.startswith('togstop:'):
        trigger_id = int(data.split(':')[1])
        trigger = DB._select('stop_triggers', filters={'id': trigger_id}, single=True)
        if trigger:
            new_active = not trigger.get('is_active', True)
            DB._update('stop_triggers', {'is_active': new_active}, {'id': trigger_id})
        show_stop_triggers_list(chat_id, user_id)
        return True
    
    # Stop trigger deletion
    if data.startswith('delstop:'):
        trigger_id = int(data.split(':')[1])
        DB.delete_stop_trigger(trigger_id)
        show_stop_triggers_list(chat_id, user_id)
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
            "📊 <b>Выберите аудиторию:</b>\n\n"
            "🔑 — есть фильтр по ключевым словам",
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
    
    # Keyword filter info
    kw_info = ""
    if source.get('keyword_filter'):
        keywords = source['keyword_filter']
        mode = 'любое' if source.get('keyword_match_mode') == 'any' else 'все'
        kw_preview = ', '.join(keywords[:5])
        if len(keywords) > 5:
            kw_preview += f'... (+{len(keywords) - 5})'
        kw_info = (
            f"\n\n🔑 <b>Ключевые слова ({len(keywords)}):</b>\n"
            f"<code>{kw_preview}</code>\n"
            f"🔍 Режим: {mode}"
        )
    
    # Filters info
    filters = source.get('filters', {})
    filters_info = ""
    if filters:
        f_parts = []
        if filters.get('only_username'):
            f_parts.append('только с username')
        if filters.get('only_photo'):
            f_parts.append('только с фото')
        if filters.get('exclude_bots'):
            f_parts.append('без ботов')
        if f_parts:
            filters_info = f"\n🔧 <b>Фильтры:</b> {', '.join(f_parts)}"
    
    # Error info
    error_info = ""
    if source.get('error'):
        error_info = f"\n\n⚠️ <b>Ошибка:</b> {source['error'][:100]}"
    
    send_message(chat_id,
        f"📊 <b>Аудитория #{source_id}</b>\n\n"
        f"🔗 Источник: {source['source_link']}\n"
        f"📈 Статус: {status_map.get(source['status'], source['status'])}\n"
        f"🏷 Теги: {tags_str}{filters_info}\n\n"
        f"<b>👥 Статистика:</b>\n"
        f"├ Всего: <b>{stats['total']}</b>\n"
        f"├ Отправлено: <b>{stats['sent']}</b>\n"
        f"└ Осталось: <b>{stats['remaining']}</b>"
        f"{kw_info}{error_info}",
        kb_audience_actions()
    )


def export_audience(chat_id: int, user_id: int, source_id: int):
    """Export audience to CSV"""
    users = DB.get_audience_with_filters(source_id, limit=5000)
    
    if not users:
        send_message(chat_id, "❌ Аудитория пуста", kb_audience_actions())
        return
    
    csv_lines = ["username,first_name,last_name,tg_user_id,sent,has_photo,is_premium"]
    for u in users:
        un = u.get('username', '') or ''
        fn = (u.get('first_name', '') or '').replace(',', ' ')
        ln = (u.get('last_name', '') or '').replace(',', ' ')
        tg_id = u.get('tg_user_id', '') or ''
        st = 'yes' if u.get('sent') else 'no'
        photo = 'yes' if u.get('has_photo') else 'no'
        premium = 'yes' if u.get('is_premium') else 'no'
        csv_lines.append(f"{un},{fn},{ln},{tg_id},{st},{photo},{premium}")
    
    csv_content = '\n'.join(csv_lines)
    send_document(chat_id, csv_content.encode('utf-8'), 
                  f"audience_{source_id}.csv", 
                  f"📤 Экспорт аудитории #{source_id}\n👥 Пользователей: {len(users)}",
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
    triggers = DB.get_stop_triggers(user_id)
    active_triggers = sum(1 for t in triggers if t.get('is_active'))
    
    # Count by source
    manual = sum(1 for b in blacklist if b.get('source') == 'manual')
    auto = sum(1 for b in blacklist if b.get('source') != 'manual')
    
    DB.set_user_state(user_id, 'audiences:blacklist')
    
    send_message(chat_id,
        f"🚫 <b>Чёрный список</b>\n\n"
        f"Всего записей: <b>{len(blacklist)}</b>\n"
        f"├ Вручную: {manual}\n"
        f"└ Автоматически: {auto}\n\n"
        f"🛡 Активных стоп-слов: <b>{active_triggers}</b>\n\n"
        "Пользователи из этого списка не будут получать рассылку.",
        kb_blacklist_menu()
    )


def show_blacklist_list(chat_id: int, user_id: int):
    """Show blacklist items"""
    items = DB.get_blacklist_items(user_id)
    
    if not items:
        send_message(chat_id, "🚫 <b>Чёрный список пуст</b>", kb_blacklist_menu())
    else:
        send_message(chat_id, 
            "🚫 <b>Чёрный список:</b>\n\n"
            "✋ — добавлен вручную\n"
            "🤖 — автоматически по ответу\n"
            "🚫 — автоблокировка",
            kb_inline_blacklist(items))
        send_message(chat_id, "👆 Нажмите ✖️ для удаления", kb_blacklist_menu())


def show_stop_triggers_menu(chat_id: int, user_id: int):
    """Show stop triggers menu from blacklist"""
    DB.set_user_state(user_id, 'audiences:stop_triggers')
    
    triggers = DB.get_stop_triggers(user_id)
    active = sum(1 for t in triggers if t.get('is_active'))
    total_hits = sum(t.get('hits_count', 0) or 0 for t in triggers)
    
    send_message(chat_id,
        f"🛡 <b>Стоп-слова</b>\n\n"
        f"Всего слов: <b>{len(triggers)}</b>\n"
        f"Активных: <b>{active}</b>\n"
        f"Срабатываний: <b>{total_hits}</b>\n\n"
        f"При получении ответа с одним из этих слов, "
        f"пользователь добавляется в чёрный список.",
        kb_stop_triggers_menu()
    )


def show_stop_triggers_list(chat_id: int, user_id: int):
    """Show list of stop triggers"""
    triggers = DB.get_stop_triggers(user_id)
    
    if not triggers:
        send_message(chat_id,
            "🛡 <b>Стоп-слова</b>\n\n"
            "Список пуст. Добавьте первое слово!",
            kb_stop_triggers_menu()
        )
    else:
        send_message(chat_id,
            f"🛡 <b>Стоп-слова ({len(triggers)}):</b>\n\n"
            f"✅ — активно, ❌ — отключено\n"
            f"Число в скобках — количество срабатываний",
            kb_inline_stop_triggers(triggers)
        )
        send_message(chat_id, "👆 Нажмите для вкл/выкл или удаления", kb_stop_triggers_menu())
