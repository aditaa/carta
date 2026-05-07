# Roadmap

This is the high-level todo list for rebuilding Carta Arcanum as a Django
monolith. The previous FastAPI and React implementation has been removed and
should not drive the new architecture.

Use `TRANSITION_TODO.md` for the detailed task checklist.

## Phase 0: Rewrite Preparation

- [x] Choose Django monolith architecture.
- [x] Remove uncommitted installer and first-run setup work from the old stack.
- [x] Update planning docs for the Django rewrite.
- [x] Delete the legacy `backend/` and `frontend/` directories before
  scaffolding Django.
- [x] Choose the Django project/app layout and package names.
- [ ] Update CI to target the Django app once the skeleton exists.

## Phase 1: Django Skeleton

- [x] Create the Django project.
- [x] Configure MySQL for supported local and production use.
- [x] Add environment-based settings for secrets, database connection, and
  deployment mode.
- [x] Add Django templates, static files, and base layout.
- [x] Add pytest or Django test runner setup.
- [x] Add linting and formatting checks for the new codebase.
- [x] Update Linux-first install and run documentation.

## Phase 2: Rulesets

- [ ] Keep versioned rules data in `rules/`.
- [ ] Port rules schema validation into the Django app.
- [ ] Model imported rulesets, resources, currencies, units, buildings,
  recipes, upkeep requirements, phases, and unlocks.
- [ ] Add a Django management command to import a rules file.
- [ ] Add admin views for inspecting imported rules.
- [ ] Add tests for validation and import behavior.

## Phase 3: Accounts And Visibility

- [ ] Define the user, denizen profile, system account, house, and kingdom
  model strategy.
- [ ] Use Django auth and sessions for login.
- [ ] Model roles, memberships, and scoped permissions.
- [ ] Implement personal, house, kingdom, and Three Crowns visibility rules.
- [ ] Add tests for permission boundaries.

## Phase 4: Core Web Workflows

- [ ] Build the dashboard shell with Django templates.
- [ ] Add building registry pages.
- [ ] Add holdings pages for denizens, houses, kingdoms, and Three Crowns.
- [ ] Use HTMX for filters, inline edits, form submissions, and preview panels.
- [ ] Add audit-friendly create/update/delete behavior.

## Phase 5: Production And Balancing

- [ ] Auto-calculate upkeep totals across owned buildings.
- [ ] Auto-calculate production totals.
- [ ] Show current deficits and surpluses.
- [ ] Add alerts like "missing X to sustain Y."
- [ ] Add tests for upkeep, production totals, and balance calculations.

## Phase 6: Production Graph

- [ ] Build graph data from Django domain services.
- [ ] Render production flow with D3.js.
- [ ] Highlight blocked or missing inputs.
- [ ] Show owner-specific and settlement-wide graph views.
- [ ] Respect visibility permissions in graph data.

## Phase 7: Progression Tracker

- [ ] Model phase-based progression.
- [ ] Track current phase.
- [ ] Show phase requirements and unlocks.
- [ ] Show what is missing to reach the next phase.

## Phase 8: Dependency Solver

- [ ] Let denizens select a desired output.
- [ ] Calculate required buildings and inputs.
- [ ] Generate the full dependency chain.
- [ ] Add minimal stable loop generation.
- [ ] Add resource balancing suggestions.
- [ ] Add solver result tests for known scenarios.

## Later Ideas

- [ ] Scenario save/load.
- [ ] Multiple campaigns or worlds.
- [ ] Owner/faction filters.
- [ ] Export planning reports.
- [ ] Compare two plans side by side.
