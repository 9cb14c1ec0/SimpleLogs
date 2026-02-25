# SimpleLogs

A self-hosted logging storage and search application with a simple API for log ingestion.

<img width="1674" height="964" alt="image" src="https://github.com/user-attachments/assets/bb234963-f4cc-42cc-a462-6603c338c1a3" />

## Features

- **Simple Ingestion API** - Send logs with 2 lines of code from any language
- **Full-text Search** - Search log messages with PostgreSQL full-text search
- **JSON Metadata** - Attach structured data to logs and filter by any field
- **Multi-team** - Isolate logs by team with multiple API keys per team
- **Retention Policies** - Auto-delete old logs per team
- **Modern Stack** - FastAPI + Vue 3 + Vuetify + PostgreSQL
- **Auto HTTPS** - Caddy handles SSL certificates automatically

## Quick Start

```bash
# Clone and configure
git clone <repo-url> simplelogs
cd simplelogs
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml

# Start services
docker-compose up -d

# Access the UI
open http://localhost
```

Default login: `admin@example.com` / `changeme`

## Configuration

Edit `.env` to configure:

```env
# Domain (use real domain for auto-HTTPS)
DOMAIN=localhost

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=simplelogs

# Security (change in production!)
SECRET_KEY=your-secure-random-string
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=changeme
```

## Sending Logs

Get your API key from the admin panel (Teams → Create Team or Manage Keys), then:

### curl

```bash
curl -X POST http://localhost/api/v1/ingest \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"level": "info", "message": "User logged in", "metadata": {"important_number": 123}}'
```

### Python

```python
import requests

requests.post("http://localhost/api/v1/ingest",
    headers={"X-API-Key": "YOUR_API_KEY"},
    json={
        "level": "error",
        "message": "Payment failed",
        "metadata": {"amount": 99.99},
        "user_id": "123"
    })
```

### JavaScript

```javascript
fetch("http://localhost/api/v1/ingest", {
    method: "POST",
    headers: {
        "X-API-Key": "YOUR_API_KEY",
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        level: "info",
        message: "Order created",
        metadata: { orderId: 456 },
        user_id: "1234"
    })
});
```

### Batch Ingestion

Send up to 1000 logs in one request:

```bash
curl -X POST http://localhost/api/v1/ingest/batch \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {"level": "info", "message": "Step 1 complete"},
      {"level": "info", "message": "Step 2 complete"},
      {"level": "error", "message": "Step 3 failed", "metadata": {"error": "timeout"}}
    ]
  }'
```

## Log Format

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `level` | string | No | `debug`, `info`, `warn`, `error`, `fatal` (default: `info`) |
| `message` | string | Yes | Log message text |
| `metadata` | object | No | JSON object with any additional data |
| `source` | string | No | Service/app name |
| `timestamp` | string | No | ISO 8601 timestamp (default: server time) |
| `user_id` | string | No | User ID so that you can filter by user if desired.

## API Key Management

Each team can have multiple API keys. Manage them from the admin panel:

- **Teams → Key icon** to open the key management dialog
- **Generate** a new key (auto-generated, shown once)
- **Provide manually** a custom key string
- **Revoke** individual keys without affecting others

When a team is created, a default key is generated automatically.

## Searching Logs

In the UI, you can search by:

- **Text** - Full-text search on message content
- **Level** - Filter by log level(s)
- **Source** - Filter by source/service name
- **Date Range** - Filter by time period
- **Metadata** - Filter by JSON fields (e.g., `user_id=123`)

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run with auto-reload
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
cd backend

# Initialize (first time)
aerich init -t app.db.TORTOISE_ORM
aerich init-db

# Create migration
aerich migrate --name add_new_field

# Apply migrations
aerich upgrade
```

## Production Deployment

1. Set a real domain in `.env`:
   ```env
   DOMAIN=logs.yourdomain.com
   ```

2. Update security settings:
   ```env
   SECRET_KEY=<generate-a-long-random-string>
   ADMIN_PASSWORD=<strong-password>
   POSTGRES_PASSWORD=<strong-password>
   ```

3. Deploy:
   ```bash
   docker-compose up -d
   ```

Caddy will automatically obtain and renew SSL certificates from Let's Encrypt.

## License

MIT
