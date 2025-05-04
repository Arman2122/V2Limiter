"""
v2iplimit.py is the
main file that run other files and functions to run the program.
"""

import argparse
import asyncio
import signal
import sys
import time
import os

from run_telegram import run_telegram_bot
from telegram_bot.send_message import send_logs
from utils.check_usage import run_check_users_usage
from utils.get_logs import (
    TASKS,
    check_and_add_new_nodes,
    create_node_task,
    create_panel_task,
    handle_cancel,
    handle_cancel_all,
)
from utils.handel_dis_users import DisabledUsers
from utils.logs import logger
from utils.panel_api import (
    enable_dis_user,
    enable_selected_users,
    get_nodes,
)
from utils.read_config import read_config
from utils.types import PanelType
from utils.redis_utils import redis_client
from api.server import run_api_server, download_swagger_ui_files

VERSION = "1.0.7"  # Updated version number

# Create banner
def print_banner():
    """Print application banner with version information."""
    banner = f"""
╔════════════════════════════════════════════════════════════╗
║                      MARZ LIMITER                          ║
║                                                            ║
║  Version: {VERSION}                                               ║
║  A network usage limiter & management tool for Marz Panel  ║
║                                                            ║
║  Press Ctrl+C to exit gracefully                          ║
╚════════════════════════════════════════════════════════════╝
"""
    print(banner)
    logger.info(f"Starting Marz Limiter v{VERSION}")

# Setup signal handlers
def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        logger.warning("Shutdown signal received! Shutting down gracefully...")
        print("\nShutting down gracefully... Please wait.")
        
        # Don't try to send Telegram messages from signal handler
        # It's not safe to use asyncio.run() from here
        logger.info("Signal received, exiting...")
        
        # Wait a moment before exiting
        time.sleep(1)
        
        # Exit with success code
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

parser = argparse.ArgumentParser(description="Marz Limiter - Network usage limiter for Marz Panel")
parser.add_argument("--version", action="version", version=VERSION)
args = parser.parse_args()

dis_obj = DisabledUsers()


async def main():
    """Main function to run the code."""
    print_banner()
    logger.info("Initializing application components...")
    
    # Start Telegram bot
    logger.info("Starting Telegram Bot...")
    telegram_task = asyncio.create_task(run_telegram_bot())
    await asyncio.sleep(2)
    await send_logs(f"ℹ️ <b>System started</b>\n\nMarz Limiter v{VERSION} is now running.")
    
    # Load configuration
    logger.info("Loading configuration...")
    while True:
        try:
            config_file = await read_config(check_required_elements=True)
            logger.info("Configuration loaded successfully")
            break
        except ValueError as error:
            logger.error(f"Configuration error: {error}")
            await send_logs(("<code>" + str(error) + "</code>"))
            await send_logs(
                "Please fill the <b>required</b> elements"
                + " (you can see more detail for each one with sending /start):\n"
                + "/create_config: <code>Config panel information (username, password,...)</code>\n"
                + "/country_code: <code>Set your country code"
                + " (to increase accuracy)</code>\n"
                + "/set_general_limit_number: <code>Set the general limit number</code>\n"
                + "/set_check_interval: <code>Set the check interval time</code>\n"
                + "/set_time_to_active_users: <code>Set the time to active users</code>\n"
                + "\nIn <b>60 seconds</b> later the program will try again."
            )
            logger.warning("Waiting 60 seconds before retrying configuration load")
            await asyncio.sleep(60)
    
    panel_data = PanelType(
        config_file["PANEL_USERNAME"],
        config_file["PANEL_PASSWORD"],
        config_file["PANEL_DOMAIN"],
    )
    logger.info(f"Panel configuration set for domain: {panel_data.panel_domain}")
    
    # Process disabled users
    logger.info("Processing disabled users...")
    dis_users = await dis_obj.read_and_clear_users()
    if dis_users:
        logger.info(f"Found {len(dis_users)} disabled users to re-enable")
    await enable_selected_users(panel_data, dis_users)
    
    # Initialize Redis
    logger.info("Initializing Redis connection...")
    try:
        await redis_client.initialize()
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.error(f"Error initializing Redis: {e}")
        await send_logs(f"⚠️ <b>Redis initialization error</b>\n\n<code>{str(e)}</code>")
        logger.warning("Continuing without Redis functionality")
    
    # Initialize nodes
    logger.info("Initializing node connections...")
    await get_nodes(panel_data)
    
    # Download Swagger UI files
    logger.info("Setting up API server...")
    try:
        await download_swagger_ui_files()
    except Exception as e:
        logger.error(f"Error downloading Swagger UI files: {e}")
        await send_logs(f"⚠️ <b>API initialization warning</b>\n\nFailed to download Swagger UI files: <code>{str(e)}</code>")
    
    # Start API server in a separate task
    api_server_task = asyncio.create_task(run_api_server())
    logger.info("API server task created")
    
    # Start all tasks
    logger.info("Starting all system tasks...")
    async with asyncio.TaskGroup() as tg:
        logger.info("Creating panel task...")
        await create_panel_task(panel_data, tg)
        await asyncio.sleep(5)
        
        nodes_list = await get_nodes(panel_data)
        if nodes_list and not isinstance(nodes_list, ValueError):
            logger.info(f"Found {len(nodes_list)} nodes, initializing node tasks...")
            connected_nodes = 0
            for node in nodes_list:
                if node.status == "connected":
                    connected_nodes += 1
                    logger.info(f"Creating task for node: {node.name}")
                    await create_node_task(panel_data, tg, node)
                    await asyncio.sleep(4)
            logger.info(f"Initialized {connected_nodes} connected nodes out of {len(nodes_list)} total nodes")
        else:
            logger.warning("No nodes found or error getting nodes")
        
        logger.info("Starting node monitoring task...")
        tg.create_task(
            check_and_add_new_nodes(panel_data, tg),
            name="add_new_nodes",
        )
        
        logger.info("Starting cancel handlers...")
        tg.create_task(
            handle_cancel(panel_data, TASKS),
            name="cancel_disable_nodes",
        )
        tg.create_task(
            handle_cancel_all(TASKS, panel_data),
            name="cancel_all",
        )
        
        logger.info("Starting user re-enablement task...")
        tg.create_task(
            enable_dis_user(panel_data),
            name="enable_dis_user",
        )
        
        logger.info("All tasks started successfully")
        logger.info("Starting user usage monitoring...")
        await run_check_users_usage(panel_data)


if __name__ == "__main__":
    setup_signal_handlers()
    
    # Main application loop
    while True:
        try:
            logger.info("Starting main application loop")
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.warning("Application interrupted by user")
            sys.exit(0)
        except Exception as er:  # pylint: disable=broad-except
            logger.error(f"Fatal error in main loop: {er}", exc_info=True)
            logger.info("Restarting in 10 seconds...")
            time.sleep(10)
