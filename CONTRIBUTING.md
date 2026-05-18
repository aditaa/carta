# Contributing

Thanks for helping build Carta Arcanum.

## Start Here

Carta Arcanum is a Django monolith backed by MySQL and server-rendered Django
templates. The supported runtime is Linux; use WSL with Ubuntu when developing
from Windows.

Read these before changing code:

- [README](README.md) for the short project overview and daily commands.
- [Install guide](docs/INSTALL.md) for complete Linux setup.
- [Architecture notes](docs/ARCHITECTURE.md) for app layout and boundaries.
- [Roadmap](docs/ROADMAP.md) for planned work.

## Workflow

1. Create a focused branch.
2. Read the existing code around the change.
3. Keep rules data separate from application logic.
4. Add or update tests for behavior changes.
5. Update docs when setup, architecture, or user workflows change.
6. Open a pull request with a short summary and verification notes.

## Quality Checks

Before opening a pull request, run:

```bash
./scripts/check.sh full
```

The full test suite expects MySQL to be running. If MySQL is not available
locally, run the narrower smoke checks from the README and let CI be the source
of truth for MySQL-only coverage.

For a faster local pass that does not require MySQL, run:

```bash
./scripts/check.sh quick
```

Windows users working outside WSL can use `.\scripts\check.ps1 quick` or
`.\scripts\check.ps1 full`.

## Pre-Commit

Optional pre-commit hooks are available for local formatting, linting, and a
settings smoke test:

```bash
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

The hooks use the Python environment already active in your shell, so install
the project requirements before running them.

## Rules Updates

Rules are manually maintained versioned data files in `rules/`.

When game rules change:

1. Add a new versioned rules file.
2. Preserve older rules files for historical compatibility.
3. Include rules version and maintainer notes in the new file.
4. Import rules through `python manage.py import_rules`.
5. Do not hard-code rules in Django models, views, templates, migrations, or
   solver code.

## Coding Standards

- Keep domain logic in service modules, not views, forms, templates, or template
  tags.
- Use Django forms and model validation for web workflows.
- Keep solver logic deterministic and testable.
- Prefer explicit resource and building identifiers over display names.
- Use HTMX for focused partial updates, previews, filters, inline edits, and
  setup flows.
- Keep custom JavaScript small and localized.
- Target Canvas or PixiJS for future large hex-grid map work.

## Pull Request Checklist

- The change is scoped and easy to review.
- Documentation is updated when needed.
- Rules data remains separate from app logic.
- Tests or verification notes are included.
- Format, lint, Django checks, migrations, rules import, and relevant tests pass
  locally or in CI.
- No unrelated formatting or generated files are included.
