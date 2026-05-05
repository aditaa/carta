# Install Guide

Carta Arcanum is supported on Linux. If you are developing from Windows, use
WSL with Ubuntu.

## System Requirements

- Linux, preferably Ubuntu 22.04 or newer.
- Python 3.11 or newer.
- MySQL 8 or compatible.
- Node.js 20 or newer.

## Backend Quick Start

From the repository root:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

The API should be available at:

```text
http://127.0.0.1:8000
```

Check the health endpoint:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Run backend tests:

```bash
PYTHONPATH=backend pytest backend/tests -m unit
PYTHONPATH=backend pytest backend/tests -m functional
```

Run the full local CI check:

```bash
PYTHONPATH=backend ruff check backend
ruff format --check backend
PYTHONPATH=backend python -c "from pathlib import Path; from app.domains.rules.importer import load_rules_dataset; load_rules_dataset(Path('rules/carta-arcanum-2.1.4.rules.json'))"
DATABASE_URL=sqlite+pysqlite:///./ci_rules.db PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
DATABASE_URL=sqlite+pysqlite:///./ci_rules.db PYTHONPATH=backend python -m app.cli.import_rules rules/carta-arcanum-2.1.4.rules.json
PYTHONPATH=backend pytest backend/tests -m unit
PYTHONPATH=backend pytest backend/tests -m functional
PYTHONPATH=backend pytest backend/tests --cov=app --cov-branch --cov-report=term-missing --cov-fail-under=70
```

Run the MySQL integration check after local MySQL is running and the
`carta_arcanum` database/user have been created:

```bash
DATABASE_URL=mysql+pymysql://carta:change-me@127.0.0.1:3306/carta_arcanum PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
DATABASE_URL=mysql+pymysql://carta:change-me@127.0.0.1:3306/carta_arcanum PYTHONPATH=backend python -m app.cli.import_rules rules/carta-arcanum-2.1.4.rules.json
DATABASE_URL=mysql+pymysql://carta:change-me@127.0.0.1:3306/carta_arcanum PYTHONPATH=backend pytest backend/tests -m integration
```

## Configuration

Backend configuration is read from environment variables.

For local development:

```bash
cp backend/.env.example backend/.env
```

The backend uses MySQL for database-backed routes and migrations. Some tests
use in-memory SQLite fixtures so CI can run quickly without a MySQL service.

## MySQL Preparation

Install MySQL when database-backed features begin:

```bash
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
```

Create the local database and user:

```bash
sudo mysql
```

```sql
CREATE DATABASE carta_arcanum;
CREATE USER 'carta'@'localhost' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON carta_arcanum.* TO 'carta'@'localhost';
FLUSH PRIVILEGES;
```

Update `backend/.env` if you choose different credentials.

Run migrations:

```bash
alembic -c backend/alembic.ini upgrade head
```

Import the current rules dataset:

```bash
PYTHONPATH=backend python -m app.cli.import_rules rules/carta-arcanum-2.1.4.rules.json
```

## Useful Backend Endpoints

- `GET /api/v1/health`
- `GET /api/v1/rules/current`
- `GET /api/v1/auth/visibility-preview`
- `GET /api/v1/buildings`

## Frontend

Install Node.js 20 or newer using your preferred Linux package manager or
NodeSource.

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run the frontend:

```bash
npm run dev
```

The app should be available at:

```text
http://127.0.0.1:5173
```

Run frontend checks:

```bash
npm run lint
npm run typecheck
npm test -- --run
npm run build
```
