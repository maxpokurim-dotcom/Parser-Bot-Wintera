"""
Auth Worker - Handles account authorization
Processes auth_tasks from database
"""
import asyncio
from telethon import errors

from .base_worker import BaseWorker
from services.database import db
from services.notifier import notifier
from services.telegram_client import client_manager
from utils.helpers import mask_phone


class AuthWorker(BaseWorker):
    """
    Processes account authorization tasks
    
    Flow:
    1. Check for pending auth tasks
    2. For 'pending' status - send code request
    3. For 'code_received' - complete authorization
    """
    
    def __init__(self):
        super().__init__('auth_worker')
        self.pending_codes = {}  # task_id -> phone_code_hash
    
    async def process(self):
        """Process pending auth tasks"""
        tasks = db.get_pending_auth_tasks()
        
        for task in tasks:
            task_id = task['id']
            phone = task['phone']
            status = task['status']
            
            try:
                if status == 'pending':
                    await self._send_code(task)
                elif status == 'code_received':
                    await self._complete_auth(task)
            except Exception as e:
                self.logger.error(f"Error processing auth task {task_id}: {e}")
                db.update_auth_task(task_id, status='error', error=str(e))
    
    async def _send_code(self, task: dict):
        """Send code request to phone"""
        task_id = task['id']
        phone = task['phone']
        account_id = task.get('account_id')
        proxy = task.get('proxy')
        
        self.logger.info(f"Sending code to {mask_phone(phone)}")
        
        try:
            phone_code_hash = await client_manager.start_auth(
                account_id or task_id,  # Use task_id if no account yet
                phone,
                proxy
            )
            
            if phone_code_hash:
                self.pending_codes[task_id] = phone_code_hash
                db.update_auth_task(
                    task_id, 
                    status='code_sent',
                    phone_code_hash=phone_code_hash
                )
                self.logger.info(f"Code sent to {mask_phone(phone)}")
            else:
                db.update_auth_task(task_id, status='error', error='Failed to send code')
                
        except errors.FloodWaitError as e:
            self.logger.warning(f"FloodWait for {mask_phone(phone)}: {e.seconds}s")
            db.update_auth_task(
                task_id, 
                status='flood_wait',
                error=f'FloodWait: {e.seconds}s'
            )
        except errors.PhoneNumberBannedError:
            db.update_auth_task(task_id, status='error', error='Phone number banned')
        except errors.PhoneNumberInvalidError:
            db.update_auth_task(task_id, status='error', error='Invalid phone number')
        except Exception as e:
            self.logger.error(f"Error sending code: {e}")
            db.update_auth_task(task_id, status='error', error=str(e))
    
    async def _complete_auth(self, task: dict):
        """Complete authorization with received code"""
        task_id = task['id']
        phone = task['phone']
        code = task.get('code')
        password = task.get('password')
        account_id = task.get('account_id')
        phone_code_hash = task.get('phone_code_hash') or self.pending_codes.get(task_id)
        
        if not code:
            self.logger.warning(f"No code for task {task_id}")
            return
        
        if not phone_code_hash:
            self.logger.error(f"No phone_code_hash for task {task_id}")
            db.update_auth_task(task_id, status='error', error='Missing phone_code_hash')
            return
        
        self.logger.info(f"Completing auth for {mask_phone(phone)}")
        
        try:
            success = await client_manager.complete_auth(
                account_id or task_id,
                phone,
                code,
                phone_code_hash,
                password
            )
            
            if success:
                # Update account status
                if account_id:
                    db.update_account(account_id, status='active')
                
                db.update_auth_task(task_id, status='completed')
                
                # Get user info
                me = await client_manager.get_me(account_id or task_id)
                if me:
                    db.update_account(
                        account_id,
                        telegram_id=me.id,
                        username=me.username,
                        first_name=me.first_name,
                        last_name=me.last_name
                    )
                
                await notifier.notify_account_authorized(account_id, phone)
                self.logger.info(f"Successfully authorized {mask_phone(phone)}")
            else:
                db.update_auth_task(task_id, status='error', error='Authorization failed')
                
        except errors.SessionPasswordNeededError:
            self.logger.info(f"2FA required for {mask_phone(phone)}")
            db.update_auth_task(task_id, status='2fa_required')
            
        except errors.PhoneCodeExpiredError:
            db.update_auth_task(task_id, status='error', error='Code expired')
            
        except errors.PhoneCodeInvalidError:
            db.update_auth_task(task_id, status='error', error='Invalid code')
            
        except errors.PasswordHashInvalidError:
            db.update_auth_task(task_id, status='error', error='Invalid 2FA password')
            
        except Exception as e:
            self.logger.error(f"Error completing auth: {e}")
            db.update_auth_task(task_id, status='error', error=str(e))
        
        # Cleanup
        if task_id in self.pending_codes:
            del self.pending_codes[task_id]
