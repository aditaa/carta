from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from rulesets.services import RulesetValidationError, import_rules_file


class Command(BaseCommand):
    help = "Validate and import a Carta Arcanum rules JSON file."

    def add_arguments(self, parser):
        parser.add_argument("rules_file", type=Path)
        parser.add_argument("--schema", type=Path, default=None)

    def handle(self, *args, **options):
        rules_file = options["rules_file"]
        schema_file = options["schema"]

        if not rules_file.exists():
            raise CommandError(f"Rules file does not exist: {rules_file}")
        if schema_file is not None and not schema_file.exists():
            raise CommandError(f"Schema file does not exist: {schema_file}")

        try:
            result = import_rules_file(rules_file, schema_path=schema_file)
        except RulesetValidationError as exc:
            raise CommandError(f"Rules validation failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Imported "
                f"{result.ruleset.game} {result.ruleset.rules_version}: "
                f"{result.currencies} currencies, "
                f"{result.resources} resources, "
                f"{result.units} units."
            )
        )
