"""
Mailing and campaign handlers - Extended v2.0
With warm start, adaptive delays, typing simulation, smart scheduling
"""
import logging
import re
from datetime import datetime, timedelta
from core.db import DB
from core.telegram import send_message, answer_callback
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel,
    kb_mailing_menu, kb_mailing_confirm, kb_campaign_actions,
    kb_mailing_settings, kb_scheduler_menu, kb_schedule_type, kb_schedule_repeat,
    kb_inline_mailing_sources, kb_inline_mailing_templates,
    kb_inline_mailing_acc_folders, kb_inline_campaigns, kb_inline_scheduled,
    kb_inline_scheduled_tasks
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_MAIL_NEW = '🚀 Новая рассылка'
BTN_MAIL_ACTIVE = '📊 Активные'
BTN_MAIL_SCHEDULED = '📅 Отложенные'
BTN_MAIL_SCHEDULER = '⏰ Планировщик'
BTN_MAIL_START = '🚀 Запустить сейчас'
BTN_MAIL_SCHEDULE = '📅 Отложить'
BTN_MAIL_SETTINGS = '⚙️ Настройки рассылки'
BTN_CAMPAIGN_PAUSE = '⏸ Приостановить'
BTN_CAMPAIGN_RESUME = '▶️ Возобновить'
BTN_CAMPAIGN_STOP = '🛑 Остановить'
BTN_CAMPAIGN_REFRESH = '🔄 Обновить'
BTN_BACK_LIST = '◀️ К списку'
BTN_SCHED_NEW = '➕ Новая задача'
BTN_SCHED_LIST = '📋 Список задач'


def show_mailing_menu(chat_id: int, user_id: int):
    """Show mailing menu"""
    # Check if system is paused
    if DB.is_system_paused(user_id):
        send_message(chat_id,
            "🚨 <b>Система приостановлена</b>\n\n"
            "Рассылки временно недоступны.\n"
            "Используйте /resume для возобновления.",
            kb_main_menu()
        )
        return
    
    DB.set_user_state(user_id, 'mailing:menu')
    
    active_campaigns = len(DB.get_active_campaigns(user_id))
    scheduled = len([m for m in DB.get_scheduled_mailings(user_id) if m['status'] == 'pending'])
    tasks = len([t for t in DB.get_scheduled_tasks(user_id) if t['status'] == 'pending'])
    
    # Get available messages count
    accounts = DB.get_active_accounts(user_id)
    total_available = sum(
        max(0, (a.get('daily_limit', 50) or 50) - (a.get('daily_sent', 0) or 0))
        for a in accounts
    )
    
    send_message(chat_id,
        f"📤 <b>Рассылка</b>\n\n"
        f"📊 Активных: <b>{active_campaigns}</b>\n"
        f"📅 Отложенных: <b>{scheduled}</b>\n"
        f"⏰ Задач в планировщике: <b>{tasks}</b>\n\n"
        f"💳 Доступно сообщений: <b>{total_available}</b>",
        kb_mailing_menu()
    )


def handle_mailing(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle mailing states. Returns True if handled."""
    
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Рассылка отменена")
        return True
    
    if text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return True
    
    if text == BTN_BACK:
        if state in ['mailing:menu', 'mailing:select_source']:
            show_main_menu(chat_id, user_id)
        elif state.startswith('mailing:view_campaign:'):
            show_active_campaigns(chat_id, user_id)
        elif state.startswith('mailing:scheduler'):
            show_mailing_menu(chat_id, user_id)
        elif state.startswith('mailing:'):
            show_mailing_menu(chat_id, user_id)
        return True
    
    if text == BTN_BACK_LIST:
        show_active_campaigns(chat_id, user_id)
        return True
    
    # Menu state
    if state == 'mailing:menu':
        if text == BTN_MAIL_NEW:
            start_new_mailing(chat_id, user_id)
            return True
        if text == BTN_MAIL_ACTIVE:
            show_active_campaigns(chat_id, user_id)
            return True
        if text == BTN_MAIL_SCHEDULED:
            show_scheduled_mailings(chat_id, user_id)
            return True
        if text == BTN_MAIL_SCHEDULER or text == '⏰ Планировщик':
            show_scheduler_menu(chat_id, user_id)
            return True
    
    # Mailing settings state
    if state == 'mailing:settings':
        return handle_mailing_settings(chat_id, user_id, text, saved)
    
    # Confirm mailing state
    if state == 'mailing:confirm':
        if text == BTN_MAIL_START:
            start_mailing_now(chat_id, user_id, saved)
            return True
        if text == BTN_MAIL_SCHEDULE:
            DB.set_user_state(user_id, 'mailing:schedule_time', saved)
            send_message(chat_id,
                "📅 <b>Отложенная рассылка</b>\n\n"
                "Введите дату и время запуска:\n\n"
                "<b>Форматы:</b>\n"
                "• <code>14:30</code> — сегодня/завтра\n"
                "• <code>2024-12-25 14:30</code>\n"
                "• <code>25.12.2024 14:30</code>\n\n"
                "⚠️ Время в UTC",
                kb_back_cancel()
            )
            return True
        if text == BTN_MAIL_SETTINGS:
            show_mailing_settings_menu(chat_id, user_id, saved)
            return True
    
    # Schedule time state
    if state == 'mailing:schedule_time':
        scheduled = parse_schedule_time(text)
        if not scheduled:
            send_message(chat_id,
                "❌ Неверный формат. Примеры:\n"
                "• <code>14:30</code>\n"
                "• <code>2024-12-25 14:30</code>",
                kb_back_cancel()
            )
            return True
        
        if scheduled <= datetime.utcnow():
            send_message(chat_id, "❌ Время должно быть в будущем", kb_back_cancel())
            return True
        
        mailing = DB.create_scheduled_mailing(
            user_id, saved['source_id'], saved['template_id'],
            account_folder_id=saved.get('account_folder_id'),
            scheduled_at=scheduled,
            use_warm_start=saved.get('use_warm_start', True)
        )
        
        DB.clear_user_state(user_id)
        
        if mailing:
            send_message(chat_id,
                f"✅ <b>Рассылка запланирована!</b>\n\n"
                f"📅 Дата: {scheduled.strftime('%d.%m.%Y %H:%M')} UTC\n"
                f"🆔 ID: {mailing['id']}",
                kb_mailing_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания рассылки", kb_mailing_menu())
        return True
    
    # View campaign state
    if state.startswith('mailing:view_campaign:'):
        campaign_id = int(state.split(':')[2])
        campaign = DB.get_campaign(campaign_id)
        
        if not campaign:
            send_message(chat_id, "❌ Кампания не найдена", kb_mailing_menu())
            return True
        
        if text == BTN_CAMPAIGN_PAUSE:
            DB.update_campaign(campaign_id, status='paused', pause_reason='Manual pause')
            send_message(chat_id, "⏸ Кампания приостановлена", kb_campaign_actions('paused'))
            return True
        
        if text == BTN_CAMPAIGN_RESUME:
            # Check if system is paused
            if DB.is_system_paused(user_id):
                send_message(chat_id, 
                    "🚨 Система приостановлена. Сначала используйте /resume",
                    kb_campaign_actions('paused'))
                return True
            DB.update_campaign(campaign_id, status='running', pause_reason=None)
            send_message(chat_id, "▶️ Кампания возобновлена", kb_campaign_actions('running'))
            return True
        
        if text == BTN_CAMPAIGN_STOP:
            DB.update_campaign(campaign_id, status='stopped')
            send_message(chat_id, "🛑 Кампания остановлена", kb_mailing_menu())
            show_active_campaigns(chat_id, user_id)
            return True
        
        if text == BTN_CAMPAIGN_REFRESH:
            show_campaign_view(chat_id, user_id, campaign_id)
            return True
    
    # Scheduler states
    if state == 'mailing:scheduler':
        if text == BTN_SCHED_NEW or text == '➕ Новая задача':
            DB.set_user_state(user_id, 'mailing:scheduler_type')
            send_message(chat_id,
                "⏰ <b>Новая задача планировщика</b>\n\n"
                "Выберите тип задачи:",
                kb_schedule_type()
            )
            return True
        if text == BTN_SCHED_LIST or text == '📋 Список задач':
            show_scheduled_tasks(chat_id, user_id)
            return True
    
    if state == 'mailing:scheduler_type':
        task_type = None
        if text == '🔍 Парсинг':
            task_type = 'parsing'
        elif text == '📤 Рассылка':
            task_type = 'mailing'
        elif text == '🔥 Прогрев аккаунтов':
            task_type = 'warmup'
        
        if task_type:
            saved['task_type'] = task_type
            DB.set_user_state(user_id, 'mailing:scheduler_time', saved)
            send_message(chat_id,
                "⏰ <b>Время запуска</b>\n\n"
                "Введите время в формате:\n"
                "• <code>14:30</code> — ежедневно в это время\n"
                "• <code>2024-12-25 14:30</code> — один раз\n\n"
                "⚠️ Время в UTC",
                kb_back_cancel()
            )
            return True
    
    if state == 'mailing:scheduler_time':
        scheduled = parse_schedule_time(text)
        if not scheduled:
            send_message(chat_id, "❌ Неверный формат времени", kb_back_cancel())
            return True
        
        saved['scheduled_at'] = scheduled
        DB.set_user_state(user_id, 'mailing:scheduler_repeat', saved)
        send_message(chat_id,
            "🔄 <b>Режим повторения</b>\n\n"
            "Как часто запускать задачу?",
            kb_schedule_repeat()
        )
        return True
    
    if state == 'mailing:scheduler_repeat':
        repeat_mode = 'once'
        if text == '🔂 Один раз':
            repeat_mode = 'once'
        elif text == '📅 Ежедневно':
            repeat_mode = 'daily'
        elif text == '📆 Еженедельно':
            repeat_mode = 'weekly'
        else:
            send_message(chat_id, "❌ Выберите режим повторения", kb_schedule_repeat())
            return True
        
        task_config = {
            'task_type': saved.get('task_type'),
            # Additional config can be added here
        }
        
        task = DB.create_scheduled_task(
            user_id=user_id,
            task_type=saved.get('task_type', 'mailing'),
            task_config=task_config,
            scheduled_at=saved['scheduled_at'],
            repeat_mode=repeat_mode
        )
        
        DB.clear_user_state(user_id)
        
        if task:
            type_names = {'parsing': 'Парсинг', 'mailing': 'Рассылка', 'warmup': 'Прогрев'}
            repeat_names = {'once': 'один раз', 'daily': 'ежедневно', 'weekly': 'еженедельно'}
            
            send_message(chat_id,
                f"✅ <b>Задача создана!</b>\n\n"
                f"📋 Тип: {type_names.get(saved.get('task_type'), saved.get('task_type'))}\n"
                f"📅 Время: {saved['scheduled_at'].strftime('%d.%m.%Y %H:%M')} UTC\n"
                f"🔄 Повторение: {repeat_names.get(repeat_mode, repeat_mode)}",
                kb_mailing_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания задачи", kb_mailing_menu())
        return True
    
    return False


def handle_mailing_settings(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle mailing settings during campaign creation"""
    
    # Toggle warm start
    if '🔥 Тёплый старт:' in text:
        saved['use_warm_start'] = not saved.get('use_warm_start', True)
        show_mailing_settings_menu(chat_id, user_id, saved)
        return True
    
    # Toggle typing simulation
    if '⌨️ Имитация печати:' in text:
        saved['use_typing'] = not saved.get('use_typing', True)
        show_mailing_settings_menu(chat_id, user_id, saved)
        return True
    
    # Toggle adaptive delays
    if '📊 Адаптивные задержки:' in text:
        saved['use_adaptive'] = not saved.get('use_adaptive', True)
        show_mailing_settings_menu(chat_id, user_id, saved)
        return True
    
    # Done - return to confirm
    if text == '✅ Готово':
        show_mailing_confirm(chat_id, user_id, saved)
        return True
    
    if text == BTN_BACK:
        show_mailing_confirm(chat_id, user_id, saved)
        return True
    
    return False


def handle_mailing_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle mailing inline callbacks"""
    state_data = DB.get_user_state(user_id)
    saved = state_data.get('data', {}) if state_data else {}
    
    # Source selection
    if data.startswith('msrc:'):
        source_id = int(data.split(':')[1])
        saved['source_id'] = source_id
        DB.set_user_state(user_id, 'mailing:select_template', saved)
        
        templates = DB.get_templates(user_id)
        if not templates:
            send_message(chat_id, "❌ Нет шаблонов. Создайте в разделе «📄 Шаблоны».", kb_mailing_menu())
            return True
        
        send_message(chat_id, "📝 <b>Шаг 2/3: Выберите шаблон:</b>", kb_inline_mailing_templates(templates))
        return True
    
    # Template selection
    if data.startswith('mtpl:'):
        template_id = int(data.split(':')[1])
        saved['template_id'] = template_id
        DB.set_user_state(user_id, 'mailing:select_accounts', saved)
        
        folders = DB.get_account_folders(user_id)
        accounts = DB.get_accounts_without_folder(user_id)
        
        kb = kb_inline_mailing_acc_folders(folders, accounts)
        if not kb or not kb.get('inline_keyboard'):
            send_message(chat_id, "❌ Нет активных аккаунтов", kb_mailing_menu())
            return True
        
        send_message(chat_id, "👤 <b>Шаг 3/3: Выберите папку аккаунтов:</b>", kb)
        return True
    
    # Account folder selection
    if data.startswith('macc:'):
        folder_id = int(data.split(':')[1])
        saved['account_folder_id'] = folder_id
        
        # Set default settings
        settings = DB.get_user_settings(user_id)
        saved['use_warm_start'] = settings.get('warmup_before_mailing', False)
        saved['use_typing'] = True
        saved['use_adaptive'] = True
        saved['delay_min'] = settings.get('delay_min', 30)
        saved['delay_max'] = settings.get('delay_max', 90)
        
        show_mailing_confirm(chat_id, user_id, saved)
        return True
    
    # Campaign selection
    if data.startswith('cmp:'):
        campaign_id = int(data.split(':')[1])
        show_campaign_view(chat_id, user_id, campaign_id)
        return True
    
    # Scheduled mailing selection/deletion
    if data.startswith('schd:'):
        mailing_id = int(data.split(':')[1])
        mailing = DB._select('scheduled_mailings', filters={'id': mailing_id}, single=True)
        if mailing:
            scheduled = mailing.get('scheduled_at', '')[:16].replace('T', ' ')
            send_message(chat_id, 
                f"📅 <b>Отложенная рассылка #{mailing_id}</b>\n\n"
                f"⏰ Запуск: {scheduled} UTC\n"
                f"📊 Статус: {mailing.get('status', 'pending')}",
                kb_mailing_menu())
        return True
    
    if data.startswith('delschd:'):
        mailing_id = int(data.split(':')[1])
        DB.delete_scheduled_mailing(mailing_id)
        send_message(chat_id, "✅ Рассылка отменена", kb_mailing_menu())
        show_scheduled_mailings(chat_id, user_id)
        return True
    
    # Scheduled task deletion
    if data.startswith('task:'):
        task_id = int(data.split(':')[1])
        task = DB._select('scheduled_tasks', filters={'id': task_id}, single=True)
        if task:
            type_names = {'parsing': 'Парсинг', 'mailing': 'Рассылка', 'warmup': 'Прогрев'}
            scheduled = task.get('scheduled_at', '')[:16].replace('T', ' ')
            send_message(chat_id,
                f"⏰ <b>Задача #{task_id}</b>\n\n"
                f"📋 Тип: {type_names.get(task.get('task_type'), task.get('task_type'))}\n"
                f"⏰ Запуск: {scheduled} UTC\n"
                f"🔄 Повтор: {task.get('repeat_mode', 'once')}",
                kb_mailing_menu())
        return True
    
    if data.startswith('deltask:'):
        task_id = int(data.split(':')[1])
        DB.delete_scheduled_task(task_id)
        send_message(chat_id, "✅ Задача удалена", kb_mailing_menu())
        show_scheduled_tasks(chat_id, user_id)
        return True
    
    return False


def start_new_mailing(chat_id: int, user_id: int):
    """Start new mailing flow"""
    # Check system status
    if DB.is_system_paused(user_id):
        send_message(chat_id,
            "🚨 <b>Система приостановлена</b>\n\n"
            "Используйте /resume для возобновления.",
            kb_mailing_menu()
        )
        return
    
    sources = DB.get_audience_sources(user_id, status='completed')
    
    if not sources:
        send_message(chat_id,
            "❌ <b>Нет готовых аудиторий</b>\n\n"
            "Сначала создайте аудиторию через парсинг.",
            kb_mailing_menu()
        )
        return
    
    # Filter sources with remaining users
    settings = DB.get_user_settings(user_id)
    cache_ttl = settings.get('mailing_cache_ttl', 30) or 30
    
    valid = []
    for s in sources:
        stats = DB.get_audience_stats(s['id'])
        if stats['remaining'] > 0:
            valid.append(s)
    
    if not valid:
        send_message(chat_id,
            "❌ <b>Нет доступных получателей</b>\n\n"
            "Все пользователи уже получили сообщения.",
            kb_mailing_menu()
        )
        return
    
    DB.set_user_state(user_id, 'mailing:select_source')
    send_message(chat_id, "📊 <b>Шаг 1/3: Выберите аудиторию:</b>", kb_inline_mailing_sources(valid))
    send_message(chat_id, "👆 Выберите аудиторию выше", kb_back_cancel())


def show_mailing_settings_menu(chat_id: int, user_id: int, saved: dict):
    """Show mailing settings menu"""
    DB.set_user_state(user_id, 'mailing:settings', saved)
    
    warm_status = 'ВКЛ ✅' if saved.get('use_warm_start', True) else 'ВЫКЛ ❌'
    typing_status = 'ВКЛ ✅' if saved.get('use_typing', True) else 'ВЫКЛ ❌'
    adaptive_status = 'ВКЛ ✅' if saved.get('use_adaptive', True) else 'ВЫКЛ ❌'
    
    # Dynamic keyboard based on current settings
    buttons = [
        [f"🔥 Тёплый старт: {warm_status}"],
        [f"⌨️ Имитация печати: {typing_status}"],
        [f"📊 Адаптивные задержки: {adaptive_status}"],
        ['✅ Готово'],
        ['◀️ Назад']
    ]
    
    kb = {'keyboard': buttons, 'resize_keyboard': True}
    
    send_message(chat_id,
        "⚙️ <b>Настройки рассылки</b>\n\n"
        f"🔥 <b>Тёплый старт:</b> {warm_status}\n"
        "<i>Первые 10 сообщений с увеличенными паузами</i>\n\n"
        f"⌨️ <b>Имитация печати:</b> {typing_status}\n"
        "<i>Отображение «печатает...» перед отправкой</i>\n\n"
        f"📊 <b>Адаптивные задержки:</b> {adaptive_status}\n"
        "<i>Автоматическая корректировка пауз при ошибках</i>\n\n"
        "Нажмите на настройку для переключения:",
        kb
    )


def show_mailing_confirm(chat_id: int, user_id: int, saved: dict):
    """Show mailing confirmation"""
    DB.set_user_state(user_id, 'mailing:confirm', saved)
    
    source = DB.get_audience_source(saved.get('source_id'))
    template = DB.get_template(saved.get('template_id'))
    stats = DB.get_audience_stats(saved.get('source_id')) if saved.get('source_id') else {}
    
    folder_id = saved.get('account_folder_id')
    if folder_id and folder_id > 0:
        folder = DB.get_account_folder(folder_id)
        folder_name = folder['name'] if folder else 'Папка'
        accounts = DB.get_accounts_in_folder(folder_id)
        active_accounts = [a for a in accounts if a.get('status') == 'active']
    else:
        folder_name = 'Без папки'
        accounts = DB.get_accounts_without_folder(user_id)
        active_accounts = [a for a in accounts if a.get('status') == 'active']
    
    active_count = len(active_accounts)
    total_available = sum(
        (a.get('daily_limit', 50) or 50) - (a.get('daily_sent', 0) or 0)
        for a in active_accounts
    )
    
    settings = DB.get_user_settings(user_id)
    delay_min = saved.get('delay_min') or settings.get('delay_min', 30) or 30
    delay_max = saved.get('delay_max') or settings.get('delay_max', 90) or 90
    
    # Settings status
    warm_icon = '✅' if saved.get('use_warm_start', True) else '❌'
    typing_icon = '✅' if saved.get('use_typing', True) else '❌'
    adaptive_icon = '✅' if saved.get('use_adaptive', True) else '❌'
    
    # Check cache TTL
    cache_ttl = settings.get('mailing_cache_ttl', 30) or 30
    cache_info = f"\n🗓 <b>Кэш:</b> {cache_ttl} дней" if cache_ttl > 0 else ""
    
    # Keyword filter info
    kw_info = ""
    if source and source.get('keyword_filter'):
        kw_info = f"\n🔑 <b>Ключевые слова:</b> {len(source['keyword_filter'])} шт."
    
    send_message(chat_id,
        f"📤 <b>Подтверждение рассылки</b>\n\n"
        f"📊 <b>Аудитория:</b> {source['source_link'] if source else '?'}{kw_info}\n"
        f"👥 <b>Получателей:</b> {stats.get('remaining', 0)}\n\n"
        f"📝 <b>Шаблон:</b> {template['name'] if template else '?'}\n\n"
        f"📁 <b>Папка аккаунтов:</b> {folder_name}\n"
        f"👤 <b>Активных аккаунтов:</b> {active_count}\n"
        f"💳 <b>Доступно сообщений:</b> {total_available}\n\n"
        f"⏱ <b>Задержка:</b> {delay_min}-{delay_max} сек{cache_info}\n\n"
        f"<b>Настройки:</b>\n"
        f"{warm_icon} Тёплый старт | {typing_icon} Печать | {adaptive_icon} Адаптив",
        kb_mailing_confirm()
    )


def start_mailing_now(chat_id: int, user_id: int, saved: dict):
    """Start mailing immediately"""
    if not all([saved.get('source_id'), saved.get('template_id')]):
        send_message(chat_id, "❌ Ошибка: данные не найдены", kb_mailing_menu())
        DB.clear_user_state(user_id)
        return
    
    # Check system status
    if DB.is_system_paused(user_id):
        send_message(chat_id,
            "🚨 <b>Система приостановлена</b>\n\n"
            "Используйте /resume для возобновления.",
            kb_mailing_menu()
        )
        DB.clear_user_state(user_id)
        return
    
    folder_id = saved.get('account_folder_id')
    if folder_id and folder_id > 0:
        accounts = DB.get_accounts_in_folder(folder_id)
    else:
        accounts = DB.get_accounts_without_folder(user_id)
    
    active_accounts = [a for a in accounts if a.get('status') == 'active']
    
    if not active_accounts:
        send_message(chat_id, "❌ Нет активных аккаунтов", kb_mailing_menu())
        DB.clear_user_state(user_id)
        return
    
    account_ids = [a['id'] for a in active_accounts]
    settings = DB.get_user_settings(user_id)
    
    campaign = DB.create_campaign(
        user_id=user_id,
        source_id=saved['source_id'],
        template_id=saved['template_id'],
        account_ids=account_ids,
        account_folder_id=folder_id,
        settings={
            'delay_min': saved.get('delay_min') or settings.get('delay_min', 30),
            'delay_max': saved.get('delay_max') or settings.get('delay_max', 90),
            'auto_switch': True,
            'report_every': 10,
            'cache_ttl': settings.get('mailing_cache_ttl', 30)
        },
        use_warm_start=saved.get('use_warm_start', True),
        use_typing=saved.get('use_typing', True),
        use_adaptive=saved.get('use_adaptive', True)
    )
    
    DB.clear_user_state(user_id)
    
    if campaign:
        stats = DB.get_audience_stats(saved['source_id'])
        
        features = []
        if saved.get('use_warm_start', True):
            features.append('🔥 тёплый старт')
        if saved.get('use_typing', True):
            features.append('⌨️ имитация печати')
        if saved.get('use_adaptive', True):
            features.append('📊 адаптивные задержки')
        
        features_str = '\n'.join(features) if features else 'стандартные'
        
        send_message(chat_id,
            f"🚀 <b>Рассылка запущена!</b>\n\n"
            f"🆔 ID кампании: <code>{campaign['id']}</code>\n"
            f"👥 Получателей: <b>{stats['remaining']}</b>\n"
            f"👤 Аккаунтов: <b>{len(account_ids)}</b>\n\n"
            f"<b>Активные функции:</b>\n{features_str}\n\n"
            f"<i>Вы будете получать отчёты о прогрессе.</i>",
            kb_mailing_menu()
        )
    else:
        send_message(chat_id, "❌ Ошибка создания рассылки", kb_mailing_menu())


def show_active_campaigns(chat_id: int, user_id: int):
    """Show active campaigns"""
    campaigns = DB.get_active_campaigns(user_id)
    DB.set_user_state(user_id, 'mailing:active_list')
    
    if not campaigns:
        send_message(chat_id,
            "📊 <b>Активные рассылки</b>\n\n"
            "Нет активных рассылок.",
            kb_mailing_menu()
        )
    else:
        txt = f"📊 <b>Активные рассылки ({len(campaigns)}):</b>\n\n"
        for c in campaigns[:5]:
            status_emoji = {'pending': '⏳', 'running': '🔄', 'paused': '⏸'}.get(c['status'], '❓')
            sent = c.get('sent_count', 0)
            failed = c.get('failed_count', 0)
            total = c.get('total_count', '?')
            
            # Progress bar
            if total and total > 0:
                progress = int(sent / total * 10)
                bar = '█' * progress + '░' * (10 - progress)
                txt += f"{status_emoji} #{c['id']} [{bar}]\n"
                txt += f"   ✅ {sent} | ❌ {failed} | 👥 {total}\n\n"
            else:
                txt += f"{status_emoji} #{c['id']} — {sent}/{total} (ошибок: {failed})\n\n"
        
        send_message(chat_id, txt, kb_inline_campaigns(campaigns))
        send_message(chat_id, "👆 Выберите для управления", kb_mailing_menu())


def show_campaign_view(chat_id: int, user_id: int, campaign_id: int):
    """Show campaign details"""
    campaign = DB.get_campaign(campaign_id)
    if not campaign:
        send_message(chat_id, "❌ Кампания не найдена", kb_mailing_menu())
        return
    
    DB.set_user_state(user_id, f'mailing:view_campaign:{campaign_id}')
    
    status_map = {
        'pending': '⏳ В очереди',
        'running': '🔄 Выполняется',
        'paused': '⏸ Приостановлена',
        'completed': '✅ Завершена',
        'stopped': '🛑 Остановлена',
        'failed': '❌ Ошибка'
    }
    
    source = DB.get_audience_source(campaign.get('source_id'))
    template = DB.get_template(campaign.get('template_id'))
    
    # Current account info
    current_acc_info = ""
    if campaign.get('current_account_id'):
        current_account = DB.get_account(campaign['current_account_id'])
        if current_account:
            phone = current_account['phone']
            masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
            reliability = current_account.get('reliability_score', 100) or 100
            rel_emoji = '🟢' if reliability >= 80 else '🟡' if reliability >= 50 else '🔴'
            current_acc_info = f"\n📱 <b>Текущий аккаунт:</b> {masked} {rel_emoji}"
    
    # Progress bar
    sent = campaign.get('sent_count', 0)
    total = campaign.get('total_count', 0) or 1
    progress = int(sent / total * 20)
    bar = '█' * progress + '░' * (20 - progress)
    percent = int(sent / total * 100)
    
    # Features
    features = []
    if campaign.get('use_warm_start'):
        warm_count = campaign.get('warm_start_count', 10)
        if sent < warm_count:
            features.append(f'🔥 Тёплый старт ({sent}/{warm_count})')
    if campaign.get('use_typing_simulation'):
        features.append('⌨️ Имитация печати')
    if campaign.get('use_adaptive_delays'):
        multiplier = campaign.get('current_delay_multiplier', 1.0) or 1.0
        features.append(f'📊 Адаптив (x{multiplier:.1f})')
    
    features_str = '\n'.join(features) if features else ''
    if features_str:
        features_str = f"\n\n<b>Активные функции:</b>\n{features_str}"
    
    # Pause reason
    pause_info = ""
    if campaign.get('pause_reason'):
        pause_info = f"\n⚠️ <b>Причина паузы:</b> {campaign['pause_reason']}"
    
    send_message(chat_id,
        f"📊 <b>Кампания #{campaign['id']}</b>\n\n"
        f"📈 <b>Статус:</b> {status_map.get(campaign['status'], campaign['status'])}{pause_info}\n"
        f"📊 <b>Аудитория:</b> {source['source_link'] if source else '?'}\n"
        f"📝 <b>Шаблон:</b> {template['name'] if template else '?'}\n\n"
        f"<b>Прогресс:</b> [{bar}] {percent}%\n"
        f"✅ <b>Отправлено:</b> {campaign.get('sent_count', 0)}\n"
        f"❌ <b>Ошибок:</b> {campaign.get('failed_count', 0)}\n"
        f"👥 <b>Всего:</b> {campaign.get('total_count', '?')}"
        f"{current_acc_info}{features_str}",
        kb_campaign_actions(campaign['status'])
    )


def show_scheduled_mailings(chat_id: int, user_id: int):
    """Show scheduled mailings"""
    mailings = DB.get_scheduled_mailings(user_id)
    pending = [m for m in mailings if m['status'] == 'pending']
    
    DB.set_user_state(user_id, 'mailing:scheduled_list')
    
    if not pending:
        send_message(chat_id,
            "📅 <b>Отложенные рассылки</b>\n\n"
            "Нет запланированных рассылок.",
            kb_mailing_menu()
        )
    else:
        txt = f"📅 <b>Отложенные рассылки ({len(pending)}):</b>\n"
        for m in pending[:5]:
            scheduled = m.get('scheduled_at', '')[:16].replace('T', ' ')
            txt += f"• #{m['id']} | {scheduled} UTC\n"
        
        send_message(chat_id, txt, kb_inline_scheduled(pending))
        send_message(chat_id, "👆 Нажмите 🗑 для отмены", kb_mailing_menu())


def show_scheduler_menu(chat_id: int, user_id: int):
    """Show scheduler menu"""
    DB.set_user_state(user_id, 'mailing:scheduler')
    
    tasks = DB.get_scheduled_tasks(user_id, status='pending')
    
    send_message(chat_id,
        f"⏰ <b>Планировщик задач</b>\n\n"
        f"📋 Активных задач: <b>{len(tasks)}</b>\n\n"
        f"Планировщик позволяет:\n"
        f"• Запускать парсинг по расписанию\n"
        f"• Автоматически запускать рассылки\n"
        f"• Планировать прогрев аккаунтов\n\n"
        f"<i>Задачи выполняются в указанное время (UTC)</i>",
        kb_scheduler_menu()
    )


def show_scheduled_tasks(chat_id: int, user_id: int):
    """Show list of scheduled tasks"""
    tasks = DB.get_scheduled_tasks(user_id)
    pending = [t for t in tasks if t['status'] == 'pending']
    
    if not pending:
        send_message(chat_id,
            "⏰ <b>Задачи планировщика</b>\n\n"
            "Нет активных задач.",
            kb_scheduler_menu()
        )
    else:
        txt = f"⏰ <b>Задачи планировщика ({len(pending)}):</b>\n\n"
        type_emoji = {'parsing': '🔍', 'mailing': '📤', 'warmup': '🔥'}
        
        for t in pending[:10]:
            emoji = type_emoji.get(t.get('task_type'), '📋')
            scheduled = t.get('scheduled_at', '')[:16].replace('T', ' ')
            repeat = '🔄' if t.get('repeat_mode') != 'once' else ''
            txt += f"{emoji}{repeat} #{t['id']} | {scheduled} UTC\n"
        
        send_message(chat_id, txt, kb_inline_scheduled_tasks(pending))
        send_message(chat_id, "👆 Нажмите 🗑 для удаления", kb_scheduler_menu())


def parse_schedule_time(text: str) -> datetime:
    """Parse schedule time from text"""
    text_clean = text.strip()
    now = datetime.utcnow()
    
    try:
        # Format: HH:MM
        if re.match(r'^\d{1,2}:\d{2}$', text_clean):
            h, m = map(int, text_clean.split(':'))
            if h > 23 or m > 59:
                return None
            scheduled = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if scheduled <= now:
                scheduled += timedelta(days=1)
            return scheduled
        
        # Format: YYYY-MM-DD HH:MM
        if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}$', text_clean):
            return datetime.strptime(text_clean, '%Y-%m-%d %H:%M')
        
        # Format: DD.MM.YYYY HH:MM
        if re.match(r'^\d{1,2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2}$', text_clean):
            return datetime.strptime(text_clean, '%d.%m.%Y %H:%M')
        
    except:
        pass
    
    return None
