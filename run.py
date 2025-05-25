#!/usr/bin/env python3
"""
Main entry point for Marz Limiter application.
This script provides a clean way to start the application with proper error handling.
"""

import os
import sys
import traceback
import asyncio
import time
import signal

# Ensure the application files are in the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from utils.logs import logger

def check_prerequisites():
    """Check if all prerequisites are met before starting the application."""
    # Check if config file exists
    if not os.path.isfile('config.json') and not os.path.isfile('config.sample.json'):
        logger.critical("No configuration file found. Please create config.json before running.")
        print("\nNo configuration file found. You need to create a config.json file.")
        print("You can copy config.sample.json to config.json and edit it with your settings.")
        return False
    
    # Make sure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    return True

def setup_signal_handlers(loop):
    """Setup signal handlers for graceful shutdown."""
    
    def signal_handler():
        logger.info("Shutdown requested - closing event loop...")
        # Cancel all running tasks
        for task in asyncio.all_tasks(loop):
            if not task.done() and task != asyncio.current_task():
                logger.debug(f"Cancelling task: {task.get_name()}")
                task.cancel()
        loop.stop()
    
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

async def start_application():
    """Start the main application."""
    try:
        # Import at runtime to avoid potential circular imports
        logger.info("Loading main application module...")
        from v2iplimit import main
        
        # Run the main application
        logger.info("Starting main application...")
        await main()
        
    except asyncio.CancelledError:
        logger.info("Application task cancelled")
        return True
    except Exception as e:
        logger.critical(f"Fatal error in application: {e}")
        logger.error(traceback.format_exc())
        print(f"\nFatal error: {e}")
        print("Check the logs for more details.")
        return False
    
    return True

def main():
    """Main entry point."""
    loop = None
    try:
        # Check prerequisites
        if not check_prerequisites():
            sys.exit(1)
        
        # Create and get the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Setup signal handlers properly
        setup_signal_handlers(loop)
        
        # Run the application until completion or interrupted
        logger.info("Starting application...")
        
        try:
            loop.run_until_complete(start_application())
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, shutting down...")
        except Exception as e:
            logger.critical(f"Unhandled exception in main: {e}")
            logger.error(traceback.format_exc())
            print(f"\nCritical error: {e}")
            print("Check the logs for more details.")
        finally:
            # Cancel any remaining tasks if the loop is still running
            try:
                if loop.is_running():
                    remaining_tasks = [task for task in asyncio.all_tasks(loop) 
                                      if not task.done() and task != asyncio.current_task()]
                    if remaining_tasks:
                        logger.info(f"Cancelling {len(remaining_tasks)} remaining tasks...")
                        for task in remaining_tasks:
                            task.cancel()
                        loop.run_until_complete(asyncio.gather(*remaining_tasks, return_exceptions=True))
            except RuntimeError as e:
                logger.error(f"Error during task cancellation: {e}")
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
        logger.info("Application terminated by user via KeyboardInterrupt")
    finally:
        print("\nShutting down...")
        if loop is not None:
            try:
                if not loop.is_closed():
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.close()
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
        logger.info("Application shutdown complete")

if __name__ == "__main__":
    main() 