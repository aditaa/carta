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
- `GET /api/v1/buildings/db`
- `POST /api/v1/buildings/db`
- `GET /api/v1/buildings/db/{building_id}`
- `PATCH /api/v1/buildings/db/{building_id}`
- `DELETE /api/v1/buildings/db/{building_id}`

The `/api/v1/buildings/db` routes are database-backed and require a bearer
token from `POST /api/v1/auth/login`; visibility is derived from the
authenticated denizen.

## Migrations

```bash
alembic -c backend/alembic.ini upgrade head
```

Alembic reads `DATABASE_URL` when present. The first migration creates
denizens, profile fields, system account flags, houses, kingdoms, memberships,
personal holdings, house stash, house-held denizen stash, kingdom stash, Three
Crowns Counting House accounts, and audit ledger entries. It also creates
scoped permission grants for ACL-style delegation.
The second migration creates owned building records for the building registry.
The third migration creates imported rules tables.

## Rules Import

Rules are maintained manually in JSON, then imported into SQL:

```bash
PYTHONPATH=backend python -m app.cli.import_rules rules/carta-arcanum-2.1.4.rules.json
```

## Local Denizen

```bash
PYTHONPATH=backend python -m app.cli.create_denizen --email you@example.com --display-name "Your Name"
```

Optional profile/setup flags include `--character-name`, `--pronouns`,
`--contact`, `--profile-note`, `--status`, `--religion`, and
`--system-account`.

## Tests

```bash
PYTHONPATH=backend pytest backend/tests
```

## Configuration

Copy `.env.example` to `.env` when local overrides are needed.

The current skeleton reads configuration from environment variables. MySQL is
the supported database target for local runs and migrations.
