# Aegis.net API Documentation

## Base URL

```
https://api.aegis.net/api/v1
```

## Authentication

All API requests require an API key in the header:

```
Authorization: Bearer YOUR_API_KEY
```

---

## Domains

### List Domains

```http
GET /domains?page=1&per_page=20
```

**Response:**

```json
{
  "domains": [
    {
      "id": "uuid",
      "domain": "example.com",
      "origin_ip": "192.168.1.1",
      "origin_port": 443,
      "status": "active",
      "config": {
        "protection_level": 1,
        "rate_limit_per_ip": 100
      }
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20
}
```

### Create Domain

```http
POST /domains
Content-Type: application/json

{
  "domain": "example.com",
  "origin_ip": "192.168.1.1",
  "origin_port": 443
}
```

### Update Domain Config

```http
PUT /domains/{domain}/config
Content-Type: application/json

{
  "protection_level": 2,
  "rate_limit_per_ip": 50,
  "whitelist_ips": ["10.0.0.1"],
  "game_protocol": "minecraft"
}
```

### Delete Domain

```http
DELETE /domains/{domain}
```

---

## Attack Mode

### Activate Attack Mode

```http
POST /attack-mode/{domain}
Content-Type: application/json

{
  "level": 3,
  "duration_minutes": 60,
  "reason": "Suspected DDoS attack"
}
```

**Levels:**

| Level | Name | Description |
|-------|------|-------------|
| 0 | Observe | Monitoring only |
| 1 | Soft | Invisible PoW challenge |
| 2 | Medium | CAPTCHA for suspicious |
| 3 | Hard | JS Challenge for all |
| 4 | Lockdown | Whitelist only |

### Get Attack Mode Status

```http
GET /attack-mode/{domain}
```

### Deactivate Attack Mode

```http
DELETE /attack-mode/{domain}
```

### Quick Increase/Decrease

```http
POST /attack-mode/{domain}/increase
POST /attack-mode/{domain}/decrease
```

---

## Statistics

### Get Domain Stats

```http
GET /domains/{domain}/stats
```

**Response:**

```json
{
  "domain": "example.com",
  "timestamp": "2026-01-14T10:45:00Z",
  "requests_per_second": 1250.5,
  "legitimate_requests": 12450,
  "challenged_requests": 2100,
  "blocked_requests": 1450,
  "unique_ips": 3420,
  "top_countries": {
    "RU": 4500,
    "DE": 2100,
    "US": 1800
  },
  "threat_level": 0.35
}
```

---

## Health Check

```http
GET /health
```

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Error Responses

```json
{
  "success": false,
  "error": "Domain not found",
  "code": "NOT_FOUND",
  "details": null
}
```

| Code | HTTP Status | Description |
|------|-------------|-------------|
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Resource already exists |
| RATE_LIMITED | 429 | Too many requests |
| UNAUTHORIZED | 401 | Invalid API key |
