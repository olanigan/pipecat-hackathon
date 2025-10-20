# Langfuse Local Setup with Docker Compose

## Overview

Setting up Langfuse locally requires orchestrating 6 interdependent services using Docker Compose. This guide covers the complete infrastructure setup, configuration, and verification process.

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Langfuse Local Stack                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ PostgreSQL  │ │ ClickHouse  │ │    Redis    │            │
│  │   (Data)    │ │  (Analytics)│ │  (Cache)    │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │    MinIO    │ │ Langfuse    │ │ Langfuse    │            │
│  │  (Storage)  │ │    Web      │ │   Worker    │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ available RAM
- 10GB+ available disk space

## Docker Compose Configuration

### Core Services

```yaml
services:
  postgres:
    image: docker.io/postgres:17
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    ports:
      - 127.0.0.1:5432:5432
    volumes:
      - langfuse_postgres_data:/var/lib/postgresql/data

  clickhouse:
    image: docker.io/clickhouse/clickhouse-server
    environment:
      CLICKHOUSE_DB: default
      CLICKHOUSE_USER: clickhouse
      CLICKHOUSE_PASSWORD: clickhouse
    ports:
      - 127.0.0.1:8123:8123
      - 127.0.0.1:9000:9000
    volumes:
      - langfuse_clickhouse_data:/var/lib/clickhouse
      - langfuse_clickhouse_logs:/var/log/clickhouse-server

  redis:
    image: docker.io/redis:7
    command: --requirepass myredissecret
    ports:
      - 127.0.0.1:6379:6379

  minio:
    image: docker.io/minio/minio
    entrypoint: sh
    command: -c 'mkdir -p /data/langfuse && minio server --address ":9000" --console-address ":9001" /data'
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: miniosecret
    ports:
      - 9090:9000
      - 127.0.0.1:9091:9001
    volumes:
      - langfuse_minio_data:/data
```

### Langfuse Services

```yaml
  langfuse-web:
    image: docker.io/langfuse/langfuse:3
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy
      redis:
        condition: service_healthy
      clickhouse:
        condition: service_healthy
    ports:
      - 3000:3000
    environment:
      # Database
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/postgres
      # Analytics
      CLICKHOUSE_URL: http://clickhouse:8123
      CLICKHOUSE_USER: clickhouse
      CLICKHOUSE_PASSWORD: clickhouse
      # Cache
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_AUTH: myredissecret
      # Storage
      LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT: http://minio:9000
      LANGFUSE_S3_MEDIA_UPLOAD_ENDPOINT: http://minio:9000
      # Initialization
      LANGFUSE_INIT_ORG_ID: local-org
      LANGFUSE_INIT_ORG_NAME: "Local Organization"
      LANGFUSE_INIT_PROJECT_ID: local-project
      LANGFUSE_INIT_PROJECT_NAME: "Pipecat Demo"
      LANGFUSE_INIT_PROJECT_PUBLIC_KEY: pk-lf-local
      LANGFUSE_INIT_PROJECT_SECRET_KEY: sk-lf-local-secret-key
      LANGFUSE_INIT_USER_EMAIL: admin@local.langfuse.com
      LANGFUSE_INIT_USER_NAME: "Admin User"
      LANGFUSE_INIT_USER_PASSWORD: admin123

  langfuse-worker:
    image: docker.io/langfuse/langfuse-worker:3
    depends_on: *langfuse-depends-on
    environment: *langfuse-worker-env
```

## Environment Variables Reference

### Database Configuration
```bash
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres
DIRECT_URL=postgresql://postgres:postgres@postgres:5432/postgres
```

### ClickHouse Analytics
```bash
CLICKHOUSE_MIGRATION_URL=clickhouse://clickhouse:clickhouse@clickhouse:9000
CLICKHOUSE_URL=http://clickhouse:8123
CLICKHOUSE_USER=clickhouse
CLICKHOUSE_PASSWORD=clickhouse
```

### Redis Cache
```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_AUTH=myredissecret
```

### MinIO Storage
```bash
LANGFUSE_S3_EVENT_UPLOAD_BUCKET=langfuse
LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID=minio
LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY=miniosecret
LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT=http://minio:9000
```

## Setup Process

### 1. Start Services
```bash
cd app/otel
docker-compose up -d
```

### 2. Verify Health Checks
```bash
docker-compose ps
# Expected: All services healthy or running
```

### 3. Check Logs
```bash
docker-compose logs langfuse-web | tail -20
# Look for: "✓ Ready in Xs"
```

### 4. Access Web UI
- URL: http://localhost:3000
- Username: admin@local.langfuse.com
- Password: admin123

### 5. Verify API Keys
```bash
# Check database for API keys
docker-compose exec postgres psql -U postgres -d postgres \
  -c "SELECT public_key, project_id FROM api_keys;"
```

## Service Dependencies

```
Langfuse Web/Worker
        ↗
PostgreSQL ← ClickHouse
        ↗
Redis ← MinIO
```

**Startup Order:**
1. PostgreSQL, ClickHouse, Redis, MinIO (data services)
2. Langfuse Worker (background processing)
3. Langfuse Web (user interface)

## Troubleshooting

### Service Won't Start
```bash
# Check service logs
docker-compose logs <service-name>

# Check service health
docker-compose ps

# Restart specific service
docker-compose restart <service-name>
```

### Database Connection Issues
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify connection
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT 1;"
```

### Port Conflicts
```bash
# Check port usage
lsof -i :3000
lsof -i :5432

# Change ports in docker-compose.yml if needed
```

## Data Persistence

```yaml
volumes:
  langfuse_postgres_data:
    driver: local
  langfuse_clickhouse_data:
    driver: local
  langfuse_clickhouse_logs:
    driver: local
  langfuse_minio_data:
    driver: local
```

**Reset Data:**
```bash
docker-compose down -v  # Removes volumes
docker-compose up -d    # Recreates with fresh data
```

## Performance Tuning

### Memory Allocation
- PostgreSQL: 512MB minimum
- ClickHouse: 1GB minimum
- Redis: 256MB minimum
- Total: 4GB+ recommended

### Storage Requirements
- PostgreSQL: 2GB initial
- ClickHouse: 5GB initial
- MinIO: 1GB initial
- Total: 10GB+ recommended

## Security Considerations

### Local Development
- All services bound to localhost
- Default passwords (change for production)
- No external access configured

### Production Deployment
- Use secrets management
- Configure TLS/SSL
- Set up proper networking
- Enable authentication
- Configure backups

## Monitoring

### Health Checks
```bash
# Service status
docker-compose ps

# Resource usage
docker stats

# Log monitoring
docker-compose logs -f --tail=100
```

### Key Metrics
- PostgreSQL connections
- ClickHouse query performance
- Redis memory usage
- MinIO storage utilization

---

*This setup requires approximately 4GB RAM and 10GB disk space. The initialization process takes 2-3 minutes on first startup.*