#!/bin/bash
#
# Quick Install Script for Telegram Worker
# Run as root: bash quick_install.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/root/telegram-worker"

echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        TELEGRAM WORKER - QUICK INSTALL               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Запустите от root: sudo bash quick_install.sh${NC}"
    exit 1
fi

# Step 1: Update system
echo -e "\n${YELLOW}[1/7] Обновление системы...${NC}"
apt update && apt upgrade -y

# Step 2: Install Python
echo -e "\n${YELLOW}[2/7] Установка Python 3.12...${NC}"
apt install -y python3.12 python3.12-venv python3-pip curl git

# Step 3: Create directories
echo -e "\n${YELLOW}[3/7] Создание директорий...${NC}"
mkdir -p $INSTALL_DIR/sessions
mkdir -p $INSTALL_DIR/logs
mkdir -p $INSTALL_DIR/data

# Step 4: Create venv
echo -e "\n${YELLOW}[4/7] Создание виртуального окружения...${NC}"
cd $INSTALL_DIR
python3.12 -m venv venv
source venv/bin/activate

# Step 5: Install dependencies
echo -e "\n${YELLOW}[5/7] Установка зависимостей...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Step 6: Create .env if not exists
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo -e "\n${YELLOW}[6/7] Создание .env файла...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠️  ВАЖНО: Заполните .env файл вашими ключами!${NC}"
else
    echo -e "\n${YELLOW}[6/7] .env файл уже существует${NC}"
fi

# Step 7: Create systemd service
echo -e "\n${YELLOW}[7/7] Создание systemd сервиса...${NC}"
cat > /etc/systemd/system/telegram-worker.service << EOF
[Unit]
Description=Telegram Worker Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/worker.log
StandardError=append:$INSTALL_DIR/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable telegram-worker

# Done
echo -e "\n${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            ✅ УСТАНОВКА ЗАВЕРШЕНА!                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}📋 Следующие шаги:${NC}"
echo -e ""
echo -e "1. ${BLUE}Заполните конфигурацию:${NC}"
echo -e "   nano $INSTALL_DIR/.env"
echo -e ""
echo -e "2. ${BLUE}Протестируйте подключения:${NC}"
echo -e "   cd $INSTALL_DIR && source venv/bin/activate"
echo -e "   python test_connection.py"
echo -e ""
echo -e "3. ${BLUE}Запустите сервис:${NC}"
echo -e "   systemctl start telegram-worker"
echo -e ""
echo -e "4. ${BLUE}Проверьте статус:${NC}"
echo -e "   systemctl status telegram-worker"
echo -e ""
echo -e "5. ${BLUE}Смотрите логи:${NC}"
echo -e "   tail -f $INSTALL_DIR/logs/worker.log"
echo -e ""
echo -e "${GREEN}Документация: $INSTALL_DIR/INSTALL_GUIDE.md${NC}"
