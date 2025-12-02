"""
Parsing handlers - Chat and Comments parsing
Extended v3.0 with AI/Semantic parsing
"""
import re
import logging
from typing import List, Dict, Optional
from core.db import DB
from core.telegram import send_message
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back_cancel,
    kb_parse_msg_limit, kb_parse_filter_yn, kb_parse_confirm,
    kb_comments_range, kb_min_length, kb_keyword_filter, kb_keyword_match_mode,
    reply_keyboard
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK

logger = logging.getLogger(__name__)


# ==================== KEYBOARDS для ИИ-парсинга ====================

def kb_parse_mode():
    """Выбор режима парсинга"""
    return reply_keyboard([
        ['📝 По ключевым словам'],
        ['🧠 Семантический (ИИ)'],
        ['⏭ Без фильтра'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_semantic_depth():
    """Глубина семантического поиска"""
    return reply_keyboard([
        ['🎯 Узкий (точное соответствие)'],
        ['📊 Средний (смежные темы)'],
        ['🌐 Широкий (общая область)'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_semantic_threshold():
    """Порог релевантности"""
    return reply_keyboard([
        ['90% (только точные)', '70% (рекомендуется)'],
        ['50% (больше результатов)'],
        ['◀️ Назад', '❌ Отмена']
    ])


# ==================== CHAT PARSING ====================

def start_chat_parsing(chat_id: int, user_id: int):
    """Start chat parsing flow"""
    # Проверяем наличие активных аккаунтов
    account = DB.get_any_active_account(user_id)
    if not account:
        send_message(chat_id,
            "❌ <b>Нет активных аккаунтов</b>\n\n"
            "Для парсинга нужен хотя бы один авторизованный аккаунт.\n"
            "Добавьте аккаунт в разделе «👤 Аккаунты».",
            kb_main_menu()
        )
        return
    
    DB.set_user_state(user_id, 'parse_chat:link', {'account_id': account['id']})
    
    send_message(chat_id,
        "🔍 <b>Парсинг чатов</b>\n\n"
        "Введите ссылку на чат/канал для парсинга:\n\n"
        "Примеры:\n"
        "• @username\n"
        "• https://t.me/username\n"
        "• https://t.me/+AbCdEfG (приватная ссылка)\n\n"
        "⚠️ Бот должен быть участником приватных чатов",
        kb_cancel()
    )


def handle_chat_parsing(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle chat parsing states"""
    
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Парсинг отменён")
        return True
    
    if text == BTN_BACK or text == '◀️ Назад':
        return _handle_chat_back(chat_id, user_id, state, saved)
    
    # Step 1: Link input
    if state == 'parse_chat:link':
        return _handle_chat_link(chat_id, user_id, text, saved)
    
    # Step 2: Message limit
    if state == 'parse_chat:limit':
        return _handle_chat_limit(chat_id, user_id, text, saved)
    
    # Step 3: Parse mode selection (keywords / semantic / none)
    if state == 'parse_chat:mode':
        return _handle_chat_mode(chat_id, user_id, text, saved)
    
    # Step 4a: Keywords input
    if state == 'parse_chat:keywords':
        return _handle_chat_keywords(chat_id, user_id, text, saved)
    
    # Step 4b: Keyword match mode
    if state == 'parse_chat:keyword_mode':
        return _handle_chat_keyword_mode(chat_id, user_id, text, saved)
    
    # Step 5a: Semantic topic input
    if state == 'parse_chat:semantic_topic':
        return _handle_chat_semantic_topic(chat_id, user_id, text, saved)
    
    # Step 5b: Semantic depth
    if state == 'parse_chat:semantic_depth':
        return _handle_chat_semantic_depth(chat_id, user_id, text, saved)
    
    # Step 5c: Semantic threshold
    if state == 'parse_chat:semantic_threshold':
        return _handle_chat_semantic_threshold(chat_id, user_id, text, saved)
    
    # Step 6: Activity filter
    if state == 'parse_chat:activity':
        return _handle_chat_activity(chat_id, user_id, text, saved)
    
    # Step 7: Username filter
    if state == 'parse_chat:username':
        return _handle_chat_username_filter(chat_id, user_id, text, saved)
    
    # Step 8: Photo filter
    if state == 'parse_chat:photo':
        return _handle_chat_photo_filter(chat_id, user_id, text, saved)
    
    # Step 9: Bots filter
    if state == 'parse_chat:bots':
        return _handle_chat_bots_filter(chat_id, user_id, text, saved)
    
    # Step 10: Confirm
    if state == 'parse_chat:confirm':
        return _handle_chat_confirm(chat_id, user_id, text, saved)
    
    return False


def _handle_chat_back(chat_id: int, user_id: int, state: str, saved: dict) -> bool:
    """Handle back navigation in chat parsing"""
    steps = {
        'parse_chat:limit': 'parse_chat:link',
        'parse_chat:mode': 'parse_chat:limit',
        'parse_chat:keywords': 'parse_chat:mode',
        'parse_chat:keyword_mode': 'parse_chat:keywords',
        'parse_chat:semantic_topic': 'parse_chat:mode',
        'parse_chat:semantic_depth': 'parse_chat:semantic_topic',
        'parse_chat:semantic_threshold': 'parse_chat:semantic_depth',
        'parse_chat:activity': 'parse_chat:mode',
        'parse_chat:username': 'parse_chat:activity',
        'parse_chat:photo': 'parse_chat:username',
        'parse_chat:bots': 'parse_chat:photo',
        'parse_chat:confirm': 'parse_chat:bots'
    }
    
    prev_state = steps.get(state)
    if prev_state:
        DB.set_user_state(user_id, prev_state, saved)
        _show_chat_step(chat_id, user_id, prev_state, saved)
        return True
    
    show_main_menu(chat_id, user_id)
    return True


def _show_chat_step(chat_id: int, user_id: int, state: str, saved: dict):
    """Show specific step in chat parsing"""
    if state == 'parse_chat:link':
        start_chat_parsing(chat_id, user_id)
    elif state == 'parse_chat:limit':
        send_message(chat_id,
            f"📊 <b>Лимит сообщений</b>\n\n"
            f"Чат: <code>{saved.get('source_link', '?')}</code>\n\n"
            f"Сколько последних сообщений анализировать?",
            kb_parse_msg_limit()
        )
    elif state == 'parse_chat:mode':
        send_message(chat_id,
            "🔍 <b>Режим фильтрации</b>\n\n"
            "Выберите как фильтровать пользователей:\n\n"
            "📝 <b>По ключевым словам</b>\n"
            "   Поиск конкретных слов в сообщениях\n\n"
            "🧠 <b>Семантический (ИИ)</b>\n"
            "   Поиск по смыслу через Yandex GPT\n"
            "   Находит релевантных даже без точных слов\n\n"
            "⏭ <b>Без фильтра</b>\n"
            "   Собрать всех активных участников",
            kb_parse_mode()
        )
    elif state == 'parse_chat:keywords':
        send_message(chat_id,
            "📝 <b>Ключевые слова</b>\n\n"
            "Введите слова через запятую:\n\n"
            "Пример: <code>купить, заказать, цена, прайс</code>",
            kb_back_cancel()
        )
    elif state == 'parse_chat:semantic_topic':
        send_message(chat_id,
            "🧠 <b>Семантический поиск</b>\n\n"
            "Опишите тему или интерес целевой аудитории:\n\n"
            "Примеры:\n"
            "• <code>автоматизация маркетинга в Telegram</code>\n"
            "• <code>люди, интересующиеся криптовалютой</code>\n"
            "• <code>владельцы малого бизнеса</code>\n\n"
            "ИИ найдёт пользователей, чьи сообщения соответствуют теме по смыслу.",
            kb_back_cancel()
        )
    elif state == 'parse_chat:activity':
        send_message(chat_id,
            "📊 <b>Фильтр по активности</b>\n\n"
            "Фильтровать пользователей по времени последнего онлайна?",
            kb_parse_filter_yn()
        )
    elif state == 'parse_chat:username':
        send_message(chat_id,
            "👤 <b>Фильтр по username</b>\n\n"
            "Собирать только пользователей с @username?\n\n"
            "⚠️ <i>Без username невозможно отправить сообщение</i>",
            kb_parse_filter_yn()
        )
    elif state == 'parse_chat:photo':
        send_message(chat_id,
            "🖼 <b>Фильтр по фото профиля</b>\n\n"
            "Собирать только пользователей с аватаркой?",
            kb_parse_filter_yn()
        )
    elif state == 'parse_chat:bots':
        send_message(chat_id,
            "🤖 <b>Исключить ботов</b>\n\n"
            "Исключить аккаунты ботов из результатов?",
            kb_parse_filter_yn()
        )


def _handle_chat_link(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle chat link input"""
    link = text.strip()
    
    # Validate link format
    if not _is_valid_chat_link(link):
        send_message(chat_id,
            "❌ Неверный формат ссылки\n\n"
            "Введите корректную ссылку на чат/канал:",
            kb_cancel()
        )
        return True
    
    saved['source_link'] = link
    saved['source_type'] = 'chat'
    DB.set_user_state(user_id, 'parse_chat:limit', saved)
    
    send_message(chat_id,
        f"✅ Чат: <code>{link}</code>\n\n"
        f"📊 <b>Лимит сообщений</b>\n\n"
        f"Сколько последних сообщений анализировать?",
        kb_parse_msg_limit()
    )
    return True


def _handle_chat_limit(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle message limit selection"""
    if text == '📝 Свой лимит':
        send_message(chat_id,
            "Введите число (от 100 до 10000):",
            kb_back_cancel()
        )
        return True
    
    try:
        limit = int(text.replace(' ', ''))
        if limit < 100:
            limit = 100
        if limit > 10000:
            limit = 10000
    except ValueError:
        send_message(chat_id,
            "❌ Введите число или выберите из предложенных:",
            kb_parse_msg_limit()
        )
        return True
    
    saved['message_limit'] = limit
    DB.set_user_state(user_id, 'parse_chat:mode', saved)
    
    send_message(chat_id,
        f"✅ Лимит: <b>{limit}</b> сообщений\n\n"
        f"🔍 <b>Режим фильтрации</b>\n\n"
        f"Выберите как фильтровать пользователей:\n\n"
        f"📝 <b>По ключевым словам</b>\n"
        f"   Поиск конкретных слов в сообщениях\n\n"
        f"🧠 <b>Семантический (ИИ)</b>\n"
        f"   Поиск по смыслу через Yandex GPT\n"
        f"   Находит релевантных даже без точных слов\n\n"
        f"⏭ <b>Без фильтра</b>\n"
        f"   Собрать всех активных участников",
        kb_parse_mode()
    )
    return True


def _handle_chat_mode(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle parse mode selection"""
    if text == '📝 По ключевым словам':
        saved['filter_mode'] = 'keywords'
        DB.set_user_state(user_id, 'parse_chat:keywords', saved)
        
        send_message(chat_id,
            "📝 <b>Ключевые слова</b>\n\n"
            "Введите слова/фразы через запятую:\n\n"
            "Пример: <code>купить, заказать, цена, интересует</code>\n\n"
            "Будут найдены пользователи, в чьих сообщениях есть эти слова.",
            kb_back_cancel()
        )
        return True
    
    if text == '🧠 Семантический (ИИ)':
        # Проверяем наличие API ключа
        settings = DB.get_user_settings(user_id)
        if not settings.get('yagpt_api_key'):
            send_message(chat_id,
                "❌ <b>Yandex GPT не настроен</b>\n\n"
                "Для семантического поиска нужен API ключ Yandex GPT.\n\n"
                "Настройте его в разделе:\n"
                "⚙️ Настройки → 🔑 API ключи → Yandex GPT",
                kb_parse_mode()
            )
            return True
        
        saved['filter_mode'] = 'semantic'
        DB.set_user_state(user_id, 'parse_chat:semantic_topic', saved)
        
        send_message(chat_id,
            "🧠 <b>Семантический поиск</b>\n\n"
            "Опишите тему или интерес целевой аудитории:\n\n"
            "Примеры:\n"
            "• <code>автоматизация маркетинга в Telegram</code>\n"
            "• <code>люди, интересующиеся криптовалютой</code>\n"
            "• <code>владельцы малого бизнеса</code>\n"
            "• <code>разработчики Python</code>\n\n"
            "ИИ найдёт пользователей по смыслу, даже если они не использовали эти слова напрямую.",
            kb_back_cancel()
        )
        return True
    
    if text == '⏭ Без фильтра':
        saved['filter_mode'] = 'none'
        DB.set_user_state(user_id, 'parse_chat:activity', saved)
        
        send_message(chat_id,
            "📊 <b>Фильтр по активности</b>\n\n"
            "Фильтровать пользователей, которые были онлайн недавно?",
            kb_parse_filter_yn()
        )
        return True
    
    send_message(chat_id, "❌ Выберите режим из списка:", kb_parse_mode())
    return True


def _handle_chat_keywords(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle keywords input"""
    keywords = [k.strip().lower() for k in text.split(',') if k.strip()]
    
    if not keywords:
        send_message(chat_id,
            "❌ Введите хотя бы одно слово:\n\n"
            "Пример: <code>купить, заказать, цена</code>",
            kb_back_cancel()
        )
        return True
    
    if len(keywords) > 20:
        keywords = keywords[:20]
        send_message(chat_id, "⚠️ Оставлены первые 20 слов")
    
    saved['keywords'] = keywords
    DB.set_user_state(user_id, 'parse_chat:keyword_mode', saved)
    
    send_message(chat_id,
        f"✅ Ключевые слова ({len(keywords)}):\n"
        f"<code>{', '.join(keywords)}</code>\n\n"
        f"🔍 <b>Режим поиска:</b>\n\n"
        f"<b>Любое слово</b> — найти если есть хотя бы одно\n"
        f"<b>Все слова</b> — найти только если есть все слова",
        kb_keyword_match_mode()
    )
    return True


def _handle_chat_keyword_mode(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle keyword match mode"""
    if text == '🔍 Любое слово':
        saved['keyword_match_mode'] = 'any'
    elif text == '🔍 Все слова':
        saved['keyword_match_mode'] = 'all'
    else:
        send_message(chat_id, "❌ Выберите режим:", kb_keyword_match_mode())
        return True
    
    DB.set_user_state(user_id, 'parse_chat:activity', saved)
    
    send_message(chat_id,
        "📊 <b>Фильтр по активности</b>\n\n"
        "Фильтровать пользователей, которые были онлайн недавно?\n\n"
        "Это поможет исключить неактивные аккаунты.",
        kb_parse_filter_yn()
    )
    return True


def _handle_chat_semantic_topic(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle semantic topic input"""
    topic = text.strip()
    
    if len(topic) < 10:
        send_message(chat_id,
            "❌ Опишите тему подробнее (минимум 10 символов):\n\n"
            "Пример: <code>люди, интересующиеся автоматизацией бизнеса</code>",
            kb_back_cancel()
        )
        return True
    
    if len(topic) > 500:
        topic = topic[:500]
    
    saved['semantic_topic'] = topic
    DB.set_user_state(user_id, 'parse_chat:semantic_depth', saved)
    
    send_message(chat_id,
        f"✅ Тема: <i>{topic[:100]}{'...' if len(topic) > 100 else ''}</i>\n\n"
        f"🎯 <b>Глубина поиска</b>\n\n"
        f"<b>Узкий</b> — только точные совпадения по теме\n"
        f"<b>Средний</b> — включая смежные темы (рекомендуется)\n"
        f"<b>Широкий</b> — максимальный охват в общей области",
        kb_semantic_depth()
    )
    return True


def _handle_chat_semantic_depth(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle semantic depth selection"""
    if '🎯 Узкий' in text:
        saved['semantic_depth'] = 'narrow'
        saved['semantic_threshold'] = 0.85
    elif '📊 Средний' in text:
        saved['semantic_depth'] = 'medium'
        saved['semantic_threshold'] = 0.70
    elif '🌐 Широкий' in text:
        saved['semantic_depth'] = 'wide'
        saved['semantic_threshold'] = 0.50
    else:
        send_message(chat_id, "❌ Выберите глубину поиска:", kb_semantic_depth())
        return True
    
    DB.set_user_state(user_id, 'parse_chat:semantic_threshold', saved)
    
    depth_name = {'narrow': 'Узкий', 'medium': 'Средний', 'wide': 'Широкий'}.get(saved['semantic_depth'])
    
    send_message(chat_id,
        f"✅ Глубина: <b>{depth_name}</b>\n\n"
        f"📊 <b>Порог релевантности</b>\n\n"
        f"Минимальный процент соответствия теме:\n\n"
        f"<b>90%</b> — только самые релевантные (меньше результатов)\n"
        f"<b>70%</b> — баланс качества и количества\n"
        f"<b>50%</b> — больше результатов (возможны нерелевантные)",
        kb_semantic_threshold()
    )
    return True


def _handle_chat_semantic_threshold(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle semantic threshold selection"""
    if '90%' in text:
        saved['semantic_threshold'] = 0.90
    elif '70%' in text:
        saved['semantic_threshold'] = 0.70
    elif '50%' in text:
        saved['semantic_threshold'] = 0.50
    else:
        send_message(chat_id, "❌ Выберите порог:", kb_semantic_threshold())
        return True
    
    DB.set_user_state(user_id, 'parse_chat:activity', saved)
    
    send_message(chat_id,
        f"✅ Порог: <b>{int(saved['semantic_threshold'] * 100)}%</b>\n\n"
        f"📊 <b>Фильтр по активности</b>\n\n"
        f"Фильтровать пользователей по времени последнего онлайна?",
        kb_parse_filter_yn()
    )
    return True


def _handle_chat_activity(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle activity filter"""
    if text == '✅ Да':
        saved['filter_activity'] = True
        saved['activity_days'] = 30  # Последние 30 дней
    elif text == '❌ Нет':
        saved['filter_activity'] = False
    else:
        send_message(chat_id, "❌ Выберите Да или Нет:", kb_parse_filter_yn())
        return True
    
    # Next: username filter
    DB.set_user_state(user_id, 'parse_chat:username', saved)
    send_message(chat_id,
        "👤 <b>Фильтр по username</b>\n\n"
        "Собирать только пользователей с @username?\n\n"
        "⚠️ <i>Без username невозможно отправить сообщение</i>",
        kb_parse_filter_yn()
    )
    return True


def _handle_chat_username_filter(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle username filter"""
    if text == '✅ Да':
        saved['filter_username'] = True
    elif text == '❌ Нет':
        saved['filter_username'] = False
    else:
        send_message(chat_id, "❌ Выберите Да или Нет:", kb_parse_filter_yn())
        return True
    
    # Next: photo filter
    DB.set_user_state(user_id, 'parse_chat:photo', saved)
    send_message(chat_id,
        "🖼 <b>Фильтр по фото профиля</b>\n\n"
        "Собирать только пользователей с аватаркой?\n\n"
        "💡 <i>Аккаунты с фото обычно более активны</i>",
        kb_parse_filter_yn()
    )
    return True


def _handle_chat_photo_filter(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle photo filter"""
    if text == '✅ Да':
        saved['filter_photo'] = True
    elif text == '❌ Нет':
        saved['filter_photo'] = False
    else:
        send_message(chat_id, "❌ Выберите Да или Нет:", kb_parse_filter_yn())
        return True
    
    # Next: bot filter
    DB.set_user_state(user_id, 'parse_chat:bots', saved)
    send_message(chat_id,
        "🤖 <b>Исключить ботов</b>\n\n"
        "Исключить аккаунты ботов из результатов?\n\n"
        "💡 <i>Рекомендуется для рассылок</i>",
        kb_parse_filter_yn()
    )
    return True


def _handle_chat_bots_filter(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle bots filter"""
    if text == '✅ Да':
        saved['filter_bots'] = True
    elif text == '❌ Нет':
        saved['filter_bots'] = False
    else:
        send_message(chat_id, "❌ Выберите Да или Нет:", kb_parse_filter_yn())
        return True
    
    # Finally: confirm
    DB.set_user_state(user_id, 'parse_chat:confirm', saved)
    _show_chat_confirmation(chat_id, user_id, saved)
    return True


def _show_chat_confirmation(chat_id: int, user_id: int, saved: dict):
    """Show parsing confirmation"""
    mode_text = {
        'keywords': f"📝 Ключевые слова: {', '.join(saved.get('keywords', [])[:5])}{'...' if len(saved.get('keywords', [])) > 5 else ''}",
        'semantic': f"🧠 Семантический: {saved.get('semantic_topic', '')[:50]}...\n   Глубина: {saved.get('semantic_depth', 'medium')}, Порог: {int(saved.get('semantic_threshold', 0.7) * 100)}%",
        'none': '⏭ Без фильтра (все участники)'
    }.get(saved.get('filter_mode', 'none'), 'Не выбран')
    
    activity_text = "✅ Да (активные за 30 дней)" if saved.get('filter_activity') else "❌ Нет"
    
    # New filters
    username_text = "✅ Да" if saved.get('filter_username') else "❌ Нет"
    photo_text = "✅ Да" if saved.get('filter_photo') else "❌ Нет"
    bots_text = "✅ Да" if saved.get('filter_bots') else "❌ Нет"
    
    send_message(chat_id,
        f"📋 <b>Подтверждение парсинга</b>\n\n"
        f"📍 Чат: <code>{saved.get('source_link', '?')}</code>\n"
        f"📊 Лимит: <b>{saved.get('message_limit', 1000)}</b> сообщений\n\n"
        f"<b>Фильтрация контента:</b>\n{mode_text}\n\n"
        f"<b>Фильтры пользователей:</b>\n"
        f"├ Активность: {activity_text}\n"
        f"├ Только с username: {username_text}\n"
        f"├ Только с фото: {photo_text}\n"
        f"└ Исключить ботов: {bots_text}\n\n"
        f"⚠️ Парсинг может занять несколько минут.",
        kb_parse_confirm()
    )


def _handle_chat_confirm(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle parsing confirmation"""
    if text != '🚀 Запустить парсинг':
        show_main_menu(chat_id, user_id, "❌ Парсинг отменён")
        return True
    
    # Prepare filters
    filters = {
        'message_limit': saved.get('message_limit', 1000),
        'filter_activity': saved.get('filter_activity', False),
        'activity_days': saved.get('activity_days', 30),
        # New user filters
        'filter_username': saved.get('filter_username', False),
        'filter_photo': saved.get('filter_photo', False),
        'filter_bots': saved.get('filter_bots', False)
    }
    
    # Prepare keyword/semantic filters
    keyword_filter = None
    keyword_match_mode = 'any'
    semantic_config = None
    
    if saved.get('filter_mode') == 'keywords':
        keyword_filter = saved.get('keywords', [])
        keyword_match_mode = saved.get('keyword_match_mode', 'any')
    elif saved.get('filter_mode') == 'semantic':
        semantic_config = {
            'topic': saved.get('semantic_topic'),
            'depth': saved.get('semantic_depth', 'medium'),
            'threshold': saved.get('semantic_threshold', 0.7)
        }
        filters['semantic_config'] = semantic_config
    
    # Create audience source
    source = DB.create_audience_source(
        user_id=user_id,
        source_type='chat',
        source_link=saved.get('source_link'),
        filters=filters,
        keyword_filter=keyword_filter,
        keyword_match_mode=keyword_match_mode
    )
    
    if source:
        mode_info = ""
        if saved.get('filter_mode') == 'semantic':
            mode_info = "\n🧠 Используется ИИ-анализ (может занять больше времени)"
        
        send_message(chat_id,
            f"✅ <b>Задача создана!</b>\n\n"
            f"ID: #{source['id']}\n"
            f"Чат: <code>{saved.get('source_link')}</code>\n"
            f"Статус: ⏳ В очереди{mode_info}\n\n"
            f"Вы получите уведомление по завершении.",
            kb_main_menu()
        )
    else:
        send_message(chat_id, "❌ Ошибка создания задачи", kb_main_menu())
    
    DB.clear_user_state(user_id)
    return True


def _is_valid_chat_link(link: str) -> bool:
    """Validate chat link format"""
    if not link:
        return False
    
    patterns = [
        r'^@[\w]+$',  # @username
        r'^https?://t\.me/[\w]+$',  # https://t.me/username
        r'^t\.me/[\w]+$',  # t.me/username
        r'^https?://t\.me/\+[\w]+$',  # https://t.me/+invite
        r'^https?://t\.me/joinchat/[\w]+$',  # old invite format
    ]
    
    for pattern in patterns:
        if re.match(pattern, link, re.IGNORECASE):
            return True
    
    return False


# ==================== COMMENTS PARSING ====================

def start_comments_parsing(chat_id: int, user_id: int):
    """Start comments parsing flow"""
    account = DB.get_any_active_account(user_id)
    if not account:
        send_message(chat_id,
            "❌ <b>Нет активных аккаунтов</b>\n\n"
            "Для парсинга нужен авторизованный аккаунт.\n"
            "Добавьте аккаунт в разделе «👤 Аккаунты».",
            kb_main_menu()
        )
        return
    
    DB.set_user_state(user_id, 'parse_comments:link', {'account_id': account['id']})
    
    send_message(chat_id,
        "💬 <b>Парсинг комментариев</b>\n\n"
        "Введите ссылку на канал с комментариями:\n\n"
        "Пример: <code>@channel</code> или <code>https://t.me/channel</code>\n\n"
        "⚠️ У канала должны быть включены комментарии",
        kb_cancel()
    )


def handle_comments_parsing(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle comments parsing states"""
    
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Парсинг отменён")
        return True
    
    if text == BTN_BACK or text == '◀️ Назад':
        return _handle_comments_back(chat_id, user_id, state, saved)
    
    # Step 1: Link
    if state == 'parse_comments:link':
        return _handle_comments_link(chat_id, user_id, text, saved)
    
    # Step 2: Post range
    if state == 'parse_comments:range':
        return _handle_comments_range(chat_id, user_id, text, saved)
    
    # Step 3: Min comment length
    if state == 'parse_comments:min_length':
        return _handle_comments_min_length(chat_id, user_id, text, saved)
    
    # Step 4: Filter mode
    if state == 'parse_comments:mode':
        return _handle_comments_mode(chat_id, user_id, text, saved)
    
    # Step 5a: Keywords
    if state == 'parse_comments:keywords':
        return _handle_comments_keywords(chat_id, user_id, text, saved)
    
    # Step 5b: Keyword mode
    if state == 'parse_comments:keyword_mode':
        return _handle_comments_keyword_mode(chat_id, user_id, text, saved)
    
    # Step 6a: Semantic topic
    if state == 'parse_comments:semantic_topic':
        return _handle_comments_semantic_topic(chat_id, user_id, text, saved)
    
    # Step 6b: Semantic threshold
    if state == 'parse_comments:semantic_threshold':
        return _handle_comments_semantic_threshold(chat_id, user_id, text, saved)
    
    # Step 7: Confirm
    if state == 'parse_comments:confirm':
        return _handle_comments_confirm(chat_id, user_id, text, saved)
    
    return False


def _handle_comments_back(chat_id: int, user_id: int, state: str, saved: dict) -> bool:
    """Handle back in comments parsing"""
    steps = {
        'parse_comments:range': 'parse_comments:link',
        'parse_comments:min_length': 'parse_comments:range',
        'parse_comments:mode': 'parse_comments:min_length',
        'parse_comments:keywords': 'parse_comments:mode',
        'parse_comments:keyword_mode': 'parse_comments:keywords',
        'parse_comments:semantic_topic': 'parse_comments:mode',
        'parse_comments:semantic_threshold': 'parse_comments:semantic_topic',
        'parse_comments:confirm': 'parse_comments:mode'
    }
    
    prev_state = steps.get(state)
    if prev_state:
        DB.set_user_state(user_id, prev_state, saved)
        _show_comments_step(chat_id, user_id, prev_state, saved)
        return True
    
    show_main_menu(chat_id, user_id)
    return True


def _show_comments_step(chat_id: int, user_id: int, state: str, saved: dict):
    """Show specific step"""
    if state == 'parse_comments:link':
        start_comments_parsing(chat_id, user_id)
    elif state == 'parse_comments:range':
        send_message(chat_id,
            "📊 <b>Диапазон постов</b>\n\n"
            "С каких последних постов собирать комментарии?",
            kb_comments_range()
        )
    elif state == 'parse_comments:min_length':
        send_message(chat_id,
            "📏 <b>Минимальная длина комментария</b>\n\n"
            "Фильтровать короткие комментарии (спам, стикеры)?",
            kb_min_length()
        )
    elif state == 'parse_comments:mode':
        send_message(chat_id,
            "🔍 <b>Режим фильтрации</b>\n\n"
            "Как фильтровать авторов комментариев?",
            kb_parse_mode()
        )


def _handle_comments_link(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle channel link input"""
    link = text.strip()
    
    if not _is_valid_chat_link(link):
        send_message(chat_id,
            "❌ Неверный формат ссылки\n\n"
            "Введите ссылку на канал:",
            kb_cancel()
        )
        return True
    
    saved['source_link'] = link
    saved['source_type'] = 'comments'
    DB.set_user_state(user_id, 'parse_comments:range', saved)
    
    send_message(chat_id,
        f"✅ Канал: <code>{link}</code>\n\n"
        f"📊 <b>Диапазон постов</b>\n\n"
        f"С каких последних постов собирать комментарии?",
        kb_comments_range()
    )
    return True


def _handle_comments_range(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle post range selection"""
    if text == '📝 Свой диапазон':
        send_message(chat_id,
            "Введите диапазон (например: 1-30):",
            kb_back_cancel()
        )
        return True
    
    try:
        if '-' in text:
            parts = text.split('-')
            start = int(parts[0].strip())
            end = int(parts[1].strip())
        else:
            start = 1
            end = int(text)
        
        if start < 1:
            start = 1
        if end > 100:
            end = 100
        if start > end:
            start, end = end, start
            
    except ValueError:
        send_message(chat_id, "❌ Неверный формат", kb_comments_range())
        return True
    
    saved['post_range'] = [start, end]
    DB.set_user_state(user_id, 'parse_comments:min_length', saved)
    
    send_message(chat_id,
        f"✅ Посты: с {start} по {end}\n\n"
        f"📏 <b>Минимальная длина комментария</b>\n\n"
        f"Фильтровать короткие комментарии?",
        kb_min_length()
    )
    return True


def _handle_comments_min_length(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle minimum length"""
    if text == '📝 Свой':
        send_message(chat_id, "Введите минимальную длину (0-500):", kb_back_cancel())
        return True
    
    try:
        if '0' in text and 'все' in text.lower():
            min_len = 0
        else:
            min_len = int(text)
        
        if min_len < 0:
            min_len = 0
        if min_len > 500:
            min_len = 500
    except ValueError:
        send_message(chat_id, "❌ Введите число", kb_min_length())
        return True
    
    saved['min_comment_length'] = min_len
    DB.set_user_state(user_id, 'parse_comments:mode', saved)
    
    send_message(chat_id,
        f"✅ Мин. длина: <b>{min_len}</b> символов\n\n"
        f"🔍 <b>Режим фильтрации</b>\n\n"
        f"Как фильтровать авторов комментариев?\n\n"
        f"📝 <b>По ключевым словам</b> — поиск слов в комментариях\n"
        f"🧠 <b>Семантический (ИИ)</b> — поиск по смыслу\n"
        f"⏭ <b>Без фильтра</b> — все авторы комментариев",
        kb_parse_mode()
    )
    return True


def _handle_comments_mode(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle filter mode for comments"""
    if text == '📝 По ключевым словам':
        saved['filter_mode'] = 'keywords'
        DB.set_user_state(user_id, 'parse_comments:keywords', saved)
        
        send_message(chat_id,
            "📝 <b>Ключевые слова</b>\n\n"
            "Введите слова через запятую:\n\n"
            "Будут найдены авторы, в чьих комментариях есть эти слова.",
            kb_back_cancel()
        )
        return True
    
    if text == '🧠 Семантический (ИИ)':
        settings = DB.get_user_settings(user_id)
        if not settings.get('yagpt_api_key'):
            send_message(chat_id,
                "❌ <b>Yandex GPT не настроен</b>\n\n"
                "Настройте API ключ в разделе:\n"
                "⚙️ Настройки → 🔑 API ключи",
                kb_parse_mode()
            )
            return True
        
        saved['filter_mode'] = 'semantic'
        DB.set_user_state(user_id, 'parse_comments:semantic_topic', saved)
        
        send_message(chat_id,
            "🧠 <b>Семантический поиск</b>\n\n"
            "Опишите, какие комментарии искать:\n\n"
            "Примеры:\n"
            "• <code>вопросы о цене и покупке</code>\n"
            "• <code>положительные отзывы о продукте</code>\n"
            "• <code>жалобы и негатив</code>",
            kb_back_cancel()
        )
        return True
    
    if text == '⏭ Без фильтра':
        saved['filter_mode'] = 'none'
        DB.set_user_state(user_id, 'parse_comments:confirm', saved)
        _show_comments_confirmation(chat_id, user_id, saved)
        return True
    
    send_message(chat_id, "❌ Выберите режим:", kb_parse_mode())
    return True


def _handle_comments_keywords(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle keywords for comments"""
    keywords = [k.strip().lower() for k in text.split(',') if k.strip()]
    
    if not keywords:
        send_message(chat_id, "❌ Введите хотя бы одно слово", kb_back_cancel())
        return True
    
    saved['keywords'] = keywords[:20]
    DB.set_user_state(user_id, 'parse_comments:keyword_mode', saved)
    
    send_message(chat_id,
        f"✅ Слова: <code>{', '.join(keywords[:5])}</code>{'...' if len(keywords) > 5 else ''}\n\n"
        f"🔍 <b>Режим поиска:</b>",
        kb_keyword_match_mode()
    )
    return True


def _handle_comments_keyword_mode(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle keyword mode"""
    if '🔍 Любое' in text:
        saved['keyword_match_mode'] = 'any'
    elif '🔍 Все' in text:
        saved['keyword_match_mode'] = 'all'
    else:
        send_message(chat_id, "❌ Выберите режим:", kb_keyword_match_mode())
        return True
    
    DB.set_user_state(user_id, 'parse_comments:confirm', saved)
    _show_comments_confirmation(chat_id, user_id, saved)
    return True


def _handle_comments_semantic_topic(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle semantic topic for comments"""
    topic = text.strip()
    
    if len(topic) < 5:
        send_message(chat_id, "❌ Опишите подробнее", kb_back_cancel())
        return True
    
    saved['semantic_topic'] = topic[:500]
    DB.set_user_state(user_id, 'parse_comments:semantic_threshold', saved)
    
    send_message(chat_id,
        f"✅ Критерий: <i>{topic[:80]}...</i>\n\n"
        f"📊 <b>Порог релевантности:</b>",
        kb_semantic_threshold()
    )
    return True


def _handle_comments_semantic_threshold(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle threshold for comments"""
    if '90%' in text:
        saved['semantic_threshold'] = 0.90
    elif '70%' in text:
        saved['semantic_threshold'] = 0.70
    elif '50%' in text:
        saved['semantic_threshold'] = 0.50
    else:
        send_message(chat_id, "❌ Выберите порог:", kb_semantic_threshold())
        return True
    
    DB.set_user_state(user_id, 'parse_comments:confirm', saved)
    _show_comments_confirmation(chat_id, user_id, saved)
    return True


def _show_comments_confirmation(chat_id: int, user_id: int, saved: dict):
    """Show comments parsing confirmation"""
    mode_text = {
        'keywords': f"📝 Ключевые слова: {', '.join(saved.get('keywords', [])[:3])}...",
        'semantic': f"🧠 Семантический: {saved.get('semantic_topic', '')[:40]}...",
        'none': '⏭ Без фильтра'
    }.get(saved.get('filter_mode', 'none'))
    
    post_range = saved.get('post_range', [1, 10])
    
    send_message(chat_id,
        f"📋 <b>Подтверждение парсинга комментариев</b>\n\n"
        f"📍 Канал: <code>{saved.get('source_link')}</code>\n"
        f"📊 Посты: с {post_range[0]} по {post_range[1]}\n"
        f"📏 Мин. длина: {saved.get('min_comment_length', 0)} символов\n\n"
        f"<b>Фильтр:</b> {mode_text}",
        kb_parse_confirm()
    )


def _handle_comments_confirm(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle comments parsing confirmation"""
    if text != '🚀 Запустить парсинг':
        show_main_menu(chat_id, user_id, "❌ Парсинг отменён")
        return True
    
    post_range = saved.get('post_range', [1, 10])
    
    filters = {
        'post_start': post_range[0],
        'post_end': post_range[1],
        'min_comment_length': saved.get('min_comment_length', 0)
    }
    
    if saved.get('filter_mode') == 'semantic':
        filters['semantic_config'] = {
            'topic': saved.get('semantic_topic'),
            'threshold': saved.get('semantic_threshold', 0.7)
        }
    
    source = DB.create_audience_source(
        user_id=user_id,
        source_type='comments',
        source_link=saved.get('source_link'),
        filters=filters,
        keyword_filter=saved.get('keywords') if saved.get('filter_mode') == 'keywords' else None,
        keyword_match_mode=saved.get('keyword_match_mode', 'any')
    )
    
    if source:
        send_message(chat_id,
            f"✅ <b>Задача создана!</b>\n\n"
            f"ID: #{source['id']}\n"
            f"Статус: ⏳ В очереди\n\n"
            f"Вы получите уведомление по завершении.",
            kb_main_menu()
        )
    else:
        send_message(chat_id, "❌ Ошибка создания задачи", kb_main_menu())
    
    DB.clear_user_state(user_id)
    return True
