"""
Statistics handlers - Extended v2.0
With hourly stats, negative responses, account predictions
"""
import logging
from datetime import datetime
from core.db import DB
from core.telegram import send_message
from core.keyboards import (
    kb_main_menu, kb_stats_menu, kb_back,
    kb_inline_hourly_stats
)
from core.menu import show_main_menu, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_ERRORS = '📉 Ошибки за 7 дней'
BTN_TOP_AUDIENCES = '🏆 Топ аудиторий'
BTN_ACTIVE_MAILINGS = '📊 Активные рассылки'
BTN_HOURLY_STATS = '⏰ Статистика по часам'
BTN_NEGATIVE_RESPONSES = '🛡 Негативные ответы'


def show_stats_menu(chat_id: int, user_id: int):
    """Show statistics menu with comprehensive description"""
    DB.set_user_state(user_id, 'stats:menu')
    
    stats = DB.get_user_stats(user_id)
    success_rate = stats.get('success_rate', 0)
    
    # Get best hours
    best_hours = DB.get_best_hours(user_id, limit=3)
    best_hours_str = ', '.join(f'{h}:00' for h in best_hours) if best_hours else 'нет данных'
    
    # Get current delay multiplier
    current_hour = datetime.utcnow().hour
    delay_mult = DB.get_delay_multiplier_for_hour(user_id, current_hour)
    delay_info = ""
    if delay_mult != 1.0:
        delay_info = f"\n⏱ Множитель задержки: <b>x{delay_mult:.1f}</b>"
    
    # System status
    system_status = ""
    if DB.is_system_paused(user_id):
        system_status = "\n\n🚨 <b>СИСТЕМА ПРИОСТАНОВЛЕНА</b>"
    
    send_message(chat_id,
        f"📈 <b>Статистика и метрики</b>{system_status}\n\n"
        f"<i>Детальный обзор работы системы,\n"
        f"эффективности рассылок и трендов.</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📊 РЕСУРСЫ</b>\n"
        f"├ Аудитории: {stats['audiences']} (готовых: {stats['audiences_completed']})\n"
        f"├ Шаблоны: {stats['templates']}\n"
        f"├ Аккаунты: {stats['accounts']} (активных: {stats['accounts_active']})\n"
        f"└ Кампании: {stats['campaigns']}\n\n"
        f"<b>📤 РЕЗУЛЬТАТЫ</b>\n"
        f"├ Спарсено контактов: {stats['total_parsed']}\n"
        f"├ ✅ Отправлено: {stats['total_sent']}\n"
        f"├ ❌ Ошибок: {stats['total_failed']}\n"
        f"└ Успешность: <b>{success_rate}%</b>\n\n"
        f"<b>⏰ АКТИВНОСТЬ</b>\n"
        f"├ Лучшие часы: {best_hours_str}{delay_info}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 <i>Анализируйте ошибки и негативные ответы\n"
        f"для улучшения стратегии рассылок</i>",
        kb_stats_menu()
    )


def handle_stats(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle statistics states. Returns True if handled."""
    
    if text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return True
    
    if text == BTN_BACK:
        if state == 'stats:menu':
            show_main_menu(chat_id, user_id)
        else:
            show_stats_menu(chat_id, user_id)
        return True
    
    # Menu state
    if state == 'stats:menu':
        if text == BTN_ERRORS:
            show_error_stats(chat_id, user_id)
            return True
        if text == BTN_TOP_AUDIENCES:
            show_top_audiences(chat_id, user_id)
            return True
        if text == BTN_ACTIVE_MAILINGS:
            show_active_mailings_stats(chat_id, user_id)
            return True
        if text == BTN_HOURLY_STATS or text == '⏰ Статистика по часам':
            show_hourly_stats(chat_id, user_id)
            return True
        if text == BTN_NEGATIVE_RESPONSES or text == '🛡 Негативные ответы':
            show_negative_responses(chat_id, user_id)
            return True
    
    return False


def show_error_stats(chat_id: int, user_id: int):
    """Show error statistics"""
    DB.set_user_state(user_id, 'stats:errors')
    
    errors = DB.get_error_stats(user_id, days=7)
    
    if not errors:
        send_message(chat_id,
            "📉 <b>Ошибки за 7 дней</b>\n\n"
            "✅ Ошибок не обнаружено!\n\n"
            "Всё работает отлично.",
            kb_back()
        )
    else:
        txt = "📉 <b>Ошибки за 7 дней</b>\n\n"
        
        # Sort by count
        sorted_errors = sorted(errors.items(), key=lambda x: -x[1])
        total_errors = sum(errors.values())
        
        for err_type, count in sorted_errors:
            # Human-readable error names
            err_names = {
                'parsing_error': '🔍 Ошибки парсинга',
                'mailing_error': '📤 Ошибки рассылки',
                'auth_error': '🔐 Ошибки авторизации',
                'flood_wait': '⏰ FloodWait',
                'peer_flood': '🚫 PeerFlood',
                'privacy_restricted': '🔒 Приватность',
                'user_blocked': '🚫 Блокировки',
                'user_not_found': '❓ Пользователь не найден',
                'chat_write_forbidden': '🔇 Запрет записи',
                'timeout': '⏱ Таймаут',
                'network_error': '🌐 Сеть'
            }
            name = err_names.get(err_type, err_type)
            percent = round(count / total_errors * 100, 1)
            txt += f"• {name}: <b>{count}</b> ({percent}%)\n"
        
        txt += f"\n📊 <b>Всего ошибок:</b> {total_errors}"
        
        # Recommendations
        recommendations = []
        if errors.get('flood_wait', 0) > 5:
            recommendations.append("💡 Много FloodWait — увеличьте задержки")
        if errors.get('peer_flood', 0) > 3:
            recommendations.append("💡 PeerFlood — дайте аккаунтам отдохнуть")
        if errors.get('privacy_restricted', 0) > 10:
            recommendations.append("💡 Много ограничений приватности — это нормально")
        
        if recommendations:
            txt += "\n\n<b>Рекомендации:</b>\n" + "\n".join(recommendations)
        
        send_message(chat_id, txt, kb_back())


def show_top_audiences(chat_id: int, user_id: int):
    """Show top audiences by size"""
    DB.set_user_state(user_id, 'stats:top')
    
    sources = DB.get_audience_sources(user_id, status='completed')
    sources_sorted = sorted(sources, key=lambda x: x.get('parsed_count', 0), reverse=True)[:10]
    
    if not sources_sorted:
        send_message(chat_id,
            "🏆 <b>Топ аудиторий</b>\n\n"
            "Нет готовых аудиторий.\n\n"
            "Создайте аудиторию через парсинг!",
            kb_back()
        )
    else:
        txt = "🏆 <b>Топ аудиторий по размеру</b>\n\n"
        
        for i, s in enumerate(sources_sorted, 1):
            link = s['source_link']
            if len(link) > 25:
                link = link[:22] + '...'
            
            stats = DB.get_audience_stats(s['id'])
            total = s.get('parsed_count', 0)
            sent = stats.get('sent', 0)
            remaining = stats.get('remaining', 0)
            
            emoji = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
            
            # Keyword icon
            kw_icon = ' 🔑' if s.get('keyword_filter') else ''
            
            # Progress
            progress = int(sent / total * 100) if total > 0 else 0
            
            txt += f"{emoji} {link}{kw_icon}\n"
            txt += f"   👥 {total} | ✅ {sent} ({progress}%) | ⏳ {remaining}\n\n"
        
        send_message(chat_id, txt, kb_back())


def show_active_mailings_stats(chat_id: int, user_id: int):
    """Show active mailings statistics"""
    DB.set_user_state(user_id, 'stats:mailings')
    
    campaigns = DB.get_active_campaigns(user_id)
    
    if not campaigns:
        send_message(chat_id,
            "📊 <b>Активные рассылки</b>\n\n"
            "Нет активных рассылок.\n\n"
            "Создайте рассылку в разделе «📤 Рассылка».",
            kb_back()
        )
    else:
        txt = f"📊 <b>Активные рассылки ({len(campaigns)})</b>\n\n"
        
        total_sent = 0
        total_failed = 0
        total_remaining = 0
        
        for c in campaigns:
            status_emoji = {
                'pending': '⏳',
                'running': '🔄',
                'paused': '⏸'
            }.get(c['status'], '❓')
            
            sent = c.get('sent_count', 0)
            failed = c.get('failed_count', 0)
            total = c.get('total_count', 0)
            remaining = max(0, total - sent - failed)
            
            total_sent += sent
            total_failed += failed
            total_remaining += remaining
            
            progress = int(sent / total * 100) if total > 0 else 0
            bar = '█' * (progress // 10) + '░' * (10 - progress // 10)
            
            # Features icons
            features = []
            if c.get('use_warm_start'):
                features.append('🔥')
            if c.get('use_typing_simulation'):
                features.append('⌨️')
            if c.get('use_adaptive_delays'):
                features.append('📊')
            features_str = ''.join(features)
            
            txt += f"{status_emoji} <b>#{c['id']}</b> {features_str}\n"
            txt += f"   [{bar}] {progress}%\n"
            txt += f"   ✅ {sent} | ❌ {failed} | ⏳ {remaining}\n\n"
        
        # Summary
        txt += f"━━━━━━━━━━━━━━━━━\n"
        txt += f"<b>Итого:</b>\n"
        txt += f"✅ Отправлено: {total_sent}\n"
        txt += f"❌ Ошибок: {total_failed}\n"
        txt += f"⏳ Осталось: {total_remaining}\n"
        
        # Success rate
        if total_sent + total_failed > 0:
            rate = round(total_sent / (total_sent + total_failed) * 100, 1)
            txt += f"📊 Успешность: {rate}%"
        
        send_message(chat_id, txt, kb_back())


def show_hourly_stats(chat_id: int, user_id: int):
    """Show hourly statistics"""
    DB.set_user_state(user_id, 'stats:hourly')
    
    stats = DB.get_hourly_stats(user_id)
    
    if not stats:
        send_message(chat_id,
            "⏰ <b>Статистика по часам</b>\n\n"
            "Пока нет данных.\n\n"
            "Статистика появится после первых рассылок.",
            kb_back()
        )
        return
    
    txt = "⏰ <b>Статистика по часам (UTC)</b>\n\n"
    txt += "Показывает успешность отправки в разное время суток.\n\n"
    
    # Group by hour
    hourly = {}
    for s in stats:
        hour = s.get('hour', 0)
        if hour not in hourly:
            hourly[hour] = {'sent': 0, 'success': 0, 'failed': 0, 'flood': 0}
        hourly[hour]['sent'] += s.get('total_sent', 0) or 0
        hourly[hour]['success'] += s.get('total_success', 0) or 0
        hourly[hour]['failed'] += s.get('total_failed', 0) or 0
        hourly[hour]['flood'] += s.get('total_flood_waits', 0) or 0
    
    # Sort by hour
    for hour in sorted(hourly.keys()):
        data = hourly[hour]
        sent = data['sent']
        if sent == 0:
            continue
        
        success_rate = round(data['success'] / sent * 100) if sent > 0 else 0
        flood_rate = round(data['flood'] / sent * 100, 1) if sent > 0 else 0
        
        # Emoji based on success rate
        if success_rate >= 90:
            emoji = '🟢'
        elif success_rate >= 70:
            emoji = '🟡'
        else:
            emoji = '🔴'
        
        # Bar
        bar_len = min(10, sent // 10)
        bar = '█' * bar_len + '░' * (10 - bar_len)
        
        txt += f"{emoji} <code>{hour:02d}:00</code> [{bar}] {success_rate}%"
        if flood_rate > 0:
            txt += f" (FW: {flood_rate}%)"
        txt += f"\n"
    
    # Best and worst hours
    if hourly:
        best_hour = max(hourly.keys(), key=lambda h: hourly[h]['success'] / max(hourly[h]['sent'], 1))
        worst_hour = min(hourly.keys(), key=lambda h: hourly[h]['success'] / max(hourly[h]['sent'], 1))
        
        txt += f"\n<b>Лучший час:</b> {best_hour:02d}:00\n"
        txt += f"<b>Худший час:</b> {worst_hour:02d}:00\n\n"
        txt += "<i>Рекомендация: планируйте рассылки на лучшие часы</i>"
    
    send_message(chat_id, txt, kb_back())


def show_negative_responses(chat_id: int, user_id: int):
    """Show negative responses statistics"""
    DB.set_user_state(user_id, 'stats:negative')
    
    responses = DB.get_negative_responses(user_id, days=7)
    triggers = DB.get_stop_triggers(user_id)
    
    # Count by trigger
    trigger_counts = {}
    for r in responses:
        trigger = r.get('trigger_matched', 'unknown')
        trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
    
    # Get blacklist stats
    blacklist = DB.get_blacklist(user_id)
    auto_blocked = sum(1 for b in blacklist if b.get('source') != 'manual')
    
    if not responses:
        txt = (
            "🛡 <b>Негативные ответы (7 дней)</b>\n\n"
            "✅ Негативных ответов не обнаружено!\n\n"
            f"🚫 Автоматически заблокировано: <b>{auto_blocked}</b>\n"
            f"🛡 Активных стоп-слов: <b>{sum(1 for t in triggers if t.get('is_active'))}</b>"
        )
    else:
        txt = f"🛡 <b>Негативные ответы (7 дней)</b>\n\n"
        txt += f"⚠️ Всего негативных: <b>{len(responses)}</b>\n"
        txt += f"🚫 Автоматически заблокировано: <b>{auto_blocked}</b>\n\n"
        
        if trigger_counts:
            txt += "<b>По стоп-словам:</b>\n"
            sorted_triggers = sorted(trigger_counts.items(), key=lambda x: -x[1])
            for trigger, count in sorted_triggers[:10]:
                txt += f"• «{trigger}»: {count}\n"
        
        txt += "\n<b>Последние ответы:</b>\n"
        for r in responses[:5]:
            username = r.get('from_username', 'unknown')
            message = (r.get('message_text', '') or '')[:50]
            if len(r.get('message_text', '') or '') > 50:
                message += '...'
            txt += f"• @{username}: <i>{message}</i>\n"
    
    txt += "\n\n<i>Негативные ответы помогают улучшить качество рассылок</i>"
    
    send_message(chat_id, txt, kb_back())
