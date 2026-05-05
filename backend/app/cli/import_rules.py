import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.domains.rules.importer import import_rules_dataset, load_rules_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a Carta Arcanum rules dataset.")
    parser.add_argument("rules_file", type=Path)
    args = parser.parse_args()

    dataset = load_rules_dataset(args.rules_file)
    with SessionLocal() as db:
        ruleset = import_rules_dataset(db, dataset)
    print(f"Imported {ruleset.game} {ruleset.version} as ruleset_id={ruleset.id}")


if __name__ == "__main__":
    main()
