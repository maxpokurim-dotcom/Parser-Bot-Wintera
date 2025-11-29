# api/accounts.py (продолжение)
"""
Account management handlers
"""
import re
import logging
from datetime import datetime
from api.db import DB
from api.telegram import edit_message, send_message
from api.keyboards import (
    kb_main, kb_cancel, kb_accounts_main, kb_account_folder_view,
    kb_account_actions, kb_account_folder_select, kb_account_limit,
    kb_delete_confirm
)

logger = logging.getLogger(__name__)

def handle_account_cb(chat_id: int, msg_id: int, user_id: int, data: str, saved: dict):
    if data in ['menu:accounts', 'account:list']:
        folders = DB.get_account_folders(user_id)
        accounts_without_folder = DB.get_accounts_without_folder(user_id)
        total_accounts = DB.count_user_accounts(user_id)
        active_accounts = DB.count_active_user_accounts(user_id)

        if total_accounts == 0 and len(folders) == 0:
            edit_message(chat_id, msg_id,
                "👤 <b>Ваши аккаунты</b>\n"
                "У вас пока нет аккаунтов.\n"
                "Добавьте первый для рассылки!", kb_accounts_main([], []))
        else:
            edit_message(chat_id, msg_id,
                f"👤 <b>Ваши аккаунты</b>\n"
                f"📊 Всего: <b>{total_accounts}</b>\n"
                f"✅ Активных: <b>{active_accounts}</b>\n"
                f"📁 Папок: <b>{len(folders)}</b>", kb_accounts_main(folders, accounts_without_folder))

    # ===== ACCOUNT FOLDERS =====
    elif data == 'acc_folder:create':
        DB.set_user_state(user_id, 'waiting_acc_folder_name')
        edit_message(chat_id, msg_id,
            "📁 <b>Создание папки аккаунтов</b>\n"
            "Введите название папки (макс. 50 символов):", kb_cancel())

    elif data.startswith('acc_folder:view:'):
        folder_id = int(data.split(':')[2])
        folder = DB.get_account_folder(folder_id)
        if not folder:
            folders = DB.get_account_folders(user_id)
            accounts_without_folder = DB.get_accounts_without_folder(user_id)
            edit_message(chat_id, msg_id, "❌ Папка не найдена", kb_accounts_main(folders, accounts_without_folder))
            return
        accounts = DB.get_accounts_in_folder(folder_id)
        active = sum(1 for a in accounts if a.get('status') == 'active')
        flood = sum(1 for a in accounts if a.get('status') == 'flood_wait')
        
        edit_message(chat_id, msg_id,
            f"📁 <b>{folder['name']}</b>\n"
            f"📊 Аккаунтов: <b>{len(accounts)}</b>\n"
            f"✅ Активных: <b>{active}</b>\n"
            f"⏰ Flood wait: <b>{flood}</b>", kb_account_folder_view(accounts, folder_id))

    elif data.startswith('acc_folder:rename:'):
        folder_id = int(data.split(':')[2])
        DB.set_user_state(user_id, 'waiting_acc_folder_rename', {'folder_id': folder_id})
        edit_message(chat_id, msg_id,
            "✏️ <b>Переименование папки</b>\n"
            "Введите новое название:", kb_cancel())

    elif data.startswith('acc_folder:delete:'):
        folder_id = int(data.split(':')[2])
        logger.info(f"Deleting account folder {folder_id} for user {user_id}")
        DB.move_accounts_from_folder(folder_id)
        result = DB.delete_account_folder(folder_id)
        logger.info(f"Delete result: {result}")
        
        folders = DB.get_account_folders(user_id)
        accounts_without_folder = DB.get_accounts_without_folder(user_id)
        total_accounts = DB.count_user_accounts(user_id)
        active_accounts = DB.count_active_user_accounts(user_id)
        edit_message(chat_id, msg_id, 
            f"✅ Папка удалена. Аккаунты перемещены в общий список.\n\n"
            f"👤 <b>Ваши аккаунты</b>\n"
            f"📊 Всего: <b>{total_accounts}</b>\n"
            f"✅ Активных: <b>{active_accounts}</b>", 
            kb_accounts_main(folders, accounts_without_folder))

    # ===== ACCOUNT VIEW =====
    elif data.startswith('account:view:'):
        acc_id = int(data.split(':')[2])
        a = DB.get_account(acc_id)
        if not a:
            folders = DB.get_account_folders(user_id)
            accounts_without_folder = DB.get_accounts_without_folder(user_id)
            total_accounts = DB.count_user_accounts(user_id)
            active_accounts = DB.count_active_user_accounts(user_id)
            edit_message(chat_id, msg_id, 
                f"❌ Аккаунт не найден или был удалён\n\n"
                f"👤 <b>Ваши аккаунты</b>\n"
                f"📊 Всего: <b>{total_accounts}</b>\n"
                f"✅ Активных: <b>{active_accounts}</b>", 
                kb_accounts_main(folders, accounts_without_folder))
            return
        
        status_map = {
            'active': '✅ Активен',
            'pending': '⏳ Ожидает авторизации',
            'code_sent': '📨 Код отправлен',
            'blocked': '🚫 Заблокирован',
            'flood_wait': '⏰ Flood wait',
            'error': '❌ Ошибка'
        }
        phone = a['phone']
        masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
        daily_sent = a.get('daily_sent', 0) or 0
        daily_limit = a.get('daily_limit', 50) or 50
        
        flood_info = ""
        if a.get('status') == 'flood_wait' and a.get('flood_wait_until'):
            try:
                flood_until = datetime.fromisoformat(a['flood_wait_until'].replace('Z', '+00:00'))
                remaining = (flood_until - datetime.utcnow()).total_seconds()
                if remaining > 0:
                    mins = int(remaining // 60)
                    flood_info = f"\n⏰ <b>Разблокируется через:</b> {mins} мин"
            except:
                pass
        
        folder_info = ""
        if a.get('folder_id'):
            folder = DB.get_account_folder(a['folder_id'])
            if folder:
                folder_info = f"\n📁 <b>Папка:</b> {folder['name']}"
        
        edit_message(chat_id, msg_id,
            f"👤 <b>Аккаунт #{a['id']}</b>\n"
            f"📱 Телефон: <code>{masked}</code>\n"
            f"📊 Статус: {status_map.get(a['status'], a['status'])}{flood_info}\n"
            f"📤 Сегодня: <b>{daily_sent}/{daily_limit}</b>\n"
            f"💳 Доступно: <b>{max(0, daily_limit - daily_sent)}</b>{folder_info}", 
            kb_account_actions(a['id']))

    # ===== ADD ACCOUNT =====
    elif data == 'account:add':
        DB.set_user_state(user_id, 'waiting_phone', {'folder_id': None})
        edit_message(chat_id, msg_id,
            "📱 <b>Добавление аккаунта</b>\n"
            "Введите номер телефона в международном формате:\n"
            "Примеры:\n"
            "• <code>+79001234567</code>\n"
            "• <code>+380501234567</code>\n"
            "⚠️ На этот номер придёт код подтверждения", kb_cancel())

    elif data.startswith('account:add_to_folder:'):
        folder_id = int(data.split(':')[2])
        DB.set_user_state(user_id, 'waiting_phone', {'folder_id': folder_id})
        folder = DB.get_account_folder(folder_id)
        folder_name = folder['name'] if folder else 'папку'
        edit_message(chat_id, msg_id,
            f"📱 <b>Добавление аккаунта в «{folder_name}»</b>\n"
            "Введите номер телефона в международном формате:\n"
            "• <code>+79001234567</code>\n"
            "⚠️ На этот номер придёт код подтверждения", kb_cancel())

    # ===== MOVE ACCOUNT =====
    elif data.startswith('account:move:'):
        acc_id = int(data.split(':')[2])
        edit_message(chat_id, msg_id,
            "📁 <b>Переместить аккаунт</b>\nВыберите папку:",
            kb_account_folder_select(user_id, acc_id))

    elif data.startswith('account:set_folder:'):
        parts = data.split(':')
        acc_id = int(parts[2])
        folder_id = int(parts[3]) if parts[3] != '0' else None
        DB.update_account(acc_id, folder_id=folder_id)
        edit_message(chat_id, msg_id, "✅ Аккаунт перемещён!", kb_account_actions(acc_id))

    # ===== ACCOUNT LIMITS =====
    elif data.startswith('account:set_limit:'):
        acc_id = int(data.split(':')[2])
        edit_message(chat_id, msg_id,
            "📊 <b>Дневной лимит</b>\n"
            "Выберите максимальное количество сообщений в день:\n"
            "⚠️ <b>Рекомендации:</b>\n"
            "• Новые аккаунты: 25-50\n"
            "• Прогретые: 75-100\n"
            "• Старые: 150-200", kb_account_limit(acc_id))

    elif data.startswith('account:limit:'):
        parts = data.split(':')
        acc_id, limit = int(parts[2]), int(parts[3])
        DB.update_account(acc_id, daily_limit=limit)
        edit_message(chat_id, msg_id, f"✅ Лимит установлен: <b>{limit}</b> сообщений/день", kb_account_actions(acc_id))

    # ===== DELETE ACCOUNT =====
    elif data.startswith('account:delete:'):
        acc_id = int(data.split(':')[2])
        edit_message(chat_id, msg_id,
            "🗑 <b>Удалить аккаунт?</b>\n"
            "⚠️ Сессия будет удалена, потребуется повторная авторизация.", kb_delete_confirm('account', acc_id))

    elif data.startswith('account:confirm_delete:'):
        acc_id = int(data.split(':')[2])
        logger.info(f"Deleting account {acc_id} for user {user_id}")
        result = DB.delete_account(acc_id)
        logger.info(f"Delete result: {result}")
        
        # Получаем актуальный список после удаления
        folders = DB.get_account_folders(user_id)
        accounts_without_folder = DB.get_accounts_without_folder(user_id)
        total_accounts = DB.count_user_accounts(user_id)
        active_accounts = DB.count_active_user_accounts(user_id)
        edit_message(chat_id, msg_id, 
            f"✅ Аккаунт удалён\n\n"
            f"👤 <b>Ваши аккаунты</b>\n"
            f"📊 Всего: <b>{total_accounts}</b>\n"
            f"✅ Активных: <b>{active_accounts}</b>", 
            kb_accounts_main(folders, accounts_without_folder))

    elif data == 'account:cancel_delete':
        folders = DB.get_account_folders(user_id)
        accounts_without_folder = DB.get_accounts_without_folder(user_id)
        total_accounts = DB.count_user_accounts(user_id)
        active_accounts = DB.count_active_user_accounts(user_id)
        edit_message(chat_id, msg_id, 
            f"👤 <b>Ваши аккаунты</b>\n"
            f"📊 Всего: <b>{total_accounts}</b>\n"
            f"✅ Активных: <b>{active_accounts}</b>", 
            kb_accounts_main(folders, accounts_without_folder))


def handle_account_state(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Returns True if state was handled"""
    
    # ===== ACCOUNT FOLDER NAME =====
    if state == 'waiting_acc_folder_name':
        name = text.strip()
        if len(name) > 50:
            send_message(chat_id, "❌ Максимум 50 символов", kb_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите название папки:", kb_cancel())
            return True
        folder = DB.create_account_folder(user_id, name)
        DB.clear_user_state(user_id)
        if folder:
            send_message(chat_id, f"✅ Папка аккаунтов «{name}» создана!", kb_main())
        else:
            send_message(chat_id, "❌ Ошибка создания папки", kb_main())
        return True

    # ===== RENAME ACCOUNT FOLDER =====
    if state == 'waiting_acc_folder_rename':
        name = text.strip()
        if len(name) > 50:
            send_message(chat_id, "❌ Максимум 50 символов", kb_cancel())
            return True
        if len(name) < 1:
            send_message(chat_id, "❌ Введите новое название:", kb_cancel())
            return True
        folder_id = saved.get('folder_id')
        if folder_id:
            DB.rename_account_folder(folder_id, name)
        DB.clear_user_state(user_id)
        send_message(chat_id, f"✅ Папка переименована в «{name}»", kb_main())
        return True

    # ===== ACCOUNT PHONE =====
    if state == 'waiting_phone':
        phone = re.sub(r'[\s\-\(\)]', '', text)
        if not re.match(r'^\+[1-9]\d{10,14}$', phone):
            send_message(chat_id, "❌ Неверный формат. Пример: <code>+79001234567</code>", kb_cancel())
            return True
        if DB.check_account_exists(user_id, phone):
            send_message(chat_id, "❌ Этот номер уже добавлен", kb_cancel())
            return True
        folder_id = saved.get('folder_id')
        task = DB.create_auth_task(user_id, phone, folder_id=folder_id)
        if task:
            DB.set_user_state(user_id, 'waiting_code', {'task_id': task['id'], 'phone': phone, 'folder_id': folder_id})
            masked = f"{phone[:4]}***{phone[-2:]}"
            send_message(chat_id,
                f"📨 <b>Ожидание кода</b>\n"
                f"На номер <code>{masked}</code> будет отправлен код.\n"
                f"Введите код после получения:", kb_cancel())
        else:
            send_message(chat_id, "❌ Ошибка создания задачи", kb_main())
        return True

    # ===== WAITING CODE =====
    if state == 'waiting_code':
        code = text.strip().replace(' ', '').replace('-', '')
        if not (code.isdigit() and 4 <= len(code) <= 6):
            send_message(chat_id, "❌ Код должен содержать 4-6 цифр", kb_cancel())
            return True
        task_id = saved.get('task_id')
        if task_id:
            DB.update_auth_task(task_id, code=code, status='code_received')
        DB.clear_user_state(user_id)
        send_message(chat_id,
            "✅ <b>Код принят!</b>\n"
            "Авторизация выполняется в фоновом режиме.\n"
            "Вы получите уведомление о результате.", kb_main())
        return True

    # ===== WAITING 2FA =====
    if state == 'waiting_2fa':
        password = text.strip()
        task_id = saved.get('task_id')
        phone = saved.get('phone', '')
        if not task_id:
            send_message(chat_id, "❌ Ошибка: задача не найдена", kb_main())
            DB.clear_user_state(user_id)
            return True
        if len(password) < 1:
            send_message(chat_id, "❌ Введите пароль 2FA:", kb_cancel())
            return True
        DB.update_auth_task(task_id, password=password)
        DB.clear_user_state(user_id)
        masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
        send_message(chat_id,
            f"🔐 <b>Пароль принят!</b>\n"
            f"📱 Аккаунт: {masked}\n"
            f"Завершаем авторизацию...", kb_main())
        return True

    return False