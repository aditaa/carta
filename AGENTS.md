# Agent Guide

This file is for AI agents and contributors working in this repository.

## Project Intent

Build Carta Arcanum, a web app that tracks buildings, resources, ownership,
upkeep, production chains, deficits, surpluses, and phase progression.

The app should eventually answer planning questions like:

- What buildings are required to sustain a desired output?
- Which inputs are missing?
- Which resources are in surplus?
- What is the full dependency chain?
- What is the minimal stable production loop?

## Expected Stack

- Backend: Python, FastAPI.
- Database: MySQL.
- Frontend: React.
- Visualization: D3.js for production graphs.
- Runtime support: Linux only. Use WSL for local testing from Windows.

## Architecture Preferences

- Keep rules data in `rules/`, separate from application logic.
- Treat rules as manually maintained versioned data. Do not hard-code game
  values in the solver, API routes, frontend components, or database
  migrations.
- Put domain logic for production chains, upkeep, balancing, and dependency
  solving in backend service modules, not route handlers.
- Keep API contracts explicit with Pydantic models.
- Design auth and permissions before expanding ownership features. A baseline
  user should see their own data; a user with house permissions should see
  their own data plus users and assets in that house.
- Prefer normalized database tables for imported rulesets, buildings,
  currencies, resources, ownership, production recipes, upkeep requirements,
  settlement tiers, and phase progression.
- Keep frontend state predictable. Use a clear data-fetching boundary between
  React components and API calls.

## Suggested Backend Domains

- `buildings`: player-owned building instances and registry behavior.
- `auth`: users, sessions or tokens, roles, permissions, and visibility scopes.
- `rules`: versioned rules loading, validation, and SQL import.
- `resources`: imported resource, currency, unit, and category records.
- `production`: inputs, outputs, upkeep, and production recipes.
- `ownership`: owners, factions, and building ownership records.
- `progression`: phases, unlocks, and phase requirements.
- `solver`: dependency solving, minimal loops, and resource balancing.

## Rules Handling

Rules are maintained manually as structured arrays. Each game rules version
should live in a versioned file under `rules/`, for example:

```text
rules/carta-arcanum-2.1.5.rules.json
```

When rules change:

1. Add a new rules file instead of editing historical versions in place.
2. Update metadata with the rules version and maintainer notes.
3. Validate that required sections are present.
4. Import the rules file into SQL instead of hand-editing SQL rows.
5. Keep migration or compatibility code separate from the raw rules file.

## Development Guidelines

- Read the existing code before making changes.
- Keep changes scoped to the user's request.
- Do not overwrite user changes.
- Prefer `rg` for searching.
- Keep install and runtime documentation Linux-first.
- Use clear names for domain concepts from the game.
- Add tests near the behavior being changed once the backend/frontend skeletons
  exist.

## Documentation Guidelines

- Update `README.md` when setup steps, architecture, or user-facing behavior
  changes.
- Update `CONTRIBUTING.md` when the development workflow changes.
- Update this file when conventions for future agents change.
