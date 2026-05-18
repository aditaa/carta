# Carta Arcanum

[![CI](https://github.com/aditaa/carta/actions/workflows/ci.yml/badge.svg)](https://github.com/aditaa/carta/actions/workflows/ci.yml)
[![Stable release verification](https://github.com/aditaa/carta/actions/workflows/stable-release-verification.yml/badge.svg)](https://github.com/aditaa/carta/actions/workflows/stable-release-verification.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Django](https://img.shields.io/badge/django-5.x-0c4b33)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)

Carta Arcanum is a Django web app for campaign logistics: buildings, resources,
ownership, holdings, upkeep, production chains, deficits, surpluses, map
assets, and phase progression for Carta Arcanum play.

The app is meant to answer practical planning questions:

- What does each denizen, house, kingdom, or Three Crowns account hold?
- Who owns which buildings?
- What upkeep is required to sustain the current build?
- Which inputs are missing?
- Which outputs are in surplus?
- What dependency chain supports a desired target?

## What This Is

Carta Arcanum is a Django monolith backed by MySQL. It favors server-rendered
pages, Django forms, service-layer domain logic, and focused HTMX interactions
over a separate API/frontend split.

Current foundations include:

- Email-based denizen accounts and login.
- Permission-aware ownership visibility.
- Imported rulesets for resources, currencies, units, buildings, recipes,
  ownership rules, and transports.
- Building registry workflows.
- Denizen, house, kingdom, and Three Crowns holdings.
- Production, upkeep, deficit, and surplus services.
- Canvas campaign map rendering with versioned map imports.
- A first-run installer for local setup.

Rules data lives in `rules/` and is imported into MySQL. Game values should
stay in versioned rules files instead of being hard-coded into views, templates,
models, migrations, or solver logic.

## How To Use

Carta Arcanum is supported on Linux. If you are on Windows, use WSL with
Ubuntu.

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Start the app after MySQL is available:

```bash
python manage.py migrate
python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
python manage.py runserver
```

Open the app:

```text
http://127.0.0.1:8000/
```

On first run, the app redirects to the installer:

```text
http://127.0.0.1:8000/install/
```

The installer checks prerequisites, saves local MySQL settings to `.env.local`,
creates the first superuser, runs migrations, imports the current rules file,
and writes `installer.lock` when setup is complete.

## Common Commands

Run the quick local checks:

```bash
./scripts/check.sh quick
```

Run the full suite after MySQL is configured:

```bash
./scripts/check.sh full
```

Windows users working outside WSL can use `.\scripts\check.ps1 quick` for the
same smoke checks.

## More Documentation

- [Docs index](docs/README.md)
- [Install guide](docs/INSTALL.md)
- [Project structure](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Backlog](docs/BACKLOG.md)
- [Contributing](CONTRIBUTING.md)
