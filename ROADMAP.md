# Roadmap

This is the high-level todo list for building Carta Arcanum.

## Phase 1: Project Skeleton

- [x] Create FastAPI backend app structure.
- [x] Create React frontend app structure.
- [x] Add shared development commands for running backend and frontend.
- [x] Add MySQL connection configuration.
- [x] Add Linux install guide.
- [x] Add baseline linting and test setup.

## Phase 2: Auth And Permissions

- [x] Create user model and authentication flow foundation.
- [x] Add session or token-based login.
- [x] Define permission scopes for personal data and house data.
- [x] Implement baseline visibility: a user can see their own data.
- [x] Implement house visibility: a user with house permission can see their
  own data plus denizens and assets in that house.
- [x] Add personal, house, and kingdom holding models for future affordability
  checks.
- [ ] Add room for future roles such as admin, house manager, or read-only
  member.
- [x] Add tests for permission boundaries.
- [ ] Replace temporary `denizen_id` query parameters with authenticated denizen
  dependencies.
- [ ] Enforce manager/admin write permissions for house and kingdom holdings.

## Phase 3: Rules Dataset

- [ ] Fill `rules/carta-arcanum-2.1.4.rules.json` manually.
- [x] Split currencies and resources into separate arrays.
- [x] Define resources, rarities, and resource categories foundation.
- [x] Define buildings such as farm, shop, market, tower, and future types.
- [x] Define production recipes with inputs and outputs.
- [x] Define upkeep rules per building.
- [ ] Define phases, unlocks, and phase requirements.
- [x] Add backend validation for the rules schema.
- [x] Add SQL import tables for rulesets and linked rule records.
- [x] Add rules import CLI foundation.

## Phase 4: Building Registry

- [x] Create database tables for owners and buildings.
- [x] Track who owns what.
- [x] Track building counts by owner.
- [x] Scope registry views by user and house permissions.
- [x] Add API endpoints for building registry CRUD.
- [x] Build the first frontend registry view.

## Phase 5: Upkeep And Resource Totals

- [x] Auto-calculate upkeep totals across owned buildings.
- [ ] Auto-calculate production totals.
- [ ] Show current deficits and surpluses.
- [ ] Add alerts like "missing X to sustain Y."
- [x] Add tests for upkeep calculations.
- [ ] Add tests for resource balance calculations.

## Phase 6: Production Graph

- [ ] Build backend graph data output for buildings and resources.
- [ ] Render production flow with D3.js.
- [ ] Highlight blocked or missing inputs.
- [ ] Show owner-specific and settlement-wide graph views.
- [ ] Respect user and house visibility permissions in graph data.

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
