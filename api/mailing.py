# api/mailing.py
"""
Mailing and campaign handlers
"""
import logging
from datetime import datetime, timedelta
from api.db import DB
from api.telegram import edit_message, send_message
from api.keyboards import (
    kb_main, kb_cancel, kb_back, kb_mailing, kb_mailing_sources,
    kb_mailing_templates, kb_mailing_account_folders, kb_mailing_confirm_multi,
    kb_mailing_settings, kb_scheduled_list, kb_active_mailings, kb_campaign_actions
)

logger = logging.getLogger(__name__)

def handle_mailing_cb(chat_id: int, msg_id: int, user_id: int, data: str, saved: dict):
    if data == 'menu:mailing':
        edit_message(chat_id, msg_id, "📤 <b>Рассылка</b>\nВыберите действие:", kb_mailing())

    elif data == 'mailing:new':
        sources = DB.get_audience_sources(user_id, status='completed')
        if not sources:
            edit_message(chat_id, msg_id,
                "❌ <b>Нет готовых аудиторий</b>\n"
                "Сначала создайте аудиторию через парсинг.", kb_back('menu:mailing'))
            return
        valid = [s for s in sources if DB.get_audience_stats(s['id'])['remaining'] > 0]
        if not valid:
            edit_message(chat_id, msg_id,
                "❌ <b>Нет доступных получателей</b>\n"
                "Все пользователи уже получили сообщения.", kb_back('menu:mailing'))
            return
        DB.clear_user_state(user_id)
        edit_message(chat_id, msg_id, "📊 <b>Шаг 1/3: Выберите аудиторию</b>", kb_mailing_sources(valid))

    elif data.startswith('mailing:source:'):
        src_id = int(data.split(':')[2])
        templates = DB.get_templates(user_id)
        if not templates:
            edit_message(chat_id, msg_id,
                "❌ <b>Нет шаблонов</b>\n"
                "Сначала создайте шаблон сообщения.", kb_back('menu:mailing'))
            return
        DB.set_user_state(user_id, 'mailing_setup', {'source_id': src_id})
        edit_message(chat_id, msg_id, "📝 <b>Шаг 2/3: Выберите шаблон</b>", kb_mailing_templates(templates))

    elif data.startswith('mailing:template:'):
        t_id = int(data.split(':')[2])
        saved['template_id'] = t_id
        
        folders = DB.get_account_folders(user_id)
        accounts_without_folder = DB.get_accounts_without_folder(user_id)
        
        has_active = False
        for f in folders:
            if DB.count_active_accounts_in_folder(f['id']) > 0:
                has_active = True
                break
        if not has_active:
            active_without = [a for a in accounts_without_folder if a.get('status') == 'active']
            has_active = len(active_without) > 0
        
        if not has_active:
            edit_message(chat_id, msg_id,
                "❌ <b>Нет активных аккаунтов</b>\n"
                "Сначала добавьте и авторизуйте аккаунт.", kb_back('menu:mailing'))
            return
        
        DB.set_user_state(user_id, 'mailing_setup', saved)
        edit_message(chat_id, msg_id, 
            "👤 <b>Шаг 3/3: Выберите папку аккаунтов</b>\n"
            "<i>Все активные аккаунты из выбранной папки будут участвовать в рассылке</i>",
            kb_mailing_account_folders(folders, accounts_without_folder))

    elif data.startswith('mailing:acc_folder:'):
        folder_id_str = data.split(':')[2]
        folder_id = int(folder_id_str) if folder_id_str != '0' else 0
        saved['account_folder_id'] = folder_id
        DB.set_user_state(user_id, 'mailing_confirm', saved)
        
        source = DB.get_audience_source(saved.get('source_id'))
        template = DB.get_template(saved.get('template_id'))
        stats = DB.get_audience_stats(saved.get('source_id')) if saved.get('source_id') else {}
        
        if folder_id > 0:
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
        delay_min = settings.get('delay_min', 30) or 30
        delay_max = settings.get('delay_max', 90) or 90
        
        edit_message(chat_id, msg_id,
            f"📤 <b>Подтверждение рассылки</b>\n\n"
            f"📊 <b>Аудитория:</b> {source['source_link'] if source else '?'}\n"
            f"👥 <b>Получателей:</b> {stats.get('remaining', 0)}\n\n"
            f"📝 <b>Шаблон:</b> {template['name'] if template else '?'}\n\n"
            f"📁 <b>Папка аккаунтов:</b> {folder_name}\n"
            f"👤 <b>Активных аккаунтов:</b> {active_count}\n"
            f"💳 <b>Доступно сообщений:</b> {total_available}\n\n"
            f"⏱ <b>Задержка:</b> {delay_min}-{delay_max} сек\n"
            f"🔄 <b>Авто-переключение:</b> ✅ Включено\n\n"
            f"<i>При Peer flood аккаунт будет автоматически заменён на следующий</i>",
            kb_mailing_confirm_multi())

    elif data == 'mailing:settings':
        settings = DB.get_user_settings(user_id)
        delay_min = settings.get('delay_min', 30) or 30
        delay_max = settings.get('delay_max', 90) or 90
        
        edit_message(chat_id, msg_id,
            f"⚙️ <b>Настройки рассылки</b>\n\n"
            f"⏱ <b>Текущая задержка:</b> {delay_min}-{delay_max} сек\n"
            f"🔄 <b>Авто-переключение:</b> ✅\n\n"
            f"<i>Задержка применяется случайно в указанном диапазоне</i>",
            kb_mailing_settings())

    elif data == 'mailing:back_to_confirm':
        handle_mailing_cb(chat_id, msg_id, user_id, f"mailing:acc_folder:{saved.get('account_folder_id', 0)}", saved)

    elif data == 'mailing:start_now':
        if not all([saved.get('source_id'), saved.get('template_id'), saved.get('account_folder_id') is not None]):
            edit_message(chat_id, msg_id, "❌ Ошибка: данные не найдены", kb_main())
            DB.clear_user_state(user_id)
            return
        
        folder_id = saved.get('account_folder_id')
        if folder_id and folder_id > 0:
            accounts = DB.get_accounts_in_folder(folder_id)
        else:
            accounts = DB.get_accounts_without_folder(user_id)
        
        active_accounts = [a for a in accounts if a.get('status') == 'active']
        if not active_accounts:
            edit_message(chat_id, msg_id, "❌ Нет активных аккаунтов в выбранной папке", kb_main())
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
                'delay_min': settings.get('delay_min', 30),
                'delay_max': settings.get('delay_max', 90),
                'auto_switch': True,
                'report_every': 10
            }
        )
        DB.clear_user_state(user_id)
        
        if campaign:
            stats = DB.get_audience_stats(saved['source_id'])
            edit_message(chat_id, msg_id,
                f"🚀 <b>Рассылка запущена!</b>\n\n"
                f"🆔 ID кампании: <code>{campaign['id']}</code>\n"
                f"👥 Получателей: <b>{stats['remaining']}</b>\n"
                f"👤 Аккаунтов: <b>{len(account_ids)}</b>\n\n"
                f"<i>Вы будете получать отчёты каждые 10 сообщений.\n"
                f"При Peer flood аккаунт будет автоматически заменён.</i>", kb_main())
        else:
            edit_message(chat_id, msg_id, "❌ Ошибка создания рассылки", kb_main())

    elif data == 'mailing:schedule':
        DB.set_user_state(user_id, 'waiting_schedule_datetime', saved)
        edit_message(chat_id, msg_id,
            "📅 <b>Отложенная рассылка</b>\n"
            "Введите дату и время запуска:\n"
            "<b>Форматы:</b>\n"
            "• <code>14:30</code> — сегодня/завтра в 14:30\n"
            "• <code>2024-12-25 14:30</code>\n"
            "• <code>25.12.2024 14:30</code>\n"
            "⚠️ Время в UTC", kb_cancel())

    elif data == 'mailing:cancel':
        DB.clear_user_state(user_id)
        edit_message(chat_id, msg_id, "❌ Рассылка отменена", kb_main())

    # ===== ACTIVE MAILINGS =====
    elif data == 'mailing:active_list':
        campaigns = DB.get_active_campaigns(user_id)
        if not campaigns:
            edit_message(chat_id, msg_id,
                "📊 <b>Активные рассылки</b>\n"
                "Нет активных рассылок.", kb_back('menu:mailing'))
        else:
            txt = f"📊 <b>Активные рассылки ({len(campaigns)})</b>\n\n"
            for c in campaigns[:5]:
                status_emoji = {'pending': '⏳', 'running': '🔄', 'paused': '⏸'}.get(c['status'], '❓')
                sent = c.get('sent_count', 0)
                failed = c.get('failed_count', 0)
                total = c.get('total_count', '?')
                txt += f"{status_emoji} ID:{c['id']} — {sent}/{total} (ошибок: {failed})\n"
            edit_message(chat_id, msg_id, txt, kb_active_mailings(campaigns))

    elif data.startswith('campaign:view:'):
        campaign_id = int(data.split(':')[2])
        campaign = DB.get_campaign(campaign_id)
        if not campaign:
            campaigns = DB.get_active_campaigns(user_id)
            edit_message(chat_id, msg_id, "❌ Кампания не найдена", kb_active_mailings(campaigns))
            return
        
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
        
        current_acc_info = ""
        if campaign.get('current_account_id'):
            current_account = DB.get_account(campaign['current_account_id'])
            if current_account:
                phone = current_account['phone']
                masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
                current_acc_info = f"\n📱 <b>Текущий аккаунт:</b> {masked}"
        
        edit_message(chat_id, msg_id,
            f"📊 <b>Кампания #{campaign['id']}</b>\n\n"
            f"📈 <b>Статус:</b> {status_map.get(campaign['status'], campaign['status'])}\n"
            f"📊 <b>Аудитория:</b> {source['source_link'] if source else '?'}\n"
            f"📝 <b>Шаблон:</b> {template['name'] if template else '?'}\n\n"
            f"✅ <b>Отправлено:</b> {campaign.get('sent_count', 0)}\n"
            f"❌ <b>Ошибок:</b> {campaign.get('failed_count', 0)}\n"
            f"👥 <b>Всего:</b> {campaign.get('total_count', '?')}{current_acc_info}",
            kb_campaign_actions(campaign_id, campaign['status']))

    elif data.startswith('campaign:pause:'):
        campaign_id = int(data.split(':')[2])
        DB.update_campaign(campaign_id, status='paused')
        edit_message(chat_id, msg_id, "⏸ <b>Кампания приостановлена</b>", kb_campaign_actions(campaign_id, 'paused'))

    elif data.startswith('campaign:resume:'):
        campaign_id = int(data.split(':')[2])
        DB.update_campaign(campaign_id, status='running')
        edit_message(chat_id, msg_id, "▶️ <b>Кампания возобновлена</b>", kb_campaign_actions(campaign_id, 'running'))

    elif data.startswith('campaign:stop:'):
        campaign_id = int(data.split(':')[2])
        DB.update_campaign(campaign_id, status='stopped')
        campaigns = DB.get_active_campaigns(user_id)
        edit_message(chat_id, msg_id, "🛑 <b>Кампания остановлена</b>", kb_active_mailings(campaigns))

    # ===== SCHEDULED MAILINGS =====
    elif data == 'mailing:scheduled_list':
        mailings = DB.get_scheduled_mailings(user_id)
        pending = [m for m in mailings if m['status'] == 'pending']
        if not pending:
            edit_message(chat_id, msg_id, "📅 <b>Отложенные рассылки</b>\nНет запланированных рассылок.", kb_back('menu:mailing'))
        else:
            txt = f"📅 <b>Отложенные рассылки ({len(pending)})</b>\n"
            for m in pending[:5]:
                scheduled = m.get('scheduled_at', '')[:16].replace('T', ' ')
                txt += f"• ID: {m['id']} | {scheduled} UTC\n"
            edit_message(chat_id, msg_id, txt, kb_scheduled_list(pending))

    elif data.startswith('scheduled:delete:'):
        mailing_id = int(data.split(':')[2])
        logger.info(f"Deleting scheduled mailing {mailing_id} for user {user_id}")
        result = DB.delete_scheduled_mailing(mailing_id)
        logger.info(f"Delete result: {result}")
        
        mailings = DB.get_scheduled_mailings(user_id)
        pending = [m for m in mailings if m['status'] == 'pending']
        if pending:
            txt = f"✅ Рассылка отменена\n\n📅 <b>Отложенные рассылки ({len(pending)})</b>\n"
            for m in pending[:5]:
                scheduled = m.get('scheduled_at', '')[:16].replace('T', ' ')
                txt += f"• ID: {m['id']} | {scheduled} UTC\n"
            edit_message(chat_id, msg_id, txt, kb_scheduled_list(pending))
        else:
            edit_message(chat_id, msg_id, "✅ Рассылка отменена\n\n📅 <b>Отложенные рассылки</b>\nНет запланированных рассылок.", kb_back('menu:mailing'))


def handle_mailing_state(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Returns True if state was handled"""
    
    if state == 'waiting_schedule_datetime':
        import re
        try:
            now = datetime.utcnow()
            text_clean = text.strip()
            if re.match(r'^\d{1,2}:\d{2}$', text_clean):
                h, m = map(int, text_clean.split(':'))
                if h > 23 or m > 59:
                    raise ValueError("Invalid time")
                scheduled = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if scheduled <= now:
                    scheduled += timedelta(days=1)
            elif re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}$', text_clean):
                scheduled = datetime.strptime(text_clean, '%Y-%m-%d %H:%M')
            elif re.match(r'^\d{1,2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2}$', text_clean):
                scheduled = datetime.strptime(text_clean, '%d.%m.%Y %H:%M')
            else:
                send_message(chat_id,
                    "❌ Неверный формат. Примеры:\n"
                    "• <code>14:30</code> (сегодня/завтра)\n"
                    "• <code>2024-12-25 14:30</code>\n"
                    "• <code>25.12.2024 14:30</code>", kb_cancel())
                return True
            if scheduled <= now:
                send_message(chat_id, "❌ Время должно быть в будущем", kb_cancel())
                return True
            if not all([saved.get('source_id'), saved.get('template_id'), saved.get('account_folder_id') is not None]):
                send_message(chat_id, "❌ Ошибка: данные рассылки не найдены", kb_main())
                DB.clear_user_state(user_id)
                return True
            mailing = DB.create_scheduled_mailing(
                user_id, saved['source_id'], saved['template_id'], 
                account_folder_id=saved.get('account_folder_id'),
                scheduled_at=scheduled
            )
            DB.clear_user_state(user_id)
            if mailing:
                send_message(chat_id,
                    f"✅ <b>Рассылка запланирована!</b>\n"
                    f"📅 Дата: {scheduled.strftime('%d.%m.%Y %H:%M')} UTC\n"
                    f"🆔 ID: {mailing['id']}", kb_main())
            else:
                send_message(chat_id, "❌ Ошибка создания рассылки", kb_main())
        except Exception as e:
            logger.error(f"Schedule parse error: {e}")
            send_message(chat_id, "❌ Ошибка обработки даты", kb_cancel())
        return True

    return False