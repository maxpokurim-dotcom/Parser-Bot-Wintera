"""
Keyboard builders - Reply keyboards (static menu) + Inline for lists
Extended v3.0 with Herder, Factory, Content, Analytics
"""
from typing import List, Dict, Optional


# ==================== REPLY KEYBOARDS (STATIC MENU) ====================

def reply_keyboard(buttons: List[List[str]], resize: bool = True, one_time: bool = False) -> dict:
    """Create reply keyboard"""
    return {
        'keyboard': buttons,
        'resize_keyboard': resize,
        'one_time_keyboard': one_time
    }


def remove_keyboard() -> dict:
    """Remove reply keyboard"""
    return {'remove_keyboard': True}


def inline_keyboard(buttons: List[List[dict]]) -> dict:
    """Create inline keyboard"""
    return {'inline_keyboard': buttons}


# ==================== MAIN MENU ====================

def kb_main_menu():
    """Main menu keyboard - Extended"""
    return reply_keyboard([
        ['🔍 Парсинг чатов', '💬 Комментарии'],
        ['📊 Аудитории', '📄 Шаблоны'],
        ['👤 Аккаунты', '📤 Рассылка'],
        ['🤖 Ботовод', '🏭 Фабрика'],
        ['📝 Контент', '📈 Аналитика'],
        ['⚙️ Настройки']
    ])


def kb_cancel():
    """Cancel button"""
    return reply_keyboard([['❌ Отмена']])


def kb_back():
    """Back button"""
    return reply_keyboard([['◀️ Назад']])


def kb_back_cancel():
    """Back and cancel buttons"""
    return reply_keyboard([['◀️ Назад', '❌ Отмена']])


def kb_back_main():
    """Back to main menu"""
    return reply_keyboard([['◀️ Главное меню']])


def kb_yes_no():
    """Yes/No buttons"""
    return reply_keyboard([
        ['✅ Да', '❌ Нет'],
        ['◀️ Назад']
    ])


def kb_confirm():
    """Confirm buttons"""
    return reply_keyboard([
        ['✅ Подтвердить', '❌ Отмена'],
        ['◀️ Назад']
    ])


def kb_confirm_delete():
    """Confirm delete buttons"""
    return reply_keyboard([
        ['🗑 Да, удалить', '❌ Отмена'],
        ['◀️ Назад']
    ])


def kb_skip():
    """Skip button"""
    return reply_keyboard([
        ['⏭ Пропустить'],
        ['◀️ Назад', '❌ Отмена']
    ])


# ==================== PARSING KEYBOARDS ====================

def kb_parse_msg_limit():
    """Message limit selection for parsing"""
    return reply_keyboard([
        ['100', '500', '1000'],
        ['2000', '5000', '📝 Свой лимит'],
        ['❌ Отмена']
    ])


def kb_parse_filter_yn():
    """Yes/No filter for parsing"""
    return reply_keyboard([
        ['✅ Да', '❌ Нет'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_parse_confirm():
    """Confirm parsing"""
    return reply_keyboard([
        ['🚀 Запустить парсинг'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_comments_range():
    """Post range selection"""
    return reply_keyboard([
        ['1-10', '1-20', '1-50'],
        ['📝 Свой диапазон'],
        ['❌ Отмена']
    ])


def kb_min_length():
    """Minimum comment length"""
    return reply_keyboard([
        ['0 (все)', '10', '50'],
        ['100', '📝 Свой'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_keyword_filter():
    """Keyword filter options"""
    return reply_keyboard([
        ['✅ Да, добавить', '❌ Нет, пропустить'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_keyword_match_mode():
    """Keyword match mode selection"""
    return reply_keyboard([
        ['🔍 Любое слово', '🔍 Все слова'],
        ['◀️ Назад', '❌ Отмена']
    ])


# ==================== AUDIENCE KEYBOARDS ====================

def kb_audiences_menu():
    """Audiences menu"""
    return reply_keyboard([
        ['📋 Список аудиторий'],
        ['🏷 Теги', '🚫 Чёрный список'],
        ['◀️ Главное меню']
    ])


def kb_audience_actions():
    """Actions for selected audience"""
    return reply_keyboard([
        ['🔍 Поиск', '📤 Экспорт'],
        ['🏷 Теги', '🗑 Удалить'],
        ['◀️ К списку', '◀️ Главное меню']
    ])


def kb_audience_tags():
    """Tags management"""
    return reply_keyboard([
        ['➕ Создать тег'],
        ['◀️ Назад']
    ])


def kb_blacklist_menu():
    """Blacklist menu"""
    return reply_keyboard([
        ['➕ Добавить', '📋 Список'],
        ['🛡 Стоп-слова'],
        ['◀️ Назад']
    ])


def kb_stop_triggers_menu():
    """Stop triggers management"""
    return reply_keyboard([
        ['➕ Добавить слово', '📋 Список слов'],
        ['◀️ Назад']
    ])


# ==================== TEMPLATE KEYBOARDS ====================

def kb_templates_menu():
    """Templates menu"""
    return reply_keyboard([
        ['📋 Список шаблонов', '📁 Папки'],
        ['➕ Создать шаблон', '📁 Создать папку'],
        ['◀️ Главное меню']
    ])


def kb_template_actions():
    """Actions for selected template"""
    return reply_keyboard([
        ['👁 Предпросмотр', '📋 Копировать'],
        ['📁 Переместить', '🗑 Удалить'],
        ['◀️ К списку', '◀️ Главное меню']
    ])


def kb_folder_actions():
    """Actions for template folder"""
    return reply_keyboard([
        ['📋 Шаблоны в папке', '➕ Создать шаблон'],
        ['✏️ Переименовать', '🗑 Удалить папку'],
        ['◀️ К списку']
    ])


# ==================== ACCOUNT KEYBOARDS ====================

def kb_accounts_menu():
    """Accounts menu"""
    return reply_keyboard([
        ['📋 Список аккаунтов', '📁 Папки'],
        ['➕ Добавить аккаунт', '📁 Создать папку'],
        ['📊 Прогноз лимитов', '🧠 Профили'],
        ['◀️ Главное меню']
    ])


def kb_account_actions():
    """Actions for selected account"""
    return reply_keyboard([
        ['📊 Установить лимит', '📁 Переместить'],
        ['🧠 Профиль', '📈 Прогноз'],
        ['🗑 Удалить'],
        ['◀️ К списку', '◀️ Главное меню']
    ])


def kb_account_limits():
    """Daily limit selection"""
    return reply_keyboard([
        ['25', '50', '75'],
        ['100', '150', '200'],
        ['📝 Свой лимит'],
        ['◀️ Назад']
    ])


def kb_acc_folder_actions():
    """Actions for account folder"""
    return reply_keyboard([
        ['📋 Аккаунты в папке', '➕ Добавить аккаунт'],
        ['✏️ Переименовать', '🗑 Удалить папку'],
        ['◀️ К списку']
    ])


def kb_account_role():
    """Account role selection"""
    return reply_keyboard([
        ['📖 Наблюдатель', '🧠 Эксперт'],
        ['💪 Поддержка', '🔥 Трендсеттер'],
        ['🎲 Случайная роль'],
        ['◀️ Назад']
    ])


# ==================== MAILING KEYBOARDS ====================

def kb_mailing_menu():
    """Mailing menu"""
    return reply_keyboard([
        ['🚀 Новая рассылка'],
        ['📊 Активные', '📅 Отложенные'],
        ['⏰ Планировщик'],
        ['◀️ Главное меню']
    ])


def kb_mailing_confirm():
    """Confirm mailing"""
    return reply_keyboard([
        ['🚀 Запустить сейчас', '📅 Отложить'],
        ['🎯 Оптимальное время'],
        ['⚙️ Настройки рассылки'],
        ['❌ Отмена']
    ])


def kb_mailing_time():
    """Mailing time selection"""
    return reply_keyboard([
        ['🚀 Сейчас'],
        ['📅 Выбрать дату и время'],
        ['🎯 Оптимальное время'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_mailing_settings():
    """Mailing settings during creation"""
    return reply_keyboard([
        ['🔥 Тёплый старт: ВКЛ', '⌨️ Имитация печати: ВКЛ'],
        ['📊 Адаптивные задержки: ВКЛ'],
        ['✅ Готово'],
        ['◀️ Назад']
    ])


def kb_campaign_actions(status: str):
    """Campaign actions based on status"""
    buttons = []
    if status == 'running':
        buttons.append(['⏸ Приостановить'])
    elif status == 'paused':
        buttons.append(['▶️ Возобновить'])
    if status in ['running', 'paused']:
        buttons.append(['🛑 Остановить'])
    buttons.append(['🔄 Обновить'])
    buttons.append(['◀️ К списку', '◀️ Главное меню'])
    return reply_keyboard(buttons)


def kb_scheduler_menu():
    """Scheduler menu"""
    return reply_keyboard([
        ['➕ Новая задача', '📋 Список задач'],
        ['◀️ Назад']
    ])


def kb_schedule_type():
    """Schedule type selection"""
    return reply_keyboard([
        ['🔍 Парсинг', '📤 Рассылка'],
        ['🔥 Прогрев аккаунтов'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_schedule_repeat():
    """Schedule repeat mode"""
    return reply_keyboard([
        ['🔂 Один раз', '📅 Ежедневно'],
        ['📆 Еженедельно'],
        ['◀️ Назад', '❌ Отмена']
    ])


# ==================== HERDER (БОТОВОД) KEYBOARDS ====================

def kb_herder_menu():
    """Herder main menu"""
    return reply_keyboard([
        ['➕ Новое задание'],
        ['📋 Мои задания', '📊 Статистика'],
        ['👥 Аккаунты', '🧠 Профили ИИ'],
        ['🎯 Стратегии', '⚙️ Настройки'],
        ['◀️ Главное меню']
    ])


def kb_herder_assignment_actions(status: str):
    """Actions for herder assignment"""
    buttons = []
    if status == 'active':
        buttons.append(['⏸ Приостановить'])
    elif status == 'paused':
        buttons.append(['▶️ Возобновить'])
    if status in ['active', 'paused']:
        buttons.append(['🛑 Остановить'])
    buttons.append(['✏️ Редактировать', '📊 Логи'])
    buttons.append(['🗑 Удалить'])
    buttons.append(['◀️ К списку', '◀️ Главное меню'])
    return reply_keyboard(buttons)


def kb_herder_strategy():
    """Strategy selection"""
    return reply_keyboard([
        ['📖 Наблюдатель', '🧠 Эксперт'],
        ['💪 Поддержка', '🔥 Трендсеттер'],
        ['👥 Комьюнити'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_herder_actions_constructor():
    """Actions constructor"""
    return reply_keyboard([
        ['📖 Чтение', '👍 Реакция'],
        ['💬 Комментарий', '💾 Сохранение'],
        ['✅ Готово'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_herder_reactions():
    """Reaction selection"""
    return reply_keyboard([
        ['👍', '❤️', '🔥'],
        ['😢', '😡', '🤔'],
        ['🎉', '👏', '🤝'],
        ['✅ Готово'],
        ['◀️ Назад']
    ])


def kb_herder_priority():
    """Priority selection"""
    return reply_keyboard([
        ['🔽 Низкий', '➖ Средний', '🔼 Высокий'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_herder_comments_limit():
    """Comments per day limit"""
    return reply_keyboard([
        ['1', '2', '3'],
        ['5', '🚫 Без комментариев'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_herder_delay():
    """Delay after post selection"""
    return reply_keyboard([
        ['5-60 мин', '30-180 мин'],
        ['60-360 мин', '📝 Свой'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_herder_profiles_menu():
    """Profiles management menu"""
    return reply_keyboard([
        ['📋 Список профилей'],
        ['➕ Создать профиль', '🎲 Сгенерировать'],
        ['📊 Эффективность'],
        ['◀️ Назад']
    ])


def kb_herder_profile_actions():
    """Profile actions"""
    return reply_keyboard([
        ['✏️ Редактировать', '🎲 Перегенерировать'],
        ['🗑 Удалить'],
        ['◀️ К списку']
    ])


def kb_herder_settings():
    """Herder settings"""
    return reply_keyboard([
        ['🎯 Стратегия по умолчанию'],
        ['📊 Лимит действий', '🗣 Координация'],
        ['🌙 Сезонное поведение', '🔇 Тихий режим'],
        ['◀️ Назад']
    ])


# ==================== FACTORY KEYBOARDS ====================

def kb_factory_menu():
    """Factory main menu"""
    return reply_keyboard([
        ['➕ Добавить вручную'],
        ['🤖 Авто-создание'],
        ['🔥 Прогрев аккаунтов'],
        ['📋 Очередь создания', '📊 Статус'],
        ['⚙️ Настройки фабрики'],
        ['◀️ Главное меню']
    ])


def kb_factory_auto_count():
    """Auto-creation count"""
    return reply_keyboard([
        ['5', '10', '20'],
        ['50', '📝 Своё количество'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_factory_country():
    """Country selection"""
    return reply_keyboard([
        ['🇷🇺 Россия', '🇺🇦 Украина'],
        ['🇰🇿 Казахстан', '🇧🇾 Беларусь'],
        ['🌍 Другая'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_factory_warmup_days():
    """Warmup days selection"""
    return reply_keyboard([
        ['3 дня', '5 дней', '7 дней'],
        ['14 дней', '🚫 Без прогрева'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_factory_task_actions():
    """Factory task actions"""
    return reply_keyboard([
        ['🔄 Обновить статус'],
        ['🛑 Отменить', '🗑 Удалить'],
        ['◀️ К списку']
    ])


def kb_warmup_menu():
    """Warmup management menu"""
    return reply_keyboard([
        ['📊 Статус прогрева'],
        ['▶️ Запустить для всех', '⏸ Приостановить'],
        ['⚙️ Настройки прогрева'],
        ['◀️ Назад']
    ])


# ==================== CONTENT KEYBOARDS ====================

def kb_content_menu():
    """Content manager menu"""
    return reply_keyboard([
        ['✍️ Генерация постов'],
        ['📊 Анализ трендов', '💬 Итоги обсуждений'],
        ['📄 Шаблоны (авто)', '📅 Контент-план'],
        ['🔗 Мои каналы'],
        ['◀️ Главное меню']
    ])


def kb_content_style():
    """Content style selection"""
    return reply_keyboard([
        ['📚 Информативный', '🎭 Развлекательный'],
        ['💰 Продающий', '🎓 Экспертный'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_content_length():
    """Content length selection"""
    return reply_keyboard([
        ['📝 Короткий', '📄 Средний', '📰 Длинный'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_content_actions():
    """Generated content actions"""
    return reply_keyboard([
        ['✏️ Редактировать', '🔄 Другой вариант'],
        ['📤 В канал', '💾 Сохранить'],
        ['❌ Отмена']
    ])


def kb_content_channels_menu():
    """User channels menu"""
    return reply_keyboard([
        ['➕ Добавить канал', '📋 Список каналов'],
        ['◀️ Назад']
    ])


def kb_content_channel_actions():
    """Channel actions"""
    return reply_keyboard([
        ['📊 Аналитика', '📤 Публикация'],
        ['✏️ Редактировать', '🗑 Удалить'],
        ['◀️ К списку']
    ])


# ==================== ANALYTICS KEYBOARDS ====================

def kb_analytics_menu():
    """Analytics menu"""
    return reply_keyboard([
        ['🔥 Heatmap активности'],
        ['⚠️ Прогноз рисков', '📊 Сегментация'],
        ['📈 Эффективность', '🧠 Обучение системы'],
        ['◀️ Главное меню']
    ])


def kb_analytics_heatmap_actions():
    """Heatmap actions"""
    return reply_keyboard([
        ['📤 Применить к рассылке'],
        ['🔄 Обновить данные'],
        ['◀️ Назад']
    ])


def kb_analytics_risk_actions():
    """Risk prediction actions"""
    return reply_keyboard([
        ['🛡 Авто-защита', '⏸ Пауза рисковых'],
        ['🔄 Обновить прогноз'],
        ['◀️ Назад']
    ])


def kb_analytics_segments():
    """Segments menu"""
    return reply_keyboard([
        ['🔥 Горячие', '🌡 Тёплые', '❄️ Холодные'],
        ['📋 Все сегменты'],
        ['◀️ Назад']
    ])


# ==================== SETTINGS KEYBOARDS ====================

def kb_settings_menu():
    """Settings menu - Extended"""
    return reply_keyboard([
        ['🌙 Тихие часы', '🔔 Уведомления'],
        ['⏱ Задержки', '🗓 Кэш рассылки'],
        ['🛡 Авто-блокировка', '🔥 Прогрев'],
        ['⚠️ Риск-толерантность'],
        ['🤖 Ботовод', '🏭 Фабрика'],
        ['🧠 ИИ и обучение', '🔑 API ключи'],
        ['◀️ Главное меню']
    ])


def kb_quiet_hours():
    """Quiet hours settings"""
    return reply_keyboard([
        ['⏰ Установить', '🔕 Отключить'],
        ['◀️ Назад']
    ])


def kb_notifications():
    """Notifications settings"""
    return reply_keyboard([
        ['🔔 Включить', '🔕 Отключить'],
        ['◀️ Назад']
    ])


def kb_delay_settings():
    """Delay settings"""
    return reply_keyboard([
        ['5-15 сек', '15-45 сек'],
        ['30-90 сек', '60-180 сек'],
        ['📝 Свой диапазон'],
        ['◀️ Назад']
    ])


def kb_cache_ttl():
    """Cache TTL settings"""
    return reply_keyboard([
        ['7 дней', '14 дней', '30 дней'],
        ['60 дней', '90 дней'],
        ['🔕 Отключить'],
        ['◀️ Назад']
    ])


def kb_auto_blacklist():
    """Auto blacklist settings"""
    return reply_keyboard([
        ['✅ Включить', '❌ Отключить'],
        ['🛡 Настроить стоп-слова'],
        ['◀️ Назад']
    ])


def kb_warmup_settings():
    """Warmup settings"""
    return reply_keyboard([
        ['✅ Включить прогрев', '❌ Отключить'],
        ['⏱ 5 минут', '⏱ 10 минут', '⏱ 15 минут'],
        ['◀️ Назад']
    ])


def kb_risk_tolerance():
    """Risk tolerance settings"""
    return reply_keyboard([
        ['🟢 Низкий', '🟡 Средний', '🔴 Высокий'],
        ['◀️ Назад']
    ])


def kb_ai_settings():
    """AI settings"""
    return reply_keyboard([
        ['📚 Режим обучения', '🔄 Авто-восстановление'],
        ['🌡 Температура GPT'],
        ['🗑 Очистить базу знаний'],
        ['◀️ Назад']
    ])


def kb_api_keys():
    """API keys settings"""
    return reply_keyboard([
        ['🔑 Yandex GPT', '📱 OnlineSim'],
        ['🌐 Прокси'],
        ['◀️ Назад']
    ])


def kb_gpt_temperature():
    """GPT temperature selection"""
    return reply_keyboard([
        ['0.3 (точный)', '0.5', '0.7 (баланс)'],
        ['0.9', '1.0 (креативный)'],
        ['◀️ Назад']
    ])


# ==================== STATS KEYBOARDS ====================

def kb_stats_menu():
    """Statistics menu"""
    return reply_keyboard([
        ['📉 Ошибки за 7 дней', '🏆 Топ аудиторий'],
        ['📊 Активные рассылки', '⏰ Статистика по часам'],
        ['🛡 Негативные ответы', '🤖 Статистика ботовода'],
        ['◀️ Главное меню']
    ])


# ==================== INLINE KEYBOARDS ====================

def _get_reliability_emoji(reliability: float) -> str:
    """Get emoji for reliability score"""
    if reliability >= 80:
        return '🟢'
    elif reliability >= 50:
        return '🟡'
    else:
        return '🔴'


def kb_inline_audiences(sources: List[dict]) -> dict:
    """Inline keyboard for audience selection"""
    buttons = []
    for s in sources[:15]:
        emoji = '💬' if s.get('source_type') == 'comments' else '👥'
        status = {'pending': '⏳', 'running': '🔄', 'completed': '✅', 'failed': '❌'}.get(s.get('status'), '❓')
        link = s['source_link'][:20] + '..' if len(s['source_link']) > 20 else s['source_link']
        count = s.get('parsed_count', 0)
        kw_icon = '🔑' if s.get('keyword_filter') else ''
        buttons.append([{
            'text': f"{emoji}{status}{kw_icon} {link} ({count})",
            'callback_data': f"aud:{s['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_templates(templates: List[dict], folders: List[dict] = None) -> dict:
    """Inline keyboard for template selection"""
    buttons = []
    for f in (folders or [])[:5]:
        buttons.append([{
            'text': f"📁 {f['name']}",
            'callback_data': f"tfld:{f['id']}"
        }])
    for t in templates[:10]:
        if not t.get('folder_id'):
            emoji = '🖼' if t.get('media_file_id') or t.get('media_url') else '📝'
            name = t['name'][:25] + '..' if len(t['name']) > 25 else t['name']
            buttons.append([{
                'text': f"{emoji} {name}",
                'callback_data': f"tpl:{t['id']}"
            }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_folder_templates(templates: List[dict], folder_id: int) -> dict:
    """Inline keyboard for templates in folder"""
    buttons = []
    for t in templates[:15]:
        emoji = '🖼' if t.get('media_file_id') or t.get('media_url') else '📝'
        name = t['name'][:25] + '..' if len(t['name']) > 25 else t['name']
        buttons.append([{
            'text': f"{emoji} {name}",
            'callback_data': f"tpl:{t['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_template_folders(folders: List[dict], mode: str = 'move', template_id: int = 0) -> dict:
    """Inline keyboard for folder selection"""
    buttons = []
    buttons.append([{'text': '📁 Без папки', 'callback_data': f"mvtpl:{template_id}:0" if mode == 'move' else 'selfld:0'}])
    for f in folders[:10]:
        cb = f"mvtpl:{template_id}:{f['id']}" if mode == 'move' else f"selfld:{f['id']}"
        buttons.append([{'text': f"📁 {f['name']}", 'callback_data': cb}])
    return inline_keyboard(buttons)


def kb_inline_accounts(folders: List[dict], accounts: List[dict]) -> dict:
    """Inline keyboard for account selection"""
    from core.db import DB
    buttons = []
    for f in folders[:8]:
        count = DB.count_accounts_in_folder(f['id'])
        buttons.append([{
            'text': f"📁 {f['name']} ({count})",
            'callback_data': f"afld:{f['id']}"
        }])
    for a in accounts[:5]:
        status = {'active': '✅', 'pending': '⏳', 'blocked': '🚫', 'flood_wait': '⏰', 'error': '❌'}.get(a.get('status'), '❓')
        phone = a['phone']
        masked = f"{phone[:4]}**{phone[-2:]}" if len(phone) > 6 else phone
        daily = f"{a.get('daily_sent', 0) or 0}/{a.get('daily_limit', 50) or 50}"
        rel = a.get('reliability_score', 100) or 100
        rel_icon = _get_reliability_emoji(rel)
        buttons.append([{
            'text': f"{status}{rel_icon} {masked} [{daily}]",
            'callback_data': f"acc:{a['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_acc_folders(folders: List[dict], accounts: List[dict]) -> dict:
    """Inline keyboard for accounts in folder"""
    buttons = []
    for a in accounts[:15]:
        status = {'active': '✅', 'pending': '⏳', 'blocked': '🚫', 'flood_wait': '⏰', 'error': '❌'}.get(a.get('status'), '❓')
        phone = a['phone']
        masked = f"{phone[:4]}**{phone[-2:]}" if len(phone) > 6 else phone
        daily = f"{a.get('daily_sent', 0) or 0}/{a.get('daily_limit', 50) or 50}"
        rel = a.get('reliability_score', 100) or 100
        rel_icon = _get_reliability_emoji(rel)
        buttons.append([{
            'text': f"{status}{rel_icon} {masked} [{daily}]",
            'callback_data': f"acc:{a['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_account_folders(folders: List[dict], account_id: int) -> dict:
    """Inline keyboard for moving account to folder"""
    buttons = []
    buttons.append([{'text': '📁 Без папки', 'callback_data': f"mvacc:{account_id}:0"}])
    for f in folders[:10]:
        buttons.append([{'text': f"📁 {f['name']}", 'callback_data': f"mvacc:{account_id}:{f['id']}"}])
    return inline_keyboard(buttons)


def kb_inline_mailing_sources(sources: List[dict]) -> dict:
    """Inline keyboard for mailing source selection"""
    from core.db import DB
    buttons = []
    for s in sources[:15]:
        emoji = '💬' if s.get('source_type') == 'comments' else '👥'
        link = s['source_link'][:20] + '..' if len(s['source_link']) > 20 else s['source_link']
        remaining = DB.get_audience_stats(s['id']).get('remaining', 0)
        buttons.append([{
            'text': f"{emoji} {link} ({remaining} осталось)",
            'callback_data': f"msrc:{s['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_mailing_templates(templates: List[dict]) -> dict:
    """Inline keyboard for mailing template selection"""
    buttons = []
    for t in templates[:15]:
        emoji = '🖼' if t.get('media_file_id') or t.get('media_url') else '📝'
        name = t['name'][:25] + '..' if len(t['name']) > 25 else t['name']
        buttons.append([{
            'text': f"{emoji} {name}",
            'callback_data': f"mtpl:{t['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_mailing_acc_folders(folders: List[dict], accounts: List[dict]) -> dict:
    """Inline keyboard for mailing account folder selection"""
    from core.db import DB
    buttons = []
    for f in folders[:8]:
        active = DB.count_active_accounts_in_folder(f['id'])
        if active > 0:
            buttons.append([{
                'text': f"📁 {f['name']} ({active} активных)",
                'callback_data': f"macc:{f['id']}"
            }])
    active_without = [a for a in accounts if a.get('status') == 'active']
    if active_without:
        buttons.append([{
            'text': f"📁 Без папки ({len(active_without)} активных)",
            'callback_data': "macc:0"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_campaigns(campaigns: List[dict]) -> dict:
    """Inline keyboard for campaign selection"""
    buttons = []
    for c in campaigns[:10]:
        status_emoji = {'pending': '⏳', 'running': '🔄', 'paused': '⏸', 'completed': '✅', 'scheduled': '📅'}.get(c['status'], '❓')
        sent = c.get('sent_count', 0)
        total = c.get('total_count', '?')
        buttons.append([{
            'text': f"{status_emoji} #{c['id']} ({sent}/{total})",
            'callback_data': f"cmp:{c['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_scheduled(mailings: List[dict]) -> dict:
    """Inline keyboard for scheduled mailings"""
    buttons = []
    for m in mailings[:10]:
        scheduled = m.get('scheduled_at', '')[:16].replace('T', ' ')
        buttons.append([
            {'text': f"📅 #{m['id']} - {scheduled}", 'callback_data': f"schd:{m['id']}"},
            {'text': '🗑', 'callback_data': f"delschd:{m['id']}"}
        ])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_scheduled_tasks(tasks: List[dict]) -> dict:
    """Inline keyboard for scheduled tasks"""
    buttons = []
    type_emoji = {'parsing': '🔍', 'mailing': '📤', 'warmup': '🔥'}
    for t in tasks[:10]:
        emoji = type_emoji.get(t.get('task_type'), '📋')
        scheduled = t.get('scheduled_at', '')[:16].replace('T', ' ')
        repeat = '🔂' if t.get('repeat_mode') != 'once' else ''
        buttons.append([
            {'text': f"{emoji}{repeat} #{t['id']} - {scheduled}", 'callback_data': f"task:{t['id']}"},
            {'text': '🗑', 'callback_data': f"deltask:{t['id']}"}
        ])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_tags(tags: List[dict]) -> dict:
    """Inline keyboard for tags"""
    buttons = []
    for t in tags[:10]:
        buttons.append([
            {'text': f"🏷 {t['name']}", 'callback_data': 'noop'},
            {'text': '🗑', 'callback_data': f"deltag:{t['id']}"}
        ])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_audience_tags(tags: List[dict], source_id: int, current: List[str]) -> dict:
    """Inline keyboard for audience tag selection"""
    buttons = []
    for t in tags[:10]:
        check = '✅' if t['name'] in current else '⬜️'
        buttons.append([{
            'text': f"{check} {t['name']}",
            'callback_data': f"togtag:{source_id}:{t['name']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_blacklist(items: List[dict]) -> dict:
    """Inline keyboard for blacklist"""
    buttons = []
    for b in items[:10]:
        display = f"@{b['username']}" if b.get('username') else str(b.get('tg_user_id', '?'))
        source_icon = {'manual': '✋', 'auto_response': '🤖', 'auto_block': '🚫'}.get(b.get('source', 'manual'), '❓')
        buttons.append([
            {'text': f"{source_icon} {display}", 'callback_data': 'noop'},
            {'text': '✖️', 'callback_data': f"delbl:{b['id']}"}
        ])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_stop_triggers(triggers: List[dict]) -> dict:
    """Inline keyboard for stop triggers"""
    buttons = []
    for t in triggers[:15]:
        word = t['trigger_word']
        hits = t.get('hits_count', 0) or 0
        active = '✅' if t.get('is_active') else '❌'
        buttons.append([
            {'text': f"{active} «{word}» ({hits})", 'callback_data': f"togstop:{t['id']}"},
            {'text': '🗑', 'callback_data': f"delstop:{t['id']}"}
        ])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_hourly_stats(stats: List[dict]) -> dict:
    """Inline keyboard showing hourly stats summary"""
    buttons = []
    for s in stats[:24]:
        hour = s.get('hour', 0)
        sent = s.get('total_sent', 0) or 0
        success = s.get('total_success', 0) or 0
        rate = round(success / sent * 100) if sent > 0 else 0
        
        if rate >= 90:
            emoji = '🟢'
        elif rate >= 70:
            emoji = '🟡'
        else:
            emoji = '🔴'
        
        buttons.append([{
            'text': f"{emoji} {hour:02d}:00 — {sent} отпр. ({rate}%)",
            'callback_data': 'noop'
        }])
    
    return inline_keyboard(buttons) if buttons else None


# ==================== HERDER INLINE KEYBOARDS ====================

def kb_inline_monitored_channels(channels: List[dict]) -> dict:
    """Inline keyboard for monitored channels"""
    buttons = []
    for c in channels[:15]:
        status = '🟢' if c.get('is_active') else '⏸'
        priority = '🔼' if c.get('priority', 3) >= 4 else ('🔽' if c.get('priority', 3) <= 2 else '')
        name = c.get('title') or f"@{c['channel_username']}"
        name = name[:25] + '..' if len(name) > 25 else name
        actions = c.get('total_actions', 0)
        buttons.append([{
            'text': f"{status}{priority} {name} ({actions})",
            'callback_data': f"hch:{c['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_herder_assignments(assignments: List[dict]) -> dict:
    """Inline keyboard for herder assignments"""
    from core.db import DB
    buttons = []
    for a in assignments[:15]:
        status = {'active': '🟢', 'paused': '⏸', 'stopped': '🔴'}.get(a.get('status'), '❓')
        channel = DB.get_monitored_channel(a['channel_id'])
        ch_name = channel.get('title') or f"@{channel['channel_username']}" if channel else f"#{a['channel_id']}"
        ch_name = ch_name[:20] + '..' if len(ch_name) > 20 else ch_name
        actions = a.get('total_actions', 0)
        buttons.append([{
            'text': f"{status} {ch_name} ({actions} действий)",
            'callback_data': f"hass:{a['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_herder_accounts(accounts: List[dict], selected: List[int] = None) -> dict:
    """Inline keyboard for selecting accounts for herder"""
    selected = selected or []
    buttons = []
    for a in accounts[:15]:
        check = '✅' if a['id'] in selected else '⬜️'
        phone = a['phone']
        masked = f"{phone[:4]}**{phone[-2:]}" if len(phone) > 6 else phone
        profile = a.get('profile', {})
        role = profile.get('role', 'observer') if profile else 'observer'
        role_emoji = {'observer': '📖', 'expert': '🧠', 'support': '💪', 'trendsetter': '🔥'}.get(role, '👤')
        buttons.append([{
            'text': f"{check} {role_emoji} {masked}",
            'callback_data': f"hselacc:{a['id']}"
        }])
    
    buttons.append([
        {'text': '✅ Выбрать все', 'callback_data': 'hselall'},
        {'text': '❌ Снять все', 'callback_data': 'hselclear'}
    ])
    buttons.append([{'text': '➡️ Далее', 'callback_data': 'hselnext'}])
    
    return inline_keyboard(buttons)


def kb_inline_herder_strategies() -> dict:
    """Inline keyboard for strategy selection"""
    buttons = [
        [{'text': '📖 Наблюдатель', 'callback_data': 'hstrat:observer'}],
        [{'text': '🧠 Эксперт', 'callback_data': 'hstrat:expert'}],
        [{'text': '💪 Поддержка', 'callback_data': 'hstrat:support'}],
        [{'text': '🔥 Трендсеттер', 'callback_data': 'hstrat:trendsetter'}],
        [{'text': '👥 Комьюнити', 'callback_data': 'hstrat:community'}]
    ]
    return inline_keyboard(buttons)


def kb_inline_account_profiles(profiles: List[dict]) -> dict:
    """Inline keyboard for account profiles"""
    buttons = []
    for p in profiles[:15]:
        acc = p.get('account', {})
        prof = p.get('profile')
        phone = acc.get('phone', '?')
        masked = f"{phone[:4]}**{phone[-2:]}" if len(phone) > 6 else phone
        
        if prof:
            role = prof.get('role', 'observer')
            role_emoji = {'observer': '📖', 'expert': '🧠', 'support': '💪', 'trendsetter': '🔥'}.get(role, '👤')
            persona = prof.get('persona', '')[:15] + '..' if prof.get('persona') and len(prof.get('persona', '')) > 15 else prof.get('persona', '-')
            buttons.append([{
                'text': f"{role_emoji} {masked} — {persona}",
                'callback_data': f"hprof:{acc['id']}"
            }])
        else:
            buttons.append([{
                'text': f"❓ {masked} — нет профиля",
                'callback_data': f"hprof:{acc['id']}"
            }])
    
    return inline_keyboard(buttons) if buttons else None


# ==================== ANALYTICS INLINE KEYBOARDS ====================

def kb_inline_risk_accounts(accounts_with_risk: List[dict]) -> dict:
    """Inline keyboard for accounts with risk predictions"""
    buttons = []
    for item in accounts_with_risk[:15]:
        acc = item.get('account', {})
        pred = item.get('prediction')
        
        phone = acc.get('phone', '?')
        masked = f"{phone[:4]}**{phone[-2:]}" if len(phone) > 6 else phone
        
        if pred:
            risk = pred.get('risk_score', 0)
            if risk > 0.7:
                emoji = '🔴'
            elif risk > 0.4:
                emoji = '🟡'
            else:
                emoji = '🟢'
            risk_pct = int(risk * 100)
            buttons.append([{
                'text': f"{emoji} {masked} — {risk_pct}% риск",
                'callback_data': f"arisk:{acc['id']}"
            }])
        else:
            buttons.append([{
                'text': f"❓ {masked} — нет данных",
                'callback_data': f"arisk:{acc['id']}"
            }])
    
    return inline_keyboard(buttons) if buttons else None


def kb_inline_segments(segments: List[dict]) -> dict:
    """Inline keyboard for audience segments"""
    buttons = []
    type_emoji = {'hot': '🔥', 'warm': '🌡', 'cold': '❄️', 'custom': '📊'}
    for s in segments[:15]:
        emoji = type_emoji.get(s.get('segment_type'), '📊')
        name = s['name'][:25] + '..' if len(s['name']) > 25 else s['name']
        count = s.get('user_count', 0)
        buttons.append([{
            'text': f"{emoji} {name} ({count})",
            'callback_data': f"aseg:{s['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


# ==================== FACTORY INLINE KEYBOARDS ====================

def kb_inline_factory_tasks(tasks: List[dict]) -> dict:
    """Inline keyboard for factory tasks"""
    buttons = []
    status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'failed': '❌'}
    for t in tasks[:10]:
        emoji = status_emoji.get(t.get('status'), '❓')
        created = t.get('created_count', 0)
        total = t.get('count', 0)
        buttons.append([{
            'text': f"{emoji} #{t['id']} — {created}/{total} создано",
            'callback_data': f"ftask:{t['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_warmup_accounts(accounts: List[dict]) -> dict:
    """Inline keyboard for accounts in warmup"""
    buttons = []
    for a in accounts[:15]:
        phone = a.get('phone', '?')
        masked = f"{phone[:4]}**{phone[-2:]}" if len(phone) > 6 else phone
        
        warmup_status = a.get('warmup_status', 'none')
        if warmup_status == 'in_progress':
            emoji = '🔥'
            day = a.get('warmup_day', 1)
            text = f"{emoji} {masked} — день {day}"
        elif warmup_status == 'completed':
            emoji = '✅'
            text = f"{emoji} {masked} — готов"
        else:
            emoji = '⏳'
            text = f"{emoji} {masked} — ожидает"
        
        buttons.append([{
            'text': text,
            'callback_data': f"fwarm:{a['id']}"
        }])
    
    return inline_keyboard(buttons) if buttons else None


# ==================== CONTENT INLINE KEYBOARDS ====================

def kb_inline_user_channels(channels: List[dict]) -> dict:
    """Inline keyboard for user channels"""
    buttons = []
    for c in channels[:10]:
        name = c.get('title') or f"@{c['channel_username']}"
        name = name[:25] + '..' if len(name) > 25 else name
        buttons.append([{
            'text': f"📢 {name}",
            'callback_data': f"uch:{c['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None


def kb_inline_generated_content(content: List[dict]) -> dict:
    """Inline keyboard for generated content"""
    buttons = []
    status_emoji = {'draft': '📝', 'scheduled': '📅', 'published': '✅', 'rejected': '❌'}
    for c in content[:15]:
        emoji = status_emoji.get(c.get('status'), '📝')
        title = c.get('title') or c.get('content', '')[:20]
        title = title[:25] + '..' if len(title) > 25 else title
        buttons.append([{
            'text': f"{emoji} {title}",
            'callback_data': f"gcont:{c['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None
