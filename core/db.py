"""
Supabase Database Client - Extended Version
With Account Folders, Multi-Account Campaigns, Dynamic Reports
Static Menu Support
"""

import os
import logging
import requests
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DB:
    """Supabase REST core Client"""

    _url: Optional[str] = None
    _key: Optional[str] = None

    @classmethod
    def _get_config(cls):
        if cls._url is None:
            cls._url = os.getenv('SUPABASE_URL')
            cls._key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        return cls._url, cls._key

    @classmethod
    def _headers(cls) -> dict:
        _, key = cls._get_config()
        return {
            'corekey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }

    @classmethod
    def _core_url(cls, table: str) -> str:
        url, _ = cls._get_config()
        return f"{url}/rest/v1/{table}"

    # ==================== БАЗОВЫЕ ОПЕРАЦИИ ====================

    @classmethod
    def _select(cls, table: str, columns: str = "*", filters: dict = None,
                order: str = None, limit: int = None, single: bool = False,
                raw_filters: dict = None) -> Any:
        try:
            params = {'select': columns}
            if filters:
                for key, value in filters.items():
                    if value is None:
                        params[key] = 'is.null'
                    else:
                        params[key] = f'eq.{value}'
            if raw_filters:
                params.update(raw_filters)
            if order:
                params['order'] = order
            if limit:
                params['limit'] = limit
            
            response = requests.get(cls._core_url(table), headers=cls._headers(), params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data[0] if single and data else (None if single else data)
        except Exception as e:
            logger.error(f"SELECT {table}: {e}")
            return None if single else []

    @classmethod
    def _insert(cls, table: str, data: dict) -> Optional[Dict]:
        try:
            response = requests.post(cls._core_url(table), headers=cls._headers(), json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"INSERT {table}: {e}")
            return None

    @classmethod
    def _update(cls, table: str, data: dict, filters: dict) -> bool:
        try:
            params = {}
            for k, v in filters.items():
                if v is None:
                    params[k] = 'is.null'
                else:
                    params[k] = f'eq.{v}'
            response = requests.patch(cls._core_url(table), headers=cls._headers(), json=data, params=params, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"UPDATE {table}: {e}")
            return False

    @classmethod
    def _delete(cls, table: str, filters: dict) -> bool:
        try:
            params = {k: f'eq.{v}' for k, v in filters.items()}
            response = requests.delete(cls._core_url(table), headers=cls._headers(), params=params, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"DELETE {table}: {e}")
            return False

    @classmethod
    def _count(cls, table: str, filters: dict = None) -> int:
        try:
            headers = cls._headers()
            headers['Prefer'] = 'count=exact'
            params = {'select': 'id'}
            if filters:
                for k, v in filters.items():
                    if v is None:
                        params[k] = 'is.null'
                    else:
                        params[k] = f'eq.{v}'
            response = requests.get(cls._core_url(table), headers=headers, params=params, timeout=10)
            content_range = response.headers.get('content-range', '*/0')
            return int(content_range.split('/')[-1])
        except Exception:
            return 0

    # ==================== USER STATES ====================

    @classmethod
    def get_user_state(cls, user_id: int) -> Optional[Dict]:
        return cls._select('user_states', filters={'user_id': user_id}, single=True)

    @classmethod
    def set_user_state(cls, user_id: int, state: str, data: dict = None) -> bool:
        try:
            cls._delete('user_states', {'user_id': user_id})
            result = cls._insert('user_states', {
                'user_id': user_id,
                'state': state,
                'data': data or {},
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            })
            return result is not None
        except Exception as e:
            logger.error(f"set_user_state error: {e}")
            return False

    @classmethod
    def clear_user_state(cls, user_id: int) -> bool:
        return cls._delete('user_states', {'user_id': user_id})

    # ==================== USER SETTINGS ====================

    @classmethod
    def get_user_settings(cls, user_id: int) -> Dict:
        settings = cls._select('user_settings', filters={'user_id': user_id}, single=True)
        return settings or {
            'user_id': user_id, 
            'quiet_hours_start': None, 
            'quiet_hours_end': None,
            'timezone': 'Europe/Moscow', 
            'daily_limit': 100,
            'notify_on_complete': True, 
            'notify_on_error': True,
            'delay_min': 30,
            'delay_max': 90
        }

    @classmethod
    def update_user_settings(cls, user_id: int, **kwargs) -> bool:
        existing = cls._select('user_settings', filters={'user_id': user_id}, single=True)
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        
        if existing:
            return cls._update('user_settings', kwargs, {'user_id': user_id})
        else:
            kwargs['user_id'] = user_id
            kwargs['created_at'] = datetime.utcnow().isoformat()
            return cls._insert('user_settings', kwargs) is not None

    # ==================== TEMPLATES ====================

    @classmethod
    def get_templates(cls, user_id: int, folder_id: int = None) -> List[Dict]:
        if folder_id is not None:
            return cls._select('message_templates', filters={'owner_id': user_id, 'folder_id': folder_id}, order='created_at.desc')
        return cls._select('message_templates', filters={'owner_id': user_id}, order='created_at.desc')

    @classmethod
    def get_template(cls, template_id: int) -> Optional[Dict]:
        t = cls._select('message_templates', filters={'id': template_id}, single=True)
        if t:
            t['user_id'] = t.get('owner_id')
        return t

    @classmethod
    def create_template(cls, user_id: int, name: str, text: str,
                       media_file_id: str = None, media_type: str = None, folder_id: int = None) -> Optional[Dict]:
        data = {
            'owner_id': user_id,
            'name': name,
            'text': text,
            'created_at': datetime.utcnow().isoformat()
        }
        if media_file_id:
            data['media_file_id'] = media_file_id
        if media_type:
            data['media_type'] = media_type
        if folder_id:
            data['folder_id'] = folder_id
        
        return cls._insert('message_templates', data)

    @classmethod
    def delete_template(cls, template_id: int) -> bool:
        return cls._delete('message_templates', {'id': template_id})

    @classmethod
    def copy_template(cls, template_id: int, user_id: int) -> Optional[Dict]:
        orig = cls.get_template(template_id)
        if not orig:
            return None
        return cls.create_template(
            user_id, 
            f"{orig['name']} (копия)", 
            orig.get('text', ''),
            orig.get('media_file_id'), 
            orig.get('media_type'), 
            orig.get('folder_id')
        )

    @classmethod
    def update_template_folder(cls, template_id: int, folder_id: int = None) -> bool:
        return cls._update('message_templates', {'folder_id': folder_id, 'updated_at': datetime.utcnow().isoformat()}, {'id': template_id})

    # ==================== TEMPLATE FOLDERS ====================

    @classmethod
    def get_template_folders(cls, user_id: int) -> List[Dict]:
        return cls._select('template_folders', filters={'owner_id': user_id}, order='name.asc')

    @classmethod
    def get_template_folder(cls, folder_id: int) -> Optional[Dict]:
        return cls._select('template_folders', filters={'id': folder_id}, single=True)

    @classmethod
    def create_template_folder(cls, user_id: int, name: str) -> Optional[Dict]:
        return cls._insert('template_folders', {
            'owner_id': user_id, 'name': name, 'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def rename_template_folder(cls, folder_id: int, name: str) -> bool:
        return cls._update('template_folders', {'name': name, 'updated_at': datetime.utcnow().isoformat()}, {'id': folder_id})

    @classmethod
    def delete_template_folder(cls, folder_id: int) -> bool:
        # Move templates to root first
        cls._update('message_templates', {'folder_id': None}, {'folder_id': folder_id})
        return cls._delete('template_folders', {'id': folder_id})

    # ==================== ACCOUNT FOLDERS ====================

    @classmethod
    def get_account_folders(cls, user_id: int) -> List[Dict]:
        return cls._select('account_folders', filters={'owner_id': user_id}, order='name.asc')

    @classmethod
    def get_account_folder(cls, folder_id: int) -> Optional[Dict]:
        return cls._select('account_folders', filters={'id': folder_id}, single=True)

    @classmethod
    def create_account_folder(cls, user_id: int, name: str) -> Optional[Dict]:
        return cls._insert('account_folders', {
            'owner_id': user_id, 
            'name': name, 
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def rename_account_folder(cls, folder_id: int, name: str) -> bool:
        return cls._update('account_folders', {'name': name, 'updated_at': datetime.utcnow().isoformat()}, {'id': folder_id})

    @classmethod
    def delete_account_folder(cls, folder_id: int) -> bool:
        # Move accounts to root first
        cls.move_accounts_from_folder(folder_id)
        return cls._delete('account_folders', {'id': folder_id})

    @classmethod
    def move_accounts_from_folder(cls, folder_id: int) -> bool:
        """Move all accounts from folder to root (no folder)"""
        try:
            params = {'folder_id': f'eq.{folder_id}'}
            data = {'folder_id': None, 'updated_at': datetime.utcnow().isoformat()}
            response = requests.patch(
                cls._core_url('telegram_accounts'),
                headers=cls._headers(),
                json=data,
                params=params,
                timeout=10
            )
            return response.ok
        except Exception as e:
            logger.error(f"move_accounts_from_folder error: {e}")
            return False

    @classmethod
    def count_accounts_in_folder(cls, folder_id: int) -> int:
        return cls._count('telegram_accounts', {'folder_id': folder_id})

    @classmethod
    def count_active_accounts_in_folder(cls, folder_id: int) -> int:
        return cls._count('telegram_accounts', {'folder_id': folder_id, 'status': 'active'})

    # ==================== ACCOUNTS ====================

    @classmethod
    def get_accounts(cls, user_id: int) -> List[Dict]:
        return cls._select('telegram_accounts', filters={'owner_id': user_id}, order='created_at.desc')

    @classmethod
    def get_accounts_in_folder(cls, folder_id: int) -> List[Dict]:
        return cls._select('telegram_accounts', filters={'folder_id': folder_id}, order='created_at.desc')

    @classmethod
    def get_accounts_without_folder(cls, user_id: int) -> List[Dict]:
        """Get accounts without folder (folder_id is NULL)"""
        try:
            params = {
                'select': '*',
                'owner_id': f'eq.{user_id}',
                'folder_id': 'is.null',
                'order': 'created_at.desc'
            }
            response = requests.get(cls._core_url('telegram_accounts'), headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_accounts_without_folder error: {e}")
            return []

    @classmethod
    def get_account(cls, account_id: int) -> Optional[Dict]:
        a = cls._select('telegram_accounts', filters={'id': account_id}, single=True)
        if a:
            a['user_id'] = a.get('owner_id')
        return a

    @classmethod
    def get_active_accounts(cls, user_id: int) -> List[Dict]:
        return cls._select('telegram_accounts', filters={'owner_id': user_id, 'status': 'active'}, order='daily_sent.asc')

    @classmethod
    def get_any_active_account(cls, user_id: int) -> Optional[Dict]:
        """Get any active account for user (for parsing, etc.)"""
        accounts = cls._select('telegram_accounts', 
                              filters={'owner_id': user_id, 'status': 'active'}, 
                              order='daily_sent.asc', 
                              limit=1)
        return accounts[0] if accounts else None

    @classmethod
    def check_account_exists(cls, user_id: int, phone: str) -> bool:
        return cls._count('telegram_accounts', {'owner_id': user_id, 'phone': phone}) > 0

    @classmethod
    def count_user_accounts(cls, user_id: int) -> int:
        return cls._count('telegram_accounts', {'owner_id': user_id})

    @classmethod
    def count_active_user_accounts(cls, user_id: int) -> int:
        return cls._count('telegram_accounts', {'owner_id': user_id, 'status': 'active'})

    @classmethod
    def update_account(cls, account_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        return cls._update('telegram_accounts', kwargs, {'id': account_id})

    @classmethod
    def delete_account(cls, account_id: int) -> bool:
        return cls._delete('telegram_accounts', {'id': account_id})

    # ==================== AUTH TASKS ====================

    @classmethod
    def create_auth_task(cls, user_id: int, phone: str, folder_id: int = None) -> Optional[Dict]:
        data = {
            'owner_id': user_id, 
            'phone': phone, 
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        }
        if folder_id:
            data['folder_id'] = folder_id
        return cls._insert('auth_tasks', data)

    @classmethod
    def update_auth_task(cls, task_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        return cls._update('auth_tasks', kwargs, {'id': task_id})

    @classmethod
    def get_auth_task(cls, task_id: int) -> Optional[Dict]:
        return cls._select('auth_tasks', filters={'id': task_id}, single=True)

    # ==================== AUDIENCE SOURCES ====================

    @classmethod
    def get_audience_sources(cls, user_id: int, status: str = None) -> List[Dict]:
        filters = {'owner_id': user_id}
        if status:
            filters['status'] = status
        return cls._select('audience_sources', filters=filters, order='created_at.desc')

    @classmethod
    def get_audience_source(cls, source_id: int) -> Optional[Dict]:
        s = cls._select('audience_sources', filters={'id': source_id}, single=True)
        if s:
            s['user_id'] = s.get('owner_id')
        return s

    @classmethod
    def create_audience_source(cls, user_id: int, source_type: str, source_link: str,
                               filters: Dict, tags: List[str] = None) -> Optional[Dict]:
        return cls._insert('audience_sources', {
            'owner_id': user_id, 'source_type': source_type, 'source_link': source_link,
            'filters': filters, 'tags': tags or [], 'status': 'pending', 'parsed_count': 0,
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def update_audience_source(cls, source_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        return cls._update('audience_sources', kwargs, {'id': source_id})

    @classmethod
    def delete_audience_source(cls, source_id: int) -> bool:
        # Delete related parsed users first
        cls._delete('parsed_audiences', {'source_id': source_id})
        return cls._delete('audience_sources', {'id': source_id})

    @classmethod
    def get_audience_stats(cls, source_id: int) -> Dict:
        total = cls._count('parsed_audiences', {'source_id': source_id})
        try:
            headers = cls._headers()
            headers['Prefer'] = 'count=exact'
            params = {'select': 'id', 'source_id': f'eq.{source_id}', 'sent': 'eq.true'}
            response = requests.get(cls._core_url('parsed_audiences'), headers=headers, params=params, timeout=10)
            sent = int(response.headers.get('content-range', '*/0').split('/')[-1])
        except Exception:
            sent = 0
        return {'total': total, 'sent': sent, 'remaining': total - sent}

    # ==================== AUDIENCE TAGS ====================

    @classmethod
    def get_audience_tags(cls, user_id: int) -> List[Dict]:
        return cls._select('audience_tags', filters={'owner_id': user_id}, order='name.asc')

    @classmethod
    def create_audience_tag(cls, user_id: int, name: str) -> Optional[Dict]:
        return cls._insert('audience_tags', {
            'owner_id': user_id, 'name': name, 'color': '#3B82F6',
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def delete_audience_tag(cls, tag_id: int) -> bool:
        return cls._delete('audience_tags', {'id': tag_id})

    @classmethod
    def add_tag_to_source(cls, source_id: int, tag_name: str) -> bool:
        source = cls.get_audience_source(source_id)
        if not source:
            return False
        tags = source.get('tags', []) or []
        if tag_name not in tags:
            tags.append(tag_name)
            return cls.update_audience_source(source_id, tags=tags)
        return True

    @classmethod
    def remove_tag_from_source(cls, source_id: int, tag_name: str) -> bool:
        source = cls.get_audience_source(source_id)
        if not source:
            return False
        tags = source.get('tags', []) or []
        if tag_name in tags:
            tags.remove(tag_name)
            return cls.update_audience_source(source_id, tags=tags)
        return True

    # ==================== PARSED AUDIENCES ====================

    @classmethod
    def search_in_audience(cls, source_id: int, query: str, limit: int = 20) -> List[Dict]:
        """Search users in audience by username or name"""
        try:
            params = {
                'select': '*', 
                'source_id': f'eq.{source_id}',
                'or': f'(username.ilike.%{query}%,first_name.ilike.%{query}%,last_name.ilike.%{query}%)',
                'limit': str(limit)
            }
            response = requests.get(cls._core_url('parsed_audiences'), headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"search_in_audience error: {e}")
            return []

    @classmethod
    def get_audience_with_filters(cls, source_id: int, limit: int = 1000, only_unsent: bool = False) -> List[Dict]:
        """Get audience users with optional filters"""
        try:
            params = {
                'select': '*',
                'source_id': f'eq.{source_id}',
                'order': 'created_at.asc',
                'limit': str(limit)
            }
            if only_unsent:
                params['sent'] = 'eq.false'
            
            response = requests.get(cls._core_url('parsed_audiences'), headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_audience_with_filters error: {e}")
            return []

    @classmethod
    def get_unsent_users(cls, source_id: int, limit: int = 50) -> List[Dict]:
        """Get unsent users from audience"""
        return cls.get_audience_with_filters(source_id, limit=limit, only_unsent=True)

    @classmethod
    def mark_user_sent(cls, user_id: int, success: bool = True, error: str = None) -> bool:
        """Mark user as sent"""
        data = {
            'sent': True,
            'sent_at': datetime.utcnow().isoformat(),
            'send_success': success
        }
        if error:
            data['send_error'] = error[:200]
        return cls._update('parsed_audiences', data, {'id': user_id})

    # ==================== BLACKLIST ====================

    @classmethod
    def get_blacklist(cls, user_id: int) -> List[Dict]:
        """Get blacklist as list of dicts"""
        return cls._select('blacklist', filters={'owner_id': user_id}, order='created_at.desc')

    @classmethod
    def get_blacklist_items(cls, user_id: int) -> List[Dict]:
        """Alias for get_blacklist - returns list of dicts"""
        return cls.get_blacklist(user_id)

    @classmethod
    def get_blacklist_set(cls, user_id: int) -> Set:
        """Get blacklist as set of user_ids and usernames"""
        items = cls.get_blacklist(user_id)
        result = set()
        for item in items:
            if item.get('tg_user_id'):
                result.add(item['tg_user_id'])
            if item.get('username'):
                result.add(item['username'].lower())
        return result

    @classmethod
    def add_to_blacklist(cls, user_id: int, tg_user_id: int = None, username: str = None) -> Optional[Dict]:
        return cls._insert('blacklist', {
            'owner_id': user_id, 'tg_user_id': tg_user_id, 'username': username,
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def remove_from_blacklist(cls, blacklist_id: int) -> bool:
        return cls._delete('blacklist', {'id': blacklist_id})

    # ==================== CAMPAIGNS ====================

    @classmethod
    def create_campaign(cls, user_id: int, source_id: int, template_id: int, 
                       account_ids: List[int] = None, account_folder_id: int = None,
                       settings: Dict = None) -> Optional[Dict]:
        stats = cls.get_audience_stats(source_id)
        return cls._insert('campaigns', {
            'owner_id': user_id, 
            'source_id': source_id, 
            'template_id': template_id,
            'account_ids': account_ids or [],
            'account_folder_id': account_folder_id,
            'current_account_id': account_ids[0] if account_ids else None,
            'next_account_index': 0,
            'status': 'pending', 
            'sent_count': 0, 
            'failed_count': 0,
            'total_count': stats['remaining'],
            'settings': settings or {},
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def get_campaigns(cls, user_id: int) -> List[Dict]:
        return cls._select('campaigns', filters={'owner_id': user_id}, order='created_at.desc')

    @classmethod
    def get_campaign(cls, campaign_id: int) -> Optional[Dict]:
        return cls._select('campaigns', filters={'id': campaign_id}, single=True)

    @classmethod
    def get_active_campaigns(cls, user_id: int) -> List[Dict]:
        """Get active campaigns (pending, running, paused)"""
        try:
            params = {
                'select': '*',
                'owner_id': f'eq.{user_id}',
                'status': 'in.(pending,running,paused)',
                'order': 'created_at.desc'
            }
            response = requests.get(cls._core_url('campaigns'), headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_active_campaigns error: {e}")
            return []

    @classmethod
    def get_pending_campaigns(cls, limit: int = 5) -> List[Dict]:
        """Get pending campaigns for processing"""
        return cls._select('campaigns', filters={'status': 'pending'}, order='created_at.asc', limit=limit)

    @classmethod
    def get_running_campaigns(cls) -> List[Dict]:
        """Get running campaigns"""
        return cls._select('campaigns', filters={'status': 'running'})

    @classmethod
    def get_paused_campaigns(cls) -> List[Dict]:
        """Get paused campaigns"""
        return cls._select('campaigns', filters={'status': 'paused'})

    @classmethod
    def update_campaign(cls, campaign_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        return cls._update('campaigns', kwargs, {'id': campaign_id})

    @classmethod
    def increment_campaign_stats(cls, campaign_id: int, sent: int = 0, failed: int = 0) -> bool:
        """Increment campaign sent/failed counters"""
        campaign = cls.get_campaign(campaign_id)
        if not campaign:
            return False
        
        return cls.update_campaign(
            campaign_id,
            sent_count=(campaign.get('sent_count', 0) or 0) + sent,
            failed_count=(campaign.get('failed_count', 0) or 0) + failed
        )

    @classmethod
    def switch_campaign_account(cls, campaign_id: int, new_account_id: int, next_index: int = 0) -> bool:
        """Switch campaign to a different account"""
        return cls.update_campaign(
            campaign_id,
            current_account_id=new_account_id,
            next_account_index=next_index
        )

    # ==================== SCHEDULED MAILINGS ====================

    @classmethod
    def create_scheduled_mailing(cls, user_id: int, source_id: int, template_id: int,
                                 account_folder_id: int = None, scheduled_at: datetime = None) -> Optional[Dict]:
        return cls._insert('scheduled_mailings', {
            'owner_id': user_id, 
            'source_id': source_id, 
            'template_id': template_id,
            'account_folder_id': account_folder_id,
            'scheduled_at': scheduled_at.isoformat() if scheduled_at else None, 
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def get_scheduled_mailings(cls, user_id: int) -> List[Dict]:
        return cls._select('scheduled_mailings', filters={'owner_id': user_id}, order='scheduled_at.asc')

    @classmethod
    def get_due_scheduled_mailings(cls) -> List[Dict]:
        """Get scheduled mailings that are due for execution"""
        try:
            now = datetime.utcnow().isoformat()
            params = {
                'select': '*',
                'status': 'eq.pending',
                'scheduled_at': f'lte.{now}',
                'order': 'scheduled_at.asc',
                'limit': '10'
            }
            response = requests.get(cls._core_url('scheduled_mailings'), headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_due_scheduled_mailings error: {e}")
            return []

    @classmethod
    def update_scheduled_mailing(cls, mailing_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        return cls._update('scheduled_mailings', kwargs, {'id': mailing_id})

    @classmethod
    def delete_scheduled_mailing(cls, mailing_id: int) -> bool:
        return cls._delete('scheduled_mailings', {'id': mailing_id})

    # ==================== SENT MESSAGES (for deduplication) ====================

    @classmethod
    def record_sent_message(cls, campaign_id: int, user_tg_id: int, 
                           account_id: int, status: str = 'sent', error: str = None) -> bool:
        """Record sent message for deduplication"""
        try:
            data = {
                'campaign_id': campaign_id,
                'user_tg_id': user_tg_id,
                'account_id': account_id,
                'status': status,
                'sent_at': datetime.utcnow().isoformat()
            }
            if error:
                data['error_message'] = error[:200]
            
            # Use upsert to handle duplicates
            headers = cls._headers()
            headers['Prefer'] = 'resolution=merge-duplicates,return=representation'
            response = requests.post(cls._core_url('sent_messages'), headers=headers, json=data, timeout=10)
            return response.ok
        except Exception as e:
            logger.error(f"record_sent_message error: {e}")
            return False

    @classmethod
    def get_sent_user_ids_for_campaign(cls, campaign_id: int) -> Set[int]:
        """Get user IDs already sent in this campaign"""
        try:
            params = {
                'select': 'user_tg_id',
                'campaign_id': f'eq.{campaign_id}'
            }
            response = requests.get(cls._core_url('sent_messages'), headers=cls._headers(), params=params, timeout=10)
            if response.ok:
                return {u['user_tg_id'] for u in response.json() if u.get('user_tg_id')}
            return set()
        except Exception as e:
            logger.error(f"get_sent_user_ids_for_campaign error: {e}")
            return set()

    # ==================== ERROR LOGS ====================

    @classmethod
    def log_error(cls, user_id: int, error_type: str, error_message: str,
                 campaign_id: int = None, account_id: int = None, context: Dict = None) -> bool:
        """Log error for tracking"""
        data = {
            'owner_id': user_id,
            'error_type': error_type,
            'error_message': error_message[:500] if error_message else None,
            'created_at': datetime.utcnow().isoformat()
        }
        if campaign_id:
            data['campaign_id'] = campaign_id
        if account_id:
            data['account_id'] = account_id
        if context:
            data['context'] = context
        
        return cls._insert('error_logs', data) is not None

    @classmethod
    def get_error_stats(cls, user_id: int, days: int = 7) -> Dict:
        """Get error statistics for user"""
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            params = {
                'select': 'error_type', 
                'owner_id': f'eq.{user_id}',
                'created_at': f'gte.{start_date}'
            }
            response = requests.get(cls._core_url('error_logs'), headers=cls._headers(), params=params, timeout=10)
            errors = response.json() if response.ok else []
            stats = {}
            for err in errors:
                t = err.get('error_type', 'unknown')
                stats[t] = stats.get(t, 0) + 1
            return stats
        except Exception:
            return {}

    # ==================== STATISTICS ====================

    @classmethod
    def get_user_stats(cls, user_id: int) -> Dict:
        sources = cls.get_audience_sources(user_id)
        templates = cls.get_templates(user_id)
        accounts = cls.get_accounts(user_id)
        campaigns = cls.get_campaigns(user_id)
        total_parsed = sum(s.get('parsed_count', 0) for s in sources)
        total_sent = sum(c.get('sent_count', 0) for c in campaigns)
        total_failed = sum(c.get('failed_count', 0) for c in campaigns)
        return {
            'audiences': len(sources),
            'audiences_completed': sum(1 for s in sources if s.get('status') == 'completed'),
            'templates': len(templates),
            'accounts': len(accounts),
            'accounts_active': sum(1 for a in accounts if a.get('status') == 'active'),
            'campaigns': len(campaigns),
            'total_parsed': total_parsed,
            'total_sent': total_sent,
            'total_failed': total_failed,
            'success_rate': round(total_sent / (total_sent + total_failed) * 100, 1) if (total_sent + total_failed) > 0 else 0
        }

    # ==================== FLOOD WAIT MANAGEMENT ====================

    @classmethod
    def set_account_flood_wait(cls, account_id: int, wait_seconds: int) -> bool:
        """Set account to flood_wait status with resume time"""
        flood_until = (datetime.utcnow() + timedelta(seconds=wait_seconds)).isoformat()
        return cls.update_account(
            account_id,
            status='flood_wait',
            flood_wait_until=flood_until,
            error_message=f'Flood wait: {wait_seconds}s'
        )

    @classmethod
    def get_accounts_ready_after_flood(cls) -> List[Dict]:
        """Get accounts whose flood_wait has expired"""
        try:
            now = datetime.utcnow().isoformat()
            params = {
                'select': '*',
                'status': 'eq.flood_wait',
                'flood_wait_until': f'lte.{now}'
            }
            response = requests.get(cls._core_url('telegram_accounts'), headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_accounts_ready_after_flood error: {e}")
            return []

    @classmethod
    def reactivate_account(cls, account_id: int) -> bool:
        """Reactivate account after flood_wait"""
        return cls.update_account(
            account_id,
            status='active',
            flood_wait_until=None,
            error_message=None
        )
