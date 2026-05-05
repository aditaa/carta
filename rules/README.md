# Rules Data

This directory stores versioned Carta Arcanum rules data as manually maintained
JSON arrays.

Rules live outside the backend and frontend so the game can change without
forcing application code changes. The app should load a selected rules version
and validate it before using it for upkeep totals, production chains, graph
generation, and dependency solving.

## Files

- `carta-arcanum-2.1.4.rules.json`: starter structured rules file for version
  2.1.4.
- `rules.schema.json`: validation schema for rules data.

## Dataset Expectations

Each rules file should be edited directly and organized as arrays:

- `currencies`
- `resources`
- `units`
- `settlement_tiers`
- `building_definitions`
- `production_recipes`
- `ownership_rules`
- `transports`
- `titles`
- `phases`

Historical rules files should remain in this directory for compatibility with
saved campaigns or older scenarios.

## App Integration

Backend code should load rules through a dedicated rules service or import them
into SQL with:

```bash
PYTHONPATH=backend python -m app.cli.import_rules rules/carta-arcanum-2.1.4.rules.json
```

The JSON file is the manual source of truth. SQL records are imported from that
file so the app can use linked keys, foreign keys, filtering, and joins.
