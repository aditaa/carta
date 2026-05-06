# Contributing

Thanks for helping build Carta Arcanum.

## Project Direction

This project is a planning and tracking app for Carta Arcanum. Contributions
should support one or more of these goals:

- Track buildings and ownership.
- Track inputs, outputs, upkeep, deficits, and surpluses.
- Visualize production chains.
- Calculate missing resources for desired outputs.
- Support phase-based progression.
- Keep rules data versioned and replaceable when the game changes.

## Local Development

The project stack is:

- Python and FastAPI for the backend.
- MySQL for persistence.
- React for the frontend.
- D3.js for production graphs.
- Linux for supported runtime environments.

See `INSTALL.md` for the current Linux install and run commands. On Windows,
use WSL with Ubuntu.

Before opening a pull request, run:

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

For frontend changes, run:

```bash
cd frontend
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

CI also runs MySQL integration checks against MySQL 8. If you have local MySQL
running, verify that path with:

```bash
DATABASE_URL=mysql+pymysql://carta:change-me@127.0.0.1:3306/carta_arcanum PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
DATABASE_URL=mysql+pymysql://carta:change-me@127.0.0.1:3306/carta_arcanum PYTHONPATH=backend python -m app.cli.import_rules rules/carta-arcanum-2.1.4.rules.json
DATABASE_URL=mysql+pymysql://carta:change-me@127.0.0.1:3306/carta_arcanum PYTHONPATH=backend pytest backend/tests -m integration
```

## Contribution Workflow

1. Create a focused branch for the change.
2. Keep rules changes separate from application logic changes when possible.
3. Add or update tests for behavior changes.
4. Update documentation when setup, architecture, or user workflows change.
5. Open a pull request with a short summary and verification notes.

## Rules Updates

Rules are stored in `rules/` as manually maintained versioned data files. If
the game rules change:

1. Add a new versioned rules file.
2. Preserve older rules files for historical compatibility.
3. Include rules version and maintainer notes in the new file.
4. Avoid hard-coding rules in backend or frontend code.

## Coding Standards

- Keep backend business logic outside of FastAPI route handlers.
- Use Pydantic models for request and response contracts.
- Keep solver logic deterministic and testable.
- Prefer explicit resource and building identifiers over display names.
- Keep React components focused and reusable.
- Use D3 for graph rendering, but keep graph data preparation outside the D3
  rendering layer.

## Pull Request Checklist

- The change is scoped and easy to review.
- Documentation is updated when needed.
- Rules data remains separate from app logic.
- Tests or verification notes are included.
- Lint, format, and tests pass locally.
- No unrelated formatting or generated files are included.
