"""
Except users synchronization between Redis and config file.
"""

import asyncio
from typing import List

from utils.logs import logger
from utils.read_config import read_config
from utils.write_config import write_config
from utils.redis_utils import redis_client


async def sync_except_users_to_redis():
    """
    Sync except users from config file to Redis.
    """
    try:
        # Read from config
        config = await read_config()
        except_users = config.get("EXCEPT_USERS", [])
        
        # Write to Redis
        if not await redis_client.set_except_users(except_users):
            logger.error("Failed to sync except users to Redis")
            return False
        
        logger.info(f"Successfully synced except users to Redis: {except_users}")
        return True
    except Exception as e:
        logger.error(f"Error syncing except users to Redis: {e}")
        return False


async def sync_except_users_to_config():
    """
    Sync except users from Redis to config file.
    """
    try:
        # Read from Redis
        except_users = await redis_client.get_except_users()
        
        # Read current config
        config = await read_config()
        
        # Update except users
        config["EXCEPT_USERS"] = except_users
        
        # Write back to config
        if not await write_config(config):
            logger.error("Failed to sync except users to config file")
            return False
        
        logger.info(f"Successfully synced except users to config file: {except_users}")
        return True
    except Exception as e:
        logger.error(f"Error syncing except users to config file: {e}")
        return False


async def add_except_user(username: str) -> bool:
    """
    Add a user to the exception list in both Redis and config.
    
    Args:
        username: The username to add
        
    Returns:
        bool: True if added successfully, False otherwise
    """
    try:
        # Initialize Redis if needed
        if not hasattr(redis_client, "_initialized") or not redis_client._initialized:
            await redis_client.initialize()
        
        # Update in Redis
        if not await redis_client.add_except_user(username):
            logger.error(f"Failed to add except user {username} in Redis")
            return False
        
        # Update in config
        if not await sync_except_users_to_config():
            logger.error(f"Failed to sync except users to config after adding {username}")
            return False
        
        logger.info(f"Successfully added except user: {username}")
        return True
    except Exception as e:
        logger.error(f"Error adding except user: {e}")
        return False


async def remove_except_user(username: str) -> bool:
    """
    Remove a user from the exception list in both Redis and config.
    
    Args:
        username: The username to remove
        
    Returns:
        bool: True if removed successfully, False otherwise
    """
    try:
        # Initialize Redis if needed
        if not hasattr(redis_client, "_initialized") or not redis_client._initialized:
            await redis_client.initialize()
        
        # Remove from Redis
        if not await redis_client.remove_except_user(username):
            logger.error(f"Failed to remove except user {username} from Redis")
            return False
        
        # Update in config
        if not await sync_except_users_to_config():
            logger.error(f"Failed to sync except users to config after removing {username}")
            return False
        
        logger.info(f"Successfully removed except user: {username}")
        return True
    except Exception as e:
        logger.error(f"Error removing except user: {e}")
        return False


async def get_except_users() -> List[str]:
    """
    Get except users from Redis.
    
    Returns:
        List[str]: List of exempt usernames
    """
    try:
        # Initialize Redis if needed
        if not hasattr(redis_client, "_initialized") or not redis_client._initialized:
            await redis_client.initialize()
        
        # Get from Redis
        return await redis_client.get_except_users()
    except Exception as e:
        logger.error(f"Error getting except users: {e}")
        return [] 