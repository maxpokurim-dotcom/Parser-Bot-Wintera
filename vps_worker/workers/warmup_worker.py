"""
Warmup Worker - Account warmup process
Gradually increases account activity to build trust
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict

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
    # Add more safe public channels
]


class WarmupWorker(BaseWorker):
    """
    Handles account warmup to build trust with Telegram
    
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
            account = account_data  # May include warmup_progress relation
            
            try:
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
