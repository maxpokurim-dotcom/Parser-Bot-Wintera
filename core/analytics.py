"""
Analytics Module - Predictions, Heatmaps, Segmentation
Version 1.0

Handles:
- Audience activity heatmap
- Account risk predictions
- AI-powered audience segmentation
- Campaign effectiveness analysis
- System learning/knowledge base
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from core.db import DB
from core.telegram import send_message, edit_message, answer_callback
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel,
    kb_analytics_menu, kb_analytics_heatmap_actions, kb_analytics_risk_actions,
    kb_analytics_segments, kb_inline_risk_accounts, kb_inline_segments,
    reply_keyboard, inline_keyboard
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_HEATMAP = '🔥 Heatmap активности'
BTN_RISKS = '⚠️ Прогноз рисков'
BTN_SEGMENTS = '📊 Сегментация'
BTN_EFFECTIVENESS = '📈 Эффективность'
BTN_LEARNING = '🧠 Обучение системы'

# Day names for heatmap
DAY_NAMES = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

# Risk thresholds
RISK_LOW = 0.3
RISK_MEDIUM = 0.6
RISK_HIGH = 0.8


def show_analytics_menu(chat_id: int, user_id: int):
    """Show analytics menu"""
    DB.set_user_state(user_id, 'analytics:menu')
    
    # Get quick stats
    stats = DB.get_dashboard_stats(user_id)
    
    # Get risk summary
    risk_predictions = DB.get_all_risk_predictions(user_id)
    high_risk = len([p for p in risk_predictions 
                     if p.get('prediction') and p['prediction'].get('risk_score', 0) > RISK_HIGH])
    medium_risk = len([p for p in risk_predictions 
                       if p.get('prediction') and RISK_MEDIUM < p['prediction'].get('risk_score', 0) <= RISK_HIGH])
    
    # Get heatmap status
    heatmap = DB.get_audience_heatmap(user_id)
    heatmap_status = f"✅ Данные на {heatmap.get('sample_size', 0)} пользователей" if heatmap else "❌ Нет данных"
    
    # Knowledge base stats
    knowledge = DB.get_herder_knowledge_stats(user_id)
    
    send_message(chat_id,
        f"📈 <b>Аналитика и прогнозы</b>\n\n"
        f"<b>📊 Общая статистика:</b>\n"
        f"├ Аккаунтов: {stats.get('accounts', 0)} ({stats.get('accounts_active', 0)} активных)\n"
        f"├ Отправлено: {stats.get('total_sent', 0)}\n"
        f"└ Успешность: {stats.get('success_rate', 0)}%\n\n"
        f"<b>⚠️ Риски аккаунтов:</b>\n"
        f"├ 🔴 Высокий риск: {high_risk}\n"
        f"└ 🟡 Средний риск: {medium_risk}\n\n"
        f"<b>🔥 Heatmap:</b> {heatmap_status}\n\n"
        f"<b>🧠 База знаний:</b>\n"
        f"├ Записей: {knowledge.get('total', 0)}\n"
        f"└ Плохих фраз: {knowledge.get('bad_phrases', 0)}",
        kb_analytics_menu()
    )


def handle_analytics(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle analytics states. Returns True if handled."""
    
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
    if state == 'analytics:menu':
        return _handle_menu(chat_id, user_id, text)
    
    # Heatmap
    if state == 'analytics:heatmap':
        return _handle_heatmap(chat_id, user_id, text, saved)
    
    if state == 'analytics:heatmap:source':
        return _handle_heatmap_source(chat_id, user_id, text, saved)
    
    # Risks
    if state == 'analytics:risks':
        return _handle_risks(chat_id, user_id, text, saved)
    
    if state.startswith('analytics:risk:'):
        return _handle_risk_account(chat_id, user_id, text, state, saved)
    
    # Segmentation
    if state == 'analytics:segments':
        return _handle_segments_menu(chat_id, user_id, text)
    
    if state == 'analytics:segments:campaign':
        return _handle_segment_campaign(chat_id, user_id, text, saved)
    
    if state.startswith('analytics:segment:'):
        return _handle_segment_view(chat_id, user_id, text, state, saved)
    
    # Effectiveness
    if state == 'analytics:effectiveness':
        return _handle_effectiveness(chat_id, user_id, text, saved)
    
    # Learning
    if state == 'analytics:learning':
        return _handle_learning(chat_id, user_id, text, saved)
    
    if state == 'analytics:learning:bad_phrase':
        return _handle_add_bad_phrase(chat_id, user_id, text, saved)
    
    return False


def _handle_back(chat_id: int, user_id: int, state: str, saved: dict):
    """Handle back navigation"""
    if state in ['analytics:menu', 'analytics:heatmap', 'analytics:risks', 
                 'analytics:segments', 'analytics:effectiveness', 'analytics:learning']:
        show_main_menu(chat_id, user_id)
    else:
        show_analytics_menu(chat_id, user_id)


def _handle_menu(chat_id: int, user_id: int, text: str) -> bool:
    """Handle main menu selection"""
    if text == BTN_HEATMAP or text == '🔥 Heatmap активности':
        show_heatmap(chat_id, user_id)
        return True
    
    if text == BTN_RISKS or text == '⚠️ Прогноз рисков':
        show_risk_predictions(chat_id, user_id)
        return True
    
    if text == BTN_SEGMENTS or text == '📊 Сегментация':
        show_segments_menu(chat_id, user_id)
        return True
    
    if text == BTN_EFFECTIVENESS or text == '📈 Эффективность':
        show_effectiveness(chat_id, user_id)
        return True
    
    if text == BTN_LEARNING or text == '🧠 Обучение системы':
        show_learning_menu(chat_id, user_id)
        return True
    
    return False


# ==================== HEATMAP ====================

def show_heatmap(chat_id: int, user_id: int):
    """Show audience activity heatmap"""
    DB.set_user_state(user_id, 'analytics:heatmap')
    
    heatmap = DB.get_audience_heatmap(user_id)
    
    if not heatmap or not heatmap.get('heatmap_data'):
        send_message(chat_id,
            "🔥 <b>Heatmap активности</b>\n\n"
            "❌ Недостаточно данных для построения карты.\n\n"
            "Для сбора данных:\n"
            "• Выполните парсинг аудитории\n"
            "• Проведите несколько рассылок\n\n"
            "Или создайте heatmap на основе аудитории:",
            reply_keyboard([
                ['📊 Создать из аудитории'],
                ['◀️ Назад']
            ])
        )
        return
    
    # Render heatmap
    heatmap_text = _render_heatmap(heatmap['heatmap_data'])
    
    # Get best times
    best_times = heatmap.get('best_times', [])
    best_text = ""
    if best_times:
        best_text = "\n\n🎯 <b>Лучшее время для рассылки:</b>\n"
        for i, bt in enumerate(best_times[:3], 1):
            day_name = DAY_NAMES[bt.get('day', 0) % 7]
            hour = bt.get('hour', 12)
            score = bt.get('score', 0)
            best_text += f"{i}. {day_name} {hour:02d}:00 (активность: {int(score*100)}%)\n"
    
    send_message(chat_id,
        f"🔥 <b>Heatmap активности аудитории</b>\n\n"
        f"<pre>{heatmap_text}</pre>\n"
        f"<i>░ — низкая, ▒ — средняя, ▓ — высокая, █ — пик</i>\n"
        f"\n📊 Данные на основе {heatmap.get('sample_size', 0)} пользователей"
        f"{best_text}",
        kb_analytics_heatmap_actions()
    )


def _render_heatmap(data: Dict) -> str:
    """Render heatmap as ASCII art"""
    # Header
    result = "     00 03 06 09 12 15 18 21\n"
    result += "    " + "─" * 25 + "\n"
    
    for day in range(7):
        day_name = DAY_NAMES[day]
        result += f"{day_name} │"
        
        day_data = data.get(str(day), {})
        
        for hour in [0, 3, 6, 9, 12, 15, 18, 21]:
            value = day_data.get(str(hour), 0)
            
            if value >= 0.8:
                char = "██"
            elif value >= 0.6:
                char = "▓▓"
            elif value >= 0.4:
                char = "▒▒"
            elif value >= 0.2:
                char = "░░"
            else:
                char = "  "
            
            result += f" {char}"
        
        result += "\n"
    
    return result


def _handle_heatmap(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle heatmap actions"""
    if text == '📤 Применить к рассылке':
        optimal = DB.get_optimal_send_time(user_id)
        if optimal:
            send_message(chat_id,
                f"✅ <b>Оптимальное время применено</b>\n\n"
                f"При создании рассылки будет предложено:\n"
                f"🎯 {optimal['formatted']} (МСК)\n\n"
                f"Также доступно через кнопку «🎯 Оптимальное время» при создании рассылки.",
                kb_analytics_menu()
            )
        else:
            send_message(chat_id, "❌ Не удалось определить оптимальное время", kb_analytics_menu())
        return True
    
    if text == '🔄 Обновить данные':
        send_message(chat_id,
            "🔄 <b>Обновление Heatmap</b>\n\n"
            "Выберите источник данных:",
            reply_keyboard([
                ['📊 Из всех аудиторий'],
                ['📤 Из результатов рассылок'],
                ['◀️ Назад']
            ])
        )
        DB.set_user_state(user_id, 'analytics:heatmap:source', saved)
        return True
    
    if text == '📊 Создать из аудитории':
        _build_heatmap_from_audiences(chat_id, user_id)
        return True
    
    return False


def _handle_heatmap_source(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle heatmap source selection"""
    if text == '📊 Из всех аудиторий':
        _build_heatmap_from_audiences(chat_id, user_id)
        return True
    
    if text == '📤 Из результатов рассылок':
        _build_heatmap_from_mailings(chat_id, user_id)
        return True
    
    return False


def _build_heatmap_from_audiences(chat_id: int, user_id: int):
    """Build heatmap from parsed audiences"""
    send_message(chat_id, "⏳ Анализирую данные аудиторий...", kb_cancel())
    
    # Initialize heatmap
    heatmap_data = {}
    for day in range(7):
        heatmap_data[str(day)] = {}
        for hour in range(24):
            heatmap_data[str(day)][str(hour)] = 0
    
    # Get all sources
    sources = DB.get_audience_sources(user_id, status='completed')
    total_users = 0
    
    for source in sources:
        # Get users with last_seen
        users = DB.get_audience_with_filters(source['id'], limit=1000)
        
        for user in users:
            last_seen = user.get('last_seen')
            if last_seen:
                try:
                    # Parse last_seen
                    from core.timezone import parse_datetime
                    dt = parse_datetime(last_seen)
                    if dt:
                        day = dt.weekday()
                        hour = dt.hour
                        heatmap_data[str(day)][str(hour)] += 1
                        total_users += 1
                except:
                    pass
    
    if total_users == 0:
        send_message(chat_id,
            "❌ <b>Недостаточно данных</b>\n\n"
            "В аудиториях нет информации о времени активности.\n"
            "Попробуйте спарсить новую аудиторию.",
            kb_analytics_menu()
        )
        DB.set_user_state(user_id, 'analytics:menu')
        return
    
    # Normalize
    max_val = max(max(h.values()) for h in heatmap_data.values()) or 1
    for day in heatmap_data:
        for hour in heatmap_data[day]:
            heatmap_data[day][hour] = heatmap_data[day][hour] / max_val
    
    # Find best times
    best_times = []
    for day, hours in heatmap_data.items():
        for hour, score in hours.items():
            best_times.append({
                'day': int(day),
                'hour': int(hour),
                'score': score
            })
    best_times.sort(key=lambda x: x['score'], reverse=True)
    
    # Save
    DB.save_audience_heatmap(
        user_id=user_id,
        heatmap_data=heatmap_data,
        best_times=best_times[:10],
        sample_size=total_users
    )
    
    send_message(chat_id,
        f"✅ <b>Heatmap обновлён!</b>\n\n"
        f"Проанализировано пользователей: {total_users}",
        kb_analytics_menu()
    )
    
    # Show updated heatmap
    show_heatmap(chat_id, user_id)


def _build_heatmap_from_mailings(chat_id: int, user_id: int):
    """Build heatmap from mailing results"""
    send_message(chat_id, "⏳ Анализирую результаты рассылок...", kb_cancel())
    
    # Get hourly stats
    hourly_stats = DB.get_hourly_stats(user_id)
    
    if not hourly_stats:
        send_message(chat_id,
            "❌ <b>Недостаточно данных</b>\n\n"
            "Проведите несколько рассылок для сбора статистики.",
            kb_analytics_menu()
        )
        DB.set_user_state(user_id, 'analytics:menu')
        return
    
    # Build heatmap from success rates
    heatmap_data = {}
    for day in range(7):
        heatmap_data[str(day)] = {}
        for hour in range(24):
            heatmap_data[str(day)][str(hour)] = 0
    
    total_samples = 0
    for stat in hourly_stats:
        day = stat.get('day_of_week', 0)
        hour = stat.get('hour', 0)
        sent = stat.get('total_sent', 0)
        success = stat.get('total_success', 0)
        
        if sent > 0:
            rate = success / sent
            heatmap_data[str(day)][str(hour)] = rate
            total_samples += 1
    
    if total_samples == 0:
        send_message(chat_id, "❌ Недостаточно данных", kb_analytics_menu())
        DB.set_user_state(user_id, 'analytics:menu')
        return
    
    # Find best times
    best_times = []
    for day, hours in heatmap_data.items():
        for hour, score in hours.items():
            if score > 0:
                best_times.append({
                    'day': int(day),
                    'hour': int(hour),
                    'score': score
                })
    best_times.sort(key=lambda x: x['score'], reverse=True)
    
    # Save
    DB.save_audience_heatmap(
        user_id=user_id,
        heatmap_data=heatmap_data,
        best_times=best_times[:10],
        sample_size=total_samples
    )
    
    send_message(chat_id, "✅ Heatmap обновлён на основе рассылок!", kb_analytics_menu())
    show_heatmap(chat_id, user_id)


# ==================== RISK PREDICTIONS ====================

def show_risk_predictions(chat_id: int, user_id: int):
    """Show risk predictions for accounts"""
    DB.set_user_state(user_id, 'analytics:risks')
    
    # Calculate risks for all accounts
    accounts = DB.get_active_accounts(user_id)
    predictions = []
    
    for account in accounts:
        risk = _calculate_account_risk(account)
        predictions.append({
            'account': account,
            'prediction': risk
        })
    
    # Sort by risk
    predictions.sort(key=lambda x: x['prediction'].get('risk_score', 0), reverse=True)
    
    if not predictions:
        send_message(chat_id,
            "⚠️ <b>Прогноз рисков</b>\n\n"
            "Нет активных аккаунтов для анализа.",
            kb_analytics_menu()
        )
        return
    
    # Summary
    high_risk = [p for p in predictions if p['prediction'].get('risk_score', 0) > RISK_HIGH]
    medium_risk = [p for p in predictions if RISK_MEDIUM < p['prediction'].get('risk_score', 0) <= RISK_HIGH]
    low_risk = [p for p in predictions if p['prediction'].get('risk_score', 0) <= RISK_MEDIUM]
    
    text = f"⚠️ <b>Прогноз рисков на 24 часа</b>\n\n"
    
    if high_risk:
        text += f"🔴 <b>Высокий риск ({len(high_risk)}):</b>\n"
        for p in high_risk[:5]:
            acc = p['account']
            risk = p['prediction']
            phone = acc['phone']
            masked = f"{phone[:4]}**{phone[-2:]}" if len(phone) > 6 else phone
            text += f"  • {masked} — {int(risk['risk_score']*100)}%\n"
        text += "\n"
    
    if medium_risk:
        text += f"🟡 <b>Средний риск ({len(medium_risk)}):</b>\n"
        for p in medium_risk[:3]:
            acc = p['account']
            risk = p['prediction']
            phone = acc['phone']
            masked = f"{phone[:4]}**{phone[-2:]}" if len(phone) > 6 else phone
            text += f"  • {masked} — {int(risk['risk_score']*100)}%\n"
        text += "\n"
    
    text += f"🟢 <b>Низкий риск:</b> {len(low_risk)} аккаунтов\n"
    
    # Show inline keyboard with accounts
    kb = kb_inline_risk_accounts(predictions[:15])
    send_message(chat_id, text, kb)
    send_message(chat_id, "Выберите аккаунт для деталей:", kb_analytics_risk_actions())


def _calculate_account_risk(account: Dict) -> Dict:
    """Calculate risk score for account"""
    risk_score = 0.0
    factors = []
    recommendations = []
    
    # Factor 1: Consecutive errors (0-25%)
    consecutive_errors = account.get('consecutive_errors', 0) or 0
    if consecutive_errors >= 5:
        risk_score += 0.25
        factors.append(f"Ошибок подряд: {consecutive_errors}")
        recommendations.append("Приостановите использование на 2-4 часа")
    elif consecutive_errors >= 3:
        risk_score += 0.15
        factors.append(f"Ошибок подряд: {consecutive_errors}")
    elif consecutive_errors >= 1:
        risk_score += 0.05
    
    # Factor 2: Reliability score (0-20%)
    reliability = account.get('reliability_score', 100) or 100
    if reliability < 30:
        risk_score += 0.20
        factors.append(f"Низкая надёжность: {reliability}%")
        recommendations.append("Рекомендуется дать отдых аккаунту")
    elif reliability < 50:
        risk_score += 0.10
        factors.append(f"Сниженная надёжность: {reliability}%")
    elif reliability < 70:
        risk_score += 0.05
    
    # Factor 3: Daily usage (0-20%)
    daily_sent = account.get('daily_sent', 0) or 0
    daily_limit = account.get('daily_limit', 50) or 50
    usage_rate = daily_sent / daily_limit if daily_limit > 0 else 0
    
    if usage_rate >= 0.9:
        risk_score += 0.20
        factors.append(f"Использование: {int(usage_rate*100)}% лимита")
        recommendations.append("Лимит почти исчерпан, переключитесь на другой аккаунт")
    elif usage_rate >= 0.7:
        risk_score += 0.10
        factors.append(f"Использование: {int(usage_rate*100)}% лимита")
    
    # Factor 4: Flood wait status (0-20%)
    if account.get('status') == 'flood_wait':
        risk_score += 0.20
        factors.append("Активный FloodWait")
        recommendations.append("Дождитесь снятия ограничения")
    
    # Factor 5: Account age estimation (0-15%)
    created_at = account.get('created_at')
    if created_at:
        try:
            from core.timezone import parse_datetime, now_moscow
            created = parse_datetime(created_at)
            if created:
                age_days = (now_moscow() - created).days
                if age_days < 3:
                    risk_score += 0.15
                    factors.append(f"Новый аккаунт: {age_days} дней")
                    recommendations.append("Новым аккаунтам нужен прогрев")
                elif age_days < 7:
                    risk_score += 0.08
                    factors.append(f"Молодой аккаунт: {age_days} дней")
        except:
            pass
    
    # Determine action
    if risk_score > RISK_HIGH:
        action = 'stop'
    elif risk_score > RISK_MEDIUM:
        action = 'reduce'
    else:
        action = 'continue'
    
    # Default recommendation
    if not recommendations:
        if action == 'stop':
            recommendations.append("Рекомендуется остановить использование")
        elif action == 'reduce':
            recommendations.append("Снизьте нагрузку на 50%")
        else:
            recommendations.append("Аккаунт в хорошем состоянии")
    
    return {
        'risk_score': min(risk_score, 1.0),
        'risk_percent': int(min(risk_score, 1.0) * 100),
        'factors': factors,
        'recommendations': recommendations,
        'suggested_action': action
    }


def _handle_risks(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle risk actions"""
    if text == '🛡 Авто-защита':
        # Enable auto-protection
        settings = DB.get_user_settings(user_id)
        settings['auto_risk_protection'] = True
        DB.update_user_settings(user_id, auto_risk_protection=True)
        
        send_message(chat_id,
            "✅ <b>Авто-защита включена</b>\n\n"
            "Система будет автоматически:\n"
            "• Снижать нагрузку на рисковые аккаунты\n"
            "• Приостанавливать критичные аккаунты\n"
            "• Уведомлять о проблемах",
            kb_analytics_risk_actions()
        )
        return True
    
    if text == '⏸ Пауза рисковых':
        # Pause high-risk accounts
        accounts = DB.get_active_accounts(user_id)
        paused = 0
        
        for acc in accounts:
            risk = _calculate_account_risk(acc)
            if risk['risk_score'] > RISK_HIGH:
                DB.update_account(acc['id'], status='paused_risk')
                paused += 1
        
        send_message(chat_id,
            f"⏸ <b>Приостановлено аккаунтов: {paused}</b>\n\n"
            f"Аккаунты с высоким риском временно отключены.\n"
            f"Возобновите вручную после снижения риска.",
            kb_analytics_risk_actions()
        )
        return True
    
    if text == '🔄 Обновить прогноз':
        show_risk_predictions(chat_id, user_id)
        return True
    
    return False


def _handle_risk_account(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle individual account risk view"""
    account_id = int(state.split(':')[2])
    account = DB.get_account(account_id)
    
    if not account:
        show_risk_predictions(chat_id, user_id)
        return True
    
    if text == '⏸ Приостановить':
        DB.update_account(account_id, status='paused_risk')
        send_message(chat_id, "✅ Аккаунт приостановлен", kb_analytics_menu())
        show_risk_predictions(chat_id, user_id)
        return True
    
    if text == '▶️ Возобновить':
        DB.update_account(account_id, status='active', consecutive_errors=0)
        send_message(chat_id, "✅ Аккаунт возобновлён", kb_analytics_menu())
        show_risk_predictions(chat_id, user_id)
        return True
    
    return False


# ==================== SEGMENTATION ====================

def show_segments_menu(chat_id: int, user_id: int):
    """Show segmentation menu"""
    DB.set_user_state(user_id, 'analytics:segments')
    
    segments = DB.get_audience_segments(user_id)
    
    # Group by type
    hot = [s for s in segments if s.get('segment_type') == 'hot']
    warm = [s for s in segments if s.get('segment_type') == 'warm']
    cold = [s for s in segments if s.get('segment_type') == 'cold']
    
    text = f"📊 <b>Сегментация аудитории</b>\n\n"
    text += f"<b>Сегменты по вовлечённости:</b>\n"
    text += f"🔥 Горячие (ответили): <b>{sum(s.get('user_count', 0) for s in hot)}</b>\n"
    text += f"🌡 Тёплые (прочитали): <b>{sum(s.get('user_count', 0) for s in warm)}</b>\n"
    text += f"❄️ Холодные (не открыли): <b>{sum(s.get('user_count', 0) for s in cold)}</b>\n\n"
    
    if segments:
        text += f"<b>Всего сегментов:</b> {len(segments)}\n"
    else:
        text += "Сегменты создаются автоматически после рассылок.\n"
    
    send_message(chat_id, text, kb_analytics_segments())


def _handle_segments_menu(chat_id: int, user_id: int, text: str) -> bool:
    """Handle segments menu"""
    if text in ['🔥 Горячие', '🌡 Тёплые', '❄️ Холодные']:
        segment_type = {'🔥 Горячие': 'hot', '🌡 Тёплые': 'warm', '❄️ Холодные': 'cold'}.get(text)
        segments = DB.get_audience_segments(user_id)
        filtered = [s for s in segments if s.get('segment_type') == segment_type]
        
        if not filtered:
            send_message(chat_id, f"В категории «{text}» пока нет сегментов.", kb_analytics_segments())
            return True
        
        kb = kb_inline_segments(filtered)
        send_message(chat_id, f"<b>{text}</b> сегменты:", kb)
        return True
    
    if text == '📋 Все сегменты':
        segments = DB.get_audience_segments(user_id)
        if not segments:
            send_message(chat_id, "Нет созданных сегментов.", kb_analytics_segments())
            return True
        
        kb = kb_inline_segments(segments)
        send_message(chat_id, "📋 <b>Все сегменты:</b>", kb)
        return True
    
    if text == '➕ Создать из рассылки':
        # Show campaigns to segment
        campaigns = DB.get_campaigns(user_id)
        completed = [c for c in campaigns if c.get('status') == 'completed']
        
        if not completed:
            send_message(chat_id,
                "❌ Нет завершённых рассылок для сегментации.\n\n"
                "Проведите рассылку, затем создайте сегменты.",
                kb_analytics_segments()
            )
            return True
        
        text = "📊 <b>Выберите рассылку для сегментации:</b>\n\n"
        buttons = []
        for c in completed[:10]:
            sent = c.get('sent_count', 0)
            buttons.append([{
                'text': f"#{c['id']} — {sent} получателей",
                'callback_data': f"aseg:create:{c['id']}"
            }])
        
        send_message(chat_id, text, inline_keyboard(buttons))
        return True
    
    return False


def _handle_segment_campaign(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle campaign selection for segmentation"""
    # Handled via callback
    return False


def _handle_segment_view(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle segment view"""
    segment_id = int(state.split(':')[2])
    segment = DB.get_audience_segment(segment_id)
    
    if not segment:
        show_segments_menu(chat_id, user_id)
        return True
    
    if text == '📤 Рассылка по сегменту':
        # Create audience source from segment
        send_message(chat_id,
            "🚧 <b>Функция в разработке</b>\n\n"
            "Скоро можно будет делать рассылку по сегментам.",
            kb_analytics_segments()
        )
        return True
    
    if text == '🗑 Удалить сегмент':
        DB.delete_audience_segment(segment_id)
        send_message(chat_id, "✅ Сегмент удалён", kb_analytics_segments())
        show_segments_menu(chat_id, user_id)
        return True
    
    return False


def create_segments_from_campaign(user_id: int, campaign_id: int) -> Dict:
    """Create segments from campaign results"""
    # This would be called after campaign completion
    # For now, placeholder implementation
    
    # Get campaign results
    campaign = DB.get_campaign(campaign_id)
    if not campaign:
        return {'error': 'Campaign not found'}
    
    # Placeholder - in real implementation, analyze responses
    hot_users = []
    warm_users = []
    cold_users = []
    
    # Create segments
    segments_created = []
    
    if hot_users:
        seg = DB.create_audience_segment(
            user_id=user_id,
            name=f"[HOT] Кампания #{campaign_id}",
            segment_type='hot',
            user_ids=hot_users,
            campaign_id=campaign_id
        )
        if seg:
            segments_created.append(seg)
    
    if warm_users:
        seg = DB.create_audience_segment(
            user_id=user_id,
            name=f"[WARM] Кампания #{campaign_id}",
            segment_type='warm',
            user_ids=warm_users,
            campaign_id=campaign_id
        )
        if seg:
            segments_created.append(seg)
    
    if cold_users:
        seg = DB.create_audience_segment(
            user_id=user_id,
            name=f"[COLD] Кампания #{campaign_id}",
            segment_type='cold',
            user_ids=cold_users,
            campaign_id=campaign_id
        )
        if seg:
            segments_created.append(seg)
    
    return {
        'segments_created': len(segments_created),
        'hot_count': len(hot_users),
        'warm_count': len(warm_users),
        'cold_count': len(cold_users)
    }


# ==================== EFFECTIVENESS ====================

def show_effectiveness(chat_id: int, user_id: int):
    """Show campaign effectiveness analysis"""
    DB.set_user_state(user_id, 'analytics:effectiveness')
    
    # Get campaigns
    campaigns = DB.get_campaigns(user_id)
    completed = [c for c in campaigns if c.get('status') == 'completed']
    
    if not completed:
        send_message(chat_id,
            "📈 <b>Эффективность кампаний</b>\n\n"
            "Нет завершённых рассылок для анализа.\n\n"
            "Проведите рассылку для получения статистики.",
            kb_analytics_menu()
        )
        return
    
    # Calculate overall stats
    total_sent = sum(c.get('sent_count', 0) for c in completed)
    total_failed = sum(c.get('failed_count', 0) for c in completed)
    success_rate = total_sent / (total_sent + total_failed) * 100 if (total_sent + total_failed) > 0 else 0
    
    # Best and worst campaigns
    completed_with_rate = []
    for c in completed:
        sent = c.get('sent_count', 0)
        failed = c.get('failed_count', 0)
        if sent + failed > 0:
            rate = sent / (sent + failed) * 100
            completed_with_rate.append({**c, 'rate': rate})
    
    completed_with_rate.sort(key=lambda x: x['rate'], reverse=True)
    
    text = f"📈 <b>Эффективность кампаний</b>\n\n"
    text += f"<b>Общая статистика:</b>\n"
    text += f"├ Кампаний: {len(completed)}\n"
    text += f"├ Отправлено: {total_sent}\n"
    text += f"├ Ошибок: {total_failed}\n"
    text += f"└ Успешность: <b>{success_rate:.1f}%</b>\n\n"
    
    if completed_with_rate:
        text += f"<b>🏆 Лучшие кампании:</b>\n"
        for c in completed_with_rate[:3]:
            text += f"  #{c['id']} — {c['rate']:.1f}% успеха\n"
        
        if len(completed_with_rate) > 3:
            text += f"\n<b>📉 Требуют внимания:</b>\n"
            for c in completed_with_rate[-3:]:
                if c['rate'] < 80:
                    text += f"  #{c['id']} — {c['rate']:.1f}% успеха\n"
    
    # Recommendations
    text += f"\n<b>💡 Рекомендации:</b>\n"
    if success_rate < 70:
        text += "• Увеличьте задержки между сообщениями\n"
        text += "• Проверьте качество аудитории\n"
    elif success_rate < 90:
        text += "• Хорошие показатели, продолжайте\n"
        text += "• Попробуйте оптимальное время рассылки\n"
    else:
        text += "• Отличные показатели!\n"
        text += "• Можно немного увеличить скорость\n"
    
    send_message(chat_id, text, reply_keyboard([
        ['📊 По часам', '📅 По дням'],
        ['◀️ Назад']
    ]))


def _handle_effectiveness(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle effectiveness actions"""
    if text == '📊 По часам':
        # Show hourly breakdown
        stats = DB.get_hourly_stats(user_id)
        
        if not stats:
            send_message(chat_id, "Недостаточно данных", kb_analytics_menu())
            return True
        
        text = "📊 <b>Эффективность по часам (МСК):</b>\n\n"
        
        hourly = {}
        for s in stats:
            hour = s.get('hour', 0)
            sent = s.get('total_sent', 0)
            success = s.get('total_success', 0)
            if sent > 0:
                hourly[hour] = success / sent * 100
        
        for hour in sorted(hourly.keys()):
            rate = hourly[hour]
            emoji = '🟢' if rate >= 90 else '🟡' if rate >= 70 else '🔴'
            bar = '█' * int(rate / 10) + '░' * (10 - int(rate / 10))
            text += f"{emoji} {hour:02d}:00 [{bar}] {rate:.0f}%\n"
        
        send_message(chat_id, text, kb_analytics_menu())
        return True
    
    if text == '📅 По дням':
        # Show daily breakdown
        stats = DB.get_hourly_stats(user_id)
        
        daily = {}
        for s in stats:
            day = s.get('day_of_week', 0)
            sent = s.get('total_sent', 0)
            success = s.get('total_success', 0)
            if day not in daily:
                daily[day] = {'sent': 0, 'success': 0}
            daily[day]['sent'] += sent
            daily[day]['success'] += success
        
        text = "📅 <b>Эффективность по дням:</b>\n\n"
        
        for day in range(7):
            if day in daily and daily[day]['sent'] > 0:
                rate = daily[day]['success'] / daily[day]['sent'] * 100
                emoji = '🟢' if rate >= 90 else '🟡' if rate >= 70 else '🔴'
                text += f"{emoji} {DAY_NAMES[day]}: {rate:.0f}% ({daily[day]['sent']} отпр.)\n"
            else:
                text += f"⚪ {DAY_NAMES[day]}: нет данных\n"
        
        send_message(chat_id, text, kb_analytics_menu())
        return True
    
    return False


# ==================== LEARNING ====================

def show_learning_menu(chat_id: int, user_id: int):
    """Show learning/knowledge base menu"""
    DB.set_user_state(user_id, 'analytics:learning')
    
    settings = DB.get_user_settings(user_id)
    learning_enabled = settings.get('learning_mode', True)
    auto_recovery = settings.get('auto_recovery_mode', True)
    
    knowledge = DB.get_herder_knowledge_stats(user_id)
    
    text = f"🧠 <b>Обучение системы</b>\n\n"
    text += f"<b>Режимы:</b>\n"
    text += f"├ Обучение: {'✅ вкл' if learning_enabled else '❌ выкл'}\n"
    text += f"└ Авто-восстановление: {'✅ вкл' if auto_recovery else '❌ выкл'}\n\n"
    text += f"<b>База знаний:</b>\n"
    text += f"├ Плохих фраз: {knowledge.get('bad_phrases', 0)}\n"
    text += f"├ Хороших паттернов: {knowledge.get('good_patterns', 0)}\n"
    text += f"├ Рисковых каналов: {knowledge.get('risky_channels', 0)}\n"
    text += f"└ Всего записей: {knowledge.get('total', 0)}\n\n"
    text += "Система обучается на:\n"
    text += "• Удалённых комментариях\n"
    text += "• Успешных взаимодействиях\n"
    text += "• FloodWait и ошибках"
    
    send_message(chat_id, text, reply_keyboard([
        ['📚 Режим обучения', '🔄 Авто-восстановление'],
        ['➕ Добавить плохую фразу'],
        ['📋 Просмотр базы', '🗑 Очистить базу'],
        ['◀️ Назад']
    ]))


def _handle_learning(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle learning menu"""
    if text == '📚 Режим обучения':
        settings = DB.get_user_settings(user_id)
        current = settings.get('learning_mode', True)
        DB.update_user_settings(user_id, learning_mode=not current)
        
        status = '✅ включён' if not current else '❌ отключён'
        send_message(chat_id, f"Режим обучения: {status}", kb_analytics_menu())
        show_learning_menu(chat_id, user_id)
        return True
    
    if text == '🔄 Авто-восстановление':
        settings = DB.get_user_settings(user_id)
        current = settings.get('auto_recovery_mode', True)
        DB.update_user_settings(user_id, auto_recovery_mode=not current)
        
        status = '✅ включено' if not current else '❌ отключено'
        send_message(chat_id, f"Авто-восстановление: {status}", kb_analytics_menu())
        show_learning_menu(chat_id, user_id)
        return True
    
    if text == '➕ Добавить плохую фразу':
        DB.set_user_state(user_id, 'analytics:learning:bad_phrase', {})
        send_message(chat_id,
            "➕ <b>Добавление плохой фразы</b>\n\n"
            "Введите фразу, которую НЕ следует использовать в комментариях.\n\n"
            "Примеры:\n"
            "• слишком рекламно\n"
            "• кликбейтные фразы\n"
            "• спамные конструкции",
            kb_back_cancel()
        )
        return True
    
    if text == '📋 Просмотр базы':
        knowledge = DB.get_herder_knowledge(user_id)
        
        if not knowledge:
            send_message(chat_id, "База знаний пуста", kb_analytics_menu())
            return True
        
        text = "📋 <b>База знаний (последние 20):</b>\n\n"
        
        type_emoji = {
            'bad_phrase': '🚫',
            'good_pattern': '✅',
            'risky_channel': '⚠️',
            'effective_time': '⏰'
        }
        
        for k in knowledge[:20]:
            emoji = type_emoji.get(k.get('type'), '📝')
            value = k.get('value', '')[:30]
            hits = k.get('hits_count', 0)
            text += f"{emoji} {value} ({hits} использований)\n"
        
        send_message(chat_id, text, kb_analytics_menu())
        show_learning_menu(chat_id, user_id)
        return True
    
    if text == '🗑 Очистить базу':
        DB.clear_herder_knowledge(user_id)
        send_message(chat_id, "✅ База знаний очищена", kb_analytics_menu())
        show_learning_menu(chat_id, user_id)
        return True
    
    return False


def _handle_add_bad_phrase(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle adding bad phrase"""
    phrase = text.strip().lower()
    
    if len(phrase) < 3:
        send_message(chat_id, "❌ Фраза слишком короткая (минимум 3 символа)", kb_back_cancel())
        return True
    
    if len(phrase) > 200:
        phrase = phrase[:200]
    
    result = DB.add_herder_knowledge(user_id, 'bad_phrase', phrase, {'source': 'manual'})
    
    if result:
        send_message(chat_id, f"✅ Фраза «{phrase}» добавлена в базу", kb_analytics_menu())
    else:
        send_message(chat_id, "❌ Ошибка добавления", kb_analytics_menu())
    
    show_learning_menu(chat_id, user_id)
    return True


# ==================== CALLBACKS ====================

def handle_analytics_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle analytics inline callbacks"""
    
    # Risk account selection
    if data.startswith('arisk:'):
        account_id = int(data.split(':')[1])
        show_risk_account_details(chat_id, user_id, account_id)
        return True
    
    # Segment selection
    if data.startswith('aseg:'):
        parts = data.split(':')
        if len(parts) >= 3 and parts[1] == 'create':
            campaign_id = int(parts[2])
            _create_segments_for_campaign(chat_id, user_id, campaign_id)
            return True
        
        segment_id = int(parts[1])
        show_segment_details(chat_id, user_id, segment_id)
        return True
    
    return False


def show_risk_account_details(chat_id: int, user_id: int, account_id: int):
    """Show detailed risk info for account"""
    account = DB.get_account(account_id)
    if not account:
        send_message(chat_id, "❌ Аккаунт не найден", kb_analytics_menu())
        return
    
    DB.set_user_state(user_id, f'analytics:risk:{account_id}')
    
    risk = _calculate_account_risk(account)
    
    phone = account['phone']
    masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
    
    # Risk emoji
    if risk['risk_score'] > RISK_HIGH:
        risk_emoji = '🔴'
        risk_level = 'Высокий'
    elif risk['risk_score'] > RISK_MEDIUM:
        risk_emoji = '🟡'
        risk_level = 'Средний'
    else:
        risk_emoji = '🟢'
        risk_level = 'Низкий'
    
    text = f"⚠️ <b>Прогноз риска</b>\n\n"
    text += f"📱 Аккаунт: <code>{masked}</code>\n"
    text += f"{risk_emoji} Риск: <b>{risk['risk_percent']}%</b> ({risk_level})\n\n"
    
    if risk['factors']:
        text += "<b>Факторы риска:</b>\n"
        for factor in risk['factors']:
            text += f"• {factor}\n"
        text += "\n"
    
    text += "<b>💡 Рекомендации:</b>\n"
    for rec in risk['recommendations']:
        text += f"• {rec}\n"
    
    # Action buttons based on status
    if account.get('status') == 'active':
        kb = reply_keyboard([
            ['⏸ Приостановить'],
            ['◀️ Назад']
        ])
    else:
        kb = reply_keyboard([
            ['▶️ Возобновить'],
            ['◀️ Назад']
        ])
    
    send_message(chat_id, text, kb)


def show_segment_details(chat_id: int, user_id: int, segment_id: int):
    """Show segment details"""
    segment = DB.get_audience_segment(segment_id)
    if not segment:
        send_message(chat_id, "❌ Сегмент не найден", kb_analytics_menu())
        return
    
    DB.set_user_state(user_id, f'analytics:segment:{segment_id}')
    
    type_emoji = {'hot': '🔥', 'warm': '🌡', 'cold': '❄️', 'custom': '📊'}.get(segment.get('segment_type'), '📊')
    
    text = f"{type_emoji} <b>{segment['name']}</b>\n\n"
    text += f"👥 Пользователей: <b>{segment.get('user_count', 0)}</b>\n"
    text += f"📅 Создан: {segment.get('created_at', '')[:10]}\n"
    
    if segment.get('campaign_id'):
        text += f"📤 Из кампании: #{segment['campaign_id']}\n"
    
    send_message(chat_id, text, reply_keyboard([
        ['📤 Рассылка по сегменту'],
        ['🗑 Удалить сегмент'],
        ['◀️ Назад']
    ]))


def _create_segments_for_campaign(chat_id: int, user_id: int, campaign_id: int):
    """Create segments from campaign"""
    send_message(chat_id, "⏳ Создаю сегменты...", kb_cancel())
    
    result = create_segments_from_campaign(user_id, campaign_id)
    
    if result.get('error'):
        send_message(chat_id, f"❌ {result['error']}", kb_analytics_segments())
    else:
        send_message(chat_id,
            f"✅ <b>Сегменты созданы!</b>\n\n"
            f"🔥 Горячие: {result.get('hot_count', 0)}\n"
            f"🌡 Тёплые: {result.get('warm_count', 0)}\n"
            f"❄️ Холодные: {result.get('cold_count', 0)}",
            kb_analytics_segments()
        )
    
    show_segments_menu(chat_id, user_id)
