# Aegis.net Control Plane

FastAPI-based control plane for managing Anti-DDoS protection.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn api.main:app --reload --port 8000
```

## API Endpoints

- `POST /api/v1/domains` — Register a domain
- `GET /api/v1/domains/{domain}` — Get domain config
- `PUT /api/v1/domains/{domain}/config` — Update protection config
- `POST /api/v1/domains/{domain}/attack-mode` — Activate attack mode
- `GET /api/v1/domains/{domain}/stats` — Get traffic statistics

## Environment Variables

```
DATABASE_URL=postgresql://user:pass@localhost/aegis
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
```
