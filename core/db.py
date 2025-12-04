"""
Supabase Database Client - Extended Version v3.0
With Herder (Botovod), Factory, Content Manager, Analytics
All times in Moscow timezone
"""

import os
import logging
import requests
import time
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ==================== TIMEZONE HELPERS ====================
# Встроены прямо в файл для избежания циклических импортов

try:
    import pytz
    MOSCOW_TZ = pytz.timezone('Europe/Moscow')
except ImportError:
    MOSCOW_TZ = None


def now_moscow() -> datetime:
    """Get current time in Moscow timezone"""
    if MOSCOW_TZ:
        return datetime.now(MOSCOW_TZ)
    return datetime.utcnow() + timedelta(hours=3)


def format_moscow(dt: datetime, fmt: str = '%d.%m.%Y %H:%M') -> str:
    """Format datetime in Moscow timezone"""
    if dt is None:
        return '-'
    try:
        if MOSCOW_TZ and dt.tzinfo is None:
            dt = MOSCOW_TZ.localize(dt)
        elif MOSCOW_TZ:
            dt = dt.astimezone(MOSCOW_TZ)
        return dt.strftime(fmt)
    except:
        return dt.strftime(fmt) if dt else '-'


def parse_datetime(dt_string: str) -> Optional[datetime]:
    """Parse ISO datetime string"""
    if not dt_string:
        return None
    try:
        dt_string = dt_string.replace('Z', '+00:00')
        dt = datetime.fromisoformat(dt_string)
        if MOSCOW_TZ:
            if dt.tzinfo is None:
                import pytz
                dt = pytz.UTC.localize(dt)
            dt = dt.astimezone(MOSCOW_TZ)
        return dt
    except Exception:
        return None


class DB:
    """Supabase REST API Client - Extended with Herder functionality"""

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
            
            # Log response for debugging
            logger.debug(f"INSERT {table} response: {result}")
            
            # Supabase returns data in different formats depending on the request
            # Check if result is a list or dict
            if isinstance(result, list):
                if len(result) > 0:
                    return result[0]
                else:
                    logger.warning(f"INSERT {table} returned empty list")
                    return None
            elif isinstance(result, dict):
                # Sometimes Supabase returns {'data': [...]} or just the object
                if 'data' in result:
                    data_list = result['data']
                    if isinstance(data_list, list) and len(data_list) > 0:
                        return data_list[0]
                    else:
                        logger.warning(f"INSERT {table} returned empty data array")
                        return None
                else:
                    # Direct object return
                    return result if result else None
            else:
                logger.warning(f"INSERT {table} returned unexpected format: {type(result)}")
                return None
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            status_code = 0
            try:
                if hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                    try:
                        error_detail = e.response.json()
                        # Log full error details
                        logger.error(f"INSERT {table} failed (HTTP {status_code}): {error_detail}")
                    except:
                        error_detail = e.response.text
                        logger.error(f"INSERT {table} failed (HTTP {status_code}): {error_detail}")
                else:
                    error_detail = str(e)
                    logger.error(f"INSERT {table} failed: {error_detail}")
            except Exception as parse_error:
                error_detail = str(e)
                logger.error(f"INSERT {table} failed: {error_detail}")
                logger.error(f"Error parsing error response: {parse_error}")
            
            logger.error(f"Data being inserted into {table}: {data}")
            return None
        except Exception as e:
            logger.error(f"INSERT {table}: {e}")
            logger.error(f"Data being inserted: {data}")
            import traceback
            logger.error(traceback.format_exc())
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
            params = {k: f'eq.{v}' for k, v in filters.items() if v is not None}
            for k, v in filters.items():
                if v is None:
                    params[k] = 'is.null'
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

    @classmethod
    def _upsert(cls, table: str, data: dict, conflict_columns: str = 'id') -> Optional[Dict]:
        """Insert or update on conflict"""
        try:
            headers = cls._headers()
            headers['Prefer'] = f'resolution=merge-duplicates,return=representation'
            response = requests.post(cls._api_url(table), headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"UPSERT {table}: {e}")
            return None

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
                'created_at': now_moscow().isoformat(),
                'updated_at': now_moscow().isoformat()
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
            'delay_max': 90,
            'mailing_cache_ttl': 30,
            'auto_blacklist_enabled': True,
            'warmup_before_mailing': False,
            'warmup_duration_minutes': 5,
            'use_smart_scheduling': True,
            'preferred_hours_start': 10,
            'preferred_hours_end': 22,
            'panic_stop_enabled': False,
            'risk_tolerance': 'medium',
            'learning_mode': True,
            'auto_recovery_mode': True,
            'gpt_temperature': 0.7,
            'yagpt_api_key': None,
            'yagpt_folder_id': None,
            'yandex_gpt_model': None,
            'onlinesim_api_key': None,
            'herder_settings': {
                'default_strategy': 'observer',
                'max_actions_per_account': 50,
                'coordinate_discussions': False,
                'seasonal_behavior': True,
                'quiet_mode_threshold': 100
            },
            'factory_settings': {
                'default_warmup_days': 5,
                'auto_proxy_assignment': True
            }
        }

    @classmethod
    def update_user_settings(cls, user_id: int, **kwargs) -> bool:
        existing = cls._select('user_settings', filters={'user_id': user_id}, single=True)
        kwargs['updated_at'] = now_moscow().isoformat()

        if existing:
            return cls._update('user_settings', kwargs, {'user_id': user_id})
        else:
            kwargs['user_id'] = user_id
            kwargs['created_at'] = now_moscow().isoformat()
            return cls._insert('user_settings', kwargs) is not None

    # ==================== SYSTEM STATUS (PANIC STOP) ====================

    @classmethod
    def get_system_status(cls, user_id: int) -> Dict:
        status = cls._select('system_status', filters={'owner_id': user_id}, single=True)
        return status or {
            'owner_id': user_id,
            'is_paused': False,
            'pause_reason': None,
            'paused_at': None,
            'auto_resume_at': None
        }

    @classmethod
    def set_panic_stop(cls, user_id: int, reason: str = 'Manual panic stop', 
                       auto_resume_minutes: int = None) -> bool:
        auto_resume = None
        if auto_resume_minutes:
            auto_resume = (now_moscow() + timedelta(minutes=auto_resume_minutes)).isoformat()
        
        data = {
            'owner_id': user_id,
            'is_paused': True,
            'pause_reason': reason,
            'paused_at': now_moscow().isoformat(),
            'auto_resume_at': auto_resume,
            'updated_at': now_moscow().isoformat()
        }
        
        existing = cls._select('system_status', filters={'owner_id': user_id}, single=True)
        if existing:
            return cls._update('system_status', data, {'owner_id': user_id})
        else:
            data['created_at'] = now_moscow().isoformat()
            return cls._insert('system_status', data) is not None

    @classmethod
    def clear_panic_stop(cls, user_id: int) -> bool:
        return cls._update('system_status', {
            'is_paused': False,
            'pause_reason': None,
            'paused_at': None,
            'auto_resume_at': None,
            'updated_at': now_moscow().isoformat()
        }, {'owner_id': user_id})

    @classmethod
    def is_system_paused(cls, user_id: int) -> bool:
        status = cls.get_system_status(user_id)
        if not status.get('is_paused'):
            return False
        
        auto_resume = status.get('auto_resume_at')
        if auto_resume:
            resume_time = parse_datetime(auto_resume)
            if resume_time and now_moscow() >= resume_time:
                cls.clear_panic_stop(user_id)
                return False
        
        return True

    # ==================== STOP TRIGGERS ====================

    @classmethod
    def get_stop_triggers(cls, user_id: int) -> List[Dict]:
        triggers = cls._select('stop_triggers', filters={'owner_id': user_id, 'is_active': True})
        if not triggers:
            cls._create_default_stop_triggers(user_id)
            triggers = cls._select('stop_triggers', filters={'owner_id': user_id, 'is_active': True})
        return triggers or []

    @classmethod
    def get_all_stop_triggers(cls, user_id: int) -> List[Dict]:
        """Получить все стоп-триггеры включая неактивные"""
        return cls._select('stop_triggers', filters={'owner_id': user_id}, order='created_at.desc')

    @classmethod
    def _create_default_stop_triggers(cls, user_id: int):
        default_words = [
            'стоп', 'stop', 'спам', 'spam', 'отписаться', 'unsubscribe',
            'не пиши', 'не надо', 'отстань', 'заблокирую', 'в бан',
            'пожалуюсь', 'жалоба', 'report', 'block', 'хватит',
            'надоел', 'достал', 'удали', 'убери'
        ]
        for word in default_words:
            cls._insert('stop_triggers', {
                'owner_id': user_id,
                'trigger_word': word,
                'action': 'blacklist',
                'is_active': True,
                'hits_count': 0,
                'created_at': now_moscow().isoformat()
            })

    @classmethod
    def add_stop_trigger(cls, user_id: int, trigger_word: str, action: str = 'blacklist') -> Optional[Dict]:
        return cls._insert('stop_triggers', {
            'owner_id': user_id,
            'trigger_word': trigger_word.lower().strip(),
            'action': action,
            'is_active': True,
            'hits_count': 0,
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def delete_stop_trigger(cls, trigger_id: int) -> bool:
        return cls._delete('stop_triggers', {'id': trigger_id})

    @classmethod
    def toggle_stop_trigger(cls, trigger_id: int) -> bool:
        trigger = cls._select('stop_triggers', filters={'id': trigger_id}, single=True)
        if trigger:
            return cls._update('stop_triggers', 
                {'is_active': not trigger.get('is_active', True)}, 
                {'id': trigger_id})
        return False

    @classmethod
    def increment_trigger_hits(cls, trigger_id: int) -> bool:
        trigger = cls._select('stop_triggers', filters={'id': trigger_id}, single=True)
        if trigger:
            return cls._update('stop_triggers', 
                {'hits_count': (trigger.get('hits_count', 0) or 0) + 1}, 
                {'id': trigger_id})
        return False

    # ==================== MAILING CACHE (TTL) ====================

    @classmethod
    def check_mailing_cache(cls, user_id: int, target_user_id: int, ttl_days: int = 30) -> bool:
        try:
            cutoff = (now_moscow() - timedelta(days=ttl_days)).isoformat()
            params = {
                'select': 'id',
                'owner_id': f'eq.{user_id}',
                'target_user_id': f'eq.{target_user_id}',
                'last_sent_at': f'gte.{cutoff}'
            }
            response = requests.get(cls._api_url('mailing_cache'), headers=cls._headers(), params=params, timeout=10)
            if response.ok:
                return len(response.json()) > 0
            return False
        except Exception as e:
            logger.error(f"check_mailing_cache error: {e}")
            return False

    @classmethod
    def add_to_mailing_cache(cls, user_id: int, target_user_id: int, 
                             target_username: str = None, campaign_id: int = None,
                             ttl_days: int = 30) -> bool:
        data = {
            'owner_id': user_id,
            'target_user_id': target_user_id,
            'target_username': target_username,
            'campaign_id': campaign_id,
            'ttl_days': ttl_days,
            'last_sent_at': now_moscow().isoformat()
        }
        return cls._upsert('mailing_cache', data) is not None

    @classmethod
    def cleanup_mailing_cache(cls, user_id: int = None) -> int:
        return 0

    # ==================== HOURLY STATS ====================

    @classmethod
    def update_hourly_stats(cls, user_id: int, sent: int = 0, success: int = 0, 
                           failed: int = 0, flood_waits: int = 0) -> bool:
        now = now_moscow()
        hour = now.hour
        day_of_week = now.weekday()
        
        existing = cls._select('hourly_stats', 
            filters={'owner_id': user_id, 'hour': hour, 'day_of_week': day_of_week}, 
            single=True)
        
        if existing:
            return cls._update('hourly_stats', {
                'total_sent': (existing.get('total_sent', 0) or 0) + sent,
                'total_success': (existing.get('total_success', 0) or 0) + success,
                'total_failed': (existing.get('total_failed', 0) or 0) + failed,
                'total_flood_waits': (existing.get('total_flood_waits', 0) or 0) + flood_waits,
                'last_updated': now.isoformat()
            }, {'id': existing['id']})
        else:
            return cls._insert('hourly_stats', {
                'owner_id': user_id,
                'hour': hour,
                'day_of_week': day_of_week,
                'total_sent': sent,
                'total_success': success,
                'total_failed': failed,
                'total_flood_waits': flood_waits,
                'last_updated': now.isoformat()
            }) is not None

    @classmethod
    def get_hourly_stats(cls, user_id: int) -> List[Dict]:
        return cls._select('hourly_stats', filters={'owner_id': user_id}, order='hour.asc')

    @classmethod
    def get_best_hours(cls, user_id: int, limit: int = 5) -> List[int]:
        stats = cls.get_hourly_stats(user_id)
        if not stats:
            return list(range(10, 22))
        
        sorted_stats = sorted(stats, key=lambda x: (
            x.get('total_success', 0) / max(x.get('total_sent', 1), 1)
        ), reverse=True)
        
        return [s['hour'] for s in sorted_stats[:limit]]

    @classmethod
    def get_delay_multiplier_for_hour(cls, user_id: int, hour: int = None) -> float:
        if hour is None:
            hour = now_moscow().hour
        
        stats = cls._select('hourly_stats', 
            filters={'owner_id': user_id, 'hour': hour}, 
            single=True)
        
        if not stats:
            return 1.0
        
        total = stats.get('total_sent', 0) or 1
        flood_waits = stats.get('total_flood_waits', 0) or 0
        
        flood_rate = flood_waits / total
        if flood_rate > 0.1:
            return 2.0
        elif flood_rate > 0.05:
            return 1.5
        elif flood_rate < 0.01:
            return 0.8
        
        return 1.0

    # ==================== SMART ACCOUNT DISTRIBUTION ====================

    @classmethod
    def get_best_account_for_mailing(cls, user_id: int, account_ids: List[int] = None,
                                     folder_id: int = None) -> Optional[Dict]:
        try:
            params = {
                'select': '*',
                'owner_id': f'eq.{user_id}',
                'status': 'eq.active',
                'order': 'reliability_score.desc,daily_sent.asc'
            }
            
            if folder_id:
                params['folder_id'] = f'eq.{folder_id}'
            
            response = requests.get(cls._api_url('telegram_accounts'), 
                                   headers=cls._headers(), params=params, timeout=10)
            
            if not response.ok:
                return None
            
            accounts = response.json()
            
            if account_ids:
                accounts = [a for a in accounts if a['id'] in account_ids]
            
            best_account = None
            best_score = -1
            
            for acc in accounts:
                daily_limit = acc.get('daily_limit', 50) or 50
                daily_sent = acc.get('daily_sent', 0) or 0
                remaining = daily_limit - daily_sent
                
                if remaining <= 0:
                    continue
                
                reliability = acc.get('reliability_score', 100) or 100
                consecutive_errors = acc.get('consecutive_errors', 0) or 0
                
                score = (remaining * reliability / 100) - (consecutive_errors * 10)
                
                if score > best_score:
                    best_score = score
                    best_account = acc
            
            return best_account
            
        except Exception as e:
            logger.error(f"get_best_account_for_mailing error: {e}")
            return None

    @classmethod
    def update_account_stats(cls, account_id: int, sent: int = 0, success: bool = True,
                            error_type: str = None, flood_wait_seconds: int = 0) -> bool:
        account = cls._select('telegram_accounts', filters={'id': account_id}, single=True)
        if not account:
            return False
        
        updates = {
            'daily_sent': (account.get('daily_sent', 0) or 0) + sent,
            'total_sent_today': (account.get('total_sent_today', 0) or 0) + sent,
            'updated_at': now_moscow().isoformat()
        }
        
        if success:
            updates['last_success_at'] = now_moscow().isoformat()
            updates['consecutive_errors'] = 0
            current_reliability = account.get('reliability_score', 100) or 100
            updates['reliability_score'] = min(100, current_reliability + 0.1)
        else:
            updates['last_error_at'] = now_moscow().isoformat()
            updates['consecutive_errors'] = (account.get('consecutive_errors', 0) or 0) + 1
            updates['total_errors_today'] = (account.get('total_errors_today', 0) or 0) + 1
            current_reliability = account.get('reliability_score', 100) or 100
            penalty = 5 if error_type == 'flood_wait' else 2
            updates['reliability_score'] = max(0, current_reliability - penalty)
        
        if flood_wait_seconds > 0:
            updates['status'] = 'flood_wait'
            updates['flood_wait_until'] = (now_moscow() + timedelta(seconds=flood_wait_seconds)).isoformat()
            updates['error_message'] = f'Flood wait: {flood_wait_seconds}s'
        
        return cls._update('telegram_accounts', updates, {'id': account_id})

    @classmethod
    def get_account_limit_prediction(cls, account_id: int) -> Dict:
        account = cls._select('telegram_accounts', filters={'id': account_id}, single=True)
        if not account:
            return {'error': 'Account not found'}
        
        daily_limit = account.get('daily_limit', 50) or 50
        daily_sent = account.get('daily_sent', 0) or 0
        remaining = max(0, daily_limit - daily_sent)
        
        week_ago = (now_moscow() - timedelta(days=7)).isoformat()
        history = cls._select('account_limits_history', 
            filters={'account_id': account_id},
            raw_filters={'date': f'gte.{week_ago[:10]}'},
            order='date.desc,hour.desc',
            limit=168)
        
        avg_hourly = 0
        if history:
            total_sent = sum(h.get('messages_sent', 0) for h in history)
            hours_with_activity = len([h for h in history if h.get('messages_sent', 0) > 0])
            if hours_with_activity > 0:
                avg_hourly = total_sent / hours_with_activity
        
        return {
            'account_id': account_id,
            'daily_limit': daily_limit,
            'daily_sent': daily_sent,
            'remaining_today': remaining,
            'reliability_score': account.get('reliability_score', 100),
            'avg_hourly_rate': round(avg_hourly, 1),
            'estimated_hours_left': round(remaining / max(avg_hourly, 1), 1) if avg_hourly > 0 else None,
            'status': account.get('status'),
            'recommendation': cls._get_account_recommendation(account, remaining, avg_hourly)
        }

    @classmethod
    def _get_account_recommendation(cls, account: Dict, remaining: int, avg_hourly: float) -> str:
        status = account.get('status')
        reliability = account.get('reliability_score', 100) or 100
        consecutive_errors = account.get('consecutive_errors', 0) or 0
        
        if status == 'flood_wait':
            return "⏳ Аккаунт временно ограничен. Дождитесь снятия flood wait."
        if remaining <= 0:
            return "🚫 Дневной лимит исчерпан. Продолжение завтра."
        if consecutive_errors >= 3:
            return "⚠️ Много ошибок подряд. Рекомендуется пауза 1-2 часа."
        if reliability < 50:
            return "📉 Низкая надёжность. Используйте другой аккаунт."
        if remaining < 10:
            return f"⚡ Осталось мало ({remaining}). Рекомендуется переключиться."
        return f"✅ Можно отправить ещё ~{remaining} сообщений."

    # ==================== SCHEDULED TASKS ====================

    @classmethod
    def create_scheduled_task(cls, user_id: int, task_type: str, task_config: Dict,
                             scheduled_at: datetime, repeat_mode: str = 'once',
                             repeat_days: List[int] = None) -> Optional[Dict]:
        return cls._insert('scheduled_tasks', {
            'owner_id': user_id,
            'task_type': task_type,
            'task_config': task_config,
            'scheduled_at': scheduled_at.isoformat(),
            'repeat_mode': repeat_mode,
            'repeat_days': repeat_days or [],
            'status': 'pending',
            'next_run_at': scheduled_at.isoformat(),
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_scheduled_tasks(cls, user_id: int, status: str = None) -> List[Dict]:
        filters = {'owner_id': user_id}
        if status:
            filters['status'] = status
        return cls._select('scheduled_tasks', filters=filters, order='scheduled_at.asc')

    @classmethod
    def get_due_scheduled_tasks(cls) -> List[Dict]:
        try:
            now = now_moscow().isoformat()
            params = {
                'select': '*',
                'status': 'eq.pending',
                'next_run_at': f'lte.{now}',
                'order': 'next_run_at.asc',
                'limit': '20'
            }
            response = requests.get(cls._api_url('scheduled_tasks'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_due_scheduled_tasks error: {e}")
            return []

    @classmethod
    def update_scheduled_task(cls, task_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('scheduled_tasks', kwargs, {'id': task_id})

    @classmethod
    def delete_scheduled_task(cls, task_id: int) -> bool:
        return cls._delete('scheduled_tasks', {'id': task_id})

    # ==================== WARMUP ACTIVITIES ====================

    @classmethod
    def create_warmup_activity(cls, account_id: int, activity_type: str, 
                               target_chat: str = None) -> Optional[Dict]:
        return cls._insert('warmup_activities', {
            'account_id': account_id,
            'activity_type': activity_type,
            'target_chat': target_chat,
            'status': 'pending',
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_pending_warmup_activities(cls, account_id: int) -> List[Dict]:
        return cls._select('warmup_activities', 
            filters={'account_id': account_id, 'status': 'pending'},
            order='created_at.asc')

    @classmethod
    def update_warmup_activity(cls, activity_id: int, status: str, error: str = None) -> bool:
        data = {
            'status': status,
            'executed_at': now_moscow().isoformat()
        }
        if error:
            data['error'] = error
        return cls._update('warmup_activities', data, {'id': activity_id})

    @classmethod
    def mark_account_warmup_complete(cls, account_id: int) -> bool:
        return cls._update('telegram_accounts', {
            'warmup_completed': True,
            'is_warming_up': False,
            'warmup_status': 'completed',
            'updated_at': now_moscow().isoformat()
        }, {'id': account_id})

    @classmethod
    def start_account_warmup(cls, account_id: int) -> bool:
        return cls._update('telegram_accounts', {
            'is_warming_up': True,
            'warmup_status': 'in_progress',
            'warmup_started_at': now_moscow().isoformat(),
            'updated_at': now_moscow().isoformat()
        }, {'id': account_id})

    # ==================== USER RESPONSES ====================

    @classmethod
    def record_user_response(cls, user_id: int, campaign_id: int, from_user_id: int,
                            from_username: str, message_text: str, 
                            is_negative: bool = False, trigger_matched: str = None,
                            action_taken: str = None) -> Optional[Dict]:
        return cls._insert('user_responses', {
            'owner_id': user_id,
            'campaign_id': campaign_id,
            'from_user_id': from_user_id,
            'from_username': from_username,
            'message_text': message_text[:1000] if message_text else None,
            'is_negative': is_negative,
            'trigger_matched': trigger_matched,
            'action_taken': action_taken,
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_negative_responses(cls, user_id: int, days: int = 7) -> List[Dict]:
        try:
            start_date = (now_moscow() - timedelta(days=days)).isoformat()
            params = {
                'select': '*',
                'owner_id': f'eq.{user_id}',
                'is_negative': 'eq.true',
                'created_at': f'gte.{start_date}',
                'order': 'created_at.desc'
            }
            response = requests.get(cls._api_url('user_responses'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_negative_responses error: {e}")
            return []

    # ==================== БОТОВОД: МОНИТОРИНГ КАНАЛОВ ====================

    @classmethod
    def create_monitored_channel(cls, user_id: int, channel_username: str,
                                  title: str = None, topic: str = None,
                                  priority: int = 3) -> Optional[Dict]:
        username = channel_username.lower().replace('@', '').replace('https://t.me/', '')
        return cls._insert('monitored_channels', {
            'owner_id': user_id,
            'channel_username': username,
            'title': title,
            'topic': topic,
            'priority': priority,
            'is_active': True,
            'total_actions': 0,
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_monitored_channels(cls, user_id: int, active_only: bool = True) -> List[Dict]:
        filters = {'owner_id': user_id}
        if active_only:
            filters['is_active'] = True
        return cls._select('monitored_channels', filters=filters, order='priority.desc,created_at.desc')

    @classmethod
    def get_monitored_channel(cls, channel_id: int) -> Optional[Dict]:
        return cls._select('monitored_channels', filters={'id': channel_id}, single=True)

    @classmethod
    def get_monitored_channel_by_username(cls, user_id: int, username: str) -> Optional[Dict]:
        username = username.lower().replace('@', '').replace('https://t.me/', '')
        return cls._select('monitored_channels', 
            filters={'owner_id': user_id, 'channel_username': username}, single=True)

    @classmethod
    def update_monitored_channel(cls, channel_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('monitored_channels', kwargs, {'id': channel_id})

    @classmethod
    def delete_monitored_channel(cls, channel_id: int) -> bool:
        cls._delete('herder_assignments', {'channel_id': channel_id})
        cls._delete('herder_logs', {'channel_id': channel_id})
        return cls._delete('monitored_channels', {'id': channel_id})

    @classmethod
    def count_monitored_channels(cls, user_id: int) -> int:
        return cls._count('monitored_channels', {'owner_id': user_id, 'is_active': True})

    # ==================== БОТОВОД: ЗАДАНИЯ ====================

    @classmethod
    def create_herder_assignment(cls, user_id: int, channel_id: int,
                                  account_ids: List[int], action_chain: List[dict],
                                  strategy: str = 'observer',
                                  settings: dict = None) -> Optional[Dict]:
        return cls._insert('herder_assignments', {
            'owner_id': user_id,
            'channel_id': channel_id,
            'account_ids': account_ids,
            'action_chain': action_chain,
            'strategy': strategy,
            'settings': settings or {
                'max_comments_per_day': 2,
                'delay_after_post': [300, 10800],
                'min_engagement_for_comment': 0.6,
                'coordinate_discussions': False,
                'seasonal_behavior': True
            },
            'status': 'active',
            'total_actions': 0,
            'total_comments': 0,
            'deleted_comments': 0,
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_herder_assignments(cls, user_id: int, status: str = None) -> List[Dict]:
        filters = {'owner_id': user_id}
        if status:
            filters['status'] = status
        return cls._select('herder_assignments', filters=filters, order='created_at.desc')

    @classmethod
    def get_herder_assignment(cls, assignment_id: int) -> Optional[Dict]:
        return cls._select('herder_assignments', filters={'id': assignment_id}, single=True)

    @classmethod
    def get_active_herder_assignments(cls) -> List[Dict]:
        return cls._select('herder_assignments', filters={'status': 'active'})

    @classmethod
    def get_herder_assignments_for_channel(cls, channel_id: int) -> List[Dict]:
        return cls._select('herder_assignments', filters={'channel_id': channel_id})

    @classmethod
    def update_herder_assignment(cls, assignment_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('herder_assignments', kwargs, {'id': assignment_id})

    @classmethod
    def pause_herder_assignment(cls, assignment_id: int, until: datetime = None) -> bool:
        data = {
            'status': 'paused',
            'updated_at': now_moscow().isoformat()
        }
        if until:
            data['paused_until'] = until.isoformat()
        return cls._update('herder_assignments', data, {'id': assignment_id})

    @classmethod
    def resume_herder_assignment(cls, assignment_id: int) -> bool:
        return cls._update('herder_assignments', {
            'status': 'active',
            'paused_until': None,
            'updated_at': now_moscow().isoformat()
        }, {'id': assignment_id})

    @classmethod
    def stop_herder_assignment(cls, assignment_id: int) -> bool:
        return cls._update('herder_assignments', {
            'status': 'stopped',
            'updated_at': now_moscow().isoformat()
        }, {'id': assignment_id})

    @classmethod
    def delete_herder_assignment(cls, assignment_id: int) -> bool:
        cls._delete('herder_logs', {'assignment_id': assignment_id})
        return cls._delete('herder_assignments', {'id': assignment_id})

    @classmethod
    def increment_herder_stats(cls, assignment_id: int, actions: int = 0, 
                                comments: int = 0, deleted: int = 0) -> bool:
        assignment = cls.get_herder_assignment(assignment_id)
        if not assignment:
            return False
        return cls._update('herder_assignments', {
            'total_actions': (assignment.get('total_actions', 0) or 0) + actions,
            'total_comments': (assignment.get('total_comments', 0) or 0) + comments,
            'deleted_comments': (assignment.get('deleted_comments', 0) or 0) + deleted,
            'updated_at': now_moscow().isoformat()
        }, {'id': assignment_id})

    @classmethod
    def count_herder_assignments(cls, user_id: int, status: str = None) -> int:
        filters = {'owner_id': user_id}
        if status:
            filters['status'] = status
        return cls._count('herder_assignments', filters)

    # ==================== БОТОВОД: ЛОГИ ====================

    @classmethod
    def log_herder_action(cls, owner_id: int, assignment_id: int, account_id: int,
                          channel_id: int, post_id: int, action_type: str,
                          action_data: dict = None, status: str = 'success',
                          error_message: str = None,
                          engagement_score: float = None,
                          emotion_analysis: dict = None) -> Optional[Dict]:
        return cls._insert('herder_logs', {
            'owner_id': owner_id,
            'assignment_id': assignment_id,
            'account_id': account_id,
            'channel_id': channel_id,
            'post_id': post_id,
            'action_type': action_type,
            'action_data': action_data,
            'status': status,
            'error_message': error_message,
            'engagement_score': engagement_score,
            'emotion_analysis': emotion_analysis,
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_herder_logs(cls, user_id: int, limit: int = 100, 
                        assignment_id: int = None, action_type: str = None) -> List[Dict]:
        filters = {'owner_id': user_id}
        if assignment_id:
            filters['assignment_id'] = assignment_id
        if action_type:
            filters['action_type'] = action_type
        return cls._select('herder_logs', filters=filters, order='created_at.desc', limit=limit)

    @classmethod
    def get_herder_logs_for_account(cls, account_id: int, action_type: str = None,
                                     date: str = None) -> List[Dict]:
        filters = {'account_id': account_id}
        if action_type:
            filters['action_type'] = action_type
        raw_filters = {}
        if date:
            raw_filters['created_at'] = f'gte.{date}T00:00:00'
        return cls._select('herder_logs', filters=filters, raw_filters=raw_filters)

    @classmethod
    def count_today_comments(cls, account_id: int) -> int:
        today = now_moscow().strftime('%Y-%m-%d')
        logs = cls.get_herder_logs_for_account(account_id, action_type='comment', date=today)
        return len([l for l in logs if l.get('status') == 'success'])

    @classmethod
    def get_herder_stats(cls, user_id: int, days: int = 7) -> Dict:
        start_date = (now_moscow() - timedelta(days=days)).isoformat()
        
        logs = cls._select('herder_logs',
            filters={'owner_id': user_id},
            raw_filters={'created_at': f'gte.{start_date}'})
        
        total_actions = len(logs)
        comments = [l for l in logs if l.get('action_type') == 'comment']
        deleted = [l for l in logs if l.get('status') == 'deleted']
        success = [l for l in logs if l.get('status') == 'success']
        
        by_type = {}
        for log in logs:
            t = log.get('action_type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            'total_actions': total_actions,
            'total_comments': len(comments),
            'deleted_comments': len(deleted),
            'success_count': len(success),
            'success_rate': round(len(success) / total_actions * 100, 1) if total_actions > 0 else 0,
            'by_type': by_type,
            'period_days': days
        }

    # ==================== БОТОВОД: БАЗА ЗНАНИЙ ====================

    @classmethod
    def add_herder_knowledge(cls, user_id: int, knowledge_type: str,
                              value: str, metadata: dict = None) -> Optional[Dict]:
        existing = cls._select('herder_knowledge',
            filters={'owner_id': user_id, 'type': knowledge_type, 'value': value},
            single=True)
        
        if existing:
            cls._update('herder_knowledge', {
                'hits_count': (existing.get('hits_count', 0) or 0) + 1,
                'last_hit_at': now_moscow().isoformat()
            }, {'id': existing['id']})
            return existing
        
        return cls._insert('herder_knowledge', {
            'owner_id': user_id,
            'type': knowledge_type,
            'value': value,
            'metadata': metadata or {},
            'hits_count': 1,
            'is_active': True,
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_bad_phrases(cls, user_id: int) -> List[str]:
        items = cls._select('herder_knowledge', 
            filters={'owner_id': user_id, 'type': 'bad_phrase', 'is_active': True})
        return [item['value'] for item in items]

    @classmethod
    def get_herder_knowledge(cls, user_id: int, knowledge_type: str = None) -> List[Dict]:
        filters = {'owner_id': user_id, 'is_active': True}
        if knowledge_type:
            filters['type'] = knowledge_type
        return cls._select('herder_knowledge', filters=filters, order='hits_count.desc')

    @classmethod
    def get_herder_knowledge_stats(cls, user_id: int) -> Dict:
        knowledge = cls._select('herder_knowledge', filters={'owner_id': user_id, 'is_active': True})
        
        stats = {
            'bad_phrases': 0,
            'good_patterns': 0,
            'risky_channels': 0,
            'effective_times': 0,
            'total': len(knowledge)
        }
        
        for item in knowledge:
            t = item.get('type', '')
            if t == 'bad_phrase':
                stats['bad_phrases'] += 1
            elif t == 'good_pattern':
                stats['good_patterns'] += 1
            elif t == 'risky_channel':
                stats['risky_channels'] += 1
            elif t == 'effective_time':
                stats['effective_times'] += 1
        
        return stats

    @classmethod
    def delete_herder_knowledge(cls, knowledge_id: int) -> bool:
        return cls._delete('herder_knowledge', {'id': knowledge_id})

    @classmethod
    def clear_herder_knowledge(cls, user_id: int, knowledge_type: str = None) -> bool:
        filters = {'owner_id': user_id}
        if knowledge_type:
            filters['type'] = knowledge_type
        return cls._delete('herder_knowledge', filters)

    # ==================== БОТОВОД: ПРОФИЛИ АККАУНТОВ ====================

    @classmethod
    def create_account_profile(cls, account_id: int, profile_data: dict) -> Optional[Dict]:
        existing = cls._select('account_profiles', filters={'account_id': account_id}, single=True)
        if existing:
            cls.update_account_profile(account_id, **profile_data)
            return cls._select('account_profiles', filters={'account_id': account_id}, single=True)
        
        return cls._insert('account_profiles', {
            'account_id': account_id,
            'persona': profile_data.get('persona'),
            'role': profile_data.get('role', 'observer'),
            'interests': profile_data.get('interests', []),
            'speech_style': profile_data.get('speech_style', 'informal'),
            'personality_vector': profile_data.get('personality_vector', {
                'friendliness': 0.7,
                'expertise': 0.5,
                'irony': 0.2
            }),
            'preferred_reactions': profile_data.get('preferred_reactions', ['👍']),
            'activity_schedule': profile_data.get('activity_schedule', {
                'weekday': [10, 19],
                'weekend': [12, 18]
            }),
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_account_profile(cls, account_id: int) -> Optional[Dict]:
        return cls._select('account_profiles', filters={'account_id': account_id}, single=True)

    @classmethod
    def update_account_profile(cls, account_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('account_profiles', kwargs, {'account_id': account_id})

    @classmethod
    def delete_account_profile(cls, account_id: int) -> bool:
        return cls._delete('account_profiles', {'account_id': account_id})

    @classmethod
    def get_accounts_by_role(cls, user_id: int, role: str) -> List[Dict]:
        accounts = cls._select('telegram_accounts', 
            filters={'owner_id': user_id, 'status': 'active'})
        
        result = []
        for acc in accounts:
            profile = cls.get_account_profile(acc['id'])
            if profile and profile.get('role') == role:
                acc['profile'] = profile
                result.append(acc)
        
        return result

    @classmethod
    def get_all_account_profiles(cls, user_id: int) -> List[Dict]:
        accounts = cls._select('telegram_accounts', filters={'owner_id': user_id})
        result = []
        for acc in accounts:
            profile = cls.get_account_profile(acc['id'])
            result.append({
                'account': acc,
                'profile': profile
            })
        return result

    # ==================== БОТОВОД: СТРАТЕГИИ ====================

    @classmethod
    def get_herder_strategies(cls) -> List[Dict]:
        """Получить доступные стратегии"""
        return [
            {
                'id': 'observer',
                'name': '📖 Наблюдатель',
                'description': 'Только чтение и редкие реакции',
                'max_daily_actions': 10,
                'can_comment': False,
                'actions': ['read', 'react']
            },
            {
                'id': 'expert',
                'name': '🧠 Эксперт',
                'description': 'Вопросы, уточнения, экспертные комментарии',
                'max_daily_actions': 25,
                'can_comment': True,
                'actions': ['read', 'react', 'comment', 'save']
            },
            {
                'id': 'support',
                'name': '💪 Поддержка',
                'description': 'Лайки комментариев, короткие согласия',
                'max_daily_actions': 20,
                'can_comment': True,
                'comment_style': 'short_agreement',
                'actions': ['read', 'react', 'comment']
            },
            {
                'id': 'trendsetter',
                'name': '🔥 Трендсеттер',
                'description': 'Первые реакции на важные посты',
                'max_daily_actions': 15,
                'can_comment': True,
                'priority': 'first_reaction',
                'actions': ['read', 'react', 'comment']
            },
            {
                'id': 'community',
                'name': '👥 Комьюнити',
                'description': 'Координированные обсуждения',
                'max_daily_actions': 30,
                'can_comment': True,
                'coordinate': True,
                'actions': ['read', 'react', 'comment', 'reply', 'save']
            }
        ]

    @classmethod
    def get_strategy_by_id(cls, strategy_id: str) -> Optional[Dict]:
        strategies = cls.get_herder_strategies()
        for s in strategies:
            if s['id'] == strategy_id:
                return s
        return None

    # ==================== ФАБРИКА АККАУНТОВ ====================

    @classmethod
    def create_factory_task(cls, user_id: int, count: int, country: str = 'ru',
                            auto_warmup: bool = True, warmup_days: int = 5,
                            role_distribution: dict = None) -> Optional[Dict]:
        return cls._insert('factory_tasks', {
            'owner_id': user_id,
            'count': count,
            'country': country,
            'auto_warmup': auto_warmup,
            'warmup_days': warmup_days,
            'role_distribution': role_distribution or {
                'observer': 0.4,
                'expert': 0.3,
                'support': 0.2,
                'trendsetter': 0.1
            },
            'status': 'pending',
            'created_count': 0,
            'failed_count': 0,
            'created_accounts': [],
            'errors': [],
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_factory_tasks(cls, user_id: int) -> List[Dict]:
        return cls._select('factory_tasks', filters={'owner_id': user_id}, order='created_at.desc')

    @classmethod
    def get_factory_task(cls, task_id: int) -> Optional[Dict]:
        return cls._select('factory_tasks', filters={'id': task_id}, single=True)

    @classmethod
    def get_pending_factory_tasks(cls) -> List[Dict]:
        return cls._select('factory_tasks', filters={'status': 'pending'}, limit=5)

    @classmethod
    def update_factory_task(cls, task_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('factory_tasks', kwargs, {'id': task_id})

    @classmethod
    def delete_factory_task(cls, task_id: int) -> bool:
        return cls._delete('factory_tasks', {'id': task_id})

    # ==================== ПРОГРЕВ АККАУНТОВ ====================

    @classmethod
    def create_warmup_progress(cls, account_id: int, total_days: int = 5, 
                               days: int = None, warmup_type: str = 'standard') -> Optional[Dict]:
        # Поддержка обоих параметров: total_days и days
        actual_days = days if days is not None else total_days
        return cls._insert('warmup_progress', {
            'account_id': account_id,
            'total_days': actual_days,
            'current_day': 1,
            'completed_actions': [],
            'status': 'in_progress',
            'warmup_type': warmup_type,
            'started_at': now_moscow().isoformat(),
            'next_action_at': now_moscow().isoformat()
        })

    @classmethod
    def get_warmup_progress(cls, account_id: int) -> Optional[Dict]:
        return cls._select('warmup_progress', filters={'account_id': account_id}, single=True)

    @classmethod
    def get_accounts_for_warmup(cls) -> List[Dict]:
        now = now_moscow().isoformat()
        return cls._select('warmup_progress', 
            filters={'status': 'in_progress'},
            raw_filters={'next_action_at': f'lte.{now}'})

    @classmethod
    def update_warmup_progress(cls, account_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('warmup_progress', kwargs, {'account_id': account_id})

    @classmethod
    def complete_warmup(cls, account_id: int) -> bool:
        cls._update('warmup_progress', {
            'status': 'completed',
            'completed_at': now_moscow().isoformat()
        }, {'account_id': account_id})
        return cls.mark_account_warmup_complete(account_id)

    @classmethod
    def get_warmup_stats(cls, user_id: int) -> Dict:
        accounts = cls._select('telegram_accounts', filters={'owner_id': user_id})
        
        in_progress = 0
        completed = 0
        pending = 0
        
        for acc in accounts:
            progress = cls.get_warmup_progress(acc['id'])
            if progress:
                if progress.get('status') == 'in_progress':
                    in_progress += 1
                elif progress.get('status') == 'completed':
                    completed += 1
            else:
                pending += 1
        
        return {
            'in_progress': in_progress,
            'completed': completed,
            'pending': pending,
            'total': len(accounts)
        }

    # ==================== АНАЛИТИКА: HEATMAP ====================

    @classmethod
    def save_audience_heatmap(cls, user_id: int, heatmap_data: dict,
                               best_times: List[dict], source_id: int = None,
                               sample_size: int = 0) -> Optional[Dict]:
        existing = cls._select('audience_heatmap', filters={'owner_id': user_id}, single=True)
        
        data = {
            'owner_id': user_id,
            'source_id': source_id,
            'heatmap_data': heatmap_data,
            'best_times': best_times,
            'sample_size': sample_size,
            'updated_at': now_moscow().isoformat()
        }
        
        if existing:
            cls._update('audience_heatmap', data, {'id': existing['id']})
            return {**existing, **data}
        else:
            data['created_at'] = now_moscow().isoformat()
            return cls._insert('audience_heatmap', data)

    @classmethod
    def get_audience_heatmap(cls, user_id: int) -> Optional[Dict]:
        return cls._select('audience_heatmap', filters={'owner_id': user_id}, single=True)

    @classmethod
    def get_optimal_send_time(cls, user_id: int) -> Optional[Dict]:
        heatmap = cls.get_audience_heatmap(user_id)
        if not heatmap or not heatmap.get('best_times'):
            return None
        
        best = heatmap['best_times'][0] if heatmap['best_times'] else None
        if not best:
            return None
        
        now = now_moscow()
        target_day = best.get('day', now.weekday())
        target_hour = best.get('hour', 12)
        
        days_ahead = target_day - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and now.hour >= target_hour):
            days_ahead += 7
        
        next_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        next_time += timedelta(days=days_ahead)
        
        day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        
        return {
            'datetime': next_time,
            'datetime_iso': next_time.isoformat(),
            'day': target_day,
            'day_name': day_names[target_day],
            'hour': target_hour,
            'score': best.get('score', 0),
            'formatted': f"{day_names[target_day]} {target_hour:02d}:00"
        }

    # ==================== АНАЛИТИКА: ПРОГНОЗ РИСКОВ ====================

    @classmethod
    def create_risk_prediction(cls, user_id: int, account_id: int,
                                risk_score: float, risk_factors: List[dict],
                                recommended_action: str,
                                recommendations: List[str]) -> Optional[Dict]:
        return cls._insert('risk_predictions', {
            'owner_id': user_id,
            'account_id': account_id,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'recommended_action': recommended_action,
            'recommendations': recommendations,
            'predicted_at': now_moscow().isoformat(),
            'valid_until': (now_moscow() + timedelta(hours=24)).isoformat()
        })

    @classmethod
    def get_latest_risk_prediction(cls, account_id: int) -> Optional[Dict]:
        now = now_moscow().isoformat()
        predictions = cls._select('risk_predictions',
            filters={'account_id': account_id},
            raw_filters={'valid_until': f'gte.{now}'},
            order='predicted_at.desc',
            limit=1)
        return predictions[0] if predictions else None

    @classmethod
    def get_all_risk_predictions(cls, user_id: int) -> List[Dict]:
        accounts = cls._select('telegram_accounts', 
            filters={'owner_id': user_id, 'status': 'active'})
        
        result = []
        for acc in accounts:
            prediction = cls.get_latest_risk_prediction(acc['id'])
            result.append({
                'account': acc,
                'prediction': prediction
            })
        
        return result

    # ==================== АНАЛИТИКА: СЕГМЕНТЫ ====================

    @classmethod
    def create_audience_segment(cls, user_id: int, name: str,
                                 segment_type: str, user_ids: List[int],
                                 source_id: int = None, campaign_id: int = None,
                                 criteria: dict = None) -> Optional[Dict]:
        return cls._insert('audience_segments', {
            'owner_id': user_id,
            'name': name,
            'segment_type': segment_type,
            'user_ids': user_ids,
            'user_count': len(user_ids),
            'source_id': source_id,
            'campaign_id': campaign_id,
            'criteria': criteria,
            'created_from': 'manual' if not campaign_id else 'mailing_results',
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_audience_segments(cls, user_id: int) -> List[Dict]:
        return cls._select('audience_segments', filters={'owner_id': user_id}, order='created_at.desc')

    @classmethod
    def get_audience_segment(cls, segment_id: int) -> Optional[Dict]:
        return cls._select('audience_segments', filters={'id': segment_id}, single=True)

    @classmethod
    def delete_audience_segment(cls, segment_id: int) -> bool:
        return cls._delete('audience_segments', {'id': segment_id})

    # ==================== КОНТЕНТ: КАНАЛЫ ПОЛЬЗОВАТЕЛЯ ====================

    @classmethod
    def create_user_channel(cls, user_id: int, channel_username: str,
                             title: str = None, niche: str = None) -> Optional[Dict]:
        username = channel_username.lower().replace('@', '').replace('https://t.me/', '')
        return cls._insert('user_channels', {
            'owner_id': user_id,
            'channel_username': username,
            'title': title,
            'niche': niche,
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_user_channels(cls, user_id: int) -> List[Dict]:
        return cls._select('user_channels', filters={'owner_id': user_id})

    @classmethod
    def get_user_channel(cls, channel_id: int) -> Optional[Dict]:
        return cls._select('user_channels', filters={'id': channel_id}, single=True)

    @classmethod
    def update_user_channel(cls, channel_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('user_channels', kwargs, {'id': channel_id})

    @classmethod
    def delete_user_channel(cls, channel_id: int) -> bool:
        return cls._delete('user_channels', {'id': channel_id})

    # ==================== КОНТЕНТ: СГЕНЕРИРОВАННЫЙ ====================

    @classmethod
    def save_generated_content(cls, user_id: int, content: str,
                                content_type: str = 'post', title: str = None,
                                generation_params: dict = None,
                                channel_id: int = None) -> Optional[Dict]:
        return cls._insert('generated_content', {
            'owner_id': user_id,
            'channel_id': channel_id,
            'type': content_type,
            'title': title,
            'content': content,
            'generation_params': generation_params,
            'status': 'draft',
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_generated_content(cls, user_id: int, status: str = None,
                               content_type: str = None, limit: int = 50) -> List[Dict]:
        filters = {'owner_id': user_id}
        if status:
            filters['status'] = status
        if content_type:
            filters['type'] = content_type
        return cls._select('generated_content', filters=filters, order='created_at.desc', limit=limit)

    @classmethod
    def get_generated_content_item(cls, content_id: int) -> Optional[Dict]:
        return cls._select('generated_content', filters={'id': content_id}, single=True)

    @classmethod
    def update_generated_content(cls, content_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('generated_content', kwargs, {'id': content_id})

    @classmethod
    def delete_generated_content(cls, content_id: int) -> bool:
        return cls._delete('generated_content', {'id': content_id})

    # ==================== STORAGE ====================

    @classmethod
    def _storage_url(cls, bucket: str, path: str = '') -> str:
        url, _ = cls._get_config()
        if path:
            return f"{url}/storage/v1/object/{bucket}/{path}"
        return f"{url}/storage/v1/object/{bucket}"

    @classmethod
    def upload_template_media(cls, user_id: int, template_id: int,
                              file_content: bytes, file_extension: str,
                              media_type: str) -> Optional[str]:
        try:
            timestamp = int(time.time())
            filename = f"{user_id}/{template_id}_{timestamp}{file_extension}"

            content_types = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                '.gif': 'image/gif', '.webp': 'image/webp', '.mp4': 'video/mp4',
                '.mov': 'video/quicktime', '.avi': 'video/x-msvideo',
                '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.wav': 'audio/wav',
                '.pdf': 'application/pdf',
            }
            content_type = content_types.get(file_extension.lower(), 'application/octet-stream')

            url, key = cls._get_config()
            upload_url = f"{url}/storage/v1/object/templates/{filename}"

            headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Content-Type': content_type,
                'x-upsert': 'true'
            }

            response = requests.post(upload_url, headers=headers, data=file_content, timeout=60)

            if response.ok:
                public_url = f"{url}/storage/v1/object/public/templates/{filename}"
                logger.info(f"Uploaded media to Storage: {public_url}")
                return public_url
            else:
                logger.error(f"Storage upload failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"upload_template_media error: {e}")
            return None

    @classmethod
    def delete_template_media(cls, media_url: str) -> bool:
        try:
            if not media_url or '/storage/v1/object/public/templates/' not in media_url:
                return True

            path = media_url.split('/storage/v1/object/public/templates/')[-1]
            url, key = cls._get_config()
            delete_url = f"{url}/storage/v1/object/templates/{path}"

            headers = {'apikey': key, 'Authorization': f'Bearer {key}'}
            response = requests.delete(delete_url, headers=headers, timeout=30)

            if response.ok:
                logger.info(f"Deleted media from Storage: {path}")
                return True
            return False

        except Exception as e:
            logger.error(f"delete_template_media error: {e}")
            return False

    @classmethod
    def create_template_with_media(cls, user_id: int, name: str, text: str,
                                   file_content: bytes = None, file_extension: str = None,
                                   media_type: str = None, media_file_id: str = None,
                                   folder_id: int = None) -> Optional[Dict]:
        data = {
            'owner_id': user_id,
            'name': name,
            'text': text,
            'created_at': now_moscow().isoformat()
        }
        if folder_id:
            data['folder_id'] = folder_id
        if media_file_id:
            data['media_file_id'] = media_file_id
        if media_type:
            data['media_type'] = media_type

        template = cls._insert('message_templates', data)
        if not template:
            return None

        if file_content and file_extension and media_type:
            media_url = cls.upload_template_media(user_id, template['id'],
                file_content, file_extension, media_type)
            if media_url:
                cls._update('message_templates', {'media_url': media_url}, {'id': template['id']})
                template['media_url'] = media_url

        return template

    # ==================== TEMPLATES ====================

    @classmethod
    def get_templates(cls, user_id: int, folder_id: int = None) -> List[Dict]:
        if folder_id is not None:
            return cls._select('message_templates', filters={'owner_id': user_id, 'folder_id': folder_id}, order='created_at.desc')
        return cls._select('message_templates', filters={'owner_id': user_id}, order='created_at.desc')

    @classmethod
    def get_templates_without_folder(cls, user_id: int) -> List[Dict]:
        try:
            params = {
                'select': '*',
                'owner_id': f'eq.{user_id}',
                'folder_id': 'is.null',
                'order': 'created_at.desc'
            }
            response = requests.get(cls._api_url('message_templates'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_templates_without_folder error: {e}")
            return []

    @classmethod
    def get_template(cls, template_id: int) -> Optional[Dict]:
        t = cls._select('message_templates', filters={'id': template_id}, single=True)
        if t:
            t['user_id'] = t.get('owner_id')
        return t

    @classmethod
    def create_template(cls, user_id: int, name: str, text: str,
                       media_file_id: str = None, media_type: str = None, 
                       folder_id: int = None, media_url: str = None) -> Optional[Dict]:
        data = {
            'owner_id': user_id,
            'name': name,
            'text': text,
            'created_at': now_moscow().isoformat()
        }
        if media_file_id:
            data['media_file_id'] = media_file_id
        if media_type:
            data['media_type'] = media_type
        if folder_id:
            data['folder_id'] = folder_id
        if media_url:
            data['media_url'] = media_url

        return cls._insert('message_templates', data)

    @classmethod
    def update_template(cls, template_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('message_templates', kwargs, {'id': template_id})

    @classmethod
    def delete_template(cls, template_id: int) -> bool:
        template = cls._select('message_templates', filters={'id': template_id}, single=True)
        if not template:
            return False
        
        if template.get('media_url'):
            cls.delete_template_media(template['media_url'])
        
        cls._delete('campaigns', {'template_id': template_id})
        cls._delete('scheduled_mailings', {'template_id': template_id})
        return cls._delete('message_templates', {'id': template_id})

    @classmethod
    def copy_template(cls, template_id: int, user_id: int) -> Optional[Dict]:
        orig = cls.get_template(template_id)
        if not orig:
            return None
        return cls.create_template(
            user_id, f"{orig['name']} (копия)", orig.get('text', ''),
            orig.get('media_file_id'), orig.get('media_type'), orig.get('folder_id'), None
        )

    @classmethod
    def update_template_folder(cls, template_id: int, folder_id: int = None) -> bool:
        return cls._update('message_templates', 
            {'folder_id': folder_id, 'updated_at': now_moscow().isoformat()}, 
            {'id': template_id})

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
            'owner_id': user_id, 'name': name, 'created_at': now_moscow().isoformat()
        })

    @classmethod
    def rename_template_folder(cls, folder_id: int, name: str) -> bool:
        return cls._update('template_folders', {'name': name}, {'id': folder_id})

    @classmethod
    def delete_template_folder(cls, folder_id: int) -> bool:
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
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def rename_account_folder(cls, folder_id: int, name: str) -> bool:
        return cls._update('account_folders', {'name': name}, {'id': folder_id})

    @classmethod
    def delete_account_folder(cls, folder_id: int) -> bool:
        cls.move_accounts_from_folder(folder_id)
        return cls._delete('account_folders', {'id': folder_id})

    @classmethod
    def move_accounts_from_folder(cls, folder_id: int) -> bool:
        try:
            params = {'folder_id': f'eq.{folder_id}'}
            data = {'folder_id': None, 'updated_at': now_moscow().isoformat()}
            response = requests.patch(cls._api_url('telegram_accounts'),
                headers=cls._headers(), json=data, params=params, timeout=10)
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
        try:
            params = {
                'select': '*',
                'owner_id': f'eq.{user_id}',
                'folder_id': 'is.null',
                'order': 'created_at.desc'
            }
            response = requests.get(cls._api_url('telegram_accounts'), 
                                   headers=cls._headers(), params=params, timeout=10)
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
        return cls._select('telegram_accounts', 
            filters={'owner_id': user_id, 'status': 'active'}, 
            order='reliability_score.desc,daily_sent.asc')

    @classmethod
    def get_any_active_account(cls, user_id: int) -> Optional[Dict]:
        accounts = cls._select('telegram_accounts',
            filters={'owner_id': user_id, 'status': 'active'},
            order='reliability_score.desc,daily_sent.asc',
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
    def create_account(cls, user_id: int, phone: str, session_file: str = None,
                       folder_id: int = None, role: str = 'observer',
                       source: str = 'manual') -> Optional[Dict]:
        """Создать новый аккаунт"""
        return cls._insert('telegram_accounts', {
            'owner_id': user_id,
            'phone': phone,
            'session_file': session_file,
            'folder_id': folder_id,
            'role': role,
            'source': source,
            'status': 'pending',
            'daily_limit': 50,
            'daily_sent': 0,
            'reliability_score': 100,
            'consecutive_errors': 0,
            'warmup_status': 'none',
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def update_account(cls, account_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('telegram_accounts', kwargs, {'id': account_id})

    @classmethod
    def delete_account(cls, account_id: int) -> bool:
        account = cls._select('telegram_accounts', filters={'id': account_id}, single=True)
        if not account:
            return False
        user_id = account.get('owner_id')
        phone = account.get('phone')
        
        # Удаляем связанные данные
        cls._delete('campaigns', {'current_account_id': account_id})
        cls._delete('sent_messages', {'account_id': account_id})
        cls._delete('warmup_activities', {'account_id': account_id})
        cls._delete('account_limits_history', {'account_id': account_id})
        cls._delete('account_profiles', {'account_id': account_id})
        cls._delete('warmup_progress', {'account_id': account_id})
        cls._delete('herder_logs', {'account_id': account_id})
        
        if user_id and phone:
            cls._delete('auth_tasks', {'owner_id': user_id, 'phone': phone})
        
        return cls._delete('telegram_accounts', {'id': account_id})

    @classmethod
    def get_accounts_for_herder(cls, user_id: int, account_ids: List[int] = None,
                                 folder_id: int = None) -> List[Dict]:
        """Получить аккаунты для ботовода с профилями"""
        if folder_id:
            accounts = cls.get_accounts_in_folder(folder_id)
        elif account_ids:
            accounts = [cls.get_account(aid) for aid in account_ids if aid]
            accounts = [a for a in accounts if a]
        else:
            accounts = cls.get_active_accounts(user_id)
        
        # Добавляем профили
        for acc in accounts:
            if acc:
                acc['profile'] = cls.get_account_profile(acc['id'])
        
        return accounts

    # ==================== AUTH TASKS ====================

    @classmethod
    def create_auth_task(cls, user_id: int, phone: str, folder_id: int = None, 
                        task_type: str = 'manual', account_id: int = None) -> Optional[Dict]:
        data = {
            'owner_id': user_id,
            'phone': phone,
            'status': 'pending',
            'task_type': task_type,
            'created_at': now_moscow().isoformat(),
            'expires_at': (now_moscow() + timedelta(minutes=10)).isoformat()
        }
        if folder_id:
            data['folder_id'] = folder_id
        if account_id:
            data['account_id'] = account_id
        return cls._insert('auth_tasks', data)

    @classmethod
    def update_auth_task(cls, task_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('auth_tasks', kwargs, {'id': task_id})

    @classmethod
    def get_auth_task(cls, task_id: int) -> Optional[Dict]:
        return cls._select('auth_tasks', filters={'id': task_id}, single=True)

    @classmethod
    def get_pending_auth_tasks(cls) -> List[Dict]:
        """Для воркера: задачи авторизации"""
        return cls._select('auth_tasks', 
            filters={'status': 'code_received'},
            order='created_at.asc',
            limit=10)

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
                               filters: Dict, tags: List[str] = None,
                               keyword_filter: List[str] = None,
                               keyword_match_mode: str = 'any') -> Optional[Dict]:
        data = {
            'owner_id': user_id, 
            'source_type': source_type, 
            'source_link': source_link,
            'filters': filters, 
            'tags': tags or [], 
            'status': 'pending', 
            'parsed_count': 0,
            'created_at': now_moscow().isoformat()
        }
        if keyword_filter:
            data['keyword_filter'] = keyword_filter
            data['keyword_match_mode'] = keyword_match_mode
        return cls._insert('audience_sources', data)

    @classmethod
    def update_audience_source(cls, source_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('audience_sources', kwargs, {'id': source_id})

    @classmethod
    def delete_audience_source(cls, source_id: int) -> bool:
        source = cls._select('audience_sources', filters={'id': source_id}, single=True)
        if not source:
            return False
        
        # Extract source_chat_id from source_link (e.g., "https://t.me/magiyarunes" -> "magiyarunes")
        source_link = source.get('source_link', '')
        owner_id = source.get('owner_id')
        
        # Try to get source_chat_id from source_link
        source_chat_id = None
        if source_link:
            # Extract username from link (remove @ if present, get last part after /)
            # Handle formats: "https://t.me/magiyarunes", "t.me/magiyarunes", "@magiyarunes", "magiyarunes"
            source_link_clean = source_link.strip().rstrip('/')
            if source_link_clean.startswith('http'):
                parts = source_link_clean.split('/')
                source_chat_id = parts[-1].lstrip('@') if parts else None
            elif source_link_clean.startswith('t.me/'):
                source_chat_id = source_link_clean.split('t.me/')[-1].lstrip('@')
            elif source_link_clean.startswith('@'):
                source_chat_id = source_link_clean.lstrip('@')
            else:
                source_chat_id = source_link_clean.lstrip('@')
        
        # Delete related data
        cls._delete('campaigns', {'source_id': source_id})
        cls._delete('scheduled_mailings', {'source_id': source_id})
        cls._delete('parsed_audiences', {'source_id': source_id})
        cls._delete('keyword_filters', {'source_id': source_id})
        cls._delete('audience_segments', {'source_id': source_id})
        
        # Delete audience_users and user_messages for this source
        if owner_id and source_chat_id:
            # Get all tg_user_ids from audience_users for this source
            audience_users = cls._select('audience_users', 
                filters={'owner_id': owner_id, 'source_chat_id': source_chat_id})
            
            if audience_users:
                tg_user_ids = [user.get('tg_user_id') for user in audience_users if user.get('tg_user_id')]
                
                logger.info(f"Deleting {len(audience_users)} audience_users and messages for {len(tg_user_ids)} users from source {source_id} (chat: {source_chat_id})")
                
                # Delete user_messages for these users
                if tg_user_ids:
                    deleted_messages = 0
                    for tg_user_id in tg_user_ids:
                        # Count messages before deletion for logging
                        msg_count = cls._count('user_messages', {'owner_id': owner_id, 'tg_user_id': tg_user_id})
                        if msg_count > 0:
                            cls._delete('user_messages', {'owner_id': owner_id, 'tg_user_id': tg_user_id})
                            deleted_messages += msg_count
                    
                    logger.info(f"Deleted {deleted_messages} user_messages for source {source_id}")
                
                # Delete audience_users
                deleted_users = cls._count('audience_users', {'owner_id': owner_id, 'source_chat_id': source_chat_id})
                cls._delete('audience_users', {'owner_id': owner_id, 'source_chat_id': source_chat_id})
                logger.info(f"Deleted {deleted_users} audience_users for source {source_id}")
            else:
                logger.debug(f"No audience_users found for source {source_id} (chat: {source_chat_id})")
        else:
            logger.warning(f"Cannot delete audience_users/user_messages: owner_id={owner_id}, source_chat_id={source_chat_id}")
        
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

    @classmethod
    def get_completed_audience_sources(cls, user_id: int) -> List[Dict]:
        """Получить завершённые парсинги для рассылки"""
        return cls._select('audience_sources', 
            filters={'owner_id': user_id, 'status': 'completed'},
            order='created_at.desc')

    # ==================== AUDIENCE TAGS ====================

    @classmethod
    def get_audience_tags(cls, user_id: int) -> List[Dict]:
        return cls._select('audience_tags', filters={'owner_id': user_id}, order='name.asc')

    @classmethod
    def create_audience_tag(cls, user_id: int, name: str) -> Optional[Dict]:
        return cls._insert('audience_tags', {
            'owner_id': user_id, 'name': name, 'color': '#3B82F6',
            'created_at': now_moscow().isoformat()
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
                'select': '*',
                'source_id': f'eq.{source_id}',
                'or': f'(username.ilike.%{query}%,first_name.ilike.%{query}%,last_name.ilike.%{query}%)',
                'limit': str(limit)
            }
            response = requests.get(cls._api_url('parsed_audiences'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"search_in_audience error: {e}")
            return []

    @classmethod
    def get_audience_with_filters(cls, source_id: int, limit: int = 1000, 
                                  only_unsent: bool = False) -> List[Dict]:
        try:
            params = {
                'select': '*',
                'source_id': f'eq.{source_id}',
                'order': 'created_at.asc',
                'limit': str(limit)
            }
            if only_unsent:
                params['sent'] = 'eq.false'

            response = requests.get(cls._api_url('parsed_audiences'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_audience_with_filters error: {e}")
            return []

    @classmethod
    def get_unsent_users(cls, source_id: int, limit: int = 50) -> List[Dict]:
        return cls.get_audience_with_filters(source_id, limit=limit, only_unsent=True)

    @classmethod
    def get_unsent_users_with_cache_check(cls, source_id: int, user_id: int, 
                                          limit: int = 50, ttl_days: int = 30) -> List[Dict]:
        users = cls.get_unsent_users(source_id, limit=limit * 2)
        
        result = []
        for u in users:
            tg_id = u.get('tg_user_id')
            if tg_id and not cls.check_mailing_cache(user_id, tg_id, ttl_days):
                result.append(u)
                if len(result) >= limit:
                    break
        
        return result

    @classmethod
    def mark_user_sent(cls, user_id: int, success: bool = True, error: str = None) -> bool:
        data = {
            'sent': True,
            'sent_at': now_moscow().isoformat(),
            'send_success': success
        }
        if error:
            data['send_error'] = error[:200]
        return cls._update('parsed_audiences', data, {'id': user_id})

    # ==================== BLACKLIST ====================

    @classmethod
    def get_blacklist(cls, user_id: int) -> List[Dict]:
        return cls._select('blacklist', filters={'owner_id': user_id}, order='created_at.desc')

    @classmethod
    def get_blacklist_items(cls, user_id: int) -> List[Dict]:
        return cls.get_blacklist(user_id)

    @classmethod
    def get_blacklist_set(cls, user_id: int) -> Set:
        items = cls.get_blacklist(user_id)
        result = set()
        for item in items:
            if item.get('tg_user_id'):
                result.add(item['tg_user_id'])
            if item.get('username'):
                result.add(item['username'].lower())
        return result

    @classmethod
    def add_to_blacklist(cls, user_id: int, tg_user_id: int = None, username: str = None,
                        source: str = 'manual', auto_reason: str = None) -> Optional[Dict]:
        return cls._insert('blacklist', {
            'owner_id': user_id, 
            'tg_user_id': tg_user_id, 
            'username': username,
            'source': source,
            'auto_reason': auto_reason,
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def remove_from_blacklist(cls, blacklist_id: int) -> bool:
        return cls._delete('blacklist', {'id': blacklist_id})

    @classmethod
    def is_in_blacklist(cls, user_id: int, tg_user_id: int = None, username: str = None) -> bool:
        if tg_user_id:
            count = cls._count('blacklist', {'owner_id': user_id, 'tg_user_id': tg_user_id})
            if count > 0:
                return True
        if username:
            count = cls._count('blacklist', {'owner_id': user_id, 'username': username.lower()})
            if count > 0:
                return True
        return False

    # ==================== CAMPAIGNS ====================

    @classmethod
    def create_campaign(cls, user_id: int, source_id: int, template_id: int,
                       account_ids: List[int] = None, account_folder_id: int = None,
                       settings: Dict = None, use_warm_start: bool = True,
                       use_typing: bool = True, use_adaptive: bool = True,
                       scheduled_at: datetime = None,
                       time_optimization: str = 'now',
                       smart_personalization: bool = False,
                       context_depth: int = 5,
                       max_response_length: int = 280,
                       tone: str = 'neutral',
                       language: str = 'ru',
                       base_template_id: int = None) -> Optional[Dict]:
        stats = cls.get_audience_stats(source_id)
        
        # Normalize account_folder_id: 0 or None should be None
        normalized_folder_id = account_folder_id if account_folder_id and account_folder_id > 0 else None
        
        data = {
            'owner_id': user_id,
            'source_id': source_id,
            'template_id': template_id,
            'account_ids': account_ids or [],
            'current_account_id': account_ids[0] if account_ids else None,
            'next_account_index': 0,
            'status': 'pending' if not scheduled_at else 'scheduled',
            'sent_count': 0,
            'failed_count': 0,
            'total_count': stats['remaining'],
            'settings': settings or {},
            'use_warm_start': use_warm_start,
            'warm_start_count': 10,
            'use_typing_simulation': use_typing,
            'use_adaptive_delays': use_adaptive,
            'use_time_optimization': True,
            'time_optimization': time_optimization,
            'smart_personalization': smart_personalization,
            # Only set smart mailing fields if smart_personalization is enabled
            'context_depth': context_depth if smart_personalization else None,
            'max_response_length': max_response_length if smart_personalization else None,
            'tone': tone if smart_personalization else None,
            'language': language if smart_personalization else None,
            'created_at': now_moscow().isoformat()
        }
        
        # Only add account_folder_id if it's not None
        if normalized_folder_id is not None:
            data['account_folder_id'] = normalized_folder_id
        
        # Only add base_template_id if it's set and smart_personalization is enabled
        # base_template_id can be the same as template_id (it's the base template for generation)
        if smart_personalization and base_template_id:
            data['base_template_id'] = base_template_id
            logger.info(f"Smart mailing: template_id={template_id}, base_template_id={base_template_id}")
        
        if scheduled_at:
            data['scheduled_at'] = scheduled_at.isoformat()
        
        logger.info(f"Creating campaign with data: {data}")
        
        # Clean data: remove None values for optional fields
        # account_folder_id, base_template_id, scheduled_at, current_account_id can be None
        cleaned_data = {}
        for k, v in data.items():
            # Skip None for most fields, but allow None for optional foreign keys
            if v is None:
                # Only include None for fields that explicitly allow it
                if k in ['account_folder_id', 'base_template_id', 'scheduled_at', 'current_account_id']:
                    # Don't include None - Supabase will use default or NULL
                    continue
                else:
                    # Skip None for required fields
                    continue
            cleaned_data[k] = v
        
        logger.info(f"Cleaned campaign data (removed None values): {cleaned_data}")
        
        try:
            result = cls._insert('campaigns', cleaned_data)
            logger.info(f"Campaign creation result: {result}")
            if not result:
                logger.error(f"Campaign creation returned None. Check Supabase logs for details.")
            return result
        except Exception as e:
            logger.error(f"Exception in create_campaign: {e}", exc_info=True)
            return None

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
            response = requests.get(cls._api_url('campaigns'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_active_campaigns error: {e}")
            return []

    @classmethod
    def get_scheduled_campaigns(cls, user_id: int) -> List[Dict]:
        return cls._select('campaigns', 
            filters={'owner_id': user_id, 'status': 'scheduled'},
            order='scheduled_at.asc')

    @classmethod
    def get_pending_campaigns(cls, limit: int = 5) -> List[Dict]:
        return cls._select('campaigns', filters={'status': 'pending'}, 
                          order='created_at.asc', limit=limit)

    @classmethod
    def get_running_campaigns(cls) -> List[Dict]:
        return cls._select('campaigns', filters={'status': 'running'})

    @classmethod
    def get_due_scheduled_campaigns(cls) -> List[Dict]:
        """Для воркера: кампании готовые к запуску"""
        try:
            now = now_moscow().isoformat()
            params = {
                'select': '*',
                'status': 'eq.scheduled',
                'scheduled_at': f'lte.{now}',
                'order': 'scheduled_at.asc',
                'limit': '10'
            }
            response = requests.get(cls._api_url('campaigns'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_due_scheduled_campaigns error: {e}")
            return []

    @classmethod
    def update_campaign(cls, campaign_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('campaigns', kwargs, {'id': campaign_id})

    @classmethod
    def increment_campaign_stats(cls, campaign_id: int, sent: int = 0, failed: int = 0) -> bool:
        campaign = cls.get_campaign(campaign_id)
        if not campaign:
            return False
        
        new_sent = (campaign.get('sent_count', 0) or 0) + sent
        new_failed = (campaign.get('failed_count', 0) or 0) + failed
        messages_since_error = campaign.get('messages_since_last_error', 0) or 0
        
        updates = {
            'sent_count': new_sent,
            'failed_count': new_failed,
        }
        
        if failed > 0:
            updates['messages_since_last_error'] = 0
        else:
            updates['messages_since_last_error'] = messages_since_error + sent
        
        return cls.update_campaign(campaign_id, **updates)

    @classmethod
    def switch_campaign_account(cls, campaign_id: int, new_account_id: int, 
                                next_index: int = 0) -> bool:
        return cls.update_campaign(campaign_id,
            current_account_id=new_account_id,
            next_account_index=next_index)

    @classmethod
    def pause_campaign(cls, campaign_id: int, reason: str = None) -> bool:
        data = {
            'status': 'paused',
            'updated_at': now_moscow().isoformat()
        }
        if reason:
            data['pause_reason'] = reason
        return cls._update('campaigns', data, {'id': campaign_id})

    @classmethod
    def resume_campaign(cls, campaign_id: int) -> bool:
        return cls.update_campaign(campaign_id, status='running', pause_reason=None)

    @classmethod
    def stop_campaign(cls, campaign_id: int) -> bool:
        return cls.update_campaign(campaign_id, status='stopped')

    @classmethod
    def complete_campaign(cls, campaign_id: int) -> bool:
        return cls.update_campaign(campaign_id, 
            status='completed',
            completed_at=now_moscow().isoformat())

    @classmethod
    def pause_all_campaigns(cls, user_id: int, reason: str = 'Panic stop') -> int:
        try:
            params = {
                'owner_id': f'eq.{user_id}',
                'status': 'in.(pending,running)'
            }
            data = {
                'status': 'paused',
                'pause_reason': reason,
                'updated_at': now_moscow().isoformat()
            }
            response = requests.patch(cls._api_url('campaigns'),
                headers=cls._headers(), json=data, params=params, timeout=10)
            return 1 if response.ok else 0
        except Exception as e:
            logger.error(f"pause_all_campaigns error: {e}")
            return 0

    @classmethod
    def delete_campaign(cls, campaign_id: int) -> bool:
        cls._delete('sent_messages', {'campaign_id': campaign_id})
        return cls._delete('campaigns', {'id': campaign_id})

    # ==================== SCHEDULED MAILINGS ====================

    @classmethod
    def create_scheduled_mailing(cls, user_id: int, source_id: int, template_id: int,
                                 account_folder_id: int = None, scheduled_at: datetime = None,
                                 use_warm_start: bool = True) -> Optional[Dict]:
        return cls._insert('scheduled_mailings', {
            'owner_id': user_id,
            'source_id': source_id,
            'template_id': template_id,
            'account_folder_id': account_folder_id,
            'account_id': 0,
            'scheduled_at': scheduled_at.isoformat() if scheduled_at else None,
            'status': 'pending',
            'use_warm_start': use_warm_start,
            'created_at': now_moscow().isoformat()
        })

    @classmethod
    def get_scheduled_mailings(cls, user_id: int) -> List[Dict]:
        return cls._select('scheduled_mailings', filters={'owner_id': user_id}, 
                          order='scheduled_at.asc')

    @classmethod
    def get_due_scheduled_mailings(cls) -> List[Dict]:
        try:
            now = now_moscow().isoformat()
            params = {
                'select': '*',
                'status': 'eq.pending',
                'scheduled_at': f'lte.{now}',
                'order': 'scheduled_at.asc',
                'limit': '10'
            }
            response = requests.get(cls._api_url('scheduled_mailings'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_due_scheduled_mailings error: {e}")
            return []

    @classmethod
    def update_scheduled_mailing(cls, mailing_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('scheduled_mailings', kwargs, {'id': mailing_id})

    @classmethod
    def delete_scheduled_mailing(cls, mailing_id: int) -> bool:
        return cls._delete('scheduled_mailings', {'id': mailing_id})

    # ==================== SENT MESSAGES ====================

    @classmethod
    def record_sent_message(cls, campaign_id: int, user_tg_id: int,
                           account_id: int, status: str = 'sent', error: str = None) -> bool:
        try:
            data = {
                'campaign_id': campaign_id,
                'user_tg_id': user_tg_id,
                'account_id': account_id,
                'status': status,
                'sent_at': now_moscow().isoformat()
            }
            if error:
                data['error_message'] = error[:200]
            headers = cls._headers()
            headers['Prefer'] = 'resolution=merge-duplicates,return=representation'
            response = requests.post(cls._api_url('sent_messages'), 
                                    headers=headers, json=data, timeout=10)
            return response.ok
        except Exception as e:
            logger.error(f"record_sent_message error: {e}")
            return False

    @classmethod
    def get_sent_user_ids_for_campaign(cls, campaign_id: int) -> Set[int]:
        try:
            params = {'select': 'user_tg_id', 'campaign_id': f'eq.{campaign_id}'}
            response = requests.get(cls._api_url('sent_messages'), 
                                   headers=cls._headers(), params=params, timeout=10)
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
        data = {
            'owner_id': user_id,
            'error_type': error_type,
            'error_message': error_message[:500] if error_message else None,
            'created_at': now_moscow().isoformat()
        }
        if campaign_id:
            data['campaign_id'] = campaign_id
        if account_id:
            data['account_id'] = account_id
        if context:
            data['context'] = context
        return cls._insert('error_logs', data) is not None

    @classmethod
    def get_error_logs(cls, user_id: int, days: int = 7, limit: int = 100) -> List[Dict]:
        start_date = (now_moscow() - timedelta(days=days)).isoformat()
        return cls._select('error_logs',
            filters={'owner_id': user_id},
            raw_filters={'created_at': f'gte.{start_date}'},
            order='created_at.desc',
            limit=limit)

    @classmethod
    def get_error_stats(cls, user_id: int, days: int = 7) -> Dict:
        try:
            start_date = (now_moscow() - timedelta(days=days)).isoformat()
            params = {
                'select': 'error_type',
                'owner_id': f'eq.{user_id}',
                'created_at': f'gte.{start_date}'
            }
            response = requests.get(cls._api_url('error_logs'), 
                                   headers=cls._headers(), params=params, timeout=10)
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
        
        # Статистика ботовода
        herder_stats = cls.get_herder_stats(user_id, days=30)
        
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
            'success_rate': round(total_sent / (total_sent + total_failed) * 100, 1) if (total_sent + total_failed) > 0 else 0,
            'herder_actions': herder_stats.get('total_actions', 0),
            'herder_comments': herder_stats.get('total_comments', 0)
        }

    @classmethod
    def get_dashboard_stats(cls, user_id: int) -> Dict:
        """Расширенная статистика для дашборда"""
        basic = cls.get_user_stats(user_id)
        
        # Добавляем данные ботовода
        herder_assignments = cls.count_herder_assignments(user_id, status='active')
        monitored_channels = cls.count_monitored_channels(user_id)
        
        # Прогрев
        warmup_stats = cls.get_warmup_stats(user_id)
        
        # Риски
        risk_predictions = cls.get_all_risk_predictions(user_id)
        high_risk_count = sum(1 for r in risk_predictions 
                             if r.get('prediction') and r['prediction'].get('risk_score', 0) > 0.7)
        
        return {
            **basic,
            'herder_active_assignments': herder_assignments,
            'monitored_channels': monitored_channels,
            'warmup_in_progress': warmup_stats.get('in_progress', 0),
            'warmup_completed': warmup_stats.get('completed', 0),
            'high_risk_accounts': high_risk_count
        }

    # ==================== FLOOD WAIT MANAGEMENT ====================

    @classmethod
    def set_account_flood_wait(cls, account_id: int, wait_seconds: int) -> bool:
        flood_until = (now_moscow() + timedelta(seconds=wait_seconds)).isoformat()
        return cls.update_account(account_id,
            status='flood_wait',
            flood_wait_until=flood_until,
            error_message=f'Flood wait: {wait_seconds}s')

    @classmethod
    def get_accounts_ready_after_flood(cls) -> List[Dict]:
        try:
            now = now_moscow().isoformat()
            params = {
                'select': '*',
                'status': 'eq.flood_wait',
                'flood_wait_until': f'lte.{now}'
            }
            response = requests.get(cls._api_url('telegram_accounts'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_accounts_ready_after_flood error: {e}")
            return []

    @classmethod
    def reactivate_account(cls, account_id: int) -> bool:
        return cls.update_account(account_id,
            status='active',
            flood_wait_until=None,
            error_message=None,
            consecutive_errors=0)

    # ==================== DAILY RESET ====================

    @classmethod
    def reset_daily_counters(cls) -> bool:
        """Сброс дневных счётчиков (вызывается в полночь по Москве)"""
        try:
            data = {
                'daily_sent': 0,
                'total_sent_today': 0,
                'total_errors_today': 0,
                'updated_at': now_moscow().isoformat()
            }
            response = requests.patch(cls._api_url('telegram_accounts'),
                headers=cls._headers(), json=data, params={}, timeout=30)
            return response.ok
        except Exception as e:
            logger.error(f"reset_daily_counters error: {e}")
            return False

    # ==================== EXPORT ====================

    @classmethod
    def export_audience_to_csv(cls, source_id: int) -> List[Dict]:
        """Получить аудиторию для экспорта"""
        return cls._select('parsed_audiences', 
            filters={'source_id': source_id},
            order='created_at.asc')

    @classmethod
    def export_campaign_results(cls, campaign_id: int) -> List[Dict]:
        """Получить результаты кампании для экспорта"""
        return cls._select('sent_messages',
            filters={'campaign_id': campaign_id},
            order='sent_at.asc')

    # ==================== VPS TASKS ====================

    @classmethod
    def create_vps_task(cls, user_id: int, task_type: str, task_data: dict,
                        priority: int = 5, scheduled_at: datetime = None) -> Optional[Dict]:
        """Создать задачу для VPS"""
        data = {
            'owner_id': user_id,
            'task_type': task_type,
            'task_data': task_data,
            'priority': priority,
            'status': 'pending',
            'created_at': now_moscow().isoformat()
        }
        if scheduled_at:
            data['scheduled_at'] = scheduled_at.isoformat()
        return cls._insert('vps_tasks', data)

    @classmethod
    def get_vps_tasks(cls, user_id: int, status: str = None) -> List[Dict]:
        """Получить VPS задачи пользователя"""
        filters = {'owner_id': user_id}
        if status:
            filters['status'] = status
        return cls._select('vps_tasks', filters=filters, order='created_at.desc')

    @classmethod
    def get_pending_vps_tasks(cls) -> List[Dict]:
        """Получить все ожидающие VPS задачи"""
        return cls._select('vps_tasks', filters={'status': 'pending'}, 
                          order='priority.desc,created_at.asc')

    @classmethod
    def update_vps_task(cls, task_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('vps_tasks', kwargs, {'id': task_id})

    @classmethod
    def delete_vps_task(cls, task_id: int) -> bool:
        return cls._delete('vps_tasks', {'id': task_id})

    # ==================== ACCOUNT FOLDER HELPERS ====================

    @classmethod
    def get_account_folder_by_name(cls, user_id: int, name: str) -> Optional[Dict]:
        """Получить папку аккаунтов по имени"""
        try:
            params = {
                'select': '*',
                'owner_id': f'eq.{user_id}',
                'name': f'eq.{name}',
                'limit': 1
            }
            response = requests.get(cls._api_url('account_folders'), 
                                   headers=cls._headers(), params=params, timeout=10)
            data = response.json() if response.ok else []
            return data[0] if data else None
        except Exception as e:
            logger.error(f"get_account_folder_by_name error: {e}")
            return None

    @classmethod
    def get_accounts_by_warmup_type(cls, user_id: int, warmup_type: str) -> List[Dict]:
        """Получить аккаунты по типу прогрева"""
        try:
            params = {
                'select': '*',
                'owner_id': f'eq.{user_id}',
                'warmup_type': f'eq.{warmup_type}',
                'warmup_status': 'in.(pending_warm,in_progress)'
            }
            response = requests.get(cls._api_url('telegram_accounts'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_accounts_by_warmup_type error: {e}")
            return []

    @classmethod
    def check_account_exists(cls, user_id: int, phone: str) -> bool:
        """Проверить существует ли аккаунт с таким номером"""
        existing = cls._select('telegram_accounts', 
                              filters={'owner_id': user_id, 'phone': phone}, 
                              single=True)
        return existing is not None

    # ==================== SCHEDULED CONTENT (CONTENT PLAN) ====================

    @classmethod
    def create_scheduled_content(cls, user_id: int, channel_id: int, content: str,
                                 scheduled_at: datetime, repeat_mode: str = 'once',
                                 media_url: str = None, media_type: str = None) -> Optional[Dict]:
        """Создать запланированный контент"""
        data = {
            'owner_id': user_id,
            'channel_id': channel_id,
            'content': content,
            'scheduled_at': scheduled_at.isoformat(),
            'repeat_mode': repeat_mode,
            'status': 'pending',
            'created_at': now_moscow().isoformat()
        }
        if media_url:
            data['media_url'] = media_url
            data['media_type'] = media_type
        return cls._insert('scheduled_content', data)

    @classmethod
    def get_scheduled_content(cls, user_id: int, status: str = None, 
                             channel_id: int = None) -> List[Dict]:
        """Получить запланированный контент"""
        filters = {'owner_id': user_id}
        if status:
            filters['status'] = status
        if channel_id:
            filters['channel_id'] = channel_id
        return cls._select('scheduled_content', filters=filters, 
                          order='scheduled_at.asc')

    @classmethod
    def get_scheduled_content_item(cls, content_id: int) -> Optional[Dict]:
        """Получить элемент запланированного контента"""
        return cls._select('scheduled_content', filters={'id': content_id}, single=True)

    @classmethod
    def get_due_scheduled_content(cls) -> List[Dict]:
        """Получить контент готовый к публикации"""
        try:
            now = now_moscow().isoformat()
            params = {
                'select': '*',
                'status': 'eq.pending',
                'scheduled_at': f'lte.{now}'
            }
            response = requests.get(cls._api_url('scheduled_content'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_due_scheduled_content error: {e}")
            return []

    @classmethod
    def update_scheduled_content(cls, content_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('scheduled_content', kwargs, {'id': content_id})

    @classmethod
    def delete_scheduled_content(cls, content_id: int) -> bool:
        return cls._delete('scheduled_content', {'id': content_id})

    # ==================== TEMPLATE SCHEDULES ====================

    @classmethod
    def create_template_schedule(cls, user_id: int, template_id: int, 
                                channel_id: int, publish_time: str) -> Optional[Dict]:
        """Создать расписание публикации шаблона"""
        data = {
            'owner_id': user_id,
            'template_id': template_id,
            'channel_id': channel_id,
            'publish_time': publish_time,
            'is_active': True,
            'created_at': now_moscow().isoformat()
        }
        return cls._insert('template_schedules', data)

    @classmethod
    def get_template_schedules(cls, user_id: int, active_only: bool = True) -> List[Dict]:
        """Получить расписания шаблонов"""
        filters = {'owner_id': user_id}
        if active_only:
            filters['is_active'] = True
        return cls._select('template_schedules', filters=filters, 
                          order='publish_time.asc')

    @classmethod
    def get_template_schedule(cls, schedule_id: int) -> Optional[Dict]:
        return cls._select('template_schedules', filters={'id': schedule_id}, single=True)

    @classmethod
    def update_template_schedule(cls, schedule_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = now_moscow().isoformat()
        return cls._update('template_schedules', kwargs, {'id': schedule_id})

    @classmethod
    def delete_template_schedule(cls, schedule_id: int) -> bool:
        return cls._delete('template_schedules', {'id': schedule_id})

    @classmethod
    def get_due_template_schedules(cls) -> List[Dict]:
        """Получить расписания готовые к публикации"""
        try:
            now = now_moscow()
            current_time = now.strftime('%H:%M')
            params = {
                'select': '*',
                'is_active': 'eq.true',
                'publish_time': f'eq.{current_time}'
            }
            response = requests.get(cls._api_url('template_schedules'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_due_template_schedules error: {e}")
            return []

    # ==================== TREND SNAPSHOTS (stub) ====================

    @classmethod
    def get_trend_snapshots(cls, user_id: int, limit: int = 10) -> List[Dict]:
        """Получить снимки трендов (заглушка - возвращает пустой список)"""
        # Тренды пока не реализованы, возвращаем пустой список
        return []
