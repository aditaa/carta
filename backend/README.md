# Backend

FastAPI backend for Carta Arcanum.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --app-dir backend
```

The API starts at:

```text
http://127.0.0.1:8000
```

Useful starter endpoints:

- `GET /api/v1/health`
- `GET /api/v1/rules/current`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/visibility-preview`
- `GET /api/v1/auth/sample-scope`
- `GET /api/v1/buildings`
- `GET /api/v1/buildings/upkeep-preview`
- `GET /api/v1/buildings/db?denizen_id=1`
- `POST /api/v1/buildings/db?denizen_id=1`
- `GET /api/v1/buildings/db/{building_id}?denizen_id=1`
- `PATCH /api/v1/buildings/db/{building_id}?denizen_id=1`
- `DELETE /api/v1/buildings/db/{building_id}?denizen_id=1`

The `/api/v1/buildings/db` routes are database-backed. They use temporary
`denizen_id` query parameter visibility until full login/session auth is wired
into registry calls.

## Migrations

```bash
alembic -c backend/alembic.ini upgrade head
```

Alembic reads `DATABASE_URL` when present. The first migration creates
denizens, houses, kingdoms, memberships, and denizen holdings. The second
migration creates owned building records for the building registry. The third
migration creates imported rules tables.

## Rules Import

Rules are maintained manually in JSON, then imported into SQL:

```bash
PYTHONPATH=backend python -m app.cli.import_rules rules/carta-arcanum-2.1.4.rules.json
```

## Local Denizen

```bash
PYTHONPATH=backend python -m app.cli.create_denizen --email you@example.com --display-name "Your Name"
```

## Tests

```bash
PYTHONPATH=backend pytest backend/tests
```

## Configuration

Copy `.env.example` to `.env` when local overrides are needed.

The current skeleton reads configuration from environment variables. MySQL is
the supported database target for local runs and migrations.
