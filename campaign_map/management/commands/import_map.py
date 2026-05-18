from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from campaign_map.services import CampaignMapImportError, import_campaign_map


class Command(BaseCommand):
    help = "Import a versioned Carta Arcanum campaign map image."

    def add_arguments(self, parser):
        parser.add_argument("map_file", type=Path)
        parser.add_argument("--key", default="known-world")
        parser.add_argument("--name", default="Known World")
        parser.add_argument("--map-version", required=True)
        parser.add_argument("--map-type", choices=["world", "detail"], default="world")
        parser.add_argument("--parent-key", default="")
        parser.add_argument("--playable-width", type=int, default=None)
        parser.add_argument("--hex-size", type=float, default=22)
        parser.add_argument("--hex-origin-x", type=float, default=7)
        parser.add_argument("--hex-origin-y", type=float, default=12)
        parser.add_argument("--notes", default="")
        parser.add_argument("--inactive", action="store_true")

    def handle(self, *args, **options):
        try:
            result = import_campaign_map(
                options["map_file"],
                key=options["key"],
                name=options["name"],
                version=options["map_version"],
                map_type=options["map_type"],
                parent_key=options["parent_key"],
                playable_width=options["playable_width"],
                hex_size=options["hex_size"],
                hex_origin_x=options["hex_origin_x"],
                hex_origin_y=options["hex_origin_y"],
                notes=options["notes"],
                activate=not options["inactive"],
            )
        except CampaignMapImportError as exc:
            raise CommandError(str(exc)) from exc

        action = "Created" if result.created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {result.map_version.name} {result.map_version.version} "
                f"({result.map_version.image_width}x{result.map_version.image_height})."
            )
        )
