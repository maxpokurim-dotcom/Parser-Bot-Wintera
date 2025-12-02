"""
Mailing Worker - Handles message campaigns
Implements warm start, adaptive delays, typing simulation
"""
import asyncio
import random
from datetime import datetime
from typing import List, Dict, Optional

from .base_worker import BaseWorker
from services.database import db
from services.notifier import notifier
from services.telegram_client import telegram_actions
from config import config
from utils.helpers import mask_phone, generate_random_delay


class MailingWorker(BaseWorker):
    """
    Processes mailing campaigns
    
    Features:
    - Warm start (increased delays for first N messages)
    - Typing simulation
    - Adaptive delays (increase on errors)
    - Multi-account rotation
    - Rate limiting per account
    """
    
    def __init__(self):
        super().__init__('mailing_worker')
        self.delay_multipliers = {}  # campaign_id -> multiplier
    
    async def process(self):
        """Process active campaigns"""
        campaigns = db.get_active_campaigns()
        
        for campaign in campaigns:
            campaign_id = campaign['id']
            user_id = campaign.get('owner_id') or campaign.get('user_id')
            status = campaign['status']
            
            # Check if system is paused
            if user_id and db.is_system_paused(user_id):
                if status == 'running':
                    db.update_campaign(campaign_id, status='paused', pause_reason='System paused')
                continue
            
            # Skip paused campaigns
            if status == 'paused':
                continue
            
            try:
                await self._process_campaign(campaign)
            except Exception as e:
                self.logger.error(f"Error processing campaign {campaign_id}: {e}")
                db.update_campaign(
                    campaign_id, 
                    status='paused', 
                    pause_reason=f'Error: {str(e)[:100]}'
                )
    
    async def _process_campaign(self, campaign: dict):
        """Process single campaign - send batch of messages"""
        campaign_id = campaign['id']
        source_id = campaign['source_id']
        template_id = campaign['template_id']
        account_ids = campaign.get('account_ids', [])
        settings = campaign.get('settings', {})
        
        # Get settings
        use_warm_start = campaign.get('use_warm_start', True)
        use_typing = campaign.get('use_typing_simulation', True)
        use_adaptive = campaign.get('use_adaptive_delays', True)
        
        delay_min = settings.get('delay_min', config.mailing.delay_min)
        delay_max = settings.get('delay_max', config.mailing.delay_max)
        
        # Update status if pending
        if campaign['status'] == 'pending':
            db.update_campaign(campaign_id, status='running')
            
            # Get total count
            source = db.get_audience_source(source_id)
            if source:
                total_count = source.get('total_count', 0)
                db.update_campaign(campaign_id, total_count=total_count)
                await notifier.notify_campaign_started(campaign_id, total_count, len(account_ids))
        
        # Get template
        template = db.get_template(template_id)
        if not template:
            self.logger.error(f"Template {template_id} not found")
            db.update_campaign(campaign_id, status='error', pause_reason='Template not found')
            return
        
        message_text = template.get('text', '')
        media_path = template.get('media_path')
        
        # Get available accounts
        accounts = db.get_accounts_for_mailing(account_ids)
        if not accounts:
            self.logger.warning(f"No available accounts for campaign {campaign_id}")
            db.update_campaign(campaign_id, status='paused', pause_reason='No available accounts')
            return
        
        # Get recipients (batch)
        batch_size = min(10, len(accounts))  # Send 10 per cycle
        recipients = db.get_audience_users(source_id, limit=batch_size)
        
        if not recipients:
            # Campaign completed
            sent = campaign.get('sent_count', 0)
            failed = campaign.get('failed_count', 0)
            db.update_campaign(campaign_id, status='completed')
            await notifier.notify_campaign_completed(campaign_id, sent, failed)
            return
        
        # Calculate delay multiplier for warm start
        sent_count = campaign.get('sent_count', 0)
        warm_count = config.mailing.warm_start_count
        
        if use_warm_start and sent_count < warm_count:
            # Warm start - increased delays
            warm_multiplier = config.mailing.warm_start_multiplier
            delay_min = int(delay_min * warm_multiplier)
            delay_max = int(delay_max * warm_multiplier)
        
        # Adaptive delay multiplier
        if use_adaptive and campaign_id in self.delay_multipliers:
            multiplier = self.delay_multipliers[campaign_id]
            delay_min = int(delay_min * multiplier)
            delay_max = int(delay_max * multiplier)
        
        # Send messages
        account_index = 0
        
        for recipient in recipients:
            telegram_id = recipient['telegram_id']
            
            # Get account (rotate)
            account = accounts[account_index % len(accounts)]
            account_id = account['id']
            phone = account['phone']
            
            # Check stop list
            owner_id = campaign.get('owner_id') or campaign.get('user_id')
            if owner_id and db.is_in_stop_list(owner_id, telegram_id):
                db.mark_user_sent(telegram_id, source_id)
                continue
            
            # Typing simulation
            typing_delay = 0
            if use_typing:
                typing_delay = random.randint(
                    config.mailing.typing_delay_min,
                    config.mailing.typing_delay_max
                )
            
            # Personalize message
            personalized_text = self._personalize_message(message_text, recipient)
            
            # Send message
            result = await telegram_actions.send_message(
                account_id,
                phone,
                telegram_id,
                personalized_text,
                media=media_path,
                typing_delay=typing_delay
            )
            
            if result['success']:
                # Success
                db.mark_user_sent(telegram_id, source_id)
                db.increment_campaign_sent(campaign_id)
                db.increment_account_sent(account_id)
                db.reset_account_errors(account_id)
                
                # Reset adaptive delay
                if campaign_id in self.delay_multipliers:
                    self.delay_multipliers[campaign_id] = max(1.0, self.delay_multipliers[campaign_id] - 0.1)
                
                self.logger.debug(f"Sent to {telegram_id} via {mask_phone(phone)}")
                
            else:
                error = result.get('error', 'unknown')
                
                if error == 'flood_wait':
                    # Flood wait - pause account
                    seconds = result.get('seconds', 300)
                    db.set_account_flood_wait(account_id, seconds)
                    await notifier.notify_account_flood(account_id, phone, seconds)
                    
                    # Increase adaptive delay
                    if use_adaptive:
                        self.delay_multipliers[campaign_id] = self.delay_multipliers.get(campaign_id, 1.0) + 0.5
                    
                elif error == 'privacy_restricted':
                    # User has privacy settings
                    db.mark_user_sent(telegram_id, source_id)  # Don't retry
                    db.increment_campaign_failed(campaign_id)
                    
                elif error == 'user_blocked':
                    # Add to stop list
                    owner_id = campaign.get('owner_id') or campaign.get('user_id')
                    if owner_id:
                        db.add_to_stop_list(owner_id, telegram_id, 'blocked')
                    db.mark_user_sent(telegram_id, source_id)
                    db.increment_campaign_failed(campaign_id)
                    
                elif error == 'peer_flood':
                    # Peer flood - pause campaign
                    db.record_account_error(account_id, error, 'Peer flood')
                    db.update_campaign(campaign_id, status='paused', pause_reason='Peer flood detected')
                    await notifier.notify_campaign_paused(campaign_id, 'Peer flood detected')
                    return
                    
                else:
                    db.record_account_error(account_id, error, str(result))
                    db.increment_campaign_failed(campaign_id)
            
            # Rotate account
            account_index += 1
            
            # Delay before next message
            delay = generate_random_delay(delay_min, delay_max)
            await asyncio.sleep(delay)
        
        # Update campaign with current account
        if accounts:
            db.update_campaign(
                campaign_id, 
                current_account_id=accounts[account_index % len(accounts)]['id']
            )
        
        # Progress notification every N messages
        sent = campaign.get('sent_count', 0) + len([r for r in recipients])
        total = campaign.get('total_count', 0)
        report_every = settings.get('report_every', 50)
        
        if total > 0 and sent % report_every < len(recipients):
            failed = campaign.get('failed_count', 0)
            await notifier.notify_campaign_progress(campaign_id, sent, failed, total)
    
    def _personalize_message(self, text: str, recipient: dict) -> str:
        """Personalize message with recipient data (sync version)"""
        replacements = {
            '{first_name}': recipient.get('first_name') or '',
            '{last_name}': recipient.get('last_name') or '',
            '{username}': recipient.get('username') or '',
            '{name}': recipient.get('first_name') or recipient.get('username') or '',
        }
        
        for placeholder, value in replacements.items():
            text = text.replace(placeholder, value)
        
        return text
    
    async def _personalize_message_ai(
        self, 
        text: str, 
        recipient: dict,
        use_ai: bool = False
    ) -> str:
        """
        Personalize message with AI enhancement
        
        Args:
            text: Message template
            recipient: Recipient data
            use_ai: Use AI for deeper personalization
        
        Returns:
            Personalized message
        """
        # Basic placeholder replacement
        result = self._personalize_message(text, recipient)
        
        # AI personalization if enabled and contains marker
        if use_ai and ('{ai_personalize}' in text or '{ai}' in text):
            try:
                from services.ai_service import ai_service
                
                result = result.replace('{ai_personalize}', '').replace('{ai}', '')
                
                ai_result = await ai_service.personalize_message(
                    template=result,
                    recipient=recipient
                )
                
                if ai_result:
                    result = ai_result
                    
            except Exception as e:
                self.logger.warning(f"AI personalization failed: {e}")
        
        return result
