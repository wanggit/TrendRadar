# TrendRadar SaaS Backend

FastAPI-based backend for TrendRadar SaaS platform.

## Quick Start

### 1. Start infrastructure

```bash
docker compose -f docker-compose.dev.yml up -d postgres redis
```

### 2. Install dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Create superuser

```bash
python -m app.db.init_db
```

### 6. Start server

```bash
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── api/                 # API routes
│   │   ├── auth.py          # Auth endpoints
│   │   ├── users.py         # User endpoints
│   │   └── deps.py          # Dependencies
│   ├── core/                # Core config & security
│   ├── db/                  # Database setup
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   └── services/            # Business logic
├── alembic/                 # Database migrations
└── requirements.txt
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/auth/register | Register new user |
| POST | /api/v1/auth/login | Login |
| POST | /api/v1/auth/refresh | Refresh token |
| POST | /api/v1/auth/change-password | Change password |
| GET | /api/v1/auth/me | Get current user |
| GET | /api/v1/users/me | Get my profile |
| PUT | /api/v1/users/me | Update my profile |
| GET | /api/v1/users/ | List all users (admin) |
| GET | /api/v1/users/{id} | Get user by ID (admin) |
