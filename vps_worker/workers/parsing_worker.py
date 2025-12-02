"""
Parsing Worker - Handles audience parsing from channels/chats
"""
import asyncio
from typing import List, Dict

from .base_worker import BaseWorker
from services.database import db
from services.notifier import notifier
from services.telegram_client import telegram_actions
from config import config
from utils.helpers import mask_phone, extract_username


class ParsingWorker(BaseWorker):
    """
    Processes parsing tasks to collect audience from:
    - Channels (subscribers)
    - Chats (members) 
    - Post comments
    """
    
    def __init__(self):
        super().__init__('parsing_worker')
    
    async def process(self):
        """Process pending parsing tasks"""
        tasks = db.get_pending_parsing_tasks()
        
        for task in tasks:
            task_id = task['id']
            user_id = task['user_id']
            
            # Check if system is paused
            if db.is_system_paused(user_id):
                continue
            
            try:
                await self._process_task(task)
            except Exception as e:
                self.logger.error(f"Error processing parsing task {task_id}: {e}")
                db.update_parsing_task(task_id, status='error', error=str(e))
    
    async def _process_task(self, task: dict):
        """Process single parsing task"""
        task_id = task['id']
        task_type = task.get('task_type', 'chat')  # chat or comments
        source_link = task['source_link']
        source_id = task.get('source_id')
        account_id = task.get('account_id')
        user_id = task['user_id']
        
        # Get account for parsing
        if not account_id:
            accounts = db.get_active_accounts(user_id)
            if not accounts:
                self.logger.error(f"No active accounts for user {user_id}")
                db.update_parsing_task(task_id, status='error', error='No active accounts')
                return
            account_id = accounts[0]['id']
        
        account = db.get_account(account_id)
        if not account:
            db.update_parsing_task(task_id, status='error', error='Account not found')
            return
        
        phone = account['phone']
        self.logger.info(f"Starting parsing task {task_id} for {source_link}")
        
        # Update status
        db.update_parsing_task(task_id, status='in_progress')
        
        # Extract channel/chat username
        channel = extract_username(source_link)
        if not channel:
            db.update_parsing_task(task_id, status='error', error='Invalid source link')
            return
        
        # Parse based on task type
        if task_type == 'comments':
            await self._parse_comments(task, account, channel)
        else:
            await self._parse_participants(task, account, channel)
    
    async def _parse_participants(self, task: dict, account: dict, channel: str):
        """Parse channel/chat participants"""
        task_id = task['id']
        source_id = task.get('source_id')
        phone = account['phone']
        account_id = account['id']
        batch_size = config.parsing.batch_size
        
        total_parsed = 0
        offset = 0
        
        while True:
            result = await telegram_actions.get_channel_participants(
                account_id,
                phone,
                channel,
                limit=batch_size,
                offset=offset
            )
            
            if not result['success']:
                if result['error'] == 'flood_wait':
                    # Wait and retry
                    wait_seconds = result.get('seconds', 60)
                    self.logger.warning(f"FloodWait in parsing: {wait_seconds}s")
                    db.set_account_flood_wait(account_id, wait_seconds)
                    await asyncio.sleep(wait_seconds)
                    continue
                else:
                    db.update_parsing_task(task_id, status='error', error=result['error'])
                    return
            
            users = result['users']
            if not users:
                break
            
            # Save users to database
            if source_id:
                added = db.add_audience_users(source_id, users)
                total_parsed += added
            else:
                total_parsed += len(users)
            
            # Update progress
            total_count = result.get('total', 0)
            db.update_parsing_task(
                task_id,
                parsed_count=total_parsed,
                total_count=total_count
            )
            
            self.logger.info(f"Parsed {total_parsed}/{total_count} from {channel}")
            
            # Check if done
            if len(users) < batch_size:
                break
            
            offset += batch_size
            
            # Delay between batches
            await asyncio.sleep(config.parsing.delay)
        
        # Complete
        db.update_parsing_task(task_id, status='completed', parsed_count=total_parsed)
        
        if source_id:
            db.update_audience_source(source_id, status='completed', total_count=total_parsed)
        
        await notifier.notify_parsing_completed(source_id or task_id, total_parsed, channel)
        self.logger.info(f"Parsing completed: {total_parsed} users from {channel}")
    
    async def _parse_comments(self, task: dict, account: dict, channel: str):
        """Parse users from post comments"""
        task_id = task['id']
        source_id = task.get('source_id')
        phone = account['phone']
        account_id = account['id']
        post_id = task.get('post_id')
        
        # Get recent posts if no specific post
        if not post_id:
            posts_result = await telegram_actions.get_channel_posts(
                account_id,
                phone, 
                channel,
                limit=10
            )
            
            if not posts_result['success']:
                db.update_parsing_task(task_id, status='error', error=posts_result['error'])
                return
            
            posts = posts_result['posts']
        else:
            posts = [{'id': post_id}]
        
        total_parsed = 0
        
        for post in posts:
            # Get comments for post
            # Note: This is simplified - actual implementation would need
            # to get discussion messages and extract users from them
            
            # For now, we'll mark as needing more complex implementation
            self.logger.info(f"Comment parsing for post {post['id']} - implementation pending")
        
        db.update_parsing_task(task_id, status='completed', parsed_count=total_parsed)
        self.logger.info(f"Comment parsing completed: {total_parsed} users")
