# api/templates.py
"""
Template management handlers
"""
import logging
from api.db import DB
from api.telegram import edit_message, send_message, send_media
from api.keyboards import (
    kb_main, kb_cancel, kb_templates, kb_template_actions,
    kb_folder_templates, kb_template_folders_for_selection,
    kb_back, kb_delete_confirm
)

logger = logging.getLogger(__name__)

def handle_template_cb(chat_id: int, msg_id: int, user_id: int, data: str, saved: dict):
    if data in ['menu:templates', 'template:list']:
        templates = DB.get_templates(user_id)
        folders = DB.get_template_folders(user_id)
        edit_message(chat_id, msg_id,
            f"📄 <b>Ваши шаблоны</b>\n"
            f"📝 Шаблонов: <b>{len(templates)}</b>\n"
            f"📁 Папок: <b>{len(folders)}</b>", kb_templates(templates, folders))

    elif data.startswith('template:view:'):
        t_id = int(data.split(':')[2])
        t = DB.get_template(t_id)
        if not t:
            templates = DB.get_templates(user_id)
            folders = DB.get_template_folders(user_id)
            edit_message(chat_id, msg_id, 
                "❌ Шаблон не найден или был удалён\n\n"
                f"📄 <b>Ваши шаблоны</b>\n"
                f"📝 Шаблонов: <b>{len(templates)}</b>", kb_templates(templates, folders))
            return
        if t.get('media_file_id'):
            media_type = t['media_type']
            file_id = t['media_file_id']
            caption = t.get('text', '') or f"📝 {t['name']}"
            if len(caption) > 1024:
                caption = caption[:1021] + "..."
            send_message(chat_id, "🖼 <b>Медиа-шаблон</b>", kb_template_actions(t_id))
            send_media(chat_id, media_type, file_id, caption)
        else:
            text_preview = t.get('text', '')[:500]
            if len(t.get('text', '')) > 500:
                text_preview += '\n<i>... (текст обрезан)</i>'
            edit_message(chat_id, msg_id,
                f"📝 <b>{t['name']}</b>\n"
                f"📏 Символов: {len(t.get('text', ''))}\n"
                f"🆔 ID: <code>{t['id']}</code>\n"
                f"<b>Текст:</b>\n{text_preview}", kb_template_actions(t['id']))

    elif data == 'template:create':
        folders = DB.get_template_folders(user_id)
        if folders:
            edit_message(chat_id, msg_id,
                "📁 <b>Создание шаблона</b>\nВыберите папку для шаблона (или без папки):",
                kb_template_folders_for_selection(user_id, 'template_create'))
        else:
            DB.set_user_state(user_id, 'waiting_template_name', {'folder_id': None})
            edit_message(chat_id, msg_id,
                "📝 <b>Создание шаблона</b>\nВведите название шаблона (макс. 100 символов):", kb_cancel())

    elif data.startswith('folder:create_template:'):
        folder_id = int(data.split(':')[2])
        DB.set_user_state(user_id, 'waiting_template_name', {'folder_id': folder_id})
        edit_message(chat_id, msg_id,
            "📝 <b>Создание шаблона</b>\nВведите название шаблона (макс. 100 символов):", kb_cancel())

    elif data.startswith('template_create:folder:'):
        fid_str = data.split(':')[2]
        folder_id = None if fid_str == '0' else int(fid_str)
        DB.set_user_state(user_id, 'waiting_template_name', {'folder_id': folder_id})
        edit_message(chat_id, msg_id,
            "📝 <b>Создание шаблона</b>\nВведите название шаблона (макс. 100 символов):", kb_cancel())

    elif data.startswith('template:preview:'):
        t_id = int(data.split(':')[2])
        t = DB.get_template(t_id)
        if t:
            preview = t.get('text', '')
            preview = preview.replace('{name}', 'Иван')
            preview = preview.replace('{first_name}', 'Иван')
            preview = preview.replace('{last_name}', 'Иванов')
            preview = preview.replace('{username}', '@ivan_user')
            edit_message(chat_id, msg_id,
                f"👁 <b>Предпросмотр шаблона</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{preview}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Переменные заменены на примеры</i>", kb_back(f"template:view:{t['id']}"))
        else:
            templates = DB.get_templates(user_id)
            folders = DB.get_template_folders(user_id)
            edit_message(chat_id, msg_id, "❌ Шаблон не найден", kb_templates(templates, folders))

    elif data.startswith('template:copy:'):
        t_id = int(data.split(':')[2])
        new_t = DB.copy_template(t_id, user_id)
        if new_t:
            edit_message(chat_id, msg_id,
                f"✅ <b>Шаблон скопирован!</b>\n"
                f"📝 Название: {new_t['name']}\n"
                f"🆔 ID: <code>{new_t['id']}</code>", kb_template_actions(new_t['id']))
        else:
            templates = DB.get_templates(user_id)
            folders = DB.get_template_folders(user_id)
            edit_message(chat_id, msg_id, "❌ Ошибка копирования", kb_templates(templates, folders))

    elif data.startswith('template:delete:'):
        t_id = int(data.split(':')[2])
        edit_message(chat_id, msg_id,
            "🗑 <b>Удалить шаблон?</b>\n"
            "⚠️ Это действие необратимо.", kb_delete_confirm('template', t_id))

    elif data.startswith('template:confirm_delete:'):
        t_id = int(data.split(':')[2])
        logger.info(f"Deleting template {t_id} for user {user_id}")
        result = DB.delete_template(t_id)
        logger.info(f"Delete result: {result}")
        
        templates = DB.get_templates(user_id)
        folders = DB.get_template_folders(user_id)
        edit_message(chat_id, msg_id, 
            f"✅ Шаблон удалён\n\n"
            f"📄 <b>Ваши шаблоны</b>\n"
            f"📝 Шаблонов: <b>{len(templates)}</b>\n"
            f"📁 Папок: <b>{len(folders)}</b>", kb_templates(templates, folders))

    elif data == 'template:cancel_delete':
        templates = DB.get_templates(user_id)
        folders = DB.get_template_folders(user_id)
        edit_message(chat_id, msg_id, 
            f"📄 <b>Ваши шаблоны</b>\n"
            f"📝 Шаблонов: <b>{len(templates)}</b>\n"
            f"📁 Папок: <b>{len(folders)}</b>", kb_templates(templates, folders))

    elif data == 'folder:create':
        DB.set_user_state(user_id, 'waiting_folder_name')
        edit_message(chat_id, msg_id,
            "📁 <b>Создание папки</b>\n"
            "Введите название папки (макс. 50 символов):", kb_cancel())

    elif data.startswith('folder:view:'):
        folder_id = int(data.split(':')[2])
        folder = DB.get_template_folder(folder_id)
        if not folder:
            templates = DB.get_templates(user_id)
            folders = DB.get_template_folders(user_id)
            edit_message(chat_id, msg_id, "❌ Папка не найдена", kb_templates(templates, folders))
            return
        templates = DB.get_templates(user_id, folder_id=folder_id)
        edit_message(chat_id, msg_id, f"📁 <b>{folder['name']}</b> ({len(templates)} шаблонов)", kb_folder_templates(templates, folder_id))

    elif data.startswith('folder:delete:'):
        folder_id = int(data.split(':')[2])
        logger.info(f"Deleting template folder {folder_id} for user {user_id}")
        result = DB.delete_template_folder(folder_id)
        logger.info(f"Delete result: {result}")
        
        templates = DB.get_templates(user_id)
        folders = DB.get_template_folders(user_id)
        edit_message(chat_id, msg_id, 
            f"✅ Папка удалена\n\n"
            f"📄 <b>Ваши шаблоны</b>\n"
            f"📝 Шаблонов: <b>{len(templates)}</b>\n"
            f"📁 Папок: <b>{len(folders)}</b>", kb_templates(templates, folders))

    elif data.startswith('template:move:'):
        template_id = int(data.split(':')[2])
        edit_message(chat_id, msg_id,
            "📁 <b>Переместить шаблон</b>\nВыберите папку:",
            kb_template_folders_for_selection(user_id, 'template_move', {'template_id': template_id}))

    elif data.startswith('template_move:folder:'):
        parts = data.split(':')
        template_id = int(parts[2])
        fid_str = parts[3]
        folder_id = None if fid_str == '0' else int(fid_str)
        success = DB.update_template_folder(template_id, folder_id)
        if success:
            edit_message(chat_id, msg_id, "✅ Шаблон перемещён!", kb_template_actions(template_id))
        else:
            edit_message(chat_id, msg_id, "❌ Ошибка перемещения", kb_template_actions(template_id))


def handle_template_state(chat_id: int, user_id: int, text: str, state: str, saved: dict, message: dict = None) -> bool:
    """Returns True if state was handled"""
    
    if state == 'waiting_template_name':
        name = text.strip()
        if len(name) > 100:
            send_message(chat_id, "❌ Название слишком длинное. Максимум 100 символов.", kb_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите название шаблона:", kb_cancel())
            return True
        folder_id = saved.get('folder_id')
        DB.set_user_state(user_id, 'waiting_template_text', {'name': name, 'folder_id': folder_id})
        send_message(chat_id,
            f"✅ Название: <b>{name}</b>\n"
            "✏️ Теперь введите текст шаблона.\n"
            "<i>Или отправьте фото/видео/документ — текст можно добавить как подпись.</i>", kb_cancel())
        return True

    if state == 'waiting_template_text':
        template_text = text.strip()
        if len(template_text) > 4000:
            send_message(chat_id, "❌ Текст слишком длинный. Максимум 4000 символов.", kb_cancel())
            return True
        if len(template_text) < 1:
            send_message(chat_id, "❌ Введите текст шаблона:", kb_cancel())
            return True
        template_name = saved.get('name', 'Без названия')
        folder_id = saved.get('folder_id')
        template = DB.create_template(user_id, template_name, template_text, folder_id=folder_id)
        DB.clear_user_state(user_id)
        if template:
            send_message(chat_id,
                f"✅ <b>Шаблон создан!</b>\n"
                f"📝 Название: {template_name}\n"
                f"📏 Длина: {len(template_text)} символов", kb_main())
        else:
            send_message(chat_id, "❌ Ошибка создания шаблона", kb_main())
        return True

    if state == 'waiting_folder_name':
        name = text.strip()
        if len(name) > 50:
            send_message(chat_id, "❌ Максимум 50 символов", kb_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите название папки:", kb_cancel())
            return True
        folder = DB.create_template_folder(user_id, name)
        DB.clear_user_state(user_id)
        if folder:
            send_message(chat_id, f"✅ Папка «{name}» создана!", kb_main())
        else:
            send_message(chat_id, "❌ Ошибка создания папки", kb_main())
        return True

    return False


def handle_template_media(chat_id: int, user_id: int, message: dict, state: str, saved: dict) -> bool:
    """Handle media messages for template creation"""
    if state != 'waiting_template_text':
        return False
    
    media_types = {'photo': 'photo', 'video': 'video', 'document': 'document', 'audio': 'audio', 'voice': 'voice'}
    
    for media_key, media_type in media_types.items():
        if media_key in message:
            if media_key == 'photo':
                file_id = message['photo'][-1]['file_id']
            else:
                file_id = message[media_key]['file_id']
            
            template_name = saved.get('name', 'Без названия')
            folder_id = saved.get('folder_id')
            caption = message.get('caption', '')
            
            template = DB.create_template(
                user_id, template_name, caption,
                media_file_id=file_id, media_type=media_type, folder_id=folder_id
            )
            DB.clear_user_state(user_id)
            
            if template:
                send_message(chat_id, f"✅ <b>Медиа-шаблон создан!</b>\nНазвание: {template_name}", kb_main())
            else:
                send_message(chat_id, "❌ Ошибка сохранения медиа", kb_main())
            return True
    
    return False