"""
API server runner for Marz Limiter.
"""

import asyncio
import os
import sys
import uvicorn
from typing import Optional

from utils.logs import logger
from api.main import app, get_api_host_and_port


async def run_api_server():
    """
    Run the API server.
    """
    try:
        # Get API host and port
        host, port, swagger_port = await get_api_host_and_port()
        
        logger.info(f"Starting API server on {host}:{port}")
        
        # Configure Swagger UI static files
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        os.makedirs(static_dir, exist_ok=True)
        
        # Start the server
        config = uvicorn.Config(
            app,
            host="0.0.0.0",  # Listen on all interfaces
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        # Run the server in a separate task
        await server.serve()
        
    except Exception as e:
        logger.error(f"Error starting API server: {e}")
        raise


async def download_swagger_ui_files():
    """
    Download Swagger UI files if they don't exist.
    """
    try:
        # Create the static directory
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        os.makedirs(static_dir, exist_ok=True)
        
        # Only download if files don't exist
        if (not os.path.exists(os.path.join(static_dir, "swagger-ui-bundle.js")) or 
            not os.path.exists(os.path.join(static_dir, "swagger-ui.css"))):
            
            logger.info("Downloading Swagger UI files...")
            
            import urllib.request
            
            # Latest Swagger UI version at the time of writing
            swagger_version = "5.16.0"
            
            # URLs for Swagger UI files
            urls = {
                "swagger-ui-bundle.js": f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{swagger_version}/swagger-ui-bundle.js",
                "swagger-ui.css": f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{swagger_version}/swagger-ui.css"
            }
            
            # Download the files
            for filename, url in urls.items():
                target_path = os.path.join(static_dir, filename)
                logger.debug(f"Downloading {url} to {target_path}")
                urllib.request.urlretrieve(url, target_path)
            
            logger.info("Swagger UI files downloaded successfully")
        else:
            logger.debug("Swagger UI files already exist")
            
        return True
    except Exception as e:
        logger.error(f"Error downloading Swagger UI files: {e}")
        return False


if __name__ == "__main__":
    # Setup for standalone execution
    try:
        # Make sure Swagger UI files are available
        asyncio.run(download_swagger_ui_files())
        
        # Run the server
        asyncio.run(run_api_server())
    except KeyboardInterrupt:
        logger.info("API server stopped by user")
    except Exception as e:
        logger.error(f"Error running API server: {e}")
        sys.exit(1) 