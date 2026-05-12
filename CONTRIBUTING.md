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

The project is being rewritten as a Django monolith. The target stack is:

- Python and Django for the web app.
- MySQL for persistence.
- Django templates with HTMX for targeted dynamic interactions.
- Canvas or PixiJS for the future interactive hex map.
- Linux for supported runtime environments.

See `INSTALL.md` for Linux install and run commands. On Windows, use WSL with
Ubuntu.

Before opening a pull request, run:

```bash
python -m ruff format --check .
python -m ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest tests/test_settings.py ownership/tests production/tests buildings/tests holdings/tests
python -m pytest accounts/tests dashboard/tests installer/tests
python -m pytest rulesets/tests
```

The full test suite expects MySQL to be running. Use the narrower non-database
smoke checks from `INSTALL.md` when MySQL is not available locally.
These commands mirror CI's separate format, lint, Django project check, domain
service test, web workflow test, and rules import test jobs so failures stay
easy to locate.

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
4. Avoid hard-coding rules in Django models, views, templates, or solver code.

## Coding Standards

- Keep business logic outside of Django views, forms, and templates.
- Use Django forms, model validation, and explicit service functions for web
  workflows.
- Keep solver logic deterministic and testable.
- Prefer explicit resource and building identifiers over display names.
- Use HTMX for focused dynamic behavior, not as a substitute for domain logic.
- Keep map and visualization data preparation in Django domain services.
  Rendering should target Canvas or PixiJS once map work begins.

## Pull Request Checklist

- The change is scoped and easy to review.
- Documentation is updated when needed.
- Rules data remains separate from app logic.
- Tests or verification notes are included.
- Format, lint, Django checks, and the split pytest groups pass locally.
- No unrelated formatting or generated files are included.
