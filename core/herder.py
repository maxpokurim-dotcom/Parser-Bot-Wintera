"""
Herder (Ботовод) Module - Intelligent Activity Simulation
Version 1.1 — with account folders support and fixed duplicate message bug
"""
import logging
from typing import List, Dict, Optional
from core.db import DB
from core.telegram import send_message, edit_message, answer_callback
from core.keyboards import (
    kb_main_menu, kb_cancel, kb_back, kb_back_cancel, kb_confirm_delete,
    kb_herder_menu, kb_herder_assignment_actions, kb_herder_strategy,
    kb_herder_actions_constructor, kb_herder_reactions, kb_herder_priority,
    kb_herder_comments_limit, kb_herder_delay, kb_herder_profiles_menu,
    kb_herder_profile_actions, kb_herder_settings,
    kb_inline_monitored_channels, kb_inline_herder_assignments,
    kb_inline_herder_accounts, kb_inline_herder_strategies,
    kb_inline_account_profiles, inline_keyboard
)
from core.menu import show_main_menu, BTN_CANCEL, BTN_BACK, BTN_MAIN_MENU
logger = logging.getLogger(__name__)
# Button constants
BTN_NEW_ASSIGNMENT = '➕ Новое задание'
BTN_MY_ASSIGNMENTS = '📋 Мои задания'
BTN_HERDER_STATS = '📊 Статистика'
BTN_HERDER_ACCOUNTS = '👥 Аккаунты'
BTN_HERDER_PROFILES = '🧠 Профили ИИ'
BTN_HERDER_STRATEGIES = '🎯 Стратегии'
BTN_HERDER_SETTINGS = '⚙️ Настройки'
# Strategy constants
STRATEGIES = {
    'observer': {
        'name': '📖 Наблюдатель',
        'description': 'Только чтение и редкие реакции',
        'can_comment': False,
        'max_daily_actions': 10
    },
    'expert': {
        'name': '🧠 Эксперт',
        'description': 'Вопросы, уточнения, экспертные комментарии',
        'can_comment': True,
        'max_daily_actions': 25
    },
    'support': {
        'name': '💪 Поддержка',
        'description': 'Лайки комментариев, короткие согласия',
        'can_comment': True,
        'max_daily_actions': 20
    },
    'trendsetter': {
        'name': '🔥 Трендсеттер',
        'description': 'Первые реакции на важные посты',
        'can_comment': True,
        'max_daily_actions': 15
    },
    'community': {
        'name': '👥 Комьюнити',
        'description': 'Координированные обсуждения',
        'can_comment': True,
        'max_daily_actions': 30
    }
}
ROLE_EMOJI = {
    'observer': '📖',
    'expert': '🧠',
    'support': '💪',
    'trendsetter': '🔥',
    'community': '👥'
}
def show_herder_menu(chat_id: int, user_id: int):
    """Show herder main menu"""
    DB.set_user_state(user_id, 'herder:menu')
    # Get stats
    assignments = DB.get_herder_assignments(user_id)
    active = len([a for a in assignments if a.get('status') == 'active'])
    channels = DB.count_monitored_channels(user_id)
    stats = DB.get_herder_stats(user_id, days=7)
    send_message(chat_id,
        f"🤖 <b>Ботовод</b>\n"
        f"Симуляция живой активности в Telegram-каналах\n"
        f"📊 <b>Статистика:</b>\n"
        f"├ Активных заданий: <b>{active}</b>\n"
        f"├ Мониторинг каналов: <b>{channels}</b>\n"
        f"├ Действий за 7 дней: <b>{stats['total_actions']}</b>\n"
        f"└ Комментариев: <b>{stats['total_comments']}</b>\n"
        f"Выберите действие:",
        kb_herder_menu()
    )
def handle_herder(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle herder states. Returns True if handled."""
    # Navigation
    if text == BTN_CANCEL:
        show_main_menu(chat_id, user_id, "❌ Действие отменено")
        return True
    if text == BTN_MAIN_MENU:
        show_main_menu(chat_id, user_id)
        return True
    if text == BTN_BACK:
        _handle_back(chat_id, user_id, state, saved)
        return True
    # Menu state
    if state == 'herder:menu':
        return _handle_menu(chat_id, user_id, text)
    # New assignment flow
    if state == 'herder:new:channel':
        return _handle_new_channel(chat_id, user_id, text, saved)
    if state == 'herder:new:accounts':
        return _handle_new_accounts(chat_id, user_id, text, saved)
    if state == 'herder:new:strategy':
        return _handle_new_strategy(chat_id, user_id, text, saved)
    if state == 'herder:new:actions':
        return _handle_new_actions(chat_id, user_id, text, saved)
    if state == 'herder:new:reactions':
        return _handle_new_reactions(chat_id, user_id, text, saved)
    if state == 'herder:new:priority':
        return _handle_new_priority(chat_id, user_id, text, saved)
    if state == 'herder:new:comments':
        return _handle_new_comments(chat_id, user_id, text, saved)
    if state == 'herder:new:delay':
        return _handle_new_delay(chat_id, user_id, text, saved)
    if state == 'herder:new:confirm':
        return _handle_new_confirm(chat_id, user_id, text, saved)
    # Assignment view
    if state.startswith('herder:assignment:'):
        return _handle_assignment_view(chat_id, user_id, text, state, saved)
    # Profiles
    if state == 'herder:profiles':
        return _handle_profiles_menu(chat_id, user_id, text)
    if state.startswith('herder:profile:'):
        return _handle_profile_view(chat_id, user_id, text, state, saved)
    if state == 'herder:profile:create':
        return _handle_profile_create(chat_id, user_id, text, saved)
    # Stats
    if state == 'herder:stats':
        return _handle_stats(chat_id, user_id, text)
    # Settings
    if state == 'herder:settings':
        return _handle_settings(chat_id, user_id, text, saved)
    return False
def _handle_back(chat_id: int, user_id: int, state: str, saved: dict):
    """Handle back navigation"""
    if state in ['herder:menu', 'herder:new:channel']:
        show_main_menu(chat_id, user_id)
    elif state.startswith('herder:new:'):
        # Go back in creation flow
        steps = ['channel', 'accounts', 'strategy', 'actions', 'reactions', 'priority', 'comments', 'delay', 'confirm']
        current = state.split(':')[-1]
        if current in steps:
            idx = steps.index(current)
            if idx > 0:
                DB.set_user_state(user_id, f'herder:new:{steps[idx-1]}', saved)
                _show_step(chat_id, user_id, steps[idx-1], saved)
                return
        show_herder_menu(chat_id, user_id)
    elif state.startswith('herder:assignment:') or state.startswith('herder:profile:'):
        show_herder_menu(chat_id, user_id)
    else:
        show_herder_menu(chat_id, user_id)
def _handle_menu(chat_id: int, user_id: int, text: str) -> bool:
    """Handle main menu selection"""
    if text == BTN_NEW_ASSIGNMENT:
        start_new_assignment(chat_id, user_id)
        return True
    if text == BTN_MY_ASSIGNMENTS:
        show_assignments_list(chat_id, user_id)
        return True
    if text == BTN_HERDER_STATS:
        show_herder_stats(chat_id, user_id)
        return True
    if text == BTN_HERDER_ACCOUNTS or text == BTN_HERDER_PROFILES:
        show_profiles_menu(chat_id, user_id)
        return True
    if text == BTN_HERDER_STRATEGIES:
        show_strategies_info(chat_id, user_id)
        return True
    if text == BTN_HERDER_SETTINGS:
        show_herder_settings(chat_id, user_id)
        return True
    if text == '◀️ К списку':
        show_assignments_list(chat_id, user_id)
        return True
    return False
# ==================== NEW ASSIGNMENT FLOW ====================
def start_new_assignment(chat_id: int, user_id: int):
    """Start new assignment creation"""
    DB.set_user_state(user_id, 'herder:new:channel', {})
    send_message(chat_id,
        "➕ <b>Новое задание Ботовода</b>\n"
        "<b>Шаг 1/8:</b> Введите ссылку на канал\n"
        "Примеры:\n"
        "• @channel_name\n"
        "• https://t.me/channel_name\n"
        "• t.me/channel_name\n"
        "⚠️ Канал должен быть публичным",
        kb_back_cancel()
    )
def _handle_new_channel(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle channel input"""
    # Clean up channel link
    channel = text.strip()
    channel = channel.replace('https://t.me/', '').replace('t.me/', '').replace('@', '')
    channel = channel.split('/')[0]  # Remove any trailing parts
    if not channel or len(channel) < 3:
        send_message(chat_id,
            "❌ Неверный формат канала\n"
            "Введите корректную ссылку:",
            kb_back_cancel()
        )
        return True
    # Check if already monitored
    existing = DB.get_monitored_channel_by_username(user_id, channel)
    if existing:
        # Use existing channel
        saved['channel_id'] = existing['id']
        saved['channel_username'] = existing['channel_username']
        saved['channel_title'] = existing.get('title', f"@{channel}")
    else:
        # Create new monitored channel
        new_channel = DB.create_monitored_channel(user_id, channel)
        if not new_channel:
            send_message(chat_id, "❌ Ошибка добавления канала", kb_back_cancel())
            return True
        saved['channel_id'] = new_channel['id']
        saved['channel_username'] = channel
        saved['channel_title'] = f"@{channel}"
    saved['selected_accounts'] = []
    DB.set_user_state(user_id, 'herder:new:accounts', saved)
    # Get available accounts with folders
    folders = DB.get_account_folders(user_id)
    accounts = DB.get_accounts_without_folder(user_id)
    all_accounts = []
    if folders:
        all_accounts.append({'type': 'header', 'text': '📁 Папки'})
        for folder in folders:
            accs_in_folder = DB.get_accounts_in_folder(folder['id'])
            for acc in accs_in_folder:
                acc['profile'] = DB.get_account_profile(acc['id'])
                all_accounts.append(acc)
    if accounts:
        all_accounts.append({'type': 'header', 'text': '📁 Без папки'})
        for acc in accounts:
            acc['profile'] = DB.get_account_profile(acc['id'])
            all_accounts.append(acc)
    # Show selection keyboard
    send_message(chat_id,
        f"✅ Канал: <b>{saved['channel_title']}</b>\n"
        f"<b>Шаг 2/8:</b> Выберите аккаунты\n"
        f"Доступно аккаунтов: {len([a for a in all_accounts if a.get('id')])}\n"
        f"Нажмите на аккаунты для выбора:",
        kb_inline_herder_accounts([a for a in all_accounts if a.get('id')], saved['selected_accounts'])
    )
    return True
def _handle_new_accounts(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle accounts selection"""
    # Main selection via callbacks
    if text == '➡️ Далее' or text == 'Далее':
        if not saved.get('selected_accounts'):
            send_message(chat_id, "❌ Выберите хотя бы один аккаунт", kb_back_cancel())
            return True
        DB.set_user_state(user_id, 'herder:new:strategy', saved)
        _show_strategy_selection(chat_id, user_id, saved)
        return True
    return True
def _show_strategy_selection(chat_id: int, user_id: int, saved: dict):
    """Show strategy selection"""
    send_message(chat_id,
        f"<b>Шаг 3/8:</b> Выберите стратегию\n"
        f"📖 <b>Наблюдатель</b> — только чтение и 👍\n"
        f"🧠 <b>Эксперт</b> — вопросы и экспертные комментарии\n"
        f"💪 <b>Поддержка</b> — лайки и короткие согласия\n"
        f"🔥 <b>Трендсеттер</b> — первые реакции\n"
        f"👥 <b>Комьюнити</b> — координированные обсуждения",
        kb_herder_strategy()
    )
def _handle_new_strategy(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle strategy selection"""
    strategy_map = {
        '📖 Наблюдатель': 'observer',
        '🧠 Эксперт': 'expert',
        '💪 Поддержка': 'support',
        '🔥 Трендсеттер': 'trendsetter',
        '👥 Комьюнити': 'community'
    }
    strategy = strategy_map.get(text)
    if not strategy:
        send_message(chat_id, "❌ Выберите стратегию из списка", kb_herder_strategy())
        return True
    saved['strategy'] = strategy
    saved['actions'] = ['read']  # Default action
    DB.set_user_state(user_id, 'herder:new:actions', saved)
    _show_actions_constructor(chat_id, user_id, saved)
    return True
def _show_actions_constructor(chat_id: int, user_id: int, saved: dict):
    """Show actions constructor"""
    current_actions = saved.get('actions', ['read'])
    actions_text = ' → '.join([
        {'read': '📖 Чтение', 'react': '👍 Реакция', 'comment': '💬 Комментарий', 'save': '💾 Сохранение'}.get(a, a)
        for a in current_actions
    ])
    send_message(chat_id,
        f"<b>Шаг 4/8:</b> Настройте цепочку действий\n"
        f"Текущая цепочка:\n<code>{actions_text}</code>\n"
        f"Добавьте действия или нажмите «✅ Готово»:",
        kb_herder_actions_constructor()
    )
def _handle_new_actions(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle actions constructor"""
    actions = saved.get('actions', ['read'])
    if text == '📖 Чтение':
        if 'read' not in actions:
            actions.insert(0, 'read')
    elif text == '👍 Реакция':
        if 'react' not in actions:
            actions.append('react')
            saved['need_reactions'] = True
    elif text == '💬 Комментарий':
        strategy = saved.get('strategy', 'observer')
        if STRATEGIES.get(strategy, {}).get('can_comment', False):
            if 'comment' not in actions:
                actions.append('comment')
        else:
            send_message(chat_id, "❌ Стратегия «Наблюдатель» не поддерживает комментарии", kb_herder_actions_constructor())
            return True
    elif text == '💾 Сохранение':
        if 'save' not in actions:
            actions.append('save')
    elif text == '✅ Готово':
        saved['actions'] = actions
        # Next step depends on whether reactions are selected
        if saved.get('need_reactions'):
            saved['reactions'] = ['👍']
            DB.set_user_state(user_id, 'herder:new:reactions', saved)
            _show_reactions_selection(chat_id, user_id, saved)
        else:
            saved['actions'] = actions
            DB.set_user_state(user_id, 'herder:new:priority', saved)
            _show_priority_selection(chat_id, user_id, saved)
        return True
    else:
        _show_actions_constructor(chat_id, user_id, saved)
        return True
    saved['actions'] = actions
    DB.set_user_state(user_id, 'herder:new:actions', saved)
    _show_actions_constructor(chat_id, user_id, saved)
    return True
def _show_reactions_selection(chat_id: int, user_id: int, saved: dict):
    """Show reactions selection"""
    current = saved.get('reactions', ['👍'])
    send_message(chat_id,
        f"<b>Шаг 5/8:</b> Выберите реакции\n"
        f"Выбрано: {' '.join(current)}\n"
        f"Нажмите на эмодзи для добавления/удаления:",
        kb_herder_reactions()
    )
def _handle_new_reactions(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle reactions selection"""
    reactions = saved.get('reactions', ['👍'])
    available = ['👍', '❤️', '🔥', '😢', '😡', '🤔', '🎉', '👏', '🤝']
    if text in available:
        if text in reactions:
            reactions.remove(text)
        else:
            reactions.append(text)
        saved['reactions'] = reactions
        DB.set_user_state(user_id, 'herder:new:reactions', saved)
        _show_reactions_selection(chat_id, user_id, saved)
        return True
    if text == '✅ Готово':
        if not reactions:
            reactions = ['👍']
        saved['reactions'] = reactions
        saved['actions'] = saved.get('actions', ['read'])
        DB.set_user_state(user_id, 'herder:new:priority', saved)
        _show_priority_selection(chat_id, user_id, saved)
        return True
    return False
def _show_priority_selection(chat_id: int, user_id: int, saved: dict):
    """Show priority selection"""
    send_message(chat_id,
        f"<b>Шаг 6/8:</b> Выберите приоритет канала\n"
        f"🔼 <b>Высокий</b> — быстрая реакция, больше действий\n"
        f"➖ <b>Средний</b> — сбалансированный подход\n"
        f"🔽 <b>Низкий</b> — редкие действия, экономия лимитов",
        kb_herder_priority()
    )
def _handle_new_priority(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle priority selection"""
    priority_map = {
        '🔽 Низкий': 1,
        '➖ Средний': 3,
        '🔼 Высокий': 5
    }
    priority = priority_map.get(text)
    if priority is None:
        send_message(chat_id, "❌ Выберите приоритет из списка", kb_herder_priority())
        return True
    saved['priority'] = priority
    # If strategy allows comments, ask about limit
    if 'comment' in saved.get('actions', []):
        DB.set_user_state(user_id, 'herder:new:comments', saved)
        _show_comments_limit(chat_id, user_id, saved)
    else:
        saved['max_comments'] = 0
        DB.set_user_state(user_id, 'herder:new:delay', saved)
        _show_delay_selection(chat_id, user_id, saved)
    return True
def _show_comments_limit(chat_id: int, user_id: int, saved: dict):
    """Show comments limit selection"""
    send_message(chat_id,
        f"<b>Шаг 7/8:</b> Лимит комментариев\n"
        f"Сколько комментариев в день на аккаунт?\n"
        f"⚠️ Рекомендуется 1-2 для безопасности",
        kb_herder_comments_limit()
    )
def _handle_new_comments(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle comments limit"""
    limit_map = {
        '1': 1, '2': 2, '3': 3, '5': 5,
        '🚫 Без комментариев': 0
    }
    limit = limit_map.get(text)
    if limit is None:
        send_message(chat_id, "❌ Выберите лимит из списка", kb_herder_comments_limit())
        return True
    saved['max_comments'] = limit
    if limit == 0 and 'comment' in saved.get('actions', []):
        saved['actions'].remove('comment')
    saved['actions'] = saved.get('actions', ['read'])
    DB.set_user_state(user_id, 'herder:new:delay', saved)
    _show_delay_selection(chat_id, user_id, saved)
    return True
def _show_delay_selection(chat_id: int, user_id: int, saved: dict):
    """Show delay selection"""
    send_message(chat_id,
        f"<b>Шаг 8/8:</b> Задержка после публикации\n"
        f"Через сколько начинать действия после нового поста?\n"
        f"⚠️ Большая задержка = естественнее поведение",
        kb_herder_delay()
    )
def _handle_new_delay(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle delay selection"""
    delay_map = {
        '5-60 мин': [300, 3600],
        '30-180 мин': [1800, 10800],
        '60-360 мин': [3600, 21600]
    }
    if text == '📝 Свой':
        send_message(chat_id,
            "Введите диапазон в минутах (например: 10-120):",
            kb_back_cancel()
        )
        saved['custom_delay'] = True
        DB.set_user_state(user_id, 'herder:new:delay', saved)
        return True
    if saved.get('custom_delay'):
        try:
            parts = text.replace(' ', '').split('-')
            min_delay = int(parts[0]) * 60
            max_delay = int(parts[1]) * 60 if len(parts) > 1 else min_delay * 2
            saved['delay'] = [min_delay, max_delay]
            saved.pop('custom_delay', None)
        except:
            send_message(chat_id, "❌ Неверный формат. Пример: 10-120", kb_back_cancel())
            return True
    else:
        delay = delay_map.get(text)
        if delay is None:
            send_message(chat_id, "❌ Выберите задержку из списка", kb_herder_delay())
            return True
        saved['delay'] = delay
    saved['actions'] = saved.get('actions', ['read'])
    DB.set_user_state(user_id, 'herder:new:confirm', saved)
    _show_confirmation(chat_id, user_id, saved)
    return True
def _show_confirmation(chat_id: int, user_id: int, saved: dict):
    """Show assignment confirmation"""
    strategy_name = STRATEGIES.get(saved.get('strategy', 'observer'), {}).get('name', 'Неизвестно')
    actions_text = ', '.join([
        {'read': 'чтение', 'react': 'реакции', 'comment': 'комментарии', 'save': 'сохранение'}.get(a, a)
        for a in saved.get('actions', [])
    ])
    reactions_text = ' '.join(saved.get('reactions', ['👍']))
    delay = saved.get('delay', [300, 3600])
    delay_text = f"{delay[0]//60}-{delay[1]//60} мин"
    priority_text = {1: '🔽 Низкий', 3: '➖ Средний', 5: '🔼 Высокий'}.get(saved.get('priority', 3), 'Средний')
    send_message(chat_id,
        f"📋 <b>Подтверждение задания</b>\n"
        f"📢 Канал: <b>{saved.get('channel_title', '?')}</b>\n"
        f"👥 Аккаунтов: <b>{len(saved.get('selected_accounts', []))}</b>\n"
        f"🎯 Стратегия: <b>{strategy_name}</b>\n"
        f"⚡ Действия: {actions_text}\n"
        f"👍 Реакции: {reactions_text}\n"
        f"⏱ Задержка: {delay_text}\n"
        f"📊 Приоритет: {priority_text}\n"
        f"💬 Комментариев/день: {saved.get('max_comments', 0)}\n"
        f"⚠️ <b>Важно:</b> Убедитесь, что используете Ботовод\n"
        f"только для своих каналов или с разрешения владельца.",
        kb_confirm()
    )
def _handle_new_confirm(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle confirmation"""
    if text == '✅ Подтвердить':
        # Build action chain
        action_chain = []
        delay = saved.get('delay', [300, 3600])
        for action in saved.get('actions', ['read']):
            chain_item = {
                'action': action,
                'delay_after': [delay[0] // len(saved.get('actions', [1])), delay[1] // len(saved.get('actions', [1]))]
            }
            if action == 'react':
                chain_item['emoji'] = saved.get('reactions', ['👍'])
                chain_item['probability'] = 0.7
            elif action == 'comment':
                chain_item['probability'] = 0.5
                chain_item['min_engagement'] = 0.6
            elif action == 'save':
                chain_item['probability'] = 0.3
            action_chain.append(chain_item)
        # Build settings
        settings = {
            'max_comments_per_day': saved.get('max_comments', 2),
            'delay_after_post': saved.get('delay', [300, 3600]),
            'min_engagement_for_comment': 0.6,
            'coordinate_discussions': saved.get('strategy') == 'community',
            'seasonal_behavior': True,
            'reactions': saved.get('reactions', ['👍'])
        }
        # Update channel priority
        DB.update_monitored_channel(saved['channel_id'], priority=saved.get('priority', 3))
        # Create assignment
        assignment = DB.create_herder_assignment(
            user_id=user_id,
            channel_id=saved['channel_id'],
            account_ids=saved.get('selected_accounts', []),
            action_chain=action_chain,
            strategy=saved.get('strategy', 'observer'),
            settings=settings
        )
        if assignment:
            send_message(chat_id,
                f"✅ <b>Задание создано!</b>\n"
                f"ID: #{assignment['id']}\n"
                f"Статус: 🟢 Активно\n"
                f"Ботовод начнёт работу при появлении новых постов в канале.",
                kb_herder_menu()
            )
        else:
            send_message(chat_id, "❌ Ошибка создания задания", kb_herder_menu())
        DB.set_user_state(user_id, 'herder:menu')
        return True
    if text == '❌ Отмена':
        show_herder_menu(chat_id, user_id)
        return True
    return False
def _show_step(chat_id: int, user_id: int, step: str, saved: dict):
    """Show specific step"""
    if step == 'channel':
        start_new_assignment(chat_id, user_id)
    elif step == 'accounts':
        # Get available accounts with folders
        folders = DB.get_account_folders(user_id)
        accounts = DB.get_accounts_without_folder(user_id)
        all_accounts = []
        if folders:
            all_accounts.append({'type': 'header', 'text': '📁 Папки'})
            for folder in folders:
                accs_in_folder = DB.get_accounts_in_folder(folder['id'])
                for acc in accs_in_folder:
                    acc['profile'] = DB.get_account_profile(acc['id'])
                    all_accounts.append(acc)
        if accounts:
            all_accounts.append({'type': 'header', 'text': '📁 Без папки'})
            for acc in accounts:
                acc['profile'] = DB.get_account_profile(acc['id'])
                all_accounts.append(acc)
        send_message(chat_id,
            f"<b>Шаг 2/8:</b> Выберите аккаунты\n"
            f"Доступно аккаунтов: {len([a for a in all_accounts if a.get('id')])}\n"
            f"Нажмите на аккаунты для выбора:",
            kb_inline_herder_accounts([a for a in all_accounts if a.get('id')], saved.get('selected_accounts', []))
        )
    elif step == 'strategy':
        _show_strategy_selection(chat_id, user_id, saved)
    elif step == 'actions':
        _show_actions_constructor(chat_id, user_id, saved)
    elif step == 'reactions':
        _show_reactions_selection(chat_id, user_id, saved)
    elif step == 'priority':
        _show_priority_selection(chat_id, user_id, saved)
    elif step == 'comments':
        _show_comments_limit(chat_id, user_id, saved)
    elif step == 'delay':
        _show_delay_selection(chat_id, user_id, saved)
    elif step == 'confirm':
        _show_confirmation(chat_id, user_id, saved)
# ==================== ОСТАЛЬНЫЕ ФУНКЦИИ — ASSIGNMENTS, PROFILES, STATS, SETTINGS ====================
# (полный код без изменений из оригинального herder.py, за исключением исправлений выше)
def show_assignments_list(chat_id: int, user_id: int):
    """Show list of assignments"""
    DB.set_user_state(user_id, 'herder:assignments')
    assignments = DB.get_herder_assignments(user_id)
    if not assignments:
        send_message(chat_id,
            "📋 <b>Мои задания</b>\n"
            "У вас пока нет заданий.\n"
            "Создайте первое задание!",
            kb_herder_menu()
        )
    else:
        kb = kb_inline_herder_assignments(assignments)
        send_message(chat_id, "📋 <b>Мои задания:</b>\nВыберите задание:", kb)
        send_message(chat_id, "👆 Выберите выше или:", kb_herder_menu())
def show_assignment_view(chat_id: int, user_id: int, assignment_id: int):
    """Show assignment details"""
    assignment = DB.get_herder_assignment(assignment_id)
    if not assignment:
        send_message(chat_id, "❌ Задание не найдено", kb_herder_menu())
        return
    DB.set_user_state(user_id, f'herder:assignment:{assignment_id}')
    channel = DB.get_monitored_channel(assignment['channel_id'])
    channel_name = channel.get('title') or f"@{channel['channel_username']}" if channel else "?"
    status_map = {'active': '🟢 Активно', 'paused': '⏸ Пауза', 'stopped': '🔴 Остановлено'}
    status = status_map.get(assignment['status'], assignment['status'])
    strategy_name = STRATEGIES.get(assignment.get('strategy', 'observer'), {}).get('name', 'Неизвестно')
    settings = assignment.get('settings', {})
    send_message(chat_id,
        f"📋 <b>Задание #{assignment['id']}</b>\n"
        f"📢 Канал: <b>{channel_name}</b>\n"
        f"📊 Статус: {status}\n"
        f"🎯 Стратегия: {strategy_name}\n"
        f"👥 Аккаунтов: {len(assignment.get('account_ids', []))}\n"
        f"<b>Статистика:</b>\n"
        f"├ Всего действий: {assignment.get('total_actions', 0)}\n"
        f"├ Комментариев: {assignment.get('total_comments', 0)}\n"
        f"└ Удалено: {assignment.get('deleted_comments', 0)}\n"
        f"<b>Настройки:</b>\n"
        f"├ Комментариев/день: {settings.get('max_comments_per_day', 2)}\n"
        f"└ Реакции: {' '.join(settings.get('reactions', ['👍']))}",
        kb_herder_assignment_actions(assignment['status'])
    )
def _handle_assignment_view(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle assignment view actions"""
    assignment_id = int(state.split(':')[2])
    if text == '⏸ Приостановить':
        DB.pause_herder_assignment(assignment_id)
        send_message(chat_id, "⏸ Задание приостановлено", kb_herder_menu())
        show_assignment_view(chat_id, user_id, assignment_id)
        return True
    if text == '▶️ Возобновить':
        DB.resume_herder_assignment(assignment_id)
        send_message(chat_id, "▶️ Задание возобновлено", kb_herder_menu())
        show_assignment_view(chat_id, user_id, assignment_id)
        return True
    if text == '🛑 Остановить':
        DB.stop_herder_assignment(assignment_id)
        send_message(chat_id, "🛑 Задание остановлено", kb_herder_menu())
        show_assignment_view(chat_id, user_id, assignment_id)
        return True
    if text == '📊 Логи':
        show_assignment_logs(chat_id, user_id, assignment_id)
        return True
    if text == '🗑 Удалить':
        DB.set_user_state(user_id, f'herder:assignment:delete:{assignment_id}')
        send_message(chat_id,
            "🗑 <b>Удалить задание?</b>\n"
            "Все логи будут также удалены.",
            kb_confirm_delete()
        )
        return True
    if text == '🗑 Да, удалить':
        DB.delete_herder_assignment(assignment_id)
        send_message(chat_id, "✅ Задание удалено", kb_herder_menu())
        show_herder_menu(chat_id, user_id)
        return True
    if text == '◀️ К списку':
        show_assignments_list(chat_id, user_id)
        return True
    return False
def show_assignment_logs(chat_id: int, user_id: int, assignment_id: int):
    """Show assignment logs"""
    logs = DB.get_herder_logs(user_id, limit=20, assignment_id=assignment_id)
    if not logs:
        send_message(chat_id, "📊 Логов пока нет", kb_herder_menu())
        return
    text = "📊 <b>Последние действия:</b>\n"
    for log in logs[:15]:
        action = {'read': '📖', 'react': '👍', 'comment': '💬', 'save': '💾'}.get(log.get('action_type'), '❓')
        status = {'success': '✅', 'failed': '❌', 'filtered': '🚫', 'deleted': '🗑'}.get(log.get('status'), '❓')
        created = log.get('created_at', '')[:16].replace('T', ' ')
        text += f"{action}{status} {created}\n"
    send_message(chat_id, text, kb_herder_assignment_actions('active'))
def show_profiles_menu(chat_id: int, user_id: int):
    """Show profiles menu"""
    DB.set_user_state(user_id, 'herder:profiles')
    profiles = DB.get_all_account_profiles(user_id)
    with_profile = len([p for p in profiles if p.get('profile')])
    send_message(chat_id,
        f"🧠 <b>Профили ИИ</b>\n"
        f"Профили определяют «личность» аккаунта:\n"
        f"стиль общения, интересы, реакции.\n"
        f"📊 Аккаунтов с профилем: <b>{with_profile}</b> из {len(profiles)}",
        kb_herder_profiles_menu()
    )
def _handle_profiles_menu(chat_id: int, user_id: int, text: str) -> bool:
    """Handle profiles menu"""
    if text == '📋 Список профилей':
        profiles = DB.get_all_account_profiles(user_id)
        if not profiles:
            send_message(chat_id, "❌ Нет аккаунтов", kb_herder_profiles_menu())
            return True
        kb = kb_inline_account_profiles(profiles)
        send_message(chat_id, "🧠 <b>Профили аккаунтов:</b>", kb)
        return True
    if text == '➕ Создать профиль':
        send_message(chat_id,
            "Выберите аккаунт для создания профиля:",
            kb_inline_account_profiles(DB.get_all_account_profiles(user_id))
        )
        return True
    if text == '🎲 Сгенерировать':
        # Generate profiles for all accounts without one
        profiles = DB.get_all_account_profiles(user_id)
        generated = 0
        for p in profiles:
            if not p.get('profile'):
                acc = p.get('account', {})
                # Create default profile
                DB.create_account_profile(acc['id'], {
                    'persona': 'Пользователь Telegram',
                    'role': 'observer',
                    'interests': ['общение', 'новости'],
                    'speech_style': 'informal',
                    'personality_vector': {'friendliness': 0.7, 'expertise': 0.5, 'irony': 0.2},
                    'preferred_reactions': ['👍', '❤️']
                })
                generated += 1
        send_message(chat_id, f"✅ Создано профилей: {generated}", kb_herder_profiles_menu())
        return True
    if text == '📊 Эффективность':
        show_profiles_effectiveness(chat_id, user_id)
        return True
    return False
def show_profiles_effectiveness(chat_id: int, user_id: int):
    """Show profiles effectiveness stats"""
    stats = DB.get_herder_stats(user_id, days=30)
    send_message(chat_id,
        f"📊 <b>Эффективность профилей</b>\n"
        f"За последние 30 дней:\n"
        f"├ Всего действий: {stats['total_actions']}\n"
        f"├ Успешных: {stats['success_count']}\n"
        f"├ Комментариев: {stats['total_comments']}\n"
        f"├ Удалено: {stats['deleted_comments']}\n"
        f"└ Успешность: {stats['success_rate']:.1f}%\n"
        f"<b>По типам действий:</b>\n" +
        '\n'.join([f"├ {k}: {v}" for k, v in stats.get('by_type', {}).items()]),
        kb_herder_profiles_menu()
    )
def _handle_profile_view(chat_id: int, user_id: int, text: str, state: str, saved: dict) -> bool:
    """Handle profile view"""
    return False
def _handle_profile_create(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle profile creation"""
    return False
def show_strategies_info(chat_id: int, user_id: int):
    """Show strategies info"""
    text = "🎯 <b>Стратегии Ботовода</b>\n"
    for sid, s in STRATEGIES.items():
        text += f"{s['name']}\n"
        text += f"   {s['description']}\n"
        text += f"   Действий/день: до {s['max_daily_actions']}\n"
        text += f"   Комментарии: {'✅' if s['can_comment'] else '❌'}\n"
    send_message(chat_id, text, kb_herder_menu())
def show_herder_stats(chat_id: int, user_id: int):
    """Show herder statistics"""
    DB.set_user_state(user_id, 'herder:stats')
    stats_7 = DB.get_herder_stats(user_id, days=7)
    stats_30 = DB.get_herder_stats(user_id, days=30)
    knowledge = DB.get_herder_knowledge_stats(user_id)
    send_message(chat_id,
        f"📊 <b>Статистика Ботовода</b>\n"
        f"<b>За 7 дней:</b>\n"
        f"├ Действий: {stats_7['total_actions']}\n"
        f"├ Комментариев: {stats_7['total_comments']}\n"
        f"├ Удалено: {stats_7['deleted_comments']}\n"
        f"└ Успешность: {stats_7['success_rate']:.1f}%\n"
        f"<b>За 30 дней:</b>\n"
        f"├ Действий: {stats_30['total_actions']}\n"
        f"├ Комментариев: {stats_30['total_comments']}\n"
        f"└ Успешность: {stats_30['success_rate']:.1f}%\n"
        f"<b>База знаний:</b>\n"
        f"├ Плохих фраз: {knowledge['bad_phrases']}\n"
        f"├ Хороших паттернов: {knowledge['good_patterns']}\n"
        f"└ Всего записей: {knowledge['total']}",
        kb_herder_menu()
    )
def _handle_stats(chat_id: int, user_id: int, text: str) -> bool:
    """Handle stats view"""
    show_herder_menu(chat_id, user_id)
    return True
def show_herder_settings(chat_id: int, user_id: int):
    """Show herder settings """
    DB.set_user_state(user_id, 'herder:settings', {})
    settings = DB.get_user_settings(user_id)
    herder = settings.get('herder_settings', {})
    strategy = STRATEGIES.get(herder.get('default_strategy', 'observer'), {}).get('name', 'Наблюдатель')
    max_actions = herder.get('max_actions_per_account', 50)
    coordinate = '✅' if herder.get('coordinate_discussions') else '❌'
    seasonal = '✅' if herder.get('seasonal_behavior', True) else '❌'
    quiet_threshold = herder.get('quiet_mode_threshold', 100)
    send_message(chat_id,
        f"⚙️ <b>Настройки Ботовода</b>\n"
        f"🎯 Стратегия по умолчанию: <b>{strategy}</b>\n"
        f"📊 Макс. действий/аккаунт: <b>{max_actions}</b>\n"
        f"🗣 Координация обсуждений: {coordinate}\n"
        f"🌙 Сезонное поведение: {seasonal}\n"
        f"🔇 Тихий режим (порог): <b>{quiet_threshold}</b> подписчиков",
        kb_herder_settings()
    )
def _handle_settings(chat_id: int, user_id: int, text: str, saved: dict) -> bool:
    """Handle settings"""
    if text == '🎯 Стратегия по умолчанию':
        send_message(chat_id, "Выберите стратегию:", kb_herder_strategy())
        saved['setting'] = 'default_strategy'
        DB.set_user_state(user_id, 'herder:settings', saved)
        return True
    # Handle strategy selection
    strategy_map = {
        '📖 Наблюдатель': 'observer',
        '🧠 Эксперт': 'expert',
        '💪 Поддержка': 'support',
        '🔥 Трендсеттер': 'trendsetter',
        '👥 Комьюнити': 'community'
    }
    if text in strategy_map and saved.get('setting') == 'default_strategy':
        settings = DB.get_user_settings(user_id)
        herder = settings.get('herder_settings', {})
        herder['default_strategy'] = strategy_map[text]
        DB.update_user_settings(user_id, herder_settings=herder)
        send_message(chat_id, f"✅ Стратегия изменена на {text}", kb_herder_settings())
        show_herder_settings(chat_id, user_id)
        return True
    return False
# ==================== CALLBACK HANDLER ====================
def handle_herder_callback(chat_id: int, msg_id: int, user_id: int,  str) -> bool:
    """Handle herder inline callbacks"""
    # Account selection for new assignment
    if data.startswith('hselacc:'):
        account_id = int(data.split(':')[1])
        state_data = DB.get_user_state(user_id)
        if not state_
            return True
        saved = state_data.get('data', {})
        selected = saved.get('selected_accounts', [])
        if account_id in selected:
            selected.remove(account_id)
        else:
            selected.append(account_id)
        saved['selected_accounts'] = selected
        DB.set_user_state(user_id, state_data.get('state', 'herder:new:accounts'), saved)
        # Update keyboard with accounts grouped by folders
        folders = DB.get_account_folders(user_id)
        accounts = DB.get_accounts_without_folder(user_id)
        all_accounts = []
        if folders:
            all_accounts.append({'type': 'header', 'text': '📁 Папки'})
            for folder in folders:
                accs_in_folder = DB.get_accounts_in_folder(folder['id'])
                for acc in accs_in_folder:
                    acc['profile'] = DB.get_account_profile(acc['id'])
                    all_accounts.append(acc)
        if accounts:
            all_accounts.append({'type': 'header', 'text': '📁 Без папки'})
            for acc in accounts:
                acc['profile'] = DB.get_account_profile(acc['id'])
                all_accounts.append(acc)
        edit_message(chat_id, msg_id,
            f"<b>Шаг 2/8:</b> Выберите аккаунты\n"
            f"Выбрано: {len(selected)}",
            kb_inline_herder_accounts([a for a in all_accounts if a.get('id')], selected)
        )
        return True
    if data == 'hselall':
        state_data = DB.get_user_state(user_id)
        saved = state_data.get('data', {}) if state_data else {}
        # Get all account IDs
        folders = DB.get_account_folders(user_id)
        accounts = DB.get_accounts_without_folder(user_id)
        all_ids = []
        for folder in folders:
            accs = DB.get_accounts_in_folder(folder['id'])
            all_ids.extend([a['id'] for a in accs])
        all_ids.extend([a['id'] for a in accounts])
        saved['selected_accounts'] = all_ids
        DB.set_user_state(user_id, state_data.get('state', 'herder:new:accounts') if state_data else 'herder:new:accounts', saved)
        # Update keyboard
        all_accounts = []
        if folders:
            all_accounts.append({'type': 'header', 'text': '📁 Папки'})
            for folder in folders:
                accs = DB.get_accounts_in_folder(folder['id'])
                for acc in accs:
                    acc['profile'] = DB.get_account_profile(acc['id'])
                    all_accounts.append(acc)
        if accounts:
            all_accounts.append({'type': 'header', 'text': '📁 Без папки'})
            for acc in accounts:
                acc['profile'] = DB.get_account_profile(acc['id'])
                all_accounts.append(acc)
        edit_message(chat_id, msg_id,
            f"<b>Шаг 2/8:</b> Выберите аккаунты\n"
            f"Выбрано: {len(all_ids)}",
            kb_inline_herder_accounts([a for a in all_accounts if a.get('id')], all_ids)
        )
        return True
    if data == 'hselclear':
        state_data = DB.get_user_state(user_id)
        saved = state_data.get('data', {}) if state_data else {}
        saved['selected_accounts'] = []
        DB.set_user_state(user_id, state_data.get('state', 'herder:new:accounts') if state_data else 'herder:new:accounts', saved)
        # Update keyboard
        folders = DB.get_account_folders(user_id)
        accounts = DB.get_accounts_without_folder(user_id)
        all_accounts = []
        if folders:
            all_accounts.append({'type': 'header', 'text': '📁 Папки'})
            for folder in folders:
                accs = DB.get_accounts_in_folder(folder['id'])
                for acc in accs:
                    acc['profile'] = DB.get_account_profile(acc['id'])
                    all_accounts.append(acc)
        if accounts:
            all_accounts.append({'type': 'header', 'text': '📁 Без папки'})
            for acc in accounts:
                acc['profile'] = DB.get_account_profile(acc['id'])
                all_accounts.append(acc)
        edit_message(chat_id, msg_id,
            f"<b>Шаг 2/8:</b> Выберите аккаунты\n"
            f"Выбрано: 0",
            kb_inline_herder_accounts([a for a in all_accounts if a.get('id')], [])
        )
        return True
    if data == 'hselnext':
        state_data = DB.get_user_state(user_id)
        saved = state_data.get('data', {}) if state_data else {}
        if not saved.get('selected_accounts'):
            answer_callback(data, "Выберите хотя бы один аккаунт")
            return True
        DB.set_user_state(user_id, 'herder:new:strategy', saved)
                _show_strategy_selection(chat_id, user_id, saved)
        return True

    # Assignment selection
    if data.startswith('hassign:'):
        assignment_id = int(data.split(':')[1])
        show_assignment_view(chat_id, user_id, assignment_id)
        return True

    # Profile selection
    if data.startswith('hprofile:'):
        account_id = int(data.split(':')[1])
        profile = DB.get_account_profile(account_id)
        if profile:
            persona = profile.get('persona', '—')
            role = profile.get('role', '—')
            interests = ', '.join(profile.get('interests', [])) or '—'
            style = profile.get('speech_style', '—')
            reactions = ' '.join(profile.get('preferred_reactions', [])) or '—'
            send_message(chat_id,
                f"🧠 <b>Профиль аккаунта</b>
"
                f"👤 Личность: {persona}
"
                f"🎭 Роль: {role}
"
                f"❤️ Интересы: {interests}
"
                f"💬 Стиль: {style}
"
                f"👍 Реакции: {reactions}",
                kb_herder_profile_actions()
            )
        else:
            send_message(chat_id, "❌ Профиль не найден", kb_herder_profiles_menu())
        return True

    # Strategy selection (in new assignment flow)
    if data.startswith('hstrategy:'):
        strategy = data.split(':')[1]
        state_data = DB.get_user_state(user_id)
        if not state_data or not state_data.get('state', '').startswith('herder:new:'):
            return True
        saved = state_data.get('data', {})
        saved['strategy'] = strategy
        saved['actions'] = ['read']
        DB.set_user_state(user_id, 'herder:new:actions', saved)
        _show_actions_constructor(chat_id, user_id, saved)
        return True

    return False


# ==================== HELPER KEYBOARDS ====================
def kb_confirm():
    """Confirm keyboard"""
    return reply_keyboard([
        ['✅ Подтвердить'],
        ['◀️ Назад', '❌ Отмена']
    ])


def kb_skip_2fa():
    """Skip 2FA keyboard"""
    return reply_keyboard([
        ['⏭ Пропустить'],
        ['◀️ Назад', '❌ Отмена']
    ])
