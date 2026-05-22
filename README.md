# Cardiac Matchmaker

## Start

```bash
cp .env.example .env
make up
```

## Stop

```bash
make down
```

## Backend

FastAPI + Peewee + cookie JWT auth. `POST /api/v1/auth/login` sets `access_token`. All `/api/v1/*` routes except `/api/v1/health`, `/api/v1/auth/login`, and `/api/v1/auth/logout` need that cookie.

```bash
docker compose exec backend python -m app.cmd.create_user admin@example.com --superuser
```

Database migrations run automatically when the backend container starts. You can also run them manually:

```bash
docker compose exec backend python -m app.cmd.migrate check
docker compose exec backend python -m app.cmd.migrate apply
```

## .env

```env
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=
POSTGRES_PORT=
JWT_SECRET_KEY=
JWT_ALGORITHM=
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=
```

## Testing

```bash
cd backend && pytest
cd frontend && npm run lint && npm run build
```
