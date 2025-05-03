"""Run the telegram bot."""

import asyncio
import traceback
import time

from telegram_bot.main import application, initialize_bot
from utils.logs import logger


async def run_telegram_bot():
    """Run the telegram bot."""
    logger.info("Initializing Telegram bot...")
    retry_count = 0
    max_retries = 5
    retry_delay = 10  # seconds
    
    while True:
        try:
            logger.info("Starting Telegram bot application")
            
            # First, initialize the bot with the correct token
            logger.info("Initializing bot with token from config...")
            await initialize_bot()
            
            if not application or not hasattr(application, 'bot'):
                logger.error("Bot initialization failed - application or bot not available")
                raise RuntimeError("Bot initialization failed")
                
            # Try a simple API call to verify the token is working
            try:
                me = await application.bot.get_me()
                logger.info(f"Telegram bot initialized successfully as @{me.username}")
            except Exception as e:
                logger.error(f"Bot token verification failed: {e}")
                raise RuntimeError(f"Invalid bot token: {e}")
            
            async with application:
                logger.info("Telegram bot started successfully")
                await application.start()
                await application.updater.start_polling()
                logger.info("Telegram bot polling started")
                
                # Keep the bot running
                while True:
                    await asyncio.sleep(40)
                    # Reset retry count after successful runtime
                    if retry_count > 0:
                        logger.info("Telegram bot running stably, resetting retry counter")
                        retry_count = 0
                        
        except asyncio.CancelledError:
            logger.warning("Telegram bot task was cancelled")
            break
            
        except Exception as e:  # pylint: disable=broad-except
            retry_count += 1
            error_traceback = traceback.format_exc()
            logger.error(f"Telegram bot error (attempt {retry_count}/{max_retries}): {e}")
            logger.debug(f"Traceback: {error_traceback}")
            
            # If it's a token error, provide a more helpful message
            if "Invalid token" in str(e) or "Not Found" in str(e) or "Unauthorized" in str(e):
                logger.critical("Invalid Telegram bot token. Please check your BOT_TOKEN in config.json")
                
            if retry_count >= max_retries:
                logger.critical(f"Failed to start Telegram bot after {max_retries} attempts. Will continue retrying with increased delay.")
                retry_delay = min(retry_delay * 2, 300)  # Increase delay up to 5 minutes
            
            logger.info(f"Waiting {retry_delay} seconds before retrying...")
            await asyncio.sleep(retry_delay)
            logger.info("Retrying Telegram bot initialization")
            continue
