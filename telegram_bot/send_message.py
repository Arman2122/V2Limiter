"""
Send logs to telegram bot.
"""

import asyncio
import traceback

# Remove direct import that causes circular dependency
# from telegram_bot.main import application
# from telegram_bot.utils import check_admin
from utils.logs import logger
from utils.read_config import read_config

# We'll get the application instance lazily to avoid circular imports
def get_application():
    """Get the application instance lazily to avoid circular imports."""
    from telegram_bot.main import application
    return application

# Get check_admin function lazily to avoid circular imports
def get_check_admin():
    """Get the check_admin function lazily to avoid circular imports."""
    from telegram_bot.utils import check_admin
    return check_admin

# This variable is set by telegram_bot.main on initialization
_extra_context = None

def set_extra_context(context):
    """
    Set extra context for logging to properly handle messages.
    This is called from telegram_bot.main
    """
    global _extra_context
    _extra_context = context


async def send_logs(msg):
    """
    Send formatted log messages to all admin users.
    
    Args:
        msg (str): The message to send to admins
    """
    # Check if notifications are enabled
    config_data = await read_config()
    send_notifications = config_data.get("SEND_NOTIFICATIONS", True)
    
    if not send_notifications:
        logger.info("Notifications are disabled in config. Message not sent.")
        return
    
    # Get check_admin function lazily
    check_admin = get_check_admin()
    admins = await check_admin()
    retries = 3
    retry_delay = 2  # seconds
    
    # Format the message if it's not already HTML formatted
    if not (msg.startswith("<b>") or msg.startswith("<code>") or 
            msg.startswith("✅") or msg.startswith("⚠️") or 
            msg.startswith("❌") or msg.startswith("ℹ️")):
        if "ERROR" in msg or "error" in msg or "failed" in msg or "Failed" in msg:
            msg = f"❌ <b>Error:</b>\n\n<code>{msg}</code>"
        elif "WARNING" in msg or "warning" in msg:
            msg = f"⚠️ <b>Warning:</b>\n\n<code>{msg}</code>"
        elif "success" in msg or "Success" in msg or "added" in msg or "Added" in msg:
            msg = f"✅ <b>Success:</b>\n\n<code>{msg}</code>"
        else:
            msg = f"ℹ️ <b>Info:</b>\n\n<code>{msg}</code>"
    
    if not admins:
        logger.warning("No admins found. Message not sent")
        return
        
    logger.debug(f"Sending message to {len(admins)} admins")
    successful_sends = 0
    
    try:
        # Get application instance only when needed
        app = get_application()
        
        # Don't check for placeholder token specifically, as it might be real token
        # Instead rely on try/except to catch any token errors
        
        for admin in admins:
            for attempt in range(retries):
                try:
                    await app.bot.sendMessage(
                        chat_id=admin, text=msg, parse_mode="HTML"
                    )
                    logger.debug(f"Message sent to admin {admin}")
                    successful_sends += 1
                    break
                except asyncio.CancelledError:
                    logger.warning("Message sending cancelled")
                    return
                except Exception as e:  # pylint: disable=broad-except
                    # Check if it's a token error
                    if "Invalid token" in str(e) or "Not Found" in str(e):
                        logger.error("Invalid Telegram token. Unable to send messages.")
                        return  # Exit early, no point in retrying with other admins
                    
                    error_msg = f"Failed to send message to admin {admin} (attempt {attempt+1}/{retries}): {e}"
                    if attempt < retries - 1:
                        logger.warning(error_msg)
                        await asyncio.sleep(retry_delay)
                    else:  # Last retry failed
                        logger.error(f"{error_msg}\nTraceback: {traceback.format_exc()}")
                        logger.error(f"Could not send message to admin {admin} after {retries} attempts")
        
        if successful_sends == 0:
            logger.error("Failed to send message to any admin")
        elif successful_sends < len(admins):
            logger.warning(f"Message sent to {successful_sends}/{len(admins)} admins")
    except Exception as e:
        logger.error(f"Error in send_logs: {e}", exc_info=True)
