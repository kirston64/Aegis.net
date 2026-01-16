# Getting Started with Aegis.net

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/kirston64/Aegis.net.git
cd Aegis.net
```

### 2. Start the Control Plane

```bash
cd control-plane

# Using Docker (recommended)
docker-compose up -d

# Or manually
pip install -r requirements.txt
uvicorn api.main:app --reload
```

API will be available at: `http://localhost:8000`

### 3. Start the Dashboard

```bash
```bash
cd dashboard
npm install
npm run dev
```

Dashboard will be available at: `http://localhost:5173`

---

## Add Your First Domain

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/domains \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "mysite.com",
    "origin_ip": "YOUR_SERVER_IP",
    "origin_port": 443
  }'
```

### Via Dashboard

1. Open `http://localhost:3000`
2. Click "Add Domain"
3. Enter domain and origin IP
4. Click "Create"

---

## Configure DNS

Point your domain to our edge nodes:

| Record | Type | Value |
|--------|------|-------|
| @ | A | 185.x.x.x (edge IP) |
| www | CNAME | edge.aegis.net |

---

## Protection Levels

| Level | When to Use |
|-------|-------------|
| 0 - Observe | Normal traffic, learning phase |
| 1 - Soft | Slight increase in traffic |
| 2 - Medium | Suspicious activity detected |
| 3 - Hard | Active DDoS attack |
| 4 - Lockdown | Emergency, critical attack |

---

## Game Server Setup

### Minecraft

```json
{
  "game_protocol": "minecraft",
  "game_port": 25565,
  "rate_limit_per_ip": 50
}
```

### GTA 5 RP (RAGE MP)

```json
{
  "game_protocol": "rage_mp",
  "game_port": 22005,
  "rate_limit_per_ip": 100
}
```

---

## Need Help?

- 📖 [API Documentation](./API.md)
- 💬 [Discord Community](https://discord.gg/aegis)
- 📧 support@aegis.net
