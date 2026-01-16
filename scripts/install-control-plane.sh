#!/bin/bash
# Aegis.net Control Plane - Automated Installation Script for Ubuntu
# Usage: curl -sSL https://raw.../install-control-plane.sh | bash

set -e

echo "======================================"
echo "Aegis.net Control Plane Installation"
echo "======================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Variables
AEGIS_USER="aegis"
AEGIS_HOME="/home/$AEGIS_USER"
AEGIS_DIR="$AEGIS_HOME/Aegis.net"
PYTHON_VERSION="3.11"

echo ""
echo "Step 1/8: Updating system..."
apt update && apt upgrade -y

echo ""
echo "Step 2/8: Installing dependencies..."
apt install -y git curl wget build-essential software-properties-common

echo ""
echo "Step 3/8: Installing Python $PYTHON_VERSION..."
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev python3-pip

echo ""
echo "Step 4/8: Installing Redis..."
apt install -y redis-server

# Configure Redis
sed -i 's/^# maxmemory .*/maxmemory 2gb/' /etc/redis/redis.conf
sed -i 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

systemctl enable redis-server
systemctl start redis-server

echo ""
echo "Step 5/8: Creating aegis user..."
if ! id "$AEGIS_USER" &>/dev/null; then
    useradd -m -s /bin/bash $AEGIS_USER
    echo "User $AEGIS_USER created"
else
    echo "User $AEGIS_USER already exists"
fi

echo ""
echo "Step 6/8: Setting up application directory..."
# Note: You need to copy files manually or clone from git
# This script assumes files will be uploaded separately
mkdir -p $AEGIS_DIR
chown -R $AEGIS_USER:$AEGIS_USER $AEGIS_DIR

echo ""
echo "Step 7/8: Installing Nginx..."
apt install -y nginx

echo ""
echo "Step 8/8: Setting up firewall..."
apt install -y ufw
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

echo ""
echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Upload Aegis.net files to: $AEGIS_DIR"
echo "2. Run setup script: sudo -u $AEGIS_USER $AEGIS_DIR/scripts/setup-control-plane.sh"
echo "3. Configure .env file in $AEGIS_DIR/control-plane/"
echo "4. Start service: systemctl start aegis-control-plane"
echo ""
echo "See docs/DEPLOYMENT_UBUNTU.md for detailed instructions"
