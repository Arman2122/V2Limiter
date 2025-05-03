"""
This module sets up the logging configuration for the application.
It configures a rotating file handler and a stream handler for the root logger.
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Define custom formatter with colors for console output
class ColoredFormatter(logging.Formatter):
    """Custom formatter adding colors to levelname output in console."""
    
    COLORS = {
        'DEBUG': '\033[94m',      # Blue
        'INFO': '\033[92m',       # Green
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[91m\033[1m',  # Bold Red
        'RESET': '\033[0m'        # Reset color
    }
    
    def format(self, record):
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set up rotating file handler for detailed logs
log_filename = f"logs/app_{datetime.now().strftime('%Y%m%d')}.log"
file_handler = RotatingFileHandler(
    log_filename, maxBytes=10 * 10**6, backupCount=5  # 10MB per file, keep 5 old files
)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s"
)
file_handler.setFormatter(file_formatter)

# Set up stream handler for console output with colors
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
console_formatter = ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
stream_handler.setFormatter(console_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def get_logger():
    """Get the configured logger instance."""
    return logger
