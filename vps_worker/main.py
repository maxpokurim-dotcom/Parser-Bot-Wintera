#!/usr/bin/env python3
"""
VPS Worker - Main Entry Point
Runs all background workers for Telegram bot operations
"""
import asyncio
import signal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import config, LOGS_DIR
from utils.logger import setup_logger, get_logger
from services.notifier import notifier
from services.telegram_client import client_manager

from workers import (
    AuthWorker,
    MailingWorker,
    ParsingWorker,
    HerderWorker,
    WarmupWorker,
    SchedulerWorker,
    FactoryWorker
)


# Setup main logger
logger = setup_logger('vps_worker', LOGS_DIR)


class WorkerManager:
    """
    Manages all worker instances
    Handles startup, shutdown, and task coordination
    """
    
    def __init__(self):
        self.workers = []
        self.tasks = []
        self.running = False
    
    def add_worker(self, worker, interval: int = 10):
        """Add worker to manager"""
        self.workers.append((worker, interval))
    
    async def start(self):
        """Start all workers"""
        self.running = True
        logger.info("Starting VPS Worker Manager...")
        
        # Notify admin
        try:
            await notifier.notify_worker_started()
        except Exception as e:
            logger.warning(f"Could not send start notification: {e}")
        
        # Create tasks for each worker
        for worker, interval in self.workers:
            task = asyncio.create_task(worker.start(interval))
            self.tasks.append(task)
            logger.info(f"Started {worker.name} (interval: {interval}s)")
        
        logger.info(f"All {len(self.workers)} workers started")
        
        # Wait for all tasks
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except asyncio.CancelledError:
            logger.info("Workers cancelled")
    
    async def stop(self):
        """Stop all workers gracefully"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping VPS Worker Manager...")
        
        # Stop each worker
        for worker, _ in self.workers:
            worker.stop()
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for cleanup
        await asyncio.sleep(1)
        
        # Disconnect all Telegram clients
        await client_manager.disconnect_all()
        
        # Notify admin
        try:
            await notifier.notify_worker_stopped()
        except:
            pass
        
        logger.info("VPS Worker Manager stopped")


async def main():
    """Main entry point"""
    logger.info("=" * 50)
    logger.info("VPS Worker starting...")
    logger.info(f"Poll interval: {config.worker.poll_interval}s")
    logger.info(f"Max concurrent tasks: {config.worker.max_concurrent_tasks}")
    logger.info("=" * 50)
    
    # Create worker manager
    manager = WorkerManager()
    
    # Add workers with different intervals
    manager.add_worker(AuthWorker(), interval=5)           # Check auth tasks frequently
    manager.add_worker(MailingWorker(), interval=10)       # Process mailings
    manager.add_worker(ParsingWorker(), interval=30)       # Process parsing tasks
    manager.add_worker(HerderWorker(), interval=60)        # Herder activity
    manager.add_worker(WarmupWorker(), interval=300)       # Warmup every 5 min
    manager.add_worker(SchedulerWorker(), interval=30)     # Check scheduled tasks
    manager.add_worker(FactoryWorker(), interval=60)       # Auto-create accounts
    
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(manager.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # Start workers
    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await manager.stop()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
