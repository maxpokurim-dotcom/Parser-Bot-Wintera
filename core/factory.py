"""
Factory Module - Account Creation and Warmup
Version 1.0

Handles:
- Manual account addition (with SMS code from user)
- Auto-creation via OnlineSim API
- Account warmup process
- Progress tracking
"""
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from core.db import DB
from core.telegram import send_message, edit_message, answer_callback
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel, kb_confirm_delete,
    kb_factory_menu, kb_factory_auto_count, kb_factory_country,
    kb_factory_warmup_days, kb_factory_task_actions, kb_warmup_menu,
    kb_account_role, kb_inline_factory_tasks, kb_inline_warmup_accounts,
    reply_keyboard, inline_keyboard
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_ADD_MANUAL = '➕ Добавить вручную'
BTN_AUTO_CREATE = '🤖 Авто-создание'
BTN_WARMUP = '🔥 Прогрев аккаунтов'
BTN_QUEUE = '📋 Очередь создания'
BTN_STATUS = '📊 Статус'
BTN_FACTORY_SETTINGS = '⚙️ Настройки фабрики'

# Country codes for OnlineSim
COUNTRIES = {
    '🇷🇺 Россия': {'code': 'ru', 'price': '~15₽'},
    '🇺🇦 Украина': {'code': 'ua', 'price': '~12₽'},
    '🇰🇿 Казахстан': {'code': 'kz', 'price': '~18₽'},
    '🇧🇾 Беларусь': {'code': 'by', 'price': '~20₽'},
    '🌍 Другая': {'code': 'other', 'price': 'varies'}
}

# Role distribution presets
ROLE_PRESETS = {
    'balanced': {'observer': 0.4, 'expert': 0.3, 'support': 0.2, 'trendsetter': 0.1},
    'passive': {'observer': 0.7, 'support': 0.2, 'expert': 0.1, 'trendsetter': 0.0},
    'active': {'expert': 0.4, 'support': 0.3, 'trendsetter': 0.2, 'observer': 0.1}
}


def show_factory_menu(chat_id: int, user_id: int):
    """Show factory main menu"""
    DB.set_user_state(user_id, 'factory:menu')
    
    # Get statistics
    accounts = DB.get_accounts(user_id)
    total = len(accounts)
    active = len([a for a in accounts if a.get('status') == 'active'])
    warming = len([a for a in accounts if a.get('warmup_status') == 'in_progress'])
    
    # Get pending tasks
    tasks = DB.get_factory_tasks(user_id)
    pending_tasks = len([t for t in tasks if t.get('status') == 'pending'])
    
    # Check OnlineSim balance
    settings = DB.get_user_settings(user_id)
    onlinesim_configured = bool(settings.get('onlinesim_api_key'))
    balance_info = ""
    if onlinesim_configured:
        balance_info = "\n💰 OnlineSim: настроен"
    else:
        balance_info = "\n⚠️ OnlineSim: не настроен"
    
    send_message(chat_id,
        f"🏭 <b>Фабрика аккаунтов</b>\n\n"
        f"Создание и прогрев Telegram-аккаунтов\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"├ Всего аккаунтов: <b>{total}</b>\n"
        f"├ Активных: <b>{active}</b>\n"
        f"├ На прогреве: <b>{warming}</b>\n"
        f"└ Задач в очереди: <b>{pending_tasks}</b>"
        f"{balance_info}",
        kb_factory_menu()
    )


def handle_factory(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle factory states. Returns True if handled."""
    
    # Navigation
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Действие отменено")
        return True
    
    if text == BTN_MAIN_MENU or text == '◀️ Главное меню':
        show_main_menu(chat_id, user_id)
        return True
    
    if text == BTN_BACK or text == '◀️ Назад':
        _handle_back(chat_id, user_id, state, saved)
        return True
    
    # Menu state
    if state == 'factory:menu':
        return _handle_menu(chat_id, user_id, text)
    
    # Manual addition flow
    if state == 'factory:manual:phone':
        return _handle_manual_phone(chat_id, user_id, text, saved)
    
    if state == 'factory:manual:code':
        return _handle_manual_code(chat_id, user_id, text, saved)
    
    if state == 'factory:manual:2fa':
        return _handle_manual_2fa(chat_id, user_id, text, saved)
    
    if state == 'factory:manual:role':
        return _handle_manual_role(chat_id, user_id, text, saved)
    
    # Auto-creation flow
    if state == 'factory:auto:count':
        return _handle_auto_count(chat_id, user_id, text, saved)
    
    if state == 'factory:auto:country':
        return _handle_auto_country(chat_id, user_id, text, saved)
    
    if state == 'factory:auto:warmup':
        return _handle_auto_warmup(chat_id, user_id, text, saved)
    
    if state == 'factory:auto:roles':
        return _handle_auto_roles(chat_id, user_id, text, saved)
    
    if state == 'factory:auto:confirm':
        return _handle_auto_confirm(chat_id, user_id, text, saved)
    
    # Warmup management
    if state == 'factory:warmup':
        return _handle_warmup_menu(chat_id, user_id, text)
    
    if state.startswith('factory:warmup:settings'):
        return _handle_warmup_settings(chat_id, user_id, text, saved)
    
    # Task view
    if state.startswith('factory:task:'):
        return _handle_task_view(chat_id, user_id, text, state, saved)
    
    # Factory settings
    if state == 'factory:settings':
        return _handle_factory_settings(chat_id, user_id, text, saved)
    
    if state.startswith('factory:settings:'):
        return _handle_factory_settings_item(chat_id, user_id, text, state, saved)
    
    return False


def _handle_back(chat_id: int, user_id: int, state: str, saved: dict):
    """Handle back navigation"""
    if state in ['factory:menu', 'factory:manual:phone', 'factory:auto:count']:
        show_main_menu(chat_id, user_id)
    elif state.startswith('factory:manual:') or state.startswith('factory:auto:'):
        show_factory_menu(chat_id, user_id)
    elif state.startswith('factory:task:') or state.startswith('factory:warmup'):
        show_factory_menu(chat_id, user_id)
    else:
        show_factory_menu(chat_id, user_id)


def _handle_menu(chat_id: int, user_id: int, text: str) -> bool:
    """Handle main menu selection"""
    if text == BTN_ADD_MANUAL or text == '➕ Добавить вручную':
        start_manual_addition(chat_id, user_id)
        return True
    
    if text == BTN_AUTO_CREATE or text == '🤖 Авто-создание':
        start_auto_creation(chat_id, user_id)
        return True
    
    if text == BTN_WARMUP or text == '🔥 Прогрев аккаунтов':
        show_warmup_menu(chat_id, user_id)
        return True
    
    if text == BTN_QUEUE or text == '📋 Очередь создания':
        show_task_queue(chat_id, user_id)
        return True
    
    if text == BTN_STATUS or text == '📊 Статус':
        show_accounts_status(chat_id, user_id)
        return True
    
    if text == BTN_FACTORY_SETTINGS or text == '⚙️ Настройки фабрики':
        show_factory_settings(chat_id, user_id)
        return True
    
    return False


# ==================== MANUAL ADDITION ====================

def start_manual_addition(chat_id: int, user_id: int):
    """Start manual account addition"""
    DB.set_user_state(user_id, 'factory:manual:phone', {})
    
    send_message(chat_id,
        "➕ <b>Добавление аккаунта вручную</b>\n\n"
        "<b>Шаг 1/4:</b> Введите номер телефона\n\n"
        "Формат: <code>+79001234567</code>\n\n"
        "⚠️ На этот номер будет отправлен код подтверждения от Telegram",
        kb_back_cancel()
    )


def _handle_manual_phone(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle phone number input"""
    phone = re.sub(r'[\s\-\(\)]', '', text)
    
    if not re.match(r'^\+[1-9]\d{10,14}$', phone):
        send_message(chat_id,
            "❌ Неверный формат номера\n\n"
            "Введите в международном формате:\n"
            "<code>+79001234567</code>",
            kb_back_cancel()
        )
        return True
    
    # Check if already exists
    if DB.check_account_exists(user_id, phone):
        send_message(chat_id,
            "❌ Этот номер уже добавлен\n\n"
            "Введите другой номер:",
            kb_back_cancel()
        )
        return True
    
    # Create auth task
    task = DB.create_auth_task(user_id, phone)
    if not task:
        send_message(chat_id, "❌ Ошибка создания задачи", kb_factory_menu())
        return True
    
    saved['task_id'] = task['id']
    saved['phone'] = phone
    DB.set_user_state(user_id, 'factory:manual:code', saved)
    
    masked = f"{phone[:4]}***{phone[-2:]}"
    
    send_message(chat_id,
        f"📱 <b>Номер принят</b>\n\n"
        f"Телефон: <code>{masked}</code>\n\n"
        f"<b>Шаг 2/4:</b> Ожидание кода\n\n"
        f"⏳ Воркер отправит запрос на авторизацию.\n"
        f"Введите код из SMS/Telegram, когда получите:",
        kb_back_cancel()
    )
    return True


def _handle_manual_code(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle SMS code input"""
    code = text.strip().replace(' ', '').replace('-', '')
    
    if not (code.isdigit() and 4 <= len(code) <= 6):
        send_message(chat_id,
            "❌ Код должен содержать 4-6 цифр\n\n"
            "Введите код из SMS:",
            kb_back_cancel()
        )
        return True
    
    task_id = saved.get('task_id')
    if task_id:
        DB.update_auth_task(task_id, code=code, status='code_received')
    
    saved['code'] = code
    DB.set_user_state(user_id, 'factory:manual:2fa', saved)
    
    send_message(chat_id,
        f"✅ <b>Код принят</b>\n\n"
        f"<b>Шаг 3/4:</b> Двухфакторная аутентификация\n\n"
        f"Если на аккаунте установлен пароль 2FA, введите его.\n"
        f"Если нет — нажмите «⏭ Пропустить»",
        kb_skip_2fa()
    )
    return True


def _handle_manual_2fa(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle 2FA password"""
    if text == '⏭ Пропустить' or text == '⏭ Пропустить':
        saved['password'] = None
    else:
        saved['password'] = text.strip()
        task_id = saved.get('task_id')
        if task_id:
            DB.update_auth_task(task_id, password=saved['password'])
    
    DB.set_user_state(user_id, 'factory:manual:role', saved)
    
    send_message(chat_id,
        f"<b>Шаг 4/4:</b> Выберите роль аккаунта\n\n"
        f"Роль определяет поведение в Ботоводе:\n\n"
        f"📖 <b>Наблюдатель</b> — только чтение и редкие 👍\n"
        f"🧠 <b>Эксперт</b> — вопросы и экспертные комментарии\n"
        f"💪 <b>Поддержка</b> — лайки и короткие согласия\n"
        f"🔥 <b>Трендсеттер</b> — первые реакции на посты",
        kb_account_role()
    )
    return True


def _handle_manual_role(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle role selection"""
    role_map = {
        '📖 Наблюдатель': 'observer',
        '🧠 Эксперт': 'expert',
        '💪 Поддержка': 'support',
        '🔥 Трендсеттер': 'trendsetter',
        '🎲 Случайная роль': 'random'
    }
    
    role = role_map.get(text)
    if not role:
        send_message(chat_id, "❌ Выберите роль из списка", kb_account_role())
        return True
    
    if role == 'random':
        import random
        role = random.choice(['observer', 'expert', 'support', 'trendsetter'])
    
    saved['role'] = role
    
    # Create account record
    account = DB.create_account(
        user_id=user_id,
        phone=saved['phone'],
        role=role,
        source='manual'
    )
    
    if account:
        # Update auth task with account_id
        task_id = saved.get('task_id')
        if task_id:
            DB.update_auth_task(task_id, account_id=account['id'])
        
        # Create default profile
        DB.create_account_profile(account['id'], {
            'persona': 'Пользователь Telegram',
            'role': role,
            'interests': ['общение', 'новости'],
            'speech_style': 'informal',
            'preferred_reactions': ['👍', '❤️']
        })
        
        role_name = {'observer': 'Наблюдатель', 'expert': 'Эксперт', 
                     'support': 'Поддержка', 'trendsetter': 'Трендсеттер'}.get(role, role)
        
        send_message(chat_id,
            f"✅ <b>Аккаунт добавлен!</b>\n\n"
            f"📱 Телефон: <code>{saved['phone'][:4]}***{saved['phone'][-2:]}</code>\n"
            f"🎭 Роль: {role_name}\n"
            f"📊 Статус: ⏳ Ожидает авторизации\n\n"
            f"Авторизация выполняется в фоновом режиме.\n"
            f"Вы получите уведомление о результате.",
            kb_factory_menu()
        )
    else:
        send_message(chat_id, "❌ Ошибка создания аккаунта", kb_factory_menu())
    
    DB.set_user_state(user_id, 'factory:menu')
    return True


# ==================== AUTO CREATION ====================

def start_auto_creation(chat_id: int, user_id: int):
    """Start automatic account creation"""
    settings = DB.get_user_settings(user_id)
    
    if not settings.get('onlinesim_api_key'):
        send_message(chat_id,
            "❌ <b>OnlineSim не настроен</b>\n\n"
            "Для автоматического создания аккаунтов нужен API ключ OnlineSim.\n\n"
            "Настройте его в разделе:\n"
            "⚙️ Настройки → 🔑 API ключи → OnlineSim\n\n"
            "Или используйте ручное добавление.",
            kb_factory_menu()
        )
        return
    
    DB.set_user_state(user_id, 'factory:auto:count', {})
    
    send_message(chat_id,
        "🤖 <b>Автоматическое создание аккаунтов</b>\n\n"
        "<b>Шаг 1/5:</b> Количество аккаунтов\n\n"
        "Сколько аккаунтов создать?\n\n"
        "⚠️ Стоимость ~15₽ за номер (зависит от страны)",
        kb_factory_auto_count()
    )


def _handle_auto_count(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle count selection"""
    if text == '📝 Своё количество':
        send_message(chat_id,
            "Введите количество (от 1 до 100):",
            kb_back_cancel()
        )
        saved['custom_count'] = True
        DB.set_user_state(user_id, 'factory:auto:count', saved)
        return True
    
    if saved.get('custom_count'):
        try:
            count = int(text)
            if count < 1 or count > 100:
                raise ValueError()
        except:
            send_message(chat_id, "❌ Введите число от 1 до 100", kb_back_cancel())
            return True
        saved.pop('custom_count', None)
    else:
        try:
            count = int(text)
        except:
            send_message(chat_id, "❌ Выберите количество", kb_factory_auto_count())
            return True
    
    saved['count'] = count
    DB.set_user_state(user_id, 'factory:auto:country', saved)
    
    send_message(chat_id,
        f"✅ Количество: <b>{count}</b>\n\n"
        f"<b>Шаг 2/5:</b> Страна номера\n\n"
        f"Выберите страну для получения номеров:",
        kb_factory_country()
    )
    return True


def _handle_auto_country(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle country selection"""
    country_data = COUNTRIES.get(text)
    
    if not country_data:
        send_message(chat_id, "❌ Выберите страну из списка", kb_factory_country())
        return True
    
    if country_data['code'] == 'other':
        send_message(chat_id,
            "Введите код страны (2 буквы, например: pl, de, tr):",
            kb_back_cancel()
        )
        saved['custom_country'] = True
        DB.set_user_state(user_id, 'factory:auto:country', saved)
        return True
    
    if saved.get('custom_country'):
        saved['country'] = text.strip().lower()[:2]
        saved.pop('custom_country', None)
    else:
        saved['country'] = country_data['code']
    
    saved['country_name'] = text
    DB.set_user_state(user_id, 'factory:auto:warmup', saved)
    
    send_message(chat_id,
        f"✅ Страна: <b>{text}</b>\n\n"
        f"<b>Шаг 3/5:</b> Прогрев аккаунтов\n\n"
        f"Автоматически прогревать после создания?\n\n"
        f"Прогрев повышает надёжность и снижает риск бана.",
        kb_factory_warmup_days()
    )
    return True


def _handle_auto_warmup(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle warmup selection"""
    warmup_map = {
        '3 дня': 3,
        '5 дней': 5,
        '7 дней': 7,
        '14 дней': 14,
        '🚫 Без прогрева': 0
    }
    
    warmup_days = warmup_map.get(text)
    if warmup_days is None:
        send_message(chat_id, "❌ Выберите из списка", kb_factory_warmup_days())
        return True
    
    saved['warmup_days'] = warmup_days
    saved['auto_warmup'] = warmup_days > 0
    
    DB.set_user_state(user_id, 'factory:auto:roles', saved)
    
    send_message(chat_id,
        f"✅ Прогрев: <b>{text}</b>\n\n"
        f"<b>Шаг 4/5:</b> Распределение ролей\n\n"
        f"Как распределить роли между аккаунтами?\n\n"
        f"📊 <b>Сбалансированно</b>\n"
        f"   40% наблюдатели, 30% эксперты, 20% поддержка, 10% трендсеттеры\n\n"
        f"📖 <b>Пассивно</b>\n"
        f"   70% наблюдатели, 20% поддержка, 10% эксперты\n\n"
        f"🔥 <b>Активно</b>\n"
        f"   40% эксперты, 30% поддержка, 20% трендсеттеры, 10% наблюдатели",
        kb_role_distribution()
    )
    return True


def _handle_auto_roles(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle role distribution"""
    preset_map = {
        '📊 Сбалансированно': 'balanced',
        '📖 Пассивно': 'passive',
        '🔥 Активно': 'active'
    }
    
    preset = preset_map.get(text)
    if not preset:
        send_message(chat_id, "❌ Выберите из списка", kb_role_distribution())
        return True
    
    saved['role_distribution'] = ROLE_PRESETS[preset]
    saved['role_preset'] = text
    
    DB.set_user_state(user_id, 'factory:auto:confirm', saved)
    _show_auto_confirmation(chat_id, user_id, saved)
    return True


def _show_auto_confirmation(chat_id: int, user_id: int, saved: dict):
    """Show auto-creation confirmation"""
    cost_estimate = saved['count'] * 15  # Rough estimate
    
    roles = saved.get('role_distribution', ROLE_PRESETS['balanced'])
    roles_text = '\n'.join([
        f"   {int(v*100)}% {{'observer': 'наблюдатели', 'expert': 'эксперты', 'support': 'поддержка', 'trendsetter': 'трендсеттеры'}.get(k, k)}"
        for k, v in roles.items() if v > 0
    ])
    
    warmup_text = f"{saved['warmup_days']} дней" if saved['warmup_days'] > 0 else "отключён"
    
    send_message(chat_id,
        f"📋 <b>Подтверждение создания</b>\n\n"
        f"📊 Количество: <b>{saved['count']}</b>\n"
        f"🌍 Страна: <b>{saved.get('country_name', saved['country'])}</b>\n"
        f"🔥 Прогрев: <b>{warmup_text}</b>\n"
        f"🎭 Роли: <b>{saved.get('role_preset', 'Сбалансированно')}</b>\n"
        f"{roles_text}\n\n"
        f"💰 <b>Примерная стоимость: ~{cost_estimate}₽</b>\n\n"
        f"⚠️ Создание может занять {saved['count'] * 2}-{saved['count'] * 5} минут",
        kb_confirm_factory()
    )


def _handle_auto_confirm(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle auto-creation confirmation"""
    if text == '✅ Подтвердить' or text == '🚀 Запустить':
        # Create factory task
        task = DB.create_factory_task(
            user_id=user_id,
            count=saved['count'],
            country=saved['country'],
            auto_warmup=saved.get('auto_warmup', True),
            warmup_days=saved.get('warmup_days', 5),
            role_distribution=saved.get('role_distribution', ROLE_PRESETS['balanced'])
        )
        
        if task:
            send_message(chat_id,
                f"✅ <b>Задача создана!</b>\n\n"
                f"🆔 ID: #{task['id']}\n"
                f"📊 Статус: ⏳ В очереди\n\n"
                f"Воркер начнёт создание аккаунтов.\n"
                f"Вы получите уведомления о прогрессе.",
                kb_factory_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания задачи", kb_factory_menu())
        
        DB.set_user_state(user_id, 'factory:menu')
        return True
    
    if text == '❌ Отмена':
        show_factory_menu(chat_id, user_id)
        return True
    
    return True


# ==================== WARMUP MANAGEMENT ====================

def show_warmup_menu(chat_id: int, user_id: int):
    """Show warmup management menu"""
    DB.set_user_state(user_id, 'factory:warmup')
    
    # Get warmup stats
    stats = DB.get_warmup_stats(user_id)
    
    send_message(chat_id,
        f"🔥 <b>Прогрев аккаунтов</b>\n\n"
        f"Прогрев повышает доверие Telegram к аккаунту\n"
        f"и снижает риск блокировки.\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"├ В процессе: <b>{stats['in_progress']}</b>\n"
        f"├ Завершено: <b>{stats['completed']}</b>\n"
        f"└ Ожидают: <b>{stats['pending']}</b>\n\n"
        f"<b>Этапы прогрева:</b>\n"
        f"День 1-2: Заполнение профиля, подписки\n"
        f"День 3-5: Чтение, редкие реакции\n"
        f"День 6-7: Больше активности\n"
        f"День 8+: Полная готовность",
        kb_warmup_menu()
    )


def _handle_warmup_menu(chat_id: int, user_id: int, text: str) -> bool:
    """Handle warmup menu"""
    if text == '📊 Статус прогрева':
        show_warmup_status(chat_id, user_id)
        return True
    
    if text == '▶️ Запустить для всех':
        start_warmup_for_all(chat_id, user_id)
        return True
    
    if text == '⏸ Приостановить':
        pause_all_warmup(chat_id, user_id)
        return True
    
    if text == '⚙️ Настройки прогрева':
        show_warmup_settings(chat_id, user_id)
        return True
    
    return False


def show_warmup_status(chat_id: int, user_id: int):
    """Show warmup status for all accounts"""
    accounts = DB.get_accounts(user_id)
    
    # Group by warmup status
    warming = []
    completed = []
    pending = []
    
    for acc in accounts:
        progress = DB.get_warmup_progress(acc['id'])
        if progress:
            if progress['status'] == 'in_progress':
                warming.append({'account': acc, 'progress': progress})
            elif progress['status'] == 'completed':
                completed.append(acc)
            else:
                pending.append(acc)
        else:
            pending.append(acc)
    
    text = f"🔥 <b>Статус прогрева</b>\n\n"
    
    if warming:
        text += f"<b>🔄 В процессе ({len(warming)}):</b>\n"
        for item in warming[:10]:
            acc = item['account']
            prog = item['progress']
            phone = acc['phone']
            masked = f"{phone[:4]}**{phone[-2:]}" if len(phone) > 6 else phone
            day = prog.get('current_day', 1)
            total = prog.get('total_days', 5)
            bar = '█' * day + '░' * (total - day)
            text += f"  {masked} [{bar}] день {day}/{total}\n"
        text += "\n"
    
    if completed:
        text += f"<b>✅ Завершено ({len(completed)}):</b> готовы к работе\n\n"
    
    if pending:
        text += f"<b>⏳ Ожидают ({len(pending)}):</b> не начат\n"
    
    kb = kb_inline_warmup_accounts(warming[:15] if warming else accounts[:15])
    send_message(chat_id, text, kb)
    send_message(chat_id, "Выберите аккаунт для деталей:", kb_warmup_menu())


def start_warmup_for_all(chat_id: int, user_id: int):
    """Start warmup for all accounts without it"""
    accounts = DB.get_accounts(user_id)
    started = 0
    
    settings = DB.get_user_settings(user_id)
    warmup_days = settings.get('factory_settings', {}).get('default_warmup_days', 5)
    
    for acc in accounts:
        if acc.get('status') != 'active':
            continue
        
        progress = DB.get_warmup_progress(acc['id'])
        if not progress or progress.get('status') not in ['in_progress', 'completed']:
            DB.create_warmup_progress(acc['id'], warmup_days)
            DB.update_account(acc['id'], warmup_status='in_progress')
            started += 1
    
    send_message(chat_id,
        f"✅ <b>Прогрев запущен</b>\n\n"
        f"Аккаунтов в прогреве: <b>{started}</b>\n"
        f"Длительность: <b>{warmup_days} дней</b>",
        kb_warmup_menu()
    )


def pause_all_warmup(chat_id: int, user_id: int):
    """Pause all warmup"""
    accounts = DB.get_accounts(user_id)
    paused = 0
    
    for acc in accounts:
        progress = DB.get_warmup_progress(acc['id'])
        if progress and progress.get('status') == 'in_progress':
            DB.update_warmup_progress(acc['id'], status='paused')
            paused += 1
    
    send_message(chat_id,
        f"⏸ <b>Прогрев приостановлен</b>\n\n"
        f"Аккаунтов: <b>{paused}</b>",
        kb_warmup_menu()
    )


def show_warmup_settings(chat_id: int, user_id: int):
    """Show warmup settings"""
    DB.set_user_state(user_id, 'factory:warmup:settings', {})
    
    settings = DB.get_user_settings(user_id)
    factory = settings.get('factory_settings', {})
    
    warmup_days = factory.get('default_warmup_days', 5)
    
    send_message(chat_id,
        f"⚙️ <b>Настройки прогрева</b>\n\n"
        f"📅 Длительность по умолчанию: <b>{warmup_days} дней</b>\n\n"
        f"<b>Этапы прогрева:</b>\n"
        f"• День 1-2: Настройка профиля\n"
        f"• День 3-5: Пассивная активность\n"
        f"• День 6+: Полная активность",
        reply_keyboard([
            ['3 дня', '5 дней', '7 дней'],
            ['14 дней'],
            ['◀️ Назад']
        ])
    )


def _handle_warmup_settings(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle warmup settings"""
    days_map = {'3 дня': 3, '5 дней': 5, '7 дней': 7, '14 дней': 14}
    
    if text in days_map:
        settings = DB.get_user_settings(user_id)
        factory = settings.get('factory_settings', {})
        factory['default_warmup_days'] = days_map[text]
        DB.update_user_settings(user_id, factory_settings=factory)
        
        send_message(chat_id, f"✅ Длительность прогрева: {text}", kb_warmup_menu())
        show_warmup_menu(chat_id, user_id)
        return True
    
    return False


# ==================== TASK QUEUE ====================

def show_task_queue(chat_id: int, user_id: int):
    """Show task queue"""
    tasks = DB.get_factory_tasks(user_id)
    
    if not tasks:
        send_message(chat_id,
            "📋 <b>Очередь создания</b>\n\n"
            "Нет задач.\n\n"
            "Создайте через «🤖 Авто-создание»",
            kb_factory_menu()
        )
        return
    
    text = f"📋 <b>Очередь создания ({len(tasks)}):</b>\n\n"
    
    for t in tasks[:10]:
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'failed': '❌'
        }.get(t['status'], '❓')
        
        created = t.get('created_count', 0)
        total = t.get('count', 0)
        
        text += f"{status_emoji} #{t['id']} — {created}/{total} создано\n"
    
    kb = kb_inline_factory_tasks(tasks)
    send_message(chat_id, text, kb)
    send_message(chat_id, "Выберите задачу для деталей:", kb_factory_menu())


def _handle_task_view(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle task view actions"""
    task_id = int(state.split(':')[2])
    
    if text == '🔄 Обновить статус':
        show_task_details(chat_id, user_id, task_id)
        return True
    
    if text == '🛑 Отменить':
        DB.update_factory_task(task_id, status='cancelled')
        send_message(chat_id, "✅ Задача отменена", kb_factory_menu())
        show_task_queue(chat_id, user_id)
        return True
    
    if text == '🗑 Удалить':
        DB.delete_factory_task(task_id)
        send_message(chat_id, "✅ Задача удалена", kb_factory_menu())
        show_task_queue(chat_id, user_id)
        return True
    
    return False


def show_task_details(chat_id: int, user_id: int, task_id: int):
    """Show task details"""
    task = DB.get_factory_task(task_id)
    if not task:
        send_message(chat_id, "❌ Задача не найдена", kb_factory_menu())
        return
    
    DB.set_user_state(user_id, f'factory:task:{task_id}')
    
    status_text = {
        'pending': '⏳ В очереди',
        'in_progress': '🔄 Выполняется',
        'completed': '✅ Завершена',
        'failed': '❌ Ошибка',
        'cancelled': '🚫 Отменена'
    }.get(task['status'], task['status'])
    
    created = task.get('created_count', 0)
    failed = task.get('failed_count', 0)
    total = task.get('count', 0)
    
    errors_text = ""
    if task.get('errors'):
        errors_text = f"\n\n⚠️ <b>Ошибки:</b>\n" + '\n'.join(task['errors'][:5])
    
    send_message(chat_id,
        f"📋 <b>Задача #{task_id}</b>\n\n"
        f"📊 Статус: {status_text}\n"
        f"🌍 Страна: {task.get('country', 'ru')}\n"
        f"🔥 Прогрев: {'да' if task.get('auto_warmup') else 'нет'}\n\n"
        f"<b>Прогресс:</b>\n"
        f"├ Создано: {created}/{total}\n"
        f"└ Ошибок: {failed}"
        f"{errors_text}",
        kb_factory_task_actions()
    )


# ==================== ACCOUNTS STATUS ====================

def show_accounts_status(chat_id: int, user_id: int):
    """Show accounts status overview"""
    accounts = DB.get_accounts(user_id)
    
    # Group by status
    by_status = {}
    for acc in accounts:
        status = acc.get('status', 'unknown')
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(acc)
    
    # Group by source
    manual = len([a for a in accounts if a.get('source') == 'manual'])
    auto = len([a for a in accounts if a.get('source') == 'auto_factory'])
    
    # Warmup stats
    warming = len([a for a in accounts if a.get('warmup_status') == 'in_progress'])
    warmed = len([a for a in accounts if a.get('warmup_status') == 'completed'])
    
    text = f"📊 <b>Статус аккаунтов</b>\n\n"
    
    text += f"<b>По статусу:</b>\n"
    status_names = {
        'active': '✅ Активные',
        'pending': '⏳ Ожидают авторизации',
        'flood_wait': '⏰ FloodWait',
        'blocked': '🚫 Заблокированы',
        'error': '❌ Ошибка'
    }
    for status, name in status_names.items():
        count = len(by_status.get(status, []))
        if count > 0:
            text += f"├ {name}: <b>{count}</b>\n"
    
    text += f"\n<b>По источнику:</b>\n"
    text += f"├ Добавлены вручную: <b>{manual}</b>\n"
    text += f"└ Авто-создание: <b>{auto}</b>\n"
    
    text += f"\n<b>Прогрев:</b>\n"
    text += f"├ В процессе: <b>{warming}</b>\n"
    text += f"└ Завершён: <b>{warmed}</b>"
    
    send_message(chat_id, text, kb_factory_menu())


# ==================== FACTORY SETTINGS ====================

def show_factory_settings(chat_id: int, user_id: int):
    """Show factory settings"""
    DB.set_user_state(user_id, 'factory:settings', {})
    
    settings = DB.get_user_settings(user_id)
    factory = settings.get('factory_settings', {})
    
    warmup_days = factory.get('default_warmup_days', 5)
    auto_proxy = '✅' if factory.get('auto_proxy_assignment', True) else '❌'
    
    onlinesim_key = settings.get('onlinesim_api_key')
    onlinesim_status = '✅ Настроен' if onlinesim_key else '❌ Не настроен'
    
    send_message(chat_id,
        f"⚙️ <b>Настройки фабрики</b>\n\n"
        f"📅 Прогрев по умолчанию: <b>{warmup_days} дней</b>\n"
        f"🌐 Авто-назначение прокси: {auto_proxy}\n\n"
        f"<b>API:</b>\n"
        f"📱 OnlineSim: {onlinesim_status}",
        reply_keyboard([
            ['📅 Длительность прогрева'],
            ['🌐 Авто-прокси'],
            ['📱 Настроить OnlineSim'],
            ['◀️ Назад']
        ])
    )


def _handle_factory_settings(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle factory settings"""
    if text == '📅 Длительность прогрева':
        show_warmup_settings(chat_id, user_id)
        return True
    
    if text == '🌐 Авто-прокси':
        settings = DB.get_user_settings(user_id)
        factory = settings.get('factory_settings', {})
        factory['auto_proxy_assignment'] = not factory.get('auto_proxy_assignment', True)
        DB.update_user_settings(user_id, factory_settings=factory)
        
        status = '✅ включено' if factory['auto_proxy_assignment'] else '❌ отключено'
        send_message(chat_id, f"Авто-назначение прокси: {status}", kb_factory_menu())
        show_factory_settings(chat_id, user_id)
        return True
    
    if text == '📱 Настроить OnlineSim':
        DB.set_user_state(user_id, 'factory:settings:onlinesim', {})
        send_message(chat_id,
            "📱 <b>Настройка OnlineSim</b>\n\n"
            "Введите API ключ от onlinesim.io:\n\n"
            "Получить ключ: https://onlinesim.io/api\n\n"
            "⚠️ Ключ будет сохранён безопасно",
            kb_back_cancel()
        )
        return True
    
    return False


def _handle_factory_settings_item(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle specific factory settings"""
    if state == 'factory:settings:onlinesim':
        api_key = text.strip()
        
        if len(api_key) < 10:
            send_message(chat_id, "❌ Неверный формат ключа", kb_back_cancel())
            return True
        
        DB.update_user_settings(user_id, onlinesim_api_key=api_key)
        send_message(chat_id, "✅ API ключ OnlineSim сохранён!", kb_factory_menu())
        show_factory_settings(chat_id, user_id)
        return True
    
    return False


# ==================== CALLBACKS ====================

def handle_factory_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle factory inline callbacks"""
    
    # Task selection
    if data.startswith('ftask:'):
        task_id = int(data.split(':')[1])
        show_task_details(chat_id, user_id, task_id)
        return True
    
    # Warmup account selection
    if data.startswith('fwarm:'):
        account_id = int(data.split(':')[1])
        show_account_warmup_details(chat_id, user_id, account_id)
        return True
    
    return False


def show_account_warmup_details(chat_id: int, user_id: int, account_id: int):
    """Show warmup details for specific account"""
    account = DB.get_account(account_id)
    if not account:
        send_message(chat_id, "❌ Аккаунт не найден", kb_warmup_menu())
        return
    
    progress = DB.get_warmup_progress(account_id)
    
    phone = account['phone']
    masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
    
    if progress:
        day = progress.get('current_day', 1)
        total = progress.get('total_days', 5)
        status = progress.get('status', 'unknown')
        
        status_text = {
            'in_progress': '🔄 В процессе',
            'completed': '✅ Завершён',
            'paused': '⏸ Пауза'
        }.get(status, status)
        
        # Show completed actions
        actions = progress.get('completed_actions', [])
        actions_text = ""
        if actions:
            actions_text = "\n\n<b>Выполненные действия:</b>\n"
            for a in actions[-5:]:
                actions_text += f"• День {a.get('day', '?')}: {a.get('action', '?')}\n"
        
        send_message(chat_id,
            f"🔥 <b>Прогрев аккаунта</b>\n\n"
            f"📱 Телефон: <code>{masked}</code>\n"
            f"📊 Статус: {status_text}\n"
            f"📅 День: {day}/{total}\n"
            f"{actions_text}",
            reply_keyboard([
                ['▶️ Продолжить' if status == 'paused' else '⏸ Пауза'],
                ['🔄 Перезапустить', '🛑 Остановить'],
                ['◀️ Назад']
            ])
        )
    else:
        send_message(chat_id,
            f"📱 <b>Аккаунт {masked}</b>\n\n"
            f"Прогрев не запущен.\n\n"
            f"Запустить прогрев?",
            reply_keyboard([
                ['▶️ Запустить прогрев'],
                ['◀️ Назад']
            ])
        )


# ==================== HELPER KEYBOARDS ====================

def kb_skip_2fa():
    """Skip 2FA keyboard"""
    return reply_keyboard([
        ['⏭ Пропустить'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_role_distribution():
    """Role distribution keyboard"""
    return reply_keyboard([
        ['📊 Сбалансированно'],
        ['📖 Пассивно', '🔥 Активно'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_confirm_factory():
    """Confirm factory keyboard"""
    return reply_keyboard([
        ['✅ Подтвердить'],
        ['◀️ Назад', '❌ Отмена']
    ])
