# DNS и Reverse Proxy - Настройка публичного доступа

Как настроить публичный доступ к вашему сайту через защиту Aegis.net.

## Схема работы

```
Пользователи вводят: https://example.com
         ↓
    DNS A-запись → IP Сервера 2 (защита)
         ↓
Сервер 2 (Aegis Protection)
    - Фильтрация DDoS
    - Rate limiting
    - Блокировка атак
         ↓ (Nginx reverse proxy)
Сервер 1 (Ваш сайт - Origin)
    - Закрыт firewall (только с Сервера 2)
    - Ваше приложение/сайт
```

---

## Шаг 1: Настройка DNS

В панели управления вашего доменного регистратора (Cloudflare, GoDaddy, Namecheap и т.д.):

### A-запись для основного домена

```
Type: A
Name: @ (или example.com)
Value: IP_СЕРВЕРА_2  (IP защиты Aegis.net)
TTL: 300 (5 минут - для тестирования)
```

### A-запись для www

```
Type: A
Name: www
Value: IP_СЕРВЕРА_2
TTL: 300
```

**Важно:** DNS указывает на **IP Сервера 2** (защита), НЕ на IP вашего сайта!

---

## Шаг 2: Nginx Reverse Proxy на Сервере 2 (Защита)

### Конфигурация для проксирования на origin

На **Сервере 2** (защита) создайте конфигурацию Nginx:

```bash
sudo nano /etc/nginx/sites-available/example.com
```

**Содержимое файла:**

```nginx
# Upstream - ваш origin сервер
upstream origin_backend {
    server ORIGIN_IP:80;  # IP Сервера 1
    keepalive 32;
}

# HTTP server (для редиректа на HTTPS)
server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;

    # Для Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Редирект на HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server (основной)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com www.example.com;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Логи
    access_log /var/log/nginx/example.com-access.log;
    error_log /var/log/nginx/example.com-error.log;

    # Заголовки безопасности
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Проксирование на origin
    location / {
        proxy_pass http://origin_backend;
        
        # Заголовки для передачи информации о клиенте
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (если нужно)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Буферизация
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
}
```

### Активация конфигурации

```bash
# Создать symlink
sudo ln -s /etc/nginx/sites-available/example.com /etc/nginx/sites-enabled/

# Проверить конфигурацию
sudo nginx -t

# Перезагрузить Nginx
sudo systemctl reload nginx
```

---

## Шаг 3: SSL сертификат на Сервере 2

### Установка Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Получение сертификата

```bash
# Создать директорию для ACME challenge
sudo mkdir -p /var/www/certbot

# Получить сертификат
sudo certbot certonly --webroot \
    -w /var/www/certbot \
    -d example.com \
    -d www.example.com \
    --email your@email.com \
    --agree-tos \
    --no-eff-email

# Обновить Nginx конфигурацию с путями к сертификатам
sudo nano /etc/nginx/sites-available/example.com
# Раскомментировать SSL строки

# Перезагрузить Nginx
sudo nginx -t
sudo systemctl reload nginx
```

### Автообновление сертификатов

```bash
# Проверить автообновление
sudo certbot renew --dry-run

# Включить systemd timer
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Шаг 4: Настройка Origin (Сервер 1)

На **Сервере 1** (ваш сайт) нужно принимать только трафик с Сервера 2.

### Firewall правила

```bash
# Разрешить SSH
sudo ufw allow 22/tcp

# Разрешить HTTP/HTTPS ТОЛЬКО с Сервера 2
sudo ufw allow from IP_СЕРВЕРА_2 to any port 80
sudo ufw allow from IP_СЕРВЕРА_2 to any port 443

# Блокировать остальное
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Включить firewall
sudo ufw enable
```

### Nginx конфигурация на Origin

```bash
sudo nano /etc/nginx/sites-available/yoursite
```

**Содержимое:**

```nginx
server {
    listen 80;
    server_name _;  # Принимает любой Host header
    
    root /var/www/yoursite;
    index index.html index.php;

    # Проверка что запрос пришёл с защиты
    # Можно проверять X-Forwarded-For или специальный заголовок
    
    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    # PHP (если используете)
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/yoursite /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Шаг 5: Интеграция с Aegis CLI

После настройки прокси, добавьте домен в защиту:

```powershell
# Подключиться к Control Plane
python aegis_cli.py connect IP_СЕРВЕРА_2

# Добавить домен
python aegis_cli.py domain add example.com --origin http://IP_СЕРВЕРА_1 --protection 3

# Настроить rate limiting
python aegis_cli.py ratelimit set example.com \
    --rps 1000 \
    --rpm 50000 \
    --per-ip-rps 10 \
    --per-ip-rpm 500 \
    --burst 20
```

---

## Проверка работы

### 1. Проверка DNS

```bash
# Проверить что DNS указывает на Сервер 2
nslookup example.com
dig example.com

# Должен вернуть IP_СЕРВЕРА_2
```

### 2. Проверка доступности

```bash
# С любой машины
curl -I https://example.com

# Должен вернуть 200 OK и ваш сайт
```

### 3. Проверка что Origin закрыт

```bash
# Попробовать зайти напрямую на Origin (должно быть заблокировано)
curl http://IP_СЕРВЕРА_1

# Ожидается: timeout или connection refused
```

### 4. Проверка заголовков

```bash
# Проверить что X-Real-IP передаётся корректно
curl -I -H "Host: example.com" https://example.com

# На origin проверить логи Nginx:
tail -f /var/log/nginx/yoursite-access.log
# Должны видеть реальные IP пользователей в X-Forwarded-For
```

---

## Мониторинг

### Логи на Сервере 2 (Защита)

```bash
# Nginx access log
tail -f /var/log/nginx/example.com-access.log

# Aegis Control Plane логи
journalctl -u aegis-control-plane -f

# Redis stats
redis-cli
> INFO MEMORY
> DBSIZE
```

### Метрики через CLI

```powershell
python aegis_cli.py stats example.com
python aegis_cli.py audit
```

---

## Оптимизация производительности

### Кеширование статики на Сервере 2

Добавить в Nginx конфигурацию на Сервере 2:

```nginx
# Кеш для статических файлов
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=static_cache:10m max_size=1g inactive=60m;

server {
    # ... остальная конфигурация ...
    
    # Кеширование статики
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf)$ {
        proxy_pass http://origin_backend;
        proxy_cache static_cache;
        proxy_cache_valid 200 60m;
        proxy_cache_valid 404 1m;
        add_header X-Cache-Status $upstream_cache_status;
        
        expires 1h;
    }
}
```

### Compression

```nginx
# В http {} блок /etc/nginx/nginx.conf
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;
```

---

## Failover и резервирование

### Несколько origin серверов

```nginx
upstream origin_backend {
    least_conn;  # Балансировка по наименьшей нагрузке
    
    server ORIGIN_IP_1:80 weight=1 max_fails=3 fail_timeout=30s;
    server ORIGIN_IP_2:80 weight=1 max_fails=3 fail_timeout=30s backup;
    
    keepalive 32;
}
```

---

## Полный чеклист

- [ ] DNS A-запись указывает на IP Сервера 2
- [ ] SSL сертификат установлен на Сервере 2
- [ ] Nginx reverse proxy настроен на Сервере 2
- [ ] Firewall на Сервере 1 разрешает только Сервер 2
- [ ] Origin доступен с Сервера 2, но не из интернета
- [ ] Домен добавлен в Aegis CLI
- [ ] Rate limiting настроен
- [ ] Сайт доступен по публичному домену
- [ ] Логи показывают реальные IP пользователей
- [ ] SSL работает (HTTPS)

---

## Troubleshooting

### 502 Bad Gateway

**Причина:** Origin недоступен с Сервера 2

**Решение:**
```bash
# На Сервере 2 проверить доступность origin
curl -I http://ORIGIN_IP

# Проверить firewall на Origin
# На Сервере 1:
sudo ufw status
```

### SSL сертификат не работает

**Решение:**
```bash
# Проверить пути к сертификатам
sudo ls -la /etc/letsencrypt/live/example.com/

# Проверить права
sudo chmod 644 /etc/letsencrypt/live/example.com/fullchain.pem
```

### Реальные IP не передаются

**Решение:**
```bash
# Убедитесь что на origin логируется X-Forwarded-For
# В Nginx access_log формат:
log_format main '$remote_addr - $http_x_forwarded_for [$time_local] "$request"';
```
