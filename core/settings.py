"""
Settings handlers
Static menu version
"""
import re
import logging
from core.db import DB
from core.telegram import send_message
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel,
    kb_settings_menu, kb_quiet_hours, kb_notifications, kb_delay_settings
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_QUIET_HOURS = '🌙 Тихие часы'
BTN_NOTIFICATIONS = '🔔 Уведомления'
BTN_DELAY = '⏱ Задержка рассылки'
BTN_SET = '⏰ Установить'
BTN_DISABLE = '🔕 Отключить'
BTN_ENABLE = '🔔 Включить'
BTN_CUSTOM_DELAY = '📝 Свой диапазон'


def show_settings_menu(chat_id: int, user_id: int):
    """Show settings menu"""
    DB.set_user_state(user_id, 'settings:menu')
    
    settings = DB.get_user_settings(user_id)
    qs = settings.get('quiet_hours_start')
    qe = settings.get('quiet_hours_end')
    quiet = f"{qs} - {qe}" if qs and qe else "не установлены"
    notify = '✅ Включены' if settings.get('notify_on_complete', True) else '❌ Отключены'
    delay_min = settings.get('delay_min', 30) or 30
    delay_max = settings.get('delay_max', 90) or 90
    
    send_message(chat_id,
        f"⚙️ <b>Настройки</b>\n\n"
        f"🌙 <b>Тихие часы:</b> {quiet}\n"
        f"🔔 <b>Уведомления:</b> {notify}\n"
        f"⏱ <b>Задержка рассылки:</b> {delay_min}-{delay_max} сек\n\n"
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
    
    # Quiet hours state
    if state == 'settings:quiet_hours':
        if text == BTN_SET:
            DB.set_user_state(user_id, 'settings:quiet_hours_input')
            send_message(chat_id,
                "🌙 <b>Установка тихих часов</b>\n\n"
                "Введите диапазон в формате:\n"
                "<code>23:00-08:00</code>\n\n"
                "В это время рассылки не будут отправляться.",
                kb_back_cancel()
            )
            return True
        if text == BTN_DISABLE:
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
        if text == BTN_ENABLE:
            DB.update_user_settings(user_id, notify_on_complete=True, notify_on_error=True)
            send_message(chat_id, "✅ Уведомления включены", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True
        if text == BTN_DISABLE:
            DB.update_user_settings(user_id, notify_on_complete=False, notify_on_error=False)
            send_message(chat_id, "✅ Уведомления отключены", kb_settings_menu())
            show_settings_menu(chat_id, user_id)
            return True
    
    # Delay settings state
    if state == 'settings:delay':
        if text == BTN_CUSTOM_DELAY:
            DB.set_user_state(user_id, 'settings:delay_input')
            send_message(chat_id,
                "⏱ <b>Своя задержка</b>\n\n"
                "Введите диапазон в формате:\n"
                "<code>мин-макс</code>\n\n"
                "Например: <code>30-90</code> (секунды)",
                kb_back_cancel()
            )
            return True
        
        # Preset delays
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
        f"• Прогресс рассылки (каждые 10 сообщений)\n"
        f"• Завершение рассылки\n"
        f"• Ошибки и проблемы с аккаунтами\n"
        f"• Восстановление аккаунтов после ограничений",
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
        f"• <b>60-180 сек</b> — безопасно, но медленно",
        kb_delay_settings()
    )
