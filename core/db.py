"""
Supabase Database Client - Extended Version v2.0
With Smart Account Distribution, Keyword Filters, Warmup, Cache TTL,
Stop Triggers, Panic Stop, Hourly Stats, and more.
"""

import os
import logging
import requests
import time
from typing import Optional, List, Dict, Any, Set, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class DB:
    """Supabase REST API Client - Extended"""

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
            'delay_max': 90,
            'mailing_cache_ttl': 30,
            'auto_blacklist_enabled': True,
            'warmup_before_mailing': False,
            'warmup_duration_minutes': 5,
            'use_smart_scheduling': True,
            'preferred_hours_start': 10,
            'preferred_hours_end': 22,
            'panic_stop_enabled': False
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
        """Активировать экстренную остановку"""
        auto_resume = None
        if auto_resume_minutes:
            auto_resume = (datetime.utcnow() + timedelta(minutes=auto_resume_minutes)).isoformat()
        
        data = {
            'owner_id': user_id,
            'is_paused': True,
            'pause_reason': reason,
            'paused_at': datetime.utcnow().isoformat(),
            'auto_resume_at': auto_resume,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        existing = cls._select('system_status', filters={'owner_id': user_id}, single=True)
        if existing:
            return cls._update('system_status', data, {'owner_id': user_id})
        else:
            data['created_at'] = datetime.utcnow().isoformat()
            return cls._insert('system_status', data) is not None

    @classmethod
    def clear_panic_stop(cls, user_id: int) -> bool:
        """Снять экстренную остановку"""
        return cls._update('system_status', {
            'is_paused': False,
            'pause_reason': None,
            'paused_at': None,
            'auto_resume_at': None,
            'updated_at': datetime.utcnow().isoformat()
        }, {'owner_id': user_id})

    @classmethod
    def is_system_paused(cls, user_id: int) -> bool:
        """Проверить, активна ли экстренная остановка"""
        status = cls.get_system_status(user_id)
        if not status.get('is_paused'):
            return False
        
        # Проверить auto_resume
        auto_resume = status.get('auto_resume_at')
        if auto_resume:
            try:
                resume_time = datetime.fromisoformat(auto_resume.replace('Z', '+00:00'))
                if datetime.utcnow() >= resume_time.replace(tzinfo=None):
                    cls.clear_panic_stop(user_id)
                    return False
            except:
                pass
        
        return True

    # ==================== STOP TRIGGERS ====================

    @classmethod
    def get_stop_triggers(cls, user_id: int) -> List[Dict]:
        triggers = cls._select('stop_triggers', filters={'owner_id': user_id, 'is_active': True})
        if not triggers:
            # Создать дефолтные при первом запросе
            cls._create_default_stop_triggers(user_id)
            triggers = cls._select('stop_triggers', filters={'owner_id': user_id, 'is_active': True})
        return triggers or []

    @classmethod
    def _create_default_stop_triggers(cls, user_id: int):
        """Создать дефолтные стоп-слова"""
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
                'created_at': datetime.utcnow().isoformat()
            })

    @classmethod
    def add_stop_trigger(cls, user_id: int, trigger_word: str, action: str = 'blacklist') -> Optional[Dict]:
        return cls._insert('stop_triggers', {
            'owner_id': user_id,
            'trigger_word': trigger_word.lower().strip(),
            'action': action,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def delete_stop_trigger(cls, trigger_id: int) -> bool:
        return cls._delete('stop_triggers', {'id': trigger_id})

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
        """Проверить, был ли пользователь в рассылке за последние N дней"""
        try:
            cutoff = (datetime.utcnow() - timedelta(days=ttl_days)).isoformat()
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
        """Добавить пользователя в кэш рассылки"""
        data = {
            'owner_id': user_id,
            'target_user_id': target_user_id,
            'target_username': target_username,
            'campaign_id': campaign_id,
            'ttl_days': ttl_days,
            'last_sent_at': datetime.utcnow().isoformat()
        }
        return cls._upsert('mailing_cache', data) is not None

    @classmethod
    def cleanup_mailing_cache(cls, user_id: int = None) -> int:
        """Очистить устаревший кэш"""
        try:
            # Это лучше делать через SQL function на стороне Supabase
            # Здесь упрощённая версия
            return 0
        except Exception as e:
            logger.error(f"cleanup_mailing_cache error: {e}")
            return 0

    # ==================== HOURLY STATS ====================

    @classmethod
    def update_hourly_stats(cls, user_id: int, sent: int = 0, success: int = 0, 
                           failed: int = 0, flood_waits: int = 0) -> bool:
        """Обновить почасовую статистику"""
        now = datetime.utcnow()
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
        """Получить почасовую статистику"""
        return cls._select('hourly_stats', filters={'owner_id': user_id}, order='hour.asc')

    @classmethod
    def get_best_hours(cls, user_id: int, limit: int = 5) -> List[int]:
        """Получить лучшие часы для рассылки (меньше ошибок)"""
        stats = cls.get_hourly_stats(user_id)
        if not stats:
            return list(range(10, 22))  # Дефолт: 10:00 - 22:00
        
        # Сортируем по успешности
        sorted_stats = sorted(stats, key=lambda x: (
            x.get('total_success', 0) / max(x.get('total_sent', 1), 1)
        ), reverse=True)
        
        return [s['hour'] for s in sorted_stats[:limit]]

    @classmethod
    def get_delay_multiplier_for_hour(cls, user_id: int, hour: int = None) -> float:
        """Получить множитель задержки для текущего часа"""
        if hour is None:
            hour = datetime.utcnow().hour
        
        stats = cls._select('hourly_stats', 
            filters={'owner_id': user_id, 'hour': hour}, 
            single=True)
        
        if not stats:
            return 1.0
        
        total = stats.get('total_sent', 0) or 1
        flood_waits = stats.get('total_flood_waits', 0) or 0
        
        # Если много flood waits в этот час - увеличиваем задержку
        flood_rate = flood_waits / total
        if flood_rate > 0.1:  # >10% flood waits
            return 2.0
        elif flood_rate > 0.05:  # >5%
            return 1.5
        elif flood_rate < 0.01:  # <1%
            return 0.8
        
        return 1.0

    # ==================== SMART ACCOUNT DISTRIBUTION ====================

    @classmethod
    def get_best_account_for_mailing(cls, user_id: int, account_ids: List[int] = None,
                                     folder_id: int = None) -> Optional[Dict]:
        """
        Умный выбор аккаунта для рассылки:
        - Учитывает остаток дневного лимита
        - Статус (active/flood_wait)
        - Историю ошибок (reliability_score)
        - Время последнего flood_wait
        """
        try:
            # Базовый запрос
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
            
            # Фильтруем по account_ids если указаны
            if account_ids:
                accounts = [a for a in accounts if a['id'] in account_ids]
            
            # Находим лучший аккаунт
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
                
                # Формула оценки: остаток * надёжность - штраф за ошибки
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
        """Обновить статистику аккаунта после отправки"""
        account = cls._select('telegram_accounts', filters={'id': account_id}, single=True)
        if not account:
            return False
        
        updates = {
            'daily_sent': (account.get('daily_sent', 0) or 0) + sent,
            'total_sent_today': (account.get('total_sent_today', 0) or 0) + sent,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if success:
            updates['last_success_at'] = datetime.utcnow().isoformat()
            updates['consecutive_errors'] = 0
            # Увеличиваем reliability если всё хорошо
            current_reliability = account.get('reliability_score', 100) or 100
            updates['reliability_score'] = min(100, current_reliability + 0.1)
        else:
            updates['last_error_at'] = datetime.utcnow().isoformat()
            updates['consecutive_errors'] = (account.get('consecutive_errors', 0) or 0) + 1
            updates['total_errors_today'] = (account.get('total_errors_today', 0) or 0) + 1
            # Уменьшаем reliability при ошибках
            current_reliability = account.get('reliability_score', 100) or 100
            penalty = 5 if error_type == 'flood_wait' else 2
            updates['reliability_score'] = max(0, current_reliability - penalty)
        
        if flood_wait_seconds > 0:
            updates['status'] = 'flood_wait'
            updates['flood_wait_until'] = (datetime.utcnow() + timedelta(seconds=flood_wait_seconds)).isoformat()
            updates['error_message'] = f'Flood wait: {flood_wait_seconds}s'
        
        return cls._update('telegram_accounts', updates, {'id': account_id})

    @classmethod
    def get_account_limit_prediction(cls, account_id: int) -> Dict:
        """Прогноз лимитов на 24 часа"""
        account = cls._select('telegram_accounts', filters={'id': account_id}, single=True)
        if not account:
            return {'error': 'Account not found'}
        
        daily_limit = account.get('daily_limit', 50) or 50
        daily_sent = account.get('daily_sent', 0) or 0
        remaining = max(0, daily_limit - daily_sent)
        
        # Получаем историю за последние 7 дней
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        history = cls._select('account_limits_history', 
            filters={'account_id': account_id},
            raw_filters={'date': f'gte.{week_ago[:10]}'},
            order='date.desc,hour.desc',
            limit=168)  # 7 дней * 24 часа
        
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
        """Генерация рекомендации по аккаунту"""
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
        """Создать запланированную задачу"""
        return cls._insert('scheduled_tasks', {
            'owner_id': user_id,
            'task_type': task_type,
            'task_config': task_config,
            'scheduled_at': scheduled_at.isoformat(),
            'repeat_mode': repeat_mode,
            'repeat_days': repeat_days or [],
            'status': 'pending',
            'next_run_at': scheduled_at.isoformat(),
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def get_scheduled_tasks(cls, user_id: int, status: str = None) -> List[Dict]:
        filters = {'owner_id': user_id}
        if status:
            filters['status'] = status
        return cls._select('scheduled_tasks', filters=filters, order='scheduled_at.asc')

    @classmethod
    def get_due_scheduled_tasks(cls) -> List[Dict]:
        """Получить задачи, готовые к выполнению"""
        try:
            now = datetime.utcnow().isoformat()
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
        kwargs['updated_at'] = datetime.utcnow().isoformat()
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
            'created_at': datetime.utcnow().isoformat()
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
            'executed_at': datetime.utcnow().isoformat()
        }
        if error:
            data['error'] = error
        return cls._update('warmup_activities', data, {'id': activity_id})

    @classmethod
    def mark_account_warmup_complete(cls, account_id: int) -> bool:
        return cls._update('telegram_accounts', {
            'warmup_completed': True,
            'is_warming_up': False,
            'updated_at': datetime.utcnow().isoformat()
        }, {'id': account_id})

    @classmethod
    def start_account_warmup(cls, account_id: int) -> bool:
        return cls._update('telegram_accounts', {
            'is_warming_up': True,
            'warmup_started_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
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
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def get_negative_responses(cls, user_id: int, days: int = 7) -> List[Dict]:
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
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

    # ==================== STORAGE (без изменений) ====================

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
            'created_at': datetime.utcnow().isoformat()
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
            'created_at': datetime.utcnow().isoformat()
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
        kwargs['updated_at'] = datetime.utcnow().isoformat()
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
            {'folder_id': folder_id, 'updated_at': datetime.utcnow().isoformat()}, 
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
            'owner_id': user_id, 'name': name, 'created_at': datetime.utcnow().isoformat()
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
            'owner_id': user_id, 'name': name, 'created_at': datetime.utcnow().isoformat()
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
            data = {'folder_id': None, 'updated_at': datetime.utcnow().isoformat()}
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
    def update_account(cls, account_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        return cls._update('telegram_accounts', kwargs, {'id': account_id})

    @classmethod
    def delete_account(cls, account_id: int) -> bool:
        account = cls._select('telegram_accounts', filters={'id': account_id}, single=True)
        if not account:
            return False
        user_id = account.get('owner_id')
        phone = account.get('phone')
        cls._delete('campaigns', {'current_account_id': account_id})
        cls._delete('sent_messages', {'account_id': account_id})
        cls._delete('warmup_activities', {'account_id': account_id})
        cls._delete('account_limits_history', {'account_id': account_id})
        if user_id and phone:
            cls._delete('auth_tasks', {'owner_id': user_id, 'phone': phone})
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
            'created_at': datetime.utcnow().isoformat()
        }
        if keyword_filter:
            data['keyword_filter'] = keyword_filter
            data['keyword_match_mode'] = keyword_match_mode
        return cls._insert('audience_sources', data)

    @classmethod
    def update_audience_source(cls, source_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        return cls._update('audience_sources', kwargs, {'id': source_id})

    @classmethod
    def delete_audience_source(cls, source_id: int) -> bool:
        source = cls._select('audience_sources', filters={'id': source_id}, single=True)
        if not source:
            return False
        cls._delete('campaigns', {'source_id': source_id})
        cls._delete('scheduled_mailings', {'source_id': source_id})
        cls._delete('parsed_audiences', {'source_id': source_id})
        cls._delete('keyword_filters', {'source_id': source_id})
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
        """Получить неотправленных пользователей с проверкой кэша"""
        users = cls.get_unsent_users(source_id, limit=limit * 2)  # Берём с запасом
        
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
            'sent_at': datetime.utcnow().isoformat(),
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
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def remove_from_blacklist(cls, blacklist_id: int) -> bool:
        return cls._delete('blacklist', {'id': blacklist_id})

    @classmethod
    def is_in_blacklist(cls, user_id: int, tg_user_id: int = None, username: str = None) -> bool:
        """Проверить, есть ли пользователь в чёрном списке"""
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
                       use_typing: bool = True, use_adaptive: bool = True) -> Optional[Dict]:
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
            'use_warm_start': use_warm_start,
            'warm_start_count': 10,
            'use_typing_simulation': use_typing,
            'use_adaptive_delays': use_adaptive,
            'use_time_optimization': True,
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
            response = requests.get(cls._api_url('campaigns'), 
                                   headers=cls._headers(), params=params, timeout=10)
            return response.json() if response.ok else []
        except Exception as e:
            logger.error(f"get_active_campaigns error: {e}")
            return []

    @classmethod
    def get_pending_campaigns(cls, limit: int = 5) -> List[Dict]:
        return cls._select('campaigns', filters={'status': 'pending'}, 
                          order='created_at.asc', limit=limit)

    @classmethod
    def get_running_campaigns(cls) -> List[Dict]:
        return cls._select('campaigns', filters={'status': 'running'})

    @classmethod
    def update_campaign(cls, campaign_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = datetime.utcnow().isoformat()
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
    def pause_all_campaigns(cls, user_id: int, reason: str = 'Panic stop') -> int:
        """Приостановить все активные кампании пользователя"""
        try:
            params = {
                'owner_id': f'eq.{user_id}',
                'status': 'in.(pending,running)'
            }
            data = {
                'status': 'paused',
                'pause_reason': reason,
                'updated_at': datetime.utcnow().isoformat()
            }
            response = requests.patch(cls._api_url('campaigns'),
                headers=cls._headers(), json=data, params=params, timeout=10)
            return 1 if response.ok else 0
        except Exception as e:
            logger.error(f"pause_all_campaigns error: {e}")
            return 0

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
            'account_id': 0,  # Будет выбран автоматически
            'scheduled_at': scheduled_at.isoformat() if scheduled_at else None,
            'status': 'pending',
            'use_warm_start': use_warm_start,
            'created_at': datetime.utcnow().isoformat()
        })

    @classmethod
    def get_scheduled_mailings(cls, user_id: int) -> List[Dict]:
        return cls._select('scheduled_mailings', filters={'owner_id': user_id}, 
                          order='scheduled_at.asc')

    @classmethod
    def get_due_scheduled_mailings(cls) -> List[Dict]:
        try:
            now = datetime.utcnow().isoformat()
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
        kwargs['updated_at'] = datetime.utcnow().isoformat()
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
                'sent_at': datetime.utcnow().isoformat()
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
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
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
        flood_until = (datetime.utcnow() + timedelta(seconds=wait_seconds)).isoformat()
        return cls.update_account(account_id,
            status='flood_wait',
            flood_wait_until=flood_until,
            error_message=f'Flood wait: {wait_seconds}s')

    @classmethod
    def get_accounts_ready_after_flood(cls) -> List[Dict]:
        try:
            now = datetime.utcnow().isoformat()
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
