# Architecture Notes

Carta Arcanum is a Django monolith. The previous FastAPI backend and React
frontend have been removed and should not guide new feature work.

## Stack

- Web framework: Python with Django.
- Database: MySQL.
- UI: Django templates with HTMX for targeted dynamic interactions.
- Map and visualization: Canvas or PixiJS for a large editable hex-grid
  campaign map.
- Supported runtime: Linux.

## Project Layout

```text
.
|-- carta/                # Django project settings and URL configuration
|-- accounts/             # Users, roles, permissions, and visibility scopes
|-- rulesets/             # Versioned rules loading, validation, and import
|-- resources/            # Resources, currencies, units, and categories
|-- buildings/            # Building registry and ownership behavior
|-- ownership/            # Houses, kingdoms, owners, and faction records
|-- holdings/             # Denizen, house, kingdom, and Three Crowns holdings
|-- production/           # Recipes, upkeep, outputs, and balance services
|-- progression/          # Phases, unlocks, and requirements
|-- solver/               # Dependency solving and resource balancing
|-- dashboard/            # Django views, templates, and page composition
|-- installer/            # First-run setup flow
|-- transports/           # Imported transport rules
|-- rules/                # Manually maintained versioned game rules data
|-- docs/                 # Long-form project documentation
|-- docs/reference/       # Source/reference material for rules maintenance
|-- AGENTS.md             # Working notes for AI/dev agents
|-- CONTRIBUTING.md       # Contribution workflow
`-- README.md             # Short overview and daily usage
```

## Boundaries

- Keep rules data in `rules/`, separate from application logic.
- Treat rules as manually maintained versioned data.
- Put production chains, upkeep, balancing, and dependency solving in Django
  app service modules.
- Keep views focused on request handling and page composition.
- Use Django forms and model validation for web interactions.
- Add explicit schema-like objects only when a boundary needs them.

## Rules Handling

Each game rules version should live in a versioned file under `rules/`, for
example:

```text
rules/carta-arcanum-2.1.4.rules.json
```

When rules change:

1. Add a new rules file instead of editing historical versions in place.
2. Update metadata with the rules version and maintainer notes.
3. Validate that required sections are present.
4. Import the rules file into the Django-managed database.
5. Keep migration or compatibility code separate from the raw rules file.

Import the current rules file with:

```bash
python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
```

The installer uses `CURRENT_RULES_FILE`, which defaults to the current rules
JSON file and can be overridden with `CARTA_CURRENT_RULES_FILE`.

## Current Status

The Django foundation includes a custom email-based user model,
`DenizenProfile`, MySQL settings, a dashboard home page, a health endpoint,
building registry pages, holdings pages, production balance services, a
first-run installer, and smoke tests.
