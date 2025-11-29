"""
Account management handlers
Static menu version
"""
import re
import logging
from datetime import datetime
from core.db import DB
from core.telegram import send_message, answer_callback
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel, kb_confirm_delete,
    kb_accounts_menu, kb_account_actions, kb_account_limits, kb_acc_folder_actions,
    kb_inline_accounts, kb_inline_acc_folders, kb_inline_account_folders
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_ACC_LIST = '📋 Список аккаунтов'
BTN_ACC_FOLDERS = '📁 Папки'
BTN_ACC_ADD = '➕ Добавить аккаунт'
BTN_ACC_CREATE_FOLDER = '📁 Создать папку'
BTN_ACC_SET_LIMIT = '📊 Установить лимит'
BTN_ACC_MOVE = '📁 Переместить'
BTN_ACC_DELETE = '🗑 Удалить'
BTN_ACC_BACK_LIST = '◀️ К списку'
BTN_FOLDER_ACCOUNTS = '📋 Аккаунты в папке'
BTN_FOLDER_ADD_ACC = '➕ Добавить аккаунт'
BTN_FOLDER_RENAME = '✏️ Переименовать'
BTN_FOLDER_DELETE = '🗑 Удалить папку'
BTN_CONFIRM_DELETE = '🗑 Да, удалить'
BTN_CUSTOM_LIMIT = '📝 Свой лимит'


def show_accounts_menu(chat_id: int, user_id: int):
    """Show accounts menu"""
    DB.set_user_state(user_id, 'accounts:menu')
    
    total = DB.count_user_accounts(user_id)
    active = DB.count_active_user_accounts(user_id)
    folders = DB.get_account_folders(user_id)
    
    send_message(chat_id,
        f"👤 <b>Аккаунты</b>\n\n"
        f"📊 Всего: <b>{total}</b>\n"
        f"✅ Активных: <b>{active}</b>\n"
        f"📁 Папок: <b>{len(folders)}</b>",
        kb_accounts_menu()
    )


def handle_accounts(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle account states. Returns True if handled."""
    
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Действие отменено")
        return True
    
    if text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return True
    
    if text == BTN_BACK:
        if state in ['accounts:menu', 'accounts:list']:
            show_main_menu(chat_id, user_id)
        elif state.startswith('accounts:view:') or state.startswith('accounts:folder:'):
            show_account_list(chat_id, user_id)
        elif state.startswith('accounts:'):
            show_accounts_menu(chat_id, user_id)
        return True
    
    if text == BTN_ACC_BACK_LIST:
        show_account_list(chat_id, user_id)
        return True
    
    # Menu state
    if state == 'accounts:menu':
        if text == BTN_ACC_LIST:
            show_account_list(chat_id, user_id)
            return True
        if text == BTN_ACC_FOLDERS:
            show_account_list(chat_id, user_id)
            return True
        if text == BTN_ACC_ADD:
            start_add_account(chat_id, user_id)
            return True
        if text == BTN_ACC_CREATE_FOLDER:
            DB.set_user_state(user_id, 'accounts:create_folder')
            send_message(chat_id, "📁 Введите название папки (макс. 50 символов):", kb_back_cancel())
            return True
    
    # Create folder
    if state == 'accounts:create_folder':
        name = text.strip()
        if len(name) > 50:
            send_message(chat_id, "❌ Максимум 50 символов", kb_back_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите название:", kb_back_cancel())
            return True
        
        folder = DB.create_account_folder(user_id, name)
        if folder:
            send_message(chat_id, f"✅ Папка «{name}» создана!", kb_accounts_menu())
        else:
            send_message(chat_id, "❌ Ошибка создания", kb_accounts_menu())
        show_accounts_menu(chat_id, user_id)
        return True
    
    # Add account - phone
    if state == 'accounts:add_phone':
        phone = re.sub(r'[\s\-\(\)]', '', text)
        if not re.match(r'^\+[1-9]\d{10,14}$', phone):
            send_message(chat_id,
                "❌ Неверный формат.\n\n"
                "Пример: <code>+79001234567</code>",
                kb_back_cancel()
            )
            return True
        
        if DB.check_account_exists(user_id, phone):
            send_message(chat_id, "❌ Этот номер уже добавлен", kb_back_cancel())
            return True
        
        folder_id = saved.get('folder_id')
        task = DB.create_auth_task(user_id, phone, folder_id=folder_id)
        
        if task:
            saved['task_id'] = task['id']
            saved['phone'] = phone
            DB.set_user_state(user_id, 'accounts:add_code', saved)
            
            masked = f"{phone[:4]}***{phone[-2:]}"
            send_message(chat_id,
                f"📨 <b>Ожидание кода</b>\n\n"
                f"На номер <code>{masked}</code> будет отправлен код.\n"
                f"Введите код после получения:",
                kb_back_cancel()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания задачи", kb_accounts_menu())
        return True
    
    # Add account - code
    if state == 'accounts:add_code':
        code = text.strip().replace(' ', '').replace('-', '')
        if not (code.isdigit() and 4 <= len(code) <= 6):
            send_message(chat_id, "❌ Код должен содержать 4-6 цифр", kb_back_cancel())
            return True
        
        task_id = saved.get('task_id')
        if task_id:
            DB.update_auth_task(task_id, code=code, status='code_received')
        
        DB.clear_user_state(user_id)
        send_message(chat_id,
            "✅ <b>Код принят!</b>\n\n"
            "Авторизация выполняется в фоновом режиме.\n"
            "Вы получите уведомление о результате.",
            kb_accounts_menu()
        )
        return True
    
    # Add account - 2FA
    if state == 'accounts:add_2fa':
        password = text.strip()
        task_id = saved.get('task_id')
        phone = saved.get('phone', '')
        
        if not task_id:
            send_message(chat_id, "❌ Ошибка: задача не найдена", kb_accounts_menu())
            DB.clear_user_state(user_id)
            return True
        
        if len(password) < 1:
            send_message(chat_id, "❌ Введите пароль 2FA:", kb_back_cancel())
            return True
        
        DB.update_auth_task(task_id, password=password)
        DB.clear_user_state(user_id)
        
        masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
        send_message(chat_id,
            f"🔐 <b>Пароль принят!</b>\n\n"
            f"📱 Аккаунт: {masked}\n"
            f"Завершаем авторизацию...",
            kb_accounts_menu()
        )
        return True
    
    # View account state
    if state.startswith('accounts:view:'):
        account_id = int(state.split(':')[2])
        
        if text == BTN_ACC_SET_LIMIT:
            DB.set_user_state(user_id, f'accounts:set_limit:{account_id}')
            send_message(chat_id,
                "📊 <b>Дневной лимит</b>\n\n"
                "Выберите максимальное количество сообщений в день:\n\n"
                "⚠️ <b>Рекомендации:</b>\n"
                "• Новые аккаунты: 25-50\n"
                "• Прогретые: 75-100\n"
                "• Старые: 150-200",
                kb_account_limits()
            )
            return True
        
        if text == BTN_ACC_MOVE:
            show_move_account(chat_id, user_id, account_id)
            return True
        
        if text == BTN_ACC_DELETE:
            DB.set_user_state(user_id, f'accounts:delete:{account_id}')
            send_message(chat_id,
                "🗑 <b>Удалить аккаунт?</b>\n\n"
                "⚠️ Сессия будет удалена, потребуется повторная авторизация.",
                kb_confirm_delete()
            )
            return True
    
    # Set limit state
    if state.startswith('accounts:set_limit:'):
        account_id = int(state.split(':')[2])
        
        if text == BTN_CUSTOM_LIMIT:
            DB.set_user_state(user_id, f'accounts:custom_limit:{account_id}')
            send_message(chat_id, "📝 Введите лимит (от 1 до 500):", kb_back_cancel())
            return True
        
        if text == BTN_BACK:
            show_account_view(chat_id, user_id, account_id)
            return True
        
        try:
            limit = int(text)
            if limit not in [25, 50, 75, 100, 150, 200]:
                raise ValueError()
        except:
            send_message(chat_id, "❌ Выберите лимит из предложенных или «📝 Свой лимит»", kb_account_limits())
            return True
        
        DB.update_account(account_id, daily_limit=limit)
        send_message(chat_id, f"✅ Лимит установлен: <b>{limit}</b> сообщений/день", kb_account_actions())
        show_account_view(chat_id, user_id, account_id)
        return True
    
    # Custom limit state
    if state.startswith('accounts:custom_limit:'):
        account_id = int(state.split(':')[2])
        
        try:
            limit = int(text)
            if limit < 1 or limit > 500:
                raise ValueError()
        except:
            send_message(chat_id, "❌ Введите число от 1 до 500:", kb_back_cancel())
            return True
        
        DB.update_account(account_id, daily_limit=limit)
        send_message(chat_id, f"✅ Лимит установлен: <b>{limit}</b> сообщений/день", kb_account_actions())
        show_account_view(chat_id, user_id, account_id)
        return True
    
    # Delete account confirm
    if state.startswith('accounts:delete:'):
        account_id = int(state.split(':')[2])
        
        if text == BTN_CONFIRM_DELETE:
            DB.delete_account(account_id)
            send_message(chat_id, "✅ Аккаунт удалён", kb_accounts_menu())
            show_account_list(chat_id, user_id)
            return True
        
        if text == BTN_CANCEL:
            show_account_view(chat_id, user_id, account_id)
            return True
    
    # Folder view state
    if state.startswith('accounts:folder:'):
        folder_id = int(state.split(':')[2])
        
        if text == BTN_FOLDER_ACCOUNTS:
            show_folder_accounts(chat_id, user_id, folder_id)
            return True
        
        if text == BTN_FOLDER_ADD_ACC:
            start_add_account(chat_id, user_id, folder_id)
            return True
        
        if text == BTN_FOLDER_RENAME:
            DB.set_user_state(user_id, f'accounts:rename_folder:{folder_id}')
            send_message(chat_id, "✏️ Введите новое название папки:", kb_back_cancel())
            return True
        
        if text == BTN_FOLDER_DELETE:
            DB.set_user_state(user_id, f'accounts:delete_folder:{folder_id}')
            send_message(chat_id,
                "🗑 <b>Удалить папку?</b>\n\n"
                "⚠️ Аккаунты будут перемещены в корень.",
                kb_confirm_delete()
            )
            return True
    
    # Rename folder
    if state.startswith('accounts:rename_folder:'):
        folder_id = int(state.split(':')[2])
        name = text.strip()
        
        if len(name) > 50:
            send_message(chat_id, "❌ Максимум 50 символов", kb_back_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите название:", kb_back_cancel())
            return True
        
        DB.rename_account_folder(folder_id, name)
        send_message(chat_id, f"✅ Папка переименована в «{name}»", kb_acc_folder_actions())
        show_folder_view(chat_id, user_id, folder_id)
        return True
    
    # Delete folder confirm
    if state.startswith('accounts:delete_folder:'):
        folder_id = int(state.split(':')[2])
        
        if text == BTN_CONFIRM_DELETE:
            DB.move_accounts_from_folder(folder_id)
            DB.delete_account_folder(folder_id)
            send_message(chat_id, "✅ Папка удалена", kb_accounts_menu())
            show_account_list(chat_id, user_id)
            return True
        
        if text == BTN_CANCEL:
            show_folder_view(chat_id, user_id, folder_id)
            return True
    
    return False


def handle_accounts_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle account inline callbacks"""
    
    # Account selection
    if data.startswith('acc:'):
        account_id = int(data.split(':')[1])
        show_account_view(chat_id, user_id, account_id)
        return True
    
    # Folder selection
    if data.startswith('afld:'):
        folder_id = int(data.split(':')[1])
        show_folder_view(chat_id, user_id, folder_id)
        return True
    
    # Move account to folder
    if data.startswith('mvacc:'):
        parts = data.split(':')
        account_id = int(parts[1])
        folder_id = int(parts[2]) if parts[2] != '0' else None
        
        DB.update_account(account_id, folder_id=folder_id)
        send_message(chat_id, "✅ Аккаунт перемещён!", kb_account_actions())
        show_account_view(chat_id, user_id, account_id)
        return True
    
    return False


def start_add_account(chat_id: int, user_id: int, folder_id: int = None):
    """Start add account flow"""
    DB.set_user_state(user_id, 'accounts:add_phone', {'folder_id': folder_id})
    
    folder_info = ""
    if folder_id:
        folder = DB.get_account_folder(folder_id)
        if folder:
            folder_info = f"\n📁 Папка: {folder['name']}"
    
    send_message(chat_id,
        f"📱 <b>Добавление аккаунта</b>{folder_info}\n\n"
        "Введите номер телефона в международном формате:\n\n"
        "Примеры:\n"
        "• <code>+79001234567</code>\n"
        "• <code>+380501234567</code>\n\n"
        "⚠️ На этот номер придёт код подтверждения",
        kb_back_cancel()
    )


def show_account_list(chat_id: int, user_id: int):
    """Show account list with folders"""
    folders = DB.get_account_folders(user_id)
    accounts = DB.get_accounts_without_folder(user_id)
    
    DB.set_user_state(user_id, 'accounts:list')
    
    if not folders and not accounts:
        send_message(chat_id,
            "👤 <b>Список аккаунтов</b>\n\n"
            "У вас пока нет аккаунтов.\n"
            "Добавьте первый аккаунт!",
            kb_accounts_menu()
        )
    else:
        kb = kb_inline_accounts(folders, accounts)
        if kb:
            send_message(chat_id, "👤 <b>Выберите аккаунт или папку:</b>", kb)
        send_message(chat_id, "👆 Выберите выше или:", kb_accounts_menu())


def show_account_view(chat_id: int, user_id: int, account_id: int):
    """Show account details"""
    account = DB.get_account(account_id)
    if not account:
        send_message(chat_id, "❌ Аккаунт не найден", kb_accounts_menu())
        return
    
    DB.set_user_state(user_id, f'accounts:view:{account_id}')
    
    status_map = {
        'active': '✅ Активен',
        'pending': '⏳ Ожидает авторизации',
        'code_sent': '📨 Код отправлен',
        'blocked': '🚫 Заблокирован',
        'flood_wait': '⏰ Flood wait',
        'error': '❌ Ошибка'
    }
    
    phone = account['phone']
    masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
    daily_sent = account.get('daily_sent', 0) or 0
    daily_limit = account.get('daily_limit', 50) or 50
    
    flood_info = ""
    if account.get('status') == 'flood_wait' and account.get('flood_wait_until'):
        try:
            flood_until = datetime.fromisoformat(account['flood_wait_until'].replace('Z', '+00:00'))
            remaining = (flood_until - datetime.utcnow()).total_seconds()
            if remaining > 0:
                mins = int(remaining // 60)
                flood_info = f"\n⏰ <b>Разблокируется через:</b> {mins} мин"
        except:
            pass
    
    folder_info = ""
    if account.get('folder_id'):
        folder = DB.get_account_folder(account['folder_id'])
        if folder:
            folder_info = f"\n📁 <b>Папка:</b> {folder['name']}"
    
    send_message(chat_id,
        f"👤 <b>Аккаунт #{account['id']}</b>\n\n"
        f"📱 Телефон: <code>{masked}</code>\n"
        f"📊 Статус: {status_map.get(account['status'], account['status'])}{flood_info}\n"
        f"📤 Сегодня: <b>{daily_sent}/{daily_limit}</b>\n"
        f"💳 Доступно: <b>{max(0, daily_limit - daily_sent)}</b>{folder_info}",
        kb_account_actions()
    )


def show_move_account(chat_id: int, user_id: int, account_id: int):
    """Show folder selection for moving account"""
    folders = DB.get_account_folders(user_id)
    
    send_message(chat_id,
        "📁 <b>Выберите папку:</b>",
        kb_inline_account_folders(folders, account_id)
    )


def show_folder_view(chat_id: int, user_id: int, folder_id: int):
    """Show folder details"""
    folder = DB.get_account_folder(folder_id)
    if not folder:
        send_message(chat_id, "❌ Папка не найдена", kb_accounts_menu())
        return
    
    accounts = DB.get_accounts_in_folder(folder_id)
    active = sum(1 for a in accounts if a.get('status') == 'active')
    flood = sum(1 for a in accounts if a.get('status') == 'flood_wait')
    
    DB.set_user_state(user_id, f'accounts:folder:{folder_id}')
    
    send_message(chat_id,
        f"📁 <b>{folder['name']}</b>\n\n"
        f"📊 Аккаунтов: <b>{len(accounts)}</b>\n"
        f"✅ Активных: <b>{active}</b>\n"
        f"⏰ Flood wait: <b>{flood}</b>",
        kb_acc_folder_actions()
    )


def show_folder_accounts(chat_id: int, user_id: int, folder_id: int):
    """Show accounts in folder"""
    accounts = DB.get_accounts_in_folder(folder_id)
    folder = DB.get_account_folder(folder_id)
    
    if not accounts:
        send_message(chat_id,
            f"📁 <b>{folder['name'] if folder else 'Папка'}</b>\n\n"
            "В этой папке пока нет аккаунтов.",
            kb_acc_folder_actions()
        )
    else:
        kb = kb_inline_acc_folders([], accounts)
        send_message(chat_id, f"📁 <b>{folder['name'] if folder else 'Папка'}:</b>", kb)
        send_message(chat_id, "👆 Выберите аккаунт выше", kb_acc_folder_actions())
