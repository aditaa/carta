param(
    [ValidateSet("quick", "full")]
    [string]$Mode = "quick"
)

$ErrorActionPreference = "Stop"

function Invoke-QuickChecks {
    python -m ruff format --check .
    python -m ruff check .
    python manage.py check
    python -m pytest dashboard/tests tests
}

function Invoke-FullChecks {
    python -m ruff format --check .
    python -m ruff check .
    python manage.py check
    python manage.py makemigrations --check --dry-run
    python manage.py migrate --noinput
    python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
    python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
    python -m pytest
}

switch ($Mode) {
    "quick" { Invoke-QuickChecks }
    "full" { Invoke-FullChecks }
}
