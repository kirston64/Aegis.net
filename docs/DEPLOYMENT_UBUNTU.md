# Aegis.net - Deployment на Ubuntu серверах

Пошаговая инструкция для развертывания Aegis.net на 2 серверах Ubuntu.

## Архитектура

```
┌─────────────────────────────────┐
│  Сервер 1 (Control Plane)       │
│  - Control Plane API             │
│  - Redis                         │
│  - CLI management                │
│  - Edge Proxy (Rust/OpenResty)   │
│  IP: CONTROL_PLANE_IP            │
└─────────────────────────────────┘
          │
          │ Proxy traffic
          ↓
┌─────────────────────────────────┐
│  Сервер 2 (Origin)               │
│  - Ваш защищаемый сайт           │
│  - Nginx/Apache                  │
│  IP: ORIGIN_IP (закрыт от мира)  │
└─────────────────────────────────┘

Пользователи → Сервер 1 (фильтрация) → Сервер 2 (origin)
```

---

## Требования

### Оба сервера:
- Ubuntu 20.04/22.04 LTS
- Минимум 2GB RAM (рекомендуется 4GB)
- 20GB disk space
- Root или sudo доступ
- Открытые порты: 80, 443 (Сервер 1), 22 (оба)

### Локальная машина (для CLI):
- Python 3.11+
- SSH доступ к Серверу 1

---

## Сервер 1: Control Plane + Edge

### Шаг 1: Подключение и обновление системы

```bash
ssh root@CONTROL_PLANE_IP

# Обновление системы
apt update && apt upgrade -y

# Установка базовых утилит
apt install -y git curl wget build-essential software-properties-common
```

### Шаг 2: Установка Python 3.11

```bash
# Добавить PPA для Python 3.11
add-apt-repository ppa:deadsnakes/ppa -y
apt update

# Установка Python 3.11 и pip
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Сделать Python 3.11 по умолчанию (опционально)
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### Шаг 3: Установка Redis

```bash
# Установка Redis
apt install -y redis-server

# Настройка Redis
nano /etc/redis/redis.conf
# Измените:
# bind 127.0.0.1 ::1
# maxmemory 2gb
# maxmemory-policy allkeys-lru

# Запуск и автозагрузка Redis
systemctl enable redis-server
systemctl start redis-server

# Проверка
redis-cli ping
# Должно вернуть: PONG
```

### Шаг 4: Установка PostgreSQL (опционально, для будущего использования)

```bash
apt install -y postgresql postgresql-contrib

# Создание базы данных
sudo -u postgres psql
CREATE DATABASE aegis;
CREATE USER aegis WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE aegis TO aegis;
\q
```

### Шаг 5: Клонирование репозитория

```bash
# Создать пользователя для приложения
useradd -m -s /bin/bash aegis
su - aegis

# Клонировать репозиторий (или загрузить файлы)
cd /home/aegis
git clone https://github.com/your-repo/Aegis.net.git
# Или скопировать файлы с вашей машины:
# На локальной машине:
# scp -r C:\Users\kirill shikhanov\.gemis\antigravity\scratch\Aegis.net aegis@CONTROL_PLANE_IP:/home/aegis/

cd Aegis.net
```

### Шаг 6: Настройка Control Plane

```bash
cd /home/aegis/Aegis.net/control-plane

# Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# Создание .env файла
cp .env.example .env
nano .env
```

**Настройте `.env` файл:**

```bash
# Сгенерируйте JWT секрет
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# В .env установите:
APP_NAME="Aegis.net Control Plane"
DEBUG=false
SECRET_KEY="your-generated-secret-here"
JWT_SECRET="your-generated-jwt-secret-here"

DATABASE_URL="postgresql+asyncpg://aegis:your_db_password@localhost:5432/aegis"
REDIS_URL="redis://localhost:6379/0"

CORS_ORIGINS='["http://localhost:3000", "http://YOUR_DOMAIN"]'

# CLI Security - оставьте пустым, заполните после setup CLI
AUTHORIZED_CLI_KEYS='[]'
WHITELISTED_IPS='["127.0.0.1", "YOUR_LOCAL_IP"]'

CLI_SESSION_TIMEOUT=1800
AUDIT_LOG_RETENTION_DAYS=90
```

### Шаг 7: Создание systemd service

```bash
# Выйти из пользователя aegis
exit

# Создать systemd service
nano /etc/systemd/system/aegis-control-plane.service
```

**Содержимое файла:**

```ini
[Unit]
Description=Aegis.net Control Plane
After=network.target redis-server.service postgresql.service

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
```

```bash
# Включить и запустить сервис
systemctl daemon-reload
systemctl enable aegis-control-plane
systemctl start aegis-control-plane

# Проверка статуса
systemctl status aegis-control-plane

# Проверка логов
journalctl -u aegis-control-plane -f
```

### Шаг 8: Настройка Nginx (reverse proxy)

```bash
apt install -y nginx

# Создать конфигурацию
nano /etc/nginx/sites-available/aegis
```

**Содержимое:**

```nginx
server {
    listen 80;
    server_name YOUR_CONTROL_PLANE_DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Включить сайт
ln -s /etc/nginx/sites-available/aegis /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Шаг 9: SSL/TLS с Let's Encrypt

```bash
apt install -y certbot python3-certbot-nginx

# Получить сертификат
certbot --nginx -d YOUR_CONTROL_PLANE_DOMAIN

# Автообновление сертификата
systemctl enable certbot.timer
```

### Шаг 10: Настройка Firewall

```bash
# UFW firewall
apt install -y ufw

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow from ORIGIN_IP to any port 8000  # Control Plane API (только для origin)

ufw enable
ufw status
```

---

## Сервер 2: Origin (Защищаемый сайт)

### Шаг 1: Подключение и обновление

```bash
ssh root@ORIGIN_IP

apt update && apt upgrade -y
apt install -y nginx
```

### Шаг 2: Настройка тестового сайта

```bash
# Создать простой тестовый сайт
mkdir -p /var/www/testsite
nano /var/www/testsite/index.html
```

**Содержимое index.html:**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Protected Test Site</title>
</head>
<body>
    <h1>This site is protected by Aegis.net</h1>
    <p>If you can see this, the protection is working!</p>
    <p>Server: Origin</p>
</body>
</html>
```

### Шаг 3: Настройка Nginx

```bash
nano /etc/nginx/sites-available/testsite
```

**Содержимое:**

```nginx
server {
    listen 80;
    server_name YOUR_ORIGIN_DOMAIN;

    root /var/www/testsite;
    index index.html;

    # Разрешить доступ ТОЛЬКО с Control Plane сервера
    allow CONTROL_PLANE_IP;
    deny all;

    location / {
        try_files $uri $uri/ =404;
    }

    # Логирование для отладки
    access_log /var/log/nginx/testsite-access.log;
    error_log /var/log/nginx/testsite-error.log;
}
```

```bash
ln -s /etc/nginx/sites-available/testsite /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Шаг 4: Firewall

```bash
apt install -y ufw

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp  # SSH
ufw allow from CONTROL_PLANE_IP to any port 80    # HTTP только с Control Plane
ufw allow from CONTROL_PLANE_IP to any port 443   # HTTPS только с Control Plane

ufw enable
```

---

## Настройка CLI на локальной машине (Windows)

### Шаг 1: Setup 2FA

```powershell
cd C:\Users\kirill shikhanov\.gemini\antigravity\scratch\Aegis.net\cli

# Установить зависимости
python -m pip install -r requirements.txt

# Запустить setup
python setup_2fa.py
```

Сохраните:
- QR код в Google Authenticator
- Публичный SSH ключ (будет показан в консоли)

### Шаг 2: Добавить SSH ключ на сервер

Скопируйте публичный ключ и добавьте в `.env` на Control Plane сервере:

```bash
# На Control Plane сервере
nano /home/aegis/Aegis.net/control-plane/.env

# Добавьте ваш SSH ключ в AUTHORIZED_CLI_KEYS:
AUTHORIZED_CLI_KEYS='["ssh-ed25519 AAAAC3NzaC... ваш_ключ_здесь"]'

# Также добавьте ваш IP
WHITELISTED_IPS='["127.0.0.1", "YOUR_LOCAL_IP"]'

# Перезапустить Control Plane
systemctl restart aegis-control-plane
```

### Шаг 3: Подключение CLI

```powershell
cd C:\Users\kirill shikhanov\.gemini\antigravity\scratch\Aegis.net\cli

# Подключение (используйте domain или IP Control Plane)
python aegis_cli.py connect YOUR_CONTROL_PLANE_DOMAIN

# Введите TOTP код из Google Authenticator
```

### Шаг 4: Добавить домен в защиту

```powershell
# Добавить ваш защищаемый домен
python aegis_cli.py domain add YOUR_ORIGIN_DOMAIN --origin http://ORIGIN_IP --protection 3

# Настроить rate limiting
python aegis_cli.py ratelimit set YOUR_ORIGIN_DOMAIN --rps 1000 --rpm 50000 --per-ip-rps 10 --per-ip-rpm 500 --burst 20

# Проверить статус
python aegis_cli.py domain list
```

---

## Проверка работы

### 1. Проверка Control Plane API

```bash
curl http://CONTROL_PLANE_IP:8000/
# Должно вернуть JSON с информацией об API
```

### 2. Проверка Origin (должен быть недоступен извне)

```bash
# С локальной машины (должно быть заблокировано)
curl http://ORIGIN_IP/
# 403 Forbidden или connection refused

# С Control Plane сервера (должно работать)
ssh root@CONTROL_PLANE_IP
curl http://ORIGIN_IP/
# Должно вернуть HTML страницу
```

### 3. Проверка защиты через Control Plane

```bash
# Запрос через публичный домен (должен проходить через фильтрацию)
curl http://YOUR_CONTROL_PLANE_DOMAIN/
```

---

## Мониторинг и логи

### Control Plane логи

```bash
# Системные логи
journalctl -u aegis-control-plane -f

# Nginx логи
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Redis логи
tail -f /var/log/redis/redis-server.log
```

### Origin логи

```bash
tail -f /var/log/nginx/testsite-access.log
tail -f /var/log/nginx/testsite-error.log
```

### Мониторинг Redis памяти

```bash
redis-cli info memory
redis-cli dbsize
```

---

## Troubleshooting

### Control Plane не запускается

```bash
# Проверить логи
journalctl -u aegis-control-plane -n 50

# Проверить зависимости
su - aegis
cd /home/aegis/Aegis.net/control-plane
source venv/bin/activate
python -c "from api.main import app; print('OK')"
```

### CLI не может подключиться

1. Проверьте firewall: `ufw status`
2. Проверьте что ваш IP в WHITELISTED_IPS
3. Проверьте что SSH ключ в AUTHORIZED_CLI_KEYS
4. Проверьте TOTP код (время должно быть синхронизировано)

### Origin недоступен с Control Plane

1. Проверьте firewall на origin: `ufw status`
2. Проверьте nginx конфигурацию: `nginx -t`
3. Проверьте что Control Plane IP в `allow` директиве

---

## Следующие шаги

После базовой установки:

1. ✅ Настроить DNS для ваших доменов
2. ✅ Установить SSL сертификаты на оба сервера
3. ✅ Настроить автоматический backup Redis
4. ✅ Настроить мониторинг (Prometheus + Grafana)
5. ✅ Развернуть Rust proxy для L7 фильтрации
6. ✅ Настроить eBPF/XDP для L3/L4 защиты

---

## Быстрая установка (скрипт)

Для автоматизации создан скрипт установки:

```bash
# Будет создан в следующем шаге
curl -sSL https://raw.githubusercontent.com/your-repo/Aegis.net/main/scripts/install.sh | bash
```

---

## Поддержка

При возникновении проблем:
1. Проверьте логи выше
2. Убедитесь что все порты открыты
3. Проверьте .env конфигурацию
4. Проверьте systemd статусы: `systemctl status aegis-control-plane`
