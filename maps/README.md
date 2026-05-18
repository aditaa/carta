# Campaign Maps

This folder stores source campaign map versions that should travel with the
repository. These are not served directly by the app.

The source map files are intentionally versioned because installs and release
verification need the same canonical campaign assets. As the map library grows,
move these large binary assets to Git LFS so normal clones stay lighter while
release artifacts remain reproducible.

Import a map version into the Django-managed active map records with:

```text
python manage.py import_map maps/known-world/known-world-2026-05-15.jpg --map-version 2026-05-15 --name "Known World" --playable-width 4096
```

Detail maps use the same importer with `--map-type detail` and
`--parent-key known-world`.

When the real-world campaign map changes, add a new source image instead of
overwriting older versions, then import the new image with a new
`--map-version`. The imported runtime copy lives under `MEDIA_ROOT`, which is
intentionally ignored by Git.
