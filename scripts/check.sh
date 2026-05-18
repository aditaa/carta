#!/usr/bin/env bash
set -euo pipefail

mode="${1:-quick}"

run_quick() {
  python -m ruff format --check .
  python -m ruff check .
  python manage.py check
  python -m pytest dashboard/tests tests
}

run_full() {
  python -m ruff format --check .
  python -m ruff check .
  python manage.py check
  python manage.py makemigrations --check --dry-run
  python manage.py migrate --noinput
  python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
  python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
  python -m pytest
}

case "$mode" in
  quick)
    run_quick
    ;;
  full)
    run_full
    ;;
  *)
    echo "Usage: ./scripts/check.sh [quick|full]" >&2
    exit 2
    ;;
esac
