"""
This module contains the main functionality of a Telegram bot.
It includes functions for adding admins,
listing admins, setting special limits, and creating a config and more...
"""

import asyncio
import os
import sys
import re
import json

try:
    from telegram import Update
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        ContextTypes,
        ConversationHandler,
        MessageHandler,
        filters,
    )
except ImportError:
    print(
        "Module 'python-telegram-bot' is not installed use:"
        + " 'pip install python-telegram-bot' to install it"
    )
    sys.exit()

from telegram_bot.utils import (
    add_admin_to_config,
    add_base_information,
    add_except_user,
    check_admin,
    get_special_limit_list,
    handel_special_limit,
    read_json_file,
    remove_admin_from_config,
    remove_except_user_from_config,
    save_check_interval,
    save_general_limit,
    save_time_to_active_users,
    show_except_users_handler,
    toggle_ip_location_check,
    write_country_code_json,
)
from utils.logs import logger
from utils.read_config import read_config
from api.token_utils import generate_and_save_token, get_token_from_config

(
    GET_DOMAIN,
    GET_PORT,
    GET_USERNAME,
    GET_PASSWORD,
    GET_CONFIRMATION,
    GET_CHAT_ID,
    GET_SPECIAL_LIMIT,
    GET_LIMIT_NUMBER,
    GET_CHAT_ID_TO_REMOVE,
    SET_COUNTRY_CODE,
    SET_EXCEPT_USERS,
    REMOVE_EXCEPT_USER,
    GET_GENERAL_LIMIT_NUMBER,
    GET_CHECK_INTERVAL,
    GET_TIME_TO_ACTIVE_USERS,
) = range(15)

# Replace the direct asyncio.run() call with a lazy-loading approach
# Initialize with None and load it during application startup
config_data = None
bot_token = None

# Function to load config data
async def load_config():
    global config_data, bot_token
    config_data = await read_config()
    try:
        bot_token = config_data["BOT_TOKEN"]
    except KeyError as exc:
        raise ValueError("BOT_TOKEN is missing in the config file.") from exc
    return bot_token

# Function to get the bot token synchronously from the config file
def get_bot_token_sync():
    """Get bot token directly from config file synchronously"""
    config_file = "config.json"
    if not os.path.exists(config_file):
        logger.error("Config file not found")
        return None
        
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            if "BOT_TOKEN" not in config:
                logger.error("BOT_TOKEN not found in config file")
                return None
            return config["BOT_TOKEN"]
    except (json.JSONDecodeError, IOError) as error:
        logger.error(f"Error reading config file: {error}")
        return None

# Try to read the token directly from the config file
initial_token = get_bot_token_sync() or "placeholder_token"
logger.info(f"Initializing application with {'valid token' if initial_token != 'placeholder_token' else 'placeholder token'}")

# Initialize the application with the token from config if available
application = ApplicationBuilder().token(initial_token).build()

# Initialize user data storage
application.user_data = {}

# We'll update the token when it's actually needed
async def initialize_bot():
    """Initialize the bot with the correct token."""
    global application
    token = await load_config()
    
    # If we're already using the correct token, no need to rebuild
    if token == initial_token and token != "placeholder_token":
        logger.info("Telegram bot already initialized with correct token")
        return
    
    # Save existing user_data if any
    existing_user_data = getattr(application, "user_data", {})
    
    # Create a new application with the correct token
    application = ApplicationBuilder().token(token).build()
    
    # Restore user_data
    application.user_data = existing_user_data
    
    logger.info("Telegram bot initialized with token from config")


START_MESSAGE = """
🚀 <b>Welcome to Marz-Limiter Bot</b> 🚀

📋 <b>COMMANDS:</b>

🔹 <b>Setup Commands:</b>
  • /start - <i>Start the bot and show all commands</i>
  • /create_config - <i>Configure panel credentials</i>
  • /country_code - <i>Set your country for better IP filtering</i>
  • /toggle_ip_location - <i>Enable/disable IP location checking</i>
  • /set_general_limit_number - <i>Set default IP limit</i>
  • /set_check_interval - <i>Set checking frequency</i>
  • /set_time_to_active_users - <i>Set user reactivation time</i>

🔹 <b>User Management:</b>
  • /set_special_limit - <i>Set custom IP limits for specific users</i>
  • /show_special_limit - <i>View all custom IP limits</i>
  • /set_except_user - <i>Add user to exception list</i>
  • /remove_except_user - <i>Remove user from exception list</i>
  • /show_except_users - <i>View all excepted users</i>

🔹 <b>Admin Controls:</b>
  • /add_admin - <i>Grant admin access to another user</i>
  • /admins_list - <i>View all bot administrators</i>
  • /remove_admin - <i>Revoke admin access</i>
  • /backup - <i>Download config backup file</i>

🔹 <b>API Management:</b>
  • /get_api_token - <i>View or generate API token</i>

⚙️ <b>For support:</b> @YourSupportUsername
"""


async def add_admin(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Adds an admin to the bot.
    At first checks if the user has admin privileges.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    if len(await check_admin()) > 5:
        await update.message.reply_html(
            text="⚠️ <b>Admin Limit Reached</b> ⚠️\n\n"
            + "You've reached the maximum limit of 5 admins.\n"
            + "Please remove an existing admin before adding a new one.\n\n"
            + "📝 View current admins: /admins_list\n"
            + "🗑️ Remove an admin: /remove_admin"
        )
        return ConversationHandler.END
    await update.message.reply_html(text="👤 <b>Add New Admin</b>\n\nPlease send the chat ID of the new admin:")
    return GET_CHAT_ID


async def get_chat_id(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Adds a new admin if the provided chat ID is valid and not already an admin.
    """
    new_admin_id = update.message.text.strip()
    try:
        if await add_admin_to_config(new_admin_id):
            await update.message.reply_html(
                text="✅ <b>Success!</b>\n\n"
                + f"Admin <code>{new_admin_id}</code> has been added successfully.\n\n"
                + "This user now has full administrative access to the bot."
            )
        else:
            await update.message.reply_html(
                text="ℹ️ <b>Already an Admin</b>\n\n"
                + f"User <code>{new_admin_id}</code> is already an administrator."
            )
    except ValueError:
        await update.message.reply_html(
            text="❌ <b>Invalid Input</b>\n\n"
            + f"<code>{update.message.text.strip()}</code> is not a valid chat ID.\n"
            + "Please try again with /add_admin"
        )
    return ConversationHandler.END


async def admins_list(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Sends a list of current admins.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    admins = await check_admin()
    if admins:
        admins_str = "\n".join([f"👤 <code>{admin}</code>" for admin in admins])
        await update.message.reply_html(
            text="📋 <b>Bot Administrators</b>\n\n"
            + f"{admins_str}\n\n"
            + "Total admins: " + str(len(admins))
        )
    else:
        await update.message.reply_html(
            text="⚠️ <b>No Admins Found</b>\n\n"
            + "There are currently no registered administrators.\n"
            + "Use /add_admin to add an administrator."
        )
    return ConversationHandler.END


async def check_admin_privilege(update: Update):
    """
    Checks if the user has admin privileges.
    """
    admins = await check_admin()
    if not admins:
        # If no admins exist, add the current user as the first admin
        await add_admin_to_config(update.effective_chat.id)
        return None  # Return None to indicate success (user is now an admin)
    
    if update.effective_chat.id not in admins:
        await update.message.reply_html(
            text="Sorry, you do not have permission to execute this command."
        )
        return ConversationHandler.END
    
    return None  # Return None to indicate success (user is an admin)


async def set_special_limit(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    set a special limit for a user.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    await update.message.reply_html(
        text="🔢 <b>Set Special IP Limit</b>\n\n"
        + "Please enter the <b>username</b> of the user you want to set a custom IP limit for.\n\n"
        + "<i>Example:</i> <code>john_doe</code>"
    )
    return GET_SPECIAL_LIMIT


async def get_special_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    get the number of limit for a user.
    """
    context.user_data["selected_user"] = update.message.text.strip()
    await update.message.reply_html(
        text="👤 <b>Setting limit for:</b> "
        + f"<code>{context.user_data['selected_user']}</code>\n\n"
        + "Please enter the <b>maximum number</b> of IPs this user can connect from.\n\n"
        + "<i>Example:</i> <code>3</code>"
    )
    return GET_LIMIT_NUMBER


async def get_limit_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sets the special limit for a user if the provided input is a valid number.
    """
    try:
        context.user_data["limit_number"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_html(
            text="❌ <b>Invalid Input</b>\n\n"
            + f"<code>{update.message.text.strip()}</code> is not a valid number.\n"
            + "Please try again with /set_special_limit"
        )
        return ConversationHandler.END
    out_put = await handel_special_limit(
        context.user_data["selected_user"], context.user_data["limit_number"]
    )
    if out_put[0]:
        update_text = "🔄 <b>Limit Updated</b>\n\n"
    else:
        update_text = "✅ <b>Limit Set Successfully</b>\n\n"
        
    await update.message.reply_html(
        text=f"{update_text}"
        + f"User: <code>{context.user_data['selected_user']}</code>\n"
        + f"IP Limit: <code>{out_put[1]}</code>\n\n"
        + "<i>This user will be disconnected if they exceed this limit.</i>"
    )
    return ConversationHandler.END


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Start function for the bot."""
    check = await check_admin_privilege(update)
    if check:
        return check
    await update.message.reply_html(text=START_MESSAGE)


async def create_config(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Add panel domain, username, and password to add into the config file.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    if os.path.exists("config.json"):
        json_data = await read_json_file()
        domain = json_data.get("PANEL_DOMAIN")
        username = json_data.get("PANEL_USERNAME")
        password = json_data.get("PANEL_PASSWORD")
        if domain and username and password:
            await update.message.reply_html(
                text="⚙️ <b>Panel Configuration</b>\n\n"
                + f"Current settings:\n"
                + f"• Domain: <code>{domain}</code>\n"
                + f"• Username: <code>{username}</code>\n"
                + f"• Password: <code>{'•' * 8}</code>\n\n"
                + "Do you want to update these settings?\n"
                + "Reply with <code>yes</code> to continue or <code>no</code> to cancel."
            )
            return GET_CONFIRMATION
    # If config.json doesn't exist or doesn't have the required data
    await update.message.reply_html(
        text="⚙️ <b>Panel Configuration</b>\n\n"
        + "Please enter your panel domain (without http/https):\n\n"
        + "<i>Example:</i> <code>panel.example.com</code>"
    )
    return GET_DOMAIN


async def get_confirmation(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Get user confirmation for changing the config file.
    """
    response = update.message.text.strip().lower()
    if response == "yes":
        await update.message.reply_html(
            text="🔄 <b>Updating Configuration</b>\n\n"
            + "Please enter your panel domain (without http/https):\n\n"
            + "<i>Example:</i> <code>panel.example.com</code> or <code>95.12.153.87:443</code>"
        )
        return GET_DOMAIN
    if response == "no":
        await update.message.reply_html(
            text="✅ <b>Configuration Unchanged</b>\n\n"
            + "Your current panel configuration has been kept.\n"
            + "Use /start to see all available commands."
        )
        return ConversationHandler.END
    await update.message.reply_html(
        text="❌ <b>Invalid Response</b>\n\n"
        + "Please respond with either <code>yes</code> or <code>no</code>."
    )
    return GET_CONFIRMATION


async def get_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Get panel domain from the user for addition to the config file.
    """
    context.user_data["domain"] = update.message.text.strip()
    await update.message.reply_html(
        text="👤 <b>Panel Username</b>\n\n"
        + "Please enter your panel username:\n\n"
        + "<i>Example:</i> <code>admin</code>"
    )
    return GET_USERNAME


async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Get panel username from the user for addition to the config file.
    """
    context.user_data["username"] = update.message.text.strip()
    await update.message.reply_html(
        text="🔒 <b>Panel Password</b>\n\n"
        + "Please enter your panel password:\n\n"
        + "<i>Your password will be stored securely.</i>"
    )
    return GET_PASSWORD


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Get panel password from the user and update the config file with the provided details.
    """
    try:
        context.user_data["password"] = update.message.text.strip()
        await add_base_information(
            context.user_data["domain"],
            context.user_data["password"],
            context.user_data["username"],
        )
        await update.message.reply_html(
            text="✅ <b>Configuration Complete!</b>\n\n"
            + "Your panel details have been successfully saved.\n\n"
            + "<b>Details:</b>\n"
            + f"• Domain: <code>{context.user_data['domain']}</code>\n"
            + f"• Username: <code>{context.user_data['username']}</code>\n"
            + f"• Password: <code>{'•' * 8}</code>\n\n"
            + "⚠️ <b>Important:</b> Please restart the bot for changes to take effect."
        )
        return ConversationHandler.END
    except ValueError as error:
        await update.message.reply_html(
            text="❌ <b>Connection Error</b>\n\n"
            + f"<code>{error}</code>\n\n"
            + "Please check your credentials and try again with /create_config"
        )
        return ConversationHandler.END


async def remove_admin(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the process of removing an admin from the bot.
    Checks if the user has admin privileges first.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    admins = await check_admin()
    if admins:
        admins_str = "\n".join([f"👤 <code>{admin}</code>" for admin in admins])
        await update.message.reply_html(
            text="🗑️ <b>Remove Administrator</b>\n\n"
            + "Current administrators:\n\n"
            + f"{admins_str}\n\n"
            + "Please enter the chat ID of the admin you want to remove:"
        )
        return GET_CHAT_ID_TO_REMOVE
    await update.message.reply_html(
        text="⚠️ <b>No Admins to Remove</b>\n\n"
        + "There are currently no registered administrators.\n"
        + "Use /add_admin to add an administrator."
    )
    return ConversationHandler.END


async def get_chat_id_to_remove(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Removes an admin based on the provided chat ID.
    """
    try:
        admin_to_remove = int(update.message.text.strip())
        admins = await check_admin()
        if admin_to_remove == update.effective_chat.id:
            await update.message.reply_html(
                text="⚠️ <b>Cannot Remove Yourself</b>\n\n"
                + "You cannot remove yourself as an administrator.\n"
                + "Please ask another admin to remove you if needed."
            )
        elif len(admins) == 1 and admin_to_remove in admins:
            await update.message.reply_html(
                text="⚠️ <b>Cannot Remove Last Admin</b>\n\n"
                + "You cannot remove the last administrator.\n"
                + "Please add another admin first with /add_admin."
            )
        elif await remove_admin_from_config(admin_to_remove):
            await update.message.reply_html(
                text="✅ <b>Admin Removed</b>\n\n"
                + f"Admin <code>{admin_to_remove}</code> has been removed successfully."
            )
        else:
            await update.message.reply_html(
                text="❌ <b>Admin Not Found</b>\n\n"
                + f"<code>{admin_to_remove}</code> is not registered as an administrator.\n"
                + "Please check the ID and try again."
            )
    except ValueError:
        await update.message.reply_html(
            text="❌ <b>Invalid Input</b>\n\n"
            + f"<code>{update.message.text.strip()}</code> is not a valid chat ID.\n"
            + "Please try again with /remove_admin"
        )
    return ConversationHandler.END


async def show_special_limit_function(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
):
    """
    Displays the special limit list to the user.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    special_limit_list = await get_special_limit_list()
    if special_limit_list:
        await update.message.reply_html(
            text="📊 <b>Special IP Limits</b>\n\n"
            + "The following users have custom IP connection limits:"
        )
        for item in special_limit_list:
            formatted_limits = "\n".join([
                f"👤 <code>{username}</code>: <b>{limit} IPs</b>" 
                for username, limit in [line.split(" : ") for line in item.split("\n")]
            ])
            await update.message.reply_html(
                text=formatted_limits
            )
    else:
        await update.message.reply_html(
            text="ℹ️ <b>No Special Limits</b>\n\n"
            + "There are currently no users with special IP limits.\n"
            + "Use /set_special_limit to create custom limits for users."
        )


async def set_country_code(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Starts the process of setting the country code.
    Shows the current country code when invoked.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    
    # Get current country code from config
    current_code = "Not set"
    if os.path.exists("config.json"):
        data = await read_json_file()
        current_code = data.get("IP_LOCATION", "Not set")
    
    await update.message.reply_html(
        text="🌎 <b>Set Country Code</b>\n\n"
        + f"<b>Current country code:</b> <code>{current_code}</code>\n\n"
        + "Please enter your two-letter country code. Only IPs from this country will be counted.\n\n"
        + "<i>Examples:</i>\n<code>US</code> - United States\n<code>GB</code> - United Kingdom\n"
        + "<code>DE</code> - Germany\n<code>IR</code> - Iran\n<code>CN</code> - China\n\n"
        + "Use /cancel to cancel this operation."
    )
    return SET_COUNTRY_CODE


async def toggle_ip_location(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Toggles IP location checking on/off
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    
    # Get current status from config
    data = await read_json_file()
    current_status = data.get("ENABLE_IP_LOCATION_CHECK", True)
    status_text = "enabled" if current_status else "disabled"
    new_status_text = "disable" if current_status else "enable"
    
    await update.message.reply_html(
        text="🌐 <b>IP Location Check</b>\n\n"
        + f"IP location checking is currently <b>{status_text}</b>.\n\n"
        + (
            "Only IPs from your configured country will be counted." 
            if current_status else 
            "All valid IPs are being counted regardless of their country location."
        )
        + f"\n\nDo you want to <b>{new_status_text}</b> IP location checking?\n"
        + "Reply with <code>yes</code> to confirm or <code>no</code> to cancel."
    )
    
    # Store context for confirmation handler
    application.user_data[update.effective_chat.id] = {"waiting_for_ip_check_confirmation": True}
    
    return ConversationHandler.END


async def write_country_code(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Writes the provided country code to the configuration file.
    """
    # Check if the user is trying to cancel
    if update.message.text.strip().startswith('/cancel'):
        return await cancel(update, _context)
        
    country_code = update.message.text.strip().upper()
    if len(country_code) != 2 or not country_code.isalpha():
        await update.message.reply_html(
            text="❌ <b>Invalid Country Code</b>\n\n"
            + "Please enter a valid two-letter country code.\n"
            + "Try again with /country_code"
        )
        return ConversationHandler.END
        
    await write_country_code_json(country_code)
    await update.message.reply_html(
        text="✅ <b>Country Code Set</b>\n\n"
        + f"Your country code has been set to <code>{country_code}</code>.\n"
        + "The system will now only count IP connections from this country."
    )
    return ConversationHandler.END


async def send_backup(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Sends the config.json file as a backup.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    try:
        await update.message.reply_html(
            text="📤 <b>Sending Backup File</b>\n\n"
            + "Preparing your configuration backup..."
        )
        await update.message.reply_document(
            document=open("config.json", "rb"),
            filename="config.json",
            caption="✅ <b>Backup Complete</b>\n\nHere is your configuration backup file."
        )
    except FileNotFoundError:
        await update.message.reply_html(
            text="❌ <b>No Configuration Found</b>\n\n"
            + "No configuration file exists to back up.\n"
            + "Please set up your configuration with /create_config first."
        )


async def set_except_users(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Starts the process of adding a user to the exception list.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    await update.message.reply_html(
        text="👤 <b>Add Exception User</b>\n\n"
        + "Please enter the username of the user you want to add to the exception list.\n"
        + "Excepted users will not be disconnected regardless of how many IPs they use.\n\n"
        + "<i>Example:</i> <code>admin_user</code>"
    )
    return SET_EXCEPT_USERS


async def set_except_users_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Adds the provided username to the exception list.
    """
    except_user = update.message.text.strip()
    result = await add_except_user(except_user)
    if result:
        await update.message.reply_html(
            text="✅ <b>User Excepted</b>\n\n"
            + f"User <code>{except_user}</code> has been added to the exception list.\n"
            + "This user will not be disconnected regardless of IP count."
        )
    else:
        await update.message.reply_html(
            text="ℹ️ <b>Already Excepted</b>\n\n"
            + f"User <code>{except_user}</code> is already in the exception list."
        )
    return ConversationHandler.END


async def remove_except_user(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Starts the process of removing a user from the exception list.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    await update.message.reply_html(
        text="🔄 <b>Remove Exception User</b>\n\n"
        + "Please enter the username of the user you want to remove from the exception list.\n\n"
        + "<i>Example:</i> <code>admin_user</code>"
    )
    return REMOVE_EXCEPT_USER


async def remove_except_user_handler(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
):
    """
    Removes the provided username from the exception list.
    """
    except_user = update.message.text.strip()
    result = await remove_except_user_from_config(except_user)
    if result:
        await update.message.reply_html(
            text="✅ <b>User Removed from Exceptions</b>\n\n"
            + f"User <code>{except_user}</code> has been removed from the exception list.\n"
            + "This user will now be subject to IP limits."
        )
    else:
        await update.message.reply_html(
            text="❌ <b>User Not Found</b>\n\n"
            + f"User <code>{except_user}</code> was not found in the exception list."
        )
    return ConversationHandler.END


async def show_except_users(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Displays the list of users in the exception list.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    except_users = await show_except_users_handler()
    if except_users:
        await update.message.reply_html(
            text="📋 <b>Exception List</b>\n\n"
            + "The following users are excepted from IP limits:"
        )
        for user_chunk in except_users:
            formatted_users = "\n".join([f"👤 <code>{user}</code>" for user in user_chunk.split("\n")])
            await update.message.reply_html(text=formatted_users)
    else:
        await update.message.reply_html(
            text="ℹ️ <b>No Excepted Users</b>\n\n"
            + "There are currently no users in the exception list.\n"
            + "Use /set_except_user to add users to the exception list."
        )


async def get_general_limit_number(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Starts the process of setting the general IP limit number.
    Shows the current limit when invoked.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    
    # Get current limit from config
    current_limit = "Not set"
    if os.path.exists("config.json"):
        data = await read_json_file()
        current_limit = data.get("GENERAL_LIMIT", "Not set")
    
    await update.message.reply_html(
        text="🔢 <b>Set General IP Limit</b>\n\n"
        + f"<b>Current limit:</b> <code>{current_limit}</code>\n\n"
        + "Please enter the default maximum number of IPs a user can connect from.\n"
        + "This limit applies to all users who don't have a special limit set.\n\n"
        + "<i>Example:</i> <code>2</code>\n\n"
        + "Use /cancel to cancel this operation."
    )
    return GET_GENERAL_LIMIT_NUMBER


async def get_general_limit_number_handler(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
):
    """
    Sets the general IP limit number based on the provided input.
    """
    # Check if the user is trying to cancel
    if update.message.text.strip().startswith('/cancel'):
        return await cancel(update, _context)
        
    try:
        limit_number = int(update.message.text.strip())
        if limit_number < 1:
            raise ValueError("Limit must be at least 1")
            
        result = await save_general_limit(limit_number)
        await update.message.reply_html(
            text="✅ <b>General Limit Set</b>\n\n"
            + f"The default IP limit has been set to <code>{result}</code>.\n"
            + "Users will be disconnected if they exceed this number of connections."
        )
    except ValueError:
        await update.message.reply_html(
            text="❌ <b>Invalid Input</b>\n\n"
            + f"<code>{update.message.text.strip()}</code> is not a valid number.\n"
            + "Please try again with /set_general_limit_number"
        )
    return ConversationHandler.END


async def get_check_interval(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Starts the process of setting the check interval time.
    Shows the current interval when invoked.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    
    # Get current interval from config
    current_interval = "Not set"
    if os.path.exists("config.json"):
        data = await read_json_file()
        current_interval = data.get("CHECK_INTERVAL", "Not set")
    
    await update.message.reply_html(
        text="⏱️ <b>Set Check Interval</b>\n\n"
        + f"<b>Current interval:</b> <code>{current_interval}</code> seconds\n\n"
        + "Please enter how often (in seconds) the system should check for users exceeding their IP limits.\n\n"
        + "<i>Recommended:</i> <code>60</code> (1 minute)\n"
        + "<i>Example:</i> <code>30</code> (30 seconds)\n\n"
        + "Use /cancel to cancel this operation."
    )
    return GET_CHECK_INTERVAL


async def get_check_interval_handler(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
):
    """
    Sets the check interval based on the provided input.
    """
    # Check if the user is trying to cancel
    if update.message.text.strip().startswith('/cancel'):
        return await cancel(update, _context)
        
    try:
        interval = int(update.message.text.strip())
        if interval < 10:
            await update.message.reply_html(
                text="⚠️ <b>Interval Too Short</b>\n\n"
                + "The check interval must be at least 10 seconds to avoid overloading the system.\n"
                + "Please try again with a larger value.\n\n"
                + "Use /cancel to cancel this operation."
            )
            return GET_CHECK_INTERVAL
            
        result = await save_check_interval(interval)
        await update.message.reply_html(
            text="✅ <b>Check Interval Set</b>\n\n"
            + f"The system will now check user IP limits every <code>{result}</code> seconds."
        )
    except ValueError:
        await update.message.reply_html(
            text="❌ <b>Invalid Input</b>\n\n"
            + f"<code>{update.message.text.strip()}</code> is not a valid number.\n"
            + "Please try again with /set_check_interval"
        )
    return ConversationHandler.END


async def get_time_to_active_users(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Starts the process of setting the time to reactivate users.
    Shows the current time when invoked.
    """
    check = await check_admin_privilege(update)
    if check:
        return check
    
    # Get current time from config
    current_time = "Not set"
    if os.path.exists("config.json"):
        data = await read_json_file()
        current_time = data.get("TIME_TO_ACTIVE_USERS", "Not set")
    
    await update.message.reply_html(
        text="⏳ <b>Set Reactivation Time</b>\n\n"
        + f"<b>Current time:</b> <code>{current_time}</code> seconds\n\n"
        + "Please enter the time (in seconds) after which a disabled user will be automatically reactivated.\n\n"
        + "<i>Recommended:</i> <code>300</code> (5 minutes)\n"
        + "<i>Example:</i> <code>600</code> (10 minutes)\n\n"
        + "Use /cancel to cancel this operation."
    )
    return GET_TIME_TO_ACTIVE_USERS


async def get_time_to_active_users_handler(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
):
    """
    Sets the time to reactivate users based on the provided input.
    """
    # Check if the user is trying to cancel
    if update.message.text.strip().startswith('/cancel'):
        return await cancel(update, _context)
        
    try:
        time_value = int(update.message.text.strip())
        if time_value < 60:
            await update.message.reply_html(
                text="⚠️ <b>Time Too Short</b>\n\n"
                + "The reactivation time must be at least 60 seconds.\n"
                + "Please try again with a larger value.\n\n"
                + "Use /cancel to cancel this operation."
            )
            return GET_TIME_TO_ACTIVE_USERS
            
        result = await save_time_to_active_users(time_value)
        await update.message.reply_html(
            text="✅ <b>Reactivation Time Set</b>\n\n"
            + f"Disabled users will now be automatically reactivated after <code>{result}</code> seconds.\n"
            + f"(<code>{result // 60}</code> minutes, <code>{result % 60}</code> seconds)"
        )
    except ValueError:
        await update.message.reply_html(
            text="❌ <b>Invalid Input</b>\n\n"
            + f"<code>{update.message.text.strip()}</code> is not a valid number.\n"
            + "Please try again with /set_time_to_active_users"
        )
    return ConversationHandler.END


async def get_api_token(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Get the current API token from the config file or generate a new one if it doesn't exist.
    """
    # Directly check if user is an admin without using check_admin_privilege
    admins = await check_admin()
    
    # If there are no admins, add the current user
    if not admins:
        await add_admin_to_config(update.effective_chat.id)
        admins = [update.effective_chat.id]  # Set admins with the current user

    # Check if the user is an admin
    if update.effective_chat.id not in admins:
        await update.message.reply_html(
            text="Sorry, you do not have permission to execute this command."
        )
        return ConversationHandler.END
    
    # Get the token directly from config file
    try:
        # Try to read directly from config file
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            token = config.get("API_TOKEN")
        
        if token:
            await update.message.reply_html(
                text="🔑 <b>API Token</b>\n\n"
                + "<b>Current token:</b> <code>" + token + "</code>\n\n"
                + "⚠️ <b>Important:</b> This token provides full access to your API. "
                + "Use this token in the Authorization header with the Bearer scheme for API requests.\n\n"
                + "To generate a new token, send /get_api_token again and select 'Generate New Token'."
            )
        else:
            # Generate a new token if one doesn't exist
            token = await generate_and_save_token()
            if token:
                await update.message.reply_html(
                    text="✅ <b>API Token Generated</b>\n\n"
                    + "A new API token has been generated and saved to the config file.\n\n"
                    + "<b>Token:</b> <code>" + token + "</code>\n\n"
                    + "⚠️ <b>Important:</b> Store this token securely. It provides "
                    + "full access to your API. Use this token in the Authorization header "
                    + "with the Bearer scheme for API requests."
                )
            else:
                await update.message.reply_html(
                    text="❌ <b>Error</b>\n\n"
                    + "Failed to generate API token. Please check the logs for more information."
                )
    except Exception as e:
        logger.error(f"Error in get_api_token: {e}")
        await update.message.reply_html(
            text="❌ <b>Error Reading Token</b>\n\n"
            + "Could not read API token from config file. Please check if the file exists and is valid."
        )
    
    return ConversationHandler.END


async def cancel(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel the current conversation.
    """
    await update.message.reply_html(
        text="🛑 <b>Operation Cancelled</b>\n\n"
        + "Current operation has been cancelled.\n"
        + "Use /start to see all available commands."
    )
    return ConversationHandler.END


async def handle_ip_check_confirmation(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Handle confirmation for toggling IP location checking
    """
    # Check if we're waiting for a confirmation
    if (
        not hasattr(application, "user_data") 
        or update.effective_chat.id not in application.user_data
        or not application.user_data[update.effective_chat.id].get("waiting_for_ip_check_confirmation")
    ):
        return
    
    # Reset waiting flag
    application.user_data[update.effective_chat.id]["waiting_for_ip_check_confirmation"] = False
    
    response = update.message.text.strip().lower()
    if response != "yes":
        await update.message.reply_html(
            text="🛑 <b>Operation Cancelled</b>\n\n"
            + "IP location checking setting remains unchanged."
        )
        return
    
    # User confirmed, toggle the setting
    success, new_value = await toggle_ip_location_check()
    
    if success:
        status = "enabled" if new_value else "disabled"
        await update.message.reply_html(
            text=f"✅ <b>IP Location Check {status.capitalize()}</b>\n\n"
            + f"IP location checking is now <b>{status}</b>.\n\n"
            + (
                "Only IPs from your configured country will be counted."
                if new_value else
                "All valid IPs will be counted regardless of their country location."
            )
        )
    else:
        await update.message.reply_html(
            text="❌ <b>Error</b>\n\n"
            + "Failed to toggle IP location checking setting.\n\n"
            + "Please check the logs for more information."
        )


# Register handlers
def register_handlers():
    """
    Register all handlers for the application.
    """
    # Start, Help, and Configuration Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admins_list", admins_list))
    application.add_handler(CommandHandler("show_special_limit", show_special_limit_function))
    application.add_handler(CommandHandler("show_except_users", show_except_users))
    application.add_handler(CommandHandler("backup", send_backup))
    application.add_handler(CommandHandler("get_api_token", get_api_token))
    application.add_handler(CommandHandler("toggle_ip_location", toggle_ip_location))
    
    # Message handler for IP location check confirmation
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r'^(yes|no)$'),
            handle_ip_check_confirmation
        )
    )
    
    # Add Admin Conversation
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("add_admin", add_admin),
            ],
            states={
                GET_CHAT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_chat_id)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("remove_admin", remove_admin),
            ],
            states={
                GET_CHAT_ID_TO_REMOVE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_chat_id_to_remove)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("country_code", set_country_code),
            ],
            states={
                SET_COUNTRY_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, write_country_code)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("set_except_user", set_except_users),
            ],
            states={
                SET_EXCEPT_USERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_except_users_handler)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    # Special Limit Conversation
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("set_special_limit", set_special_limit),
            ],
            states={
                GET_SPECIAL_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_special_limit)],
                GET_LIMIT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_limit_number)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    # Time to Active Users Conversation
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("set_time_to_active_users", get_time_to_active_users),
            ],
            states={
                GET_TIME_TO_ACTIVE_USERS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_time_to_active_users_handler)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    # Check Interval Conversation
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("set_check_interval", get_check_interval),
            ],
            states={
                GET_CHECK_INTERVAL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_check_interval_handler)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    # General Limit Conversation
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("set_general_limit_number", get_general_limit_number),
            ],
            states={
                GET_GENERAL_LIMIT_NUMBER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_general_limit_number_handler)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    # Remove Exception Conversation
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler("remove_except_user", remove_except_user),
            ],
            states={
                REMOVE_EXCEPT_USER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, remove_except_user_handler)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    # Unknown command handler
    unknown_handler = MessageHandler(filters.TEXT, start)
    application.add_handler(unknown_handler)
    unknown_handler_command = MessageHandler(filters.COMMAND, start)
    application.add_handler(unknown_handler_command)

# Register handlers when the module is loaded
register_handlers()
