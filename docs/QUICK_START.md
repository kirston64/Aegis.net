# Aegis.net - Quick Start для тестирования на 2 серверах Ubuntu

Упрощённая инструкция для быстрого развёртывания на 2 серверах.

## Что вам понадобится

- 2 Ubuntu сервера (20.04/22.04)
- Root/sudo доступ к обоим серверам
- Python 3.11+ на локальной машине (для CLI)

## Быстрая установка (30 минут)

### Сервер 1 (Control Plane) - 15 минут

```bash
# 1. Подключитесь к серверу
ssh root@YOUR_CONTROL_PLANE_IP

# 2. Скачайте и запустите установочный скрипт
cd /root
wget https://raw.githubusercontent.com/your-repo/Aegis.net/main/scripts/install-control-plane.sh
chmod +x install-control-plane.sh
./install-control-plane.sh

# 3. Загрузите файлы проекта
# На вашей локальной машине:
scp -r "C:\Users\kirill shikhanov\.gemini\antigravity\scratch\Aegis.net" root@YOUR_CONTROL_PLANE_IP:/home/aegis/

# 4. Запустите setup (на сервере)
sudo -u aegis /home/aegis/Aegis.net/scripts/setup-control-plane.sh

# 5. Настройте .env
nano /home/aegis/Aegis.net/control-plane/.env
# Установите YOUR_LOCAL_IP в WHITELISTED_IPS
# Остальное можно оставить по умолчанию для теста

# 6. Установите и запустите systemd service
cp /home/aegis/Aegis.net/scripts/aegis-control-plane.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable aegis-control-plane
systemctl start aegis-control-plane

# 7. Проверьте статус
systemctl status aegis-control-plane
curl http://localhost:8000/
# Должно вернуть JSON
```

### Сервер 2 (Origin) - 5 минут

```bash
# 1. Подключитесь к серверу
ssh root@YOUR_ORIGIN_IP

# 2. Установите Nginx
apt update
apt install -y nginx ufw

# 3. Создайте тестовый сайт
mkdir -p /var/www/testsite
cat > /var/www/testsite/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head><title>Protected Site</title></head>
<body>
    <h1>🛡️ This site is protected by Aegis.net</h1>
    <p>Server: Origin</p>
</body>
</html>
EOF

# 4. Настройте Nginx
cat > /etc/nginx/sites-available/testsite << EOF
server {
    listen 80;
    server_name _;
    root /var/www/testsite;
    index index.html;
    
    # Разрешить только с Control Plane
    allow YOUR_CONTROL_PLANE_IP;
    deny all;
    
    location / {
        try_files \$uri \$uri/ =404;
    }
}
EOF

ln -s /etc/nginx/sites-available/testsite /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# 5. Настройте firewall
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow from YOUR_CONTROL_PLANE_IP to any port 80

# 6. Проверьте что origin доступен только с Control Plane
# На Control Plane сервере:
curl http://YOUR_ORIGIN_IP/
# Должно показать HTML
```

### Локальная машина (CLI) - 10 минут

```powershell
# 1. Перейдите в директорию CLI
cd "C:\Users\kirill shikhanov\.gemini\antigravity\scratch\Aegis.net\cli"

# 2. Установите зависимости
python -m pip install -r requirements.txt

# 3. Запустите setup 2FA
python setup_2fa.py
# Сканируйте QR код в Google Authenticator
# Скопируйте ваш SSH публичный ключ (будет показан)

# 4. Добавьте SSH ключ на Control Plane сервер
# На Control Plane сервере:
nano /home/aegis/Aegis.net/control-plane/.env
# Добавьте ваш SSH ключ в AUTHORIZED_CLI_KEYS:
# AUTHORIZED_CLI_KEYS='["ssh-ed25519 AAAAC3... ваш_ключ"]'

# Перезапустите сервис:
systemctl restart aegis-control-plane

# 5. Подключитесь к Control Plane
python aegis_cli.py connect YOUR_CONTROL_PLANE_IP
# Введите TOTP код

# 6. Добавьте origin домен
python aegis_cli.py domain add test.local --origin http://YOUR_ORIGIN_IP --protection 2

# 7. Настройте rate limiting
python aegis_cli.py ratelimit set test.local --rps 100 --rpm 5000 --per-ip-rps 5 --per-ip-rpm 200

# 8. Проверьте конфигурацию
python aegis_cli.py domain list
python aegis_cli.py stats test.local
```

## Тестирование

### 1. Проверка что Origin закрыт от внешнего мира

```bash
# С вашей локальной машины (не должно работать):
curl http://YOUR_ORIGIN_IP/
# Ожидается: Connection refused или 403 Forbidden
```

### 2. Проверка что Control Plane работает

```bash
curl http://YOUR_CONTROL_PLANE_IP:8000/
# Ожидается: JSON ответ с информацией об API
```

### 3. Проверка CLI

```powershell
python aegis_cli.py domain list
python aegis_cli.py audit
```

## Проблемы и решения

### CLI не может подключиться

**Проблема:** `IP address not whitelisted` или `SSH key not authorized`

**Решение:**
```bash
# На Control Plane:
nano /home/aegis/Aegis.net/control-plane/.env
# Проверьте WHITELISTED_IPS и AUTHORIZED_CLI_KEYS
systemctl restart aegis-control-plane
```

### Origin недоступен с Control Plane

**Проблема:** `curl http://ORIGIN_IP` возвращает ошибку

**Решение:**
```bash
# На Origin сервере:
# Проверьте firewall
ufw status
# Убедитесь что Control Plane IP разрешён
ufw allow from YOUR_CONTROL_PLANE_IP to any port 80

# Проверьте nginx
nginx -t
systemctl status nginx
```

### Control Plane не запускается

**Решение:**
```bash
# Проверьте логи
journalctl -u aegis-control-plane -n 50

# Проверьте Redis
systemctl status redis-server
redis-cli ping

# Проверьте .env файл
cat /home/aegis/Aegis.net/control-plane/.env
```

## Следующие шаги

После успешного тестирования:

1. ✅ Настроить реальные домены (DNS)
2. ✅ Установить SSL сертификаты
3. ✅ Настроить мониторинг
4. ✅ Настроить автоматический backup Redis
5. ✅ Развернуть Rust proxy (для production)

## Полная документация

См. [DEPLOYMENT_UBUNTU.md](DEPLOYMENT_UBUNTU.md) для детальных инструкций.

## Архитектура

```
Пользователи → Control Plane (фильтрация) → Origin (ваш сайт)
                YOUR_CONTROL_PLANE_IP          YOUR_ORIGIN_IP
                                               (закрыт от мира)
```
