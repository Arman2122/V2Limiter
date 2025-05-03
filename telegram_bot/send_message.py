"""
Send logs to telegram bot.
"""

from telegram_bot.main import application
from telegram_bot.utils import check_admin


async def send_logs(msg):
    """
    Send formatted log messages to all admin users.
    
    Args:
        msg (str): The message to send to admins
    """
    admins = await check_admin()
    retries = 2
    
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
    
    if admins:
        for admin in admins:
            for attempt in range(retries):
                try:
                    await application.bot.sendMessage(
                        chat_id=admin, text=msg, parse_mode="HTML"
                    )
                    break
                except Exception as e:  # pylint: disable=broad-except
                    print(f"Failed to send message to admin {admin} (attempt {attempt+1}): {e}")
                    if attempt == retries - 1:  # Last retry failed
                        print(f"Could not send message to admin {admin} after {retries} attempts")
    else:
        print("No admins found. Message not sent:", msg)
