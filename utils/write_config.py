"""
Write config file utility.
"""

import json
import os
import asyncio
from typing import Dict, Any

from utils.logs import logger


async def write_config(config_data: Dict[str, Any]) -> bool:
    """
    Write data to the config.json file.
    
    Args:
        config_data: The full config data to write
        
    Returns:
        bool: True if successful, False otherwise
    """
    config_file = "config.json"
    backup_file = "config.json.bak"
    
    try:
        # Create a backup first
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                original_data = f.read()
            
            with open(backup_file, "w", encoding="utf-8") as f:
                f.write(original_data)
        
        # Write the new config
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        
        logger.info("Successfully updated config.json")
        return True
    except Exception as e:
        logger.error(f"Error writing to config file: {e}")
        
        # If we failed, restore from backup if possible
        if os.path.exists(backup_file):
            try:
                with open(backup_file, "r", encoding="utf-8") as f:
                    backup_data = f.read()
                
                with open(config_file, "w", encoding="utf-8") as f:
                    f.write(backup_data)
                
                logger.info("Restored config.json from backup")
            except Exception as restore_error:
                logger.error(f"Failed to restore config from backup: {restore_error}")
        
        return False

# Function to update just the special limits
async def update_special_limits(special_limits: Dict[str, int]) -> bool:
    """
    Update only the special limits in the config file.
    
    Args:
        special_limits: Dict of username to limit
        
    Returns:
        bool: True if successful, False otherwise
    """
    from utils.read_config import read_config
    
    try:
        # Read the current config
        config = await read_config()
        
        # Update the special limits
        config["SPECIAL_LIMIT"] = special_limits
        
        # Write the updated config
        return await write_config(config)
    except Exception as e:
        logger.error(f"Error updating special limits: {e}")
        return False 