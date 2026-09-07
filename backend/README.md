# VERIFAI Backend

FastAPI backend for the AI-Powered Fake Identity & Document Risk Screening System.

## What This Backend Does

- Manages screening cases (create, list, view, decide)
- Stores uploaded document images
- Integrates AI module results (OCR, MRZ, face, forensics)
- Runs the rule-based risk engine
- Enforces human-in-the-loop decision making
- Logs all actions for audit/accountability
- Provides REST API for the React frontend

## Prerequisites

- **Python 3.12+**
- **PostgreSQL 16** (via Docker or installed locally)
- **Docker & Docker Compose** (recommended) OR local PostgreSQL

## Quick Start (Docker — Recommended)

```bash
# 1. Install Docker Desktop: https://docs.docker.com/desktop/install/mac-install/
# 2. Start everything:
docker compose up --build

# 3. Visit:
#    http://localhost:8000       → API root
#    http://localhost:8000/docs  → Interactive API docs (Swagger)
```

## Quick Start (Without Docker)

```bash
# 1. Install PostgreSQL locally
brew install postgresql@16
brew services start postgresql@16

# 2. Create the database
createuser verifai
createdb verifai_db -O verifai

# 3. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Copy and edit environment variables
cp .env.example .env
# Edit .env if your PostgreSQL config differs

# 5. Run the server
uvicorn app.main:app --reload --port 8000

# 6. Visit http://localhost:8000/docs
```

## Running Tests

```bash
# Activate the virtual environment first
source venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v
```

## Project Structure

```
backend/
├── app/
│   ├── main.py           # FastAPI app entry point (start here!)
│   ├── api/              # Route handlers (endpoints)
│   │   ├── router.py     # Assembles all route modules
│   │   ├── health.py     # GET /api/v1/health/
│   │   └── cases.py      # Case CRUD endpoints
│   ├── core/
│   │   └── config.py     # Settings from environment variables
│   ├── models/           # SQLAlchemy database models
│   │   ├── base.py       # Base class + TimestampMixin
│   │   ├── user.py       # Officer/admin accounts
│   │   ├── case.py       # Cases + Documents
│   │   └── audit.py      # Audit log
│   ├── schemas/          # Pydantic request/response models
│   │   ├── case.py       # Case API contracts
│   │   ├── user.py       # User/auth contracts
│   │   ├── health.py     # Health check
│   │   └── common.py     # RiskSignal + RiskAssessment (shared)
│   ├── services/         # Business logic
│   │   └── audit.py      # Audit logging helper
│   ├── integrations/     # AI module integration stubs
│   └── db/
│       └── session.py    # Database connection setup
├── tests/                # pytest test files
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── Dockerfile            # Container build recipe
├── docker-compose.yml    # Multi-container development setup
└── pytest.ini            # Test configuration
```

## How Teammates Add New Modules

1. **Create a route file**: `app/api/your_module.py`
2. **Define endpoints** using `APIRouter()`
3. **Register in router**: Add one line to `app/api/router.py`
4. **Use shared schemas**: Import `RiskSignalIn` from `app/schemas/common.py`

Example:
```python
# app/api/ocr.py
from fastapi import APIRouter
router = APIRouter()

@router.post("/{document_id}/ocr")
async def run_ocr(document_id: UUID):
    ...
```

Then in `app/api/router.py`:
```python
from app.api.ocr import router as ocr_router
api_router.include_router(ocr_router, prefix="/documents", tags=["ocr"])
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Welcome + links |
| GET | `/api/v1/health/` | Health check |
| POST | `/api/v1/cases` | Create a case |
| GET | `/api/v1/cases` | List all cases |
| GET | `/api/v1/cases/{id}` | Get case details |
| POST | `/api/v1/cases/{id}/decision` | Officer decision |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://verifai:verifai_dev@localhost:5432/verifai_db` |
| `SECRET_KEY` | JWT signing key | (must change in production) |
| `UPLOAD_DIR` | Document image storage path | `uploads` |

