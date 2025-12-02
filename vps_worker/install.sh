#!/bin/bash
#
# VPS Worker Installation Script
# For Ubuntu 24.04 (Beget.com or any VPS)
#
# Usage: sudo bash install.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Config
INSTALL_DIR="/opt/vps_worker"
LOG_DIR="/var/log/vps_worker"
SERVICE_USER="www-data"

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}VPS Worker Installation Script${NC}"
echo -e "${GREEN}=================================${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (sudo bash install.sh)${NC}"
    exit 1
fi

# Update system
echo -e "\n${YELLOW}Updating system packages...${NC}"
apt update && apt upgrade -y

# Install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
apt install -y python3.12 python3.12-venv python3-pip git curl

# Create directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p $INSTALL_DIR
mkdir -p $LOG_DIR
mkdir -p $INSTALL_DIR/sessions
mkdir -p $INSTALL_DIR/logs
mkdir -p $INSTALL_DIR/data

# Copy files
echo -e "\n${YELLOW}Copying files...${NC}"
cp -r . $INSTALL_DIR/
cd $INSTALL_DIR

# Create virtual environment
echo -e "\n${YELLOW}Creating Python virtual environment...${NC}"
python3.12 -m venv venv
source venv/bin/activate

# Install Python packages
echo -e "\n${YELLOW}Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Create .env from example if not exists
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo -e "\n${YELLOW}Creating .env file from example...${NC}"
    cp .env.example .env
    echo -e "${RED}IMPORTANT: Edit $INSTALL_DIR/.env with your credentials!${NC}"
fi

# Set permissions
echo -e "\n${YELLOW}Setting permissions...${NC}"
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
chown -R $SERVICE_USER:$SERVICE_USER $LOG_DIR
chmod 600 $INSTALL_DIR/.env
chmod +x $INSTALL_DIR/main.py

# Install systemd service
echo -e "\n${YELLOW}Installing systemd service...${NC}"
cp vps-worker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable vps-worker

echo -e "\n${GREEN}=================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}=================================${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. Edit configuration: ${GREEN}nano $INSTALL_DIR/.env${NC}"
echo -e "2. Start service: ${GREEN}sudo systemctl start vps-worker${NC}"
echo -e "3. Check status: ${GREEN}sudo systemctl status vps-worker${NC}"
echo -e "4. View logs: ${GREEN}tail -f $LOG_DIR/worker.log${NC}"

echo -e "\n${YELLOW}Required configuration in .env:${NC}"
echo -e "- SUPABASE_URL and SUPABASE_KEY"
echo -e "- TELEGRAM_API_ID and TELEGRAM_API_HASH"
echo -e "- BOT_TOKEN and ADMIN_CHAT_ID"

echo -e "\n${YELLOW}Commands:${NC}"
echo -e "Start:   ${GREEN}sudo systemctl start vps-worker${NC}"
echo -e "Stop:    ${GREEN}sudo systemctl stop vps-worker${NC}"
echo -e "Restart: ${GREEN}sudo systemctl restart vps-worker${NC}"
echo -e "Status:  ${GREEN}sudo systemctl status vps-worker${NC}"
echo -e "Logs:    ${GREEN}journalctl -u vps-worker -f${NC}"
