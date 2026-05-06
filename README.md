# Carta Arcanum

Carta Arcanum is a planning app for tracking buildings, ownership, upkeep,
production chains, deficits, surpluses, and phase progression for Carta
Arcanum play.

The goal is to help players answer practical questions quickly:

- Who owns which buildings?
- What does the settlement currently produce?
- What upkeep is required to sustain the current build?
- Which inputs are missing?
- Which outputs are in surplus?
- What dependency chain is needed to support a desired target?

## Core Features

- Building registry for farms, shops, markets, towers, and future building
  types.
- Denizen authentication with permission-scoped visibility.
- Ownership tracking for players, groups, or factions.
- Input and output tracking for crops, currency, rarities, and other resources.
- Auto-calculated upkeep totals across all owned buildings.
- Deficit and surplus alerts such as "missing 3 crop to sustain 1 farm."
- Production graph showing resource flow between buildings.
- Phase-based progression tracker for settlement or campaign advancement.

## Solver Goals

The planner should eventually allow a user to choose a desired output, such as
"sustain 1 farm", and calculate:

- Required buildings.
- Required inputs.
- Full dependency chain.
- Resource balance after upkeep.
- Minimal loops that keep a production chain stable.

Bonus solver capabilities:

- Dependency solver.
- Minimal loop generator.
- Resource balancing.
- D3.js production graph visualization.

## Tech Stack

- Backend: Python with FastAPI.
- Database: MySQL.
- Frontend: React.
- Graph visualization: D3.js.
- Supported runtime: Linux.

## Proposed Project Layout

```text
.
|-- backend/              # FastAPI service, domain logic, solver APIs
|-- frontend/             # React app and D3 visualizations
|-- rules/                # Manually maintained versioned game rules data
|-- AGENTS.md             # Working notes for AI/dev agents
|-- CONTRIBUTING.md       # Contribution workflow
|-- INSTALL.md            # Linux install and run guide
|-- ROADMAP.md            # Big milestone and todo tracker
`-- README.md
```

## Quick Install

Carta Arcanum is supported on Linux. On Windows, use WSL with Ubuntu.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

Then open:

```text
http://127.0.0.1:8000/api/v1/health
```

See `INSTALL.md` for the full setup guide.

Frontend quick start:

```bash
cd frontend
npm ci
npm run dev
```

Then open:

```text
http://127.0.0.1:5173
```

## Quality Checks

CI runs on Ubuntu for pushes to `main` or `master` and for pull requests.
Run the same backend checks locally before opening a PR:

```bash
source .venv/bin/activate
PYTHONPATH=backend ruff check backend
ruff format --check backend
PYTHONPATH=backend python -c "from pathlib import Path; from app.domains.rules.importer import load_rules_dataset; load_rules_dataset(Path('rules/carta-arcanum-2.1.4.rules.json'))"
DATABASE_URL=sqlite+pysqlite:///./ci_rules.db PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
DATABASE_URL=sqlite+pysqlite:///./ci_rules.db PYTHONPATH=backend python -m app.cli.import_rules rules/carta-arcanum-2.1.4.rules.json
PYTHONPATH=backend pytest backend/tests -m unit
PYTHONPATH=backend pytest backend/tests -m functional
PYTHONPATH=backend pytest backend/tests --cov=app --cov-branch --cov-report=term-missing --cov-fail-under=70
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

CI also runs a MySQL integration job with a real MySQL 8 service:

```bash
DATABASE_URL=mysql+pymysql://carta:carta@127.0.0.1:3306/carta_arcanum PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
DATABASE_URL=mysql+pymysql://carta:carta@127.0.0.1:3306/carta_arcanum PYTHONPATH=backend python -m app.cli.import_rules rules/carta-arcanum-2.1.4.rules.json
DATABASE_URL=mysql+pymysql://carta:carta@127.0.0.1:3306/carta_arcanum PYTHONPATH=backend pytest backend/tests -m integration
```

Create a local login denizen after migrations are applied:

```bash
PYTHONPATH=backend python -m app.cli.create_denizen --email you@example.com --display-name "Your Name"
```

## Rules Data

Rules are intentionally kept separate in `rules/` so game changes can be
entered manually without rewriting app logic.

The starter rules file is:

```text
rules/carta-arcanum-2.1.4.rules.json
```

Application code should treat this as versioned input data made of arrays for
currencies, resources, units, settlement tiers, building definitions,
production recipes, ownership rules, transports, titles, and phases. The JSON
file is the manual source of truth; SQL records are imported from it for linked
queries and validation. Backend models, database migrations, and solver logic
should not hard-code values that belong in the rules file.

## Roadmap

See `ROADMAP.md` for the milestone todo list.

## Development Status

This repository is in project setup mode. Current foundations include rules
validation/import, denizen token login, auth visibility scaffolding, building registry
CRUD, upkeep preview calculations, and a React dashboard shell. The next build
steps are:

1. Apply authenticated user scope to database-backed building endpoints.
2. Continue final-checking the manually maintained rules dataset.
3. Add production totals and deficit/surplus calculations.
4. Add editable frontend registry workflows.
5. Add graph visualization and dependency solving.
