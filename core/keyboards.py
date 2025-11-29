"""
Keyboard builders - Reply keyboards (static menu) + Inline for lists
"""
from typing import List, Dict, Optional
from core.db import DB


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


# ==================== MAIN MENU ====================

def kb_main_menu():
    """Main menu keyboard"""
    return reply_keyboard([
        ['🔍 Парсинг чатов', '💬 Комментарии'],
        ['📊 Аудитории', '📄 Шаблоны'],
        ['👤 Аккаунты', '📤 Рассылка'],
        ['📈 Статистика', '⚙️ Настройки']
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

def kb_yes_no():
    """Yes/No buttons"""
    return reply_keyboard([
        ['✅ Да', '❌ Нет'],
        ['◀️ Назад']
    ])

def kb_confirm_delete():
    """Confirm delete buttons"""
    return reply_keyboard([
        ['🗑 Да, удалить', '❌ Отмена'],
        ['◀️ Назад']
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
        ['◀️ Главное меню']
    ])

def kb_account_actions():
    """Actions for selected account"""
    return reply_keyboard([
        ['📊 Установить лимит', '📁 Переместить'],
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


# ==================== MAILING KEYBOARDS ====================

def kb_mailing_menu():
    """Mailing menu"""
    return reply_keyboard([
        ['🚀 Новая рассылка'],
        ['📊 Активные', '📅 Отложенные'],
        ['◀️ Главное меню']
    ])

def kb_mailing_confirm():
    """Confirm mailing"""
    return reply_keyboard([
        ['🚀 Запустить сейчас', '📅 Отложить'],
        ['⚙️ Настройки рассылки'],
        ['❌ Отмена']
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


# ==================== STATS KEYBOARDS ====================

def kb_stats_menu():
    """Statistics menu"""
    return reply_keyboard([
        ['📉 Ошибки за 7 дней', '🏆 Топ аудиторий'],
        ['📊 Активные рассылки'],
        ['◀️ Главное меню']
    ])


# ==================== SETTINGS KEYBOARDS ====================

def kb_settings_menu():
    """Settings menu"""
    return reply_keyboard([
        ['🌙 Тихие часы', '🔔 Уведомления'],
        ['⏱ Задержка рассылки'],
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


# ==================== INLINE KEYBOARDS (for lists only) ====================

def inline_keyboard(buttons: List[List[dict]]) -> dict:
    """Create inline keyboard"""
    return {'inline_keyboard': buttons}

def kb_inline_audiences(sources: List[dict]) -> dict:
    """Inline keyboard for audience selection"""
    buttons = []
    for s in sources[:15]:
        emoji = '💬' if s.get('source_type') == 'comments' else '👥'
        status = {'pending': '⏳', 'running': '🔄', 'completed': '✅', 'failed': '❌'}.get(s.get('status'), '❓')
        link = s['source_link'][:20] + '..' if len(s['source_link']) > 20 else s['source_link']
        count = s.get('parsed_count', 0)
        buttons.append([{
            'text': f"{emoji}{status} {link} ({count})",
            'callback_data': f"aud:{s['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None

def kb_inline_templates(templates: List[dict], folders: List[dict] = None) -> dict:
    """Inline keyboard for template selection"""
    buttons = []
    # Folders first
    for f in (folders or [])[:5]:
        buttons.append([{
            'text': f"📁 {f['name']}",
            'callback_data': f"tfld:{f['id']}"
        }])
    # Templates without folder
    for t in templates[:10]:
        if not t.get('folder_id'):
            emoji = '🖼' if t.get('media_file_id') else '📝'
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
        emoji = '🖼' if t.get('media_file_id') else '📝'
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
    buttons = []
    # Folders
    for f in folders[:8]:
        count = DB.count_accounts_in_folder(f['id'])
        buttons.append([{
            'text': f"📁 {f['name']} ({count})",
            'callback_data': f"afld:{f['id']}"
        }])
    # Accounts without folder
    for a in accounts[:5]:
        status = {'active': '✅', 'pending': '⏳', 'blocked': '🚫', 'flood_wait': '⏰', 'error': '❌'}.get(a.get('status'), '❓')
        phone = a['phone']
        masked = f"{phone[:4]}**{phone[-2:]}" if len(phone) > 6 else phone
        daily = f"{a.get('daily_sent', 0) or 0}/{a.get('daily_limit', 50) or 50}"
        buttons.append([{
            'text': f"{status} {masked} [{daily}]",
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
        buttons.append([{
            'text': f"{status} {masked} [{daily}]",
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
    buttons = []
    for s in sources[:15]:
        emoji = '💬' if s.get('source_type') == 'comments' else '👥'
        link = s['source_link'][:20] + '..' if len(s['source_link']) > 20 else s['source_link']
        count = s.get('parsed_count', 0)
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
        emoji = '🖼' if t.get('media_file_id') else '📝'
        name = t['name'][:25] + '..' if len(t['name']) > 25 else t['name']
        buttons.append([{
            'text': f"{emoji} {name}",
            'callback_data': f"mtpl:{t['id']}"
        }])
    return inline_keyboard(buttons) if buttons else None

def kb_inline_mailing_acc_folders(folders: List[dict], accounts: List[dict]) -> dict:
    """Inline keyboard for mailing account folder selection"""
    buttons = []
    for f in folders[:8]:
        active = DB.count_active_accounts_in_folder(f['id'])
        if active > 0:
            buttons.append([{
                'text': f"📁 {f['name']} ({active} активных)",
                'callback_data': f"macc:{f['id']}"
            }])
    # Accounts without folder
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
        status_emoji = {'pending': '⏳', 'running': '🔄', 'paused': '⏸', 'completed': '✅'}.get(c['status'], '❓')
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
        buttons.append([
            {'text': f"🚫 {display}", 'callback_data': 'noop'},
            {'text': '✖️', 'callback_data': f"delbl:{b['id']}"}
        ])
    return inline_keyboard(buttons) if buttons else None
