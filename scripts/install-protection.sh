#!/bin/bash
# Aegis.net - Автоматическая установка СЕРВЕР 2 (PROTECTION/ЗАЩИТА)
# Использование: bash install-protection.sh ORIGIN_IP DOMAIN

set -e

echo "================================================"
echo " Aegis.net - Установка Protection Server (Защита)"
echo "================================================"
echo ""

# Проверка аргументов
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Ошибка: Укажите IP origin сервера и домен"
    echo "Использование: bash install-protection.sh ORIGIN_IP DOMAIN"
    echo "Пример: bash install-protection.sh 192.168.1.100 example.com"
    exit 1
fi

ORIGIN_IP="$1"
DOMAIN="$2"

# Проверка root
if [ "$EUID" -ne 0 ]; then 
    echo "Запустите с sudo или от root"
    exit 1
fi

echo "Origin сервер: $ORIGIN_IP"
echo "Домен: $DOMAIN"
echo ""
read -p "Продолжить? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo ""
echo "[1/10] Обновление системы..."
apt update && apt upgrade -y

echo ""
echo "[2/10] Установка зависимостей..."
apt install -y git curl wget build-essential software-properties-common nginx ufw

echo ""
echo "[3/10] Установка Python 3.11..."
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

echo ""
echo "[4/10] Установка Redis..."
apt install -y redis-server

# Настройка Redis
sed -i 's/^# maxmemory .*/maxmemory 2gb/' /etc/redis/redis.conf
sed -i 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

systemctl enable redis-server
systemctl start redis-server

echo ""
echo "[5/10] Создание пользователя aegis..."
if ! id "aegis" &>/dev/null; then
    useradd -m -s /bin/bash aegis
fi

echo ""
echo "[6/10] ВАЖНО: Загрузите файлы Aegis.net"
echo "Выполните на вашей локальной машине:"
echo ""
echo "  scp -r \"C:\\Users\\kirill shikhanov\\.gemini\\antigravity\\scratch\\Aegis.net\" root@$(hostname -I | awk '{print $1}'):/home/aegis/"
echo ""
read -p "Файлы загружены? Нажмите Enter когда готово..."

# Проверка что файлы загружены
if [ ! -d "/home/aegis/Aegis.net" ]; then
    echo "Ошибка: /home/aegis/Aegis.net не найден"
    echo "Загрузите файлы и запустите скрипт снова"
    exit 1
fi

chown -R aegis:aegis /home/aegis/Aegis.net

echo ""
echo "[7/10] Настройка Control Plane..."
su - aegis << 'EOSU'
cd /home/aegis/Aegis.net/control-plane
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
EOSU

# Создание .env
if [ ! -f "/home/aegis/Aegis.net/control-plane/.env" ]; then
    cp /home/aegis/Aegis.net/control-plane/.env.example /home/aegis/Aegis.net/control-plane/.env
    
    # Генерация секретов
    SECRET_KEY=$(python3.11 -c "import secrets; print(secrets.token_urlsafe(32))")
    JWT_SECRET=$(python3.11 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Обновление .env
    sed -i "s/change-me-in-production-min-32-chars/$SECRET_KEY/" /home/aegis/Aegis.net/control-plane/.env
    sed -i "s/CHANGE_THIS_TO_RANDOM_SECRET_MIN_32_CHARS/$JWT_SECRET/" /home/aegis/Aegis.net/control-plane/.env
    
    chown aegis:aegis /home/aegis/Aegis.net/control-plane/.env
fi

echo ""
echo "[8/10] Создание systemd service..."
cat > /etc/systemd/system/aegis-control-plane.service << 'EOF'
[Unit]
Description=Aegis.net Control Plane
After=network.target redis-server.service

[Service]
Type=simple
User=aegis
Group=aegis
WorkingDirectory=/home/aegis/Aegis.net/control-plane
Environment="PATH=/home/aegis/Aegis.net/control-plane/venv/bin"
ExecStart=/home/aegis/Aegis.net/control-plane/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable aegis-control-plane
systemctl start aegis-control-plane

echo ""
echo "[9/10] Настройка Nginx Reverse Proxy..."
cat > /etc/nginx/sites-available/aegis-proxy << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    location / {
        proxy_pass http://$ORIGIN_IP:80;
        
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

ln -sf /etc/nginx/sites-available/aegis-proxy /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable nginx
systemctl restart nginx

echo ""
echo "[10/10] Настройка Firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw default deny incoming
ufw default allow outgoing
ufw --force enable

echo ""
echo "================================================"
echo "  ✅ УСТАНОВКА ЗАВЕРШЕНА!"
echo "================================================"
echo ""
echo "Сервер защиты настроен:"
echo "  - Control Plane: http://$(hostname -I | awk '{print $1}'):8000"
echo "  - Nginx Proxy: http://$DOMAIN → $ORIGIN_IP"
echo "  - Redis: running"
echo ""
echo "Проверка:"
echo "  systemctl status aegis-control-plane"
echo "  curl http://localhost:8000/"
echo ""
echo "Следующие шаги:"
echo "  1. Настройте DNS: $DOMAIN → $(hostname -I | awk '{print $1}')"
echo "  2. Настройте CLI на локальной машине"
echo "  3. Добавьте SSH ключ в .env:"
echo "     nano /home/aegis/Aegis.net/control-plane/.env"
echo "  4. Установите SSL:"
echo "     apt install -y certbot python3-certbot-nginx"
echo "     certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo ""
