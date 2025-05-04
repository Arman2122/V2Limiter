"""
Main API module for Marz Limiter.
"""

import json
import os
import socket
import time
from typing import Dict, List, Optional, Any, Union

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from api.auth import verify_token
from utils.logs import logger
from utils.redis_utils import redis_client
from utils.read_config import read_config
from utils.special_limits_sync import (
    get_special_limits, 
    add_special_limit as add_special_limit_util,
    remove_special_limit as remove_special_limit_util,
    sync_special_limits_to_redis
)
from utils.except_users_sync import (
    get_except_users,
    add_except_user as add_except_user_util,
    remove_except_user as remove_except_user_util,
    sync_except_users_to_redis
)

# Create FastAPI instance
app = FastAPI(
    title="Marz Limiter API",
    description="API for Marz Limiter",
    version="1.0.0",
    docs_url=None,  # Disable default docs URL
    redoc_url=None,  # Disable redoc URL
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Response models
class ServiceIPResponse(BaseModel):
    """Response model for service IPs."""
    services: Dict[str, List[str]]
    last_update: int
    check_interval: int

class APIStatusResponse(BaseModel):
    """Response model for API status."""
    status: str
    version: str

# Add new models for special limits
class SpecialLimitsResponse(BaseModel):
    """Response model for special limits."""
    limits: Dict[str, int]

class SpecialLimitRequest(BaseModel):
    """Request model for adding a special limit."""
    username: str
    limit: int

class SpecialLimitDeleteRequest(BaseModel):
    """Request model for removing a special limit."""
    username: str

# Add new models for except users
class ExceptUsersResponse(BaseModel):
    """Response model for except users."""
    users: List[str]

class ExceptUserRequest(BaseModel):
    """Request model for adding an except user."""
    username: str

# Track last refresh time
last_refresh_time = 0

# API routes
@app.get("/api/status", response_model=APIStatusResponse)
async def get_status():
    """
    Get API status.
    """
    return {
        "status": "active",
        "version": "1.0.0"
    }

@app.get("/api/connected-ips", response_model=ServiceIPResponse, dependencies=[Depends(verify_token)])
async def get_connected_ips():
    """
    Get all connected IPs for all services.
    
    Returns:
        ServiceIPResponse: Dictionary with services and their IPs, along with last_update and check_interval
    """
    global last_refresh_time
    
    try:
        # Initialize Redis client if not already initialized
        if not hasattr(redis_client, "_initialized") or not redis_client._initialized:
            await redis_client.initialize()
        
        # Get the CHECK_INTERVAL from config
        config = await read_config()
        check_interval = int(config.get("CHECK_INTERVAL", 240))
        
        # Check if it's time to clear the IPs
        current_time = time.time()
        if current_time - last_refresh_time >= check_interval:
            # Clear all IPs
            logger.info(f"Clearing all IP data (CHECK_INTERVAL of {check_interval}s passed)")
            await redis_client.clear_all_data()
            last_refresh_time = current_time
        
        # Get all service IPs
        result = await redis_client.get_all_service_ips()
        
        # Add check_interval to the response
        result["check_interval"] = check_interval
        
        return result
    except Exception as e:
        logger.error(f"Error getting connected IPs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving connected IPs: {str(e)}"
        )

# New endpoints for special limits
@app.get("/api/special-limits", response_model=SpecialLimitsResponse, dependencies=[Depends(verify_token)])
async def get_all_special_limits():
    """
    Get all special limits.
    
    Returns:
        SpecialLimitsResponse: Dictionary with usernames and their limits
    """
    try:
        # First sync from config to Redis to ensure we have the latest data
        await sync_special_limits_to_redis()
        
        # Get limits from Redis
        limits = await get_special_limits()
        
        return {"limits": limits}
    except Exception as e:
        logger.error(f"Error getting special limits: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving special limits: {str(e)}"
        )

@app.post("/api/special-limits", dependencies=[Depends(verify_token)])
async def add_special_limit(request: SpecialLimitRequest):
    """
    Add or update a special limit for a user.
    
    Args:
        request: The request containing username and limit
        
    Returns:
        dict: Status message
    """
    try:
        # Add the special limit
        success = await add_special_limit_util(request.username, request.limit)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to add special limit"
            )
        
        return {
            "status": "success",
            "message": f"Special limit for {request.username} set to {request.limit}"
        }
    except Exception as e:
        logger.error(f"Error adding special limit: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error adding special limit: {str(e)}"
        )

@app.delete("/api/special-limits", dependencies=[Depends(verify_token)])
async def remove_special_limit(request: SpecialLimitDeleteRequest):
    """
    Remove a special limit for a user.
    
    Args:
        request: The request containing username to remove
        
    Returns:
        dict: Status message
    """
    try:
        # Remove the special limit
        success = await remove_special_limit_util(request.username)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Special limit for {request.username} not found or could not be removed"
            )
        
        return {
            "status": "success",
            "message": f"Special limit for {request.username} removed"
        }
    except Exception as e:
        logger.error(f"Error removing special limit: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error removing special limit: {str(e)}"
        )

# New endpoints for except users
@app.get("/api/except-users", response_model=ExceptUsersResponse, dependencies=[Depends(verify_token)])
async def get_all_except_users():
    """
    Get all except users.
    
    Returns:
        ExceptUsersResponse: List of usernames that are exempted
    """
    try:
        # First sync from config to Redis to ensure we have the latest data
        await sync_except_users_to_redis()
        
        # Get users from Redis
        users = await get_except_users()
        
        return {"users": users}
    except Exception as e:
        logger.error(f"Error getting except users: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving except users: {str(e)}"
        )

@app.post("/api/except-users", dependencies=[Depends(verify_token)])
async def add_except_user(request: ExceptUserRequest):
    """
    Add a user to the exception list.
    
    Args:
        request: The request containing username to add
        
    Returns:
        dict: Status message
    """
    try:
        # Add the except user
        success = await add_except_user_util(request.username)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to add except user"
            )
        
        return {
            "status": "success",
            "message": f"User {request.username} added to exceptions"
        }
    except Exception as e:
        logger.error(f"Error adding except user: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error adding except user: {str(e)}"
        )

@app.delete("/api/except-users", dependencies=[Depends(verify_token)])
async def remove_except_user(request: ExceptUserRequest):
    """
    Remove a user from the exception list.
    
    Args:
        request: The request containing username to remove
        
    Returns:
        dict: Status message
    """
    try:
        # Remove the except user
        success = await remove_except_user_util(request.username)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"User {request.username} not found in exceptions or could not be removed"
            )
        
        return {
            "status": "success",
            "message": f"User {request.username} removed from exceptions"
        }
    except Exception as e:
        logger.error(f"Error removing except user: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error removing except user: {str(e)}"
        )

# Custom Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    Custom Swagger UI endpoint.
    """
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=None,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    """
    OpenAPI specification endpoint.
    """
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

# Serve static files for Swagger UI
@app.get("/static/{file_path:path}", include_in_schema=False)
async def get_static(file_path: str):
    """
    Get static files for Swagger UI.
    """
    try:
        # This assumes you have the Swagger UI files in a 'static' directory
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        file_path = os.path.join(static_dir, file_path)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Determine content type based on file extension
        if file_path.endswith(".js"):
            content_type = "application/javascript"
        elif file_path.endswith(".css"):
            content_type = "text/css"
        else:
            content_type = "application/octet-stream"
        
        # Use Response instead of JSONResponse for binary data
        return Response(
            content=content,
            media_type=content_type,
        )
    except Exception as e:
        logger.error(f"Error serving static file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_api_host_and_port() -> tuple:
    """
    Get the API host and port from config.json.
    
    Returns:
        tuple: (host, port, swagger_port)
    """
    try:
        config = await read_config()
        
        # Get API settings from config
        api_port = config.get("API_PORT", 8080)
        swagger_port = config.get("SWAGGER_PORT", api_port)
        domain = config.get("API_DOMAIN", "")
        
        # If no domain is specified, use the server's IP
        if not domain:
            hostname = socket.gethostname()
            domain = socket.gethostbyname(hostname)
        
        return domain, api_port, swagger_port
    except Exception as e:
        logger.error(f"Error getting API host and port: {e}")
        # Default values
        return "localhost", 8080, 8080 