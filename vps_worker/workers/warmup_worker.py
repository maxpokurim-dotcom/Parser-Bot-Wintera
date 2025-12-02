"""
Warmup Worker - Account warmup process
Gradually increases account activity to build trust
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .base_worker import BaseWorker
from services.database import db
from services.notifier import notifier
from services.telegram_client import telegram_actions, client_manager
from config import config
from utils.helpers import mask_phone


# Channels to join during warmup (public, safe channels)
WARMUP_CHANNELS = [
    'telegram',
    'durov',
    'telegram_rus',
    'TGnews',
    'tginfo',
    # Add more safe public channels
]


class WarmupWorker(BaseWorker):
    """
    Handles account warmup to build trust with Telegram
    
    Warmup types:
    - standard: Regular 5-day warmup
    - warm_account: 2-day warm account warmup with AI profile
    
    Warmup stages:
    Day 1-2: Profile setup, join channels
    Day 3-5: Read messages, rare reactions  
    Day 6-7: More reactions, simple activity
    Day 8+: Ready for work
    """
    
    def __init__(self):
        super().__init__('warmup_worker')
    
    async def process(self):
        """Process accounts that need warmup"""
        accounts = db.get_accounts_for_warmup()
        
        for account_data in accounts:
            account = account_data
            
            try:
                # Check warmup type
                warmup_type = account.get('warmup_type', 'standard')
                
                if warmup_type == 'warm_account':
                    await self._process_warm_account_warmup(account)
                else:
                    await self._process_warmup(account)
                    
            except Exception as e:
                self.logger.error(f"Error in warmup for account {account['id']}: {e}")
    
    async def _process_warmup(self, account: dict):
        """Process warmup for single account"""
        account_id = account['id']
        phone = account['phone']
        user_id = account['user_id']
        
        # Check if system is paused
        if db.is_system_paused(user_id):
            return
        
        # Get warmup progress
        progress = db.get_warmup_progress(account_id)
        if not progress:
            return
        
        current_day = progress.get('current_day', 1)
        total_days = progress.get('total_days', 5)
        status = progress.get('status', 'pending')
        
        if status != 'in_progress':
            return
        
        # Check if already did actions today
        last_action = progress.get('last_action_at')
        if last_action:
            try:
                last_dt = datetime.fromisoformat(last_action.replace('Z', '+00:00'))
                if last_dt.date() == datetime.utcnow().date():
                    return  # Already did warmup today
            except:
                pass
        
        self.logger.info(f"Warmup day {current_day}/{total_days} for {mask_phone(phone)}")
        
        # Execute warmup actions based on day
        if current_day <= 2:
            await self._warmup_stage_1(account_id, phone)
        elif current_day <= 5:
            await self._warmup_stage_2(account_id, phone)
        else:
            await self._warmup_stage_3(account_id, phone)
        
        # Update progress
        completed_actions = progress.get('completed_actions', [])
        completed_actions.append({
            'day': current_day,
            'action': f'warmup_day_{current_day}',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Check if warmup completed
        if current_day >= total_days:
            db.update_warmup_progress(
                account_id,
                status='completed',
                completed_actions=completed_actions,
                last_action_at=datetime.utcnow().isoformat()
            )
            db.update_account(account_id, warmup_status='completed')
            self.logger.info(f"Warmup completed for {mask_phone(phone)}")
        else:
            # Move to next day
            db.update_warmup_progress(
                account_id,
                current_day=current_day + 1,
                completed_actions=completed_actions,
                last_action_at=datetime.utcnow().isoformat()
            )
    
    async def _warmup_stage_1(self, account_id: int, phone: str):
        """
        Stage 1 (Day 1-2): Profile setup and joining channels
        """
        self.logger.debug(f"Warmup stage 1 for {mask_phone(phone)}")
        
        # Join some public channels
        channels = random.sample(WARMUP_CHANNELS, min(3, len(WARMUP_CHANNELS)))
        
        for channel in channels:
            result = await telegram_actions.join_channel(account_id, phone, channel)
            if result['success']:
                self.logger.debug(f"Joined @{channel}")
            await asyncio.sleep(random.randint(30, 120))
    
    async def _warmup_stage_2(self, account_id: int, phone: str):
        """
        Stage 2 (Day 3-5): Reading and rare reactions
        """
        self.logger.debug(f"Warmup stage 2 for {mask_phone(phone)}")
        
        # Get posts from joined channels
        channel = random.choice(WARMUP_CHANNELS)
        
        posts_result = await telegram_actions.get_channel_posts(
            account_id, phone, channel, limit=5
        )
        
        if posts_result['success'] and posts_result.get('posts'):
            # React to 1-2 posts
            posts = random.sample(
                posts_result['posts'], 
                min(2, len(posts_result['posts']))
            )
            
            for post in posts:
                # Small chance to react
                if random.random() < 0.3:
                    emoji = random.choice(['👍', '❤️', '🔥'])
                    await telegram_actions.send_reaction(
                        account_id, phone, channel, post['id'], emoji
                    )
                await asyncio.sleep(random.randint(60, 300))
    
    async def _warmup_stage_3(self, account_id: int, phone: str):
        """
        Stage 3 (Day 6+): More active behavior
        """
        self.logger.debug(f"Warmup stage 3 for {mask_phone(phone)}")
        
        # More reactions
        channel = random.choice(WARMUP_CHANNELS)
        
        posts_result = await telegram_actions.get_channel_posts(
            account_id, phone, channel, limit=10
        )
        
        if posts_result['success'] and posts_result.get('posts'):
            posts = random.sample(
                posts_result['posts'],
                min(4, len(posts_result['posts']))
            )
            
            for post in posts:
                # Higher chance to react
                if random.random() < 0.5:
                    emoji = random.choice(['👍', '❤️', '🔥', '👏', '🎉'])
                    await telegram_actions.send_reaction(
                        account_id, phone, channel, post['id'], emoji
                    )
                await asyncio.sleep(random.randint(30, 180))
    
    async def _process_warm_account_warmup(self, account: dict):
        """Process warm account warmup (shorter 2-day cycle)"""
        account_id = account['id']
        phone = account['phone']
        user_id = account.get('owner_id')
        target_folder_id = account.get('target_folder_id')
        
        # Check if system is paused
        if db.is_system_paused(user_id):
            return
        
        # Get warmup progress
        progress = db.get_warmup_progress(account_id)
        if not progress:
            # Create progress entry for warm account
            db.client.table('warmup_progress').insert({
                'account_id': account_id,
                'warmup_type': 'warm_account',
                'total_days': 2,
                'current_day': 1,
                'status': 'in_progress',
                'started_at': datetime.utcnow().isoformat()
            }).execute()
            progress = db.get_warmup_progress(account_id)
        
        if not progress:
            return
        
        current_day = progress.get('current_day', 1)
        total_days = progress.get('total_days', 2)
        status = progress.get('status', 'pending')
        
        if status != 'in_progress':
            return
        
        # Check if already did actions today
        last_action = progress.get('last_action_at')
        if last_action:
            try:
                last_dt = datetime.fromisoformat(last_action.replace('Z', '+00:00'))
                if last_dt.date() == datetime.utcnow().date():
                    return  # Already did warmup today
            except:
                pass
        
        self.logger.info(f"Warm account warmup day {current_day}/{total_days} for {mask_phone(phone)}")
        
        # Execute warmup actions (more intensive for warm accounts)
        await self._warm_account_day_actions(account_id, phone, current_day)
        
        # Update progress
        completed_actions = progress.get('completed_actions', [])
        completed_actions.append({
            'day': current_day,
            'action': f'warm_account_day_{current_day}',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Check if warmup completed
        if current_day >= total_days:
            db.update_warmup_progress(
                account_id,
                status='completed',
                completed_actions=completed_actions,
                last_action_at=datetime.utcnow().isoformat()
            )
            
            # Move to warm accounts folder if specified
            update_data = {'warmup_status': 'completed'}
            if target_folder_id:
                update_data['folder_id'] = target_folder_id
            
            db.update_account(account_id, **update_data)
            
            self.logger.info(f"Warm account warmup completed for {mask_phone(phone)}")
            
            await notifier.send_message(
                f"🌡 <b>Тёплый аккаунт готов</b>\n\n"
                f"📱 {mask_phone(phone)}\n"
                f"✅ Прогрев завершён за {total_days} дня\n"
                f"📁 Перемещён в папку Тёплые аккаунты"
            )
        else:
            # Move to next day
            db.update_warmup_progress(
                account_id,
                current_day=current_day + 1,
                completed_actions=completed_actions,
                last_action_at=datetime.utcnow().isoformat()
            )
    
    async def _warm_account_day_actions(self, account_id: int, phone: str, day: int):
        """Execute daily warmup actions for warm account"""
        self.logger.debug(f"Warm account day {day} actions for {mask_phone(phone)}")
        
        # Day 1: Profile is already set, join channels, browse
        # Day 2: More activity, reactions, ready for use
        
        if day == 1:
            # Join several channels
            channels = random.sample(WARMUP_CHANNELS, min(4, len(WARMUP_CHANNELS)))
            
            for channel in channels:
                result = await telegram_actions.join_channel(account_id, phone, channel)
                if result['success']:
                    self.logger.debug(f"Joined @{channel}")
                await asyncio.sleep(random.randint(60, 180))
            
            # Browse and react to some posts
            channel = random.choice(WARMUP_CHANNELS)
            posts_result = await telegram_actions.get_channel_posts(
                account_id, phone, channel, limit=5
            )
            
            if posts_result['success'] and posts_result.get('posts'):
                for post in posts_result['posts'][:2]:
                    if random.random() < 0.5:
                        emoji = random.choice(['👍', '❤️', '🔥'])
                        await telegram_actions.send_reaction(
                            account_id, phone, channel, post['id'], emoji
                        )
                    await asyncio.sleep(random.randint(30, 90))
        
        else:  # Day 2 - more active
            # More reactions
            for _ in range(2):
                channel = random.choice(WARMUP_CHANNELS)
                posts_result = await telegram_actions.get_channel_posts(
                    account_id, phone, channel, limit=8
                )
                
                if posts_result['success'] and posts_result.get('posts'):
                    posts = random.sample(
                        posts_result['posts'],
                        min(3, len(posts_result['posts']))
                    )
                    
                    for post in posts:
                        if random.random() < 0.7:
                            emoji = random.choice(['👍', '❤️', '🔥', '👏', '🎉'])
                            await telegram_actions.send_reaction(
                                account_id, phone, channel, post['id'], emoji
                            )
                        await asyncio.sleep(random.randint(20, 60))
                
                await asyncio.sleep(random.randint(120, 300))
