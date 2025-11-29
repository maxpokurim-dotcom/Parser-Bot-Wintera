# api/keyboards.py
"""
All keyboard builders
"""
from api.db import DB

# ==================== BASIC KEYBOARDS ====================
def kb_main():
    return {'inline_keyboard': [
        [{'text': '🔍 Парсинг чатов', 'callback_data': 'menu:parsing_chats'},
         {'text': '💬 Комментарии', 'callback_data': 'menu:parsing_comments'}],
        [{'text': '📊 Аудитории', 'callback_data': 'menu:audiences'},
         {'text': '📄 Шаблоны', 'callback_data': 'menu:templates'}],
        [{'text': '👤 Аккаунты', 'callback_data': 'menu:accounts'},
         {'text': '📤 Рассылка', 'callback_data': 'menu:mailing'}],
        [{'text': '📈 Статистика', 'callback_data': 'menu:stats'},
         {'text': '⚙️ Настройки', 'callback_data': 'menu:settings'}]
    ]}

def kb_cancel():
    return {'inline_keyboard': [[{'text': '❌ Отмена', 'callback_data': 'action:cancel'}]]}

def kb_back(cb: str):
    return {'inline_keyboard': [[{'text': '◀️ Назад', 'callback_data': cb}]]}

def kb_yes_no(prefix: str):
    return {'inline_keyboard': [
        [{'text': '✅ Да', 'callback_data': f'{prefix}:yes'}, {'text': '❌ Нет', 'callback_data': f'{prefix}:no'}],
        [{'text': '◀️ Отмена', 'callback_data': 'action:cancel'}]
    ]}

def kb_confirm(prefix: str):
    return {'inline_keyboard': [
        [{'text': '✅ Подтвердить', 'callback_data': f'{prefix}:confirm'},
         {'text': '❌ Отмена', 'callback_data': f'{prefix}:cancel'}]
    ]}

def kb_delete_confirm(prefix: str, item_id: int):
    return {'inline_keyboard': [
        [{'text': '🗑 Да, удалить', 'callback_data': f'{prefix}:confirm_delete:{item_id}'},
         {'text': '❌ Отмена', 'callback_data': f'{prefix}:cancel_delete'}]
    ]}

def kb_msg_limit():
    return {'inline_keyboard': [
        [{'text': '100', 'callback_data': 'parse_msg_limit:100'},
         {'text': '500', 'callback_data': 'parse_msg_limit:500'},
         {'text': '1000', 'callback_data': 'parse_msg_limit:1000'}],
        [{'text': '2000', 'callback_data': 'parse_msg_limit:2000'},
         {'text': '5000', 'callback_data': 'parse_msg_limit:5000'}],
        [{'text': '❌ Отмена', 'callback_data': 'action:cancel'}]
    ]}

# ==================== STATS KEYBOARDS ====================
def kb_stats():
    return {'inline_keyboard': [
        [{'text': '📉 Ошибки за 7 дней', 'callback_data': 'stats:errors'}],
        [{'text': '🏆 Топ аудиторий', 'callback_data': 'stats:top_audiences'}],
        [{'text': '📊 Активные рассылки', 'callback_data': 'stats:active_mailings'}],
        [{'text': '◀️ Главное меню', 'callback_data': 'menu:main'}]
    ]}

# ==================== AUDIENCE KEYBOARDS ====================
def kb_audiences_empty():
    return {'inline_keyboard': [
        [{'text': '🔍 Парсинг чатов', 'callback_data': 'menu:parsing_chats'}],
        [{'text': '💬 Парсинг комментариев', 'callback_data': 'menu:parsing_comments'}],
        [{'text': '◀️ Главное меню', 'callback_data': 'menu:main'}]
    ]}

def kb_audiences_list(sources: list):
    buttons = []
    for s in sources[:10]:
        emoji = '💬' if s.get('source_type') == 'comments' else '👥'
        st = {'pending': '⏳', 'running': '🔄', 'completed': '✅', 'failed': '❌'}.get(s.get('status'), '❓')
        link = s['source_link'][:15] + '..' if len(s['source_link']) > 15 else s['source_link']
        buttons.append([{'text': f"{emoji}{st} {link} ({s.get('parsed_count', 0)})", 'callback_data': f"audience:view:{s['id']}"}])
    buttons.append([{'text': '🏷 Теги', 'callback_data': 'menu:tags'}, {'text': '🚫 Blacklist', 'callback_data': 'menu:blacklist'}])
    buttons.append([{'text': '◀️ Главное меню', 'callback_data': 'menu:main'}])
    return {'inline_keyboard': buttons}

def kb_audience_actions(source_id: int, status: str):
    buttons = []
    if status == 'completed':
        buttons.append([{'text': '🔍 Поиск', 'callback_data': f'audience:search:{source_id}'},
                        {'text': '📤 Экспорт', 'callback_data': f'audience:export:{source_id}'}])
    buttons.append([{'text': '🏷 Теги', 'callback_data': f'audience:tags:{source_id}'}])
    buttons.append([{'text': '🗑 Удалить', 'callback_data': f'audience:delete:{source_id}'}])
    buttons.append([{'text': '◀️ К списку', 'callback_data': 'menu:audiences'}])
    return {'inline_keyboard': buttons}

def kb_tags_menu(tags: list):
    buttons = [[{'text': f"🏷 {t['name']}", 'callback_data': 'noop'}, {'text': '🗑', 'callback_data': f"tag:delete:{t['id']}"}] for t in tags[:10]]
    buttons.append([{'text': '➕ Создать тег', 'callback_data': 'tag:create'}])
    buttons.append([{'text': '◀️ Назад', 'callback_data': 'menu:audiences'}])
    return {'inline_keyboard': buttons}

def kb_tags_select(source_id: int, tags: list, current: list):
    buttons = [[{'text': f"{'✅' if t['name'] in current else '⬜️'} {t['name']}", 'callback_data': f"audience:toggle_tag:{source_id}:{t['name']}"}] for t in tags[:10]]
    buttons.append([{'text': '◀️ Назад', 'callback_data': f'audience:view:{source_id}'}])
    return {'inline_keyboard': buttons}

def kb_blacklist(bl: list):
    buttons = []
    for b in bl[:8]:
        d = f"@{b['username']}" if b.get('username') else str(b.get('tg_user_id', '?'))[:10]
        buttons.append([{'text': f"🚫 {d}", 'callback_data': 'noop'}, {'text': '✖️', 'callback_data': f"blacklist:remove:{b['id']}"}])
    buttons.append([{'text': '➕ Добавить', 'callback_data': 'blacklist:add'}])
    buttons.append([{'text': '◀️ Назад', 'callback_data': 'menu:audiences'}])
    return {'inline_keyboard': buttons}

# ==================== TEMPLATE KEYBOARDS ====================
def kb_template_folders_for_selection(user_id: int, mode: str, extra_data: dict = None):
    folders = DB.get_template_folders(user_id)
    buttons = []

    if mode == 'template_create':
        buttons.append([{'text': '📁 Без папки', 'callback_data': 'template_create:folder:0'}])
        for f in folders:
            buttons.append([{'text': f"📁 {f['name']}", 'callback_data': f"template_create:folder:{f['id']}"}])
        buttons.append([{'text': '❌ Отмена', 'callback_data': 'action:cancel'}])
    elif mode == 'template_move':
        template_id = extra_data.get('template_id') if extra_data else 0
        buttons.append([{'text': '📁 Без папки', 'callback_data': f'template_move:folder:{template_id}:0'}])
        for f in folders:
            buttons.append([{'text': f"📁 {f['name']}", 'callback_data': f"template_move:folder:{template_id}:{f['id']}"}])
        buttons.append([{'text': '◀️ Назад', 'callback_data': f'template:view:{template_id}'}])

    return {'inline_keyboard': buttons}

def kb_templates(templates: list, folders: list = None):
    buttons = []
    for f in (folders or [])[:5]:
        buttons.append([{'text': f"📁 {f['name']}", 'callback_data': f"folder:view:{f['id']}"}])
    for t in templates[:8]:
        if not t.get('folder_id'):
            e = '🖼' if t.get('media_file_id') else '📝'
            n = t['name'][:20] + '..' if len(t['name']) > 20 else t['name']
            buttons.append([{'text': f"{e} {n}", 'callback_data': f"template:view:{t['id']}"}])
    buttons.append([{'text': '➕ Шаблон', 'callback_data': 'template:create'}, {'text': '📁 Папка', 'callback_data': 'folder:create'}])
    buttons.append([{'text': '◀️ Главное меню', 'callback_data': 'menu:main'}])
    return {'inline_keyboard': buttons}

def kb_folder_templates(templates: list, folder_id: int):
    buttons = [[{'text': f"{'🖼' if t.get('media_file_id') else '📝'} {t['name'][:20]}", 'callback_data': f"template:view:{t['id']}"}] for t in templates[:10]]
    buttons.append([{'text': '➕ Шаблон', 'callback_data': f'folder:create_template:{folder_id}'}])
    buttons.append([{'text': '🗑 Удалить папку', 'callback_data': f'folder:delete:{folder_id}'}])
    buttons.append([{'text': '◀️ К списку', 'callback_data': 'template:list'}])
    return {'inline_keyboard': buttons}

def kb_template_actions(template_id: int):
    return {'inline_keyboard': [
        [{'text': '👁 Предпросмотр', 'callback_data': f'template:preview:{template_id}'}],
        [{'text': '📁 Переместить', 'callback_data': f'template:move:{template_id}'},
         {'text': '📋 Копировать', 'callback_data': f'template:copy:{template_id}'},
         {'text': '🗑 Удалить', 'callback_data': f'template:delete:{template_id}'}],
        [{'text': '◀️ К списку', 'callback_data': 'template:list'}]
    ]}

# ==================== ACCOUNT KEYBOARDS ====================
def kb_accounts_main(folders: list, accounts_without_folder: list):
    buttons = []

    for f in folders[:8]:
        acc_count = DB.count_accounts_in_folder(f['id'])
        buttons.append([{'text': f"📁 {f['name']} ({acc_count})", 'callback_data': f"acc_folder:view:{f['id']}"}])

    for a in accounts_without_folder[:5]:
        st = {'active': '✅', 'pending': '⏳', 'blocked': '🚫', 'flood_wait': '⏰', 'error': '❌'}.get(a.get('status'), '❓')
        p = a['phone']
        m = f"{p[:4]}**{p[-2:]}" if len(p) > 6 else p
        d = f"{a.get('daily_sent', 0) or 0}/{a.get('daily_limit', 50) or 50}"
        buttons.append([{'text': f"{st} {m} [{d}]", 'callback_data': f"account:view:{a['id']}"}])

    buttons.append([{'text': '➕ Аккаунт', 'callback_data': 'account:add'}, 
                    {'text': '📁 Папка', 'callback_data': 'acc_folder:create'}])
    buttons.append([{'text': '◀️ Главное меню', 'callback_data': 'menu:main'}])
    return {'inline_keyboard': buttons}

def kb_account_folder_view(accounts: list, folder_id: int):
    buttons = []
    for a in accounts[:10]:
        st = {'active': '✅', 'pending': '⏳', 'blocked': '🚫', 'flood_wait': '⏰', 'error': '❌'}.get(a.get('status'), '❓')
        p = a['phone']
        m = f"{p[:4]}**{p[-2:]}" if len(p) > 6 else p
        d = f"{a.get('daily_sent', 0) or 0}/{a.get('daily_limit', 50) or 50}"
        buttons.append([{'text': f"{st} {m} [{d}]", 'callback_data': f"account:view:{a['id']}"}])

    buttons.append([{'text': '➕ Добавить аккаунт', 'callback_data': f'account:add_to_folder:{folder_id}'}])
    buttons.append([{'text': '✏️ Переименовать', 'callback_data': f'acc_folder:rename:{folder_id}'},
                    {'text': '🗑 Удалить папку', 'callback_data': f'acc_folder:delete:{folder_id}'}])
    buttons.append([{'text': '◀️ К списку', 'callback_data': 'account:list'}])
    return {'inline_keyboard': buttons}

def kb_account_actions(account_id: int):
    return {'inline_keyboard': [
        [{'text': '📊 Установить лимит', 'callback_data': f'account:set_limit:{account_id}'}],
        [{'text': '📁 Переместить', 'callback_data': f'account:move:{account_id}'}],
        [{'text': '🗑 Удалить', 'callback_data': f'account:delete:{account_id}'}],
        [{'text': '◀️ К списку', 'callback_data': 'account:list'}]
    ]}

def kb_account_folder_select(user_id: int, account_id: int):
    folders = DB.get_account_folders(user_id)
    buttons = []

    buttons.append([{'text': '📁 Без папки', 'callback_data': f'account:set_folder:{account_id}:0'}])
    for f in folders:
        buttons.append([{'text': f"📁 {f['name']}", 'callback_data': f"account:set_folder:{account_id}:{f['id']}"}])

    buttons.append([{'text': '◀️ Назад', 'callback_data': f'account:view:{account_id}'}])
    return {'inline_keyboard': buttons}

def kb_account_limit(account_id: int):
    return {'inline_keyboard': [
        [{'text': '25', 'callback_data': f'account:limit:{account_id}:25'},
         {'text': '50', 'callback_data': f'account:limit:{account_id}:50'},
         {'text': '75', 'callback_data': f'account:limit:{account_id}:75'}],
        [{'text': '100', 'callback_data': f'account:limit:{account_id}:100'},
         {'text': '150', 'callback_data': f'account:limit:{account_id}:150'},
         {'text': '200', 'callback_data': f'account:limit:{account_id}:200'}],
        [{'text': '◀️ Назад', 'callback_data': f'account:view:{account_id}'}]
    ]}

# ==================== MAILING KEYBOARDS ====================
def kb_mailing():
    return {'inline_keyboard': [
        [{'text': '🚀 Новая рассылка', 'callback_data': 'mailing:new'}],
        [{'text': '📊 Активные рассылки', 'callback_data': 'mailing:active_list'}],
        [{'text': '📅 Отложенные', 'callback_data': 'mailing:scheduled_list'}],
        [{'text': '◀️ Главное меню', 'callback_data': 'menu:main'}]
    ]}

def kb_mailing_sources(sources: list):
    buttons = [[{'text': f"{'💬' if s.get('source_type') == 'comments' else '👥'} {s['source_link'][:18]} ({s.get('parsed_count', 0)})",
                 'callback_data': f"mailing:source:{s['id']}"}] for s in sources[:10]]
    buttons.append([{'text': '❌ Отмена', 'callback_data': 'mailing:cancel'}])
    return {'inline_keyboard': buttons}

def kb_mailing_templates(templates: list):
    buttons = [[{'text': f"{'🖼' if t.get('media_file_id') else '📝'} {t['name'][:22]}",
                 'callback_data': f"mailing:template:{t['id']}"}] for t in templates[:10]]
    buttons.append([{'text': '❌ Отмена', 'callback_data': 'mailing:cancel'}])
    return {'inline_keyboard': buttons}

def kb_mailing_account_folders(folders: list, accounts_without_folder: list):
    buttons = []

    for f in folders[:8]:
        active_count = DB.count_active_accounts_in_folder(f['id'])
        if active_count > 0:
            buttons.append([{'text': f"📁 {f['name']} ({active_count} активных)", 
                           'callback_data': f"mailing:acc_folder:{f['id']}"}])

    active_without = [a for a in accounts_without_folder if a.get('status') == 'active']
    if active_without:
        buttons.append([{'text': f"📁 Без папки ({len(active_without)} активных)", 
                        'callback_data': 'mailing:acc_folder:0'}])

    buttons.append([{'text': '❌ Отмена', 'callback_data': 'mailing:cancel'}])
    return {'inline_keyboard': buttons}

def kb_mailing_confirm_multi():
    return {'inline_keyboard': [
        [{'text': '🚀 Запустить', 'callback_data': 'mailing:start_now'}],
        [{'text': '📅 Отложить', 'callback_data': 'mailing:schedule'}],
        [{'text': '⚙️ Настройки рассылки', 'callback_data': 'mailing:settings'}],
        [{'text': '❌ Отмена', 'callback_data': 'mailing:cancel'}]
    ]}

def kb_mailing_settings():
    return {'inline_keyboard': [
        [{'text': '⏱ Задержка: случайная', 'callback_data': 'mailing:delay_type'}],
        [{'text': '🔄 Авто-переключение аккаунтов: ВКЛ', 'callback_data': 'mailing:auto_switch'}],
        [{'text': '◀️ Назад', 'callback_data': 'mailing:back_to_confirm'}]
    ]}

def kb_scheduled_list(mailings: list):
    buttons = [[{'text': f"📅 ID:{m['id']}", 'callback_data': 'noop'},
                {'text': '🗑', 'callback_data': f"scheduled:delete:{m['id']}"}]
               for m in mailings[:10] if m['status'] == 'pending']
    buttons.append([{'text': '◀️ Назад', 'callback_data': 'menu:mailing'}])
    return {'inline_keyboard': buttons}

def kb_active_mailings(campaigns: list):
    buttons = []
    for c in campaigns[:10]:
        if c['status'] in ['pending', 'running', 'paused']:
            status_emoji = {'pending': '⏳', 'running': '🔄', 'paused': '⏸'}.get(c['status'], '❓')
            buttons.append([
                {'text': f"{status_emoji} ID:{c['id']} ({c.get('sent_count', 0)}/{c.get('total_count', '?')})",
                 'callback_data': f"campaign:view:{c['id']}"}
            ])

    if not buttons:
        buttons.append([{'text': 'Нет активных рассылок', 'callback_data': 'noop'}])

    buttons.append([{'text': '◀️ Назад', 'callback_data': 'menu:mailing'}])
    return {'inline_keyboard': buttons}

def kb_campaign_actions(campaign_id: int, status: str):
    buttons = []

    if status == 'running':
        buttons.append([{'text': '⏸ Приостановить', 'callback_data': f'campaign:pause:{campaign_id}'}])
    elif status == 'paused':
        buttons.append([{'text': '▶️ Возобновить', 'callback_data': f'campaign:resume:{campaign_id}'}])

    if status in ['running', 'paused', 'pending']:
        buttons.append([{'text': '🛑 Остановить', 'callback_data': f'campaign:stop:{campaign_id}'}])

    buttons.append([{'text': '🔄 Обновить', 'callback_data': f'campaign:view:{campaign_id}'}])
    buttons.append([{'text': '◀️ К списку', 'callback_data': 'mailing:active_list'}])
    return {'inline_keyboard': buttons}

# ==================== SETTINGS KEYBOARDS ====================
def kb_settings():
    return {'inline_keyboard': [
        [{'text': '🌙 Тихие часы', 'callback_data': 'settings:quiet_hours'}],
        [{'text': '🔕 Отключить тихие часы', 'callback_data': 'settings:quiet_hours_off'}],
        [{'text': '⏱ Задержка рассылки', 'callback_data': 'settings:mailing_delay'}],
        [{'text': '🔔 Уведомления ВКЛ', 'callback_data': 'settings:notify:on'},
         {'text': '🔕 ВЫКЛ', 'callback_data': 'settings:notify:off'}],
        [{'text': '◀️ Главное меню', 'callback_data': 'menu:main'}]
    ]}

def kb_delay_settings():
    return {'inline_keyboard': [
        [{'text': '5-15 сек (быстро)', 'callback_data': 'settings:delay:5:15'}],
        [{'text': '15-45 сек (средне)', 'callback_data': 'settings:delay:15:45'}],
        [{'text': '30-90 сек (медленно)', 'callback_data': 'settings:delay:30:90'}],
        [{'text': '60-180 сек (безопасно)', 'callback_data': 'settings:delay:60:180'}],
        [{'text': '◀️ Назад', 'callback_data': 'menu:settings'}]
    ]}