"""
Utilities for API token generation and management.
"""

import json
import os
import secrets
import string
from typing import Optional

from utils.logs import logger


def generate_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: The length of the token
        
    Returns:
        str: The generated token
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


async def save_token_to_config(token: str) -> bool:
    """
    Save the API token to the config file.
    
    Args:
        token: The token to save
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Read the current config
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Update the token
        config["API_TOKEN"] = token
        
        # Write back to the file
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        
        logger.info("API token saved to config.json")
        return True
    except Exception as e:
        logger.error(f"Error saving API token to config: {e}")
        return False


async def get_token_from_config() -> Optional[str]:
    """
    Get the API token from the config file.
    
    Returns:
        Optional[str]: The API token, or None if not found
    """
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("API_TOKEN")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error reading API token from config: {e}")
        return None


async def generate_and_save_token() -> Optional[str]:
    """
    Generate a new API token and save it to the config file.
    
    Returns:
        Optional[str]: The generated token, or None if an error occurred
    """
    token = generate_token()
    success = await save_token_to_config(token)
    return token if success else None 