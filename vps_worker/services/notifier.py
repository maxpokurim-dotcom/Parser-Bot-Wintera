"""
Notifier service - Send notifications via Telegram bot
"""
import aiohttp
import asyncio
from typing import Optional
from config import config
from utils.logger import get_logger

logger = get_logger('notifier')


class Notifier:
    """Send notifications to admin via Telegram bot"""
    
    def __init__(self):
        self.bot_token = config.telegram.bot_token
        self.admin_chat_id = config.telegram.admin_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_message(
        self, 
        text: str, 
        chat_id: Optional[int] = None,
        parse_mode: str = 'HTML',
        disable_notification: bool = False
    ) -> bool:
        """
        Send message via Telegram bot
        
        Args:
            text: Message text
            chat_id: Target chat ID (defaults to admin)
            parse_mode: HTML or Markdown
            disable_notification: Silent notification
        
        Returns:
            True if sent successfully
        """
        if not self.bot_token:
            logger.warning("Bot token not configured, cannot send notification")
            return False
        
        target_chat = chat_id or self.admin_chat_id
        if not target_chat:
            logger.warning("No chat ID for notification")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        'chat_id': target_chat,
                        'text': text,
                        'parse_mode': parse_mode,
                        'disable_notification': disable_notification
                    }
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"Telegram API error: {error}")
                        return False
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    async def notify_campaign_started(self, campaign_id: int, total_count: int, accounts_count: int):
        """Notify about campaign start"""
        await self.send_message(
            f"🚀 <b>Рассылка #{campaign_id} запущена</b>\n\n"
            f"👥 Получателей: <b>{total_count}</b>\n"
            f"👤 Аккаунтов: <b>{accounts_count}</b>"
        )
    
    async def notify_campaign_progress(self, campaign_id: int, sent: int, failed: int, total: int):
        """Notify about campaign progress"""
        percent = int(sent / total * 100) if total > 0 else 0
        progress = '█' * (percent // 10) + '░' * (10 - percent // 10)
        
        await self.send_message(
            f"📊 <b>Прогресс рассылки #{campaign_id}</b>\n\n"
            f"[{progress}] {percent}%\n"
            f"✅ Отправлено: {sent}\n"
            f"❌ Ошибок: {failed}\n"
            f"👥 Всего: {total}",
            disable_notification=True
        )
    
    async def notify_campaign_completed(self, campaign_id: int, sent: int, failed: int):
        """Notify about campaign completion"""
        await self.send_message(
            f"✅ <b>Рассылка #{campaign_id} завершена!</b>\n\n"
            f"✅ Отправлено: <b>{sent}</b>\n"
            f"❌ Ошибок: <b>{failed}</b>"
        )
    
    async def notify_campaign_paused(self, campaign_id: int, reason: str):
        """Notify about campaign pause"""
        await self.send_message(
            f"⏸ <b>Рассылка #{campaign_id} приостановлена</b>\n\n"
            f"Причина: {reason}"
        )
    
    async def notify_account_error(self, account_id: int, phone: str, error: str):
        """Notify about account error"""
        masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
        await self.send_message(
            f"⚠️ <b>Ошибка аккаунта #{account_id}</b>\n\n"
            f"📱 Телефон: <code>{masked}</code>\n"
            f"❌ Ошибка: {error}"
        )
    
    async def notify_account_flood(self, account_id: int, phone: str, seconds: int):
        """Notify about flood wait"""
        masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
        minutes = seconds // 60
        await self.send_message(
            f"⏰ <b>FloodWait на аккаунте #{account_id}</b>\n\n"
            f"📱 Телефон: <code>{masked}</code>\n"
            f"⏱ Ожидание: {minutes} мин"
        )
    
    async def notify_account_authorized(self, account_id: int, phone: str):
        """Notify about successful authorization"""
        masked = f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else phone
        await self.send_message(
            f"✅ <b>Аккаунт авторизован</b>\n\n"
            f"📱 Телефон: <code>{masked}</code>\n"
            f"🆔 ID: {account_id}"
        )
    
    async def notify_parsing_completed(self, source_id: int, count: int, source_link: str):
        """Notify about parsing completion"""
        await self.send_message(
            f"✅ <b>Парсинг завершён</b>\n\n"
            f"📊 Источник: {source_link}\n"
            f"👥 Собрано: <b>{count}</b> пользователей"
        )
    
    async def notify_error(self, module: str, error: str):
        """Notify about general error"""
        await self.send_message(
            f"❌ <b>Ошибка в модуле {module}</b>\n\n"
            f"<code>{error[:500]}</code>"
        )
    
    async def notify_worker_started(self):
        """Notify that worker has started"""
        await self.send_message(
            f"🟢 <b>VPS Worker запущен</b>\n\n"
            f"Все сервисы активны."
        )
    
    async def notify_worker_stopped(self):
        """Notify that worker has stopped"""
        await self.send_message(
            f"🔴 <b>VPS Worker остановлен</b>"
        )


# Global notifier instance
notifier = Notifier()
