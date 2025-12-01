"""
Content Manager Module - AI-Powered Content Generation
Version 1.0

Handles:
- Post generation via Yandex GPT
- Trend analysis
- Discussion summaries
- Content planning
- User channel management
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from core.db import DB
from core.telegram import send_message, edit_message, answer_callback
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel,
    kb_content_menu, kb_content_style, kb_content_length, kb_content_actions,
    kb_content_channels_menu, kb_content_channel_actions,
    kb_inline_user_channels, kb_inline_generated_content,
    reply_keyboard, inline_keyboard
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU

logger = logging.getLogger(__name__)

# Button constants
BTN_GENERATE = '✍️ Генерация постов'
BTN_TRENDS = '📊 Анализ трендов'
BTN_SUMMARIES = '💬 Итоги обсуждений'
BTN_AUTO_TEMPLATES = '📄 Шаблоны (авто)'
BTN_CONTENT_PLAN = '📅 Контент-план'
BTN_MY_CHANNELS = '🔗 Мои каналы'

# Content styles
CONTENT_STYLES = {
    '📚 Информативный': {
        'id': 'informative',
        'description': 'Факты, полезная информация, обучение',
        'prompt_hint': 'информативный, с фактами и пользой'
    },
    '🎭 Развлекательный': {
        'id': 'entertaining',
        'description': 'Лёгкий, весёлый, с юмором',
        'prompt_hint': 'развлекательный, лёгкий, с юмором'
    },
    '💰 Продающий': {
        'id': 'selling',
        'description': 'Призыв к действию, выгоды, УТП',
        'prompt_hint': 'продающий, с призывом к действию и выгодами'
    },
    '🎓 Экспертный': {
        'id': 'expert',
        'description': 'Глубокий анализ, профессиональный тон',
        'prompt_hint': 'экспертный, глубокий, профессиональный'
    }
}

# Content lengths
CONTENT_LENGTHS = {
    '📝 Короткий': {'id': 'short', 'chars': '200-500', 'prompt': 'короткий (200-500 символов)'},
    '📄 Средний': {'id': 'medium', 'chars': '500-1000', 'prompt': 'средний (500-1000 символов)'},
    '📰 Длинный': {'id': 'long', 'chars': '1000-2000', 'prompt': 'длинный (1000-2000 символов)'}
}


def show_content_menu(chat_id: int, user_id: int):
    """Show content manager menu"""
    DB.set_user_state(user_id, 'content:menu')
    
    # Check if YaGPT is configured
    settings = DB.get_user_settings(user_id)
    yagpt_configured = bool(settings.get('yagpt_api_key'))
    
    # Get stats
    content = DB.get_generated_content(user_id, limit=100)
    channels = DB.get_user_channels(user_id)
    drafts = len([c for c in content if c.get('status') == 'draft'])
    published = len([c for c in content if c.get('status') == 'published'])
    
    api_status = "✅ Yandex GPT настроен" if yagpt_configured else "⚠️ Yandex GPT не настроен"
    
    send_message(chat_id,
        f"📝 <b>Контент-менеджер</b>\n\n"
        f"Генерация контента с помощью ИИ\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"├ Каналов: <b>{len(channels)}</b>\n"
        f"├ Черновиков: <b>{drafts}</b>\n"
        f"└ Опубликовано: <b>{published}</b>\n\n"
        f"🤖 {api_status}",
        kb_content_menu()
    )


def handle_content(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle content states. Returns True if handled."""
    
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
    if state == 'content:menu':
        return _handle_menu(chat_id, user_id, text)
    
    # Generation flow
    if state == 'content:generate:topic':
        return _handle_generate_topic(chat_id, user_id, text, saved)
    
    if state == 'content:generate:style':
        return _handle_generate_style(chat_id, user_id, text, saved)
    
    if state == 'content:generate:length':
        return _handle_generate_length(chat_id, user_id, text, saved)
    
    if state == 'content:generate:trends':
        return _handle_generate_trends(chat_id, user_id, text, saved)
    
    if state == 'content:generate:result':
        return _handle_generate_result(chat_id, user_id, text, saved)
    
    if state == 'content:generate:edit':
        return _handle_generate_edit(chat_id, user_id, text, saved)
    
    # Trends analysis
    if state == 'content:trends:niche':
        return _handle_trends_niche(chat_id, user_id, text, saved)
    
    if state == 'content:trends:result':
        return _handle_trends_result(chat_id, user_id, text, saved)
    
    # Discussion summaries
    if state == 'content:summary:channel':
        return _handle_summary_channel(chat_id, user_id, text, saved)
    
    if state == 'content:summary:period':
        return _handle_summary_period(chat_id, user_id, text, saved)
    
    if state == 'content:summary:result':
        return _handle_summary_result(chat_id, user_id, text, saved)
    
    # Channels management
    if state == 'content:channels':
        return _handle_channels_menu(chat_id, user_id, text)
    
    if state == 'content:channels:add':
        return _handle_channel_add(chat_id, user_id, text, saved)
    
    if state == 'content:channels:add_niche':
        return _handle_channel_add_niche(chat_id, user_id, text, saved)
    
    if state.startswith('content:channel:'):
        return _handle_channel_view(chat_id, user_id, text, state, saved)
    
    # Content plan
    if state == 'content:plan':
        return _handle_content_plan(chat_id, user_id, text, saved)
    
    # View generated content
    if state.startswith('content:view:'):
        return _handle_content_view(chat_id, user_id, text, state, saved)
    
    return False


def _handle_back(chat_id: int, user_id: int, state: str, saved: dict):
    """Handle back navigation"""
    if state in ['content:menu', 'content:generate:topic', 'content:trends:niche', 
                 'content:summary:channel', 'content:channels']:
        show_main_menu(chat_id, user_id)
    elif state.startswith('content:generate:'):
        show_content_menu(chat_id, user_id)
    elif state.startswith('content:channel:'):
        show_channels_menu(chat_id, user_id)
    else:
        show_content_menu(chat_id, user_id)


def _handle_menu(chat_id: int, user_id: int, text: str) -> bool:
    """Handle main menu selection"""
    if text == BTN_GENERATE or text == '✍️ Генерация постов':
        start_generation(chat_id, user_id)
        return True
    
    if text == BTN_TRENDS or text == '📊 Анализ трендов':
        start_trends_analysis(chat_id, user_id)
        return True
    
    if text == BTN_SUMMARIES or text == '💬 Итоги обсуждений':
        start_summary_generation(chat_id, user_id)
        return True
    
    if text == BTN_AUTO_TEMPLATES or text == '📄 Шаблоны (авто)':
        show_auto_templates(chat_id, user_id)
        return True
    
    if text == BTN_CONTENT_PLAN or text == '📅 Контент-план':
        show_content_plan(chat_id, user_id)
        return True
    
    if text == BTN_MY_CHANNELS or text == '🔗 Мои каналы':
        show_channels_menu(chat_id, user_id)
        return True
    
    return False


# ==================== POST GENERATION ====================

def start_generation(chat_id: int, user_id: int):
    """Start post generation flow"""
    settings = DB.get_user_settings(user_id)
    
    if not settings.get('yagpt_api_key'):
        send_message(chat_id,
            "❌ <b>Yandex GPT не настроен</b>\n\n"
            "Для генерации контента нужен API ключ.\n\n"
            "Настройте в разделе:\n"
            "⚙️ Настройки → 🔑 API ключи → Yandex GPT",
            kb_content_menu()
        )
        return
    
    DB.set_user_state(user_id, 'content:generate:topic', {})
    
    send_message(chat_id,
        "✍️ <b>Генерация поста</b>\n\n"
        "<b>Шаг 1/4:</b> Тема поста\n\n"
        "Введите тему или ключевые слова:\n\n"
        "Примеры:\n"
        "• <code>5 способов увеличить продажи</code>\n"
        "• <code>тренды маркетинга 2024</code>\n"
        "• <code>как выбрать CRM для бизнеса</code>",
        kb_back_cancel()
    )


def _handle_generate_topic(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle topic input"""
    topic = text.strip()
    
    if len(topic) < 5:
        send_message(chat_id,
            "❌ Тема слишком короткая\n\n"
            "Опишите тему подробнее (минимум 5 символов):",
            kb_back_cancel()
        )
        return True
    
    if len(topic) > 500:
        topic = topic[:500]
    
    saved['topic'] = topic
    DB.set_user_state(user_id, 'content:generate:style', saved)
    
    send_message(chat_id,
        f"✅ Тема: <i>{topic[:100]}{'...' if len(topic) > 100 else ''}</i>\n\n"
        f"<b>Шаг 2/4:</b> Стиль поста\n\n"
        f"📚 <b>Информативный</b> — факты и польза\n"
        f"🎭 <b>Развлекательный</b> — лёгкий, с юмором\n"
        f"💰 <b>Продающий</b> — призыв к действию\n"
        f"🎓 <b>Экспертный</b> — глубокий анализ",
        kb_content_style()
    )
    return True


def _handle_generate_style(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle style selection"""
    style_data = CONTENT_STYLES.get(text)
    
    if not style_data:
        send_message(chat_id, "❌ Выберите стиль из списка", kb_content_style())
        return True
    
    saved['style'] = style_data['id']
    saved['style_name'] = text
    saved['style_hint'] = style_data['prompt_hint']
    
    DB.set_user_state(user_id, 'content:generate:length', saved)
    
    send_message(chat_id,
        f"✅ Стиль: <b>{text}</b>\n\n"
        f"<b>Шаг 3/4:</b> Длина поста\n\n"
        f"📝 <b>Короткий</b> — 200-500 символов\n"
        f"📄 <b>Средний</b> — 500-1000 символов\n"
        f"📰 <b>Длинный</b> — 1000-2000 символов",
        kb_content_length()
    )
    return True


def _handle_generate_length(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle length selection"""
    length_data = CONTENT_LENGTHS.get(text)
    
    if not length_data:
        send_message(chat_id, "❌ Выберите длину из списка", kb_content_length())
        return True
    
    saved['length'] = length_data['id']
    saved['length_name'] = text
    saved['length_prompt'] = length_data['prompt']
    
    DB.set_user_state(user_id, 'content:generate:trends', saved)
    
    send_message(chat_id,
        f"✅ Длина: <b>{text}</b>\n\n"
        f"<b>Шаг 4/4:</b> Использовать тренды?\n\n"
        f"ИИ может учесть актуальные тренды в вашей нише\n"
        f"для повышения вовлечённости.",
        reply_keyboard([
            ['✅ Да, учесть тренды'],
            ['❌ Нет, без трендов'],
            ['◀️ Назад', '❌ Отмена']
        ])
    )
    return True


def _handle_generate_trends(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle trends option"""
    if text == '✅ Да, учесть тренды':
        saved['use_trends'] = True
    elif text == '❌ Нет, без трендов':
        saved['use_trends'] = False
    else:
        return True
    
    # Generate content
    send_message(chat_id, "⏳ <b>Генерирую пост...</b>\n\nЭто может занять 10-30 секунд.", kb_cancel())
    
    # Build prompt
    prompt = _build_generation_prompt(saved)
    
    # Call YaGPT (simulated for now - actual call would be in worker)
    generated_text = _generate_with_yagpt(user_id, prompt, saved)
    
    if generated_text:
        saved['generated_text'] = generated_text
        DB.set_user_state(user_id, 'content:generate:result', saved)
        
        send_message(chat_id,
            f"✅ <b>Пост сгенерирован!</b>\n\n"
            f"{'─' * 30}\n"
            f"{generated_text}\n"
            f"{'─' * 30}\n\n"
            f"<b>Параметры:</b>\n"
            f"├ Тема: {saved['topic'][:50]}...\n"
            f"├ Стиль: {saved['style_name']}\n"
            f"└ Длина: {saved['length_name']}",
            kb_content_actions()
        )
    else:
        send_message(chat_id,
            "❌ <b>Ошибка генерации</b>\n\n"
            "Не удалось сгенерировать пост.\n"
            "Проверьте настройки API или попробуйте позже.",
            kb_content_menu()
        )
        DB.set_user_state(user_id, 'content:menu')
    
    return True


def _handle_generate_result(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle generation result actions"""
    if text == '✏️ Редактировать':
        DB.set_user_state(user_id, 'content:generate:edit', saved)
        send_message(chat_id,
            "✏️ <b>Редактирование</b>\n\n"
            "Отправьте исправленный текст поста:",
            kb_back_cancel()
        )
        return True
    
    if text == '🔄 Другой вариант':
        # Regenerate
        send_message(chat_id, "⏳ Генерирую другой вариант...", kb_cancel())
        
        prompt = _build_generation_prompt(saved)
        generated_text = _generate_with_yagpt(user_id, prompt, saved, variation=True)
        
        if generated_text:
            saved['generated_text'] = generated_text
            DB.set_user_state(user_id, 'content:generate:result', saved)
            
            send_message(chat_id,
                f"✅ <b>Новый вариант:</b>\n\n"
                f"{'─' * 30}\n"
                f"{generated_text}\n"
                f"{'─' * 30}",
                kb_content_actions()
            )
        else:
            send_message(chat_id, "❌ Ошибка генерации", kb_content_actions())
        return True
    
    if text == '💾 Сохранить':
        # Save as draft
        content = DB.save_generated_content(
            user_id=user_id,
            content=saved['generated_text'],
            content_type='post',
            title=saved['topic'][:100],
            generation_params={
                'topic': saved['topic'],
                'style': saved['style'],
                'length': saved['length'],
                'use_trends': saved.get('use_trends', False)
            }
        )
        
        if content:
            send_message(chat_id,
                f"✅ <b>Пост сохранён!</b>\n\n"
                f"ID: #{content['id']}\n"
                f"Статус: 📝 Черновик\n\n"
                f"Найти в разделе «📄 Шаблоны (авто)»",
                kb_content_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка сохранения", kb_content_menu())
        
        DB.set_user_state(user_id, 'content:menu')
        return True
    
    if text == '📤 В канал':
        # Show channel selection
        channels = DB.get_user_channels(user_id)
        if not channels:
            send_message(chat_id,
                "❌ Нет добавленных каналов\n\n"
                "Сначала добавьте канал в разделе «🔗 Мои каналы»",
                kb_content_actions()
            )
            return True
        
        kb = kb_inline_user_channels(channels)
        send_message(chat_id, "📤 <b>Выберите канал для публикации:</b>", kb)
        return True
    
    return True


def _handle_generate_edit(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle post editing"""
    edited_text = text.strip()
    
    if len(edited_text) < 10:
        send_message(chat_id, "❌ Текст слишком короткий", kb_back_cancel())
        return True
    
    saved['generated_text'] = edited_text
    DB.set_user_state(user_id, 'content:generate:result', saved)
    
    send_message(chat_id,
        f"✅ <b>Текст обновлён:</b>\n\n"
        f"{'─' * 30}\n"
        f"{edited_text}\n"
        f"{'─' * 30}",
        kb_content_actions()
    )
    return True


def _build_generation_prompt(saved: dict) -> str:
    """Build prompt for YaGPT"""
    prompt = f"""Напиши пост для Telegram-канала.

Тема: {saved['topic']}
Стиль: {saved['style_hint']}
Длина: {saved['length_prompt']}

Требования:
- Естественный язык, без канцеляризмов
- Используй emoji уместно (не более 3-5 на пост)
- Без кликбейта и капслока
- Добавь призыв к действию в конце (если уместно)
- Пиши от первого лица или обезличенно

Верни ТОЛЬКО текст поста, без пояснений и кавычек."""

    if saved.get('use_trends'):
        prompt += "\n\nУчти актуальные тренды и сделай пост более вовлекающим."
    
    return prompt


def _generate_with_yagpt(user_id: int, prompt: str, saved: dict, variation: bool = False) -> Optional[str]:
    """
    Generate content with YaGPT
    In real implementation, this would call the YaGPT API
    For now, returns a placeholder or calls worker
    """
    settings = DB.get_user_settings(user_id)
    api_key = settings.get('yagpt_api_key')
    folder_id = settings.get('yagpt_folder_id')
    
    if not api_key:
        return None
    
    # Create generation task for worker
    # In real implementation, this would be async
    # For now, create a task and return placeholder
    
    task_data = {
        'type': 'content_generation',
        'prompt': prompt,
        'params': saved,
        'variation': variation
    }
    
    # Placeholder response (worker would replace this)
    topic = saved.get('topic', '')
    style = saved.get('style', 'informative')
    
    # Generate simple placeholder based on topic
    placeholders = {
        'informative': f"📚 {topic}\n\nЭто важная тема, которую стоит рассмотреть подробнее.\n\nОсновные моменты:\n• Пункт 1\n• Пункт 2\n• Пункт 3\n\n💡 Сохраните пост, чтобы не потерять!",
        'entertaining': f"🎉 {topic}\n\nНу что, готовы узнать кое-что интересное?\n\nСпойлер: это будет весело! 😄\n\n#интересное #факты",
        'selling': f"🔥 {topic}\n\nХотите узнать секрет успеха?\n\n✅ Преимущество 1\n✅ Преимущество 2\n✅ Преимущество 3\n\n👉 Напишите в комментариях «ХОЧУ» для подробностей!",
        'expert': f"🎓 {topic}\n\nРазберём эту тему детально.\n\nКлючевые аспекты:\n\n1️⃣ Первый важный момент\n2️⃣ Второй важный момент\n3️⃣ Третий важный момент\n\nВыводы и рекомендации в следующем посте 👇"
    }
    
    return placeholders.get(style, placeholders['informative'])


# ==================== TRENDS ANALYSIS ====================

def start_trends_analysis(chat_id: int, user_id: int):
    """Start trends analysis"""
    settings = DB.get_user_settings(user_id)
    
    if not settings.get('yagpt_api_key'):
        send_message(chat_id,
            "❌ <b>Yandex GPT не настроен</b>\n\n"
            "Для анализа трендов нужен API ключ.",
            kb_content_menu()
        )
        return
    
    DB.set_user_state(user_id, 'content:trends:niche', {})
    
    send_message(chat_id,
        "📊 <b>Анализ трендов</b>\n\n"
        "Введите вашу нишу или тематику:\n\n"
        "Примеры:\n"
        "• <code>digital-маркетинг</code>\n"
        "• <code>криптовалюты и блокчейн</code>\n"
        "• <code>фитнес и здоровье</code>",
        kb_back_cancel()
    )


def _handle_trends_niche(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle niche input for trends"""
    niche = text.strip()
    
    if len(niche) < 3:
        send_message(chat_id, "❌ Укажите нишу подробнее", kb_back_cancel())
        return True
    
    saved['niche'] = niche
    
    send_message(chat_id, "⏳ <b>Анализирую тренды...</b>", kb_cancel())
    
    # Analyze trends (placeholder)
    trends = _analyze_trends(user_id, niche)
    
    if trends:
        saved['trends'] = trends
        DB.set_user_state(user_id, 'content:trends:result', saved)
        
        text = f"📊 <b>Тренды в нише «{niche}»</b>\n\n"
        
        if trends.get('topics'):
            text += "<b>🔥 Горячие темы:</b>\n"
            for i, topic in enumerate(trends['topics'][:5], 1):
                text += f"{i}. {topic}\n"
            text += "\n"
        
        if trends.get('formats'):
            text += "<b>📝 Популярные форматы:</b>\n"
            for fmt in trends['formats'][:3]:
                text += f"• {fmt}\n"
            text += "\n"
        
        if trends.get('hooks'):
            text += "<b>🎣 Эффективные хуки:</b>\n"
            for hook in trends['hooks'][:3]:
                text += f"• «{hook}»\n"
            text += "\n"
        
        if trends.get('recommendations'):
            text += "<b>💡 Рекомендации:</b>\n"
            for rec in trends['recommendations'][:3]:
                text += f"• {rec}\n"
        
        send_message(chat_id, text, reply_keyboard([
            ['✍️ Создать пост по тренду'],
            ['🔄 Обновить анализ'],
            ['◀️ Назад']
        ]))
    else:
        send_message(chat_id, "❌ Не удалось проанализировать тренды", kb_content_menu())
        DB.set_user_state(user_id, 'content:menu')
    
    return True


def _handle_trends_result(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle trends result actions"""
    if text == '✍️ Создать пост по тренду':
        # Start generation with trend topic
        trends = saved.get('trends', {})
        if trends.get('topics'):
            saved['topic'] = trends['topics'][0]
            saved['use_trends'] = True
            DB.set_user_state(user_id, 'content:generate:style', saved)
            
            send_message(chat_id,
                f"✅ Тема: <i>{saved['topic']}</i>\n\n"
                f"<b>Выберите стиль поста:</b>",
                kb_content_style()
            )
        else:
            start_generation(chat_id, user_id)
        return True
    
    if text == '🔄 Обновить анализ':
        niche = saved.get('niche', '')
        return _handle_trends_niche(chat_id, user_id, niche, {})
    
    return False


def _analyze_trends(user_id: int, niche: str) -> Optional[Dict]:
    """
    Analyze trends in niche
    In real implementation, this would use YaGPT
    """
    # Placeholder response
    return {
        'topics': [
            f'Как использовать ИИ в {niche}',
            f'Топ-5 ошибок в {niche}',
            f'Тренды {niche} на 2024 год',
            f'Личный опыт в {niche}',
            f'Чек-лист по {niche}'
        ],
        'formats': [
            'Списки и чек-листы',
            'Личные истории',
            'Разборы кейсов'
        ],
        'hooks': [
            'Я потратил X, чтобы вы не тратили...',
            'То, о чём молчат эксперты...',
            '90% делают эту ошибку...'
        ],
        'recommendations': [
            'Добавляйте личный опыт',
            'Используйте конкретные цифры',
            'Задавайте вопросы аудитории'
        ]
    }


# ==================== DISCUSSION SUMMARIES ====================

def start_summary_generation(chat_id: int, user_id: int):
    """Start discussion summary generation"""
    channels = DB.get_user_channels(user_id)
    
    if not channels:
        send_message(chat_id,
            "❌ <b>Нет добавленных каналов</b>\n\n"
            "Сначала добавьте канал в разделе «🔗 Мои каналы»",
            kb_content_menu()
        )
        return
    
    DB.set_user_state(user_id, 'content:summary:channel', {})
    
    kb = kb_inline_user_channels(channels)
    send_message(chat_id,
        "💬 <b>Итоги обсуждений</b>\n\n"
        "Выберите канал для анализа комментариев:",
        kb
    )


def _handle_summary_channel(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle channel selection for summary"""
    # Handled via callback
    return False


def _handle_summary_period(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle period selection"""
    period_map = {
        '📅 Неделя': 7,
        '📅 2 недели': 14,
        '📅 Месяц': 30
    }
    
    days = period_map.get(text)
    if not days:
        return False
    
    saved['period_days'] = days
    
    send_message(chat_id, "⏳ <b>Анализирую обсуждения...</b>", kb_cancel())
    
    # Generate summary (placeholder)
    summary = _generate_discussion_summary(user_id, saved)
    
    if summary:
        saved['summary'] = summary
        DB.set_user_state(user_id, 'content:summary:result', saved)
        
        send_message(chat_id,
            f"💬 <b>Итоги обсуждений за {days} дней</b>\n\n"
            f"{summary}\n\n"
            f"<i>На основе анализа комментариев</i>",
            reply_keyboard([
                ['📤 Опубликовать итоги'],
                ['✏️ Редактировать'],
                ['◀️ Назад']
            ])
        )
    else:
        send_message(chat_id, "❌ Не удалось проанализировать обсуждения", kb_content_menu())
        DB.set_user_state(user_id, 'content:menu')
    
    return True


def _handle_summary_result(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle summary result actions"""
    if text == '📤 Опубликовать итоги':
        # Save and publish
        content = DB.save_generated_content(
            user_id=user_id,
            content=saved.get('summary', ''),
            content_type='summary',
            title='Итоги обсуждений',
            channel_id=saved.get('channel_id'),
            generation_params={'period_days': saved.get('period_days')}
        )
        
        if content:
            DB.update_generated_content(content['id'], status='scheduled')
            send_message(chat_id, "✅ Итоги сохранены и готовы к публикации!", kb_content_menu())
        else:
            send_message(chat_id, "❌ Ошибка сохранения", kb_content_menu())
        
        DB.set_user_state(user_id, 'content:menu')
        return True
    
    if text == '✏️ Редактировать':
        DB.set_user_state(user_id, 'content:summary:edit', saved)
        send_message(chat_id, "Отправьте исправленный текст:", kb_back_cancel())
        return True
    
    return False


def _generate_discussion_summary(user_id: int, saved: dict) -> Optional[str]:
    """Generate discussion summary"""
    # Placeholder
    return """📊 <b>Топ-3 обсуждаемые темы недели:</b>

1️⃣ <b>Автоматизация рассылок</b> (23 комментария)
   Главный вопрос: как избежать блокировок?
   
2️⃣ <b>Лимиты Telegram</b> (18 комментариев)
   Обсуждали новые ограничения платформы
   
3️⃣ <b>Прогрев аккаунтов</b> (12 комментариев)
   Делились опытом и лайфхаками

💡 <b>Вывод:</b> Вас интересует безопасность при автоматизации. Готовим подробный гайд!

Какую тему разобрать первой? 👇"""


# ==================== CHANNELS MANAGEMENT ====================

def show_channels_menu(chat_id: int, user_id: int):
    """Show user channels menu"""
    DB.set_user_state(user_id, 'content:channels')
    
    channels = DB.get_user_channels(user_id)
    
    if not channels:
        send_message(chat_id,
            "🔗 <b>Мои каналы</b>\n\n"
            "У вас нет добавленных каналов.\n\n"
            "Добавьте канал, чтобы:\n"
            "• Публиковать сгенерированный контент\n"
            "• Анализировать обсуждения\n"
            "• Планировать публикации",
            kb_content_channels_menu()
        )
    else:
        text = f"🔗 <b>Мои каналы ({len(channels)}):</b>\n\n"
        for ch in channels:
            name = ch.get('title') or f"@{ch['channel_username']}"
            niche = ch.get('niche', 'не указана')
            text += f"📢 {name}\n   Ниша: {niche}\n\n"
        
        kb = kb_inline_user_channels(channels)
        send_message(chat_id, text, kb)
        send_message(chat_id, "Выберите канал или:", kb_content_channels_menu())


def _handle_channels_menu(chat_id: int, user_id: int, text: str) -> bool:
    """Handle channels menu"""
    if text == '➕ Добавить канал':
        DB.set_user_state(user_id, 'content:channels:add', {})
        send_message(chat_id,
            "➕ <b>Добавление канала</b>\n\n"
            "Введите ссылку на ваш канал:\n\n"
            "Примеры:\n"
            "• @my_channel\n"
            "• https://t.me/my_channel\n\n"
            "⚠️ Вы должны быть администратором канала",
            kb_back_cancel()
        )
        return True
    
    if text == '📋 Список каналов':
        show_channels_menu(chat_id, user_id)
        return True
    
    return False


def _handle_channel_add(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle channel addition"""
    channel = text.strip()
    channel = channel.replace('https://t.me/', '').replace('t.me/', '').replace('@', '')
    channel = channel.split('/')[0]
    
    if not channel or len(channel) < 3:
        send_message(chat_id, "❌ Неверный формат канала", kb_back_cancel())
        return True
    
    # Check if already added
    existing = DB._select('user_channels', 
        filters={'owner_id': user_id, 'channel_username': channel.lower()}, 
        single=True)
    
    if existing:
        send_message(chat_id, "❌ Этот канал уже добавлен", kb_content_channels_menu())
        DB.set_user_state(user_id, 'content:channels')
        return True
    
    saved['channel_username'] = channel
    DB.set_user_state(user_id, 'content:channels:add_niche', saved)
    
    send_message(chat_id,
        f"✅ Канал: @{channel}\n\n"
        f"Укажите тематику канала:\n\n"
        f"Примеры: маркетинг, технологии, бизнес, развлечения",
        kb_back_cancel()
    )
    return True


def _handle_channel_add_niche(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle channel niche input"""
    niche = text.strip()
    
    if len(niche) < 2:
        send_message(chat_id, "❌ Укажите тематику", kb_back_cancel())
        return True
    
    # Create channel
    channel = DB.create_user_channel(
        user_id=user_id,
        channel_username=saved['channel_username'],
        title=f"@{saved['channel_username']}",
        niche=niche
    )
    
    if channel:
        send_message(chat_id,
            f"✅ <b>Канал добавлен!</b>\n\n"
            f"📢 @{saved['channel_username']}\n"
            f"🏷 Ниша: {niche}",
            kb_content_channels_menu()
        )
    else:
        send_message(chat_id, "❌ Ошибка добавления канала", kb_content_channels_menu())
    
    DB.set_user_state(user_id, 'content:channels')
    return True


def _handle_channel_view(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle channel view actions"""
    channel_id = int(state.split(':')[2])
    
    if text == '📊 Аналитика':
        send_message(chat_id,
            "📊 <b>Аналитика канала</b>\n\n"
            "⚠️ Функция в разработке.\n\n"
            "Скоро здесь будет:\n"
            "• Статистика публикаций\n"
            "• Анализ вовлечённости\n"
            "• Лучшее время для постов",
            kb_content_channel_actions()
        )
        return True
    
    if text == '📤 Публикация':
        # Start generation for this channel
        saved['target_channel_id'] = channel_id
        start_generation(chat_id, user_id)
        return True
    
    if text == '✏️ Редактировать':
        send_message(chat_id, "Введите новую тематику канала:", kb_back_cancel())
        DB.set_user_state(user_id, f'content:channel:edit:{channel_id}', saved)
        return True
    
    if text == '🗑 Удалить':
        DB.delete_user_channel(channel_id)
        send_message(chat_id, "✅ Канал удалён", kb_content_channels_menu())
        show_channels_menu(chat_id, user_id)
        return True
    
    return False


# ==================== AUTO TEMPLATES ====================

def show_auto_templates(chat_id: int, user_id: int):
    """Show auto-generated templates"""
    content = DB.get_generated_content(user_id, status='draft')
    
    if not content:
        send_message(chat_id,
            "📄 <b>Сгенерированные шаблоны</b>\n\n"
            "Пока нет сохранённых шаблонов.\n\n"
            "Создайте через «✍️ Генерация постов»",
            kb_content_menu()
        )
        return
    
    kb = kb_inline_generated_content(content)
    send_message(chat_id,
        f"📄 <b>Сгенерированные шаблоны ({len(content)}):</b>\n\n"
        f"📝 — черновик, 📅 — запланирован, ✅ — опубликован",
        kb
    )
    send_message(chat_id, "Выберите шаблон для просмотра:", kb_content_menu())


# ==================== CONTENT PLAN ====================

def show_content_plan(chat_id: int, user_id: int):
    """Show content plan"""
    DB.set_user_state(user_id, 'content:plan', {})
    
    # Get scheduled content
    content = DB.get_generated_content(user_id, status='scheduled')
    
    text = "📅 <b>Контент-план</b>\n\n"
    
    if content:
        text += f"<b>Запланировано ({len(content)}):</b>\n\n"
        for c in content[:10]:
            title = c.get('title', 'Без названия')[:30]
            scheduled = c.get('scheduled_at', '')[:16].replace('T', ' ') if c.get('scheduled_at') else 'не указано'
            text += f"📝 {title}\n   📅 {scheduled}\n\n"
    else:
        text += "Нет запланированных публикаций.\n\n"
    
    text += "Создайте контент через «✍️ Генерация постов» и запланируйте публикацию."
    
    send_message(chat_id, text, reply_keyboard([
        ['✍️ Создать пост'],
        ['📊 Оптимальное время'],
        ['◀️ Назад']
    ]))


def _handle_content_plan(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle content plan"""
    if text == '✍️ Создать пост':
        start_generation(chat_id, user_id)
        return True
    
    if text == '📊 Оптимальное время':
        # Show optimal posting times
        optimal = DB.get_optimal_send_time(user_id)
        
        if optimal:
            send_message(chat_id,
                f"📊 <b>Оптимальное время публикации</b>\n\n"
                f"На основе активности вашей аудитории:\n\n"
                f"🎯 Лучшее время: <b>{optimal['formatted']}</b>\n\n"
                f"<i>Данные на основе heatmap активности</i>",
                kb_content_menu()
            )
        else:
            send_message(chat_id,
                "📊 <b>Оптимальное время</b>\n\n"
                "Недостаточно данных для анализа.\n\n"
                "Выполните парсинг аудитории для сбора статистики.",
                kb_content_menu()
            )
        return True
    
    return False


# ==================== CALLBACKS ====================

def handle_content_callback(chat_id: int, msg_id: int, user_id: int, data: str) -> bool:
    """Handle content inline callbacks"""
    
    # Channel selection
    if data.startswith('uch:'):
        channel_id = int(data.split(':')[1])
        show_channel_view(chat_id, user_id, channel_id)
        return True
    
    # Content selection
    if data.startswith('gcont:'):
        content_id = int(data.split(':')[1])
        show_content_view(chat_id, user_id, content_id)
        return True
    
    return False


def show_channel_view(chat_id: int, user_id: int, channel_id: int):
    """Show channel details"""
    channel = DB.get_user_channel(channel_id)
    if not channel:
        send_message(chat_id, "❌ Канал не найден", kb_content_channels_menu())
        return
    
    DB.set_user_state(user_id, f'content:channel:{channel_id}')
    
    name = channel.get('title') or f"@{channel['channel_username']}"
    niche = channel.get('niche', 'не указана')
    
    send_message(chat_id,
        f"📢 <b>{name}</b>\n\n"
        f"🔗 @{channel['channel_username']}\n"
        f"🏷 Ниша: {niche}",
        kb_content_channel_actions()
    )


def show_content_view(chat_id: int, user_id: int, content_id: int):
    """Show generated content details"""
    content = DB.get_generated_content_item(content_id)
    if not content:
        send_message(chat_id, "❌ Контент не найден", kb_content_menu())
        return
    
    DB.set_user_state(user_id, f'content:view:{content_id}')
    
    status_emoji = {
        'draft': '📝',
        'scheduled': '📅',
        'published': '✅',
        'rejected': '❌'
    }.get(content.get('status'), '❓')
    
    title = content.get('title', 'Без названия')
    text_preview = content.get('content', '')[:500]
    if len(content.get('content', '')) > 500:
        text_preview += '...'
    
    send_message(chat_id,
        f"{status_emoji} <b>{title}</b>\n\n"
        f"{'─' * 30}\n"
        f"{text_preview}\n"
        f"{'─' * 30}\n\n"
        f"Статус: {content.get('status', 'draft')}",
        reply_keyboard([
            ['📤 Опубликовать', '✏️ Редактировать'],
            ['📋 В шаблоны', '🗑 Удалить'],
            ['◀️ Назад']
        ])
    )


def _handle_content_view(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle content view actions"""
    content_id = int(state.split(':')[2])
    content = DB.get_generated_content_item(content_id)
    
    if not content:
        show_auto_templates(chat_id, user_id)
        return True
    
    if text == '📤 Опубликовать':
        channels = DB.get_user_channels(user_id)
        if channels:
            kb = kb_inline_user_channels(channels)
            send_message(chat_id, "Выберите канал для публикации:", kb)
        else:
            send_message(chat_id, "❌ Сначала добавьте канал", kb_content_menu())
        return True
    
    if text == '✏️ Редактировать':
        saved['editing_content_id'] = content_id
        saved['generated_text'] = content.get('content', '')
        DB.set_user_state(user_id, 'content:generate:edit', saved)
        send_message(chat_id, "Отправьте исправленный текст:", kb_back_cancel())
        return True
    
    if text == '📋 В шаблоны':
        # Copy to regular templates
        from core.db import DB as db
        template = db.create_template(
            user_id=user_id,
            name=content.get('title', 'Из контент-менеджера'),
            text=content.get('content', '')
        )
        if template:
            send_message(chat_id, "✅ Скопировано в шаблоны!", kb_content_menu())
        else:
            send_message(chat_id, "❌ Ошибка копирования", kb_content_menu())
        return True
    
    if text == '🗑 Удалить':
        DB.delete_generated_content(content_id)
        send_message(chat_id, "✅ Удалено", kb_content_menu())
        show_auto_templates(chat_id, user_id)
        return True
    
    return False
