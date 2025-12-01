"""
Content Manager Module - Telegram UI for AI Content Generation
Version 1.0
Handles:
- Post generation via YaGPT (task creation)
- Trend analysis (task creation)
- Discussion summaries (task creation)
- User channel management
- Content plan (UI + task creation)
All AI processing happens on VPS — this module only creates tasks.
"""
import logging
from typing import List, Dict, Optional
from core.db import DB
from core.telegram import send_message, edit_message, answer_callback
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel, kb_confirm_delete,
    kb_content_menu, kb_content_style, kb_content_length, kb_content_actions,
    kb_content_channels_menu, kb_content_channel_actions,
    kb_inline_user_channels, kb_inline_generated_content,
    reply_keyboard
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_GEN_POST = '✍️ Генерация постов'
BTN_ANALYZE_TRENDS = '📊 Анализ трендов'
BTN_SUMMARY = '💬 Итоги обсуждений'
BTN_AUTO_TEMPLATES = '📄 Шаблоны (авто)'
BTN_CONTENT_PLAN = '📅 Контент-план'
BTN_MY_CHANNELS = '🔗 Мои каналы'

BTN_STYLE_INFO = '📚 Информативный'
BTN_STYLE_ENTERTAIN = '🎭 Развлекательный'
BTN_STYLE_SALES = '💰 Продающий'
BTN_STYLE_EXPERT = '🎓 Экспертный'

BTN_LEN_SHORT = '📝 Короткий'
BTN_LEN_MEDIUM = '📄 Средний'
BTN_LEN_LONG = '📰 Длинный'

BTN_USE_TRENDS = '📈 Использовать тренды'
BTN_TOPIC = '🎯 Тема'
BTN_CHANNEL = '📢 Канал'

BTN_CHANNEL_ADD = '➕ Добавить канал'
BTN_CHANNEL_LIST = '📋 Список каналов'

BTN_SUMMARY_PERIOD_WEEK = '📆 Неделя'
BTN_SUMMARY_PERIOD_MONTH = '📆 Месяц'
BTN_SUMMARY_PERIOD_CUSTOM = '📆 Свой'

def show_content_menu(chat_id: int, user_id: int):
    """Show content manager main menu"""
    DB.set_user_state(user_id, 'content:menu')
    # Get stats
    channels = DB.get_user_channels(user_id)
    generated = DB.get_generated_content(user_id, status='draft', limit=1)
    trends = DB.get_trend_snapshots(user_id, limit=1)
    send_message(chat_id,
        f"📝 <b>Контент-менеджер</b>\n"
        f"ИИ-генерация контента и анализ\n"
        f"📊 <b>Статистика:</b>\n"
        f"├ Мои каналы: <b>{len(channels)}</b>\n"
        f"├ Сгенерировано: <b>{len(generated)}</b>\n"
        f"└ Актуальных трендов: <b>{len(trends)}</b>\n"
        f"<i>Все генерации выполняются на стороне сервера</i>",
        kb_content_menu()
    )

def handle_content(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle content states. Returns True if handled."""
    # Navigation
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Действие отменено")
        return True
    if text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return True
    if text == BTN_BACK or text == '◀️ Назад':
        _handle_back(chat_id, user_id, state, saved)
        return True

    # Menu state
    if state == 'content:menu':
        if text == BTN_GEN_POST:
            start_post_generation(chat_id, user_id)
            return True
        if text == BTN_ANALYZE_TRENDS:
            start_trend_analysis(chat_id, user_id)
            return True
        if text == BTN_SUMMARY:
            start_discussion_summary(chat_id, user_id)
            return True
        if text == BTN_AUTO_TEMPLATES:
            show_auto_templates(chat_id, user_id)
            return True
        if text == BTN_CONTENT_PLAN:
            show_content_plan(chat_id, user_id)
            return True
        if text == BTN_MY_CHANNELS:
            show_my_channels_menu(chat_id, user_id)
            return True

    # Post generation flow
    if state == 'content:gen:topic':
        return _handle_gen_topic(chat_id, user_id, text, saved)
    if state == 'content:gen:style':
        return _handle_gen_style(chat_id, user_id, text, saved)
    if state == 'content:gen:length':
        return _handle_gen_length(chat_id, user_id, text, saved)
    if state == 'content:gen:trends':
        return _handle_gen_trends(chat_id, user_id, text, saved)
    if state == 'content:gen:channel':
        return _handle_gen_channel(chat_id, user_id, text, saved)
    if state == 'content:gen:confirm':
        return _handle_gen_confirm(chat_id, user_id, text, saved)

    # Trend analysis flow
    if state == 'content:trend:channel':
        return _handle_trend_channel(chat_id, user_id, text, saved)
    if state == 'content:trend:period':
        return _handle_trend_period(chat_id, user_id, text, saved)
    if state == 'content:trend:confirm':
        return _handle_trend_confirm(chat_id, user_id, text, saved)

    # Discussion summary flow
    if state == 'content:summary:channel':
        return _handle_summary_channel(chat_id, user_id, text, saved)
    if state == 'content:summary:period':
        return _handle_summary_period(chat_id, user_id, text, saved)
    if state == 'content:summary:confirm':
        return _handle_summary_confirm(chat_id, user_id, text, saved)

    # Channel management
    if state == 'content:channels:menu':
        if text == BTN_CHANNEL_ADD:
            start_add_channel(chat_id, user_id)
            return True
        if text == BTN_CHANNEL_LIST:
            show_channel_list(chat_id, user_id)
            return True

    if state == 'content:channels:add':
        return _handle_add_channel(chat_id, user_id, text, saved)

    if state.startswith('content:channel:view:'):
        channel_id = int(state.split(':')[3])
        if text == '📊 Аналитика':
            show_channel_analytics(chat_id, user_id, channel_id)
            return True
        if text == '📤 Публикация':
            start_channel_posting(chat_id, user_id, channel_id)
            return True
        if text == '🗑 Удалить':
            DB.set_user_state(user_id, f'content:channel:delete:{channel_id}')
            send_message(chat_id,
                "🗑 <b>Удалить канал?</b>\n"
                "⚠️ Все связанные задачи будут отменены.",
                kb_confirm_delete()
            )
            return True

    if state.startswith('content:channel:delete:'):
        channel_id = int(state.split(':')[3])
        if text == '🗑 Да, удалить':
            DB.delete_user_channel(channel_id)
            send_message(chat_id, "✅ Канал удалён", kb_content_channels_menu())
            show_my_channels_menu(chat_id, user_id)
            return True

    return False

def _handle_back(chat_id: int, user_id: int, state: str, saved: dict):
    """Handle back navigation"""
    if state in ['content:menu']:
        show_main_menu(chat_id, user_id)
    elif state.startswith('content:gen:'):
        show_content_menu(chat_id, user_id)
    elif state.startswith('content:trend:'):
        show_content_menu(chat_id, user_id)
    elif state.startswith('content:summary:'):
        show_content_menu(chat_id, user_id)
    elif state == 'content:channels:menu':
        show_content_menu(chat_id, user_id)
    elif state.startswith('content:channel:view:'):
        show_channel_list(chat_id, user_id)
    else:
        show_content_menu(chat_id, user_id)

def start_post_generation(chat_id: int, user_id: int):
    """Start post generation flow"""
    # Check YaGPT API key
    settings = DB.get_user_settings(user_id)
    if not settings.get('yagpt_api_key') or not settings.get('yagpt_folder_id'):
        send_message(chat_id,
            "❌ <b>Yandex GPT не настроен</b>\n"
            "Для генерации постов настройте API ключи:\n"
            "⚙️ Настройки → 🔑 API ключи → Yandex GPT",
            kb_content_menu()
        )
        return

    DB.set_user_state(user_id, 'content:gen:topic', {})
    send_message(chat_id,
        "✍️ <b>Генерация поста</b>\n"
        "Введите тему или ключевые слова для поста:\n"
        "Примеры:\n"
        "• <code>автоматизация Telegram-маркетинга</code>\n"
        "• <code>как прогреть аккаунт перед рассылкой</code>\n"
        "• <code>ИИ в управлении Telegram-каналами</code>",
        kb_back_cancel()
    )

def _handle_gen_topic(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle topic input"""
    topic = text.strip()
    if len(topic) < 5:
        send_message(chat_id, "❌ Тема должна быть минимум 5 символов", kb_back_cancel())
        return True
    if len(topic) > 300:
        topic = topic[:300]
    saved['topic'] = topic
    DB.set_user_state(user_id, 'content:gen:style', saved)
    send_message(chat_id,
        f"✅ Тема: <i>{topic}</i>\n"
        f"🎭 <b>Выберите стиль поста:</b>",
        kb_content_style()
    )
    return True

def _handle_gen_style(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle style selection"""
    style_map = {
        BTN_STYLE_INFO: 'informative',
        BTN_STYLE_ENTERTAIN: 'entertaining',
        BTN_STYLE_SALES: 'sales',
        BTN_STYLE_EXPERT: 'expert'
    }
    style = style_map.get(text)
    if not style:
        send_message(chat_id, "❌ Выберите стиль из меню", kb_content_style())
        return True
    saved['style'] = style
    DB.set_user_state(user_id, 'content:gen:length', saved)
    send_message(chat_id,
        f"✅ Стиль: <b>{text}</b>\n"
        f"📏 <b>Выберите длину:</b>",
        kb_content_length()
    )
    return True

def _handle_gen_length(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle length selection"""
    length_map = {
        BTN_LEN_SHORT: 'short',
        BTN_LEN_MEDIUM: 'medium',
        BTN_LEN_LONG: 'long'
    }
    length = length_map.get(text)
    if not length:
        send_message(chat_id, "❌ Выберите длину из меню", kb_content_length())
        return True
    saved['length'] = length
    DB.set_user_state(user_id, 'content:gen:trends', saved)
    send_message(chat_id,
        f"✅ Длина: <b>{text}</b>\n"
        f"📈 <b>Использовать актуальные тренды?</b>\n"
        f"Это сделает пост более релевантным.",
        reply_keyboard([
            ['✅ Да', '❌ Нет'],
            ['◀️ Назад', '❌ Отмена']
        ])
    )
    return True

def _handle_gen_trends(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle trends usage"""
    if text == '✅ Да':
        saved['use_trends'] = True
    elif text == '❌ Нет':
        saved['use_trends'] = False
    else:
        send_message(chat_id, "❌ Выберите Да или Нет", kb_back_cancel())
        return True

    channels = DB.get_user_channels(user_id)
    if channels:
        saved['channels'] = channels
        DB.set_user_state(user_id, 'content:gen:channel', saved)
        send_message(chat_id,
            "📢 <b>Целевой канал</b>\n"
            "Выберите канал, для которого генерируется пост:",
            kb_inline_user_channels(channels)
        )
    else:
        saved['channel_id'] = None
        _show_generation_confirmation(chat_id, user_id, saved)
    return True

def _handle_gen_channel(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle channel selection via inline callback (handled in callback)"""
    send_message(chat_id, "Выберите канал из списка выше", kb_back_cancel())
    return True

def _show_generation_confirmation(chat_id: int, user_id: int, saved: dict):
    """Show confirmation before creating task"""
    style_names = {
        'informative': 'Информативный',
        'entertaining': 'Развлекательный',
        'sales': 'Продающий',
        'expert': 'Экспертный'
    }
    length_names = {'short': 'Короткий', 'medium': 'Средний', 'long': 'Длинный'}

    channel_info = ""
    if saved.get('channel_id'):
        ch = DB.get_user_channel(saved['channel_id'])
        if ch:
            channel_info = f"\n📢 Канал: @{ch['channel_username']}"
    elif saved.get('channels'):
        # Auto-select first if not chosen
        saved['channel_id'] = saved['channels'][0]['id']
        ch = saved['channels'][0]
        channel_info = f"\n📢 Канал: @{ch['channel_username']}"

    send_message(chat_id,
        f"📋 <b>Подтверждение генерации</b>\n"
        f"🎯 Тема: <i>{saved['topic']}</i>\n"
        f"🎭 Стиль: {style_names.get(saved['style'], saved['style'])}\n"
        f"📏 Длина: {length_names.get(saved['length'], saved['length'])}\n"
        f"📈 Тренды: {'✅ Да' if saved.get('use_trends') else '❌ Нет'}"
        f"{channel_info}\n"
        f"🕒 Генерация займёт 10-60 секунд",
        kb_content_actions()
    )
    DB.set_user_state(user_id, 'content:gen:confirm', saved)

def _handle_gen_confirm(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle generation confirmation"""
    if text in ['✏️ Редактировать', '🔄 Другой вариант', '📤 В канал', '💾 Сохранить']:
        # Save task to DB
        task = DB.save_generated_content(
            user_id=user_id,
            content="",
            content_type='post',
            title=saved.get('topic', 'Без названия')[:100],
            generation_params={
                'topic': saved['topic'],
                'style': saved['style'],
                'length': saved['length'],
                'use_trends': saved.get('use_trends', False),
                'channel_id': saved.get('channel_id'),
                'temperature': DB.get_user_settings(user_id).get('gpt_temperature', 0.7)
            },
            channel_id=saved.get('channel_id')
        )
        if task:
            send_message(chat_id,
                f"✅ <b>Задача создана!</b>\n"
                f"🆔 ID: #{task['id']}\n"
                f"Статус: ⏳ Ожидает генерации\n"
                f"Результат появится в разделе «Сгенерированные»",
                kb_content_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания задачи", kb_content_menu())
        DB.set_user_state(user_id, 'content:menu')
        return True
    if text == '❌ Отмена':
        show_content_menu(chat_id, user_id)
        return True
    return False

# ==================== TREND ANALYSIS ====================
def start_trend_analysis(chat_id: int, user_id: int):
    """Start trend analysis flow"""
    settings = DB.get_user_settings(user_id)
    if not settings.get('yagpt_api_key') or not settings.get('yagpt_folder_id'):
        send_message(chat_id,
            "❌ <b>Yandex GPT не настроен</b>\n"
            "Настройте API ключи в разделе настроек.",
            kb_content_menu()
        )
        return

    channels = DB.get_user_channels(user_id)
    if not channels:
        send_message(chat_id,
            "❌ <b>Нет добавленных каналов</b>\n"
            "Добавьте каналы в разделе «🔗 Мои каналы»",
            kb_content_menu()
        )
        return

    DB.set_user_state(user_id, 'content:trend:channel', {'channels': channels})
    send_message(chat_id,
        "📊 <b>Анализ трендов</b>\n"
        "Выберите канал для анализа:",
        kb_inline_user_channels(channels)
    )

def _handle_trend_channel(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    send_message(chat_id, "Выберите канал из списка", kb_back_cancel())
    return True

def _show_trend_confirmation(chat_id: int, user_id: int, saved: dict):
    channel = DB.get_user_channel(saved['channel_id'])
    channel_name = f"@{channel['channel_username']}" if channel else f"ID {saved['channel_id']}"
    send_message(chat_id,
        f"📋 <b>Подтверждение анализа</b>\n"
        f"📢 Канал: {channel_name}\n"
        f"📈 Будет проанализировано до 100 последних постов\n"
        f"🕒 Анализ займёт 1-3 минуты",
        kb_content_actions()
    )
    DB.set_user_state(user_id, 'content:trend:confirm', saved)

def _handle_trend_confirm(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    if text == '💾 Сохранить' or text == '✅ Подтвердить':
        # Create trend analysis task
        snapshot = DB.create_trend_snapshot(
            user_id=user_id,
            niche=saved.get('niche', 'general'),
            source_channel_id=saved['channel_id'],
            status='pending',
            created_at=DB.now_moscow().isoformat()
        )
        if snapshot:
            send_message(chat_id,
                f"✅ <b>Анализ запущен!</b>\n"
                f"🆔 ID: #{snapshot['id']}\n"
                f"Статус: ⏳ В обработке",
                kb_content_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания задачи", kb_content_menu())
        DB.set_user_state(user_id, 'content:menu')
        return True
    return False

# ==================== DISCUSSION SUMMARY ====================
def start_discussion_summary(chat_id: int, user_id: int):
    """Start discussion summary flow"""
    settings = DB.get_user_settings(user_id)
    if not settings.get('yagpt_api_key') or not settings.get('yagpt_folder_id'):
        send_message(chat_id,
            "❌ <b>Yandex GPT не настроен</b>",
            kb_content_menu()
        )
        return

    channels = DB.get_user_channels(user_id)
    if not channels:
        send_message(chat_id,
            "❌ <b>Нет добавленных каналов</b>",
            kb_content_menu()
        )
        return

    DB.set_user_state(user_id, 'content:summary:channel', {'channels': channels})
    send_message(chat_id,
        "💬 <b>Итоги обсуждений</b>\n"
        "Выберите канал для анализа комментариев:",
        kb_inline_user_channels(channels)
    )

def _handle_summary_channel(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    send_message(chat_id, "Выберите канал", kb_back_cancel())
    return True

def _handle_summary_period(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    period_map = {
        BTN_SUMMARY_PERIOD_WEEK: 7,
        BTN_SUMMARY_PERIOD_MONTH: 30,
        BTN_SUMMARY_PERIOD_CUSTOM: None
    }
    if text == BTN_SUMMARY_PERIOD_CUSTOM:
        send_message(chat_id, "Введите количество дней (1-60):", kb_back_cancel())
        saved['custom_period'] = True
        DB.set_user_state(user_id, 'content:summary:period', saved)
        return True
    days = period_map.get(text)
    if days is None:
        send_message(chat_id, "❌ Выберите период", kb_back_cancel())
        return True
    saved['period_days'] = days
    _show_summary_confirmation(chat_id, user_id, saved)
    return True

def _show_summary_confirmation(chat_id: int, user_id: int, saved: dict):
    channel = DB.get_user_channel(saved['channel_id'])
    channel_name = f"@{channel['channel_username']}" if channel else f"ID {saved['channel_id']}"
    send_message(chat_id,
        f"📋 <b>Подтверждение итогов</b>\n"
        f"📢 Канал: {channel_name}\n"
        f"📆 Период: {saved['period_days']} дней\n"
        f"🕒 Генерация займёт 30-90 секунд",
        kb_content_actions()
    )
    DB.set_user_state(user_id, 'content:summary:confirm', saved)

def _handle_summary_confirm(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    if text == '💾 Сохранить':
        content = DB.save_generated_content(
            user_id=user_id,
            content="",
            content_type='summary',
            title=f"Итоги за {saved['period_days']} дней",
            generation_params={
                'channel_id': saved['channel_id'],
                'period_days': saved['period_days'],
                'type': 'discussion_summary'
            },
            channel_id=saved['channel_id']
        )
        if content:
            send_message(chat_id,
                f"✅ <b>Задача создана!</b>\n"
                f"Результат появится в разделе «Сгенерированные»",
                kb_content_menu()
            )
        DB.set_user_state(user_id, 'content:menu')
        return True
    return False

# ==================== CHANNEL MANAGEMENT ====================
def show_my_channels_menu(chat_id: int, user_id: int):
    """Show channel management menu"""
    DB.set_user_state(user_id, 'content:channels:menu')
    channels = DB.get_user_channels(user_id)
    count = len(channels)
    send_message(chat_id,
        f"🔗 <b>Мои каналы</b>\n"
        f"Управляйте своими Telegram-каналами\n"
        f"📊 Каналов: <b>{count}</b>",
        kb_content_channels_menu()
    )

def start_add_channel(chat_id: int, user_id: int):
    """Start add channel flow"""
    DB.set_user_state(user_id, 'content:channels:add', {})
    send_message(chat_id,
        "➕ <b>Добавление канала</b>\n"
        "Введите ссылку на ваш Telegram-канал:\n"
        "Примеры:\n"
        "• @mychannel\n"
        "• https://t.me/mychannel",
        kb_back_cancel()
    )

def _handle_add_channel(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle channel addition"""
    import re
    link = text.strip().lower()
    username = re.sub(r'^(@|https?://t\.me/)', '', link)
    username = username.split('/')[0]  # Remove any trailing parts
    if not re.match(r'^[a-zA-Z][\w_]{4,}$', username):
        send_message(chat_id, "❌ Неверный формат канала", kb_back_cancel())
        return True

    channel = DB.create_user_channel(user_id, username)
    if channel:
        send_message(chat_id,
            f"✅ <b>Канал добавлен!</b>\n"
            f"📢 @{username}\n"
            f"Теперь вы можете генерировать для него контент",
            kb_content_channels_menu()
        )
    else:
        send_message(chat_id, "❌ Ошибка добавления", kb_content_channels_menu())
    show_my_channels_menu(chat_id, user_id)
    return True

def show_channel_list(chat_id: int, user_id: int):
    """Show list of user channels"""
    channels = DB.get_user_channels(user_id)
    if not channels:
        send_message(chat_id,
            "🔗 <b>Мои каналы</b>\n"
            "У вас пока нет добавленных каналов.",
            kb_content_channels_menu()
        )
        return
    send_message(chat_id,
        "🔗 <b>Выберите канал:</b>",
        kb_inline_user_channels(channels)
    )

def show_channel_view(chat_id: int, user_id: int, channel_id: int):
    """Show channel details"""
    channel = DB.get_user_channel(channel_id)
    if not channel:
        send_message(chat_id, "❌ Канал не найден", kb_content_channels_menu())
        return
    DB.set_user_state(user_id, f'content:channel:view:{channel_id}')
    username = channel['channel_username']
    niche = channel.get('niche', '—')
    send_message(chat_id,
        f"📢 <b>@{username}</b>\n"
        f"🏷 Ниша: {niche}\n"
        f"🆔 ID: {channel_id}",
        kb_content_channel_actions()
    )

def show_channel_analytics(chat_id: int, user_id: int, channel_id: int):
    """Show channel analytics (stub)"""
    send_message(chat_id,
        "📊 <b>Аналитика канала</b>\n"
        "Функция в разработке.\n"
        "На VPS будет собирать статистику постов и комментариев.",
        kb_content_channel_actions()
    )

def start_channel_posting(chat_id: int, user_id: int, channel_id: int):
    """Start posting to channel (stub)"""
    send_message(chat_id,
        "📤 <b>Публикация в канал</b>\n"
        "Выберите сгенерированный пост для публикации:",
        kb_content_menu()
    )

# ==================== OTHER MENUS ====================
def show_auto_templates(chat_id: int, user_id: int):
    """Show auto-generated templates (from generated_content folder)"""
    send_message(chat_id,
        "📄 <b>Шаблоны (авто)</b>\n"
        "Авто-сгенерированные шаблоны сохраняются в папку «Сгенерированные».\n"
        "Откройте раздел шаблонов для просмотра.",
        kb_content_menu()
    )

def show_content_plan(chat_id: int, user_id: int):
    """Show content plan (stub with task creation)"""
    send_message(chat_id,
        "📅 <b>Контент-план</b>\n"
        "Функция в разработке.\n"
        "В будущем будет доступно планирование публикаций.",
        kb_content_menu()
    )

# ==================== CALLBACK HANDLER ====================
def handle_content_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle content inline callbacks"""
    # Channel selection
    if data.startswith('uch:'):
        channel_id = int(data.split(':')[1])
        show_channel_view(chat_id, user_id, channel_id)
        return True

    # Generated content selection
    if data.startswith('gcont:'):
        content_id = int(data.split(':')[1])
        show_generated_content(chat_id, user_id, content_id)
        return True

    # Post generation channel selection
    if data.startswith('gench:'):
        channel_id = int(data.split(':')[1])
        state_data = DB.get_user_state(user_id)
        if state_data and state_data.get('state', '').startswith('content:gen:'):
            saved = state_data.get('data', {})
            saved['channel_id'] = channel_id
            _show_generation_confirmation(chat_id, user_id, saved)
        return True

    # Trend analysis channel selection
    if data.startswith('trendch:'):
        channel_id = int(data.split(':')[1])
        state_data = DB.get_user_state(user_id)
        if state_data and state_data.get('state', '').startswith('content:trend:'):
            saved = state_data.get('data', {})
            saved['channel_id'] = channel_id
            _show_trend_confirmation(chat_id, user_id, saved)
        return True

    # Summary channel selection
    if data.startswith('sumch:'):
        channel_id = int(data.split(':')[1])
        state_data = DB.get_user_state(user_id)
        if state_data and state_data.get('state', '').startswith('content:summary:'):
            saved = state_data.get('data', {})
            saved['channel_id'] = channel_id
            DB.set_user_state(user_id, 'content:summary:period', saved)
            send_message(chat_id,
                "📆 <b>Период анализа</b>",
                reply_keyboard([
                    [BTN_SUMMARY_PERIOD_WEEK, BTN_SUMMARY_PERIOD_MONTH],
                    [BTN_SUMMARY_PERIOD_CUSTOM],
                    ['◀️ Назад']
                ])
            )
        return True

    return False

def show_generated_content(chat_id: int, user_id: int, content_id: int):
    """Show generated content"""
    content = DB.get_generated_content_item(content_id)
    if not content:
        send_message(chat_id, "❌ Контент не найден", kb_content_menu())
        return

    status_map = {
        'draft': '📝 Черновик',
        'scheduled': '📅 Запланирован',
        'published': '✅ Опубликован',
        'rejected': '❌ Отклонён'
    }
    status = status_map.get(content.get('status', 'draft'), content.get('status'))
    title = content.get('title', 'Без названия')
    text = content.get('content', '—')
    if not text.strip():
        text = "<i>Генерация в процессе...</i>"

    send_message(chat_id,
        f"📄 <b>{title}</b>\n"
        f"Статус: {status}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        f"━━━━━━━━━━━━━━━━━━━",
        kb_content_actions()
    )
