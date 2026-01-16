#!/bin/bash
# Setup script for Control Plane (run as aegis user)
# Usage: sudo -u aegis /home/aegis/Aegis.net/scripts/setup-control-plane.sh

set -e

AEGIS_DIR="/home/aegis/Aegis.net"
CONTROL_PLANE_DIR="$AEGIS_DIR/control-plane"

echo "======================================"
echo "Control Plane Setup"
echo "======================================"

cd $CONTROL_PLANE_DIR

echo ""
echo "Step 1/4: Creating virtual environment..."
python3.11 -m venv venv

echo ""
echo "Step 2/4: Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Step 3/4: Creating .env configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    
    # Generate secrets
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Update .env with generated secrets
    sed -i "s/change-me-in-production-min-32-chars/$SECRET_KEY/" .env
    sed -i "s/CHANGE_THIS_TO_RANDOM_SECRET_MIN_32_CHARS/$JWT_SECRET/" .env
    
    echo "✓ .env file created with generated secrets"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and configure:"
    echo "   - AUTHORIZED_CLI_KEYS (add your SSH public key)"
    echo "   - WHITELISTED_IPS (add your IP address)"
    echo "   - Other settings as needed"
else
    echo ".env file already exists, skipping"
fi

echo ""
echo "Step 4/4: Testing configuration..."
python3 -c "from api.config import settings; print('✓ Configuration loaded successfully')"

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env: nano $CONTROL_PLANE_DIR/.env"
echo "2. Test manually: source venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8000"
echo "3. Install systemd service (as root): sudo cp $AEGIS_DIR/scripts/aegis-control-plane.service /etc/systemd/system/"
echo "4. Start service: sudo systemctl start aegis-control-plane"
