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
        
        # Get source_type from task
        source_type = task.get('source_type', 'chat')
        
        self.logger.info(f"Task type: {source_type}")
        
        # Parse based on source_type
        if source_type == 'comments':
            # Comments on channel posts
            await self._parse_comments(task, account, channel)
        elif source_type == 'chat':
            # Chat messages - collect authors of messages
            await self._parse_messages(task, account, channel)
        elif source_type in ('participants', 'members', 'subscribers'):
            # Direct participants list (for groups only)
            await self._parse_participants(task, account, channel)
        else:
            # Default: parse messages (most common use case)
            await self._parse_messages(task, account, channel)
    
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
    
    async def _parse_messages(self, task: dict, account: dict, channel: str):
        """
        Parse users from chat messages.
        
        Reads last N messages from chat and collects unique users who wrote them.
        Supports:
        - Keyword filtering (fast, local)
        - Semantic/AI filtering (batch analysis via YandexGPT)
        """
        task_id = task['id']
        source_id = task.get('source_id') or task['id']
        phone = account['phone']
        account_id = account['id']
        user_id = task.get('owner_id') or task.get('user_id')
        
        # Get filters from task (stored as JSON in 'filters' column)
        filters = task.get('filters') or {}
        if isinstance(filters, str):
            import json
            try:
                filters = json.loads(filters)
            except:
                filters = {}
        
        # Message limit from filters.message_limit (how bot saves it)
        message_limit = filters.get('message_limit', 1000)
        
        # User filters (bot uses filter_username, filter_photo, filter_bots)
        only_with_username = filters.get('filter_username', False) or filters.get('only_with_username', False)
        only_with_photo = filters.get('filter_photo', False) or filters.get('only_with_photo', False)
        exclude_bots = filters.get('filter_bots', True) or filters.get('exclude_bots', True)
        
        # Keywords stored in separate column 'keyword_filter' (array)
        keywords = task.get('keyword_filter') or filters.get('keywords') or []
        keyword_match_mode = task.get('keyword_match_mode', 'any')  # 'any' or 'all'
        
        # Semantic config for AI-based filtering
        semantic_config = filters.get('semantic_config')
        use_semantic = bool(semantic_config and semantic_config.get('topic'))
        
        if use_semantic:
            self.logger.info(f"🧠 Semantic parsing enabled: '{semantic_config.get('topic')}'")
            # Load user's AI model preference
            await self._setup_ai_model(user_id)
        
        self.logger.info(f"Parsing message authors from {channel} (last {message_limit} messages)")
        
        # Get client
        from services.telegram_client import client_manager
        client = await client_manager.get_client(account_id, phone)
        if not client:
            db.update_parsing_task(task_id, status='error', error='Client not available')
            return
        
        try:
            # Get chat entity
            chat_entity = await client.get_entity(channel)
            
            # Collect messages and users
            users_collected = {}  # telegram_id -> user data
            messages_for_analysis = []  # For semantic analysis: [{id, text, sender_id}]
            message_senders = {}  # message_id -> sender data
            messages_processed = 0
            keyword_matches = 0
            
            # Iterate through messages
            async for message in client.iter_messages(chat_entity, limit=message_limit):
                messages_processed += 1
                
                # Skip messages without sender
                if not message.sender:
                    continue
                
                sender = message.sender
                
                # Skip deleted users
                if hasattr(sender, 'deleted') and sender.deleted:
                    continue
                
                # Skip if not a User (could be Channel forwarding)
                if not hasattr(sender, 'bot'):
                    continue
                
                # Apply user filters first
                if exclude_bots and sender.bot:
                    continue
                
                if only_with_username and not sender.username:
                    continue
                
                if only_with_photo and not sender.photo:
                    continue
                
                # Prepare user data
                user_data = {
                    'telegram_id': sender.id,
                    'tg_user_id': sender.id,
                    'username': sender.username,
                    'first_name': sender.first_name,
                    'last_name': sender.last_name,
                    'is_premium': getattr(sender, 'premium', False),
                    'is_bot': sender.bot or False,
                    'has_photo': sender.photo is not None
                }
                
                # Semantic mode: collect messages for batch analysis
                if use_semantic:
                    if message.text:
                        messages_for_analysis.append({
                            'id': message.id,
                            'text': message.text
                        })
                        message_senders[message.id] = user_data
                    # Skip messages without text in semantic mode
                    continue
                
                # Keyword mode: filter locally
                if keywords:
                    if not message.text:
                        continue
                    
                    text_lower = message.text.lower()
                    
                    if keyword_match_mode == 'all':
                        keyword_found = all(kw.lower() in text_lower for kw in keywords)
                    else:
                        keyword_found = any(kw.lower() in text_lower for kw in keywords)
                    
                    if not keyword_found:
                        continue
                    
                    keyword_matches += 1
                    if sender.id not in users_collected:
                        users_collected[sender.id] = user_data
                
                # No filter mode: collect all
                else:
                    if sender.id not in users_collected:
                        users_collected[sender.id] = user_data
                
                # Progress log every 200 messages
                if messages_processed % 200 == 0:
                    self.logger.info(f"Processed {messages_processed} messages...")
            
            # Semantic analysis: process collected messages in batches
            if use_semantic and messages_for_analysis:
                self.logger.info(f"🧠 Analyzing {len(messages_for_analysis)} messages with AI...")
                
                from services.ai_service import ai_service
                
                topic = semantic_config.get('topic', '')
                threshold = semantic_config.get('threshold', 0.7)
                depth = semantic_config.get('depth', 'medium')
                
                BATCH_SIZE = 15  # Messages per AI request
                matching_message_ids = set()
                
                for i in range(0, len(messages_for_analysis), BATCH_SIZE):
                    batch = messages_for_analysis[i:i + BATCH_SIZE]
                    
                    self.logger.info(f"  Batch {i // BATCH_SIZE + 1}: analyzing {len(batch)} messages...")
                    
                    try:
                        matched_ids = await ai_service.analyze_messages_semantic(
                            messages=batch,
                            topic=topic,
                            threshold=threshold,
                            depth=depth
                        )
                        matching_message_ids.update(matched_ids)
                        
                        self.logger.info(f"  Found {len(matched_ids)} matches in this batch")
                        
                    except Exception as e:
                        self.logger.error(f"  AI analysis error: {e}")
                    
                    # Rate limiting between batches
                    await asyncio.sleep(1)
                
                # Collect users from matching messages
                for msg_id in matching_message_ids:
                    if msg_id in message_senders:
                        sender_data = message_senders[msg_id]
                        sender_id = sender_data['telegram_id']
                        if sender_id not in users_collected:
                            users_collected[sender_id] = sender_data
                
                self.logger.info(f"🧠 Semantic analysis complete: {len(matching_message_ids)} matching messages, {len(users_collected)} unique users")
            
            filtered_users = list(users_collected.values())
            
            if keywords:
                self.logger.info(f"Keyword matches: {keyword_matches} messages with keywords")
            
            self.logger.info(f"Processed {messages_processed} messages, found {len(filtered_users)} unique users")
            
            # Save users to database
            total_parsed = 0
            if source_id and filtered_users:
                total_parsed = db.add_audience_users(source_id, filtered_users)
            else:
                total_parsed = len(filtered_users)
            
            # Complete
            db.update_parsing_task(task_id, status='completed', parsed_count=total_parsed)
            
            if source_id:
                db.update_audience_source(source_id, status='completed', total_count=total_parsed)
            
            mode = "🧠 семантический" if use_semantic else ("🔑 по ключевым" if keywords else "📝 все сообщения")
            await notifier.notify_parsing_completed(source_id or task_id, total_parsed, f"{mode} {channel}")
            self.logger.info(f"Message parsing completed: {total_parsed} users from {channel}")
            
        except Exception as e:
            self.logger.error(f"Error parsing messages: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            db.update_parsing_task(task_id, status='error', error=str(e))
    
    async def _setup_ai_model(self, user_id: int):
        """Load user's AI credentials and model preference from database"""
        try:
            if not user_id:
                self.logger.warning("No user_id provided for AI setup")
                return
            
            # Get user settings
            settings = db.get_user_settings(user_id)
            if not settings:
                self.logger.warning(f"No settings found for user {user_id}")
                return
            
            from services.ai_service import ai_service
            
            # Load API credentials from user settings (override .env)
            api_key = settings.get('yagpt_api_key')
            folder_id = settings.get('yagpt_folder_id')
            
            if api_key and folder_id:
                ai_service.yandex.api_key = api_key
                ai_service.yandex.folder_id = folder_id
                self.logger.info(f"Using user's YandexGPT credentials (folder: {folder_id[:10]}...)")
            else:
                self.logger.warning(f"User has no YandexGPT credentials configured (api_key={bool(api_key)}, folder_id={bool(folder_id)})")
            
            # Load model preference
            yandex_model = settings.get('yandex_gpt_model')
            if yandex_model:
                ai_service.set_yandex_model(yandex_model)
                self.logger.info(f"Using AI model: {yandex_model}")
            else:
                self.logger.info("No model preference set, using default")
                
        except Exception as e:
            self.logger.error(f"Could not load AI settings: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    async def _parse_comments(self, task: dict, account: dict, channel: str):
        """Parse users from post comments"""
        task_id = task['id']
        source_id = task.get('source_id') or task['id']
        phone = account['phone']
        account_id = account['id']
        
        # Get filters
        filters = task.get('filters') or {}
        if isinstance(filters, str):
            import json
            try:
                filters = json.loads(filters)
            except:
                filters = {}
        
        # Post range from filters (bot saves as post_start, post_end)
        post_start = filters.get('post_start', 1)
        post_end = filters.get('post_end', 10)
        post_limit = post_end - post_start + 1
        min_comment_length = filters.get('min_comment_length', 0)
        
        # Keywords from separate column
        keywords = task.get('keyword_filter') or []
        keyword_match_mode = task.get('keyword_match_mode', 'any')
        
        self.logger.info(f"Parsing comments from {channel} (posts {post_start}-{post_end})")
        
        # Get client for comment parsing
        from services.telegram_client import client_manager
        client = await client_manager.get_client(account_id, phone)
        if not client:
            db.update_parsing_task(task_id, status='error', error='Client not available')
            return
        
        try:
            from telethon.tl.functions.messages import GetRepliesRequest
            
            channel_entity = await client.get_entity(channel)
            
            # Get posts to parse comments from
            messages = await client.get_messages(channel_entity, limit=post_end)
            posts = messages[post_start-1:post_end] if len(messages) >= post_start else messages
            
            if not posts:
                db.update_parsing_task(task_id, status='completed', parsed_count=0)
                self.logger.info(f"No posts found in {channel}")
                return
            
            users_collected = {}  # telegram_id -> user data (dedup)
            total_comments = 0
            keyword_matches = 0
            
            for post in posts:
                post_id = post.id
                
                try:
                    # Get replies (comments) for the post
                    replies = await client(GetRepliesRequest(
                        peer=channel_entity,
                        msg_id=post_id,
                        offset_id=0,
                        offset_date=None,
                        add_offset=0,
                        limit=200,  # Up to 200 comments per post
                        max_id=0,
                        min_id=0,
                        hash=0
                    ))
                    
                    # Build user map from replies.users
                    user_map = {u.id: u for u in replies.users if hasattr(u, 'id')}
                    
                    # Process each comment message
                    for msg in replies.messages:
                        total_comments += 1
                        
                        # Skip if no text or too short
                        if not msg.message:
                            continue
                        if len(msg.message) < min_comment_length:
                            continue
                        
                        # Keyword filtering
                        if keywords:
                            text_lower = msg.message.lower()
                            if keyword_match_mode == 'all':
                                keyword_found = all(kw.lower() in text_lower for kw in keywords)
                            else:
                                keyword_found = any(kw.lower() in text_lower for kw in keywords)
                            
                            if not keyword_found:
                                continue
                            keyword_matches += 1
                        
                        # Get user who wrote this comment
                        sender_id = msg.from_id.user_id if hasattr(msg.from_id, 'user_id') else None
                        if not sender_id or sender_id not in user_map:
                            continue
                        
                        user = user_map[sender_id]
                        
                        # Skip bots
                        if hasattr(user, 'bot') and user.bot:
                            continue
                        
                        # Skip deleted users
                        if hasattr(user, 'deleted') and user.deleted:
                            continue
                        
                        # Add user if not collected
                        if user.id not in users_collected:
                            users_collected[user.id] = {
                                'telegram_id': user.id,
                                'tg_user_id': user.id,
                                'username': user.username,
                                'first_name': user.first_name,
                                'last_name': user.last_name,
                                'is_premium': getattr(user, 'premium', False),
                                'is_bot': False,
                                'has_photo': user.photo is not None
                            }
                    
                except Exception as e:
                    self.logger.debug(f"Could not get comments for post {post_id}: {e}")
                    continue
                
                # Small delay between posts
                await asyncio.sleep(0.5)
            
            self.logger.info(f"Processed {total_comments} comments from {len(posts)} posts")
            if keywords:
                self.logger.info(f"Keyword matches: {keyword_matches} comments")
            
            filtered_users = list(users_collected.values())
            
            # Save users to database
            total_parsed = 0
            if source_id and filtered_users:
                total_parsed = db.add_audience_users(source_id, filtered_users)
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
