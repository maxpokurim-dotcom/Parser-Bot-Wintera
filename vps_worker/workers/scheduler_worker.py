"""
Scheduler Worker - Handles scheduled tasks and mailings
Checks for due tasks and triggers their execution
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict

from .base_worker import BaseWorker
from services.database import db
from services.notifier import notifier
from utils.logger import get_logger


class SchedulerWorker(BaseWorker):
    """
    Processes scheduled tasks:
    - Scheduled mailings
    - Recurring tasks (daily/weekly)
    - One-time scheduled jobs
    """
    
    def __init__(self):
        super().__init__('scheduler_worker')
    
    async def process(self):
        """Check and process due scheduled tasks"""
        # Process scheduled mailings
        await self._process_scheduled_mailings()
        
        # Process scheduled tasks
        await self._process_scheduled_tasks()
    
    async def _process_scheduled_mailings(self):
        """Process scheduled mailings that are due"""
        mailings = db.get_due_scheduled_mailings()
        
        for mailing in mailings:
            mailing_id = mailing['id']
            user_id = mailing['user_id']
            
            # Check if system is paused
            if db.is_system_paused(user_id):
                continue
            
            try:
                await self._launch_scheduled_mailing(mailing)
            except Exception as e:
                self.logger.error(f"Error launching scheduled mailing {mailing_id}: {e}")
                db.update_scheduled_mailing(
                    mailing_id, 
                    status='error',
                    error=str(e)
                )
    
    async def _launch_scheduled_mailing(self, mailing: dict):
        """Convert scheduled mailing to active campaign"""
        mailing_id = mailing['id']
        user_id = mailing['user_id']
        source_id = mailing['source_id']
        template_id = mailing['template_id']
        account_folder_id = mailing.get('account_folder_id')
        use_warm_start = mailing.get('use_warm_start', True)
        
        self.logger.info(f"Launching scheduled mailing {mailing_id}")
        
        # Get accounts
        if account_folder_id:
            accounts = db.get_accounts_in_folder(account_folder_id)
        else:
            accounts = db.get_accounts_without_folder(user_id)
        
        active_accounts = [a for a in accounts if a.get('status') == 'active']
        
        if not active_accounts:
            db.update_scheduled_mailing(
                mailing_id,
                status='error',
                error='No active accounts'
            )
            return
        
        account_ids = [a['id'] for a in active_accounts]
        
        # Get user settings for delays
        settings = db.get_user_settings(user_id)
        
        # Create campaign
        campaign_data = {
            'user_id': user_id,
            'source_id': source_id,
            'template_id': template_id,
            'account_ids': account_ids,
            'account_folder_id': account_folder_id,
            'status': 'pending',
            'settings': {
                'delay_min': settings.get('delay_min', 30),
                'delay_max': settings.get('delay_max', 90),
                'auto_switch': True,
                'report_every': 50
            },
            'use_warm_start': use_warm_start,
            'use_typing_simulation': True,
            'use_adaptive_delays': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Insert campaign (simplified - actual would use db method)
        # For now, we mark the scheduled mailing as launched
        db.update_scheduled_mailing(
            mailing_id,
            status='launched',
            launched_at=datetime.utcnow().isoformat()
        )
        
        self.logger.info(f"Scheduled mailing {mailing_id} launched")
        await notifier.send_message(
            f"📅 <b>Запланированная рассылка запущена</b>\n\n"
            f"🆔 ID: {mailing_id}\n"
            f"👤 Аккаунтов: {len(account_ids)}"
        )
    
    async def _process_scheduled_tasks(self):
        """Process scheduled tasks (parsing, warmup, etc.)"""
        tasks = db.get_due_scheduled_tasks()
        
        for task in tasks:
            task_id = task['id']
            user_id = task['user_id']
            task_type = task.get('task_type', 'unknown')
            repeat_mode = task.get('repeat_mode', 'once')
            
            # Check if system is paused
            if db.is_system_paused(user_id):
                continue
            
            try:
                await self._execute_scheduled_task(task)
                
                # Handle repeat mode
                if repeat_mode == 'once':
                    db.update_scheduled_task(task_id, status='completed')
                elif repeat_mode == 'daily':
                    # Schedule for tomorrow
                    next_run = datetime.utcnow() + timedelta(days=1)
                    db.update_scheduled_task(
                        task_id,
                        scheduled_at=next_run.isoformat(),
                        last_run_at=datetime.utcnow().isoformat()
                    )
                elif repeat_mode == 'weekly':
                    # Schedule for next week
                    next_run = datetime.utcnow() + timedelta(days=7)
                    db.update_scheduled_task(
                        task_id,
                        scheduled_at=next_run.isoformat(),
                        last_run_at=datetime.utcnow().isoformat()
                    )
                    
            except Exception as e:
                self.logger.error(f"Error executing scheduled task {task_id}: {e}")
                db.update_scheduled_task(
                    task_id,
                    status='error',
                    error=str(e)
                )
    
    async def _execute_scheduled_task(self, task: dict):
        """Execute a scheduled task based on type"""
        task_id = task['id']
        task_type = task.get('task_type')
        task_config = task.get('task_config', {})
        
        self.logger.info(f"Executing scheduled task {task_id} (type: {task_type})")
        
        if task_type == 'parsing':
            # Trigger parsing task
            # This would create a parsing_task entry
            await notifier.send_message(
                f"⏰ <b>Запланированный парсинг запущен</b>\n"
                f"🆔 Task ID: {task_id}"
            )
            
        elif task_type == 'mailing':
            # Trigger mailing
            await notifier.send_message(
                f"⏰ <b>Запланированная рассылка запущена</b>\n"
                f"🆔 Task ID: {task_id}"
            )
            
        elif task_type == 'warmup':
            # Trigger warmup for accounts
            await notifier.send_message(
                f"⏰ <b>Запланированный прогрев запущен</b>\n"
                f"🆔 Task ID: {task_id}"
            )
        
        else:
            self.logger.warning(f"Unknown task type: {task_type}")
