# Roadmap

This is the high-level todo list for Carta Arcanum as a Django monolith.

Use [BACKLOG.md](BACKLOG.md) for the detailed implementation tracker.

## Phase 0: Project Foundation

- [x] Choose Django monolith architecture.
- [x] Keep the repository focused on the current Django application.
- [x] Update planning docs for the current architecture.
- [x] Choose the Django project/app layout and package names.
- [x] Update CI to target the Django app.

## Phase 1: Django Skeleton

- [x] Create the Django project.
- [x] Configure MySQL for supported local and production use.
- [x] Add environment-based settings for secrets, database connection, and
  deployment mode.
- [x] Add a local GUI path for validating and saving MySQL connection settings.
- [x] Add a local GUI path for running migrations and importing rules.
- [x] Add a first-run installer flow with prerequisite checks, superuser
  creation, application setup, and installer locking.
- [x] Add Django templates, static files, and base layout.
- [x] Add pytest or Django test runner setup.
- [x] Add linting and formatting checks for the new codebase.
- [x] Update Linux-first install and run documentation.

## Phase 2: Rulesets

- [x] Keep versioned rules data in `rules/`.
- [x] Port rules schema validation into the Django app.
- [x] Model imported rulesets, resources, currencies, units, buildings,
  recipes, settlement tiers, build costs, upkeep requirements, and recipe
  inputs/outputs.
- [x] Model imported ownership rules and transports.
- [x] Model imported titles, phases, and unlocks once rules data exists.
- [x] Add a Django management command to import a rules file.
- [x] Add admin views for inspecting imported rules.
- [x] Add tests for validation and import behavior.

## Phase 3: Accounts And Visibility

- [x] Define the user, denizen profile, system account, house, and kingdom
  model strategy.
- [x] Use Django auth and sessions for login.
- [x] Model roles, memberships, and scoped permissions.
- [ ] Implement personal, house, kingdom, and Three Crowns visibility rules.
- [x] Add tests for permission boundaries.

## Phase 4: Core Web Workflows

- [x] Build the dashboard shell with Django templates.
- [x] Add building registry pages.
- [x] Add holdings pages for denizens, houses, kingdoms, and Three Crowns.
- [ ] Use HTMX for filters, inline edits, form submissions, and preview panels.
- [ ] Add audit-friendly create/update/delete behavior.
- [ ] Add planned, confirmed, and verified lifecycle states for event-bound
  game updates.

## Phase 5: Production And Balancing

- [x] Auto-calculate upkeep totals across owned buildings.
- [x] Auto-calculate production totals.
- [x] Show current deficits and surpluses.
- [x] Add alerts like "missing X to sustain Y."
- [ ] Add owner-specific and settlement-wide views.
- [x] Add tests for upkeep, production totals, and balance calculations.

## Phase 6: Interactive Map

- [x] Prototype the map renderer with Canvas or PixiJS.
- [x] Add a map page with pan, zoom, and coordinate readout.
- [x] Support the hex grid used by Carta Arcanum maps.
- [x] Add versioned world and detail map image imports for release artifacts.
- [ ] Model map overlay records for territories, borders, settlements, landmarks,
  points of interest, routes, and event markers.
- [ ] Link map overlay records to ownership/faction data where applicable.
- [ ] Add territory and faction-control overlays.
- [ ] Add settlement, landmark, and point-of-interest overlays.
- [ ] Add player-owned building markers for map-visible assets.
- [ ] Add overlay toggles for territory, settlements, buildings, routes, and events.
- [ ] Respect visibility permissions in map data.

## Phase 7: Progression Tracker

- [ ] Model phase-based progression.
- [ ] Track current phase.
- [ ] Show phase requirements and unlocks.
- [ ] Show what is missing to reach the next phase.

## Phase 8: Dependency Solver

- [x] Let denizens select a desired output.
- [x] Calculate required buildings and inputs.
- [x] Generate the full dependency chain.
- [ ] Add minimal stable loop generation.
- [ ] Add resource balancing suggestions.
- [x] Add solver result tests for known scenarios.

## Later Ideas

- [ ] Expand admin maintenance dashboards with deeper rules import, migration,
  backup, and restore guidance.
- [ ] Add an optional production WSGI service helper for running Carta Arcanum
  beyond the temporary test-server unit.
- [ ] Scenario save/load.
- [ ] Multiple campaigns or worlds.
- [ ] Owner/faction filters.
- [ ] Export planning reports.
- [ ] Compare two plans side by side.
- [ ] Prototype PixiJS rendering if Canvas performance or interaction
  complexity needs WebGL acceleration.
