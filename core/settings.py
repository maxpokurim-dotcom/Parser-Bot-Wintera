"""
Settings handlers - Extended v2.0
With cache TTL, auto-blacklist, warmup settings
"""
import re
import logging
from core.db import DB
from core.telegram import send_message
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel,
    kb_settings_menu, kb_quiet_hours, kb_notifications, kb_delay_settings,
    kb_cache_ttl, kb_auto_blacklist, kb_warmup_settings,
    kb_stop_triggers_menu, kb_inline_stop_triggers
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_QUIET_HOURS = '🌙 Тихие часы'
BTN_NOTIFICATIONS = '🔔 Уведомления'
BTN_DELAY = '⏱ Задержка рассылки'
BTN_CACHE_TTL = '🗓 Кэш рассылки'
BTN_AUTO_BLACKLIST = '🛡 Авто-блокировка'
BTN_WARMUP = '🔥 Прогрев'
BTN_SET = '⏰ Установить'
BTN_DISABLE = '🔕 Отключить'
BTN_ENABLE = '🔔 Включить'
BTN_CUSTOM_DELAY = '📝 Свой диапазон'
BTN_STOP_WORDS = '🛡 Настроить стоп-слова'
BTN_ADD_WORD = '➕ Добавить слово'
BTN_LIST_WORDS = '📋 Список слов'


def show_settings_menu(chat_id: int, user_id: int):
    """Show settings menu"""
    DB.set_user_state(user_id, 'settings:menu')
    
    settings = DB.get_user_settings(user_id)
    qs = settings.get('quiet_hours_start')
    qe = settings.get('quiet_hours_end')
    quiet = f"{qs} - {qe}" if qs and qe else "не установлены"
    notify = '✅' if settings.get('notify_on_complete', True) else '❌'
    delay_min = settings.get('delay_min', 30) or 30
    delay_max = settings.get('delay_max', 90) or 90
    cache_ttl = settings.get('mailing_cache_ttl', 30) or 30
    auto_bl = '✅' if settings.get('auto_blacklist_enabled', True) else '❌'
    warmup = '✅' if settings.get('warmup_before_mailing', False) else '❌'
    
    send_message(chat_id,
        f"⚙️ <b>Настройки</b>\n\n"
        f"🌙 <b>Тихие часы:</b> {quiet}\n"
        f"🔔 <b>Уведомления:</b> {notify}\n"
        f"⏱ <b>Задержка:</b> {delay_min}-{delay_max} сек\n"
        f"🗓 <b>Кэш рассылки:</b> {cache_ttl} дней\n"
        f"🛡 <b>Авто-блокировка:</b> {auto_bl}\n"
        f"🔥 <b>Прогрев:</b> {warmup}\n\n"
        f"<i>В тихие часы рассылки не отправляются</i>",
        kb_settings_menu()
    )


def handle_settings(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle settings states. Returns True if handled."""
    
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Действие отменено")
        return True
    
    if text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return True
    
    if text == BTN_BACK:
        if state == 'settings:menu':
            show_main_menu(chat_id, user_id)
        elif state == 'settings:stop_triggers':
            show_auto_blacklist(chat_id, user_id)
        else:
            show_settings_menu(chat_id, user_id)
        return True
    
    # Menu state
    if state == 'settings:menu':
        if text == BTN_QUIET_HOURS:
            show_quiet_hours(chat_id, user_id)
            return True
        if text == BTN_NOTIFICATIONS:
            show_notifications(chat_id, user_id)
            return True
        if text == BTN_DELAY:
            show_delay_settings(chat_id, user_id)
            return True
        if text == BTN_CACHE_TTL:
            show_cache_settings(chat_id, user_id)
            return True
        if text == BTN_AUTO_BLACKLIST:
            show_auto_blacklist(chat_id, user_id)
            return True
        if text == BTN_WARMUP:
            show_warmup_settings(chat_id, user_id)
            return True
    
    # Quiet hours state
    if state == 'settings:quiet_hours':
        if text == BTN_SET or text == '⏰ Установить':
            DB.set_user_state(user_id, 'settings:quiet_hours_input')
            send_message(chat_id,
                "🌙 <b>Установка тихих часов</b>\n\n"
                "Введите диапазон в формате:\n"
                "<code>23:00-08:00</code>\n\n"
                "В это время рассылки не будут отправляться.",
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
        send_message(chat_id, f"✅ Тихие часы установлены: {sh:02d}:{sm:02d} - {eh:02d}:{em:02d}", kb_settings_menu())
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
                "⏱ <b>Своя задержка</b>\n\n"
                "Введите диапазон в формате:\n"
                "<code>мин-макс</code>\n\n"
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
            send_message(chat_id, f"✅ Задержка установлена: {delay_min}-{delay_max} сек", kb_settings_menu())
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
            send_message(chat_id, "❌ Задержка должна быть от 1 до 600 секунд", kb_back_cancel())
            return True
        
        DB.update_user_settings(user_id, delay_min=delay_min, delay_max=delay_max)
        send_message(chat_id, f"✅ Задержка установлена: {delay_min}-{delay_max} сек", kb_settings_menu())
        show_settings_menu(chat_id, user_id)
        return True
    
    # Cache TTL state
    if state == 'settings:cache_ttl':
        if text == '🔕 Отключить':
            DB.update_user_settings(user_id, mailing_cache_ttl=0)
            send_message(chat_id, "✅ Кэш рассылки отключён", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True
        
        ttl_map = {
            '7 дней': 7,
            '14 дней': 14,
            '30 дней': 30,
            '60 дней': 60,
            '90 дней': 90
        }
        
        if text in ttl_map:
            DB.update_user_settings(user_id, mailing_cache_ttl=ttl_map[text])
            send_message(chat_id, f"✅ Кэш рассылки: {ttl_map[text]} дней", kb_settings_menu())
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
                "🛡 <b>Добавление стоп-слова</b>\n\n"
                "Введите слово или фразу.\n"
                "При получении сообщения с этим словом пользователь будет добавлен в чёрный список.\n\n"
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
        
        duration_map = {
            '⏱ 5 минут': 5,
            '⏱ 10 минут': 10,
            '⏱ 15 минут': 15
        }
        
        if text in duration_map:
            DB.update_user_settings(user_id, 
                warmup_before_mailing=True,
                warmup_duration_minutes=duration_map[text]
            )
            send_message(chat_id, f"✅ Прогрев: {duration_map[text]} минут перед рассылкой", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True
    
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


def show_quiet_hours(chat_id: int, user_id: int):
    """Show quiet hours settings"""
    DB.set_user_state(user_id, 'settings:quiet_hours')
    
    settings = DB.get_user_settings(user_id)
    qs = settings.get('quiet_hours_start')
    qe = settings.get('quiet_hours_end')
    
    current = f"Текущие: <b>{qs} - {qe}</b>" if qs and qe else "Сейчас: <b>не установлены</b>"
    
    send_message(chat_id,
        f"🌙 <b>Тихие часы</b>\n\n"
        f"{current}\n\n"
        f"<b>Что это?</b>\n"
        f"В тихие часы рассылки автоматически приостанавливаются. "
        f"Это полезно, чтобы не отправлять сообщения ночью.\n\n"
        f"<i>Время указывается в UTC</i>",
        kb_quiet_hours()
    )


def show_notifications(chat_id: int, user_id: int):
    """Show notifications settings"""
    DB.set_user_state(user_id, 'settings:notifications')
    
    settings = DB.get_user_settings(user_id)
    enabled = settings.get('notify_on_complete', True)
    
    status = "✅ <b>Включены</b>" if enabled else "❌ <b>Отключены</b>"
    
    send_message(chat_id,
        f"🔔 <b>Уведомления</b>\n\n"
        f"Статус: {status}\n\n"
        f"<b>Какие уведомления приходят:</b>\n"
        f"• Завершение парсинга\n"
        f"• Прогресс рассылки\n"
        f"• Завершение рассылки\n"
        f"• Ошибки и проблемы с аккаунтами\n"
        f"• Негативные ответы пользователей",
        kb_notifications()
    )


def show_delay_settings(chat_id: int, user_id: int):
    """Show delay settings"""
    DB.set_user_state(user_id, 'settings:delay')
    
    settings = DB.get_user_settings(user_id)
    delay_min = settings.get('delay_min', 30) or 30
    delay_max = settings.get('delay_max', 90) or 90
    
    send_message(chat_id,
        f"⏱ <b>Задержка между сообщениями</b>\n\n"
        f"Текущая: <b>{delay_min}-{delay_max} сек</b>\n\n"
        f"Задержка будет случайной в выбранном диапазоне.\n\n"
        f"⚠️ <b>Рекомендации:</b>\n"
        f"• <b>5-15 сек</b> — быстро, но риск бана выше\n"
        f"• <b>15-45 сек</b> — средний вариант\n"
        f"• <b>30-90 сек</b> — оптимально для большинства\n"
        f"• <b>60-180 сек</b> — безопасно, но медленно\n\n"
        f"<i>При включённых адаптивных задержках система сама корректирует интервалы</i>",
        kb_delay_settings()
    )


def show_cache_settings(chat_id: int, user_id: int):
    """Show cache TTL settings"""
    DB.set_user_state(user_id, 'settings:cache_ttl')
    
    settings = DB.get_user_settings(user_id)
    ttl = settings.get('mailing_cache_ttl', 30) or 30
    
    status = f"<b>{ttl} дней</b>" if ttl > 0 else "<b>отключён</b>"
    
    send_message(chat_id,
        f"🗓 <b>Кэш рассылки</b>\n\n"
        f"Текущий TTL: {status}\n\n"
        f"<b>Что это?</b>\n"
        f"Если пользователь уже получал от вас рассылку в течение указанного "
        f"периода — он будет временно исключён из новых кампаний.\n\n"
        f"<b>Преимущества:</b>\n"
        f"• Повышает вовлечённость\n"
        f"• Снижает количество жалоб\n"
        f"• Уменьшает риск блокировок",
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
        f"🛡 <b>Авто-блокировка</b>\n\n"
        f"Статус: {status}\n"
        f"Активных стоп-слов: <b>{active_count}</b>\n\n"
        f"<b>Что это?</b>\n"
        f"При получении ответа со стоп-словом (например, «спам», «стоп») "
        f"пользователь автоматически добавляется в чёрный список.\n\n"
        f"<b>Это защищает от:</b>\n"
        f"• Жалоб на спам\n"
        f"• Блокировок аккаунтов\n"
        f"• Негативной реакции",
        kb_auto_blacklist()
    )


def show_stop_triggers(chat_id: int, user_id: int):
    """Show stop triggers menu"""
    DB.set_user_state(user_id, 'settings:stop_triggers')
    
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


def show_warmup_settings(chat_id: int, user_id: int):
    """Show warmup settings"""
    DB.set_user_state(user_id, 'settings:warmup')
    
    settings = DB.get_user_settings(user_id)
    enabled = settings.get('warmup_before_mailing', False)
    duration = settings.get('warmup_duration_minutes', 5) or 5
    
    status = f"✅ <b>Включён ({duration} мин)</b>" if enabled else "❌ <b>Отключён</b>"
    
    send_message(chat_id,
        f"🔥 <b>Прогрев аккаунтов</b>\n\n"
        f"Статус: {status}\n\n"
        f"<b>Что это?</b>\n"
        f"Перед началом рассылки аккаунты автоматически «прогреваются»:\n"
        f"• Читают сообщения в чатах\n"
        f"• Смотрят профили\n"
        f"• Имитируют живую активность\n\n"
        f"<b>Это снижает риск:</b>\n"
        f"• Shadow Ban\n"
        f"• Быстрых блокировок\n"
        f"• Flood Wait при старте\n\n"
        f"<i>Чаты для прогрева берутся из названия аудитории</i>",
        kb_warmup_settings()
    )
