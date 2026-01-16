#!/bin/bash
# Aegis.net - Автоматическая установка СЕРВЕР 1 (ORIGIN/САЙТ)
# Использование: bash install-origin.sh ЗАЩИТА_СЕРВЕР_IP

set -e

echo "================================================"
echo "  Aegis.net - Установка Origin Server (Сайт)  "
echo "================================================"
echo ""

# Проверка аргументов
if [ -z "$1" ]; then
    echo "Ошибка: Укажите IP сервера защиты"
    echo "Использование: bash install-origin.sh ЗАЩИТА_IP"
    exit 1
fi

PROTECTION_IP="$1"

# Проверка root
if [ "$EUID" -ne 0 ]; then 
    echo "Запустите с sudo или от root"
    exit 1
fi

echo "Сервер защиты: $PROTECTION_IP"
echo ""
read -p "Продолжить? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo ""
echo "[1/6] Обновление системы..."
apt update && apt upgrade -y

echo ""
echo "[2/6] Установка Nginx..."
apt install -y nginx

echo ""
echo "[3/6] Создание директории для сайта..."
mkdir -p /var/www/mysite

echo ""
echo "[4/6] Создание тестового сайта..."
cat > /var/www/mysite/index.html << 'EOF'
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Protected by Aegis.net</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 { font-size: 3em; margin: 0; }
        p { font-size: 1.2em; }
        .shield { font-size: 5em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="shield">🛡️</div>
        <h1>Protected by Aegis.net</h1>
        <p>This site is protected from DDoS attacks</p>
        <p><small>Origin Server</small></p>
    </div>
</body>
</html>
EOF

echo ""
echo "[5/6] Настройка Nginx..."
cat > /etc/nginx/sites-available/mysite << EOF
server {
    listen 80;
    server_name _;
    
    root /var/www/mysite;
    index index.html index.php;
    
    location / {
        try_files \$uri \$uri/ =404;
    }
    
    access_log /var/log/nginx/mysite-access.log;
    error_log /var/log/nginx/mysite-error.log;
}
EOF

ln -sf /etc/nginx/sites-available/mysite /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable nginx
systemctl restart nginx

echo ""
echo "[6/6] Настройка Firewall..."
apt install -y ufw

# Разрешить SSH
ufw allow 22/tcp

# Разрешить HTTP/HTTPS ТОЛЬКО с сервера защиты
ufw allow from $PROTECTION_IP to any port 80
ufw allow from $PROTECTION_IP to any port 443

# Блокировать все остальное
ufw default deny incoming
ufw default allow outgoing

# Включить firewall
ufw --force enable

echo ""
echo "================================================"
echo "  ✅ УСТАНОВКА ЗАВЕРШЕНА!"
echo "================================================"
echo ""
echo "Сервер origin настроен:"
echo "  - Nginx установлен и запущен"
echo "  - Тестовый сайт: /var/www/mysite"
echo "  - Firewall: разрешен только $PROTECTION_IP"
echo ""
echo "Проверка:"
echo "  curl http://localhost"
echo ""
echo "Следующие шаги:"
echo "  1. Загрузите ваш сайт в /var/www/mysite"
echo "  2. Настройте Сервер 2 (защита)"
echo "  3. Настройте DNS на IP сервера защиты"
echo ""
