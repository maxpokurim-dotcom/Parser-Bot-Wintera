"""
Template management handlers
Static menu version
"""
import logging
from api.db import DB
from api.telegram import send_message, send_media, answer_callback
from api.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel, kb_confirm_delete,
    kb_templates_menu, kb_template_actions, kb_folder_actions,
    kb_inline_templates, kb_inline_folder_templates, kb_inline_template_folders
)
from api.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

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
    """Show templates menu"""
    DB.set_user_state(user_id, 'templates:menu')
    templates = DB.get_templates(user_id)
    folders = DB.get_template_folders(user_id)
    
    send_message(chat_id,
        f"📄 <b>Шаблоны</b>\n\n"
        f"📝 Шаблонов: <b>{len(templates)}</b>\n"
        f"📁 Папок: <b>{len(folders)}</b>",
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
            "• <code>{username}</code> — @username",
            kb_back_cancel()
        )
        return True
    
    # Create template -
