# Django Transition Todo

This checklist tracks the work needed to move Carta Arcanum from the removed
FastAPI/React split app to a Django monolith.

## 1. Transition Decisions

- [x] Decide whether to delete the legacy `backend/` and `frontend/`
  directories immediately or archive them until the Django app reaches feature
  parity. Decision: delete legacy code now.
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
  Decision: start with this app set unless scaffolding reveals a clearer split.
- [x] Decide whether to use Django's default `User` model with a denizen
  profile or a custom user model before the first migration. Decision: custom
  email-based user model plus `DenizenProfile`.
- [x] Decide whether local development may use SQLite temporarily or whether
  MySQL is required from day one. Decision: MySQL from day one.
- [x] Decide whether to use plain Django tests or `pytest-django`. Decision:
  use pytest and `pytest-django`.

## 2. Repository Cleanup

- [x] Remove or archive the legacy FastAPI backend.
- [x] Remove or archive the legacy React frontend.
- [x] Remove Alembic configuration with the legacy backend.
- [x] Remove old Vite, TypeScript, and frontend package files if React is not
  retained.
- [x] Remove old API-only docs after Django docs replace them.
- [x] Update `.gitignore` for Django artifacts, static output, local env files,
  and MySQL/dev database leftovers.
- [x] Update `pyproject.toml` for Django package names and lint paths.
- [x] Update CI to stop running old FastAPI and React checks.

## 3. Django Framework Skeleton

- [x] Create a Python virtual environment workflow for the new app.
- [x] Add root `requirements.txt` or equivalent dependency file.
- [x] Add Django.
- [x] Add MySQL driver.
- [x] Add environment configuration support.
- [x] Run `django-admin startproject carta .`.
- [x] Create base settings with environment-based `SECRET_KEY`, `DEBUG`,
  `ALLOWED_HOSTS`, database credentials, timezone, static files, and media
  files.
- [x] Add a local GUI path for validating and saving MySQL connection settings.
- [x] Add a local GUI path for running migrations and importing rules.
- [x] Add local development settings documentation.
- [x] Create initial URL configuration.
- [x] Create base template layout.
- [x] Create static CSS entrypoint.
- [x] Add HTMX to the base template.
- [ ] Prototype the map renderer with Canvas or PixiJS.
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
- [x] Add a MySQL-backed CI job once models exist.
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
- [ ] Create phase and unlock models once rules data exists.
- [x] Create transport and ownership-rule models used by the rules file.
- [ ] Create title models once rules data exists.
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
- [ ] Create scoped permission grant model if Django groups/permissions are not
  enough.
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
- [ ] Add HTMX forms for focused holding edits.
- [ ] Add tests for validation and permission boundaries.

## 8. Building Registry

- [x] Model owned buildings.
- [x] Link owned buildings to owners and imported building definitions.
- [x] Add building registry list page.
- [x] Add building edit form.
- [x] Add building delete form.
- [x] Add building create form.
- [ ] Add HTMX partials for inline edits and filters.
- [x] Add status, category, and owner-scope filters.
- [ ] Add specific owner filters.
- [x] Add registry summary counts.
- [x] Add audit ledger entries for building changes.
- [x] Add tests for registry visibility.
- [x] Add tests for create/update/delete permissions.

## 9. Production, Upkeep, And Balance

- [ ] Create domain service for upkeep totals.
- [ ] Create domain service for production totals.
- [ ] Create domain service for net resource balance.
- [ ] Calculate deficits.
- [ ] Calculate surpluses.
- [ ] Create dashboard panels for upkeep, production, deficits, and surplus.
- [ ] Add alerts like "missing X to sustain Y."
- [ ] Add owner-specific and settlement-wide views.
- [ ] Add tests for known upkeep examples.
- [ ] Add tests for known production examples.
- [ ] Add tests for deficit and surplus calculations.

## 10. Interactive Map

- [ ] Define the first map use case: view-only campaign map, editable hex map,
  or both.
- [ ] Prototype Canvas rendering for the hex map.
- [ ] Prototype PixiJS rendering for the hex map if Canvas performance or
  interaction complexity needs WebGL acceleration.
- [ ] Choose Canvas or PixiJS for the first production map implementation.
- [ ] Define map coordinate and hex-coordinate systems.
- [ ] Add map image or tile asset storage strategy.
- [ ] Add map page.
- [ ] Add pan, zoom, and fit-to-map controls.
- [ ] Add coordinate readout for cursor/selected hex.
- [ ] Add territory overlays.
- [ ] Add settlement and point-of-interest overlays.
- [ ] Add visibility filters for denizen, house, kingdom, and settlement views.
- [ ] Add tests for map data generation.
- [ ] Add browser/manual verification notes for map rendering.

## 11. Progression Tracker

- [ ] Model campaign or settlement progression state.
- [ ] Model current phase.
- [ ] Model completed requirements.
- [ ] Show phase requirements.
- [ ] Show unlocks.
- [ ] Show missing requirements for next phase.
- [ ] Add admin tools for progression correction.
- [ ] Add tests for phase requirement calculations.

## 12. Dependency Solver

- [ ] Define solver input shape.
- [ ] Define solver result shape.
- [ ] Build dependency chain traversal.
- [ ] Calculate required buildings for a desired output.
- [ ] Calculate required inputs.
- [ ] Calculate resulting deficits and surpluses.
- [ ] Detect circular dependencies.
- [ ] Generate minimal stable production loops.
- [ ] Add solver page with target selection.
- [ ] Add tests for known simple scenarios.
- [ ] Add tests for circular and missing-input scenarios.

## 13. Django Admin And Operations

- [ ] Register core models in Django admin.
- [ ] Add useful list displays, filters, and search fields.
- [ ] Protect dangerous admin edits where rules data should stay import-owned.
- [ ] Add admin-only import status page or command output guidance.
- [ ] Add deployment health checks.
- [ ] Add static file collection docs.
- [ ] Add production service docs for Linux.
- [ ] Add backup and restore notes for MySQL.

## 14. Documentation

- [x] Update `README.md` after the Django skeleton exists.
- [x] Update `INSTALL.md` with exact Django setup commands.
- [x] Update `CONTRIBUTING.md` with exact lint, test, migration, and rules
  import commands.
- [x] Update `AGENTS.md` when the app layout is finalized.
- [x] Keep `ROADMAP.md` high-level and use this file for transition detail.
- [x] Add user-facing notes for first-run setup or admin creation.

## 15. Feature Parity Check

- [ ] Rules validation/import exists in Django.
- [ ] Login exists in Django.
- [ ] Visibility scopes exist in Django.
- [ ] Holdings foundations exist in Django.
- [ ] Building registry exists in Django.
- [ ] Upkeep preview exists in Django.
- [x] Dashboard shell exists in Django.
- [x] Tests cover core migrated behavior.
- [x] Legacy FastAPI code can be safely removed.
- [x] Legacy React code can be safely removed.
