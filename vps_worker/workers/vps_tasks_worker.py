"""
VPS Tasks Worker - Processes VPS tasks created by the Telegram bot
Handles warm account creation, profile generation, etc.
"""
import asyncio
from datetime import datetime
from typing import Dict, Optional

from .base_worker import BaseWorker
from services.database import db
from services.notifier import notifier
from services.ai_service import ai_service
from services.telegram_client import client_manager
from utils.logger import get_logger
from utils.helpers import mask_phone

logger = get_logger('vps_tasks_worker')


class VPSTasksWorker(BaseWorker):
    """
    Processes VPS tasks from the vps_tasks table
    
    Task types:
    - warm_account_create: Create warm account with AI profile
    - content_publish: Publish scheduled content
    - profile_update: Update account profile via AI
    """
    
    def __init__(self):
        super().__init__('vps_tasks_worker')
    
    async def process(self):
        """Process pending VPS tasks"""
        tasks = db.get_pending_vps_tasks()
        
        for task in tasks:
            task_id = task['id']
            task_type = task.get('task_type')
            
            try:
                # Mark as in progress
                db.update_vps_task(task_id, status='in_progress', started_at=datetime.utcnow().isoformat())
                
                # Process based on type
                if task_type == 'warm_account_create':
                    await self._process_warm_account(task)
                elif task_type == 'warm_account':
                    await self._process_warm_account(task)
                elif task_type == 'profile_generate':
                    await self._process_profile_generation(task)
                else:
                    self.logger.warning(f"Unknown VPS task type: {task_type}")
                    db.update_vps_task(task_id, status='error', error=f'Unknown task type: {task_type}')
                    
            except Exception as e:
                self.logger.error(f"Error processing VPS task {task_id}: {e}")
                
                # Increment attempts
                attempts = (task.get('attempts') or 0) + 1
                max_attempts = task.get('max_attempts') or 3
                
                if attempts >= max_attempts:
                    db.update_vps_task(task_id, 
                        status='failed', 
                        attempts=attempts,
                        error=str(e)
                    )
                else:
                    db.update_vps_task(task_id, 
                        status='pending',
                        attempts=attempts,
                        error=str(e)
                    )
    
    async def _process_warm_account(self, task: Dict):
        """Process warm account creation task"""
        task_id = task['id']
        task_data = task.get('task_data', {})
        
        account_id = task_data.get('account_id')
        profile_type = task_data.get('profile_type', 'reader')
        profile_params = task_data.get('profile_params', {})
        warmup_config = task_data.get('warmup', {})
        
        if not account_id:
            db.update_vps_task(task_id, status='error', error='No account_id provided')
            return
        
        account = db.get_account(account_id)
        if not account:
            db.update_vps_task(task_id, status='error', error='Account not found')
            return
        
        self.logger.info(f"Processing warm account creation for account {account_id}")
        
        # Step 1: Generate profile via YaGPT
        profile_result = await self._generate_ai_profile(profile_type, profile_params)
        
        if not profile_result:
            db.update_vps_task(task_id, status='error', error='Failed to generate AI profile')
            return
        
        # Step 2: Update account profile in database
        db.create_account_profile(account_id, profile_result)
        
        # Step 3: Apply profile to Telegram account (if authorized)
        if account.get('status') == 'active':
            await self._apply_telegram_profile(account_id, account['phone'], profile_result)
        
        # Step 4: Start warmup if configured
        if warmup_config.get('enabled', True):
            warmup_days = warmup_config.get('duration_days', 2)
            db.update_account(account_id, 
                warmup_status='in_progress',
                warmup_day=0
            )
            
            # Create or update warmup progress
            existing_progress = db.get_warmup_progress(account_id)
            if not existing_progress:
                db.client.table('warmup_progress').insert({
                    'account_id': account_id,
                    'total_days': warmup_days,
                    'current_day': 1,
                    'status': 'in_progress',
                    'warmup_type': 'warm_account',
                    'started_at': datetime.utcnow().isoformat()
                }).execute()
        
        # Mark task as completed
        db.update_vps_task(task_id, 
            status='completed',
            completed_at=datetime.utcnow().isoformat(),
            result={'profile': profile_result}
        )
        
        # Notify
        phone = account.get('phone', '')
        await notifier.send_message(
            f"✅ <b>Тёплый аккаунт настроен</b>\n\n"
            f"📱 {mask_phone(phone)}\n"
            f"🎭 Профиль: {profile_result.get('persona', profile_type)}\n"
            f"🔥 Прогрев: {warmup_config.get('duration_days', 2)} дней"
        )
        
        self.logger.info(f"Warm account {account_id} setup completed")
    
    async def _generate_ai_profile(self, profile_type: str, params: dict) -> Optional[Dict]:
        """Generate AI profile using YandexGPT"""
        
        # Profile type descriptions
        profile_prompts = {
            'expert': 'Профессионал в своей области, даёт экспертные советы и анализ',
            'reader': 'Активный подписчик каналов, интересуется новостями и контентом',
            'critic': 'Вдумчивый аналитик, задаёт вопросы и анализирует материал',
            'supporter': 'Позитивный участник, поддерживает авторов и контент',
            'trendsetter': 'Следит за трендами, первым реагирует на новое'
        }
        
        base_description = profile_prompts.get(profile_type, profile_prompts['reader'])
        interests = params.get('base_interests', ['общение', 'новости', 'технологии'])
        speech_style = params.get('speech_style', 'informal')
        
        # Generate name and bio via AI
        prompt = f"""Создай профиль для Telegram аккаунта.

Тип персоны: {base_description}
Интересы: {', '.join(interests)}
Стиль общения: {speech_style}

Сгенерируй:
1. Русское имя (имя и фамилия)
2. Краткое био для профиля (до 70 символов)
3. Список из 5 интересов

Формат ответа (строго JSON):
{{"name": "Имя Фамилия", "bio": "Краткое био", "interests": ["интерес1", "интерес2", "интерес3", "интерес4", "интерес5"]}}"""

        try:
            result = await ai_service.generate(
                prompt=prompt,
                task="content_generate",
                max_tokens=300,
                temperature=0.8
            )
            
            if result:
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    profile_data = json.loads(json_match.group())
                    
                    return {
                        'persona': profile_data.get('name', 'Пользователь'),
                        'bio': profile_data.get('bio', ''),
                        'role': profile_type,
                        'interests': profile_data.get('interests', interests),
                        'speech_style': speech_style,
                        'personality_vector': {
                            'friendliness': 0.7,
                            'expertise': 0.5 if profile_type == 'expert' else 0.3,
                            'irony': 0.2
                        },
                        'preferred_reactions': ['👍', '❤️', '🔥']
                    }
            
        except Exception as e:
            self.logger.error(f"AI profile generation error: {e}")
        
        # Fallback to default profile
        return {
            'persona': 'Пользователь Telegram',
            'bio': 'Интересуюсь новостями и технологиями',
            'role': profile_type,
            'interests': interests,
            'speech_style': speech_style,
            'personality_vector': {'friendliness': 0.7, 'expertise': 0.3},
            'preferred_reactions': ['👍', '❤️']
        }
    
    async def _apply_telegram_profile(self, account_id: int, phone: str, profile: Dict):
        """Apply profile to Telegram account"""
        try:
            client = await client_manager.get_client(account_id, phone)
            if not client:
                self.logger.warning(f"Cannot apply profile: client not available for {account_id}")
                return
            
            from telethon.tl.functions.account import UpdateProfileRequest
            from telethon.tl.functions.photos import UploadProfilePhotoRequest
            
            # Update name and bio
            name_parts = profile.get('persona', '').split(' ', 1)
            first_name = name_parts[0] if name_parts else 'User'
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            bio = profile.get('bio', '')[:70]  # Telegram bio limit
            
            await client(UpdateProfileRequest(
                first_name=first_name,
                last_name=last_name,
                about=bio
            ))
            
            self.logger.info(f"Applied Telegram profile to account {account_id}")
            
        except Exception as e:
            self.logger.error(f"Error applying Telegram profile: {e}")
    
    async def _process_profile_generation(self, task: Dict):
        """Process standalone profile generation task"""
        task_id = task['id']
        task_data = task.get('task_data', {})
        
        account_id = task_data.get('account_id')
        profile_type = task_data.get('profile_type', 'reader')
        
        if not account_id:
            db.update_vps_task(task_id, status='error', error='No account_id')
            return
        
        profile_result = await self._generate_ai_profile(profile_type, task_data)
        
        if profile_result:
            db.create_account_profile(account_id, profile_result)
            db.update_vps_task(task_id, 
                status='completed',
                completed_at=datetime.utcnow().isoformat(),
                result=profile_result
            )
        else:
            db.update_vps_task(task_id, status='error', error='Profile generation failed')
