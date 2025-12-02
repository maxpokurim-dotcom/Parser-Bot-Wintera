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
            user_id = task.get('owner_id') or task.get('user_id')
            
            # Check if system is paused
            if user_id and db.is_system_paused(user_id):
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
        source_id = task.get('source_id') or task['id']  # Use task id as source_id if not set
        account_id = task.get('account_id')
        user_id = task.get('owner_id') or task.get('user_id')
        
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
        """Parse channel/chat participants with filters"""
        task_id = task['id']
        source_id = task.get('source_id')
        phone = account['phone']
        account_id = account['id']
        
        # Get parsing filters from task
        filters = task.get('filters', {})
        only_with_username = filters.get('only_with_username', False)
        only_with_photo = filters.get('only_with_photo', False)
        exclude_bots = filters.get('exclude_bots', True)
        limit = task.get('limit', 0)  # 0 = no limit
        
        # Default limit if not set (prevent massive parsing)
        parse_limit = limit if limit > 0 else 10000
        
        self.logger.info(f"Parsing up to {parse_limit} users from {channel}")
        
        # Get all participants at once (Telethon handles pagination with aggressive=True)
        result = await telegram_actions.get_channel_participants(
            account_id,
            phone,
            channel,
            limit=parse_limit
        )
        
        if not result['success']:
            if result['error'] == 'flood_wait':
                wait_seconds = result.get('seconds', 60)
                self.logger.warning(f"FloodWait in parsing: {wait_seconds}s")
                db.set_account_flood_wait(account_id, wait_seconds)
            db.update_parsing_task(task_id, status='error', error=result['error'])
            return
        
        users = result['users']
        total_count = result.get('total', len(users))
        
        channel_type = result.get('channel_type', 'unknown')
        self.logger.info(f"Got {len(users)} users from {channel} (type: {channel_type}, total: {total_count})")
        
        # Warning for broadcast channels
        if channel_type == 'channel' and len(users) < 20:
            self.logger.warning(
                f"⚠️ {channel} is a BROADCAST CHANNEL! "
                f"Only admins visible ({len(users)} users). "
                f"For subscribers, use COMMENT parsing (source_type='comments')."
            )
        
        # Apply filters
        filtered_users = []
        for user in users:
            # Exclude bots filter
            if exclude_bots and user.get('is_bot'):
                continue
            
            # Only with username filter
            if only_with_username and not user.get('username'):
                continue
            
            # Only with photo filter
            if only_with_photo and not user.get('has_photo', True):
                continue
            
            filtered_users.append(user)
            
            # Check limit
            if limit > 0 and len(filtered_users) >= limit:
                break
        
        self.logger.info(f"After filters: {len(filtered_users)} users")
        
        # Save filtered users to database
        total_parsed = 0
        if source_id and filtered_users:
            total_parsed = db.add_audience_users(source_id, filtered_users)
        else:
            total_parsed = len(filtered_users)
        
        # Complete
        db.update_parsing_task(task_id, status='completed', parsed_count=total_parsed)
        
        if source_id:
            db.update_audience_source(source_id, status='completed', total_count=total_parsed)
        
        await notifier.notify_parsing_completed(source_id or task_id, total_parsed, channel)
        self.logger.info(f"Parsed {total_parsed} from {channel}")
    
    async def _parse_comments(self, task: dict, account: dict, channel: str):
        """Parse users from post comments"""
        task_id = task['id']
        source_id = task.get('source_id')
        phone = account['phone']
        account_id = account['id']
        post_limit = task.get('post_limit', 10)
        filters = task.get('filters', {})
        
        self.logger.info(f"Parsing comments from {channel}")
        
        # Get recent posts
        posts_result = await telegram_actions.get_channel_posts(
            account_id,
            phone, 
            channel,
            limit=post_limit
        )
        
        if not posts_result['success']:
            db.update_parsing_task(task_id, status='error', error=posts_result['error'])
            return
        
        posts = posts_result.get('posts', [])
        if not posts:
            db.update_parsing_task(task_id, status='completed', parsed_count=0)
            return
        
        total_parsed = 0
        users_collected = {}  # telegram_id -> user data (dedup)
        
        # Get client for comment parsing
        from services.telegram_client import client_manager
        client = await client_manager.get_client(account_id, phone)
        if not client:
            db.update_parsing_task(task_id, status='error', error='Client not available')
            return
        
        try:
            from telethon.tl.functions.messages import GetDiscussionMessageRequest, GetRepliesRequest
            
            channel_entity = await client.get_entity(channel)
            
            for post in posts:
                post_id = post['id']
                
                try:
                    # Try to get discussion/replies for the post
                    replies = await client(GetRepliesRequest(
                        peer=channel_entity,
                        msg_id=post_id,
                        offset_id=0,
                        offset_date=None,
                        add_offset=0,
                        limit=100,
                        max_id=0,
                        min_id=0,
                        hash=0
                    ))
                    
                    # Extract users from replies
                    for user in replies.users:
                        if user.bot:
                            if filters.get('exclude_bots', True):
                                continue
                        
                        if filters.get('only_with_username') and not user.username:
                            continue
                        
                        if user.id not in users_collected:
                            users_collected[user.id] = {
                                'telegram_id': user.id,
                                'username': user.username,
                                'first_name': user.first_name,
                                'last_name': user.last_name,
                                'is_premium': getattr(user, 'premium', False),
                                'is_bot': user.bot,
                                'has_photo': user.photo is not None
                            }
                    
                except Exception as e:
                    self.logger.debug(f"Could not get comments for post {post_id}: {e}")
                    continue
                
                # Small delay between posts
                await asyncio.sleep(1)
            
            # Apply additional filters
            filtered_users = []
            for user in users_collected.values():
                # Only with photo filter
                if filters.get('only_with_photo') and not user.get('has_photo'):
                    continue
                filtered_users.append(user)
            
            # Save users to database
            if source_id and filtered_users:
                added = db.add_audience_users(source_id, filtered_users)
                total_parsed = added
            else:
                total_parsed = len(filtered_users)
            
        except Exception as e:
            self.logger.error(f"Error parsing comments: {e}")
            db.update_parsing_task(task_id, status='error', error=str(e))
            return
        
        # Complete
        db.update_parsing_task(task_id, status='completed', parsed_count=total_parsed)
        
        if source_id:
            db.update_audience_source(source_id, status='completed', total_count=total_parsed)
        
        await notifier.notify_parsing_completed(source_id or task_id, total_parsed, f"комментарии {channel}")
        self.logger.info(f"Comment parsing completed: {total_parsed} users from {channel}")
