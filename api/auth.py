"""
Authentication module for the API.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import json
import os

from utils.logs import logger

# Define the security scheme
security = HTTPBearer()

async def get_token_from_config() -> str:
    """
    Get the API token from the config file.
    
    Returns:
        str: The API token
    """
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("API_TOKEN", "")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error reading API token from config: {e}")
        return ""

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """
    Verify the token from the Authorization header.
    
    Args:
        credentials: The credentials from the Authorization header
        
    Returns:
        bool: True if the token is valid
        
    Raises:
        HTTPException: If the token is invalid or missing
    """
    token = credentials.credentials if credentials else ""
    
    if not token:
        logger.warning("Missing API token in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get the token from the config
    expected_token = await get_token_from_config()
    
    if not expected_token:
        logger.error("API token not configured in config.json")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API token not configured",
        )
    
    if token != expected_token:
        logger.warning("Invalid API token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True 