# Production Deployment Guide

## Environment Variables

Create a `.env` file in the project root:

```env
# Application
PROJECT_NAME=Orbit
API_V1_STR=/api/v1

# Database (Production)
DATABASE_URL=postgresql+asyncpg://orbit:SECURE_PASSWORD@db:5432/orbit_db

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
BACKEND_CORS_ORIGINS=["https://yourdomain.com"]
```

## Docker Production Setup

1. Build the production image:
```bash
docker build -t orbit:latest .
```

2. Run with docker-compose:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Database Migrations

Initialize Alembic:
```bash
alembic init alembic
```

Create a migration:
```bash
alembic revision --autogenerate -m "Initial migration"
```

Apply migrations:
```bash
alembic upgrade head
```

## Monitoring

- Health check endpoint: `/health`
- Metrics endpoint: `/metrics` (if enabled)
- Logs: Structured JSON logging to stdout

## Scaling

### Horizontal Scaling
- Run multiple API instances behind a load balancer
- Use Redis for distributed WebSocket pub/sub
- Implement Celery for distributed task execution

### Database Optimization
- Enable connection pooling
- Add appropriate indexes on `status` and `workflow_id` columns
- Consider read replicas for heavy read workloads

## Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Implement rate limiting
- [ ] Enable JWT authentication
- [ ] Set up database backups
- [ ] Configure firewall rules
- [ ] Enable audit logging
