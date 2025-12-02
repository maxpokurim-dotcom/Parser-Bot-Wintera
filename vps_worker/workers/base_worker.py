"""
Base worker class with common functionality
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Optional
from utils.logger import get_logger
from services.database import db
from services.notifier import notifier


class BaseWorker(ABC):
    """
    Base class for all workers
    Provides common functionality for background processing
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(name)
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    @abstractmethod
    async def process(self):
        """
        Main processing logic - must be implemented by subclasses
        Should process one batch of tasks and return
        """
        pass
    
    async def start(self, interval: int = 10):
        """
        Start worker loop
        
        Args:
            interval: Seconds between processing cycles
        """
        self.running = True
        self.logger.info(f"Starting {self.name} worker")
        
        while self.running:
            try:
                await self.process()
            except Exception as e:
                self.logger.error(f"Error in {self.name}: {e}", exc_info=True)
                await notifier.notify_error(self.name, str(e))
            
            await asyncio.sleep(interval)
    
    def stop(self):
        """Stop worker"""
        self.running = False
        self.logger.info(f"Stopping {self.name} worker")
    
    async def run_once(self):
        """Run single processing cycle (for testing)"""
        await self.process()
