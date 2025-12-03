"""
AI Service - YandexGPT and OpenAI integration
For content generation, comment creation, and message personalization
"""
import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger

logger = get_logger('ai_service')


class AIProvider(Enum):
    YANDEX = "yandex"
    OPENAI = "openai"


# Available Yandex models
YANDEX_MODELS = {
    'aliceai-llm': 'Alice AI LLM (новейшая)',
    'yandexgpt-5.1': 'YandexGPT 5.1 Pro',
    'yandexgpt-5-pro': 'YandexGPT 5 Pro', 
    'yandexgpt-5-lite': 'YandexGPT 5 Lite',
    'yandexgpt-4-lite': 'YandexGPT 4 Lite',
    'yandexgpt-lite': 'YandexGPT Lite (legacy)',
}


@dataclass
class AIConfig:
    """AI service configuration"""
    # YandexGPT
    yandex_folder_id: str = ""
    yandex_api_key: str = ""
    yandex_iam_token: str = ""
    yandex_model: str = "yandexgpt-5-lite"  # Default model
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    
    # General
    default_provider: AIProvider = AIProvider.YANDEX
    max_tokens: int = 500
    temperature: float = 0.7
    
    @classmethod
    def from_env(cls) -> "AIConfig":
        return cls(
            yandex_folder_id=os.getenv('YANDEX_CLOUD_FOLDER_ID', ''),
            yandex_api_key=os.getenv('YANDEX_CLOUD_API_KEY', ''),
            yandex_iam_token=os.getenv('YANDEX_CLOUD_IAM_TOKEN', ''),
            yandex_model=os.getenv('YANDEX_GPT_MODEL', 'yandexgpt-5-lite'),
            openai_api_key=os.getenv('OPENAI_API_KEY', ''),
            openai_model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        )


class YandexGPT:
    """YandexGPT API client"""
    
    BASE_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1"
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.folder_id = config.yandex_folder_id
        self.api_key = config.yandex_api_key
        self.iam_token = config.yandex_iam_token
        self.model = config.yandex_model
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        headers = {"Content-Type": "application/json"}
        
        if self.iam_token:
            headers["Authorization"] = f"Bearer {self.iam_token}"
        elif self.api_key:
            headers["Authorization"] = f"Api-Key {self.api_key}"
        else:
            raise ValueError("YandexGPT: No API key or IAM token provided")
        
        return headers
    
    def _get_model_uri(self, model_override: Optional[str] = None) -> str:
        """Get model URI"""
        model = model_override or self.model
        
        # If already a full URI, return as is
        if model and model.startswith('gpt://'):
            return model
        
        # Validate we have required components
        if not self.folder_id:
            logger.error("YandexGPT: folder_id is not set!")
            return ""
        
        if not model:
            model = 'yandexgpt-5-lite'  # Default fallback
        
        uri = f"gpt://{self.folder_id}/{model}/latest"
        logger.debug(f"Model URI: {uri}")
        return uri
    
    def set_model(self, model: str):
        """Set the model to use"""
        self.model = model
        logger.info(f"YandexGPT model set to: {model}")
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Optional[str]:
        """
        Generate text using YandexGPT
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            max_tokens: Maximum response length
            temperature: Creativity (0-1)
        
        Returns:
            Generated text or None on error
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "text": system_prompt
            })
        
        messages.append({
            "role": "user", 
            "text": prompt
        })
        
        model_uri = self._get_model_uri()
        
        if not model_uri:
            logger.error("Cannot generate: model_uri is empty")
            return None
        
        payload = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": str(max_tokens)
            },
            "messages": messages
        }
        
        logger.info(f"YandexGPT request: model={model_uri}, folder={self.folder_id}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/completion",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get("result", {})
                        alternatives = result.get("alternatives", [])
                        if alternatives:
                            return alternatives[0].get("message", {}).get("text", "")
                    else:
                        error_text = await response.text()
                        logger.error(f"YandexGPT error {response.status}: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"YandexGPT request error: {e}")
            return None
        
        return None
    
    async def is_available(self) -> bool:
        """Check if YandexGPT is configured and available"""
        if not self.folder_id:
            return False
        if not self.api_key and not self.iam_token:
            return False
        return True


class OpenAIClient:
    """OpenAI API client"""
    
    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.api_key = config.openai_api_key
        self.model = config.openai_model
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Optional[str]:
        """Generate text using OpenAI"""
        if not self.api_key:
            return None
        
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenAI error {response.status}: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"OpenAI request error: {e}")
            return None
        
        return None
    
    async def is_available(self) -> bool:
        """Check if OpenAI is configured"""
        return bool(self.api_key)


class AIService:
    """
    Unified AI service for content generation
    Supports YandexGPT (primary) and OpenAI (fallback)
    """
    
    # System prompts for different tasks
    PROMPTS = {
        "comment_expert": """Ты эксперт в Telegram-каналах. Твоя задача - писать короткие, 
естественные комментарии к постам. Комментарии должны быть:
- На русском языке
- Короткие (1-3 предложения)
- Релевантные теме поста
- Без спама и рекламы
- Как от реального человека""",

        "comment_support": """Ты активный подписчик канала. Пишешь короткие поддерживающие 
комментарии. Стиль - разговорный, дружелюбный. Можешь использовать эмодзи.""",

        "comment_trendsetter": """Ты трендсеттер, который первым реагирует на посты. 
Пишешь короткие, энергичные комментарии. Показываешь энтузиазм.""",

        "message_personalize": """Ты помощник по персонализации сообщений. 
Адаптируй текст под получателя, делая его более личным и релевантным.""",

        "content_generate": """Ты копирайтер для Telegram-каналов. 
Создаёшь вовлекающий контент на русском языке. 
Используешь эмодзи уместно. Форматируешь текст для удобного чтения.""",

        "content_rewrite": """Ты рерайтер. Переписываешь текст своими словами, 
сохраняя смысл, но меняя формулировки. Делаешь текст уникальным.""",

        "analyze_channel": """Ты аналитик Telegram-каналов. 
Анализируешь контент и даёшь краткие выводы о тематике, стиле и аудитории."""
    }
    
    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or AIConfig.from_env()
        self.yandex = YandexGPT(self.config)
        self.openai = OpenAIClient(self.config)
    
    async def generate(
        self,
        prompt: str,
        task: str = "content_generate",
        custom_system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        provider: Optional[AIProvider] = None
    ) -> Optional[str]:
        """
        Generate text using available AI provider
        
        Args:
            prompt: User prompt
            task: Task type (key from PROMPTS)
            custom_system_prompt: Override system prompt
            max_tokens: Max response length
            temperature: Creativity level
            provider: Force specific provider
        
        Returns:
            Generated text or None
        """
        system_prompt = custom_system_prompt or self.PROMPTS.get(task, "")
        
        # Determine provider order
        if provider:
            providers = [provider]
        else:
            # Try YandexGPT first (better for Russian), then OpenAI
            providers = [AIProvider.YANDEX, AIProvider.OPENAI]
        
        for prov in providers:
            result = None
            
            if prov == AIProvider.YANDEX and await self.yandex.is_available():
                result = await self.yandex.generate(
                    prompt, system_prompt, max_tokens, temperature
                )
            elif prov == AIProvider.OPENAI and await self.openai.is_available():
                result = await self.openai.generate(
                    prompt, system_prompt, max_tokens, temperature
                )
            
            if result:
                return result
        
        logger.warning("No AI provider available for generation")
        return None
    
    async def generate_comment(
        self,
        post_text: str,
        strategy: str = "expert",
        account_profile: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Generate comment for a post
        
        Args:
            post_text: Post content to comment on
            strategy: Comment strategy (expert, support, trendsetter)
            account_profile: Optional account persona
        
        Returns:
            Generated comment
        """
        task = f"comment_{strategy}"
        if task not in self.PROMPTS:
            task = "comment_support"
        
        # Build prompt
        prompt = f"""Пост в канале:
"{post_text[:500]}"

Напиши короткий комментарий к этому посту (1-2 предложения)."""
        
        if account_profile:
            persona = account_profile.get('persona', '')
            interests = account_profile.get('interests', [])
            if persona or interests:
                prompt += f"\n\nТвоя роль: {persona}. Интересы: {', '.join(interests)}."
        
        return await self.generate(
            prompt=prompt,
            task=task,
            max_tokens=150,
            temperature=0.8
        )
    
    async def personalize_message(
        self,
        template: str,
        recipient: Dict,
        context: Optional[str] = None
    ) -> str:
        """
        Personalize message template for recipient
        
        Args:
            template: Message template with placeholders
            recipient: Recipient info (first_name, username, etc.)
            context: Additional context
        
        Returns:
            Personalized message
        """
        # First, simple placeholder replacement
        replacements = {
            '{first_name}': recipient.get('first_name') or '',
            '{last_name}': recipient.get('last_name') or '',
            '{username}': recipient.get('username') or '',
            '{name}': recipient.get('first_name') or recipient.get('username') or '',
        }
        
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        # If AI personalization requested and available
        if '{ai_personalize}' in template or context:
            prompt = f"""Персонализируй это сообщение для получателя:

Сообщение: {result}

Получатель: {recipient.get('first_name', 'Пользователь')}
{"Контекст: " + context if context else ""}

Сделай сообщение более личным, но сохрани основной смысл."""
            
            ai_result = await self.generate(
                prompt=prompt,
                task="message_personalize",
                max_tokens=len(template) + 100,
                temperature=0.6
            )
            
            if ai_result:
                result = ai_result
        
        return result
    
    async def generate_post(
        self,
        topic: str,
        style: str = "informative",
        length: str = "medium",
        include_emoji: bool = True
    ) -> Optional[str]:
        """
        Generate post content
        
        Args:
            topic: Post topic
            style: Writing style (informative, casual, promotional)
            length: Post length (short, medium, long)
            include_emoji: Add emojis
        
        Returns:
            Generated post
        """
        length_tokens = {
            "short": 100,
            "medium": 300,
            "long": 500
        }
        
        prompt = f"""Создай пост для Telegram-канала.

Тема: {topic}
Стиль: {style}
{'Используй эмодзи для визуального оформления.' if include_emoji else 'Без эмодзи.'}

Пост должен быть вовлекающим и легко читаемым."""
        
        return await self.generate(
            prompt=prompt,
            task="content_generate",
            max_tokens=length_tokens.get(length, 300),
            temperature=0.8
        )
    
    async def rewrite_text(self, text: str, style: Optional[str] = None) -> Optional[str]:
        """
        Rewrite text to make it unique
        
        Args:
            text: Original text
            style: Optional style modifier
        
        Returns:
            Rewritten text
        """
        prompt = f"""Перепиши этот текст своими словами, сохранив смысл:

"{text}"

{"Стиль: " + style if style else ""}
Сделай текст уникальным, но сохрани основную идею."""
        
        return await self.generate(
            prompt=prompt,
            task="content_rewrite",
            max_tokens=len(text) + 200,
            temperature=0.7
        )
    
    async def analyze_channel_content(self, posts: List[str]) -> Optional[Dict]:
        """
        Analyze channel content
        
        Args:
            posts: List of recent post texts
        
        Returns:
            Analysis dict with topics, style, recommendations
        """
        sample = "\n---\n".join(posts[:5])
        
        prompt = f"""Проанализируй эти посты из Telegram-канала:

{sample}

Дай краткий анализ в формате JSON:
{{
    "main_topics": ["тема1", "тема2"],
    "content_style": "стиль контента",
    "target_audience": "описание аудитории",
    "posting_recommendations": ["рекомендация1", "рекомендация2"]
}}"""
        
        result = await self.generate(
            prompt=prompt,
            task="analyze_channel",
            max_tokens=500,
            temperature=0.5
        )
        
        if result:
            try:
                # Try to parse JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
        
        return None
    
    async def get_available_provider(self) -> Optional[str]:
        """Get name of available AI provider"""
        if await self.yandex.is_available():
            return "YandexGPT"
        if await self.openai.is_available():
            return "OpenAI"
        return None
    
    def set_yandex_model(self, model: str):
        """Set YandexGPT model"""
        self.yandex.set_model(model)
    
    def set_yandex_credentials(self, api_key: str, folder_id: str):
        """Set YandexGPT API credentials (override .env)"""
        self.yandex.api_key = api_key
        self.yandex.folder_id = folder_id
        logger.info(f"YandexGPT credentials updated (folder: {folder_id[:8]}...)")
    
    async def analyze_messages_semantic(
        self,
        messages: List[Dict],
        topic: str,
        threshold: float = 0.7,
        depth: str = "medium"
    ) -> List[int]:
        """
        Analyze batch of messages for semantic relevance to topic.
        
        Args:
            messages: List of dicts with 'id' and 'text' keys
            topic: Topic/theme to match against
            threshold: Relevance threshold (0-1)
            depth: Search depth (narrow/medium/wide)
        
        Returns:
            List of message IDs that match the topic
        """
        if not messages:
            return []
        
        # Build message list for prompt
        msg_list = []
        for i, msg in enumerate(messages):
            msg_id = msg.get('id', i)
            text = msg.get('text', '')[:300]  # Truncate long messages
            if text:
                msg_list.append(f"[{msg_id}] {text}")
        
        if not msg_list:
            return []
        
        messages_text = "\n".join(msg_list)
        
        # Depth affects how strict the matching is
        depth_instructions = {
            'narrow': "Ищи ТОЛЬКО сообщения, которые ТОЧНО соответствуют теме. Будь очень строгим.",
            'medium': "Ищи сообщения, которые соответствуют теме напрямую или косвенно связаны с ней.",
            'wide': "Ищи любые сообщения, которые хоть как-то связаны с темой или её общей областью."
        }
        
        depth_instruction = depth_instructions.get(depth, depth_instructions['medium'])
        
        prompt = f"""Проанализируй сообщения и найди те, которые соответствуют теме.

ТЕМА: {topic}

ИНСТРУКЦИЯ: {depth_instruction}
Порог релевантности: {int(threshold * 100)}%

СООБЩЕНИЯ:
{messages_text}

ЗАДАЧА: Верни ТОЛЬКО номера сообщений (в квадратных скобках), которые соответствуют теме.
Формат ответа: список номеров через запятую, например: 1, 5, 12, 23
Если ни одно сообщение не подходит, верни: НЕТ

ОТВЕТ:"""

        system_prompt = """Ты анализатор сообщений. Твоя задача - определить релевантность сообщений заданной теме.
Отвечай ТОЛЬКО номерами сообщений или словом "НЕТ". Никаких пояснений."""

        result = await self.generate(
            prompt=prompt,
            custom_system_prompt=system_prompt,
            max_tokens=200,
            temperature=0.3  # Low temperature for consistent results
        )
        
        if not result:
            logger.warning("AI returned no result for semantic analysis")
            return []
        
        logger.debug(f"AI semantic response: {result}")
        
        # Parse response - extract numbers
        if 'НЕТ' in result.upper() or 'NONE' in result.upper():
            return []
        
        import re
        # Find all numbers in the response
        numbers = re.findall(r'\d+', result)
        matching_ids = []
        
        # Map back to original message IDs
        msg_id_map = {i: msg.get('id', i) for i, msg in enumerate(messages)}
        valid_ids = {msg.get('id', i) for i, msg in enumerate(messages)}
        
        for num_str in numbers:
            try:
                num = int(num_str)
                if num in valid_ids:
                    matching_ids.append(num)
            except ValueError:
                continue
        
        logger.info(f"Semantic analysis: {len(matching_ids)} matches out of {len(messages)} messages")
        return matching_ids


# Global AI service instance
ai_service = AIService()
