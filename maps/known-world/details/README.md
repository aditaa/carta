# Known World Detail Maps

These PNG files are zoomed-in detail views for the Known World campaign map.
They were downloaded from the shared Google Drive folder on 2026-05-15 and
are versioned as `2025-09-20`, matching the Drive modified dates.

Import all detail maps with:

```text
python manage.py import_map maps/known-world/details/hellfire-2025-09-20.png --key hellfire --name "Hellfire" --map-version 2025-09-20 --map-type detail --parent-key known-world
```

Use the same pattern for future real-world map updates: add new files instead
of overwriting old ones, then import each with a new `--map-version`.
