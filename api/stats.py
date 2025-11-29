# api/stats.py
"""
Statistics handlers
"""
from api.db import DB
from api.telegram import edit_message
from api.keyboards import kb_stats, kb_back

def handle_stats_cb(chat_id: int, msg_id: int, user_id: int, data: str):
    if data == 'menu:stats':
        stats = DB.get_user_stats(user_id)
        success_rate = stats.get('success_rate', 0)
        edit_message(chat_id, msg_id,
            f"📈 <b>Статистика</b>\n\n"
            f"📊 <b>Аудитории:</b> {stats['audiences']} (готовых: {stats['audiences_completed']})\n"
            f"📄 <b>Шаблоны:</b> {stats['templates']}\n"
            f"👤 <b>Аккаунты:</b> {stats['accounts']} (активных: {stats['accounts_active']})\n"
            f"📤 <b>Кампании:</b> {stats['campaigns']}\n\n"
            f"👥 <b>Всего спарсено:</b> {stats['total_parsed']}\n"
            f"✅ <b>Отправлено:</b> {stats['total_sent']}\n"
            f"❌ <b>Ошибок:</b> {stats['total_failed']}\n"
            f"📊 <b>Успешность:</b> {success_rate}%", kb_stats())

    elif data == 'stats:errors':
        errors = DB.get_error_stats(user_id, days=7)
        if not errors:
            edit_message(chat_id, msg_id,
                "📉 <b>Ошибки за 7 дней</b>\n"
                "✅ Ошибок не обнаружено!", kb_back('menu:stats'))
        else:
            txt = "📉 <b>Ошибки за 7 дней</b>\n\n"
            for err_type, count in sorted(errors.items(), key=lambda x: -x[1]):
                txt += f"• {err_type}: <b>{count}</b>\n"
            edit_message(chat_id, msg_id, txt, kb_back('menu:stats'))

    elif data == 'stats:top_audiences':
        sources = DB.get_audience_sources(user_id, status='completed')
        sources_sorted = sorted(sources, key=lambda x: x.get('parsed_count', 0), reverse=True)[:10]
        if not sources_sorted:
            edit_message(chat_id, msg_id,
                "🏆 <b>Топ аудиторий</b>\n"
                "Нет готовых аудиторий", kb_back('menu:stats'))
        else:
            txt = "🏆 <b>Топ аудиторий по размеру</b>\n\n"
            for i, s in enumerate(sources_sorted, 1):
                link = s['source_link']
                if len(link) > 25:
                    link = link[:22] + '...'
                txt += f"{i}. {link}: <b>{s.get('parsed_count', 0)}</b>\n"
            edit_message(chat_id, msg_id, txt, kb_back('menu:stats'))

    elif data == 'stats:active_mailings':
        campaigns = DB.get_active_campaigns(user_id)
        if not campaigns:
            edit_message(chat_id, msg_id,
                "📊 <b>Активные рассылки</b>\n"
                "Нет активных рассылок", kb_back('menu:stats'))
        else:
            txt = f"📊 <b>Активные рассылки ({len(campaigns)})</b>\n\n"
            for c in campaigns:
                status_emoji = {'pending': '⏳', 'running': '🔄', 'paused': '⏸'}.get(c['status'], '❓')
                sent = c.get('sent_count', 0)
                failed = c.get('failed_count', 0)
                total = c.get('total_count', '?')
                txt += f"{status_emoji} ID:{c['id']} — {sent}/{total} (ошибок: {failed})\n"
            edit_message(chat_id, msg_id, txt, kb_back('menu:stats'))