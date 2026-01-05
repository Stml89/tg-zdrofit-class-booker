"""Main bot application."""

import asyncio
from telegram.ext import Application
from telegram import Bot
from telegram.request import HTTPXRequest

from src.telegram_bot.handlers import setup_bot_handlers
from src.scheduler.class_scheduler import scheduler
from src.utils.logger import get_logger
from config.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CONNECT_TIMEOUT,
    TELEGRAM_READ_TIMEOUT,
    TELEGRAM_WRITE_TIMEOUT,
    TELEGRAM_POOL_TIMEOUT,
    TELEGRAM_POOL_SIZE
)

logger = get_logger(__name__)


class ZdrofitBot:
    """Main Telegram bot application."""
    
    def __init__(self):
        # Configure HTTP client with timeouts
        http_client = HTTPXRequest(
            connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
            read_timeout=TELEGRAM_READ_TIMEOUT,
            write_timeout=TELEGRAM_WRITE_TIMEOUT,
            pool_timeout=TELEGRAM_POOL_TIMEOUT,
            connection_pool_size=TELEGRAM_POOL_SIZE
        )
        bot = Bot(token=TELEGRAM_BOT_TOKEN, request=http_client)
        self.app = Application.builder().bot(bot).build()
        self.scheduler = scheduler
        # Pass app to scheduler so it can use the same bot
        self.scheduler.app = self.app
    
    def setup(self):
        """Setup bot handlers and features."""
        logger.info("Setting up bot...")
        setup_bot_handlers(self.app)
        logger.info("Bot setup complete")
    
    async def start(self):
        """Start the bot."""
        logger.info("Starting Telegram bot...")
        
        # Get the current event loop and pass it to scheduler
        import asyncio as asyncio_module
        loop = asyncio_module.get_event_loop()
        self.scheduler.loop = loop
        
        # Start scheduler for class checking
        self.scheduler.start()
        
        # Start bot polling
        async with self.app:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(allowed_updates=['message', 'callback_query'])
            logger.info("Bot started successfully!")
            
            # Keep running
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                await self.stop()
    
    async def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping bot...")
        
        # Stop scheduler
        self.scheduler.stop()
        
        # Stop polling
        if self.app.updater.running:
            await self.app.updater.stop()
        await self.app.stop()
        
        logger.info("Bot stopped")


def main():
    """Main entry point."""
    logger.info("=" * 50)
    logger.info("Starting Zdrofit Class Booker Bot")
    logger.info("=" * 50)
    
    try:
        bot = ZdrofitBot()
        bot.setup()
        asyncio.run(bot.start())
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
