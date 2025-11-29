# api/audiences.py
"""
Audience management handlers
"""
import logging
from api.db import DB
from api.telegram import edit_message, send_message, send_document
from api.keyboards import (
    kb_main, kb_cancel, kb_audiences_empty, kb_audiences_list,
    kb_audience_actions, kb_tags_select, kb_delete_confirm
)

logger = logging.getLogger(__name__)

def handle_audience_cb(chat_id: int, msg_id: int, user_id: int, data: str, saved: dict):
    if data == 'menu:audiences':
        sources = DB.get_audience_sources(user_id)
        if not sources:
            edit_message(chat_id, msg_id,
                "📊 <b>Ваши аудитории</b>\n"
                "У вас пока нет аудиторий.\n"
                "Создайте через парсинг!", kb_audiences_empty())
        else:
            total = sum(s.get('parsed_count', 0) for s in sources)
            completed = sum(1 for s in sources if s.get('status') == 'completed')
            edit_message(chat_id, msg_id,
                f"📊 <b>Ваши аудитории</b>\n"
                f"📁 Всего: <b>{len(sources)}</b>\n"
                f"✅ Готовых: <b>{completed}</b>\n"
                f"👥 Пользователей: <b>{total}</b>", kb_audiences_list(sources))

    elif data.startswith('audience:view:'):
        src_id = int(data.split(':')[2])
        source = DB.get_audience_source(src_id)
        if not source:
            sources = DB.get_audience_sources(user_id)
            if sources:
                edit_message(chat_id, msg_id, "❌ Аудитория не найдена или была удалена", kb_audiences_list(sources))
            else:
                edit_message(chat_id, msg_id, "❌ Аудитория не найдена", kb_audiences_empty())
            return
        stats = DB.get_audience_stats(src_id)
        status_map = {'pending': '⏳ В очереди', 'running': '🔄 Выполняется', 'completed': '✅ Готово', 'failed': '❌ Ошибка'}
        tags_str = ', '.join(source.get('tags', [])) or 'нет'
        edit_message(chat_id, msg_id,
            f"📊 <b>Аудитория #{src_id}</b>\n"
            f"🔗 Источник: {source['source_link']}\n"
            f"📈 Статус: {status_map.get(source['status'], source['status'])}\n"
            f"🏷 Теги: {tags_str}\n"
            f"<b>👥 Статистика:</b>\n"
            f"├ Всего: <b>{stats['total']}</b>\n"
            f"├ Отправлено: <b>{stats['sent']}</b>\n"
            f"└ Осталось: <b>{stats['remaining']}</b>", kb_audience_actions(src_id, source['status']))

    elif data.startswith('audience:search:'):
        src_id = int(data.split(':')[2])
        DB.set_user_state(user_id, 'waiting_audience_search', {'source_id': src_id})
        edit_message(chat_id, msg_id, "🔍 <b>Поиск в аудитории</b>\nВведите @username или имя:", kb_cancel())

    elif data.startswith('audience:export:'):
        src_id = int(data.split(':')[2])
        users = DB.get_audience_with_filters(src_id, limit=1000)
        if not users:
            edit_message(chat_id, msg_id, "❌ Аудитория пуста", kb_main())
            return
        csv_lines = ["username,first_name,last_name,sent"]
        for u in users:
            un = u.get('username', '') or ''
            fn = (u.get('first_name', '') or '').replace(',', ' ')
            ln = (u.get('last_name', '') or '').replace(',', ' ')
            st = 'yes' if u.get('sent') else 'no'
            csv_lines.append(f"{un},{fn},{ln},{st}")
        csv_content = '\n'.join(csv_lines)
        send_document(chat_id, csv_content.encode('utf-8'), f"audience_{src_id}.csv", "📤 Экспорт аудитории")

    elif data.startswith('audience:tags:'):
        src_id = int(data.split(':')[2])
        tags = DB.get_audience_tags(user_id)
        source = DB.get_audience_source(src_id)
        current = source.get('tags', []) if source else []
        edit_message(chat_id, msg_id,
            f"🏷 <b>Теги аудитории</b>\n"
            f"Текущие: {', '.join(current) or 'нет'}\n"
            f"Нажмите для добавления/удаления:", kb_tags_select(src_id, tags, current))

    elif data.startswith('audience:toggle_tag:'):
        parts = data.split(':')
        src_id, tag = int(parts[2]), parts[3]
        source = DB.get_audience_source(src_id)
        if source:
            current = source.get('tags') or []
            if tag in current:
                DB.remove_tag_from_source(src_id, tag)
            else:
                DB.add_tag_to_source(src_id, tag)
        tags = DB.get_audience_tags(user_id)
        source = DB.get_audience_source(src_id)
        current = source.get('tags', []) if source else []
        edit_message(chat_id, msg_id, f"🏷 Теги: {', '.join(current) or 'нет'}", kb_tags_select(src_id, tags, current))

    elif data.startswith('audience:delete:'):
        src_id = int(data.split(':')[2])
        edit_message(chat_id, msg_id,
            "🗑 <b>Удалить аудиторию?</b>\n"
            "⚠️ Все пользователи будут удалены безвозвратно.", kb_delete_confirm('audience', src_id))

    elif data.startswith('audience:confirm_delete:'):
        src_id = int(data.split(':')[2])
        logger.info(f"Deleting audience source {src_id} for user {user_id}")
        result = DB.delete_audience_source(src_id)
        logger.info(f"Delete result: {result}")
        
        # Получаем актуальный список после удаления
        sources = DB.get_audience_sources(user_id)
        if sources:
            total = sum(s.get('parsed_count', 0) for s in sources)
            completed = sum(1 for s in sources if s.get('status') == 'completed')
            edit_message(chat_id, msg_id,
                f"✅ Аудитория удалена\n\n"
                f"📊 <b>Ваши аудитории</b>\n"
                f"📁 Всего: <b>{len(sources)}</b>\n"
                f"✅ Готовых: <b>{completed}</b>\n"
                f"👥 Пользователей: <b>{total}</b>", kb_audiences_list(sources))
        else:
            edit_message(chat_id, msg_id, 
                "✅ Аудитория удалена\n\n"
                "📊 <b>Ваши аудитории</b>\n"
                "У вас пока нет аудиторий.", kb_audiences_empty())

    elif data == 'audience:cancel_delete':
        sources = DB.get_audience_sources(user_id)
        if sources:
            edit_message(chat_id, msg_id, "📊 <b>Ваши аудитории</b>", kb_audiences_list(sources))
        else:
            edit_message(chat_id, msg_id, "📊 <b>Ваши аудитории</b>", kb_audiences_empty())

    elif data == 'audience:list':
        sources = DB.get_audience_sources(user_id)
        if sources:
            edit_message(chat_id, msg_id, "📊 <b>Аудитории</b>", kb_audiences_list(sources))
        else:
            edit_message(chat_id, msg_id, "📊 <b>Аудитории</b>\nПока нет аудиторий.", kb_audiences_empty())


def handle_audience_state(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Returns True if state was handled"""
    
    if state == 'waiting_audience_search':
        source_id = saved.get('source_id')
        if not source_id:
            DB.clear_user_state(user_id)
            send_message(chat_id, "❌ Ошибка: источник не найден", kb_main())
            return True
        results = DB.search_in_audience(source_id, text.strip(), limit=20)
        DB.clear_user_state(user_id)
        if not results:
            send_message(chat_id, f"🔍 По запросу «{text}» ничего не найдено", kb_main())
        else:
            txt = f"🔍 <b>Найдено ({len(results)}):</b>\n"
            for u in results[:10]:
                un = f"@{u['username']}" if u.get('username') else "—"
                st = "✅" if u.get('sent') else "⏳"
                name = u.get('first_name', '') or ''
                txt += f"{st} {un} | {name}\n"
            send_message(chat_id, txt, kb_main())
        return True

    return False