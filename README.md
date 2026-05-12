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
- Denizen, house, kingdom, and Three Crowns holdings that accept rules-backed
  currencies, resources, and units.
- Ownership tracking for players, groups, or factions.
- Input and output tracking for crops, currency, rarities, and other resources.
- Auto-calculated upkeep totals across all owned buildings.
- Deficit and surplus alerts such as "missing 3 crop to sustain 1 farm."
- Interactive campaign map for territories, hexes, settlements, and points of
  interest.
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
- Interactive map and planning visualization.

## Tech Stack

Carta Arcanum is being rewritten as a Django monolith. The previous FastAPI
backend and React frontend have been removed and should not be treated as the
target architecture for new feature work.

- Web framework: Python with Django.
- Database: MySQL.
- UI: Django templates with HTMX for targeted dynamic interactions.
- Map and visualization: target Canvas or PixiJS for a large editable hex-grid
  campaign map.
- Supported runtime: Linux.

## Proposed Project Layout

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
|-- rules/                # Manually maintained versioned game rules data
|-- AGENTS.md             # Working notes for AI/dev agents
|-- CONTRIBUTING.md       # Contribution workflow
|-- INSTALL.md            # Linux install and run guide
|-- ROADMAP.md            # Big milestone and todo tracker
`-- README.md
```

## Rewrite Status

The first Django skeleton is in place with a custom email-based user model,
`DenizenProfile`, MySQL settings, a dashboard home page, a health endpoint,
building registry pages, holdings pages, production balance services, and
smoke tests.

Carta Arcanum remains Linux-first. On Windows, use WSL with Ubuntu.

## Quality Checks

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run checks that do not require a local MySQL server:

```bash
python -m ruff check .
python -m ruff format --check .
python manage.py check
python -m pytest dashboard/tests tests
```

Run the full test suite after MySQL is running and configured:

```bash
python manage.py migrate
python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
python -m pytest
```

The local web installer starts at `/install/`. It can test and save the MySQL
connection to `.env.local`, then run migrations and import the current rules
file after the server restarts with the saved settings.

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
file is the manual source of truth; Django models, migrations, templates, and
solver logic should not hard-code values that belong in the rules file.

Import the current rules file with:

```bash
python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
```

## Roadmap

See `ROADMAP.md` for the milestone todo list and `TRANSITION_TODO.md` for the
detailed Django rewrite checklist.

## Development Status

This repository is pivoting from a split FastAPI/React app to a Django
monolith. Core dashboard, building, holdings, and production balance flows are
now implemented. The next build steps are:

1. Complete permissions and visibility boundaries for denizen, house,
   kingdom, and Three Crowns data.
2. Finish HTMX workflows for building and holding edits.
3. Stabilize production alerts and owner-specific balance overviews.
4. Add the installer, interactive map, and dependency solver after the first
   version is usable.
