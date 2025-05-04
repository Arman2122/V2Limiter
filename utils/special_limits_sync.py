"""
Special limits synchronization between Redis and config file.
"""

import asyncio
from typing import Dict

from utils.logs import logger
from utils.read_config import read_config
from utils.write_config import update_special_limits
from utils.redis_utils import redis_client


async def sync_special_limits_to_redis():
    """
    Sync special limits from config file to Redis.
    """
    try:
        # Read from config
        config = await read_config()
        special_limits = config.get("SPECIAL_LIMIT", {})
        
        # Write to Redis
        if not await redis_client.set_special_limits(special_limits):
            logger.error("Failed to sync special limits to Redis")
            return False
        
        logger.info(f"Successfully synced special limits to Redis: {special_limits}")
        return True
    except Exception as e:
        logger.error(f"Error syncing special limits to Redis: {e}")
        return False


async def sync_special_limits_to_config():
    """
    Sync special limits from Redis to config file.
    """
    try:
        # Read from Redis
        special_limits = await redis_client.get_special_limits()
        
        # Write to config
        if not await update_special_limits(special_limits):
            logger.error("Failed to sync special limits to config file")
            return False
        
        logger.info(f"Successfully synced special limits to config file: {special_limits}")
        return True
    except Exception as e:
        logger.error(f"Error syncing special limits to config file: {e}")
        return False


async def add_special_limit(username: str, limit: int) -> bool:
    """
    Add or update a special limit for a user in both Redis and config.
    
    Args:
        username: The username
        limit: The limit value
        
    Returns:
        bool: True if updated successfully, False otherwise
    """
    try:
        # Initialize Redis if needed
        if not hasattr(redis_client, "_initialized") or not redis_client._initialized:
            await redis_client.initialize()
        
        # Update in Redis
        if not await redis_client.add_special_limit(username, limit):
            logger.error(f"Failed to add special limit for {username} in Redis")
            return False
        
        # Update in config
        if not await sync_special_limits_to_config():
            logger.error(f"Failed to sync special limits to config after adding {username}")
            return False
        
        logger.info(f"Successfully added special limit for {username}: {limit}")
        return True
    except Exception as e:
        logger.error(f"Error adding special limit: {e}")
        return False


async def remove_special_limit(username: str) -> bool:
    """
    Remove a special limit for a user from both Redis and config.
    
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
        if not await redis_client.remove_special_limit(username):
            logger.error(f"Failed to remove special limit for {username} from Redis")
            return False
        
        # Update in config
        if not await sync_special_limits_to_config():
            logger.error(f"Failed to sync special limits to config after removing {username}")
            return False
        
        logger.info(f"Successfully removed special limit for {username}")
        return True
    except Exception as e:
        logger.error(f"Error removing special limit: {e}")
        return False


async def get_special_limits() -> Dict[str, int]:
    """
    Get special limits from Redis.
    
    Returns:
        Dict[str, int]: Dict of username to limit
    """
    try:
        # Initialize Redis if needed
        if not hasattr(redis_client, "_initialized") or not redis_client._initialized:
            await redis_client.initialize()
        
        # Get from Redis
        return await redis_client.get_special_limits()
    except Exception as e:
        logger.error(f"Error getting special limits: {e}")
        return {} 