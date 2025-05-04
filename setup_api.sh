#!/bin/bash

# Script to set up Redis and the API server for Marz Limiter
# This script should be run as root or with sudo

# Text formatting
BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run this script as root or with sudo${NC}"
  exit 1
fi

echo -e "${BOLD}Marz Limiter API and Redis Setup${NC}"
echo "This script will set up Redis and configure the API server."
echo -e "${YELLOW}Note: This script assumes you're running Ubuntu.${NC}"
echo ""

# Install Redis
echo -e "${BOLD}Step 1: Installing Redis${NC}"
apt update
if apt install -y redis-server; then
  echo -e "${GREEN}Redis installation successful!${NC}"
else
  echo -e "${RED}Failed to install Redis. Please install it manually.${NC}"
  exit 1
fi

# Configure Redis to start on boot
echo -e "${BOLD}Step 2: Configuring Redis${NC}"
systemctl enable redis-server
systemctl start redis-server

# Check if Redis is running
if systemctl is-active --quiet redis-server; then
  echo -e "${GREEN}Redis is running!${NC}"
else
  echo -e "${RED}Redis is not running. Please check the Redis logs.${NC}"
  exit 1
fi

# Install Nginx if not already installed
echo -e "${BOLD}Step 3: Installing Nginx${NC}"
if apt install -y nginx; then
  echo -e "${GREEN}Nginx installation successful!${NC}"
else
  echo -e "${RED}Failed to install Nginx. Please install it manually.${NC}"
  exit 1
fi

# Enable and start Nginx
systemctl enable nginx
systemctl start nginx

# Check if Nginx is running
if systemctl is-active --quiet nginx; then
  echo -e "${GREEN}Nginx is running!${NC}"
else
  echo -e "${RED}Nginx is not running. Please check the Nginx logs.${NC}"
  exit 1
fi

# Copy Nginx configuration
echo -e "${BOLD}Step 4: Configuring Nginx${NC}"

# Check if the configuration file exists
if [ -f "nginx/marz-limiter-api.conf" ]; then
  # Create a backup of existing configuration if it exists
  if [ -f "/etc/nginx/sites-available/marz-limiter-api.conf" ]; then
    cp /etc/nginx/sites-available/marz-limiter-api.conf /etc/nginx/sites-available/marz-limiter-api.conf.bak
    echo "Created backup of existing configuration as /etc/nginx/sites-available/marz-limiter-api.conf.bak"
  fi
  
  # Copy the new configuration
  cp nginx/marz-limiter-api.conf /etc/nginx/sites-available/
  
  # Create a symlink if it doesn't exist
  if [ ! -f "/etc/nginx/sites-enabled/marz-limiter-api.conf" ]; then
    ln -s /etc/nginx/sites-available/marz-limiter-api.conf /etc/nginx/sites-enabled/
  fi
  
  echo -e "${GREEN}Nginx configuration copied!${NC}"
  
  # Test Nginx configuration
  if nginx -t; then
    echo -e "${GREEN}Nginx configuration is valid!${NC}"
    # Reload Nginx to apply changes
    systemctl reload nginx
  else
    echo -e "${RED}Nginx configuration is invalid. Please check the configuration file.${NC}"
    exit 1
  fi
else
  echo -e "${RED}Nginx configuration file not found at nginx/marz-limiter-api.conf${NC}"
  echo "Please check if the file exists or create it manually."
  exit 1
fi

# Generate API token
echo -e "${BOLD}Step 5: Generating API token${NC}"
echo "Please use the Telegram bot command /generate_api_token to generate a token."
echo "Once generated, the token will be automatically saved to config.json."

echo -e "${BOLD}Step 6: Configuration Notes${NC}"
echo -e "${YELLOW}Important:${NC} Before running the API server, make sure to update config.json with your desired settings:"
echo "  - API_PORT: The port the API server will listen on (default: 8080)"
echo "  - SWAGGER_PORT: The port for Swagger UI (default: same as API_PORT)"
echo "  - API_DOMAIN: Your domain name (optional)"
echo "  - REDIS_HOST: Redis host (default: localhost)"
echo "  - REDIS_PORT: Redis port (default: 6379)"
echo "  - REDIS_DB: Redis database number (default: 0)"
echo "  - REDIS_PASSWORD: Redis password (default: null)"

echo -e "${BOLD}Step 7: Starting the Application${NC}"
echo "To start the application, run:"
echo "  python3 run.py"
echo "This will start the main application, including the API server."

echo -e "${GREEN}Setup complete!${NC}" 