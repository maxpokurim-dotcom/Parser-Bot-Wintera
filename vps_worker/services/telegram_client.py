"""
Telegram Client Service - Telethon wrapper
Manages multiple account sessions
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Optional, List, Callable, Any
from telethon import TelegramClient, errors
from telethon.tl.types import User, Channel, Chat
from telethon.sessions import StringSession

from config import config, SESSIONS_DIR
from utils.logger import get_logger
from utils.helpers import mask_phone, generate_session_name, parse_proxy

logger = get_logger('telegram_client')


class TelegramClientManager:
    """
    Manages multiple Telegram client sessions
    Each account has its own session file
    """
    
    def __init__(self):
        self.clients: Dict[int, TelegramClient] = {}  # account_id -> client
        self.api_id = config.telegram.api_id
        self.api_hash = config.telegram.api_hash
    
    async def get_client(self, account_id: int, phone: str, proxy: Optional[str] = None) -> Optional[TelegramClient]:
        """
        Get or create Telegram client for account
        
        Args:
            account_id: Database account ID
            phone: Phone number for session name
            proxy: Optional proxy string
        
        Returns:
            Connected TelegramClient or None
        """
        # Check cache
        if account_id in self.clients:
            client = self.clients[account_id]
            if client.is_connected():
                return client
            else:
                # Reconnect
                try:
                    await client.connect()
                    if await client.is_user_authorized():
                        return client
                except Exception as e:
                    logger.error(f"Error reconnecting client for account {account_id}: {e}")
                    del self.clients[account_id]
        
        # Create new client
        session_file = SESSIONS_DIR / f"account_{account_id}.session"
        
        # Parse proxy if provided
        proxy_dict = None
        if proxy:
            proxy_dict = parse_proxy(proxy)
            if proxy_dict:
                # Convert to Telethon format
                import socks
                proxy_type = {
                    'socks5': socks.SOCKS5,
                    'socks4': socks.SOCKS4,
                    'http': socks.HTTP
                }.get(proxy_dict['proxy_type'], socks.SOCKS5)
                
                proxy_dict = (
                    proxy_type,
                    proxy_dict['addr'],
                    proxy_dict['port'],
                    True,  # RDNS
                    proxy_dict.get('username'),
                    proxy_dict.get('password')
                )
        
        try:
            client = TelegramClient(
                str(session_file),
                self.api_id,
                self.api_hash,
                proxy=proxy_dict,
                device_model="Desktop",
                system_version="Windows 10",
                app_version="4.0.0",
                lang_code="ru",
                system_lang_code="ru-RU"
            )
            
            await client.connect()
            
            if await client.is_user_authorized():
                self.clients[account_id] = client
                logger.info(f"Client ready for account {account_id} ({mask_phone(phone)})")
                return client
            else:
                logger.warning(f"Client not authorized for account {account_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating client for account {account_id}: {e}")
            return None
    
    async def disconnect(self, account_id: int):
        """Disconnect client for account"""
        if account_id in self.clients:
            try:
                await self.clients[account_id].disconnect()
            except:
                pass
            del self.clients[account_id]
    
    async def disconnect_all(self):
        """Disconnect all clients"""
        for account_id in list(self.clients.keys()):
            await self.disconnect(account_id)
    
    async def start_auth(
        self, 
        account_id: int, 
        phone: str,
        proxy: Optional[str] = None
    ) -> Optional[str]:
        """
        Start authorization process - send code request
        
        Returns:
            phone_code_hash if successful, None otherwise
        """
        session_file = SESSIONS_DIR / f"account_{account_id}.session"
        
        # Parse proxy
        proxy_dict = None
        if proxy:
            proxy_dict = parse_proxy(proxy)
            if proxy_dict:
                import socks
                proxy_type = {
                    'socks5': socks.SOCKS5,
                    'socks4': socks.SOCKS4,
                    'http': socks.HTTP
                }.get(proxy_dict['proxy_type'], socks.SOCKS5)
                
                proxy_dict = (
                    proxy_type,
                    proxy_dict['addr'],
                    proxy_dict['port'],
                    True,
                    proxy_dict.get('username'),
                    proxy_dict.get('password')
                )
        
        try:
            client = TelegramClient(
                str(session_file),
                self.api_id,
                self.api_hash,
                proxy=proxy_dict
            )
            
            await client.connect()
            
            # Send code request
            result = await client.send_code_request(phone)
            
            # Store client for later sign in
            self.clients[account_id] = client
            
            logger.info(f"Code sent to {mask_phone(phone)}")
            return result.phone_code_hash
            
        except errors.FloodWaitError as e:
            logger.error(f"FloodWait for {mask_phone(phone)}: {e.seconds}s")
            raise
        except errors.PhoneNumberBannedError:
            logger.error(f"Phone {mask_phone(phone)} is banned")
            raise
        except errors.PhoneNumberInvalidError:
            logger.error(f"Invalid phone number: {mask_phone(phone)}")
            raise
        except Exception as e:
            logger.error(f"Error starting auth for {mask_phone(phone)}: {e}")
            raise
    
    async def complete_auth(
        self,
        account_id: int,
        phone: str,
        code: str,
        phone_code_hash: str,
        password: Optional[str] = None
    ) -> bool:
        """
        Complete authorization with code (and optional 2FA password)
        
        Returns:
            True if authorized successfully
        """
        client = self.clients.get(account_id)
        if not client:
            logger.error(f"No client found for account {account_id}")
            return False
        
        try:
            # Try to sign in with code
            try:
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            except errors.SessionPasswordNeededError:
                # 2FA required
                if not password:
                    logger.warning(f"2FA required for {mask_phone(phone)}")
                    raise
                await client.sign_in(password=password)
            
            # Check if authorized
            if await client.is_user_authorized():
                logger.info(f"Successfully authorized {mask_phone(phone)}")
                return True
            else:
                return False
                
        except errors.PhoneCodeExpiredError:
            logger.error(f"Code expired for {mask_phone(phone)}")
            raise
        except errors.PhoneCodeInvalidError:
            logger.error(f"Invalid code for {mask_phone(phone)}")
            raise
        except errors.PasswordHashInvalidError:
            logger.error(f"Invalid 2FA password for {mask_phone(phone)}")
            raise
        except Exception as e:
            logger.error(f"Error completing auth for {mask_phone(phone)}: {e}")
            raise
    
    async def get_me(self, account_id: int) -> Optional[User]:
        """Get current user info"""
        client = self.clients.get(account_id)
        if not client:
            return None
        
        try:
            return await client.get_me()
        except Exception as e:
            logger.error(f"Error getting user info for account {account_id}: {e}")
            return None


class TelegramActions:
    """
    High-level Telegram actions using client manager
    """
    
    def __init__(self, client_manager: TelegramClientManager):
        self.manager = client_manager
    
    async def send_message(
        self,
        account_id: int,
        phone: str,
        target_user: int,
        message: str,
        media: Optional[str] = None,
        typing_delay: int = 0
    ) -> Dict[str, Any]:
        """
        Send message to user
        
        Args:
            account_id: Sender account ID
            phone: Sender phone
            target_user: Target Telegram ID
            message: Message text
            media: Optional media file path
            typing_delay: Seconds to simulate typing
        
        Returns:
            dict with success, message_id or error
        """
        client = await self.manager.get_client(account_id, phone)
        if not client:
            return {'success': False, 'error': 'Client not available'}
        
        try:
            # Get target entity
            try:
                entity = await client.get_input_entity(target_user)
            except (errors.UsernameNotOccupiedError, errors.UsernameInvalidError):
                return {'success': False, 'error': 'User not found'}
            except errors.PeerIdInvalidError:
                return {'success': False, 'error': 'Invalid peer'}
            
            # Simulate typing
            if typing_delay > 0:
                async with client.action(entity, 'typing'):
                    await asyncio.sleep(typing_delay)
            
            # Send message
            if media and os.path.exists(media):
                result = await client.send_file(entity, media, caption=message)
            else:
                result = await client.send_message(entity, message)
            
            return {
                'success': True,
                'message_id': result.id
            }
            
        except errors.FloodWaitError as e:
            logger.warning(f"FloodWait on send: {e.seconds}s")
            return {'success': False, 'error': 'flood_wait', 'seconds': e.seconds}
        
        except errors.UserPrivacyRestrictedError:
            return {'success': False, 'error': 'privacy_restricted'}
        
        except errors.UserIsBlockedError:
            return {'success': False, 'error': 'user_blocked'}
        
        except errors.PeerFloodError:
            return {'success': False, 'error': 'peer_flood'}
        
        except errors.ChatWriteForbiddenError:
            return {'success': False, 'error': 'write_forbidden'}
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {'success': False, 'error': str(e)}
    
    async def join_channel(
        self,
        account_id: int,
        phone: str,
        channel: str
    ) -> Dict[str, Any]:
        """
        Join channel or group
        
        Args:
            channel: Username or invite link
        
        Returns:
            dict with success or error
        """
        client = await self.manager.get_client(account_id, phone)
        if not client:
            return {'success': False, 'error': 'Client not available'}
        
        try:
            from telethon.tl.functions.channels import JoinChannelRequest
            from telethon.tl.functions.messages import ImportChatInviteRequest
            
            if 'joinchat/' in channel or '+' in channel:
                # Private invite link
                invite_hash = channel.split('/')[-1].replace('+', '')
                await client(ImportChatInviteRequest(invite_hash))
            else:
                # Public channel
                channel_entity = await client.get_entity(channel)
                await client(JoinChannelRequest(channel_entity))
            
            return {'success': True}
            
        except errors.FloodWaitError as e:
            return {'success': False, 'error': 'flood_wait', 'seconds': e.seconds}
        except errors.UserAlreadyParticipantError:
            return {'success': True}  # Already joined
        except errors.InviteHashExpiredError:
            return {'success': False, 'error': 'invite_expired'}
        except Exception as e:
            logger.error(f"Error joining channel: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_channel_participants(
        self,
        account_id: int,
        phone: str,
        channel: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get channel participants for parsing
        
        Uses Telethon's built-in get_participants which properly iterates
        through all participants, not just search results.
        
        Returns:
            dict with success, users list or error
        """
        client = await self.manager.get_client(account_id, phone)
        if not client:
            return {'success': False, 'error': 'Client not available', 'users': []}
        
        try:
            channel_entity = await client.get_entity(channel)
            
            # Use Telethon's built-in method which handles pagination properly
            # aggressive=True uses multiple API calls with different filters
            # to get ALL participants, not just search results
            participants = await client.get_participants(
                channel_entity,
                limit=limit,
                aggressive=True  # Important: gets all users, not just search results
            )
            
            users = []
            for user in participants:
                if not user.deleted:
                    users.append({
                        'telegram_id': user.id,
                        'tg_user_id': user.id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_premium': getattr(user, 'premium', False),
                        'is_bot': user.bot or False,
                        'has_photo': user.photo is not None
                    })
            
            # Get total count
            total = participants.total if hasattr(participants, 'total') else len(users)
            
            return {
                'success': True,
                'users': users,
                'total': total
            }
            
        except errors.FloodWaitError as e:
            return {'success': False, 'error': 'flood_wait', 'seconds': e.seconds, 'users': []}
        except errors.ChatAdminRequiredError:
            return {'success': False, 'error': 'admin_required', 'users': []}
        except Exception as e:
            logger.error(f"Error getting participants: {e}")
            return {'success': False, 'error': str(e), 'users': []}
    
    async def send_reaction(
        self,
        account_id: int,
        phone: str,
        channel: str,
        message_id: int,
        emoji: str = '👍'
    ) -> Dict[str, Any]:
        """
        Send reaction to message
        """
        client = await self.manager.get_client(account_id, phone)
        if not client:
            return {'success': False, 'error': 'Client not available'}
        
        try:
            from telethon.tl.functions.messages import SendReactionRequest
            from telethon.tl.types import ReactionEmoji
            
            channel_entity = await client.get_entity(channel)
            
            await client(SendReactionRequest(
                peer=channel_entity,
                msg_id=message_id,
                reaction=[ReactionEmoji(emoticon=emoji)]
            ))
            
            return {'success': True}
            
        except errors.FloodWaitError as e:
            return {'success': False, 'error': 'flood_wait', 'seconds': e.seconds}
        except errors.ReactionInvalidError:
            return {'success': False, 'error': 'invalid_reaction'}
        except Exception as e:
            logger.error(f"Error sending reaction: {e}")
            return {'success': False, 'error': str(e)}
    
    async def send_comment(
        self,
        account_id: int,
        phone: str,
        channel: str,
        message_id: int,
        comment: str
    ) -> Dict[str, Any]:
        """
        Send comment to channel post
        """
        client = await self.manager.get_client(account_id, phone)
        if not client:
            return {'success': False, 'error': 'Client not available'}
        
        try:
            from telethon.tl.functions.messages import GetDiscussionMessageRequest
            
            channel_entity = await client.get_entity(channel)
            
            # Get discussion (comments) for the post
            discussion = await client(GetDiscussionMessageRequest(
                peer=channel_entity,
                msg_id=message_id
            ))
            
            if discussion.messages:
                # Send to discussion group
                result = await client.send_message(
                    discussion.chats[0],
                    comment,
                    reply_to=discussion.messages[0].id
                )
                return {'success': True, 'comment_id': result.id}
            else:
                return {'success': False, 'error': 'no_discussion'}
            
        except errors.FloodWaitError as e:
            return {'success': False, 'error': 'flood_wait', 'seconds': e.seconds}
        except errors.MsgIdInvalidError:
            return {'success': False, 'error': 'invalid_message'}
        except Exception as e:
            logger.error(f"Error sending comment: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_channel_posts(
        self,
        account_id: int,
        phone: str,
        channel: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get recent posts from channel
        """
        client = await self.manager.get_client(account_id, phone)
        if not client:
            return {'success': False, 'error': 'Client not available', 'posts': []}
        
        try:
            channel_entity = await client.get_entity(channel)
            
            messages = await client.get_messages(channel_entity, limit=limit)
            
            posts = []
            for msg in messages:
                if msg.text or msg.media:
                    posts.append({
                        'id': msg.id,
                        'text': msg.text or '',
                        'date': msg.date.isoformat(),
                        'views': msg.views or 0,
                        'replies': getattr(msg.replies, 'replies', 0) if msg.replies else 0,
                        'has_media': msg.media is not None
                    })
            
            return {'success': True, 'posts': posts}
            
        except errors.FloodWaitError as e:
            return {'success': False, 'error': 'flood_wait', 'seconds': e.seconds, 'posts': []}
        except Exception as e:
            logger.error(f"Error getting posts: {e}")
            return {'success': False, 'error': str(e), 'posts': []}


# Global instances
client_manager = TelegramClientManager()
telegram_actions = TelegramActions(client_manager)
