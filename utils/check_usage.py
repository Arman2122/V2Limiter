"""
This module checks if a user (name and IP address)
appears more than two times in the ACTIVE_USERS list.
"""

import asyncio
import time
from collections import Counter

from telegram_bot.send_message import send_logs
from utils.logs import logger
from utils.panel_api import disable_user
from utils.read_config import read_config
from utils.types import PanelType, UserType
from utils.redis_utils import redis_client

ACTIVE_USERS: dict[str, UserType] | dict = {}


async def check_ip_used() -> dict:
    """
    This function checks if a user (name and IP address)
    appears more than two times in the ACTIVE_USERS list.
    """
    logger.info(f"Starting IP usage check for {len(ACTIVE_USERS)} active users")
    start_time = time.time()
    
    all_users_log = {}
    for email in list(ACTIVE_USERS.keys()):
        data = ACTIVE_USERS[email]
        ip_counts = Counter(data.ip)
        data.ip = list({ip for ip in data.ip if ip_counts[ip] > 2})
        all_users_log[email] = data.ip
        if data.ip:
            logger.debug(f"User {email} has {len(data.ip)} IPs with count > 2: {data.ip}")
    
    # Sort and prepare report
    total_ips = sum(len(ips) for ips in all_users_log.values())
    all_users_log = dict(
        sorted(
            all_users_log.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )
    )
    
    # Log statistics
    users_with_ips = sum(1 for ips in all_users_log.values() if ips)
    logger.info(f"IP usage check completed in {time.time() - start_time:.2f}s")
    logger.info(f"Found {total_ips} active IPs across {users_with_ips} users")
    
    # Prepare messages for admins
    messages = [
        f"<code>{email}</code> with <code>{len(ips)}</code> active ip  \n- "
        + "\n- ".join(ips)
        for email, ips in all_users_log.items()
        if ips
    ]
    
    messages.append(f"---------\nCount Of All Active IPs: <b>{total_ips}</b>")
    
    # Split into chunks to avoid telegram message size limits
    shorter_messages = [
        "\n".join(messages[i : i + 100]) for i in range(0, len(messages), 100)
    ]
    
    # Send messages to admins
    for i, message in enumerate(shorter_messages):
        logger.debug(f"Sending message chunk {i+1}/{len(shorter_messages)} to admins")
        await send_logs(message)
    
    return all_users_log


async def check_users_usage(panel_data: PanelType):
    """
    Checks the usage of active users and disables users exceeding their limits
    """
    logger.info("Starting user usage check...")
    start_time = time.time()
    
    try:
        # Load configuration
        config_data = await read_config()
        logger.debug("Configuration loaded for usage check")
        
        # Get user IP data
        all_users_log = await check_ip_used()
        
        # Get user exceptions and limits
        except_users = config_data.get("EXCEPT_USERS", [])
        if except_users:
            logger.debug(f"Found {len(except_users)} users in exception list")
            
        special_limit = config_data.get("SPECIAL_LIMIT", {})
        if special_limit:
            logger.debug(f"Found {len(special_limit)} users with special limits")
            
        limit_number = config_data["GENERAL_LIMIT"]
        logger.debug(f"General limit is set to {limit_number}")
        
        # Check each user against their limits
        disabled_count = 0
        for user_name, user_ip in all_users_log.items():
            if user_name not in except_users:
                user_limit_number = int(special_limit.get(user_name, limit_number))
                unique_ips = set(user_ip)
                
                if len(unique_ips) > user_limit_number:
                    message = (
                        f"User {user_name} has {len(unique_ips)}"
                        + f" active IPs (limit: {user_limit_number}). IPs: {unique_ips}"
                    )
                    logger.warning(message)
                    await send_logs(str("<b>Warning: </b>" + message))
                    
                    try:
                        logger.info(f"Disabling user {user_name} for exceeding IP limit")
                        await disable_user(panel_data, UserType(name=user_name, ip=[]))
                        disabled_count += 1
                        
                        # Remove from Redis when disabled
                        try:
                            # Make sure Redis client is initialized
                            if not hasattr(redis_client, "_initialized") or not redis_client._initialized:
                                await redis_client.initialize()
                            
                            # Remove all IPs for this service from Redis
                            service_ips = await redis_client.get_service_ips(user_name)
                            for ip in service_ips:
                                await redis_client.remove_ip_from_service(user_name, ip)
                            logger.debug(f"Removed {len(service_ips)} IPs for {user_name} from Redis")
                        except Exception as e:
                            logger.error(f"Error removing IPs from Redis: {e}")
                            
                    except ValueError as error:
                        logger.error(f"Failed to disable user {user_name}: {error}")
        
        # Cleanup and log results
        ACTIVE_USERS.clear()
        all_users_log.clear()
        
        execution_time = time.time() - start_time
        logger.info(f"User usage check completed in {execution_time:.2f}s. Disabled {disabled_count} users.")
        
    except Exception as e:
        logger.error(f"Error in check_users_usage: {e}", exc_info=True)
        await send_logs(f"❌ <b>Error in user usage check</b>\n\n<code>{str(e)}</code>")


async def run_check_users_usage(panel_data: PanelType) -> None:
    """
    Periodically runs check_users_usage according to the configured interval
    """
    logger.info("Starting periodic user usage monitoring")
    cycle_count = 0
    
    while True:
        cycle_count += 1
        logger.info(f"Starting user usage check cycle #{cycle_count}")
        
        try:
            await check_users_usage(panel_data)
            
            # Get updated check interval
            data = await read_config()
            interval = int(data["CHECK_INTERVAL"])
            logger.info(f"User usage check cycle #{cycle_count} completed. Next check in {interval} seconds.")
            
            await asyncio.sleep(interval)
            
        except asyncio.CancelledError:
            logger.warning("User usage monitoring task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in user usage monitoring cycle: {e}", exc_info=True)
            await send_logs(f"❌ <b>Error in usage monitoring cycle</b>\n\n<code>{str(e)}</code>")
            # Still sleep to avoid rapid failure loops
            await asyncio.sleep(30)
