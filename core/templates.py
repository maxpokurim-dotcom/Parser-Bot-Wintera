"""
Template management handlers
Static menu version with Storage support
"""
import logging
from core.db import DB
from core.telegram import (
    send_message, send_media, send_media_by_url, 
    answer_callback, download_telegram_file
)
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel, kb_confirm_delete,
    kb_templates_menu, kb_template_actions, kb_folder_actions,
    kb_inline_templates, kb_inline_folder_templates, kb_inline_template_folders
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_TPL_LIST = '📋 Список шаблонов'
BTN_TPL_FOLDERS = '📁 Папки'
BTN_TPL_CREATE = '➕ Создать шаблон'
BTN_TPL_CREATE_FOLDER = '📁 Создать папку'
BTN_TPL_PREVIEW = '👁 Предпросмотр'
BTN_TPL_COPY = '📋 Копировать'
BTN_TPL_MOVE = '📁 Переместить'
BTN_TPL_DELETE = '🗑 Удалить'
BTN_TPL_BACK_LIST = '◀️ К списку'
BTN_FOLDER_TEMPLATES = '📋 Шаблоны в папке'
BTN_FOLDER_CREATE_TPL = '➕ Создать шаблон'
BTN_FOLDER_RENAME = '✏️ Переименовать'
BTN_FOLDER_DELETE = '🗑 Удалить папку'
BTN_CONFIRM_DELETE = '🗑 Да, удалить'


def show_templates_menu(chat_id: int, user_id: int):
    """Show templates menu with comprehensive description"""
    DB.set_user_state(user_id, 'templates:menu')
    templates = DB.get_templates(user_id)
    folders = DB.get_template_folders(user_id)
    
    # Count templates by type
    text_count = sum(1 for t in templates if t.get('media_type') == 'text' or not t.get('media_type'))
    media_count = len(templates) - text_count
    
    send_message(chat_id,
        f"📄 <b>Шаблоны сообщений</b>\n\n"
        f"<i>Создавайте и управляйте шаблонами\n"
        f"для быстрой настройки рассылок.</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📊 СТАТИСТИКА</b>\n"
        f"├ Всего шаблонов: <b>{len(templates)}</b>\n"
        f"├ Текстовых: <b>{text_count}</b>\n"
        f"├ С медиа: <b>{media_count}</b>\n"
        f"└ Папок: <b>{len(folders)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>🛠 Возможности:</b>\n"
        f"• <b>Создать</b> — новый шаблон с текстом/медиа\n"
        f"• <b>Список</b> — все сохранённые шаблоны\n"
        f"• <b>Папки</b> — группировка по категориям\n"
        f"• <b>Предпросмотр</b> — проверка перед отправкой\n\n"
        f"💡 <i>Используйте переменные в шаблонах:\n"
        f"{{name}} — имя получателя\n"
        f"{{username}} — @username</i>",
        kb_templates_menu()
    )


def handle_templates(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle template states. Returns True if handled."""
    
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Действие отменено")
        return True
    
    if text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return True
    
    if text == BTN_BACK:
        if state in ['templates:menu', 'templates:list']:
            show_main_menu(chat_id, user_id)
        elif state.startswith('templates:view:') or state.startswith('templates:folder:'):
            show_template_list(chat_id, user_id)
        elif state.startswith('templates:'):
            show_templates_menu(chat_id, user_id)
        return True
    
    if text == BTN_TPL_BACK_LIST:
        show_template_list(chat_id, user_id)
        return True
    
    # Menu state
    if state == 'templates:menu':
        if text == BTN_TPL_LIST:
            show_template_list(chat_id, user_id)
            return True
        if text == BTN_TPL_FOLDERS:
            show_template_list(chat_id, user_id)
            return True
        if text == BTN_TPL_CREATE:
            start_template_creation(chat_id, user_id)
            return True
        if text == BTN_TPL_CREATE_FOLDER:
            DB.set_user_state(user_id, 'templates:create_folder')
            send_message(chat_id, "📁 Введите название папки (макс. 50 символов):", kb_back_cancel())
            return True
    
    # Create folder
    if state == 'templates:create_folder':
        name = text.strip()
        if len(name) > 50:
            send_message(chat_id, "❌ Максимум 50 символов", kb_back_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите название:", kb_back_cancel())
            return True
        
        folder = DB.create_template_folder(user_id, name)
        if folder:
            send_message(chat_id, f"✅ Папка «{name}» создана!", kb_templates_menu())
        else:
            send_message(chat_id, "❌ Ошибка создания", kb_templates_menu())
        show_templates_menu(chat_id, user_id)
        return True
    
    # Create template - name
    if state == 'templates:create_name':
        name = text.strip()
        if len(name) > 100:
            send_message(chat_id, "❌ Максимум 100 символов", kb_back_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите название:", kb_back_cancel())
            return True
        
        saved['name'] = name
        DB.set_user_state(user_id, 'templates:create_text', saved)
        send_message(chat_id,
            f"✅ Название: <b>{name}</b>\n\n"
            "✏️ Теперь введите текст шаблона.\n"
            "<i>Или отправьте фото/видео — текст можно добавить как подпись.</i>\n\n"
            "Доступные переменные:\n"
            "• <code>{name}</code> — имя\n"
            "• <code>{first_name}</code> — имя\n"
            "• <code>{username}</code> — @username",
            kb_back_cancel()
        )
        return True
    
    # Create template - text (only plain text, media handled separately)
    if state == 'templates:create_text':
        template_text = text.strip()
        if len(template_text) > 4000:
            send_message(chat_id, "❌ Максимум 4000 символов", kb_back_cancel())
            return True
        if len(template_text) < 1:
            send_message(chat_id, "❌ Введите текст шаблона:", kb_back_cancel())
            return True
        
        template_name = saved.get('name', 'Без названия')
        folder_id = saved.get('folder_id')
        
        template = DB.create_template(user_id, template_name, template_text, folder_id=folder_id)
        DB.clear_user_state(user_id)
        
        if template:
            send_message(chat_id,
                f"✅ <b>Шаблон создан!</b>\n\n"
                f"📝 Название: {template_name}\n"
                f"📏 Длина: {len(template_text)} символов",
                kb_templates_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания шаблона", kb_templates_menu())
        return True
    
    # View template state
    if state.startswith('templates:view:'):
        template_id = int(state.split(':')[2])
        
        if text == BTN_TPL_PREVIEW:
            show_template_preview(chat_id, user_id, template_id)
            return True
        
        if text == BTN_TPL_COPY:
            new_template = DB.copy_template(template_id, user_id)
            if new_template:
                send_message(chat_id,
                    f"✅ Шаблон скопирован!\n"
                    f"📝 Название: {new_template['name']}",
                    kb_template_actions()
                )
            else:
                send_message(chat_id, "❌ Ошибка копирования", kb_template_actions())
            return True
        
        if text == BTN_TPL_MOVE:
            show_move_template(chat_id, user_id, template_id)
            return True
        
        if text == BTN_TPL_DELETE:
            DB.set_user_state(user_id, f'templates:delete:{template_id}')
            send_message(chat_id,
                "🗑 <b>Удалить шаблон?</b>\n\n"
                "⚠️ Это действие необратимо.",
                kb_confirm_delete()
            )
            return True
    
    # Delete template confirm
    if state.startswith('templates:delete:'):
        template_id = int(state.split(':')[2])
        
        if text == BTN_CONFIRM_DELETE:
            # Get template to delete media from Storage
            template = DB.get_template(template_id)
            if template and template.get('media_url'):
                DB.delete_template_media(template['media_url'])
            
            DB.delete_template(template_id)
            send_message(chat_id, "✅ Шаблон удалён", kb_templates_menu())
            show_template_list(chat_id, user_id)
            return True
        
        if text == BTN_CANCEL:
            show_template_view(chat_id, user_id, template_id)
            return True
    
    # Folder view state
    if state.startswith('templates:folder:'):
        folder_id = int(state.split(':')[2])
        
        if text == BTN_FOLDER_TEMPLATES:
            show_folder_templates(chat_id, user_id, folder_id)
            return True
        
        if text == BTN_FOLDER_CREATE_TPL:
            start_template_creation(chat_id, user_id, folder_id)
            return True
        
        if text == BTN_FOLDER_RENAME:
            DB.set_user_state(user_id, f'templates:rename_folder:{folder_id}')
            send_message(chat_id, "✏️ Введите новое название папки:", kb_back_cancel())
            return True
        
        if text == BTN_FOLDER_DELETE:
            DB.set_user_state(user_id, f'templates:delete_folder:{folder_id}')
            send_message(chat_id,
                "🗑 <b>Удалить папку?</b>\n\n"
                "⚠️ Шаблоны будут перемещены в корень.",
                kb_confirm_delete()
            )
            return True
    
    # Rename folder
    if state.startswith('templates:rename_folder:'):
        folder_id = int(state.split(':')[2])
        name = text.strip()
        
        if len(name) > 50:
            send_message(chat_id, "❌ Максимум 50 символов", kb_back_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите название:", kb_back_cancel())
            return True
        
        DB.rename_template_folder(folder_id, name)
        send_message(chat_id, f"✅ Папка переименована в «{name}»", kb_folder_actions())
        show_folder_view(chat_id, user_id, folder_id)
        return True
    
    # Delete folder confirm
    if state.startswith('templates:delete_folder:'):
        folder_id = int(state.split(':')[2])
        
        if text == BTN_CONFIRM_DELETE:
            DB.delete_template_folder(folder_id)
            send_message(chat_id, "✅ Папка удалена", kb_templates_menu())
            show_template_list(chat_id, user_id)
            return True
        
        if text == BTN_CANCEL:
            show_folder_view(chat_id, user_id, folder_id)
            return True
    
    return False


def handle_templates_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle template inline callbacks"""
    
    # Template selection
    if data.startswith('tpl:'):
        template_id = int(data.split(':')[1])
        show_template_view(chat_id, user_id, template_id)
        return True
    
    # Folder selection
    if data.startswith('tfld:'):
        folder_id = int(data.split(':')[1])
        show_folder_view(chat_id, user_id, folder_id)
        return True
    
    # Move template to folder
    if data.startswith('mvtpl:'):
        parts = data.split(':')
        template_id = int(parts[1])
        folder_id = int(parts[2]) if parts[2] != '0' else None
        
        DB.update_template_folder(template_id, folder_id)
        send_message(chat_id, "✅ Шаблон перемещён!", kb_template_actions())
        show_template_view(chat_id, user_id, template_id)
        return True
    
    # Select folder for new template
    if data.startswith('selfld:'):
        folder_id = int(data.split(':')[1]) if data.split(':')[1] != '0' else None
        state_data = DB.get_user_state(user_id)
        saved = state_data.get('data', {}) if state_data else {}
        saved['folder_id'] = folder_id
        
        DB.set_user_state(user_id, 'templates:create_name', saved)
        send_message(chat_id, "📝 Введите название шаблона (макс. 100 символов):", kb_back_cancel())
        return True
    
    return False


def handle_template_media(chat_id: int, user_id: int, message: dict, state: str, saved: dict) -> bool:
    """Handle media messages for template creation with Storage upload"""
    if state != 'templates:create_text':
        return False
    
    media_types = {
        'photo': 'photo', 
        'video': 'video', 
        'document': 'document', 
        'audio': 'audio', 
        'voice': 'voice'
    }
    
    for media_key, media_type in media_types.items():
        if media_key in message:
            # Get file_id
            if media_key == 'photo':
                file_id = message['photo'][-1]['file_id']  # Largest photo
            else:
                file_id = message[media_key]['file_id']
            
            template_name = saved.get('name', 'Без названия')
            folder_id = saved.get('folder_id')
            caption = message.get('caption', '')
            
            # Send processing message
            send_message(chat_id, "⏳ Загружаю медиа...", kb_cancel())
            
            # Try to download file from Telegram
            file_content, file_extension = download_telegram_file(file_id)
            
            if file_content:
                # Upload to Storage and create template
                template = DB.create_template_with_media(
                    user_id=user_id,
                    name=template_name,
                    text=caption,
                    file_content=file_content,
                    file_extension=file_extension,
                    media_type=media_type,
                    media_file_id=file_id,  # Keep as fallback
                    folder_id=folder_id
                )
            else:
                # Fallback: save only file_id (won't work with Telethon)
                logger.warning(f"Failed to download file, saving file_id only")
                template = DB.create_template(
                    user_id, template_name, caption,
                    media_file_id=file_id, media_type=media_type, folder_id=folder_id
                )
            
            DB.clear_user_state(user_id)
            
            if template:
                storage_info = ""
                if template.get('media_url'):
                    storage_info = "\n☁️ Медиа сохранено в облако"
                
                send_message(chat_id,
                    f"✅ <b>Медиа-шаблон создан!</b>\n"
                    f"📝 Название: {template_name}\n"
                    f"📎 Тип: {media_type}"
                    f"{storage_info}",
                    kb_templates_menu()
                )
            else:
                send_message(chat_id, "❌ Ошибка сохранения", kb_templates_menu())
            return True
    
    return False


def start_template_creation(chat_id: int, user_id: int, folder_id: int = None):
    """Start template creation flow"""
    folders = DB.get_template_folders(user_id)
    
    if folders and folder_id is None:
        # Ask to select folder
        DB.set_user_state(user_id, 'templates:select_folder')
        send_message(chat_id,
            "📁 <b>Выберите папку для шаблона:</b>",
            kb_inline_template_folders(folders, 'select')
        )
        send_message(chat_id, "👆 Выберите папку выше", kb_back_cancel())
    else:
        # Start name input
        DB.set_user_state(user_id, 'templates:create_name', {'folder_id': folder_id})
        send_message(chat_id,
            "📝 <b>Создание шаблона</b>\n\n"
            "Введите название шаблона (макс. 100 символов):",
            kb_back_cancel()
        )


def show_template_list(chat_id: int, user_id: int):
    """Show template list with folders"""
    templates = DB.get_templates(user_id)
    folders = DB.get_template_folders(user_id)
    
    DB.set_user_state(user_id, 'templates:list')
    
    if not templates and not folders:
        send_message(chat_id,
            "📄 <b>Список шаблонов</b>\n\n"
            "У вас пока нет шаблонов.\n"
            "Создайте первый шаблон!",
            kb_templates_menu()
        )
    else:
        kb = kb_inline_templates(templates, folders)
        if kb:
            send_message(chat_id, "📄 <b>Выберите шаблон или папку:</b>", kb)
        send_message(chat_id, "👆 Выберите выше или:", kb_templates_menu())


def show_template_view(chat_id: int, user_id: int, template_id: int):
    """Show template details"""
    template = DB.get_template(template_id)
    if not template:
        send_message(chat_id, "❌ Шаблон не найден", kb_templates_menu())
        return
    
    DB.set_user_state(user_id, f'templates:view:{template_id}')
    
    # Check if has media
    has_media = template.get('media_file_id') or template.get('media_url')
    
    if has_media:
        storage_info = "☁️ В облаке" if template.get('media_url') else "📱 Telegram"
        send_message(chat_id,
            f"🖼 <b>Медиа-шаблон: {template['name']}</b>\n\n"
            f"📎 Тип: {template.get('media_type', 'unknown')}\n"
            f"💾 Хранение: {storage_info}\n"
            f"🆔 ID: <code>{template['id']}</code>",
            kb_template_actions()
        )
    else:
        text_preview = template.get('text', '')[:300]
        if len(template.get('text', '')) > 300:
            text_preview += '\n<i>... (текст обрезан)</i>'
        
        send_message(chat_id,
            f"📝 <b>{template['name']}</b>\n\n"
            f"📏 Символов: {len(template.get('text', ''))}\n"
            f"🆔 ID: <code>{template['id']}</code>\n\n"
            f"<b>Текст:</b>\n{text_preview}",
            kb_template_actions()
        )


def show_template_preview(chat_id: int, user_id: int, template_id: int):
    """Show template preview with variable substitution"""
    template = DB.get_template(template_id)
    if not template:
        send_message(chat_id, "❌ Шаблон не найден", kb_template_actions())
        return
    
    # Replace variables with examples
    preview = template.get('text', '')
    preview = preview.replace('{name}', 'Иван')
    preview = preview.replace('{first_name}', 'Иван')
    preview = preview.replace('{last_name}', 'Иванов')
    preview = preview.replace('{username}', '@ivan_user')
    
    # Send media if present
    has_media = template.get('media_file_id') or template.get('media_url')
    
    if has_media:
        media_type = template.get('media_type', 'photo')
        
        # Prefer Storage URL, fallback to file_id
        if template.get('media_url'):
            send_media_by_url(chat_id, media_type, template['media_url'], preview)
        elif template.get('media_file_id'):
            send_media(chat_id, media_type, template['media_file_id'], preview)
    
    send_message(chat_id,
        f"👁 <b>Предпросмотр</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{preview}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Переменные заменены на примеры</i>",
        kb_template_actions()
    )


def show_move_template(chat_id: int, user_id: int, template_id: int):
    """Show folder selection for moving template"""
    folders = DB.get_template_folders(user_id)
    
    send_message(chat_id,
        "📁 <b>Выберите папку:</b>",
        kb_inline_template_folders(folders, 'move', template_id)
    )


def show_folder_view(chat_id: int, user_id: int, folder_id: int):
    """Show folder details"""
    folder = DB.get_template_folder(folder_id)
    if not folder:
        send_message(chat_id, "❌ Папка не найдена", kb_templates_menu())
        return
    
    templates = DB.get_templates(user_id, folder_id=folder_id)
    DB.set_user_state(user_id, f'templates:folder:{folder_id}')
    
    send_message(chat_id,
        f"📁 <b>{folder['name']}</b>\n\n"
        f"📝 Шаблонов: <b>{len(templates)}</b>",
        kb_folder_actions()
    )


def show_folder_templates(chat_id: int, user_id: int, folder_id: int):
    """Show templates in folder"""
    templates = DB.get_templates(user_id, folder_id=folder_id)
    folder = DB.get_template_folder(folder_id)
    
    if not templates:
        send_message(chat_id,
            f"📁 <b>{folder['name'] if folder else 'Папка'}</b>\n\n"
            "В этой папке пока нет шаблонов.",
            kb_folder_actions()
        )
    else:
        kb = kb_inline_folder_templates(templates, folder_id)
        send_message(chat_id, f"📁 <b>{folder['name'] if folder else 'Папка'}:</b>", kb)
        send_message(chat_id, "👆 Выберите шаблон выше", kb_folder_actions())
