"""
Settings handlers - Extended v3.1
Fixed navigation loops in Herder/Factory settings
"""
import re
import logging
from core.db import DB
from core.telegram import send_message
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel,
    kb_settings_menu, kb_settings_schedule, kb_settings_security, kb_settings_automation,
    kb_quiet_hours, kb_notifications, kb_delay_settings,
    kb_cache_ttl, kb_auto_blacklist, kb_warmup_settings, kb_risk_tolerance,
    kb_ai_settings, kb_api_keys, kb_gpt_temperature,
    kb_stop_triggers_menu, kb_inline_stop_triggers,
    kb_yandex_models,
    reply_keyboard
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU
logger = logging.getLogger(__name__)

# Button constants - existing
BTN_QUIET_HOURS = '🌙 Тихие часы'
BTN_NOTIFICATIONS = '🔔 Уведомления'
BTN_DELAY = '⏱ Задержки'
BTN_CACHE_TTL = '🗓 Кэш рассылки'
BTN_AUTO_BLACKLIST = '🛡 Авто-блокировка'
BTN_WARMUP = '🔥 Прогрев'

# Button constants - new
BTN_RISK_TOLERANCE = '⚠️ Риск-толерантность'
BTN_HERDER_SETTINGS = '🤖 Ботовод'
BTN_FACTORY_SETTINGS = '🏭 Фабрика'
BTN_AI_SETTINGS = '🧠 ИИ и обучение'
BTN_API_KEYS = '🔑 API ключи'

# Other buttons
BTN_SET = '⏰ Установить'
BTN_DISABLE = '🔕 Отключить'
BTN_ENABLE = '🔔 Включить'
BTN_CUSTOM_DELAY = '📝 Свой диапазон'
BTN_STOP_WORDS = '🛡 Настроить стоп-слова'
BTN_ADD_WORD = '➕ Добавить слово'
BTN_LIST_WORDS = '📋 Список слов'

def show_settings_menu(chat_id: int, user_id: int):
    """Show settings menu - Extended with comprehensive description"""
    DB.set_user_state(user_id, 'settings:menu')
    settings = DB.get_user_settings(user_id)
    # Basic settings
    qs = settings.get('quiet_hours_start')
    qe = settings.get('quiet_hours_end')
    quiet = f"{qs}-{qe}" if qs and qe else "выкл"
    notify = '✅' if settings.get('notify_on_complete', True) else '❌'
    delay_min = settings.get('delay_min', 30) or 30
    delay_max = settings.get('delay_max', 90) or 90
    cache_ttl = settings.get('mailing_cache_ttl', 30) or 30
    auto_bl = '✅' if settings.get('auto_blacklist_enabled', True) else '❌'
    warmup = '✅' if settings.get('warmup_before_mailing', False) else '❌'
    # New settings
    risk = {'low': '🟢 Низкий', 'medium': '🟡 Средний', 'high': '🔴 Высокий'}.get(
        settings.get('risk_tolerance', 'medium'), '🟡 Средний')
    learning = '✅' if settings.get('learning_mode', True) else '❌'
    # API status
    yagpt = '✅' if settings.get('yagpt_api_key') else '❌'
    onlinesim = '✅' if settings.get('onlinesim_api_key') else '❌'
    send_message(chat_id,
        f"⚙️ <b>Настройки</b>\n\n"
        f"<i>Настройте поведение бота, задержки, API-интеграции\n"
        f"и параметры безопасности под ваши задачи.</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📤 РАССЫЛКА</b>\n"
        f"├ 🌙 Тихие часы: {quiet}\n"
        f"├ 🔔 Уведомления: {notify}\n"
        f"├ ⏱ Задержка: {delay_min}-{delay_max} сек\n"
        f"├ 🗓 Кэш: {cache_ttl} дней\n"
        f"├ 🛡 Авто-ЧС: {auto_bl}\n"
        f"└ 🔥 Прогрев: {warmup}\n\n"
        f"<b>🛡 СИСТЕМА</b>\n"
        f"├ ⚠️ Риск-толерантность: {risk}\n"
        f"└ 🧠 Обучение: {learning}\n\n"
        f"<b>🔑 API ИНТЕГРАЦИИ</b>\n"
        f"├ 🔑 Yandex GPT: {yagpt}\n"
        f"└ 📱 OnlineSim: {onlinesim}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 <i>Нажмите на раздел для настройки</i>",
        kb_settings_menu()
    )


def show_schedule_submenu(chat_id: int, user_id: int):
    """Show schedule and time settings submenu"""
    DB.set_user_state(user_id, 'settings:schedule')
    settings = DB.get_user_settings(user_id)
    
    qs = settings.get('quiet_hours_start')
    qe = settings.get('quiet_hours_end')
    quiet = f"{qs}-{qe} МСК" if qs and qe else "выкл"
    
    delay_min = settings.get('delay_min', 30) or 30
    delay_max = settings.get('delay_max', 90) or 90
    
    cache_ttl = settings.get('mailing_cache_ttl', 30) or 30
    cache_status = f"{cache_ttl} дней" if cache_ttl > 0 else "выкл"
    
    send_message(chat_id,
        f"🕐 <b>Расписание и время</b>\n\n"
        f"🌙 <b>Тихие часы:</b> {quiet}\n"
        f"<i>Время, когда рассылки не отправляются</i>\n\n"
        f"⏱ <b>Задержки:</b> {delay_min}-{delay_max} сек\n"
        f"<i>Пауза между сообщениями</i>\n\n"
        f"🗓 <b>Кэш рассылки:</b> {cache_status}\n"
        f"<i>Исключение повторных отправок</i>",
        kb_settings_schedule()
    )


def show_security_submenu(chat_id: int, user_id: int):
    """Show security settings submenu"""
    DB.set_user_state(user_id, 'settings:security')
    settings = DB.get_user_settings(user_id)
    
    auto_bl = '✅ вкл' if settings.get('auto_blacklist_enabled', True) else '❌ выкл'
    triggers = DB.get_stop_triggers(user_id)
    active_count = sum(1 for t in triggers if t.get('is_active'))
    
    risk = {'low': '🟢 Низкий', 'medium': '🟡 Средний', 'high': '🔴 Высокий'}.get(
        settings.get('risk_tolerance', 'medium'), '🟡 Средний')
    
    warmup = '✅ вкл' if settings.get('warmup_before_mailing', False) else '❌ выкл'
    warmup_mins = settings.get('warmup_duration_minutes', 5) or 5
    
    send_message(chat_id,
        f"🛡 <b>Безопасность</b>\n\n"
        f"🛡 <b>Авто-блокировка:</b> {auto_bl}\n"
        f"<i>Стоп-слов: {active_count}</i>\n\n"
        f"⚠️ <b>Риск-толерантность:</b> {risk}\n"
        f"<i>Влияет на агрессивность работы</i>\n\n"
        f"🔥 <b>Прогрев:</b> {warmup}\n"
        f"<i>Подготовка аккаунтов ({warmup_mins} мин)</i>",
        kb_settings_security()
    )


def show_automation_submenu(chat_id: int, user_id: int):
    """Show automation settings submenu"""
    DB.set_user_state(user_id, 'settings:automation')
    settings = DB.get_user_settings(user_id)
    
    herder = settings.get('herder_settings', {})
    strategy_names = {
        'observer': '📖 Наблюдатель',
        'expert': '🧠 Эксперт',
        'support': '💪 Поддержка',
        'trendsetter': '🔥 Трендсеттер',
        'community': '👥 Комьюнити'
    }
    strategy = strategy_names.get(herder.get('default_strategy', 'observer'), '📖 Наблюдатель')
    
    factory = settings.get('factory_settings', {})
    warmup_days = factory.get('default_warmup_days', 5)
    
    learning = '✅ вкл' if settings.get('learning_mode', True) else '❌ выкл'
    
    send_message(chat_id,
        f"🤖 <b>Автоматизация</b>\n\n"
        f"🤖 <b>Ботовод:</b>\n"
        f"<i>Стратегия: {strategy}</i>\n\n"
        f"🏭 <b>Фабрика:</b>\n"
        f"<i>Прогрев: {warmup_days} дней</i>\n\n"
        f"🧠 <b>ИИ и обучение:</b> {learning}\n"
        f"<i>Самообучение на результатах</i>",
        kb_settings_automation()
    )


def handle_settings(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle settings states. Returns True if handled."""
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Действие отменено")
        return True
    if text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return True
    if text == BTN_BACK or text == '◀️ Назад':
        if state == 'settings:menu':
            show_main_menu(chat_id, user_id)
        # Submenus back to main settings
        elif state in ['settings:schedule', 'settings:security', 'settings:automation']:
            show_settings_menu(chat_id, user_id)
        # Schedule items back to schedule submenu
        elif state in ['settings:quiet_hours', 'settings:quiet_hours_input', 
                       'settings:delay', 'settings:delay_input', 'settings:cache_ttl']:
            show_schedule_submenu(chat_id, user_id)
        # Security items back to security submenu
        elif state in ['settings:auto_blacklist', 'settings:risk_tolerance', 'settings:warmup']:
            show_security_submenu(chat_id, user_id)
        elif state == 'settings:stop_triggers':
            show_auto_blacklist(chat_id, user_id)
        # Automation items back to automation submenu
        elif state in ['settings:herder', 'settings:herder:strategy', 'settings:herder:max_actions',
                       'settings:factory', 'settings:factory:warmup_days',
                       'settings:ai', 'settings:ai:temperature']:
            show_automation_submenu(chat_id, user_id)
        # API keys back to main settings
        elif state in ['settings:api_keys', 'settings:api:yagpt', 'settings:api:yagpt_folder', 
                       'settings:api:onlinesim', 'settings:api:model', 'settings:api:yagpt_model', 'settings:notifications']:
            show_settings_menu(chat_id, user_id)
        else:
            show_settings_menu(chat_id, user_id)
        return True

    # Menu state - new grouped structure
    if state == 'settings:menu':
        if text == '🕐 Расписание и время':
            show_schedule_submenu(chat_id, user_id)
            return True
        if text == '🛡 Безопасность':
            show_security_submenu(chat_id, user_id)
            return True
        if text == '🤖 Автоматизация':
            show_automation_submenu(chat_id, user_id)
            return True
        if text == BTN_NOTIFICATIONS:
            show_notifications(chat_id, user_id)
            return True
        if text == BTN_API_KEYS:
            show_api_keys(chat_id, user_id)
            return True
    
    # Schedule submenu
    if state == 'settings:schedule':
        if text == BTN_QUIET_HOURS:
            show_quiet_hours(chat_id, user_id)
            return True
        if text == BTN_DELAY or text == '⏱ Задержки':
            show_delay_settings(chat_id, user_id)
            return True
        if text == BTN_CACHE_TTL:
            show_cache_settings(chat_id, user_id)
            return True
    
    # Security submenu
    if state == 'settings:security':
        if text == BTN_AUTO_BLACKLIST:
            show_auto_blacklist(chat_id, user_id)
            return True
        if text == BTN_RISK_TOLERANCE or text == '⚠️ Риск-толерантность':
            show_risk_tolerance(chat_id, user_id)
            return True
        if text == '🔥 Прогрев аккаунтов':
            show_warmup_settings(chat_id, user_id)
            return True
    
    # Automation submenu
    if state == 'settings:automation':
        if text == BTN_HERDER_SETTINGS:
            show_herder_settings(chat_id, user_id)
            return True
        if text == BTN_FACTORY_SETTINGS:
            show_factory_settings(chat_id, user_id)
            return True
        if text == BTN_AI_SETTINGS:
            show_ai_settings(chat_id, user_id)
            return True

    # Quiet hours state
    if state == 'settings:quiet_hours':
        if text == BTN_SET or text == '⏰ Установить':
            DB.set_user_state(user_id, 'settings:quiet_hours_input')
            send_message(chat_id,
                "🌙 <b>Установка тихих часов</b>\n"
                "Введите диапазон в формате:\n"
                "<code>23:00-08:00</code>\n"
                "В это время рассылки не будут отправляться.\n"
                "⚠️ Время в московском часовом поясе (МСК)",
                kb_back_cancel()
            )
            return True
        if text == BTN_DISABLE or text == '🔕 Отключить':
            DB.update_user_settings(user_id, quiet_hours_start=None, quiet_hours_end=None)
            send_message(chat_id, "✅ Тихие часы отключены", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True

    # Quiet hours input
    if state == 'settings:quiet_hours_input':
        m = re.match(r'^(\d{1,2}):(\d{2})\s*[-—]\s*(\d{1,2}):(\d{2})$', text.strip())
        if not m:
            send_message(chat_id, "❌ Неверный формат. Пример: <code>23:00-08:00</code>", kb_back_cancel())
            return True
        sh, sm, eh, em = map(int, m.groups())
        if sh > 23 or sm > 59 or eh > 23 or em > 59:
            send_message(chat_id, "❌ Неверное время", kb_back_cancel())
            return True
        DB.update_user_settings(user_id,
            quiet_hours_start=f"{sh:02d}:{sm:02d}",
            quiet_hours_end=f"{eh:02d}:{em:02d}"
        )
        send_message(chat_id, f"✅ Тихие часы: {sh:02d}:{sm:02d} - {eh:02d}:{em:02d} МСК", kb_settings_menu())
        show_settings_menu(chat_id, user_id)
        return True

    # Notifications state
    if state == 'settings:notifications':
        if text == BTN_ENABLE or text == '🔔 Включить':
            DB.update_user_settings(user_id, notify_on_complete=True, notify_on_error=True)
            send_message(chat_id, "✅ Уведомления включены", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True
        if text == BTN_DISABLE or text == '🔕 Отключить':
            DB.update_user_settings(user_id, notify_on_complete=False, notify_on_error=False)
            send_message(chat_id, "✅ Уведомления отключены", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True

    # Delay settings state
    if state == 'settings:delay':
        if text == BTN_CUSTOM_DELAY or text == '📝 Свой диапазон':
            DB.set_user_state(user_id, 'settings:delay_input')
            send_message(chat_id,
                "⏱ <b>Своя задержка</b>\n"
                "Введите диапазон в формате:\n"
                "<code>мин-макс</code>\n"
                "Например: <code>30-90</code> (секунды)",
                kb_back_cancel()
            )
            return True
        delays = {
            '5-15 сек': (5, 15),
            '15-45 сек': (15, 45),
            '30-90 сек': (30, 90),
            '60-180 сек': (60, 180)
        }
        if text in delays:
            delay_min, delay_max = delays[text]
            DB.update_user_settings(user_id, delay_min=delay_min, delay_max=delay_max)
            send_message(chat_id, f"✅ Задержка: {delay_min}-{delay_max} сек", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True

    # Delay input state
    if state == 'settings:delay_input':
        m = re.match(r'^(\d+)\s*[-—]\s*(\d+)$', text.strip())
        if not m:
            send_message(chat_id, "❌ Неверный формат. Пример: <code>30-90</code>", kb_back_cancel())
            return True
        delay_min, delay_max = int(m.group(1)), int(m.group(2))
        if delay_min > delay_max:
            delay_min, delay_max = delay_max, delay_min
        if delay_min < 1 or delay_max > 600:
            send_message(chat_id, "❌ Задержка от 1 до 600 секунд", kb_back_cancel())
            return True
        DB.update_user_settings(user_id, delay_min=delay_min, delay_max=delay_max)
        send_message(chat_id, f"✅ Задержка: {delay_min}-{delay_max} сек", kb_settings_menu())
        show_settings_menu(chat_id, user_id)
        return True

    # Cache TTL state
    if state == 'settings:cache_ttl':
        if text == '🔕 Отключить':
            DB.update_user_settings(user_id, mailing_cache_ttl=0)
            send_message(chat_id, "✅ Кэш рассылки отключён", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True
        ttl_map = {'7 дней': 7, '14 дней': 14, '30 дней': 30, '60 дней': 60, '90 дней': 90}
        if text in ttl_map:
            DB.update_user_settings(user_id, mailing_cache_ttl=ttl_map[text])
            send_message(chat_id, f"✅ Кэш: {ttl_map[text]} дней", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True

    # Auto blacklist state
    if state == 'settings:auto_blacklist':
        if text == '✅ Включить':
            DB.update_user_settings(user_id, auto_blacklist_enabled=True)
            send_message(chat_id, "✅ Авто-блокировка включена", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True
        if text == '❌ Отключить':
            DB.update_user_settings(user_id, auto_blacklist_enabled=False)
            send_message(chat_id, "✅ Авто-блокировка отключена", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True
        if text == '🛡 Настроить стоп-слова':
            show_stop_triggers(chat_id, user_id)
            return True

    # Stop triggers state
    if state == 'settings:stop_triggers':
        if text == '➕ Добавить слово':
            DB.set_user_state(user_id, 'settings:add_stop_word')
            send_message(chat_id,
                "🛡 <b>Добавление стоп-слова</b>\n"
                "Введите слово или фразу.\n"
                "При получении ответа с этим словом пользователь добавляется в ЧС.\n"
                "Примеры: <code>спам</code>, <code>не пиши</code>",
                kb_back_cancel()
            )
            return True
        if text == '📋 Список слов':
            show_stop_triggers_list(chat_id, user_id)
            return True

    # Add stop word state
    if state == 'settings:add_stop_word':
        word = text.strip().lower()
        if len(word) < 2:
            send_message(chat_id, "❌ Минимум 2 символа", kb_back_cancel())
            return True
        if len(word) > 100:
            send_message(chat_id, "❌ Максимум 100 символов", kb_back_cancel())
            return True
        result = DB.add_stop_trigger(user_id, word)
        if result:
            send_message(chat_id, f"✅ Стоп-слово «{word}» добавлено", kb_stop_triggers_menu())
        else:
            send_message(chat_id, "❌ Ошибка добавления", kb_stop_triggers_menu())
        DB.set_user_state(user_id, 'settings:stop_triggers')
        return True

    # Warmup settings state
    if state == 'settings:warmup':
        if text == '✅ Включить прогрев':
            DB.update_user_settings(user_id, warmup_before_mailing=True)
            send_message(chat_id, "✅ Прогрев включён", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True
        if text == '❌ Отключить':
            DB.update_user_settings(user_id, warmup_before_mailing=False)
            send_message(chat_id, "✅ Прогрев отключён", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True
        duration_map = {'⏱ 5 минут': 5, '⏱ 10 минут': 10, '⏱ 15 минут': 15}
        if text in duration_map:
            DB.update_user_settings(user_id, 
                warmup_before_mailing=True,
                warmup_duration_minutes=duration_map[text]
            )
            send_message(chat_id, f"✅ Прогрев: {duration_map[text]} минут", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True

    # ==================== NEW SETTINGS ====================
    # Risk tolerance state
    if state == 'settings:risk_tolerance':
        risk_map = {
            '🟢 Низкий': 'low',
            '🟡 Средний': 'medium',
            '🔴 Высокий': 'high'
        }
        if text in risk_map:
            DB.update_user_settings(user_id, risk_tolerance=risk_map[text])
            send_message(chat_id, f"✅ Риск-толерантность: {text}", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True

    # Herder settings state
    if state == 'settings:herder':
        return _handle_herder_settings(chat_id, user_id, text, saved)
    if state == 'settings:herder:strategy':
        return _handle_herder_strategy(chat_id, user_id, text, saved)
    if state == 'settings:herder:max_actions':
        return _handle_herder_max_actions(chat_id, user_id, text, saved)

    # Factory settings state
    if state == 'settings:factory':
        return _handle_factory_settings(chat_id, user_id, text, saved)
    if state == 'settings:factory:warmup_days':
        return _handle_factory_warmup_days(chat_id, user_id, text, saved)

    # AI settings state
    if state == 'settings:ai':
        return _handle_ai_settings(chat_id, user_id, text, saved)
    if state == 'settings:ai:temperature':
        return _handle_ai_temperature(chat_id, user_id, text, saved)

    # API keys state
    if state == 'settings:api_keys':
        return _handle_api_keys(chat_id, user_id, text, saved)
    if state == 'settings:api:yagpt':
        return _handle_api_yagpt(chat_id, user_id, text, saved)
    if state == 'settings:api:yagpt_folder':
        return _handle_api_yagpt_folder(chat_id, user_id, text, saved)
    if state == 'settings:api:onlinesim':
        return _handle_api_onlinesim(chat_id, user_id, text, saved)
    if state == 'settings:api:model':
        return _handle_model_selection(chat_id, user_id, text, saved)
    if state == 'settings:api:yagpt_model':
        return _handle_yagpt_model_selection(chat_id, user_id, text, saved)

    return False

def handle_settings_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle settings inline callbacks"""
    # Toggle stop trigger
    if data.startswith('togstop:'):
        trigger_id = int(data.split(':')[1])
        trigger = DB._select('stop_triggers', filters={'id': trigger_id}, single=True)
        if trigger:
            new_active = not trigger.get('is_active', True)
            DB._update('stop_triggers', {'is_active': new_active}, {'id': trigger_id})
        show_stop_triggers_list(chat_id, user_id)
        return True
    # Delete stop trigger
    if data.startswith('delstop:'):
        trigger_id = int(data.split(':')[1])
        DB.delete_stop_trigger(trigger_id)
        show_stop_triggers_list(chat_id, user_id)
        return True
    return False

# ==================== EXISTING SETTINGS VIEWS ====================
def show_quiet_hours(chat_id: int, user_id: int):
    """Show quiet hours settings"""
    DB.set_user_state(user_id, 'settings:quiet_hours')
    settings = DB.get_user_settings(user_id)
    qs = settings.get('quiet_hours_start')
    qe = settings.get('quiet_hours_end')
    current = f"Текущие: <b>{qs} - {qe} МСК</b>" if qs and qe else "Сейчас: <b>не установлены</b>"
    send_message(chat_id,
        f"🌙 <b>Тихие часы</b>\n"
        f"{current}\n"
        f"В тихие часы рассылки не отправляются.\n"
        f"⚠️ Время в московском часовом поясе (МСК)",
        kb_quiet_hours()
    )

def show_notifications(chat_id: int, user_id: int):
    """Show notifications settings"""
    DB.set_user_state(user_id, 'settings:notifications')
    settings = DB.get_user_settings(user_id)
    enabled = settings.get('notify_on_complete', True)
    status = "✅ <b>Включены</b>" if enabled else "❌ <b>Отключены</b>"
    send_message(chat_id,
        f"🔔 <b>Уведомления</b>\n"
        f"Статус: {status}\n"
        f"<b>Типы уведомлений:</b>\n"
        f"• Завершение парсинга/рассылки\n"
        f"• Ошибки и проблемы\n"
        f"• Негативные ответы\n"
        f"• Действия ботовода",
        kb_notifications()
    )

def show_delay_settings(chat_id: int, user_id: int):
    """Show delay settings"""
    DB.set_user_state(user_id, 'settings:delay')
    settings = DB.get_user_settings(user_id)
    delay_min = settings.get('delay_min', 30) or 30
    delay_max = settings.get('delay_max', 90) or 90
    send_message(chat_id,
        f"⏱ <b>Задержка между сообщениями</b>\n"
        f"Текущая: <b>{delay_min}-{delay_max} сек</b>\n"
        f"⚠️ <b>Рекомендации:</b>\n"
        f"• <b>5-15</b> — быстро, риск выше\n"
        f"• <b>15-45</b> — средний вариант\n"
        f"• <b>30-90</b> — оптимально\n"
        f"• <b>60-180</b> — безопасно",
        kb_delay_settings()
    )

def show_cache_settings(chat_id: int, user_id: int):
    """Show cache TTL settings"""
    DB.set_user_state(user_id, 'settings:cache_ttl')
    settings = DB.get_user_settings(user_id)
    ttl = settings.get('mailing_cache_ttl', 30) or 30
    status = f"<b>{ttl} дней</b>" if ttl > 0 else "<b>отключён</b>"
    send_message(chat_id,
        f"🗓 <b>Кэш рассылки</b>\n"
        f"Текущий TTL: {status}\n"
        f"Если пользователь получал рассылку в этот период —\n"
        f"он исключается из новых кампаний.",
        kb_cache_ttl()
    )

def show_auto_blacklist(chat_id: int, user_id: int):
    """Show auto blacklist settings"""
    DB.set_user_state(user_id, 'settings:auto_blacklist')
    settings = DB.get_user_settings(user_id)
    enabled = settings.get('auto_blacklist_enabled', True)
    triggers = DB.get_stop_triggers(user_id)
    active_count = sum(1 for t in triggers if t.get('is_active'))
    status = "✅ <b>Включена</b>" if enabled else "❌ <b>Отключена</b>"
    send_message(chat_id,
        f"🛡 <b>Авто-блокировка</b>\n"
        f"Статус: {status}\n"
        f"Стоп-слов: <b>{active_count}</b>\n"
        f"При ответе со стоп-словом пользователь\n"
        f"автоматически добавляется в ЧС.",
        kb_auto_blacklist()
    )

def show_stop_triggers(chat_id: int, user_id: int):
    """Show stop triggers menu"""
    DB.set_user_state(user_id, 'settings:stop_triggers')
    triggers = DB.get_stop_triggers(user_id)
    active = sum(1 for t in triggers if t.get('is_active'))
    total_hits = sum(t.get('hits_count', 0) or 0 for t in triggers)
    send_message(chat_id,
        f"🛡 <b>Стоп-слова</b>\n"
        f"Всего: <b>{len(triggers)}</b>\n"
        f"Активных: <b>{active}</b>\n"
        f"Срабатываний: <b>{total_hits}</b>",
        kb_stop_triggers_menu()
    )

def show_stop_triggers_list(chat_id: int, user_id: int):
    """Show list of stop triggers"""
    triggers = DB.get_stop_triggers(user_id)
    if not triggers:
        send_message(chat_id,
            "🛡 <b>Стоп-слова</b>\nСписок пуст.",
            kb_stop_triggers_menu()
        )
    else:
        send_message(chat_id,
            f"🛡 <b>Стоп-слова ({len(triggers)}):</b>\n"
            f"✅ — активно, ❌ — отключено",
            kb_inline_stop_triggers(triggers)
        )
        send_message(chat_id, "👆 Нажмите для управления", kb_stop_triggers_menu())

def show_warmup_settings(chat_id: int, user_id: int):
    """Show warmup settings"""
    DB.set_user_state(user_id, 'settings:warmup')
    settings = DB.get_user_settings(user_id)
    enabled = settings.get('warmup_before_mailing', False)
    duration = settings.get('warmup_duration_minutes', 5) or 5
    status = f"✅ <b>{duration} мин</b>" if enabled else "❌ <b>Отключён</b>"
    send_message(chat_id,
        f"🔥 <b>Прогрев перед рассылкой</b>\n"
        f"Статус: {status}\n"
        f"Аккаунты «прогреваются» перед рассылкой:\n"
        f"читают сообщения, имитируют активность.",
        kb_warmup_settings()
    )

# ==================== NEW SETTINGS VIEWS ====================
def show_risk_tolerance(chat_id: int, user_id: int):
    """Show risk tolerance settings"""
    DB.set_user_state(user_id, 'settings:risk_tolerance')
    settings = DB.get_user_settings(user_id)
    current = settings.get('risk_tolerance', 'medium')
    levels = {
        'low': ('🟢', 'Низкий', 'Максимальная безопасность, большие задержки'),
        'medium': ('🟡', 'Средний', 'Баланс скорости и безопасности'),
        'high': ('🔴', 'Высокий', 'Агрессивная работа, риск блокировок')
    }
    emoji, name, desc = levels.get(current, levels['medium'])
    send_message(chat_id,
        f"⚠️ <b>Риск-толерантность</b>\n"
        f"Текущий: {emoji} <b>{name}</b>\n"
        f"<i>{desc}</i>\n"
        f"<b>Влияет на:</b>\n"
        f"• Задержки между сообщениями\n"
        f"• Количество действий в час\n"
        f"• Агрессивность комментирования\n"
        f"• Скорость прогрева аккаунтов",
        kb_risk_tolerance()
    )

def show_herder_settings(chat_id: int, user_id: int):
    """Show herder (botovod) settings"""
    DB.set_user_state(user_id, 'settings:herder', {})
    settings = DB.get_user_settings(user_id)
    herder = settings.get('herder_settings', {})
    strategy_names = {
        'observer': '📖 Наблюдатель',
        'expert': '🧠 Эксперт',
        'support': '💪 Поддержка',
        'trendsetter': '🔥 Трендсеттер',
        'community': '👥 Комьюнити'
    }
    strategy = strategy_names.get(herder.get('default_strategy', 'observer'), '📖 Наблюдатель')
    max_actions = herder.get('max_actions_per_account', 50)
    coordinate = '✅' if herder.get('coordinate_discussions') else '❌'
    seasonal = '✅' if herder.get('seasonal_behavior', True) else '❌'
    quiet_threshold = herder.get('quiet_mode_threshold', 100)
    send_message(chat_id,
        f"🤖 <b>Настройки Ботовода</b>\n"
        f"🎯 Стратегия: <b>{strategy}</b>\n"
        f"📊 Макс. действий/аккаунт: <b>{max_actions}</b>\n"
        f"🗣 Координация обсуждений: {coordinate}\n"
        f"🌙 Сезонное поведение: {seasonal}\n"
        f"🔇 Тихий режим (порог): <b>{quiet_threshold}</b> подп.",
        reply_keyboard([
            ['🎯 Стратегия по умолчанию'],
            ['📊 Лимит действий', '🗣 Координация'],
            ['🌙 Сезонное поведение', '🔇 Тихий режим'],
            ['◀️ Назад']
        ])
    )

def _handle_herder_settings(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle herder settings"""
    settings = DB.get_user_settings(user_id)
    herder = settings.get('herder_settings', {})
    if text == '🎯 Стратегия по умолчанию':
        DB.set_user_state(user_id, 'settings:herder:strategy', {})
        send_message(chat_id, "Выберите стратегию по умолчанию:",
            reply_keyboard([
                ['📖 Наблюдатель', '🧠 Эксперт'],
                ['💪 Поддержка', '🔥 Трендсеттер'],
                ['👥 Комьюнити'],
                ['◀️ Назад']
            ])
        )
        return True
    if text == '📊 Лимит действий':
        DB.set_user_state(user_id, 'settings:herder:max_actions', {})
        send_message(chat_id,
            "Максимум действий на аккаунт в день:",
            reply_keyboard([
                ['25', '50', '75'],
                ['100', '150'],
                ['◀️ Назад']
            ])
        )
        return True
    if text == '🗣 Координация':
        herder['coordinate_discussions'] = not herder.get('coordinate_discussions', False)
        DB.update_user_settings(user_id, herder_settings=herder)
        status = '✅ включена' if herder['coordinate_discussions'] else '❌ отключена'
        send_message(chat_id, f"Координация обсуждений: {status}", kb_settings_menu())
        show_herder_settings(chat_id, user_id)
        return True
    if text == '🌙 Сезонное поведение':
        herder['seasonal_behavior'] = not herder.get('seasonal_behavior', True)
        DB.update_user_settings(user_id, herder_settings=herder)
        status = '✅ включено' if herder['seasonal_behavior'] else '❌ отключено'
        send_message(chat_id, f"Сезонное поведение: {status}", kb_settings_menu())
        show_herder_settings(chat_id, user_id)
        return True
    if text == '🔇 Тихий режим':
        send_message(chat_id,
            "Порог подписчиков для тихого режима:\n"
            "(каналы с меньшим числом подписчиков получают меньше активности)",
            reply_keyboard([
                ['50', '100', '200'],
                ['500', '1000'],
                ['◀️ Назад']
            ])
        )
        DB.set_user_state(user_id, 'settings:herder:quiet_threshold', {})
        return True
    return False

def _handle_herder_strategy(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle herder strategy selection"""
    strategy_map = {
        '📖 Наблюдатель': 'observer',
        '🧠 Эксперт': 'expert',
        '💪 Поддержка': 'support',
        '🔥 Трендсеттер': 'trendsetter',
        '👥 Комьюнити': 'community'
    }
    if text in strategy_map:
        settings = DB.get_user_settings(user_id)
        herder = settings.get('herder_settings', {})
        herder['default_strategy'] = strategy_map[text]
        DB.update_user_settings(user_id, herder_settings=herder)
        send_message(chat_id, f"✅ Стратегия: {text}", kb_settings_menu())
        show_herder_settings(chat_id, user_id)
        return True
    if text == '◀️ Назад':
        show_herder_settings(chat_id, user_id)
        return True
    return False

def _handle_herder_max_actions(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle herder max actions"""
    try:
        max_actions = int(text)
        if max_actions < 10 or max_actions > 200:
            send_message(chat_id, "❌ Введите число от 10 до 200", kb_back_cancel())
            return True
        settings = DB.get_user_settings(user_id)
        herder = settings.get('herder_settings', {})
        herder['max_actions_per_account'] = max_actions
        DB.update_user_settings(user_id, herder_settings=herder)
        send_message(chat_id, f"✅ Лимит действий: {max_actions}", kb_settings_menu())
        show_herder_settings(chat_id, user_id)
        return True
    except:
        return False

def _handle_herder_quiet_threshold(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle quiet threshold input"""
    try:
        threshold = int(text)
        settings = DB.get_user_settings(user_id)
        herder = settings.get('herder_settings', {})
        herder['quiet_mode_threshold'] = threshold
        DB.update_user_settings(user_id, herder_settings=herder)
        send_message(chat_id, f"✅ Порог тихого режима: {threshold} подписчиков", kb_settings_menu())
        show_herder_settings(chat_id, user_id)
        return True
    except:
        send_message(chat_id, "❌ Введите число", kb_back_cancel())
        return True

def show_factory_settings(chat_id: int, user_id: int):
    """Show factory settings"""
    DB.set_user_state(user_id, 'settings:factory', {})
    settings = DB.get_user_settings(user_id)
    factory = settings.get('factory_settings', {})
    warmup_days = factory.get('default_warmup_days', 5)
    auto_proxy = '✅' if factory.get('auto_proxy_assignment', True) else '❌'
    send_message(chat_id,
        f"🏭 <b>Настройки Фабрики</b>\n"
        f"📅 Прогрев по умолчанию: <b>{warmup_days} дней</b>\n"
        f"🌐 Авто-назначение прокси: {auto_proxy}",
        reply_keyboard([
            ['📅 Длительность прогрева'],
            ['🌐 Авто-прокси'],
            ['◀️ Назад']
        ])
    )

def _handle_factory_settings(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle factory settings"""
    if text == '📅 Длительность прогрева':
        DB.set_user_state(user_id, 'settings:factory:warmup_days', {})
        send_message(chat_id,
            "Длительность прогрева по умолчанию:",
            reply_keyboard([
                ['3 дня', '5 дней', '7 дней'],
                ['14 дней'],
                ['◀️ Назад']
            ])
        )
        return True
    if text == '🌐 Авто-прокси':
        settings = DB.get_user_settings(user_id)
        factory = settings.get('factory_settings', {})
        factory['auto_proxy_assignment'] = not factory.get('auto_proxy_assignment', True)
        DB.update_user_settings(user_id, factory_settings=factory)
        status = '✅ включено' if factory['auto_proxy_assignment'] else '❌ отключено'
        send_message(chat_id, f"Авто-назначение прокси: {status}", kb_settings_menu())
        show_factory_settings(chat_id, user_id)
        return True
    return False

def _handle_factory_warmup_days(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle factory warmup days"""
    days_map = {'3 дня': 3, '5 дней': 5, '7 дней': 7, '14 дней': 14}
    if text in days_map:
        settings = DB.get_user_settings(user_id)
        factory = settings.get('factory_settings', {})
        factory['default_warmup_days'] = days_map[text]
        DB.update_user_settings(user_id, factory_settings=factory)
        send_message(chat_id, f"✅ Прогрев: {text}", kb_settings_menu())
        show_factory_settings(chat_id, user_id)
        return True
    if text == '◀️ Назад':
        show_factory_settings(chat_id, user_id)
        return True
    return False

def show_ai_settings(chat_id: int, user_id: int):
    """Show AI and learning settings"""
    DB.set_user_state(user_id, 'settings:ai', {})
    settings = DB.get_user_settings(user_id)
    learning = '✅ Вкл' if settings.get('learning_mode', True) else '❌ Выкл'
    auto_recovery = '✅ Вкл' if settings.get('auto_recovery_mode', True) else '❌ Выкл'
    temperature = settings.get('gpt_temperature', 0.7)
    knowledge = DB.get_herder_knowledge_stats(user_id)
    send_message(chat_id,
        f"🧠 <b>ИИ и обучение</b>\n"
        f"📚 Режим обучения: {learning}\n"
        f"🔄 Авто-восстановление: {auto_recovery}\n"
        f"🌡 Температура GPT: <b>{temperature}</b>\n"
        f"<b>База знаний:</b>\n"
        f"├ Плохих фраз: {knowledge.get('bad_phrases', 0)}\n"
        f"├ Хороших паттернов: {knowledge.get('good_patterns', 0)}\n"
        f"└ Всего записей: {knowledge.get('total', 0)}",
        reply_keyboard([
            ['📚 Режим обучения', '🔄 Авто-восстановление'],
            ['🌡 Температура GPT'],
            ['🗑 Очистить базу знаний'],
            ['◀️ Назад']
        ])
    )

def _handle_ai_settings(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle AI settings"""
    if text == '📚 Режим обучения':
        settings = DB.get_user_settings(user_id)
        current = settings.get('learning_mode', True)
        DB.update_user_settings(user_id, learning_mode=not current)
        status = '✅ включён' if not current else '❌ отключён'
        send_message(chat_id, f"Режим обучения: {status}", kb_settings_menu())
        show_ai_settings(chat_id, user_id)
        return True
    if text == '🔄 Авто-восстановление':
        settings = DB.get_user_settings(user_id)
        current = settings.get('auto_recovery_mode', True)
        DB.update_user_settings(user_id, auto_recovery_mode=not current)
        status = '✅ включено' if not current else '❌ отключено'
        send_message(chat_id, f"Авто-восстановление: {status}", kb_settings_menu())
        show_ai_settings(chat_id, user_id)
        return True
    if text == '🌡 Температура GPT':
        DB.set_user_state(user_id, 'settings:ai:temperature', {})
        send_message(chat_id,
            "🌡 <b>Температура GPT</b>\n"
            "Влияет на креативность генерации:\n"
            "• 0.3 — точный, предсказуемый\n"
            "• 0.7 — баланс\n"
            "• 1.0 — креативный, разнообразный",
            kb_gpt_temperature()
        )
        return True
    if text == '🗑 Очистить базу знаний':
        DB.clear_herder_knowledge(user_id)
        send_message(chat_id, "✅ База знаний очищена", kb_settings_menu())
        show_ai_settings(chat_id, user_id)
        return True
    return False

def _handle_ai_temperature(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle AI temperature setting"""
    temp_map = {
        '0.3 (точный)': 0.3,
        '0.5': 0.5,
        '0.7 (баланс)': 0.7,
        '0.9': 0.9,
        '1.0 (креативный)': 1.0
    }
    if text in temp_map:
        DB.update_user_settings(user_id, gpt_temperature=temp_map[text])
        send_message(chat_id, f"✅ Температура GPT: {temp_map[text]}", kb_settings_menu())
        show_ai_settings(chat_id, user_id)
        return True
    if text == '◀️ Назад':
        show_ai_settings(chat_id, user_id)
        return True
    return False

def show_api_keys(chat_id: int, user_id: int):
    """Show API keys settings"""
    DB.set_user_state(user_id, 'settings:api_keys', {})
    settings = DB.get_user_settings(user_id)
    yagpt_key = settings.get('yagpt_api_key')
    yagpt_status = '✅ Настроен' if yagpt_key else '❌ Не настроен'
    yagpt_preview = f"...{yagpt_key[-8:]}" if yagpt_key and len(yagpt_key) > 8 else ''
    
    # Model selection
    yagpt_model = settings.get('yandex_gpt_model')
    if not yagpt_model or not isinstance(yagpt_model, str):
        yagpt_model = 'yandexgpt-5-lite'
    model_names = {
        'aliceai-llm/latest': '🆕 Alice AI LLM',
        'yandexgpt-5.1/latest': 'YandexGPT 5.1 Pro',
        'yandexgpt-5-pro/latest': 'YandexGPT 5 Pro',
        'yandexgpt-5-lite/latest': 'YandexGPT 5 Lite',
        'yandexgpt-4-lite/latest': 'YandexGPT 4 Lite',
        'aliceai-llm': '🆕 Alice AI LLM',  # Legacy support
        'yandexgpt-5.1': 'YandexGPT 5.1 Pro',
        'yandexgpt-5-pro': 'YandexGPT 5 Pro',
        'yandexgpt-5-lite': 'YandexGPT 5 Lite',
        'yandexgpt-4-lite': 'YandexGPT 4 Lite',
        'yandexgpt-lite': 'YandexGPT Lite (legacy)',
    }
    # Normalize model name for display
    model_display = model_names.get(yagpt_model, yagpt_model)
    if not model_display or model_display == yagpt_model:
        # Try without /latest suffix
        model_base = yagpt_model.replace('/latest', '')
        model_display = model_names.get(model_base, yagpt_model)
    
    onlinesim_key = settings.get('onlinesim_api_key')
    onlinesim_status = '✅ Настроен' if onlinesim_key else '❌ Не настроен'
    send_message(chat_id,
        f"🔑 <b>API ключи</b>\n\n"
        f"<b>🧠 Yandex GPT:</b> {yagpt_status}\n"
        f"   Модель: <b>{model_display}</b>\n"
        f"   {f'Ключ: {yagpt_preview}' if yagpt_preview else ''}\n\n"
        f"<b>📱 OnlineSim:</b> {onlinesim_status}\n"
        f"   Для автоматического создания аккаунтов\n\n"
        f"<b>🌐 Прокси:</b> (в разработке)",
        kb_api_keys(has_yagpt_key=bool(yagpt_key))
    )

def _handle_api_keys(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle API keys menu"""
    if text == '🔑 Yandex GPT' or text == '✏️ Изменить Yandex GPT':
        DB.set_user_state(user_id, 'settings:api:yagpt', {})
        send_message(chat_id,
            "🔑 <b>Настройка Yandex GPT</b>\n"
            "Введите API ключ от Yandex Cloud:\n"
            "Получить: https://console.cloud.yandex.ru/\n"
            "Раздел: API Keys\n"
            "⚠️ Ключ сохраняется безопасно",
            kb_back_cancel()
        )
        return True
    if text == '🧠 Выбор модели':
        show_model_selection(chat_id, user_id)
        return True
    if text == '📱 OnlineSim':
        DB.set_user_state(user_id, 'settings:api:onlinesim', {})
        send_message(chat_id,
            "📱 <b>Настройка OnlineSim</b>\n"
            "Введите API ключ от onlinesim.io:\n"
            "Получить: https://onlinesim.io/api\n"
            "⚠️ Используется для автоматического получения номеров",
            kb_back_cancel()
        )
        return True
    if text == '🌐 Прокси':
        settings = DB.get_user_settings(user_id)
        yagpt_key = settings.get('yagpt_api_key')
        send_message(chat_id,
            "🌐 <b>Прокси</b>\n"
            "Функция управления прокси в разработке.\n"
            "Пока вы можете добавлять прокси вручную\n"
            "при создании аккаунтов.",
            kb_api_keys(has_yagpt_key=bool(yagpt_key))
        )
        return True
    return False

def _handle_api_yagpt(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle YaGPT API key input"""
    api_key = text.strip()
    if len(api_key) < 10:
        send_message(chat_id, "❌ Неверный формат ключа", kb_back_cancel())
        return True
    DB.set_user_state(user_id, 'settings:api:yagpt_folder', {'yagpt_key': api_key})
    send_message(chat_id,
        "✅ API ключ принят!\n"
        "Теперь введите <b>Folder ID</b> из Yandex Cloud:\n"
        "Найти: https://console.cloud.yandex.ru/\n"
        "Раздел: Каталог → ID",
        kb_back_cancel()
    )
    return True

def _handle_api_yagpt_folder(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle YaGPT folder ID input"""
    folder_id = text.strip()
    if len(folder_id) < 10:
        send_message(chat_id, "❌ Неверный формат Folder ID", kb_back_cancel())
        return True
    # Save folder, then ask for model selection
    saved['yagpt_folder'] = folder_id
    DB.set_user_state(user_id, 'settings:api:yagpt_model', saved)
    send_message(chat_id,
        "✅ API ключ и Folder ID приняты!\n\n"
        "Теперь выберите модель GPT:\n\n"
        "🆕 <b>Alice AI LLM</b> — новейшая, лучшее качество\n"
        "📊 <b>YandexGPT 5.1 Pro</b> — продвинутая\n"
        "📊 <b>YandexGPT 5 Pro</b> — высокое качество\n"
        "⚡ <b>YandexGPT 5 Lite</b> — быстрая, экономичная\n"
        "📦 <b>YandexGPT 4 Lite</b> — предыдущее поколение",
        kb_yandex_models()
    )
    return True

def _handle_api_onlinesim(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle OnlineSim API key input"""
    api_key = text.strip()
    if len(api_key) < 10:
        send_message(chat_id, "❌ Неверный формат ключа", kb_back_cancel())
        return True
    DB.update_user_settings(user_id, onlinesim_api_key=api_key)
    send_message(chat_id,
        "✅ <b>OnlineSim настроен!</b>\n"
        "Теперь доступно:\n"
        "• Автоматическое создание аккаунтов\n"
        "• Получение номеров из разных стран",
        kb_api_keys()
    )
    show_api_keys(chat_id, user_id)
    return True


# ==================== YANDEX MODEL SELECTION ====================

def show_model_selection(chat_id: int, user_id: int):
    """Show Yandex GPT model selection (standalone)"""
    DB.set_user_state(user_id, 'settings:api:model', {})
    settings = DB.get_user_settings(user_id)
    current = settings.get('yandex_gpt_model', 'yandexgpt-5-lite/latest')
    
    # Normalize model name for display
    model_base = current.replace('/latest', '') if '/latest' in current else current
    model_info = {
        'aliceai-llm': ('🆕 Alice AI LLM', 'Новейшая модель, лучшее качество'),
        'yandexgpt-5.1': ('YandexGPT 5.1 Pro', 'Продвинутая Pro-версия'),
        'yandexgpt-5-pro': ('YandexGPT 5 Pro', 'Высокое качество, Pro'),
        'yandexgpt-5-lite': ('YandexGPT 5 Lite', 'Быстрая, экономичная'),
        'yandexgpt-4-lite': ('YandexGPT 4 Lite', 'Предыдущее поколение'),
    }
    
    current_name, current_desc = model_info.get(model_base, (current, ''))
    
    send_message(chat_id,
        f"🧠 <b>Выбор модели YandexGPT</b>\n\n"
        f"Текущая: <b>{current_name}</b>\n"
        f"<i>{current_desc}</i>\n\n"
        f"<b>Доступные модели:</b>\n"
        f"🆕 <b>Alice AI LLM</b> — новейшая, лучшее качество\n"
        f"📊 <b>YandexGPT 5.1 Pro</b> — продвинутая\n"
        f"📊 <b>YandexGPT 5 Pro</b> — высокое качество\n"
        f"⚡ <b>YandexGPT 5 Lite</b> — быстрая, экономичная\n"
        f"📦 <b>YandexGPT 4 Lite</b> — предыдущее поколение\n\n"
        f"💡 Модель используется для семантического парсинга,\n"
        f"генерации комментариев и контента.",
        kb_yandex_models()
    )


def _handle_model_selection(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle Yandex model selection (standalone, without key/folder change)"""
    model_map = {
        '🆕 Alice AI LLM': 'aliceai-llm/latest',
        'YandexGPT 5.1 Pro': 'yandexgpt-5.1/latest',
        'YandexGPT 5 Pro': 'yandexgpt-5-pro/latest',
        'YandexGPT 5 Lite': 'yandexgpt-5-lite/latest',
        'YandexGPT 4 Lite': 'yandexgpt-4-lite/latest',
    }
    
    if text in model_map:
        model_id = model_map[text]
        DB.update_user_settings(user_id, yandex_gpt_model=model_id)
        settings = DB.get_user_settings(user_id)
        yagpt_key = settings.get('yagpt_api_key')
        send_message(chat_id,
            f"✅ <b>Модель изменена!</b>\n\n"
            f"Выбрана: <b>{text}</b>\n\n"
            f"Теперь эта модель будет использоваться для:\n"
            f"• Семантического парсинга\n"
            f"• Генерации комментариев\n"
            f"• Создания контента",
            kb_api_keys(has_yagpt_key=bool(yagpt_key))
        )
        show_api_keys(chat_id, user_id)
        return True
    
    if text == '◀️ Назад':
        show_api_keys(chat_id, user_id)
        return True
    
    return False

def _handle_yagpt_model_selection(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle Yandex model selection during initial setup or change"""
    model_map = {
        '🆕 Alice AI LLM': 'aliceai-llm/latest',
        'YandexGPT 5.1 Pro': 'yandexgpt-5.1/latest',
        'YandexGPT 5 Pro': 'yandexgpt-5-pro/latest',
        'YandexGPT 5 Lite': 'yandexgpt-5-lite/latest',
        'YandexGPT 4 Lite': 'yandexgpt-4-lite/latest',
    }
    
    if text in model_map:
        model_id = model_map[text]
        # Save all: key, folder, and model
        DB.update_user_settings(user_id, 
            yagpt_api_key=saved.get('yagpt_key'),
            yagpt_folder_id=saved.get('yagpt_folder'),
            yandex_gpt_model=model_id
        )
        send_message(chat_id,
            f"✅ <b>Yandex GPT полностью настроен!</b>\n\n"
            f"API ключ: ✅\n"
            f"Folder ID: ✅\n"
            f"Модель: <b>{text}</b>\n\n"
            f"Теперь доступны:\n"
            f"• Генерация комментариев в Ботоводе\n"
            f"• Генерация постов в Контент-менеджере\n"
            f"• Семантический парсинг\n"
            f"• Анализ трендов и эмоций",
            kb_api_keys(has_yagpt_key=True)
        )
        show_api_keys(chat_id, user_id)
        return True
    
    if text == '◀️ Назад':
        # Go back to folder input
        DB.set_user_state(user_id, 'settings:api:yagpt_folder', saved)
        send_message(chat_id,
            "Введите <b>Folder ID</b> из Yandex Cloud:\n"
            "Найти: https://console.cloud.yandex.ru/\n"
            "Раздел: Каталог → ID",
            kb_back_cancel()
        )
        return True
    
    return False


