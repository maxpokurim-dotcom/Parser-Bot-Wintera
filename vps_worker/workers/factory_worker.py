"""
Factory Worker - Automatic account creation using OnlineSim
Creates new Telegram accounts with purchased SMS numbers
"""
import asyncio
import random
from datetime import datetime
from typing import List, Dict, Optional

from .base_worker import BaseWorker
from services.database import db
from services.notifier import notifier
from services.onlinesim import onlinesim, OnlineSimError
from services.telegram_client import client_manager
from config import config
from utils.helpers import mask_phone


# Role distribution presets
ROLE_PRESETS = {
    'balanced': {'observer': 0.4, 'expert': 0.3, 'support': 0.2, 'trendsetter': 0.1},
    'passive': {'observer': 0.7, 'support': 0.2, 'expert': 0.1, 'trendsetter': 0.0},
    'active': {'expert': 0.4, 'support': 0.3, 'trendsetter': 0.2, 'observer': 0.1}
}


class FactoryWorker(BaseWorker):
    """
    Automatic account creation worker
    
    Process:
    1. Get phone number from OnlineSim
    2. Send authorization request to Telegram
    3. Wait for SMS code from OnlineSim
    4. Complete Telegram authorization
    5. Create account in database
    6. Start warmup if configured
    """
    
    def __init__(self):
        super().__init__('factory_worker')
    
    async def process(self):
        """Process pending factory tasks"""
        # Check if OnlineSim is available
        if not await onlinesim.is_available():
            return
        
        tasks = db.get_pending_factory_tasks()
        
        for task in tasks:
            task_id = task['id']
            user_id = task['user_id']
            
            # Check if system is paused
            if db.is_system_paused(user_id):
                continue
            
            try:
                await self._process_task(task)
            except Exception as e:
                self.logger.error(f"Error processing factory task {task_id}: {e}")
                db.update_factory_task(
                    task_id,
                    status='error',
                    errors=[str(e)]
                )
    
    async def _process_task(self, task: dict):
        """Process single factory task"""
        task_id = task['id']
        user_id = task['user_id']
        count = task.get('count', 1)
        country = task.get('country', 'ru')
        auto_warmup = task.get('auto_warmup', True)
        warmup_days = task.get('warmup_days', 5)
        role_distribution = task.get('role_distribution', ROLE_PRESETS['balanced'])
        
        # Get current progress
        created_count = task.get('created_count', 0) or 0
        failed_count = task.get('failed_count', 0) or 0
        errors = task.get('errors', []) or []
        
        # Check if task is complete
        if created_count + failed_count >= count:
            db.update_factory_task(task_id, status='completed')
            return
        
        # Update status if starting
        if task.get('status') == 'pending':
            db.update_factory_task(task_id, status='in_progress')
        
        # Create one account per cycle (to avoid overwhelming the system)
        self.logger.info(f"Factory task {task_id}: creating account {created_count + 1}/{count}")
        
        try:
            # Check balance first
            balance = await onlinesim.get_balance()
            if balance < 15:  # Minimum for one number
                self.logger.warning(f"OnlineSim balance too low: {balance}")
                db.update_factory_task(
                    task_id,
                    status='paused',
                    errors=errors + [f"Balance too low: {balance}"]
                )
                await notifier.send_message(
                    f"⚠️ <b>Фабрика приостановлена</b>\n\n"
                    f"Недостаточно баланса OnlineSim: {balance}₽"
                )
                return
            
            # Create account
            result = await self._create_account(
                user_id=user_id,
                country=country,
                auto_warmup=auto_warmup,
                warmup_days=warmup_days,
                role_distribution=role_distribution
            )
            
            if result['success']:
                created_count += 1
                db.update_factory_task(
                    task_id,
                    created_count=created_count
                )
                
                await notifier.send_message(
                    f"✅ <b>Аккаунт создан</b>\n\n"
                    f"📱 {mask_phone(result['phone'])}\n"
                    f"📊 Прогресс: {created_count}/{count}"
                )
            else:
                failed_count += 1
                errors.append(result.get('error', 'Unknown error'))
                db.update_factory_task(
                    task_id,
                    failed_count=failed_count,
                    errors=errors[-10:]  # Keep last 10 errors
                )
            
            # Check if task is complete
            if created_count + failed_count >= count:
                db.update_factory_task(task_id, status='completed')
                await notifier.send_message(
                    f"🏭 <b>Фабрика завершена</b>\n\n"
                    f"✅ Создано: {created_count}\n"
                    f"❌ Ошибок: {failed_count}"
                )
                
        except OnlineSimError as e:
            self.logger.error(f"OnlineSim error: {e}")
            errors.append(str(e))
            db.update_factory_task(
                task_id,
                failed_count=failed_count + 1,
                errors=errors[-10:]
            )
            
        except Exception as e:
            self.logger.error(f"Factory error: {e}")
            errors.append(str(e))
            db.update_factory_task(
                task_id,
                failed_count=failed_count + 1,
                errors=errors[-10:]
            )
    
    async def _create_account(
        self,
        user_id: int,
        country: str,
        auto_warmup: bool,
        warmup_days: int,
        role_distribution: Dict[str, float]
    ) -> Dict:
        """
        Create single account
        
        Returns:
            dict with success, phone, account_id or error
        """
        phone = None
        tzid = None
        
        try:
            # Step 1: Get phone number from OnlineSim
            self.logger.info(f"Getting phone number from OnlineSim (country: {country})")
            phone_data = await onlinesim.get_number(service='telegram', country=country)
            phone = phone_data.number
            tzid = phone_data.tzid
            
            self.logger.info(f"Got number: {mask_phone(phone)}")
            
            # Step 2: Create temporary account record
            role = self._select_role(role_distribution)
            account = db.client.table('telegram_accounts').insert({
                'owner_id': user_id,
                'phone': phone,
                'status': 'pending',
                'source': 'auto_factory',
                'role': role,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
            if not account.data:
                raise Exception("Failed to create account record")
            
            account_id = account.data[0]['id']
            
            # Step 3: Start Telegram authorization
            self.logger.info(f"Starting Telegram authorization for {mask_phone(phone)}")
            
            try:
                phone_code_hash = await client_manager.start_auth(
                    account_id=account_id,
                    phone=phone
                )
            except Exception as e:
                self.logger.error(f"Telegram auth request failed: {e}")
                db.update_account(account_id, status='error')
                await onlinesim.cancel_number(tzid)
                return {'success': False, 'error': f'Telegram auth failed: {e}'}
            
            # Step 4: Wait for SMS code from OnlineSim
            self.logger.info(f"Waiting for SMS code...")
            code = await onlinesim.wait_for_code(tzid, timeout=300)
            
            if not code:
                self.logger.error("Timeout waiting for SMS code")
                db.update_account(account_id, status='error')
                await onlinesim.cancel_number(tzid)
                return {'success': False, 'error': 'SMS code timeout'}
            
            self.logger.info(f"Received SMS code for {mask_phone(phone)}")
            
            # Step 5: Complete Telegram authorization
            try:
                success = await client_manager.complete_auth(
                    account_id=account_id,
                    phone=phone,
                    code=code,
                    phone_code_hash=phone_code_hash
                )
                
                if not success:
                    raise Exception("Authorization failed")
                    
            except Exception as e:
                self.logger.error(f"Telegram sign in failed: {e}")
                db.update_account(account_id, status='error')
                return {'success': False, 'error': f'Sign in failed: {e}', 'phone': phone}
            
            # Step 6: Confirm OnlineSim usage
            await onlinesim.set_operation_ok(tzid)
            
            # Step 7: Update account status
            me = await client_manager.get_me(account_id)
            
            update_data = {
                'status': 'active',
                'telegram_id': me.id if me else None,
                'username': me.username if me else None,
                'first_name': me.first_name if me else None,
            }
            
            if auto_warmup:
                update_data['warmup_status'] = 'in_progress'
                # Create warmup progress
                try:
                    db.client.table('warmup_progress').insert({
                        'account_id': account_id,
                        'status': 'in_progress',
                        'current_day': 1,
                        'total_days': warmup_days,
                        'warmup_type': 'standard',
                        'completed_actions': [],
                        'created_at': datetime.utcnow().isoformat()
                    }).execute()
                except:
                    pass  # May already exist
            
            db.update_account(account_id, **update_data)
            
            # Create profile
            try:
                db.client.table('account_profiles').insert({
                    'account_id': account_id,
                    'persona': 'Пользователь Telegram',
                    'role': role,
                    'interests': ['общение', 'новости'],
                    'speech_style': 'informal',
                    'preferred_reactions': ['👍', '❤️', '🔥'],
                    'created_at': datetime.utcnow().isoformat()
                }).execute()
            except:
                pass  # May already exist
            
            self.logger.info(f"Successfully created account {mask_phone(phone)}")
            
            return {
                'success': True,
                'phone': phone,
                'account_id': account_id
            }
            
        except Exception as e:
            self.logger.error(f"Account creation failed: {e}")
            
            # Cleanup
            if tzid:
                try:
                    await onlinesim.cancel_number(tzid)
                except:
                    pass
            
            return {'success': False, 'error': str(e), 'phone': phone}
    
    def _select_role(self, distribution: Dict[str, float]) -> str:
        """Select role based on distribution"""
        rand = random.random()
        cumulative = 0
        
        for role, probability in distribution.items():
            cumulative += probability
            if rand <= cumulative:
                return role
        
        return 'observer'
