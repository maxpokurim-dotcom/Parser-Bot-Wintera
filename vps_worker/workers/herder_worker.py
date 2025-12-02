"""
Herder Worker - Bot activity simulation
Automatically reads posts, sends reactions and comments
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .base_worker import BaseWorker
from services.database import db
from services.notifier import notifier
from services.telegram_client import telegram_actions
from config import config
from utils.helpers import mask_phone, generate_random_delay


# Reaction emojis available in Telegram
REACTIONS = ['👍', '❤️', '🔥', '😢', '😡', '🤔', '🎉', '👏', '🤝', '👎', '😁', '😮']


class HerderWorker(BaseWorker):
    """
    Simulates natural user activity in channels
    
    Strategies:
    - observer: Only read and rare reactions
    - expert: Questions, expert comments
    - support: Likes and short agreements
    - trendsetter: First reactions on posts
    - community: Coordinated discussions
    """
    
    def __init__(self):
        super().__init__('herder_worker')
        self.daily_actions = {}  # account_id -> count today
        self.last_reset = datetime.utcnow().date()
    
    async def process(self):
        """Process active herder assignments"""
        # Reset daily counters
        today = datetime.utcnow().date()
        if today != self.last_reset:
            self.daily_actions.clear()
            self.last_reset = today
        
        assignments = db.get_active_herder_assignments()
        
        for assignment in assignments:
            assignment_id = assignment['id']
            user_id = assignment['user_id']
            
            # Check if system is paused
            if db.is_system_paused(user_id):
                continue
            
            try:
                await self._process_assignment(assignment)
            except Exception as e:
                self.logger.error(f"Error in herder assignment {assignment_id}: {e}")
                db.log_herder_action(
                    assignment_id, 0, 'error', 'failed',
                    {'error': str(e)}
                )
    
    async def _process_assignment(self, assignment: dict):
        """Process single herder assignment"""
        assignment_id = assignment['id']
        channel_id = assignment['channel_id']
        account_ids = assignment.get('account_ids', [])
        strategy = assignment.get('strategy', 'observer')
        action_chain = assignment.get('action_chain', [])
        settings = assignment.get('settings', {})
        
        # Get channel info
        channel = db.get_monitored_channel(channel_id)
        if not channel:
            self.logger.warning(f"Channel {channel_id} not found")
            return
        
        channel_username = channel.get('channel_username')
        if not channel_username:
            return
        
        # Get max actions from settings
        max_daily = settings.get('max_comments_per_day', 2) * len(account_ids)
        max_per_account = config.herder.max_daily_actions
        
        # Check delay after post
        delay_range = settings.get('delay_after_post', [300, 3600])
        
        # Get random account from list
        available_accounts = []
        for acc_id in account_ids:
            if self.daily_actions.get(acc_id, 0) < max_per_account:
                account = db.get_account(acc_id)
                if account and account.get('status') == 'active':
                    available_accounts.append(account)
        
        if not available_accounts:
            return
        
        account = random.choice(available_accounts)
        account_id = account['id']
        phone = account['phone']
        
        # Get recent posts from channel
        posts_result = await telegram_actions.get_channel_posts(
            account_id,
            phone,
            channel_username,
            limit=5
        )
        
        if not posts_result['success']:
            return
        
        posts = posts_result.get('posts', [])
        if not posts:
            return
        
        # Select a post based on strategy
        post = self._select_post(posts, strategy)
        if not post:
            return
        
        # Execute action chain
        for action_config in action_chain:
            action_type = action_config.get('action', 'read')
            probability = action_config.get('probability', 1.0)
            
            # Random skip based on probability
            if random.random() > probability:
                continue
            
            success = await self._execute_action(
                assignment_id,
                account,
                channel_username,
                post,
                action_type,
                action_config,
                strategy
            )
            
            if success:
                # Update daily counter
                self.daily_actions[account_id] = self.daily_actions.get(account_id, 0) + 1
                
                # Update assignment stats
                db.update_herder_assignment(
                    assignment_id,
                    total_actions=(assignment.get('total_actions', 0) or 0) + 1
                )
            
            # Delay between actions
            delay_after = action_config.get('delay_after', [60, 300])
            await asyncio.sleep(generate_random_delay(delay_after[0], delay_after[1]))
    
    def _select_post(self, posts: List[Dict], strategy: str) -> Optional[Dict]:
        """Select post based on strategy"""
        if not posts:
            return None
        
        if strategy == 'trendsetter':
            # Select most recent post
            return posts[0]
        elif strategy == 'expert':
            # Select post with fewer replies (opportunity for expert input)
            posts_sorted = sorted(posts, key=lambda p: p.get('replies', 0))
            return posts_sorted[0] if posts_sorted else None
        elif strategy == 'support':
            # Select popular post
            posts_sorted = sorted(posts, key=lambda p: p.get('views', 0), reverse=True)
            return posts_sorted[0] if posts_sorted else None
        else:
            # Random for observer and community
            return random.choice(posts)
    
    async def _execute_action(
        self,
        assignment_id: int,
        account: dict,
        channel: str,
        post: dict,
        action_type: str,
        action_config: dict,
        strategy: str
    ) -> bool:
        """Execute single action"""
        account_id = account['id']
        phone = account['phone']
        post_id = post['id']
        
        self.logger.debug(f"Executing {action_type} on {channel} post {post_id}")
        
        if action_type == 'read':
            # Just "read" - no API call needed, just log
            db.log_herder_action(assignment_id, account_id, 'read', 'success')
            return True
        
        elif action_type == 'react':
            # Send reaction
            emoji = action_config.get('emoji', ['👍'])
            if isinstance(emoji, list):
                emoji = random.choice(emoji)
            
            result = await telegram_actions.send_reaction(
                account_id,
                phone,
                channel,
                post_id,
                emoji
            )
            
            status = 'success' if result['success'] else 'failed'
            db.log_herder_action(
                assignment_id, account_id, 'react', status,
                {'emoji': emoji, 'post_id': post_id, 'error': result.get('error')}
            )
            return result['success']
        
        elif action_type == 'comment':
            # Generate and send comment
            comment = await self._generate_comment(post, strategy, account)
            
            if not comment:
                return False
            
            result = await telegram_actions.send_comment(
                account_id,
                phone,
                channel,
                post_id,
                comment
            )
            
            status = 'success' if result['success'] else 'failed'
            db.log_herder_action(
                assignment_id, account_id, 'comment', status,
                {'comment': comment[:100], 'post_id': post_id, 'error': result.get('error')}
            )
            
            if result['success']:
                db.update_herder_assignment(
                    assignment_id,
                    total_comments=(db.get_herder_assignment(assignment_id) or {}).get('total_comments', 0) + 1
                )
            
            return result['success']
        
        elif action_type == 'save':
            # Save to favorites (not implemented in API, log only)
            db.log_herder_action(assignment_id, account_id, 'save', 'success')
            return True
        
        return False
    
    async def _generate_comment(self, post: dict, strategy: str, account: dict) -> Optional[str]:
        """Generate comment based on strategy and post content"""
        post_text = post.get('text', '')[:200]
        
        # Get account profile for personalization
        profile = db.get_account_profile(account['id'])
        
        # Simple comment templates based on strategy
        if strategy == 'expert':
            templates = [
                "Интересная точка зрения! А как вы относитесь к {topic}?",
                "Важная тема. По моему опыту, {opinion}",
                "Хороший материал. Добавлю, что {addition}",
            ]
            # For now, use simple comments without AI
            comments = [
                "Интересный материал, спасибо за информацию!",
                "Полезно, сохранил себе 👍",
                "Согласен с автором, важная тема",
                "Хорошая подборка, как раз искал подобное"
            ]
        elif strategy == 'support':
            comments = [
                "👍👍👍",
                "Супер!",
                "Отлично!",
                "+1",
                "Согласен!",
                "Поддерживаю",
                "🔥🔥🔥"
            ]
        elif strategy == 'trendsetter':
            comments = [
                "Первый! 🎉",
                "Новый пост, отлично!",
                "Ждал этого!",
                "Наконец-то!",
                "🚀"
            ]
        else:
            comments = [
                "👍",
                "Интересно",
                "Спасибо",
                "🙏"
            ]
        
        return random.choice(comments)
