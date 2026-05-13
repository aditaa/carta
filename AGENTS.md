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

Carta Arcanum is being rewritten as a Django monolith. The previous FastAPI
backend and React frontend have been removed; new work should target Django.

- Web framework: Python with Django.
- Database: MySQL.
- UI: Django templates with HTMX for targeted dynamic interactions.
- Interactive map: target Canvas or PixiJS for a large hex-grid campaign map.
- Runtime support: Linux only. Use WSL for local testing from Windows.

## Architecture Preferences

- Keep rules data in `rules/`, separate from application logic.
- Treat rules as manually maintained versioned data. Do not hard-code game
  values in the solver, Django views, templates, or database migrations.
- Put domain logic for production chains, upkeep, balancing, and dependency
  solving in Django app service modules, not views, template tags, or forms.
- Use Django forms and model validation for web interactions. Add explicit
  schema-like objects only when a boundary needs them.
- Design auth and permissions before expanding ownership features. A baseline
  user should see their own data; a user with house permissions should see
  their own data plus users and assets in that house.
- Prefer normalized database tables for imported rulesets, buildings,
  currencies, resources, ownership, production recipes, upkeep requirements,
  settlement tiers, and phase progression.
- Prefer server-rendered pages. Use HTMX for partial updates, previews,
  filters, inline edits, and setup flows. Keep custom JavaScript small and
  localized.
- Do not assume D3 or Leaflet for the map. Target Canvas or PixiJS so the app
  can support a large, smooth, editable hex-grid campaign map.
- Treat game updates as event-bound work. Future update workflows should model
  planned, confirmed, and verified states so players can queue planned changes,
  confirm them at or after events, and mark them verified once success is
  confirmed.

## Suggested Django Apps

- `accounts`: users, sessions, roles, permissions, and visibility scopes.
- `rulesets`: versioned rules loading, validation, and SQL import.
- `resources`: imported resource, currency, unit, and category records.
- `buildings`: player-owned building instances and registry behavior.
- `ownership`: owners, factions, houses, kingdoms, and building ownership.
- `holdings`: denizen, house, kingdom, and Three Crowns inventories.
- `production`: inputs, outputs, upkeep, and production recipes.
- `progression`: phases, unlocks, and phase requirements.
- `solver`: dependency solving, minimal loops, and resource balancing.
- `dashboard`: web views that compose summaries from domain services.

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
4. Import the rules file into the Django-managed database instead of
   hand-editing SQL rows.
5. Keep migration or compatibility code separate from the raw rules file.

## Development Guidelines

- Read the existing code before making changes.
- Keep changes scoped to the user's request.
- Do not overwrite user changes.
- Prefer `rg` for searching.
- Keep install and runtime documentation Linux-first.
- Use clear names for domain concepts from the game.
- Add tests near the behavior being changed once the Django skeleton exists.
- Prefer larger pull requests when the work belongs to one coherent feature or
  branch goal, but keep them scoped and reviewable.
- Keep branches focused on one task, improvement, or bug fix. A branch may be
  large when the work is one coherent feature area, but avoid mixing unrelated
  admin, gameplay, documentation, or infrastructure changes.
- Use branch names that describe the branch goal clearly. Prefer names like
  `codex/admin-settings-workflows` over stale or unrelated names.
- Commit and push useful increments often within a branch instead of saving one
  large commit for the end.
- Make small commits at meaningful boundaries and push to Git frequently so the
  remote branch stays current and the eventual pull request is easy to review.
- Keep commit boundaries meaningful, such as model/migration, web workflow,
  tests, or documentation updates.
- After a pull request is closed and the branch is no longer active, remove the
  old local and remote branches to keep the repository tidy. Do not delete a
  branch if there is still follow-up work, an open PR, or uncertainty about
  whether the branch is still needed.
- Run the relevant local quality checks before each commit, and run the full
  CI-style test set before opening or updating a pull request for review.

## Documentation Guidelines

- Keep `README.md` focused on what the project is and how to use it.
- Put longer setup, architecture, roadmap, and transition details in `docs/`.
- Update `docs/INSTALL.md` when setup steps change.
- Update `CONTRIBUTING.md` when the development workflow changes.
- Update this file when conventions for future agents change.
