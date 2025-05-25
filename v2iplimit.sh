#!/bin/bash
[ "$(uname)" = "Linux" ] && sed -i 's/\r$//' "$0"

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Banner function
show_banner() {
    clear
    echo -e "${BLUE}${BOLD}"
    echo "┌──────────────────────────────────────────┐"
    echo "│                                          │"
    echo "│             V2IP LIMITER                 │"
    echo "│       Advanced Installation Script       │"
    echo "│               V 1.0.7                    │"
    echo "│                                          │"
    echo "└──────────────────────────────────────────┘"
    echo -e "${NC}"
}

# Check for required dependencies
check_dependencies() {
    local missing_deps=()
    
    for cmd in git screen jq; do
        if ! command -v $cmd &>/dev/null; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${RED}${BOLD}Missing dependencies:${NC} ${missing_deps[*]}"
        echo -e "${YELLOW}Installing missing dependencies...${NC}"
        
        # Determine package manager
        if command -v apt &>/dev/null; then
            sudo apt update
            sudo apt install -y ${missing_deps[*]}
        elif command -v yum &>/dev/null; then
            sudo yum install -y ${missing_deps[*]}
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y ${missing_deps[*]}
        else
            echo -e "${RED}${BOLD}Error:${NC} Could not determine package manager."
            echo "Please install the following manually: ${missing_deps[*]}"
            exit 1
        fi
    fi
}

# Function to clone or update repository
setup_repository() {
    local repo_dir="V2Limiter"
    
    if [ -d "$repo_dir" ]; then
        echo -e "${YELLOW}Repository already exists. Updating...${NC}"
        cd "$repo_dir"
        git pull
        cd ..
    else
        echo -e "${CYAN}Cloning repository...${NC}"
        git clone https://github.com/Arman2122/V2Limiter.git
        if [ $? -ne 0 ]; then
            echo -e "${RED}${BOLD}Error:${NC} Failed to clone repository."
            exit 1
        fi
    fi
    
    # Set up correct permissions
    cd "$repo_dir"
    chmod +x *.py
    chmod +x main.py
    cd ..
}

# Function to check if service is running
is_running() {
    if systemctl is-active --quiet v2iplimit.service 2>/dev/null; then
        return 0
    elif screen -list | grep -q "v2iplimit"; then
        return 0
    else
        return 1
    fi
}

# Function to set up configuration
setup_config() {
    local config_file="V2Limiter/config.json"
    
    if [ -f "$config_file" ]; then
        echo -e "${GREEN}Configuration file exists.${NC}"
        echo -e "${YELLOW}Do you want to use the existing configuration? [Y/n]${NC}"
        read -r use_existing
        
        if [[ "$use_existing" =~ ^[Nn]$ ]]; then
            create_config
        fi
    else
        echo -e "${YELLOW}Configuration file not found. Creating new configuration.${NC}"
        create_config
    fi
}

# Function to create configuration
create_config() {
    local config_file="V2Limiter/config.json"
    
    echo -e "${CYAN}${BOLD}Configuration Setup${NC}"
    
    # Initialize with default values from sample
    if [ -f "V2Limiter/config.sample.json" ]; then
        cp "V2Limiter/config.sample.json" "$config_file"
    else
        echo "{}" > "$config_file"
    fi
    
    # Bot Token
    echo -e "${CYAN}You need to create a Telegram bot and get the token from @BotFather.${NC}"
    read -p "Enter BOT_TOKEN: " bot_token
    jq --arg token "$bot_token" '.BOT_TOKEN = $token' "$config_file" > tmp.json && mv tmp.json "$config_file"
    
    # Admin IDs
    echo -e "${CYAN}Enter your Telegram chat ID (you can get it from @userinfobot).${NC}"
    read -p "Enter ADMIN ID: " admin_id
    jq --arg admin "$admin_id" '.ADMINS = [$admin | tonumber]' "$config_file" > tmp.json && mv tmp.json "$config_file"
    
    # Panel Information
    echo -e "${CYAN}Enter Marzban panel details:${NC}"
    read -p "Panel Domain (with port if needed): " panel_domain
    read -p "Panel Username: " panel_username
    read -p "Panel Password: " panel_password
    
    jq --arg domain "$panel_domain" --arg username "$panel_username" --arg password "$panel_password" \
        '.PANEL_DOMAIN = $domain | .PANEL_USERNAME = $username | .PANEL_PASSWORD = $password' \
        "$config_file" > tmp.json && mv tmp.json "$config_file"
    
    # Advanced Settings
    echo -e "${CYAN}Do you want to configure advanced settings? [y/N]${NC}"
    read -r configure_advanced
    
    if [[ "$configure_advanced" =~ ^[Yy]$ ]]; then
        read -p "Check interval in seconds (default: 240): " check_interval
        read -p "Time to consider users active in seconds (default: 1800): " active_time
        read -p "General connection limit per user (default: 2): " general_limit
        
        # Set values if provided
        if [ -n "$check_interval" ]; then
            jq --arg interval "$check_interval" '.CHECK_INTERVAL = ($interval | tonumber)' "$config_file" > tmp.json && mv tmp.json "$config_file"
        fi
        
        if [ -n "$active_time" ]; then
            jq --arg time "$active_time" '.TIME_TO_ACTIVE_USERS = ($time | tonumber)' "$config_file" > tmp.json && mv tmp.json "$config_file"
        fi
        
        if [ -n "$general_limit" ]; then
            jq --arg limit "$general_limit" '.GENERAL_LIMIT = ($limit | tonumber)' "$config_file" > tmp.json && mv tmp.json "$config_file"
        fi
        
        # API Configuration
        echo -e "${CYAN}Do you want to configure the API? [y/N]${NC}"
        read -r configure_api
        
        if [[ "$configure_api" =~ ^[Yy]$ ]]; then
            read -p "API Token: " api_token
            read -p "API Port (default: 8080): " api_port
            
            if [ -n "$api_token" ]; then
                jq --arg token "$api_token" '.API_TOKEN = $token' "$config_file" > tmp.json && mv tmp.json "$config_file"
            fi
            
            if [ -n "$api_port" ]; then
                jq --arg port "$api_port" \
                    '.API_PORT = ($port | tonumber) | .SWAGGER_PORT = ($port | tonumber)' \
                    "$config_file" > tmp.json && mv tmp.json "$config_file"
            fi
        fi
        
        # Redis Configuration
        echo -e "${CYAN}Do you want to configure Redis? [y/N]${NC}"
        read -r configure_redis
        
        if [[ "$configure_redis" =~ ^[Yy]$ ]]; then
            read -p "Redis Host (default: localhost): " redis_host
            read -p "Redis Port (default: 6379): " redis_port
            read -p "Redis Password (press Enter for none): " redis_password
            
            if [ -n "$redis_host" ]; then
                jq --arg host "$redis_host" '.REDIS_HOST = $host' "$config_file" > tmp.json && mv tmp.json "$config_file"
            fi
            
            if [ -n "$redis_port" ]; then
                jq --arg port "$redis_port" '.REDIS_PORT = ($port | tonumber)' "$config_file" > tmp.json && mv tmp.json "$config_file"
            fi
            
            if [ -n "$redis_password" ]; then
                jq --arg password "$redis_password" '.REDIS_PASSWORD = $password' "$config_file" > tmp.json && mv tmp.json "$config_file"
            fi
        fi
    fi
    
    echo -e "${GREEN}${BOLD}Configuration saved successfully!${NC}"
}

# Function to setup systemd service
setup_systemd() {
    echo -e "${CYAN}${BOLD}Systemd Service Setup${NC}"
    
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Please run as root to set up systemd service.${NC}"
        return 1
    fi
    

    local script_path=$(readlink -f "$0")
    local script_dir=$(dirname "$script_path")
    
    if [[ "$script_dir" == *"/V2Limiter"* ]]; then
        local abs_repo_path=$(echo "$script_dir" | sed 's|\(.*V2Limiter\).*|\1|')
    elif [[ -d "$script_dir/V2Limiter" ]]; then
        local abs_repo_path="$script_dir/V2Limiter"
    else
        local abs_repo_path="$script_dir"
    fi
    
    if [[ ! -f "$abs_repo_path/v2iplimit.py" ]]; then
        echo -e "${YELLOW}Warning: Could not find run.py in $abs_repo_path${NC}"
        echo -e "${YELLOW}Using current directory as fallback${NC}"
        local abs_repo_path=$(pwd)
    fi
    
    # Create systemd service file
    cat > /etc/systemd/system/v2iplimit.service << EOF
[Unit]
Description=V2IP Limiter
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=root
WorkingDirectory=${abs_repo_path}
ExecStart=/usr/bin/python3 ${abs_repo_path}/v2iplimit.py
Restart=on-failure
RestartSec=10
KillSignal=SIGINT
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal

# Security hardening
ProtectSystem=full
PrivateTmp=true
ProtectControlGroups=true
ProtectKernelModules=true
ProtectKernelTunables=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictNamespaces=true

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd daemon
    systemctl daemon-reload
    
    echo -e "${GREEN}${BOLD}Systemd service created!${NC}"
    echo -e "${CYAN}You can now manage the service with these commands:${NC}"
    echo -e "${YELLOW}  systemctl start v2iplimit${NC} - Start the service"
    echo -e "${YELLOW}  systemctl stop v2iplimit${NC} - Stop the service"
    echo -e "${YELLOW}  systemctl status v2iplimit${NC} - Check service status"
    echo -e "${YELLOW}  systemctl enable v2iplimit${NC} - Enable on boot"
}

# Function to start program using screen
start_with_screen() {
    if is_running; then
        echo -e "${YELLOW}The program is already running.${NC}"
        return
    fi
    
    cd V2Limiter
    screen -Sdm v2iplimit python3 main.py
    cd ..
    
    echo -e "${GREEN}${BOLD}The program has been started with screen.${NC}"
    echo -e "${CYAN}To attach to the screen session: ${YELLOW}screen -r v2iplimit${NC}"
}

# Function to start program using systemd
start_with_systemd() {
    if ! systemctl status v2iplimit.service &>/dev/null; then
        echo -e "${RED}Systemd service not found. Please set up the service first.${NC}"
        return
    fi
    
    sudo systemctl start v2iplimit.service
    echo -e "${GREEN}${BOLD}The program has been started with systemd.${NC}"
}

# Function to stop program
stop_program() {
    # Check if running with systemd
    if systemctl is-active --quiet v2iplimit.service; then
        sudo systemctl stop v2iplimit.service
        echo -e "${GREEN}${BOLD}The program has been stopped (systemd).${NC}"
    # Check if running with screen
    elif screen -list | grep -q "v2iplimit"; then
        screen -S v2iplimit -X quit
        echo -e "${GREEN}${BOLD}The program has been stopped (screen).${NC}"
    else
        echo -e "${YELLOW}The program is not running.${NC}"
    fi
}

# Function to attach to screen session
attach_program() {
    if screen -list | grep -q "v2iplimit"; then
        echo -e "${CYAN}You are about to attach to the program's screen session."
        echo -e "To detach without stopping, press ${BOLD}Ctrl-a followed by d${NC}"
        read -p "Do you want to continue? [Y/n] " confirm
        
        if [[ "$confirm" =~ ^[Nn]$ ]]; then
            return
        fi
        
        screen -r v2iplimit
    else
        echo -e "${YELLOW}No screen session found.${NC}"
    fi
}

# Main menu function
show_menu() {
    show_banner
    
    echo -e "${CYAN}${BOLD}MAIN MENU${NC}"
    echo -e "${BLUE}--------------------------------------${NC}"
    echo -e "${YELLOW}1.${NC} Install/Update Repository"
    echo -e "${YELLOW}2.${NC} Configure Settings"
    echo -e "${YELLOW}3.${NC} Set Up Systemd Service"
    echo -e "${YELLOW}4.${NC} Start with Screen"
    echo -e "${YELLOW}5.${NC} Start with Systemd"
    echo -e "${YELLOW}6.${NC} Stop Service"
    echo -e "${YELLOW}7.${NC} Attach to Screen"
    echo -e "${YELLOW}8.${NC} Check Status"
    echo -e "${YELLOW}9.${NC} Exit"
    echo -e "${BLUE}--------------------------------------${NC}"
    
    read -p "Enter your choice [1-9]: " choice
    
    case $choice in
        1) setup_repository ;;
        2) setup_config ;;
        3) setup_systemd ;;
        4) start_with_screen ;;
        5) start_with_systemd ;;
        6) stop_program ;;
        7) attach_program ;;
        8) check_status ;;
        9) exit 0 ;;
        *) echo -e "${RED}Invalid choice. Please try again.${NC}" ;;
    esac
    
    # Pause before showing menu again
    echo
    read -p "Press Enter to continue..."
}

# Function to check status
check_status() {
    echo -e "${CYAN}${BOLD}SERVICE STATUS${NC}"
    
    # Check systemd status
    if systemctl status v2iplimit.service &>/dev/null; then
        echo -e "${YELLOW}Systemd service:${NC} $(systemctl is-active v2iplimit.service)"
        systemctl status v2iplimit.service --no-pager | head -n 15
    else
        echo -e "${YELLOW}Systemd service:${NC} Not configured"
    fi
    
    # Check screen status
    if screen -list | grep -q "v2iplimit"; then
        echo -e "${YELLOW}Screen session:${NC} Running"
        screen -list | grep "v2iplimit"
    else
        echo -e "${YELLOW}Screen session:${NC} Not running"
    fi
    
    # Check configuration
    if [ -f "V2Limiter/config.json" ]; then
        echo -e "${YELLOW}Configuration:${NC} Present"
    else
        echo -e "${YELLOW}Configuration:${NC} Missing"
    fi
}

# Parse command line arguments
if [ $# -gt 0 ]; then
    case $1 in
        start)
            check_dependencies
            
            if [ "$2" = "systemd" ]; then
                start_with_systemd
            else
                start_with_screen
            fi
            ;;
        stop)
            stop_program
            ;;
        status)
            check_status
            ;;
        setup)
            check_dependencies
            setup_repository
            setup_config
            ;;
        *)
            echo -e "${RED}Usage: $0 {start|stop|status|setup}${NC}"
            echo -e "${YELLOW}  start [systemd] - Start the service (with systemd if specified)${NC}"
            echo -e "${YELLOW}  stop - Stop the service${NC}"
            echo -e "${YELLOW}  status - Check service status${NC}"
            echo -e "${YELLOW}  setup - Set up repository and configuration${NC}"
            exit 1
            ;;
    esac
else
    # Interactive mode
    check_dependencies
    
    while true; do
        show_menu
    done
fi
