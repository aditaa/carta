# Rules Data

This directory stores versioned Carta Arcanum rules data as manually maintained
JSON arrays.

Rules live outside the Django app logic so the game can change without forcing
application code changes. The app should load a selected rules version and
validate it before using it for upkeep totals, production chains, map overlays,
and dependency solving.

## Files

- `carta-arcanum-2.1.4.rules.json`: starter structured rules file for version
  2.1.4.
- `rules.schema.json`: validation schema for rules data.

Reference source material used while maintaining rules data belongs in
`docs/reference/`. The current 2.1.4 PDF source is stored there rather than in
the repository root.

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

Django code should load rules through a dedicated rules service and import them
into SQL with:

```bash
python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
```

The JSON file is the manual source of truth. SQL records are imported from that
file so the app can use linked keys, foreign keys, filtering, and joins.
Current import coverage includes rulesets, currencies, resources, units,
settlement tiers, building definitions, build costs, upkeep requirements,
production recipes, recipe inputs/outputs, ownership rules, transports,
transport build costs, transport repair costs, and transport upkeep.
