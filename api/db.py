"""
Supabase Database Client - Extended Version
With Account Folders, Multi-Account Campaigns, Dynamic Reports
"""

import os
import logging
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DB:
    """Supabase REST API Client"""

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
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }

    @classmethod
    def _api_url(cls, table: str) -> str:
        url, _ = cls._get_config()
        return f"{url}/rest/v1/{table}"

    # ==================== БАЗОВЫЕ ОПЕРАЦИИ ====================

    @classmethod
    def _select(cls, table: str, columns: str = "*", filters: dict = None,
                order: str = None, limit: int = None, single: bool = False) -> Any:
        try:
            params = {'select': columns}
            if filters:
                for key, value in filters.items():
                    if value is None:
                        params[key] = 'is.null'
                    else:
                        params[key] = f'eq.{value}'
            if order:
                params['order'] = order
            if limit:
                params['limit'] = limit
            
            response = requests.get(cls._api_url(table), headers=cls._headers(), params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data[0] if single and data else (None if single else data)
        except Exception as e:
            logger.error(f"SELECT {table}: {e}")
            return None if single else []

    @classmethod
    def _insert(cls, table: str, data: dict) -> Optional[Dict]:
        try:
            response = requests.post(cls._api_url(table), headers=cls._headers(), json=data, timeout=10)
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
            response = requests.patch(cls._api_url(table), headers=cls._headers(), json=data, params=params, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"UPDATE {table}: {e}")
            return False

    @classmethod
    def _delete(cls, table: str, filters: dict) -> bool:
        try:
            params = {k: f'eq.{v}' for k, v in filters.items()}
            response = requests.delete(cls._api_url(table), headers=cls._headers(), params=params, timeout=10)
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
            response = requests.get(cls._api_url(table), headers=headers, params=params, timeout=10)
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
        if folder_id:
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
        return cls._update('message_templates', {'folder_id': folder_id}, {'id': template_id})

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
    def delete_template_folder(cls, folder_id: int) -> bool:
        cls._update('message_templates', {'folder_id': None}, {'folder_id': folder_id})
        return cls._delete('template_folders', {'id': folder_id})

    # ==================== ACCOUNT FOLDERS (UPDATED) ====================

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
        folder = cls.get_account_folder(folder_id)
        if not folder:
            return False
        user_id = folder['owner_id']
        try:
            params = {
                'folder_id': f'eq.{folder_id}',
                'owner_id': f'eq.{user_id}'
            }
            data = {'folder_id': None, 'updated_at': datetime.utcnow().isoformat()}
            response = requests.patch(
                cls._api_url('telegram_accounts'),
                headers=cls._headers(),
                json=data,
                params=params,
                timeout=10
            )
            if not response.ok:
                logger.warning(f"Failed to reset folder_id for accounts in folder {folder_id}")
        except Exception as e:
            logger.error(f"Error moving accounts out of folder {folder_id}: {e}")
        return cls._delete('account_folders', {'id': folder_id})

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
        return cls._select('telegram_accounts', filters={'owner_id': user_id, 'folder_id': None}, order='created_at.desc')

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
        cls._delete('parsed_audiences', {'source_id': source_id})
        return cls._delete('audience_sources', {'id': source_id})

    @classmethod
    def get_audience_stats(cls, source_id: int) -> Dict:
        total = cls._count('parsed_audiences', {'source_id': source_id})
        try:
            headers = cls._headers()
            headers['Prefer'] = 'count=exact'
            params = {'select': 'id', 'source_id': f'eq.{source_id}', 'sent': 'eq.true'}
            response = requests.get(cls._api_url('parsed_audiences'), headers=headers, params=params, timeout=10)
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
        try:
            params = {
                'select': '*', 'source_id': f'eq.{source_id}',
                'or': f'(username.ilike.%{query}%,first_name.ilike.%{query}%)',
                'limit': str(limit)
            }
            response = requests.get(cls._api_url('parsed_audiences'), headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception:
            return []

    @classmethod
    def get_audience_with_filters(cls, source_id: int, limit: int = 100) -> List[Dict]:
        return cls._select('parsed_audiences', filters={'source_id': source_id}, limit=limit)

    # ==================== BLACKLIST ====================

    @classmethod
    def get_blacklist(cls, user_id: int) -> List[Dict]:
        return cls._select('blacklist', filters={'owner_id': user_id}, order='created_at.desc')

    @classmethod
    def add_to_blacklist(cls, user_id: int, tg_user_id: int = None, username: str = None) -> Optional[Dict]:
        return cls._insert('blacklist', {
            'owner_id': user_id, 'tg_user_id': tg_user_id, 'username': username,
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def remove_from_blacklist(cls, blacklist_id: int) -> bool:
        return cls._delete('blacklist', {'id': blacklist_id})

    # ==================== CAMPAIGNS (UPDATED) ====================

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
        try:
            params = {
                'select': '*',
                'owner_id': f'eq.{user_id}',
                'status': 'in.(pending,running,paused)',
                'order': 'created_at.desc'
            }
            response = requests.get(cls._api_url('campaigns'), headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_active_campaigns error: {e}")
            return []

    @classmethod
    def update_campaign(cls, campaign_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        return cls._update('campaigns', kwargs, {'id': campaign_id})

    # ==================== SCHEDULED MAILINGS (UPDATED) ====================

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
    def delete_scheduled_mailing(cls, mailing_id: int) -> bool:
        return cls._delete('scheduled_mailings', {'id': mailing_id})

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

    @classmethod
    def get_error_stats(cls, user_id: int, days: int = 7) -> Dict:
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            params = {
                'select': 'error_type', 
                'owner_id': f'eq.{user_id}',
                'created_at': f'gte.{start_date}'
            }
            response = requests.get(cls._api_url('error_logs'), headers=cls._headers(), params=params, timeout=10)
            errors = response.json() if response.ok else []
            stats = {}
            for err in errors:
                t = err.get('error_type', 'unknown')
                stats[t] = stats.get(t, 0) + 1
            return stats
        except Exception:
            return {}