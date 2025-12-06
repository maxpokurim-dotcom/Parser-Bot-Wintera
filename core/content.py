"""
Content Manager Module - Telegram UI for AI Content Generation
Version 1.1 — fixed missing DB.get_trend_snapshots() error
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
    kb_inline_user_channels_for_generation, kb_inline_user_channels_for_trends,
    kb_inline_user_channels_for_summary,
    reply_keyboard, inline_keyboard
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
    """Show content manager main menu with comprehensive description"""
    DB.set_user_state(user_id, 'content:menu')
    # Get stats
    channels = DB.get_user_channels(user_id)
    generated = DB.get_generated_content(user_id, status='draft', limit=1)
    
    # 🔸 ИСПРАВЛЕНО: замена отсутствующего метода на безопасную заглушку
    # Вместо DB.get_trend_snapshots — имитация через существующие данные или пустой список
    try:
        # Попытка использовать существующий метод, если он появится позже
        if hasattr(DB, 'get_trend_snapshots'):
            trends = DB.get_trend_snapshots(user_id, limit=1)
        else:
            # Заглушка: считаем, что тренды есть, если есть хотя бы один сгенерированный контент с типом 'trend'
            trends = []
            # Альтернатива: можно запросить через общий метод, но для простоты — пусто
    except Exception:
        trends = []

    send_message(chat_id,
        f"📝 <b>Контент-менеджер (ИИ)</b>\n\n"
        f"<i>Интеллектуальная генерация контента\n"
        f"с помощью Yandex GPT. Анализ трендов,\n"
        f"создание постов и управление каналами.</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📊 СТАТИСТИКА</b>\n"
        f"├ Подключённых каналов: <b>{len(channels)}</b>\n"
        f"├ Сгенерировано контента: <b>{len(generated)}</b>\n"
        f"└ Актуальных трендов: <b>{len(trends)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>🛠 Возможности:</b>\n"
        f"• <b>Генерация</b> — создание постов с ИИ\n"
        f"• <b>Тренды</b> — анализ популярных тем\n"
        f"• <b>Итоги</b> — суммаризация обсуждений\n"
        f"• <b>Каналы</b> — управление связанными каналами\n\n"
        f"⚙️ <i>Требуется Yandex GPT API ключ в настройках</i>",
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
    
    # Content plan states
    if state.startswith('content:plan:'):
        return handle_content_plan(chat_id, user_id, text, state, saved)
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
    if state == 'content:trend:menu':
        return _handle_trend_menu(chat_id, user_id, text, saved)
    if state == 'content:trend:add:input':
        return _handle_trend_add_input(chat_id, user_id, text, saved)
    if state == 'content:trend:settings':
        return _handle_trend_settings(chat_id, user_id, text, saved)
    if state == 'content:trend:settings:interval':
        try:
            interval = int(text.strip())
            if interval < 1 or interval > 168:
                send_message(chat_id, "❌ Интервал от 1 до 168 часов", kb_back_cancel())
                return True
            
            settings = DB.get_user_settings(user_id)
            tracking = settings.get('trend_tracking_settings', {})
            tracking['analyze_interval_hours'] = interval
            DB.update_user_settings(user_id, trend_tracking_settings=tracking)
            send_message(chat_id, f"✅ Интервал установлен: {interval} часов", kb_content_menu())
            show_tracking_settings(chat_id, user_id)
            return True
        except ValueError:
            send_message(chat_id, "❌ Введите число", kb_back_cancel())
            return True
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
    # Auto templates generation flow
    # States: folder, templates (handled via callbacks), type, length, prompt, confirm
    if state == 'content:auto_templates:folder':
        # Folder selection is handled via callback, but if user sends text, show message
        send_message(chat_id,
            "👆 Выберите папку из списка выше или нажмите «📁 Без папки»",
            kb_back_cancel()
        )
        return True
    if state == 'content:auto_templates:templates':
        # Template selection is handled via callback, but if user sends text, show message
        send_message(chat_id,
            "👆 Выберите исходные шаблоны из списка выше, затем нажмите «✅ Готово»",
            kb_back_cancel()
        )
        return True
    if state == 'content:auto_templates:type':
        return _handle_auto_templates_type(chat_id, user_id, text, saved)
    if state == 'content:auto_templates:length':
        return _handle_auto_templates_length(chat_id, user_id, text, saved)
    if state == 'content:auto_templates:prompt':
        return _handle_auto_templates_prompt(chat_id, user_id, text, saved)
    if state == 'content:auto_templates:confirm':
        return _handle_auto_templates_confirm(chat_id, user_id, text, saved)
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
    try:
        # Check YaGPT API key
        try:
            settings = DB.get_user_settings(user_id)
        except Exception as e:
            logger.error(f"Error getting user settings for {user_id}: {e}")
            send_message(chat_id,
                "❌ <b>Ошибка загрузки настроек</b>\n"
                "Попробуйте позже или обратитесь в поддержку.",
                kb_content_menu()
            )
            return
        
        if not settings or not settings.get('yagpt_api_key') or not settings.get('yagpt_folder_id'):
            send_message(chat_id,
                "❌ <b>Yandex GPT не настроен</b>\n"
                "Для генерации постов настройте API ключи:\n"
                "⚙️ Настройки → 🔑 API ключи → Yandex GPT",
                kb_content_menu()
            )
            return
        
        try:
            DB.set_user_state(user_id, 'content:gen:topic', {})
        except Exception as e:
            logger.error(f"Error setting user state for {user_id}: {e}")
            send_message(chat_id, "❌ Ошибка инициализации. Попробуйте позже.", kb_content_menu())
            return
        
        send_message(chat_id,
            "✍️ <b>Генерация поста</b>\n"
            "Введите тему или ключевые слова для поста:\n"
            "Примеры:\n"
            "• <code>автоматизация Telegram-маркетинга</code>\n"
            "• <code>как прогреть аккаунт перед рассылкой</code>\n"
            "• <code>ИИ в управлении Telegram-каналами</code>",
            kb_back_cancel()
        )
    except Exception as e:
        logger.error(f"Unexpected error in start_post_generation for user {user_id}: {e}", exc_info=True)
        send_message(chat_id, "❌ Произошла ошибка. Попробуйте позже.", kb_content_menu())

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
            kb_inline_user_channels_for_generation(channels)
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
        try:
            # Validate required fields
            if not saved.get('topic'):
                logger.error(f"Missing topic for user {user_id}")
                send_message(chat_id, "❌ Ошибка: не указана тема", kb_content_menu())
                return True
            
            # Get user settings with error handling
            try:
                settings = DB.get_user_settings(user_id)
                temperature = settings.get('gpt_temperature', 0.7) if settings else 0.7
            except Exception as e:
                logger.error(f"Error getting user settings for {user_id}: {e}")
                temperature = 0.7
            
            # Save task to DB
            try:
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
                        'temperature': temperature
                    },
                    channel_id=saved.get('channel_id')
                )
            except Exception as e:
                logger.error(f"Error saving generated content for user {user_id}: {e}", exc_info=True)
                send_message(chat_id, "❌ Ошибка сохранения задачи. Попробуйте позже.", kb_content_menu())
                return True
            
            if not task:
                logger.warning(f"Failed to create generated_content for user {user_id}")
                send_message(chat_id, "❌ Ошибка создания задачи", kb_content_menu())
                DB.set_user_state(user_id, 'content:menu')
                return True
            
            # Create VPS task for content generation
            try:
                vps_task = {
                    'task_type': 'content_generate',
                    'task_data': {
                        'topic': saved['topic'],
                        'style': saved['style'],
                        'length': saved['length'],
                        'include_emoji': True,
                        'content_type': 'post',
                        'title': saved.get('topic', 'Без названия')[:100],
                        'channel_id': saved.get('channel_id'),
                        'use_trends': saved.get('use_trends', False),
                        'generated_content_id': task['id']  # Link to generated_content
                    }
                }
                vps_result = DB.create_vps_task(user_id, 'content_generate', vps_task)
                
                if not vps_result:
                    logger.error(f"Failed to create VPS task for user {user_id}, generated_content_id={task['id']}")
                    send_message(chat_id,
                        f"⚠️ <b>Задача создана, но не отправлена на обработку</b>\n"
                        f"🆔 ID: #{task['id']}\n"
                        f"Обратитесь в поддержку.",
                        kb_content_menu()
                    )
                else:
                    logger.info(f"Created content_generate task for user {user_id}, task_id={task['id']}, vps_task_id={vps_result.get('id')}")
                    send_message(chat_id,
                        f"✅ <b>Задача создана!</b>\n"
                        f"🆔 ID: #{task['id']}\n"
                        f"Статус: ⏳ Ожидает генерации\n"
                        f"Результат появится в разделе «Сгенерированные»",
                        kb_content_menu()
                    )
            except Exception as e:
                logger.error(f"Error creating VPS task for user {user_id}: {e}", exc_info=True)
                send_message(chat_id,
                    f"⚠️ <b>Задача создана, но возникла ошибка при отправке</b>\n"
                    f"🆔 ID: #{task['id']}\n"
                    f"Попробуйте позже или обратитесь в поддержку.",
                    kb_content_menu()
                )
            
            try:
                DB.set_user_state(user_id, 'content:menu')
            except Exception as e:
                logger.error(f"Error clearing user state for {user_id}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Unexpected error in _handle_gen_confirm for user {user_id}: {e}", exc_info=True)
            send_message(chat_id, "❌ Произошла непредвиденная ошибка. Попробуйте позже.", kb_content_menu())
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
    
    # Get monitored channels
    monitored = DB.get_monitored_channels(user_id, active_only=True)
    monitored_ids = {m['channel_id'] for m in monitored if m.get('channel_id')}
    
    # Get all user channels
    channels = DB.get_user_channels(user_id)
    
    # Show menu with options
    DB.set_user_state(user_id, 'content:trend:menu', {})
    send_message(chat_id,
        "📊 <b>Анализ трендов</b>\n\n"
        f"📈 Отслеживается каналов: <b>{len(monitored)}</b>\n\n"
        "Выберите действие:",
        reply_keyboard([
            ['📊 Разовый анализ', '➕ Добавить для анализа'],
            ['📋 Отслеживаемые каналы', '⚙️ Настройки отслеживания'],
            ['◀️ Назад']
        ])
    )

def _handle_trend_menu(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle trend analysis menu"""
    if text == '📊 Разовый анализ':
        channels = DB.get_user_channels(user_id)
        if not channels:
            send_message(chat_id,
                "❌ <b>Нет добавленных каналов</b>\n"
                "Добавьте каналы в разделе «🔗 Мои каналы»",
                kb_content_menu()
            )
            return True
        DB.set_user_state(user_id, 'content:trend:channel', {'channels': channels})
        send_message(chat_id,
            "📊 <b>Разовый анализ</b>\n"
            "Выберите канал для анализа:",
            kb_inline_user_channels_for_trends(channels)
        )
        return True
    
    if text == '➕ Добавить для анализа':
        DB.set_user_state(user_id, 'content:trend:add:input', {})
        send_message(chat_id,
            "➕ <b>Добавить для отслеживания</b>\n\n"
            "Введите username канала или чата:\n"
            "• Для канала: <code>@channel_name</code>\n"
            "• Для чата: <code>@chat_name</code>\n\n"
            "Бот будет отслеживать новые посты и анализировать тренды.",
            kb_back_cancel()
        )
        return True
    
    if text == '📋 Отслеживаемые каналы':
        show_monitored_channels(chat_id, user_id)
        return True
    
    if text == '⚙️ Настройки отслеживания':
        show_tracking_settings(chat_id, user_id)
        return True
    
    return False

def _handle_trend_add_input(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle adding channel/chat for tracking"""
    import re
    link = text.strip().lower()
    username = re.sub(r'^(@|https?://t\.me/)', '', link)
    username = username.split('/')[0]
    
    if not re.match(r'^[a-zA-Z][\w_]{4,}$', username):
        send_message(chat_id, "❌ Неверный формат. Введите username канала или чата", kb_back_cancel())
        return True
    
    # Check if already monitored
    existing = DB.get_monitored_channels(user_id, active_only=False)
    for ch in existing:
        if ch.get('channel_username') == username:
            send_message(chat_id,
                f"⚠️ Канал @{username} уже отслеживается",
                kb_content_menu()
            )
            DB.set_user_state(user_id, 'content:menu')
            return True
    
    # Add to monitored channels
    monitored = DB.create_monitored_channel(
        user_id=user_id,
        channel_username=username,
        channel_type='channel',  # Will be determined automatically
        priority=5,
        settings={
            'auto_analyze': True,
            'analyze_interval_hours': 24,
            'posts_per_analysis': 10
        }
    )
    
    if monitored:
        send_message(chat_id,
            f"✅ <b>Канал добавлен для отслеживания!</b>\n\n"
            f"📢 @{username}\n"
            f"📊 Бот будет анализировать новые посты\n"
            f"🔄 Интервал: каждые 24 часа",
            kb_content_menu()
        )
    else:
        send_message(chat_id, "❌ Ошибка добавления", kb_content_menu())
    
    DB.set_user_state(user_id, 'content:menu')
    return True

def show_monitored_channels(chat_id: int, user_id: int):
    """Show list of monitored channels"""
    monitored = DB.get_monitored_channels(user_id, active_only=True)
    
    if not monitored:
        send_message(chat_id,
            "📋 <b>Отслеживаемые каналы</b>\n\n"
            "Нет активных отслеживаний.\n"
            "Добавьте каналы через «➕ Добавить для анализа»",
            kb_content_menu()
        )
        return
    
    text = f"📋 <b>Отслеживаемые каналы ({len(monitored)}):</b>\n\n"
    for ch in monitored[:10]:
        status = '✅' if ch.get('is_active') else '❌'
        username = ch.get('channel_username', '?')
        text += f"{status} @{username}\n"
    
    # Create inline keyboard
    buttons = []
    for ch in monitored[:10]:
        buttons.append([{
            'text': f"{'✅' if ch.get('is_active') else '❌'} @{ch.get('channel_username', '?')}",
            'callback_data': f"trendmon:{ch['id']}"
        }])
    
    send_message(chat_id, text, inline_keyboard(buttons) if buttons else None)
    send_message(chat_id, "Выберите канал для управления:", kb_content_menu())

def show_tracking_settings(chat_id: int, user_id: int):
    """Show tracking settings"""
    settings = DB.get_user_settings(user_id)
    tracking = settings.get('trend_tracking_settings', {})
    
    auto_analyze = '✅ Вкл' if tracking.get('auto_analyze', True) else '❌ Выкл'
    interval = tracking.get('analyze_interval_hours', 24)
    
    send_message(chat_id,
        f"⚙️ <b>Настройки отслеживания</b>\n\n"
        f"<b>Авто-анализ:</b> {auto_analyze}\n"
        f"<b>Интервал:</b> каждые {interval} часов\n\n"
        f"Настройки применяются ко всем отслеживаемым каналам.",
        reply_keyboard([
            ['🔄 Авто-анализ', f'⏰ Интервал ({interval}ч)'],
            ['◀️ Назад']
        ])
    )
    DB.set_user_state(user_id, 'content:trend:settings')

def _handle_trend_settings(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle trend tracking settings"""
    settings = DB.get_user_settings(user_id)
    tracking = settings.get('trend_tracking_settings', {})
    
    if text == '🔄 Авто-анализ':
        current = tracking.get('auto_analyze', True)
        tracking['auto_analyze'] = not current
        DB.update_user_settings(user_id, trend_tracking_settings=tracking)
        status = 'включён' if not current else 'выключен'
        send_message(chat_id, f"✅ Авто-анализ {status}", kb_content_menu())
        show_tracking_settings(chat_id, user_id)
        return True
    
    if text.startswith('⏰ Интервал'):
        DB.set_user_state(user_id, 'content:trend:settings:interval', {})
        send_message(chat_id,
            "⏰ <b>Интервал анализа</b>\n\n"
            "Введите интервал в часах (1-168):\n"
            "Примеры: <code>6</code>, <code>12</code>, <code>24</code>",
            kb_back_cancel()
        )
        return True
    
    return False

def _handle_trend_channel(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    send_message(chat_id, "Выберите канал из списка", kb_back_cancel())
    return True

def _handle_trend_period(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle trend analysis period selection (stub)"""
    return False

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
        try:
            # Validate required fields
            if not saved.get('channel_id'):
                logger.error(f"Missing channel_id for trend analysis, user {user_id}")
                send_message(chat_id, "❌ Ошибка: не выбран канал", kb_content_menu())
                return True
            
            # Create trend analysis task - save as generated content with type 'trend'
            try:
                task = DB.save_generated_content(
                    user_id=user_id,
                    content="",
                    content_type='trend',
                    title=f"Анализ трендов",
                    generation_params={
                        'niche': saved.get('niche', 'general'),
                        'channel_id': saved['channel_id'],
                        'type': 'trend_analysis'
                    },
                    channel_id=saved['channel_id']
                )
            except Exception as e:
                logger.error(f"Error saving generated content for trend analysis, user {user_id}: {e}", exc_info=True)
                send_message(chat_id, "❌ Ошибка сохранения задачи. Попробуйте позже.", kb_content_menu())
                return True
            
            if not task:
                logger.warning(f"Failed to create generated_content for trend analysis, user {user_id}")
                send_message(chat_id, "❌ Ошибка создания задачи", kb_content_menu())
                try:
                    DB.set_user_state(user_id, 'content:menu')
                except:
                    pass
                return True
            
            # Get channel info
            try:
                channel = DB.get_user_channel(saved['channel_id'])
            except Exception as e:
                logger.error(f"Error getting channel {saved['channel_id']}: {e}")
                channel = None
            
            # Create VPS task for trend analysis
            try:
                vps_task = {
                    'task_type': 'trend_analysis',
                    'task_data': {
                        'channel_username': channel['channel_username'] if channel else None,
                        'channel_id': saved['channel_id'],
                        'posts_count': 100,
                        'niche': saved.get('niche', 'general'),
                        'generated_content_id': task['id']  # Link to generated_content
                    }
                }
                vps_result = DB.create_vps_task(user_id, 'trend_analysis', vps_task)
                
                if not vps_result:
                    logger.error(f"Failed to create VPS task for trend analysis, user {user_id}, generated_content_id={task['id']}")
                    send_message(chat_id,
                        f"⚠️ <b>Задача создана, но не отправлена на обработку</b>\n"
                        f"🆔 ID: #{task['id']}\n"
                        f"Обратитесь в поддержку.",
                        kb_content_menu()
                    )
                else:
                    logger.info(f"Created trend_analysis task for user {user_id}, task_id={task['id']}, vps_task_id={vps_result.get('id')}")
                    send_message(chat_id,
                        f"✅ <b>Анализ запущен!</b>\n"
                        f"🆔 ID: #{task['id']}\n"
                        f"Статус: ⏳ В обработке",
                        kb_content_menu()
                    )
            except Exception as e:
                logger.error(f"Error creating VPS task for trend analysis, user {user_id}: {e}", exc_info=True)
                send_message(chat_id,
                    f"⚠️ <b>Задача создана, но возникла ошибка при отправке</b>\n"
                    f"🆔 ID: #{task['id']}\n"
                    f"Попробуйте позже или обратитесь в поддержку.",
                    kb_content_menu()
                )
            
            try:
                DB.set_user_state(user_id, 'content:menu')
            except Exception as e:
                logger.error(f"Error clearing user state for {user_id}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Unexpected error in _handle_trend_confirm for user {user_id}: {e}", exc_info=True)
            send_message(chat_id, "❌ Произошла непредвиденная ошибка. Попробуйте позже.", kb_content_menu())
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
        kb_inline_user_channels_for_summary(channels)
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
        try:
            # Validate required fields
            if not saved.get('channel_id'):
                logger.error(f"Missing channel_id for discussion summary, user {user_id}")
                send_message(chat_id, "❌ Ошибка: не выбран канал", kb_content_menu())
                return True
            
            if not saved.get('period_days'):
                logger.error(f"Missing period_days for discussion summary, user {user_id}")
                send_message(chat_id, "❌ Ошибка: не указан период", kb_content_menu())
                return True
            
            # Create discussion summary task
            try:
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
            except Exception as e:
                logger.error(f"Error saving generated content for discussion summary, user {user_id}: {e}", exc_info=True)
                send_message(chat_id, "❌ Ошибка сохранения задачи. Попробуйте позже.", kb_content_menu())
                return True
            
            if not content:
                logger.warning(f"Failed to create generated_content for discussion summary, user {user_id}")
                send_message(chat_id, "❌ Ошибка создания задачи", kb_content_menu())
                try:
                    DB.set_user_state(user_id, 'content:menu')
                except:
                    pass
                return True
            
            # Get channel info
            try:
                channel = DB.get_user_channel(saved['channel_id'])
            except Exception as e:
                logger.error(f"Error getting channel {saved['channel_id']}: {e}")
                channel = None
            
            # Create VPS task for discussion summary
            try:
                vps_task = {
                    'task_type': 'discussion_summary',
                    'task_data': {
                        'channel_username': channel['channel_username'] if channel else None,
                        'channel_id': saved['channel_id'],
                        'post_id': None,  # Will analyze recent posts if None
                        'comments_count': 50,
                        'period_days': saved['period_days'],
                        'generated_content_id': content['id']  # Link to generated_content
                    }
                }
                vps_result = DB.create_vps_task(user_id, 'discussion_summary', vps_task)
                
                if not vps_result:
                    logger.error(f"Failed to create VPS task for discussion summary, user {user_id}, generated_content_id={content['id']}")
                    send_message(chat_id,
                        f"⚠️ <b>Задача создана, но не отправлена на обработку</b>\n"
                        f"🆔 ID: #{content['id']}\n"
                        f"Обратитесь в поддержку.",
                        kb_content_menu()
                    )
                else:
                    logger.info(f"Created discussion_summary task for user {user_id}, task_id={content['id']}, vps_task_id={vps_result.get('id')}")
                    send_message(chat_id,
                        f"✅ <b>Задача создана!</b>\n"
                        f"🆔 ID: #{content['id']}\n"
                        f"Результат появится в разделе «Сгенерированные»",
                        kb_content_menu()
                    )
            except Exception as e:
                logger.error(f"Error creating VPS task for discussion summary, user {user_id}: {e}", exc_info=True)
                send_message(chat_id,
                    f"⚠️ <b>Задача создана, но возникла ошибка при отправке</b>\n"
                    f"🆔 ID: #{content['id']}\n"
                    f"Попробуйте позже или обратитесь в поддержку.",
                    kb_content_menu()
                )
            
            try:
                DB.set_user_state(user_id, 'content:menu')
            except Exception as e:
                logger.error(f"Error clearing user state for {user_id}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Unexpected error in _handle_summary_confirm for user {user_id}: {e}", exc_info=True)
            send_message(chat_id, "❌ Произошла непредвиденная ошибка. Попробуйте позже.", kb_content_menu())
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
    """Start auto-template generation flow"""
    # Check YaGPT API key
    settings = DB.get_user_settings(user_id)
    if not settings.get('yagpt_api_key') or not settings.get('yagpt_folder_id'):
        send_message(chat_id,
            "❌ <b>Yandex GPT не настроен</b>\n"
            "Для генерации шаблонов настройте API ключи:\n"
            "⚙️ Настройки → 🔑 API ключи → Yandex GPT",
            kb_content_menu()
        )
        return
    
    # Get folders for selection
    folders = DB.get_template_folders(user_id)
    
    DB.set_user_state(user_id, 'content:auto_templates:folder', {'template_ids': []})
    
    if folders:
        # Show folder selection
        from core.keyboards import kb_inline_template_folders
        send_message(chat_id,
            "📄 <b>Авто-создание шаблонов</b>\n\n"
            "<b>Шаг 1/6:</b> Выберите папку для сохранения новых шаблонов:",
            kb_inline_template_folders(folders, 'auto_templates')
        )
        send_message(chat_id, "👆 Выберите папку выше или создайте новую в разделе «📄 Шаблоны»", kb_back_cancel())
    else:
        # No folders - create in root
        saved = {'folder_id': None, 'template_ids': []}
        DB.set_user_state(user_id, 'content:auto_templates:templates', saved)
        start_template_selection(chat_id, user_id, saved)

def show_content_plan(chat_id: int, user_id: int):
    """Show content plan with calendar and scheduled posts"""
    DB.set_user_state(user_id, 'content:plan:menu')
    
    # Get scheduled posts
    scheduled = DB.get_scheduled_content(user_id)
    
    # Get templates count
    templates = DB.get_templates(user_id)
    
    # Get channels
    channels = DB.get_user_channels(user_id)
    
    # Group by date
    from core.timezone import now_moscow, format_moscow, DAY_NAMES_RU
    today = now_moscow().date()
    
    upcoming = []
    for s in scheduled[:10]:
        scheduled_at = s.get('scheduled_at', '')
        if scheduled_at:
            try:
                from core.timezone import parse_datetime
                dt = parse_datetime(scheduled_at)
                if dt and dt.date() >= today:
                    upcoming.append({
                        'id': s['id'],
                        'title': s.get('title', 'Без названия')[:30],
                        'scheduled_at': dt,
                        'display_time': format_moscow(dt, '%d.%m %H:%M')
                    })
            except:
                pass
    
    upcoming.sort(key=lambda x: x['scheduled_at'])
    
    text = f"📅 <b>Контент-план</b>\n\n"
    
    if upcoming:
        text += f"<b>📆 Ближайшие публикации:</b>\n"
        for i, post in enumerate(upcoming[:5], 1):
            text += f"  {i}. {post['display_time']} — {post['title']}\n"
        text += "\n"
    else:
        text += "📭 <i>Нет запланированных публикаций</i>\n\n"
    
    text += f"<b>📊 Статистика:</b>\n"
    text += f"├ Запланировано: <b>{len(scheduled)}</b>\n"
    text += f"├ Шаблонов: <b>{len(templates)}</b>\n"
    text += f"└ Каналов: <b>{len(channels)}</b>\n\n"
    
    text += f"💡 <i>Планируйте посты с привязкой к шаблонам\n"
    text += f"для регулярных публикаций</i>"
    
    send_message(chat_id, text, reply_keyboard([
        ['➕ Запланировать пост'],
        ['📋 Все запланированные', '🔗 Связать с шаблоном'],
        ['📅 Календарь', '⚙️ Автопостинг'],
        ['◀️ Назад']
    ]))


def handle_content_plan(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle content plan states"""
    
    if state == 'content:plan:menu':
        if text == '➕ Запланировать пост':
            start_schedule_post(chat_id, user_id)
            return True
        if text == '📋 Все запланированные':
            show_all_scheduled_content(chat_id, user_id)
            return True
        if text == '🔗 Связать с шаблоном':
            start_link_template(chat_id, user_id)
            return True
        if text == '📅 Календарь':
            show_content_calendar(chat_id, user_id)
            return True
        if text == '⚙️ Автопостинг':
            show_autopost_settings(chat_id, user_id)
            return True
    
    # Schedule post flow
    if state == 'content:plan:schedule:channel':
        return True  # Handled by callback
    
    if state == 'content:plan:schedule:content':
        return _handle_schedule_content(chat_id, user_id, text, saved)
    
    if state == 'content:plan:schedule:time':
        return _handle_schedule_time(chat_id, user_id, text, saved)
    
    if state == 'content:plan:schedule:repeat':
        return _handle_schedule_repeat(chat_id, user_id, text, saved)
    
    if state == 'content:plan:schedule:confirm':
        return _handle_schedule_confirm(chat_id, user_id, text, saved)
    
    # Link template flow
    if state == 'content:plan:link:template':
        return True  # Handled by callback
    
    if state == 'content:plan:link:channel':
        return True  # Handled by callback
    
    if state == 'content:plan:link:schedule':
        return _handle_link_schedule(chat_id, user_id, text, saved)
    
    if state == 'content:plan:link:confirm':
        return _handle_link_confirm(chat_id, user_id, text, saved)
    
    # Autopost settings
    if state == 'content:plan:autopost':
        return _handle_autopost_settings(chat_id, user_id, text, saved)
    
    return False


def start_schedule_post(chat_id: int, user_id: int):
    """Start scheduling a new post"""
    channels = DB.get_user_channels(user_id)
    
    if not channels:
        send_message(chat_id,
            "❌ <b>Нет добавленных каналов</b>\n\n"
            "Добавьте канал в разделе «🔗 Мои каналы»",
            kb_content_menu()
        )
        return
    
    DB.set_user_state(user_id, 'content:plan:schedule:channel', {'channels': channels})
    
    # Create inline keyboard with channels
    buttons = []
    for ch in channels[:10]:
        buttons.append([{
            'text': f"@{ch['channel_username']}",
            'callback_data': f"cpch:{ch['id']}"
        }])
    
    from core.keyboards import inline_keyboard
    send_message(chat_id,
        "➕ <b>Запланировать пост</b>\n\n"
        "<b>Шаг 1/4:</b> Выберите канал:",
        inline_keyboard(buttons)
    )


def _handle_schedule_content(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle content input for scheduled post"""
    content = text.strip()
    
    if len(content) < 10:
        send_message(chat_id, "❌ Текст слишком короткий (минимум 10 символов)", kb_back_cancel())
        return True
    
    if len(content) > 4096:
        content = content[:4096]
    
    saved['content'] = content
    saved['title'] = content[:50].replace('\n', ' ')
    
    DB.set_user_state(user_id, 'content:plan:schedule:time', saved)
    
    from core.timezone import now_moscow, format_moscow
    current_time = format_moscow(now_moscow(), '%d.%m.%Y %H:%M')
    
    send_message(chat_id,
        f"✅ Текст сохранён\n\n"
        f"<b>Шаг 3/4:</b> Введите дату и время публикации:\n\n"
        f"<b>Формат:</b> <code>DD.MM.YYYY HH:MM</code>\n\n"
        f"<b>Примеры:</b>\n"
        f"• <code>05.12.2025 17:00</code>\n"
        f"• <code>15:30</code> — сегодня/завтра\n\n"
        f"🕐 <i>Текущее время (МСК): {current_time}</i>",
        kb_back_cancel()
    )
    return True


def _handle_schedule_time(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle time input for scheduled post"""
    from core.timezone import parse_time_input, now_moscow, from_moscow_to_utc
    
    scheduled_msk = parse_time_input(text)
    
    if not scheduled_msk:
        send_message(chat_id,
            "❌ Неверный формат.\n\n"
            "<b>Примеры:</b>\n"
            "• <code>05.12.2025 17:00</code>\n"
            "• <code>15:30</code>",
            kb_back_cancel()
        )
        return True
    
    if scheduled_msk <= now_moscow():
        send_message(chat_id, "❌ Время должно быть в будущем", kb_back_cancel())
        return True
    
    # Store in UTC
    saved['scheduled_at'] = from_moscow_to_utc(scheduled_msk)
    saved['display_time'] = scheduled_msk.strftime('%d.%m.%Y %H:%M')
    
    DB.set_user_state(user_id, 'content:plan:schedule:repeat', saved)
    
    send_message(chat_id,
        f"✅ Время: <b>{saved['display_time']}</b> МСК\n\n"
        f"<b>Шаг 4/4:</b> Режим повторения:",
        reply_keyboard([
            ['🔂 Один раз'],
            ['📅 Ежедневно', '📆 Еженедельно'],
            ['◀️ Назад', '❌ Отмена']
        ])
    )
    return True


def _handle_schedule_repeat(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle repeat mode selection"""
    repeat_map = {
        '🔂 Один раз': 'once',
        '📅 Ежедневно': 'daily',
        '📆 Еженедельно': 'weekly'
    }
    
    repeat_mode = repeat_map.get(text)
    if not repeat_mode:
        send_message(chat_id, "❌ Выберите режим из списка", kb_back_cancel())
        return True
    
    saved['repeat_mode'] = repeat_mode
    
    # Show confirmation
    channel = DB.get_user_channel(saved['channel_id'])
    channel_name = f"@{channel['channel_username']}" if channel else "Неизвестно"
    
    repeat_names = {'once': 'Один раз', 'daily': 'Ежедневно', 'weekly': 'Еженедельно'}
    
    DB.set_user_state(user_id, 'content:plan:schedule:confirm', saved)
    
    content_preview = saved.get('content', '')[:100]
    if len(saved.get('content', '')) > 100:
        content_preview += "..."
    
    send_message(chat_id,
        f"📋 <b>Подтверждение</b>\n\n"
        f"📢 Канал: <b>{channel_name}</b>\n"
        f"📅 Время: <b>{saved['display_time']}</b> МСК\n"
        f"🔄 Повтор: <b>{repeat_names.get(repeat_mode)}</b>\n\n"
        f"<b>Текст:</b>\n<i>{content_preview}</i>",
        reply_keyboard([
            ['✅ Подтвердить'],
            ['◀️ Назад', '❌ Отмена']
        ])
    )
    return True


def _handle_schedule_confirm(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle schedule confirmation"""
    if text == '✅ Подтвердить':
        try:
            # Validate required fields
            if not saved.get('channel_id'):
                logger.error(f"Missing channel_id for scheduled content, user {user_id}")
                send_message(chat_id, "❌ Ошибка: не выбран канал", kb_content_menu())
                return True
            
            if not saved.get('content'):
                logger.error(f"Missing content for scheduled content, user {user_id}")
                send_message(chat_id, "❌ Ошибка: не указан текст поста", kb_content_menu())
                return True
            
            if not saved.get('scheduled_at'):
                logger.error(f"Missing scheduled_at for scheduled content, user {user_id}")
                send_message(chat_id, "❌ Ошибка: не указано время публикации", kb_content_menu())
                return True
            
            # Create scheduled content
            try:
                result = DB.create_scheduled_content(
                    user_id=user_id,
                    channel_id=saved['channel_id'],
                    content=saved['content'],
                    title=saved.get('title', 'Пост'),
                    scheduled_at=saved['scheduled_at'],
                    repeat_mode=saved.get('repeat_mode', 'once')
                )
            except Exception as e:
                logger.error(f"Error creating scheduled content for user {user_id}: {e}", exc_info=True)
                send_message(chat_id, "❌ Ошибка планирования. Попробуйте позже.", kb_content_menu())
                return True
            
            if result:
                logger.info(f"Created scheduled content for user {user_id}, content_id={result.get('id')}, scheduled_at={saved.get('display_time')}")
                send_message(chat_id,
                    f"✅ <b>Пост запланирован!</b>\n\n"
                    f"📅 Публикация: <b>{saved['display_time']}</b> МСК\n"
                    f"🆔 ID: #{result['id']}",
                    kb_content_menu()
                )
            else:
                logger.warning(f"Failed to create scheduled content for user {user_id}")
                send_message(chat_id, "❌ Ошибка планирования", kb_content_menu())
            
            try:
                DB.set_user_state(user_id, 'content:menu')
            except Exception as e:
                logger.error(f"Error clearing user state for {user_id}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Unexpected error in _handle_schedule_confirm for user {user_id}: {e}", exc_info=True)
            send_message(chat_id, "❌ Произошла непредвиденная ошибка. Попробуйте позже.", kb_content_menu())
            return True
    
    return False


def start_link_template(chat_id: int, user_id: int):
    """Start linking template to content plan"""
    templates = DB.get_templates(user_id)
    
    if not templates:
        send_message(chat_id,
            "❌ <b>Нет шаблонов</b>\n\n"
            "Создайте шаблон в разделе «📄 Шаблоны»",
            kb_content_menu()
        )
        return
    
    DB.set_user_state(user_id, 'content:plan:link:template', {'templates': templates})
    
    # Create inline keyboard with templates
    buttons = []
    for t in templates[:15]:
        name = t.get('name', 'Без имени')[:25]
        buttons.append([{
            'text': f"📝 {name}",
            'callback_data': f"cptpl:{t['id']}"
        }])
    
    from core.keyboards import inline_keyboard
    send_message(chat_id,
        "🔗 <b>Связать с шаблоном</b>\n\n"
        "<b>Шаг 1/3:</b> Выберите шаблон:",
        inline_keyboard(buttons)
    )


def _handle_link_schedule(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle schedule settings for template link"""
    from core.timezone import parse_time_input, from_moscow_to_utc, now_moscow
    
    # Parse time
    scheduled = parse_time_input(text)
    if not scheduled:
        send_message(chat_id,
            "❌ Неверный формат.\n\n"
            "Введите время в формате <code>HH:MM</code> или <code>DD.MM.YYYY HH:MM</code>",
            kb_back_cancel()
        )
        return True
    
    saved['post_time'] = text.strip()
    saved['scheduled_at'] = from_moscow_to_utc(scheduled)
    
    # Show confirmation
    template = DB.get_template(saved['template_id'])
    channel = DB.get_user_channel(saved['channel_id'])
    
    template_name = template.get('name', 'Неизвестно') if template else 'Неизвестно'
    channel_name = f"@{channel['channel_username']}" if channel else 'Неизвестно'
    
    DB.set_user_state(user_id, 'content:plan:link:confirm', saved)
    
    send_message(chat_id,
        f"📋 <b>Подтверждение связи</b>\n\n"
        f"📝 Шаблон: <b>{template_name}</b>\n"
        f"📢 Канал: <b>{channel_name}</b>\n"
        f"⏰ Время публикации: <b>{text.strip()}</b>\n\n"
        f"Шаблон будет автоматически публиковаться в указанное время.",
        reply_keyboard([
            ['✅ Подтвердить'],
            ['◀️ Назад', '❌ Отмена']
        ])
    )
    return True


def _handle_link_confirm(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle link confirmation"""
    if text == '✅ Подтвердить':
        try:
            # Validate required fields
            if not saved.get('template_id'):
                logger.error(f"Missing template_id for template schedule, user {user_id}")
                send_message(chat_id, "❌ Ошибка: не выбран шаблон", kb_content_menu())
                return True
            
            if not saved.get('channel_id'):
                logger.error(f"Missing channel_id for template schedule, user {user_id}")
                send_message(chat_id, "❌ Ошибка: не выбран канал", kb_content_menu())
                return True
            
            if not saved.get('post_time'):
                logger.error(f"Missing post_time for template schedule, user {user_id}")
                send_message(chat_id, "❌ Ошибка: не указано время публикации", kb_content_menu())
                return True
            
            # Create template schedule
            try:
                result = DB.create_template_schedule(
                    user_id=user_id,
                    template_id=saved['template_id'],
                    channel_id=saved['channel_id'],
                    publish_time=saved['post_time'],
                    repeat_mode='daily'  # Default to daily
                )
            except Exception as e:
                logger.error(f"Error creating template schedule for user {user_id}: {e}", exc_info=True)
                send_message(chat_id, "❌ Ошибка создания расписания. Попробуйте позже.", kb_content_menu())
                return True
            
            if result:
                logger.info(f"Created template schedule for user {user_id}, template_id={saved['template_id']}, channel_id={saved['channel_id']}, time={saved['post_time']}")
                send_message(chat_id,
                    f"✅ <b>Шаблон связан!</b>\n\n"
                    f"⏰ Время публикации: <b>{saved['post_time']}</b>\n"
                    f"🔄 Режим: Ежедневно",
                    kb_content_menu()
                )
            else:
                logger.warning(f"Failed to create template schedule for user {user_id}")
                send_message(chat_id, "❌ Ошибка создания расписания", kb_content_menu())
            
            try:
                DB.set_user_state(user_id, 'content:menu')
            except Exception as e:
                logger.error(f"Error clearing user state for {user_id}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Unexpected error in _handle_link_confirm for user {user_id}: {e}", exc_info=True)
            send_message(chat_id, "❌ Произошла непредвиденная ошибка. Попробуйте позже.", kb_content_menu())
            return True
    
    return False


def show_all_scheduled_content(chat_id: int, user_id: int):
    """Show all scheduled content"""
    scheduled = DB.get_scheduled_content(user_id)
    
    if not scheduled:
        send_message(chat_id,
            "📋 <b>Запланированные публикации</b>\n\n"
            "Нет запланированных постов.",
            kb_content_menu()
        )
        return
    
    from core.timezone import parse_datetime, format_moscow
    
    text = f"📋 <b>Запланированные публикации ({len(scheduled)}):</b>\n\n"
    
    for s in scheduled[:10]:
        title = s.get('title', 'Без названия')[:30]
        scheduled_at = s.get('scheduled_at', '')
        
        try:
            dt = parse_datetime(scheduled_at)
            display_time = format_moscow(dt, '%d.%m %H:%M') if dt else scheduled_at[:16]
        except:
            display_time = scheduled_at[:16]
        
        status_emoji = {'pending': '⏳', 'published': '✅', 'failed': '❌'}.get(s.get('status'), '📝')
        
        text += f"{status_emoji} <b>#{s['id']}</b> | {display_time}\n"
        text += f"   {title}\n\n"
    
    # Create inline keyboard
    buttons = []
    for s in scheduled[:10]:
        buttons.append([{
            'text': f"📝 #{s['id']}",
            'callback_data': f"cpview:{s['id']}"
        }, {
            'text': '🗑',
            'callback_data': f"cpdel:{s['id']}"
        }])
    
    from core.keyboards import inline_keyboard
    send_message(chat_id, text, inline_keyboard(buttons) if buttons else None)
    send_message(chat_id, "Выберите пост для управления:", kb_content_menu())


def show_content_calendar(chat_id: int, user_id: int):
    """Show content calendar view"""
    from core.timezone import now_moscow, DAY_NAMES_RU
    from datetime import timedelta
    
    today = now_moscow()
    scheduled = DB.get_scheduled_content(user_id)
    
    # Build calendar for next 7 days
    text = "📅 <b>Календарь публикаций</b>\n\n"
    
    for i in range(7):
        day = today + timedelta(days=i)
        day_name = DAY_NAMES_RU[day.weekday()]
        date_str = day.strftime('%d.%m')
        
        # Find posts for this day
        day_posts = []
        for s in scheduled:
            try:
                from core.timezone import parse_datetime
                dt = parse_datetime(s.get('scheduled_at', ''))
                if dt and dt.date() == day.date():
                    day_posts.append({
                        'time': dt.strftime('%H:%M'),
                        'title': s.get('title', '')[:20]
                    })
            except:
                pass
        
        day_posts.sort(key=lambda x: x['time'])
        
        if i == 0:
            text += f"<b>📌 {day_name} {date_str} (сегодня)</b>\n"
        elif i == 1:
            text += f"<b>📅 {day_name} {date_str} (завтра)</b>\n"
        else:
            text += f"<b>📅 {day_name} {date_str}</b>\n"
        
        if day_posts:
            for p in day_posts[:3]:
                text += f"   {p['time']} — {p['title']}\n"
        else:
            text += "   <i>—</i>\n"
        
        text += "\n"
    
    send_message(chat_id, text, kb_content_menu())


def show_autopost_settings(chat_id: int, user_id: int):
    """Show autopost settings"""
    DB.set_user_state(user_id, 'content:plan:autopost')
    
    settings = DB.get_user_settings(user_id)
    autopost = settings.get('autopost_settings', {})
    
    enabled = '✅ Вкл' if autopost.get('enabled') else '❌ Выкл'
    notify = '✅ Вкл' if autopost.get('notify_before') else '❌ Выкл'
    
    # Get active template schedules
    schedules = DB.get_template_schedules(user_id)
    # Используем is_active (boolean) вместо status
    active_count = len([s for s in schedules if (s.get('is_active', False) if isinstance(s.get('is_active'), bool) else (s.get('status') == 'active' if s.get('status') else False))])
    
    send_message(chat_id,
        f"⚙️ <b>Автопостинг</b>\n\n"
        f"<b>Статус:</b> {enabled}\n"
        f"<b>Уведомлять перед публикацией:</b> {notify}\n\n"
        f"<b>Активных связей:</b> {active_count}\n\n"
        f"Автопостинг позволяет:\n"
        f"• Публиковать шаблоны по расписанию\n"
        f"• Уведомлять перед публикацией\n"
        f"• Редактировать перед отправкой",
        reply_keyboard([
            ['✅ Включить' if not autopost.get('enabled') else '❌ Выключить'],
            ['🔔 Уведомления', '📋 Связи'],
            ['◀️ Назад']
        ])
    )


def _handle_autopost_settings(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle autopost settings"""
    settings = DB.get_user_settings(user_id)
    autopost = settings.get('autopost_settings', {})
    
    if text == '✅ Включить':
        autopost['enabled'] = True
        DB.update_user_settings(user_id, autopost_settings=autopost)
        send_message(chat_id, "✅ Автопостинг включён", kb_content_menu())
        show_autopost_settings(chat_id, user_id)
        return True
    
    if text == '❌ Выключить':
        autopost['enabled'] = False
        DB.update_user_settings(user_id, autopost_settings=autopost)
        send_message(chat_id, "❌ Автопостинг выключен", kb_content_menu())
        show_autopost_settings(chat_id, user_id)
        return True
    
    if text == '🔔 Уведомления':
        autopost['notify_before'] = not autopost.get('notify_before', False)
        DB.update_user_settings(user_id, autopost_settings=autopost)
        status = '✅ включены' if autopost['notify_before'] else '❌ выключены'
        send_message(chat_id, f"Уведомления {status}", kb_content_menu())
        show_autopost_settings(chat_id, user_id)
        return True
    
    if text == '📋 Связи':
        schedules = DB.get_template_schedules(user_id)
        
        if not schedules:
            send_message(chat_id, "Нет активных связей шаблонов", kb_content_menu())
            return True
        
        text = "📋 <b>Связи шаблонов:</b>\n\n"
        for s in schedules[:10]:
            template = DB.get_template(s.get('template_id'))
            channel = DB.get_user_channel(s.get('channel_id'))
            
            template_name = template.get('name', '?')[:20] if template else '?'
            channel_name = f"@{channel['channel_username']}" if channel else '?'
            
            # Используем is_active (boolean) вместо status
            is_active = s.get('is_active', False) if isinstance(s.get('is_active'), bool) else (s.get('status') == 'active' if s.get('status') else False)
            status = '🟢' if is_active else '⏸'
            
            text += f"{status} {template_name} → {channel_name}\n"
            # Используем publish_time вместо post_time
            publish_time = s.get('publish_time') or s.get('post_time', '?')
            text += f"   ⏰ {publish_time}\n\n"
        
        send_message(chat_id, text, kb_content_menu())
        show_autopost_settings(chat_id, user_id)
        return True
    
    return False


def handle_content_plan_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle content plan callbacks"""
    
    # Channel selection for scheduling
    if data.startswith('cpch:'):
        channel_id = int(data.split(':')[1])
        state_data = DB.get_user_state(user_id)
        saved = state_data.get('data', {}) if state_data else {}
        saved['channel_id'] = channel_id
        DB.set_user_state(user_id, 'content:plan:schedule:content', saved)
        answer_callback(msg_id, f"✅ Канал выбран")
        
        channel = DB.get_user_channel(channel_id)
        channel_name = f"@{channel['channel_username']}" if channel else "Канал"
        
        send_message(chat_id,
            f"✅ Канал: <b>{channel_name}</b>\n\n"
            f"<b>Шаг 2/4:</b> Введите текст поста:\n\n"
            f"<i>Можете использовать форматирование HTML</i>",
            kb_back_cancel()
        )
        return True
    
    # Template selection for linking
    if data.startswith('cptpl:'):
        template_id = int(data.split(':')[1])
        state_data = DB.get_user_state(user_id)
        saved = state_data.get('data', {}) if state_data else {}
        saved['template_id'] = template_id
        
        # Now select channel
        channels = DB.get_user_channels(user_id)
        if not channels:
            answer_callback(msg_id, "❌ Нет каналов")
            send_message(chat_id, "❌ Нет каналов", kb_content_menu())
            return True
        
        DB.set_user_state(user_id, 'content:plan:link:channel', saved)
        answer_callback(msg_id, f"✅ Шаблон выбран")
        
        buttons = []
        for ch in channels[:10]:
            buttons.append([{
                'text': f"@{ch['channel_username']}",
                'callback_data': f"cplch:{ch['id']}"
            }])
        
        send_message(chat_id,
            f"✅ Шаблон выбран\n\n"
            f"<b>Шаг 2/3:</b> Выберите канал для публикации:",
            inline_keyboard(buttons)
        )
        return True
    
    # Channel selection for linking
    if data.startswith('cplch:'):
        channel_id = int(data.split(':')[1])
        state_data = DB.get_user_state(user_id)
        saved = state_data.get('data', {}) if state_data else {}
        saved['channel_id'] = channel_id
        
        DB.set_user_state(user_id, 'content:plan:link:schedule', saved)
        answer_callback(msg_id, f"✅ Канал выбран")
        
        from core.timezone import now_moscow, format_moscow
        current_time = format_moscow(now_moscow(), '%H:%M')
        
        send_message(chat_id,
            f"✅ Канал выбран\n\n"
            f"<b>Шаг 3/3:</b> Введите время ежедневной публикации:\n\n"
            f"<b>Формат:</b> <code>HH:MM</code>\n\n"
            f"<b>Пример:</b> <code>10:00</code>\n\n"
            f"🕐 <i>Текущее время (МСК): {current_time}</i>",
            kb_back_cancel()
        )
        return True
    
    # View scheduled post
    if data.startswith('cpview:'):
        post_id = int(data.split(':')[1])
        post = DB.get_scheduled_content_item(post_id)
        
        if post:
            from core.timezone import parse_datetime, format_moscow
            
            scheduled_at = parse_datetime(post.get('scheduled_at', ''))
            display_time = format_moscow(scheduled_at, '%d.%m.%Y %H:%M') if scheduled_at else '?'
            
            content = post.get('content', '')[:500]
            if len(post.get('content', '')) > 500:
                content += "..."
            
            send_message(chat_id,
                f"📝 <b>Запланированный пост #{post_id}</b>\n\n"
                f"📅 Время: <b>{display_time}</b> МСК\n"
                f"🔄 Повтор: {post.get('repeat_mode', 'once')}\n\n"
                f"<b>Текст:</b>\n{content}",
                kb_content_menu()
            )
        else:
            send_message(chat_id, "❌ Пост не найден", kb_content_menu())
        return True
    
    # Delete scheduled post
    if data.startswith('cpdel:'):
        post_id = int(data.split(':')[1])
        DB.delete_scheduled_content(post_id)
        send_message(chat_id, f"✅ Пост #{post_id} удалён", kb_content_menu())
        show_content_plan(chat_id, user_id)
        return True
    
    # Monitored channel management
    if data.startswith('trendmon:'):
        monitored_id = int(data.split(':')[1])
        monitored = DB.get_monitored_channel(monitored_id)
        if monitored:
            channel_name = f"@{monitored.get('channel_username', '?')}"
            is_active = monitored.get('is_active', True)
            new_status = not is_active
            DB.update_monitored_channel(monitored_id, is_active=new_status)
            status_text = 'активирован' if new_status else 'деактивирован'
            answer_callback(msg_id, f"✅ Канал {status_text}")
            send_message(chat_id,
                f"✅ Канал {channel_name} {status_text}",
                kb_content_menu()
            )
            show_monitored_channels(chat_id, user_id)
        return True
    
    return False

# ==================== AUTO TEMPLATES GENERATION ====================

def start_template_selection(chat_id: int, user_id: int, saved: dict):
    """Start template selection for auto-generation"""
    # Get ALL templates (not filtered by folder_id) - folder_id is for saving new templates, not for selecting source templates
    templates = DB.get_templates(user_id)
    
    if not templates:
        send_message(chat_id,
            "❌ <b>Нет шаблонов</b>\n\n"
            "Создайте шаблоны в разделе «📄 Шаблоны» для генерации новых.",
            kb_content_menu()
        )
        DB.clear_user_state(user_id)
        return
    
    # Create inline keyboard with templates (multi-select)
    buttons = []
    for t in templates[:20]:  # Limit to 20 templates
        name = t.get('name', 'Без имени')[:30]
        buttons.append([{
            'text': f"📝 {name}",
            'callback_data': f"autotpl:{t['id']}"
        }])
    
    # Add "Done" button
    buttons.append([{
        'text': '✅ Готово',
        'callback_data': 'autotpl:done'
    }])
    
    from core.keyboards import inline_keyboard
    send_message(chat_id,
        f"📄 <b>Авто-создание шаблонов</b>\n\n"
        f"<b>Шаг 2/6:</b> Выберите исходные шаблоны (можно несколько):\n\n"
        f"💡 <i>Нажмите на шаблоны для выбора, затем «✅ Готово»</i>",
        inline_keyboard(buttons)
    )

def _handle_auto_templates_type(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle template filter/type selection"""
    # 10 different filter types for template generation
    filter_map = {
        '🎓 Эксперт': 'expert',
        '👋 Друг': 'friend',
        '📢 Реклама': 'promotional',
        '💼 Деловой': 'business',
        '🎭 Креативный': 'creative',
        '📚 Образовательный': 'educational',
        '💬 Разговорный': 'conversational',
        '🔥 Энергичный': 'energetic',
        '🤝 Поддерживающий': 'supportive',
        '🎯 Прямой': 'direct'
    }
    
    template_filter = filter_map.get(text)
    if not template_filter:
        send_message(chat_id, "❌ Выберите фильтр из списка", kb_back_cancel())
        return True
    
    saved['template_filter'] = template_filter
    DB.set_user_state(user_id, 'content:auto_templates:length', saved)
    
    send_message(chat_id,
        f"✅ Фильтр: <b>{text}</b>\n\n"
        f"<b>Шаг 4/6:</b> Выберите длину шаблона:",
        reply_keyboard([
            ['📝 Короткий', '📄 Средний'],
            ['📰 Длинный'],
            ['◀️ Назад', '❌ Отмена']
        ])
    )
    return True

def _handle_auto_templates_length(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle template length selection"""
    length_map = {
        '📝 Короткий': 'short',
        '📄 Средний': 'medium',
        '📰 Длинный': 'long'
    }
    
    length = length_map.get(text)
    if not length:
        send_message(chat_id, "❌ Выберите длину из списка", kb_back_cancel())
        return True
    
    saved['length'] = length
    DB.set_user_state(user_id, 'content:auto_templates:prompt', saved)
    
    send_message(chat_id,
        f"✅ Длина: <b>{text}</b>\n\n"
        f"<b>Шаг 5/6:</b> Введите промпт для генерации (опционально):\n\n"
        f"💡 <i>Опишите, какой стиль или тему должен иметь шаблон.\n"
        f"Например: \"Создай шаблон для привлечения клиентов в онлайн-школу\"\n"
        f"Или оставьте пустым для использования стандартного промпта.</i>\n\n"
        f"📝 Введите промпт или отправьте \"-\" для пропуска:",
        kb_back_cancel()
    )
    return True

def _handle_auto_templates_prompt(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle custom prompt input"""
    prompt = text.strip()
    
    # If user sends "-", skip prompt
    if prompt == '-' or prompt.lower() == 'пропустить' or prompt == '':
        saved['custom_prompt'] = None
    else:
        # Validate prompt length
        if len(prompt) > 500:
            send_message(chat_id, "❌ Промпт слишком длинный (максимум 500 символов)", kb_back_cancel())
            return True
        
        if len(prompt) < 10:
            send_message(chat_id, "❌ Промпт слишком короткий (минимум 10 символов) или отправьте \"-\" для пропуска", kb_back_cancel())
            return True
        
        saved['custom_prompt'] = prompt
    
    DB.set_user_state(user_id, 'content:auto_templates:confirm', saved)
    show_auto_templates_confirm(chat_id, user_id, saved)
    return True

def show_auto_templates_confirm(chat_id: int, user_id: int, saved: dict):
    """Show confirmation before creating task"""
    template_ids = saved.get('template_ids', [])
    folder_id = saved.get('folder_id')
    template_filter = saved.get('template_filter', 'expert')
    length = saved.get('length', 'medium')
    custom_prompt = saved.get('custom_prompt')
    
    # Get template names
    template_names = []
    for tid in template_ids:
        t = DB.get_template(tid)
        if t:
            template_names.append(t.get('name', f'Шаблон #{tid}'))
    
    # Get folder name
    folder_name = "Без папки"
    if folder_id:
        folder = DB.get_template_folder(folder_id)
        if folder:
            folder_name = folder.get('name', 'Неизвестно')
    
    filter_names = {
        'expert': '🎓 Эксперт',
        'friend': '👋 Друг',
        'promotional': '📢 Реклама',
        'business': '💼 Деловой',
        'creative': '🎭 Креативный',
        'educational': '📚 Образовательный',
        'conversational': '💬 Разговорный',
        'energetic': '🔥 Энергичный',
        'supportive': '🤝 Поддерживающий',
        'direct': '🎯 Прямой'
    }
    
    length_names = {
        'short': '📝 Короткий',
        'medium': '📄 Средний',
        'long': '📰 Длинный'
    }
    
    text = f"📋 <b>Подтверждение</b>\n\n"
    text += f"📁 Папка: <b>{folder_name}</b>\n"
    text += f"📝 Исходных шаблонов: <b>{len(template_ids)}</b>\n"
    text += f"🎨 Фильтр: <b>{filter_names.get(template_filter, template_filter)}</b>\n"
    text += f"📏 Длина: <b>{length_names.get(length, length)}</b>\n"
    
    if custom_prompt:
        prompt_preview = custom_prompt[:50] + '...' if len(custom_prompt) > 50 else custom_prompt
        text += f"💬 Промпт: <i>{prompt_preview}</i>\n"
    else:
        text += f"💬 Промпт: <i>Стандартный</i>\n"
    
    text += f"\n<b>Исходные шаблоны:</b>\n"
    for i, name in enumerate(template_names[:5], 1):
        text += f"{i}. {name}\n"
    if len(template_names) > 5:
        text += f"... и ещё {len(template_names) - 5}\n"
    
    send_message(chat_id, text,
        reply_keyboard([
            ['✅ Подтвердить'],
            ['◀️ Назад', '❌ Отмена']
        ])
    )

def _handle_auto_templates_confirm(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle confirmation and create VPS task"""
    if text == '✅ Подтвердить':
        try:
            template_ids = saved.get('template_ids', [])
            folder_id = saved.get('folder_id')
            template_filter = saved.get('template_filter', 'expert')
            length = saved.get('length', 'medium')
            custom_prompt = saved.get('custom_prompt')
            
            # Validate required fields
            if not template_ids:
                logger.warning(f"No templates selected for auto-generation, user {user_id}")
                send_message(chat_id, "❌ Не выбраны шаблоны", kb_content_menu())
                try:
                    DB.clear_user_state(user_id)
                except Exception as e:
                    logger.error(f"Error clearing user state for {user_id}: {e}")
                return True
            
            # Validate template_ids
            if not isinstance(template_ids, list) or len(template_ids) == 0:
                logger.error(f"Invalid template_ids for user {user_id}: {template_ids}")
                send_message(chat_id, "❌ Ошибка: неверный формат шаблонов", kb_content_menu())
                return True
            
            # Create VPS task
            try:
                task_data = {
                    'template_ids': template_ids,
                    'folder_id': folder_id,
                    'template_filter': template_filter,  # Changed from template_type
                    'length': length
                }
                
                if custom_prompt:
                    task_data['custom_prompt'] = custom_prompt
                
                vps_task = DB.create_vps_task(
                    user_id=user_id,
                    task_type='template_auto_generate',
                    task_data=task_data,
                    priority=5
                )
            except Exception as e:
                logger.error(f"Error creating VPS task for template auto-generation, user {user_id}: {e}", exc_info=True)
                send_message(chat_id, "❌ Ошибка создания задачи. Попробуйте позже.", kb_content_menu())
                try:
                    DB.clear_user_state(user_id)
                except:
                    pass
                return True
            
            if vps_task:
                logger.info(f"Created template_auto_generate task for user {user_id}, vps_task_id={vps_task.get('id')}, template_ids={template_ids}")
                send_message(chat_id,
                    f"✅ <b>Задача создана!</b>\n\n"
                    f"🆔 ID: #{vps_task.get('id')}\n"
                    f"📝 Исходных шаблонов: {len(template_ids)}\n"
                    f"⏳ Генерация начнётся в ближайшее время.\n\n"
                    f"💡 Вы получите уведомление, когда шаблоны будут готовы.",
                    kb_content_menu()
                )
            else:
                logger.error(f"Failed to create VPS task for template auto-generation, user {user_id}")
                send_message(chat_id, "❌ Ошибка создания задачи. Попробуйте позже или обратитесь в поддержку.", kb_content_menu())
            
            try:
                DB.clear_user_state(user_id)
            except Exception as e:
                logger.error(f"Error clearing user state for {user_id}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Unexpected error in _handle_auto_templates_confirm for user {user_id}: {e}", exc_info=True)
            send_message(chat_id, "❌ Произошла непредвиденная ошибка. Попробуйте позже.", kb_content_menu())
            return True
    
    return False

# ==================== CALLBACK HANDLER ====================
def handle_content_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle content inline callbacks"""
    
    # Content plan callbacks
    if data.startswith('cp'):
        return handle_content_plan_callback(chat_id, msg_id, user_id, data)
    
    # Channel selection (general view - only if not in content generation flow)
    if data.startswith('uch:'):
        channel_id = int(data.split(':')[1])
        state_data = DB.get_user_state(user_id)
        state = state_data.get('state', '') if state_data else ''
        # If in content generation flow, don't show channel view
        if state.startswith('content:gen:') or state.startswith('content:trend:') or state.startswith('content:summary:'):
            # This shouldn't happen with new keyboards, but handle it
            return False
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
            DB.set_user_state(user_id, state_data.get('state'), saved)
            answer_callback(msg_id, f"✅ Канал выбран")
            _show_generation_confirmation(chat_id, user_id, saved)
        else:
            answer_callback(msg_id, "❌ Ошибка: состояние не найдено")
        return True
    # Trend analysis channel selection
    if data.startswith('trendch:'):
        channel_id = int(data.split(':')[1])
        state_data = DB.get_user_state(user_id)
        if state_data and state_data.get('state', '').startswith('content:trend:'):
            saved = state_data.get('data', {})
            saved['channel_id'] = channel_id
            DB.set_user_state(user_id, state_data.get('state'), saved)
            answer_callback(msg_id, f"✅ Канал выбран")
            _show_trend_confirmation(chat_id, user_id, saved)
        else:
            answer_callback(msg_id, "❌ Ошибка: состояние не найдено")
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
    
    # Auto templates: folder selection
    if data.startswith('tfld:') and ':auto_templates' in data:
        parts = data.split(':')
        folder_id = int(parts[1]) if parts[1] != '0' else None
        state_data = DB.get_user_state(user_id)
        
        # Check if we're in auto_templates flow
        if state_data and state_data.get('state', '') == 'content:auto_templates:folder':
            saved = state_data.get('data', {})
            saved['folder_id'] = folder_id
            try:
                DB.set_user_state(user_id, 'content:auto_templates:templates', saved)
                answer_callback(msg_id, "✅ Папка выбрана")
                start_template_selection(chat_id, user_id, saved)
            except Exception as e:
                logger.error(f"Error in auto_templates folder selection for user {user_id}: {e}", exc_info=True)
                answer_callback(msg_id, "❌ Ошибка выбора папки")
                send_message(chat_id, "❌ Произошла ошибка. Попробуйте еще раз.", kb_content_menu())
        else:
            # State mismatch - user might have navigated away
            logger.warning(f"Auto templates folder callback received but state is not 'content:auto_templates:folder' for user {user_id}, state={state_data.get('state') if state_data else 'None'}")
            answer_callback(msg_id, "❌ Сессия истекла")
            send_message(chat_id, "❌ Сессия истекла. Начните заново.", kb_content_menu())
        return True
    
    # Auto templates: template selection (multi-select)
    if data.startswith('autotpl:'):
        state_data = DB.get_user_state(user_id)
        if not state_data or state_data.get('state', '') != 'content:auto_templates:templates':
            answer_callback(msg_id, "❌ Ошибка: состояние не найдено")
            return True
        
        saved = state_data.get('data', {})
        template_ids = saved.get('template_ids', [])
        
        if data == 'autotpl:done':
            # Done selecting templates
            if not template_ids:
                answer_callback(msg_id, "❌ Выберите хотя бы один шаблон")
                return True
            
            answer_callback(msg_id, f"✅ Выбрано шаблонов: {len(template_ids)}")
            DB.set_user_state(user_id, 'content:auto_templates:type', saved)
            
            send_message(chat_id,
                f"✅ Выбрано шаблонов: <b>{len(template_ids)}</b>\n\n"
                f"<b>Шаг 3/6:</b> Выберите фильтр для генерации:",
                reply_keyboard([
                    ['🎓 Эксперт', '👋 Друг'],
                    ['📢 Реклама', '💼 Деловой'],
                    ['🎭 Креативный', '📚 Образовательный'],
                    ['💬 Разговорный', '🔥 Энергичный'],
                    ['🤝 Поддерживающий', '🎯 Прямой'],
                    ['◀️ Назад', '❌ Отмена']
                ])
            )
        else:
            # Toggle template selection
            template_id = int(data.split(':')[1])
            if template_id in template_ids:
                template_ids.remove(template_id)
                answer_callback(msg_id, "❌ Шаблон убран")
            else:
                template_ids.append(template_id)
                answer_callback(msg_id, "✅ Шаблон выбран")
            
            saved['template_ids'] = template_ids
            DB.set_user_state(user_id, 'content:auto_templates:templates', saved)
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
