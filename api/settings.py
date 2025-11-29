# api/settings.py
"""
Settings handlers
"""
import re
from api.db import DB
from api.telegram import edit_message, send_message
from api.keyboards import kb_main, kb_cancel, kb_settings, kb_delay_settings

def handle_settings_cb(chat_id: int, msg_id: int, user_id: int, data: str):
    if data == 'menu:settings':
        settings = DB.get_user_settings(user_id)
        qs = settings.get('quiet_hours_start')
        qe = settings.get('quiet_hours_end')
        quiet = f"{qs} - {qe}" if qs and qe else "не установлены"
        notify = '✅' if settings.get('notify_on_complete', True) else '❌'
        delay_min = settings.get('delay_min', 30) or 30
        delay_max = settings.get('delay_max', 90) or 90

        edit_message(chat_id, msg_id,
            f"⚙️ <b>Настройки</b>\n\n"
            f"🌙 <b>Тихие часы:</b> {quiet}\n"
            f"⏱ <b>Задержка рассылки:</b> {delay_min}-{delay_max} сек\n"
            f"🔔 <b>Уведомления о завершении:</b> {notify}\n\n"
            f"<i>В тихие часы рассылки не отправляются</i>", kb_settings())

    elif data == 'settings:quiet_hours':
        DB.set_user_state(user_id, 'waiting_quiet_hours')
        edit_message(chat_id, msg_id,
            "🌙 <b>Тихие часы</b>\n"
            "В это время рассылки не будут отправляться.\n"
            "Введите диапазон в формате:\n"
            "<code>23:00-08:00</code>", kb_cancel())

    elif data == 'settings:quiet_hours_off':
        DB.update_user_settings(user_id, quiet_hours_start=None, quiet_hours_end=None)
        edit_message(chat_id, msg_id, "✅ Тихие часы отключены", kb_settings())

    elif data == 'settings:mailing_delay':
        edit_message(chat_id, msg_id,
            "⏱ <b>Задержка между сообщениями</b>\n\n"
            "Выберите диапазон задержки.\n"
            "Задержка будет случайной в выбранном диапазоне.\n\n"
            "⚠️ <b>Рекомендации:</b>\n"
            "• Быстро (5-15 сек) — риск бана выше\n"
            "• Безопасно (60-180 сек) — минимальный риск", kb_delay_settings())

    elif data.startswith('settings:delay:'):
        parts = data.split(':')
        delay_min, delay_max = int(parts[2]), int(parts[3])
        DB.update_user_settings(user_id, delay_min=delay_min, delay_max=delay_max)
        edit_message(chat_id, msg_id, f"✅ Задержка установлена: {delay_min}-{delay_max} сек", kb_settings())

    elif data.startswith('settings:notify:'):
        value = data.endswith(':on')
        DB.update_user_settings(user_id, notify_on_complete=value, notify_on_error=value)
        status = 'включены' if value else 'отключены'
        edit_message(chat_id, msg_id, f"✅ Уведомления {status}", kb_settings())


def handle_settings_state(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Returns True if state was handled"""
    
    if state == 'waiting_quiet_hours':
        m = re.match(r'^(\d{1,2}):(\d{2})\s*[-—]\s*(\d{1,2}):(\d{2})$', text.strip())
        if m:
            sh, sm, eh, em = map(int, m.groups())
            if sh > 23 or sm > 59 or eh > 23 or em > 59:
                send_message(chat_id, "❌ Неверное время", kb_cancel())
                return True
            DB.update_user_settings(user_id,
                quiet_hours_start=f"{sh:02d}:{sm:02d}",
                quiet_hours_end=f"{eh:02d}:{em:02d}"
            )
            DB.clear_user_state(user_id)
            send_message(chat_id, f"✅ Тихие часы установлены: {sh:02d}:{sm:02d} - {eh:02d}:{em:02d}", kb_main())
        else:
            send_message(chat_id, "❌ Неверный формат. Пример: <code>23:00-08:00</code>", kb_cancel())
        return True

    return False