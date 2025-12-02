"""
Content Worker - Handles scheduled content publishing
Publishes posts to channels based on content plan
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base_worker import BaseWorker
from services.database import db
from services.notifier import notifier
from services.telegram_client import telegram_actions, client_manager
from services.ai_service import ai_service
from utils.logger import get_logger
from utils.helpers import mask_phone

logger = get_logger('content_worker')


class ContentWorker(BaseWorker):
    """
    Publishes scheduled content to Telegram channels
    
    Features:
    - Scheduled one-time posts
    - Template-based recurring posts
    - AI content generation before posting
    - Multiple channel support
    """
    
    def __init__(self):
        super().__init__('content_worker')
    
    async def process(self):
        """Process scheduled content"""
        # Process one-time scheduled content
        await self._process_scheduled_content()
        
        # Process template schedules (recurring)
        await self._process_template_schedules()
    
    async def _process_scheduled_content(self):
        """Process one-time scheduled content items"""
        items = db.get_due_scheduled_content()
        
        for item in items:
            content_id = item['id']
            user_id = item.get('owner_id')
            
            # Check if system is paused
            if db.is_system_paused(user_id):
                continue
            
            try:
                await self._publish_content(item)
            except Exception as e:
                self.logger.error(f"Error publishing content {content_id}: {e}")
                db.update_scheduled_content(content_id, 
                    status='error',
                    error=str(e)
                )
    
    async def _process_template_schedules(self):
        """Process template-based schedules (recurring)"""
        schedules = db.get_due_template_schedules()
        
        for schedule in schedules:
            schedule_id = schedule['id']
            
            try:
                await self._publish_template_content(schedule)
            except Exception as e:
                self.logger.error(f"Error publishing template schedule {schedule_id}: {e}")
                db.update_template_schedule(schedule_id, error=str(e))
    
    async def _publish_content(self, content: Dict):
        """Publish single content item to channel"""
        content_id = content['id']
        channel_id = content.get('channel_id')
        content_text = content.get('content_text', '')
        content_type = content.get('content_type', 'text')
        media_url = content.get('media_url')
        use_ai = content.get('use_ai_rewrite', False)
        
        self.logger.info(f"Publishing content {content_id} to channel {channel_id}")
        
        # Get channel info
        channel = db.get_user_channel(channel_id) if channel_id else None
        if not channel:
            db.update_scheduled_content(content_id, 
                status='error',
                error='Channel not found'
            )
            return
        
        channel_username = channel.get('channel_id') or channel.get('channel_username')
        owner_id = channel.get('owner_id')
        
        # Get an active account to post from
        accounts = db.get_active_accounts(owner_id)
        if not accounts:
            db.update_scheduled_content(content_id, 
                status='error',
                error='No active accounts available'
            )
            return
        
        account = accounts[0]
        account_id = account['id']
        phone = account['phone']
        
        # AI rewrite if enabled
        if use_ai and content_text:
            rewritten = await ai_service.rewrite_text(content_text)
            if rewritten:
                content_text = rewritten
        
        # Publish to channel
        result = await self._send_to_channel(
            account_id=account_id,
            phone=phone,
            channel=channel_username,
            text=content_text,
            media=media_url
        )
        
        if result['success']:
            db.update_scheduled_content(content_id, 
                status='published',
                published_at=datetime.utcnow().isoformat(),
                message_id=result.get('message_id')
            )
            
            await notifier.send_message(
                f"✅ <b>Контент опубликован</b>\n\n"
                f"📢 Канал: @{channel_username}\n"
                f"📝 ID: {content_id}"
            )
            
            self.logger.info(f"Content {content_id} published successfully")
        else:
            db.update_scheduled_content(content_id, 
                status='error',
                error=result.get('error', 'Unknown error')
            )
    
    async def _publish_template_content(self, schedule: Dict):
        """Publish content based on template schedule"""
        schedule_id = schedule['id']
        template_id = schedule.get('template_id')
        channel_id = schedule.get('channel_id')
        repeat_days = schedule.get('repeat_days', [])
        
        # Check if today is in repeat days
        today = datetime.utcnow().strftime('%a').lower()[:2]
        day_map = {'mo': 0, 'tu': 1, 'we': 2, 'th': 3, 'fr': 4, 'sa': 5, 'su': 6}
        today_num = datetime.utcnow().weekday()
        
        if repeat_days and today_num not in repeat_days:
            return
        
        # Get template
        template = db.get_template(template_id)
        if not template:
            self.logger.warning(f"Template {template_id} not found for schedule {schedule_id}")
            return
        
        # Get channel
        channel = db.get_user_channel(channel_id)
        if not channel:
            self.logger.warning(f"Channel {channel_id} not found for schedule {schedule_id}")
            return
        
        channel_username = channel.get('channel_id') or channel.get('channel_username')
        owner_id = schedule.get('owner_id')
        
        # Get account
        accounts = db.get_active_accounts(owner_id)
        if not accounts:
            self.logger.warning(f"No active accounts for schedule {schedule_id}")
            return
        
        account = accounts[0]
        account_id = account['id']
        phone = account['phone']
        
        # Get template content
        text = template.get('text', '')
        media_path = template.get('media_path')
        
        self.logger.info(f"Publishing template {template_id} to @{channel_username}")
        
        # Publish
        result = await self._send_to_channel(
            account_id=account_id,
            phone=phone,
            channel=channel_username,
            text=text,
            media=media_path
        )
        
        if result['success']:
            # Update last published time
            db.update_template_schedule(schedule_id,
                last_published_at=datetime.utcnow().isoformat()
            )
            
            await notifier.send_message(
                f"📅 <b>Авто-публикация</b>\n\n"
                f"📢 Канал: @{channel_username}\n"
                f"📋 Шаблон: {template.get('name', template_id)}",
                disable_notification=True
            )
            
            self.logger.info(f"Template schedule {schedule_id} published")
        else:
            self.logger.error(f"Failed to publish template schedule {schedule_id}: {result.get('error')}")
    
    async def _send_to_channel(
        self,
        account_id: int,
        phone: str,
        channel: str,
        text: str,
        media: Optional[str] = None
    ) -> Dict:
        """Send message to channel"""
        try:
            client = await client_manager.get_client(account_id, phone)
            if not client:
                return {'success': False, 'error': 'Client not available'}
            
            # Get channel entity
            try:
                entity = await client.get_entity(channel)
            except Exception as e:
                return {'success': False, 'error': f'Channel not found: {e}'}
            
            # Send message
            if media:
                import os
                if os.path.exists(media):
                    message = await client.send_file(entity, media, caption=text)
                else:
                    # Try as URL
                    message = await client.send_message(entity, text)
            else:
                message = await client.send_message(entity, text)
            
            return {
                'success': True,
                'message_id': message.id
            }
            
        except Exception as e:
            self.logger.error(f"Error sending to channel: {e}")
            return {'success': False, 'error': str(e)}
