# Backlog

This checklist tracks Carta Arcanum's implemented foundation and captured
follow-up work. Completed items document useful project decisions; unchecked
items are the active backlog.

## 1. Foundation Decisions

- [x] Decide the top-level Django project name. Decision: `carta`.
- [x] Decide the first Django app set. Decision:
  - [x] `accounts`
  - [x] `rulesets`
  - [x] `resources`
  - [x] `ownership`
  - [x] `holdings`
  - [x] `buildings`
  - [x] `production`
  - [x] `progression`
  - [x] `solver`
  - [x] `dashboard`
  Decision: keep this app set unless future domain boundaries call for a clearer
  split.
- [x] Decide whether to use Django's default `User` model with a denizen
  profile or a custom user model before the first migration. Decision: custom
  email-based user model plus `DenizenProfile`.
- [x] Decide whether local development may use SQLite temporarily or whether
  MySQL is required from day one. Decision: MySQL from day one.
- [x] Decide whether to use plain Django tests or `pytest-django`. Decision:
  use pytest and `pytest-django`.

## 2. Repository Baseline

- [x] Keep the repository focused on the current Django application.
- [x] Remove obsolete app code, tooling, and docs that no longer describe the
  supported product.
- [x] Update `.gitignore` for Django artifacts, static output, local env files,
  and MySQL/dev database leftovers.
- [x] Update `pyproject.toml` for Django package names and lint paths.
- [x] Update CI to run the current Django lint and test checks.

## 3. Framework Skeleton

- [x] Create a Python virtual environment workflow for the app.
- [x] Add root `requirements.txt`.
- [x] Add Django.
- [x] Add MySQL driver.
- [x] Add environment configuration support.
- [x] Run `django-admin startproject carta .`.
- [x] Create base settings with environment-based `SECRET_KEY`, `DEBUG`,
  `ALLOWED_HOSTS`, database credentials, timezone, static files, and media
  files.
- [x] Add a local GUI path for validating and saving MySQL connection settings.
- [x] Add a local GUI path for running migrations and importing rules.
- [x] Add first-run redirect to the installer before setup is complete.
- [x] Add installer prerequisite checks.
- [x] Add installer superuser creation.
- [x] Lock the installer after successful setup.
- [x] Add local development settings documentation.
- [x] Create initial URL configuration.
- [x] Create base template layout.
- [x] Create static CSS entrypoint.
- [x] Add HTMX to the base template.
- [x] Prototype the map renderer with Canvas or PixiJS.
- [x] Add a dashboard home page.
- [x] Add a health/status page for deployment checks.

## 4. Tooling And Quality

- [x] Configure linting for the Django codebase.
- [x] Configure formatting.
- [x] Configure tests.
- [x] Add a first smoke test for the home page.
- [x] Add a first smoke test for settings import.
- [x] Add a first database migration test or documented migration check.
- [x] Update GitHub Actions for Django lint/test checks.
- [x] Add a MySQL-backed CI job for model and service tests.
- [x] Document local quality commands in `README.md` and `CONTRIBUTING.md`.

## 5. Rules Data Foundation

- [x] Keep raw rules files in `rules/`.
- [x] Keep `rules/rules.schema.json` as the validation contract unless a better
  Django-native validation layer replaces it.
- [x] Create `rulesets` models for imported ruleset metadata.
- [x] Create `resources` models for currencies, resources, units, rarities, and
  categories.
- [x] Create building definition models.
- [x] Create production recipe models.
- [x] Create upkeep requirement models.
- [x] Create phase and unlock models once rules data exists.
- [x] Create transport and ownership-rule models used by the rules file.
- [x] Create title models once rules data exists.
- [x] Port rules JSON loading into a Django service.
- [x] Add rules validation service.
- [x] Add `manage.py import_rules`.
- [x] Make import idempotent by rules version.
- [x] Add admin pages for imported rules.
- [x] Add tests for valid rules import.
- [x] Add tests for invalid rules rejection.

## 6. Accounts, Auth, And Permissions

- [x] Choose final user model strategy before migrations.
- [x] Create denizen profile model.
- [x] Add system account support.
- [x] Create house model.
- [x] Create kingdom model.
- [x] Create house membership model.
- [x] Create kingdom membership model.
- [x] Define role choices: read-only, member, manager, admin.
- [x] Use Django groups/permissions for scoped platform grants unless a future
  boundary needs a custom grant model.
- [x] Create visibility service for denizen, house, and kingdom scopes.
- [ ] Add Three Crowns visibility scopes.
- [x] Add login/logout pages.
- [x] Add first-admin setup path.
- [x] Add permission tests for personal visibility.
- [x] Add permission tests for house visibility.
- [x] Add permission tests for kingdom visibility.
- [ ] Add permission tests for Three Crowns visibility.

## 7. Holdings And Ownership

- [x] Model denizen personal holdings.
- [x] Model house holdings.
- [x] Model house-held denizen holdings.
- [x] Model kingdom holdings.
- [x] Model Three Crowns denizen accounts.
- [x] Model Three Crowns house accounts.
- [x] Model Three Crowns kingdom accounts.
- [x] Validate holding item keys against imported rules.
- [x] Add audit ledger model for holding changes.
- [x] Add service methods for deposit, withdrawal, transfer, and correction.
- [x] Add admin views for inspecting holdings.
- [x] Add web pages for holdings summaries.
- [x] Add web forms for deposit, withdrawal, transfer, and correction.
- [x] Add HTMX forms for focused holding edits.
- [x] Add tests for validation and permission boundaries.

## 8. Building Registry

- [x] Model owned buildings.
- [x] Link owned buildings to owners and imported building definitions.
- [x] Add building registry list page.
- [x] Add building edit form.
- [x] Add building delete form.
- [x] Add building create form.
- [x] Add HTMX partials for inline edits and filters.
- [x] Add status, category, and owner-scope filters.
- [x] Add specific owner filters.
- [x] Add registry summary counts.
- [x] Add audit ledger entries for building changes.
- [x] Add tests for registry visibility.
- [x] Add tests for create/update/delete permissions.

## 9. Production, Upkeep, And Balance

- [x] Create domain service for upkeep totals.
- [x] Create domain service for production totals.
- [x] Create domain service for net resource balance.
- [x] Calculate deficits.
- [x] Calculate surpluses.
- [x] Create dashboard panels for upkeep, production, deficits, and surplus.
- [x] Add alerts like "missing X to sustain Y."
- [x] Add tests for known upkeep examples.
- [x] Add tests for known production examples.
- [x] Add tests for deficit and surplus calculations.

## 10. Interactive Map

- [x] Define the first map use case: view-only campaign map, editable hex map,
  or both.
- [x] Prototype Canvas rendering for the hex map.
- [x] Choose Canvas or PixiJS for the first production map implementation.
- [x] Define map coordinate and hex-coordinate systems.
- [x] Add map image or tile asset storage strategy.
- [x] Add versioned world map and detail map imports for release artifacts.
- [x] Add map page.
- [x] Add pan, zoom, and fit-to-map controls.
- [x] Add coordinate readout for cursor/selected hex.

## 11. Dependency Solver

- [x] Define solver input shape.
- [x] Define solver result shape.
- [x] Build dependency chain traversal.
- [x] Calculate required buildings for a desired output.
- [x] Calculate required inputs.
- [x] Calculate resulting deficits and surpluses.
- [x] Detect circular dependencies.
- [x] Add solver page with target selection.
- [x] Add tests for known simple scenarios.
- [x] Add tests for circular and missing-input scenarios.

## 12. Admin And Operations

- [x] Register core models in Django admin.
- [x] Add useful list displays, filters, and search fields.
- [ ] Protect dangerous admin edits where rules data should stay import-owned.
- [ ] Add admin-only import status page or command output guidance.
- [x] Add a superuser status page for install health and core runtime checks.
- [x] Add a superuser settings section for app configuration.
- [x] Add a web-based upgrade and maintenance plan to the superuser
  status/settings area, including current version display, backup reminders,
  migration/rules import readiness checks, upgrade progress, and rollback
  guidance.
- [x] Add `.env.local` and `installer.lock` write-permission checks to the
  superuser status page.
- [x] Add an optional systemd service helper or documented command for running
  the app from a cloned release branch.
- [x] Add deployment health checks.
- [x] Add static file collection docs.
- [x] Add production service docs for Linux.
- [x] Add backup and restore notes for MySQL.

## 13. Documentation

- [x] Keep `README.md` focused on what Carta Arcanum is and how to run it.
- [x] Update `docs/INSTALL.md` with exact Django setup commands.
- [x] Update `CONTRIBUTING.md` with exact lint, test, migration, and rules
  import commands.
- [x] Update `AGENTS.md` when the app layout is finalized.
- [x] Keep `docs/ROADMAP.md` high-level and use this file for detailed backlog
  tracking.
- [x] Add user-facing notes for first-run setup or admin creation.

## 14. Current Foundation Check

- [x] Rules validation/import exists.
- [x] Login exists.
- [ ] Visibility scopes are complete.
- [x] Holdings foundations exist.
- [x] Building registry exists.
- [x] Upkeep preview exists.
- [x] Dashboard shell exists.
- [x] Tests cover core behavior.
