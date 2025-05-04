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