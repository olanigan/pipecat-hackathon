# Langfuse Local Setup

This directory contains Docker setup for running Langfuse locally for development and testing.

## Quick Start

1. **Start Langfuse:**
   ```bash
   cd app/otel
   docker-compose up -d
   ```

2. **Wait for services to be healthy:**
   ```bash
   docker-compose ps
   ```

3. **Access Langfuse UI:**
   - Open http://localhost:3000
   - Create your first user account

4. **Update Pipecat server configuration:**
   The `app/server/.env` should already be configured to use local Langfuse OTEL endpoint.

## Services

- **Langfuse Web UI**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **OTEL Endpoint**: http://localhost:3000/api/public/otel

## Configuration

Copy `.env` and update the secrets:
```bash
cp .env .env.local
# Edit .env.local with your preferred secrets
```

## Testing OTEL Connection

Use the test script to verify OTEL endpoint connectivity:
```bash
cd ../server
uv run python test_otel.py
```

## Stopping Services

```bash
cd app/otel
docker-compose down
```

## Data Persistence

PostgreSQL data is persisted in a Docker volume. To reset the database:
```bash
docker-compose down -v
```