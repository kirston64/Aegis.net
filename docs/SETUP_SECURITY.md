# Настройка безопасности Aegis.net

## Конфигурация Control Plane

### 1. Добавьте SSH публичные ключи

Откройте `.env` файл в директории `control-plane/` и добавьте:

```bash
AUTHORIZED_CLI_KEYS='["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxxxxxxxxxxxxxxxxxxxx admin@aegis"]'
```

Замените на ваши реальные публичные ключи. Формат: JSON массив строк.

### 2. Настройте IP whitelist

```bash
WHITELISTED_IPS='["127.0.0.1", "::1", "YOUR_IP_HERE"]'
```

**Важно**: Добавьте IP адреса, с которых будет производиться управление через CLI.

### 3. Задайте JWT секрет

```bash
JWT_SECRET="your-random-secret-here-min-32-characters"
```

Сгенерируйте случайный секрет:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Настройте Redis

```bash
REDIS_URL="redis://localhost:6379/0"
```

Убедитесь что Redis запущен:
```bash
redis-cli ping
# Должно вернуть: PONG
```

### 5. Опционально: Настройте срок хранения логов

```bash
AUDIT_LOG_RETENTION_DAYS=90
CLI_SESSION_TIMEOUT=1800  # 30 минут в секундах
```

## Регистрация пользователя CLI

### 1. Пользователь запускает setup

```bash
cd cli
python setup_2fa.py
```

### 2. Пользователь отправляет вам публичный ключ

Файл: `~/.ssh/aegis_cli.pub`

### 3. Добавьте ключ в конфигурацию

Добавьте публичный ключ в `AUTHORIZED_CLI_KEYS` переменную в `.env` файле.

Перезапустите Control Plane:
```bash
cd control-plane
uvicorn api.main:app --reload
```

### 4. Добавьте IP пользователя в whitelist

Узнайте IP: `curl ifconfig.me`

Добавьте в `WHITELISTED_IPS`.

## Управление TOTP секретами

Для каждого пользователя нужно зарегистрировать TOTP секрет.

Временное решение (продакшн - использовать БД):

```python
# В Python консоли на Control Plane
from api.services.auth import get_auth_service
auth = get_auth_service()
auth.register_totp_secret("user_id", "their_totp_secret_from_setup")
```

## Мониторинг безопасности

### Просмотр логов аутентификации

```bash
cd control-plane
tail -f api/logs/aegis.log | grep auth
```

### Просмотр audit лога через CLI

```bash
python cli/aegis_cli.py connect localhost
python cli/aegis_cli.py audit
```

### Redis мониторинг

```bash
redis-cli info memory
redis-cli keys "audit:*" | wc -l  # Количество audit записей
redis-cli keys "ratelimit:*" | wc -l  # Количество rate limit конфигураций
```

## Безопасность в продакшн

### Обязательно перед развёртыванием:

1. ☑ Сгенерируйте новый `JWT_SECRET` (минимум 32 символа)
2. ☑ Используйте SSL/TLS для Control Plane (загрузите сертификаты)
3. ☑ Ограничьте `WHITELISTED_IPS` только доверенными адресами
4. ☑ Настройте firewall для закрытия порта 8000 извне (только VPN/SSH tunnel)
5. ☑ Храните TOTP секреты в базе данных, не в памяти
6. ☑ Включите rate limiting для API endpoints
7. ☑ Настройте автоматический backup Redis данных
8. ☑ Мониторинг: добавьте алерты на неудачные попытки аутентификации

### Рекомендуемая архитектура для продакшн:

```
User → VPN/SSH Tunnel → Control Plane (localhost:8000)
```

Не открывайте Control Plane напрямую в интернет. Используйте:
- VPN (WireGuard, OpenVPN)
- SSH туннель: `ssh -L 8000:localhost:8000 server`

## Восстановление доступа

### Пользователь потерял TOTP

1. Временно удалите пользователя из `AUTHORIZED_CLI_KEYS`
2. Попросите пере-запустить setup: `python cli/setup_2fa.py`
3. Добавьте новый ключ в конфигурацию
4. Зарегистрируйте новый TOTP секрет

### Утечка JWT_SECRET

1. Сгенерируйте новый секрет: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Обновите `JWT_SECRET` в `.env`
3. Перезапустите Control Plane
4. Все существующие сессии станут недействительны
5. Пользователи должны переподключиться

## Проверка конфигурации

```bash
# В директории control-plane
python -c "from api.config import settings; print('Keys:', len(settings.AUTHORIZED_CLI_KEYS)); print('IPs:', len(settings.WHITELISTED_IPS)); print('Secret length:', len(settings.JWT_SECRET))"
```

Должно показать:
- Количество авторизованных ключей
- Количество whitelisted IP
- Длина JWT секрета (≥ 32)
