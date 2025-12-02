"""
Database service - Supabase client
Syncs with the Telegram bot on Vercel
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from supabase import create_client, Client
from config import config
from utils.logger import get_logger

logger = get_logger('database')


class Database:
    """Supabase database client"""
    
    def __init__(self):
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        """Lazy initialization of Supabase client"""
        if self._client is None:
            self._client = create_client(
                config.supabase.url,
                config.supabase.service_key or config.supabase.key
            )
        return self._client
    
    # ===========================================
    # ACCOUNTS
    # ===========================================
    
    def get_account(self, account_id: int) -> Optional[Dict]:
        """Get account by ID"""
        result = self.client.table('accounts').select('*').eq('id', account_id).execute()
        return result.data[0] if result.data else None
    
    def get_account_by_phone(self, user_id: int, phone: str) -> Optional[Dict]:
        """Get account by phone number"""
        result = self.client.table('accounts').select('*')\
            .eq('user_id', user_id).eq('phone', phone).execute()
        return result.data[0] if result.data else None
    
    def get_active_accounts(self, user_id: int) -> List[Dict]:
        """Get all active accounts for user"""
        result = self.client.table('accounts').select('*')\
            .eq('user_id', user_id).eq('status', 'active').execute()
        return result.data
    
    def get_accounts_for_mailing(self, account_ids: List[int]) -> List[Dict]:
        """Get accounts by IDs that are ready for mailing"""
        result = self.client.table('accounts').select('*')\
            .in_('id', account_ids).eq('status', 'active').execute()
        
        # Filter out accounts that reached daily limit
        ready = []
        for acc in result.data:
            daily_limit = acc.get('daily_limit') or 50
            daily_sent = acc.get('daily_sent') or 0
            if daily_sent < daily_limit:
                ready.append(acc)
        
        return ready
    
    def update_account(self, account_id: int, **kwargs) -> bool:
        """Update account fields"""
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            self.client.table('accounts').update(kwargs).eq('id', account_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating account {account_id}: {e}")
            return False
    
    def increment_account_sent(self, account_id: int) -> bool:
        """Increment daily sent counter"""
        try:
            # Get current value
            account = self.get_account(account_id)
            if not account:
                return False
            
            daily_sent = (account.get('daily_sent') or 0) + 1
            total_sent = (account.get('total_sent') or 0) + 1
            
            self.client.table('accounts').update({
                'daily_sent': daily_sent,
                'total_sent': total_sent,
                'last_activity': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', account_id).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error incrementing sent for account {account_id}: {e}")
            return False
    
    def record_account_error(self, account_id: int, error_type: str, error_message: str) -> bool:
        """Record account error and update reliability"""
        try:
            account = self.get_account(account_id)
            if not account:
                return False
            
            consecutive_errors = (account.get('consecutive_errors') or 0) + 1
            reliability = max(0, (account.get('reliability_score') or 100) - 5)
            
            update_data = {
                'consecutive_errors': consecutive_errors,
                'reliability_score': reliability,
                'last_error': error_message,
                'last_error_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Handle flood wait
            if error_type == 'flood_wait':
                update_data['status'] = 'flood_wait'
                update_data['flood_wait_count'] = (account.get('flood_wait_count') or 0) + 1
            
            # Pause account if too many errors
            if consecutive_errors >= config.worker.max_consecutive_errors:
                update_data['status'] = 'error'
                logger.warning(f"Account {account_id} paused due to {consecutive_errors} consecutive errors")
            
            self.client.table('accounts').update(update_data).eq('id', account_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error recording account error: {e}")
            return False
    
    def reset_account_errors(self, account_id: int) -> bool:
        """Reset consecutive errors after successful operation"""
        try:
            self.client.table('accounts').update({
                'consecutive_errors': 0,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', account_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error resetting account errors: {e}")
            return False
    
    def set_account_flood_wait(self, account_id: int, seconds: int) -> bool:
        """Set account flood wait status"""
        try:
            flood_until = (datetime.utcnow() + timedelta(seconds=seconds)).isoformat()
            self.client.table('accounts').update({
                'status': 'flood_wait',
                'flood_wait_until': flood_until,
                'flood_wait_count': self.client.rpc('increment', {'row_id': account_id, 'column_name': 'flood_wait_count'}),
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', account_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error setting flood wait: {e}")
            return False
    
    def get_accounts_in_folder(self, folder_id: int) -> List[Dict]:
        """Get all accounts in a folder"""
        result = self.client.table('accounts').select('*')\
            .eq('folder_id', folder_id).eq('status', 'active').execute()
        return result.data
    
    def get_accounts_without_folder(self, user_id: int) -> List[Dict]:
        """Get accounts without folder"""
        result = self.client.table('accounts').select('*')\
            .eq('user_id', user_id).is_('folder_id', 'null').eq('status', 'active').execute()
        return result.data
    
    # ===========================================
    # AUTH TASKS
    # ===========================================
    
    def get_pending_auth_tasks(self) -> List[Dict]:
        """Get pending authorization tasks"""
        result = self.client.table('auth_tasks').select('*')\
            .in_('status', ['pending', 'code_received']).execute()
        return result.data
    
    def update_auth_task(self, task_id: int, **kwargs) -> bool:
        """Update auth task"""
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            self.client.table('auth_tasks').update(kwargs).eq('id', task_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating auth task {task_id}: {e}")
            return False
    
    # ===========================================
    # CAMPAIGNS (Mailings)
    # ===========================================
    
    def get_active_campaigns(self, user_id: Optional[int] = None) -> List[Dict]:
        """Get active/running campaigns"""
        query = self.client.table('campaigns').select('*')\
            .in_('status', ['pending', 'running'])
        
        if user_id:
            query = query.eq('user_id', user_id)
        
        result = query.execute()
        return result.data
    
    def get_campaign(self, campaign_id: int) -> Optional[Dict]:
        """Get campaign by ID"""
        result = self.client.table('campaigns').select('*').eq('id', campaign_id).execute()
        return result.data[0] if result.data else None
    
    def update_campaign(self, campaign_id: int, **kwargs) -> bool:
        """Update campaign"""
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            self.client.table('campaigns').update(kwargs).eq('id', campaign_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating campaign {campaign_id}: {e}")
            return False
    
    def increment_campaign_sent(self, campaign_id: int) -> bool:
        """Increment campaign sent counter"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                return False
            
            sent_count = (campaign.get('sent_count') or 0) + 1
            total_count = campaign.get('total_count') or 0
            
            update = {
                'sent_count': sent_count,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Check if completed
            if total_count > 0 and sent_count >= total_count:
                update['status'] = 'completed'
                update['completed_at'] = datetime.utcnow().isoformat()
            
            self.client.table('campaigns').update(update).eq('id', campaign_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error incrementing campaign sent: {e}")
            return False
    
    def increment_campaign_failed(self, campaign_id: int) -> bool:
        """Increment campaign failed counter"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                return False
            
            self.client.table('campaigns').update({
                'failed_count': (campaign.get('failed_count') or 0) + 1,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', campaign_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error incrementing campaign failed: {e}")
            return False
    
    # ===========================================
    # AUDIENCE
    # ===========================================
    
    def get_audience_source(self, source_id: int) -> Optional[Dict]:
        """Get audience source"""
        result = self.client.table('audience_sources').select('*').eq('id', source_id).execute()
        return result.data[0] if result.data else None
    
    def update_audience_source(self, source_id: int, **kwargs) -> bool:
        """Update audience source"""
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            self.client.table('audience_sources').update(kwargs).eq('id', source_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating audience source: {e}")
            return False
    
    def get_audience_users(
        self, 
        source_id: int, 
        limit: int = 100, 
        exclude_sent: bool = True,
        exclude_stopped: bool = True
    ) -> List[Dict]:
        """Get audience users for mailing"""
        query = self.client.table('audience_users').select('*')\
            .eq('source_id', source_id)
        
        if exclude_sent:
            query = query.eq('is_sent', False)
        
        if exclude_stopped:
            query = query.eq('is_stopped', False)
        
        result = query.limit(limit).execute()
        return result.data
    
    def mark_user_sent(self, user_id: int, source_id: int) -> bool:
        """Mark audience user as sent"""
        try:
            self.client.table('audience_users').update({
                'is_sent': True,
                'sent_at': datetime.utcnow().isoformat()
            }).eq('telegram_id', user_id).eq('source_id', source_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking user sent: {e}")
            return False
    
    def add_audience_users(self, source_id: int, users: List[Dict]) -> int:
        """Add users to audience (batch insert)"""
        try:
            if not users:
                return 0
            
            # Prepare data
            rows = []
            for user in users:
                rows.append({
                    'source_id': source_id,
                    'telegram_id': user['telegram_id'],
                    'username': user.get('username'),
                    'first_name': user.get('first_name'),
                    'last_name': user.get('last_name'),
                    'is_premium': user.get('is_premium', False),
                    'is_bot': user.get('is_bot', False),
                    'created_at': datetime.utcnow().isoformat()
                })
            
            # Insert with upsert to handle duplicates
            result = self.client.table('audience_users').upsert(
                rows, 
                on_conflict='source_id,telegram_id'
            ).execute()
            
            return len(result.data)
        except Exception as e:
            logger.error(f"Error adding audience users: {e}")
            return 0
    
    # ===========================================
    # TEMPLATES
    # ===========================================
    
    def get_template(self, template_id: int) -> Optional[Dict]:
        """Get template by ID"""
        result = self.client.table('templates').select('*').eq('id', template_id).execute()
        return result.data[0] if result.data else None
    
    # ===========================================
    # PARSING TASKS
    # ===========================================
    
    def get_pending_parsing_tasks(self) -> List[Dict]:
        """Get pending parsing tasks"""
        result = self.client.table('parsing_tasks').select('*')\
            .in_('status', ['pending', 'in_progress'])\
            .order('created_at').execute()
        return result.data
    
    def update_parsing_task(self, task_id: int, **kwargs) -> bool:
        """Update parsing task"""
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            self.client.table('parsing_tasks').update(kwargs).eq('id', task_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating parsing task: {e}")
            return False
    
    # ===========================================
    # HERDER (Bot Activity)
    # ===========================================
    
    def get_active_herder_assignments(self) -> List[Dict]:
        """Get active herder assignments"""
        result = self.client.table('herder_assignments').select('*')\
            .eq('status', 'active').execute()
        return result.data
    
    def get_herder_assignment(self, assignment_id: int) -> Optional[Dict]:
        """Get herder assignment by ID"""
        result = self.client.table('herder_assignments').select('*')\
            .eq('id', assignment_id).execute()
        return result.data[0] if result.data else None
    
    def update_herder_assignment(self, assignment_id: int, **kwargs) -> bool:
        """Update herder assignment"""
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            self.client.table('herder_assignments').update(kwargs)\
                .eq('id', assignment_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating herder assignment: {e}")
            return False
    
    def log_herder_action(
        self, 
        assignment_id: int, 
        account_id: int, 
        action_type: str, 
        status: str,
        details: Optional[Dict] = None
    ) -> bool:
        """Log herder action"""
        try:
            self.client.table('herder_logs').insert({
                'assignment_id': assignment_id,
                'account_id': account_id,
                'action_type': action_type,
                'status': status,
                'details': json.dumps(details) if details else None,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error logging herder action: {e}")
            return False
    
    def get_monitored_channel(self, channel_id: int) -> Optional[Dict]:
        """Get monitored channel by ID"""
        result = self.client.table('monitored_channels').select('*')\
            .eq('id', channel_id).execute()
        return result.data[0] if result.data else None
    
    # ===========================================
    # FACTORY TASKS
    # ===========================================
    
    def get_pending_factory_tasks(self) -> List[Dict]:
        """Get pending factory tasks"""
        result = self.client.table('factory_tasks').select('*')\
            .in_('status', ['pending', 'in_progress']).execute()
        return result.data
    
    def update_factory_task(self, task_id: int, **kwargs) -> bool:
        """Update factory task"""
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            self.client.table('factory_tasks').update(kwargs).eq('id', task_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating factory task: {e}")
            return False
    
    # ===========================================
    # WARMUP
    # ===========================================
    
    def get_accounts_for_warmup(self) -> List[Dict]:
        """Get accounts that need warmup"""
        result = self.client.table('accounts').select('*, warmup_progress(*)')\
            .eq('warmup_status', 'in_progress').execute()
        return result.data
    
    def get_warmup_progress(self, account_id: int) -> Optional[Dict]:
        """Get warmup progress for account"""
        result = self.client.table('warmup_progress').select('*')\
            .eq('account_id', account_id).execute()
        return result.data[0] if result.data else None
    
    def update_warmup_progress(self, account_id: int, **kwargs) -> bool:
        """Update warmup progress"""
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            self.client.table('warmup_progress').update(kwargs)\
                .eq('account_id', account_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating warmup progress: {e}")
            return False
    
    # ===========================================
    # SCHEDULED TASKS
    # ===========================================
    
    def get_due_scheduled_mailings(self) -> List[Dict]:
        """Get scheduled mailings that are due"""
        now = datetime.utcnow().isoformat()
        result = self.client.table('scheduled_mailings').select('*')\
            .eq('status', 'pending')\
            .lte('scheduled_at', now).execute()
        return result.data
    
    def get_due_scheduled_tasks(self) -> List[Dict]:
        """Get scheduled tasks that are due"""
        now = datetime.utcnow().isoformat()
        result = self.client.table('scheduled_tasks').select('*')\
            .eq('status', 'pending')\
            .lte('scheduled_at', now).execute()
        return result.data
    
    def update_scheduled_mailing(self, mailing_id: int, **kwargs) -> bool:
        """Update scheduled mailing"""
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            self.client.table('scheduled_mailings').update(kwargs)\
                .eq('id', mailing_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating scheduled mailing: {e}")
            return False
    
    def update_scheduled_task(self, task_id: int, **kwargs) -> bool:
        """Update scheduled task"""
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            self.client.table('scheduled_tasks').update(kwargs)\
                .eq('id', task_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating scheduled task: {e}")
            return False
    
    # ===========================================
    # USER SETTINGS
    # ===========================================
    
    def get_user_settings(self, user_id: int) -> Dict:
        """Get user settings"""
        result = self.client.table('user_settings').select('*')\
            .eq('user_id', user_id).execute()
        return result.data[0] if result.data else {}
    
    def is_system_paused(self, user_id: int) -> bool:
        """Check if system is paused for user"""
        settings = self.get_user_settings(user_id)
        return settings.get('system_paused', False)
    
    # ===========================================
    # STOP LIST
    # ===========================================
    
    def is_in_stop_list(self, user_id: int, telegram_id: int) -> bool:
        """Check if telegram user is in stop list"""
        result = self.client.table('stop_list').select('id')\
            .eq('user_id', user_id).eq('telegram_id', telegram_id).execute()
        return len(result.data) > 0
    
    def add_to_stop_list(self, user_id: int, telegram_id: int, reason: str = 'manual') -> bool:
        """Add user to stop list"""
        try:
            self.client.table('stop_list').upsert({
                'user_id': user_id,
                'telegram_id': telegram_id,
                'reason': reason,
                'created_at': datetime.utcnow().isoformat()
            }, on_conflict='user_id,telegram_id').execute()
            return True
        except Exception as e:
            logger.error(f"Error adding to stop list: {e}")
            return False
    
    # ===========================================
    # ACCOUNT PROFILES
    # ===========================================
    
    def get_account_profile(self, account_id: int) -> Optional[Dict]:
        """Get AI profile for account"""
        result = self.client.table('account_profiles').select('*')\
            .eq('account_id', account_id).execute()
        return result.data[0] if result.data else None


# Global database instance
db = Database()
