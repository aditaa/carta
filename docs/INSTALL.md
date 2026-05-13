# Install Guide

Carta Arcanum is supported on Linux. If you are developing from Windows, use
WSL with Ubuntu.

## Rewrite Status

Carta Arcanum is being rewritten as a Django monolith. The first Django
skeleton is in place, and the app now includes a working dashboard, building
registry pages, holdings flows, and production balance services.

## System Requirements

- Linux, preferably Ubuntu 22.04 or newer.
- Python 3.11 or newer.
- MySQL 8 or compatible.
- Node.js only if a future map, visualization, or asset pipeline requires it.

## Django Quick Start

From the repository root:

```bash
git clone --branch stable <repository-url> carta
cd carta
sudo apt update
sudo apt install -y python3 python3-venv python3-pip mysql-server
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

If the app will be opened through a DNS name or reverse proxy, edit `.env`
before starting the server. For example:

```text
DJANGO_ALLOWED_HOSTS=carta.golden-blades.com,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=http://carta.golden-blades.com,https://carta.golden-blades.com
```

Restart the app after changing `.env`.

Start MySQL and create the development database/user:

```bash
sudo systemctl enable --now mysql
sudo mysql
```

```sql
CREATE DATABASE IF NOT EXISTS carta_arcanum CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS test_carta_arcanum CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'carta'@'localhost' IDENTIFIED BY 'change-me';
ALTER USER 'carta'@'localhost' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON carta_arcanum.* TO 'carta'@'localhost';
GRANT ALL PRIVILEGES ON test_carta_arcanum.* TO 'carta'@'localhost';
GRANT CREATE, DROP ON *.* TO 'carta'@'localhost';
FLUSH PRIVILEGES;
```

For the guided first-run installer, start the server after installing
dependencies and creating the MySQL database/user:

```bash
python manage.py runserver 0.0.0.0:8000
```

The first page redirects to the installer until setup is complete:

```text
http://127.0.0.1:8000/install/
```

The installer checks prerequisites, validates the MySQL connection, saves local
MySQL settings to `.env.local`, creates the first superuser, runs migrations,
imports the current rules file, and writes `installer.lock` when setup is
complete.

After the first superuser signs in, open `Settings -> Application Status` to
review health checks, editable app settings, email configuration, Git file
status, and upgrade readiness. The broader admin workflow is documented in
[`docs/ADMIN.md`](ADMIN.md).

If you prefer to run setup from the command line instead of the installer:

```bash
python manage.py migrate
python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
python manage.py runserver 0.0.0.0:8000
```

The app should be available at:

```text
http://127.0.0.1:8000
```

## Installer Recovery

The installer locks itself by writing `installer.lock` in the repository root.
That file prevents accidental reruns after the app is live.

If setup must be intentionally rerun, stop the app and remove only the lock
file:

```bash
rm installer.lock
```

Then start the app again and open:

```text
http://127.0.0.1:8000/install/
```

Do not remove `.env.local` unless you want to re-enter the MySQL connection.
Do not drop the MySQL database unless you intend to erase app data and start
over.

If the app cannot create the lock file, make the repository folder writable by
the service user, for example:

```bash
sudo chown -R "$USER":"$USER" /path/to/carta
chmod u+w /path/to/carta
```

If a service user runs the app, use that service user instead of `$USER`.

## Fresh Reinstall

Use this path only when you want to erase the current Carta Arcanum install and
start with a blank book. It removes app data from the MySQL database.

Before wiping anything, stop the app:

```bash
sudo systemctl stop carta
```

If you are running the app manually, stop the `runserver` process with
`Ctrl+C` instead.

Make a backup first:

```bash
mysqldump -u carta -p carta_arcanum > carta_arcanum_backup.sql
cp .env .env.backup
cp .env.local .env.local.backup 2>/dev/null || true
```

Then reset the application database:

```bash
sudo mysql
```

```sql
DROP DATABASE IF EXISTS carta_arcanum;
CREATE DATABASE carta_arcanum CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON carta_arcanum.* TO 'carta'@'localhost';
FLUSH PRIVILEGES;
```

Remove installer state so the guided setup can run again:

```bash
rm -f installer.lock
rm -f .env.local
```

Keep `.env` if the hostname, secret key, and other app settings are still
valid. Remove or edit `.env` only if you intentionally want to reconfigure
those values.

Install current dependencies and restart the app:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 0.0.0.0:8000
```

Open `/install/` and complete the installer again. If you use systemd, start
the service instead:

```bash
sudo systemctl start carta
```

## Upgrade Existing Install

Use this path when you want to keep current data and move to a newer version of
Carta Arcanum.

The in-app upgrade button on `Settings -> Application Status` is the preferred
path for superusers once the server is configured. It expects the install to
track the `stable` branch, treats Git as the source of truth for application
code, resets changed tracked files before upgrading, runs migrations and
`collectstatic`, and runs the configured restart command when one is set.

Use the manual steps below when the web app is unavailable or when you want to
perform the upgrade from a shell.

Stop the app:

```bash
sudo systemctl stop carta
```

If you are running `runserver` manually, stop it with `Ctrl+C`.

Back up the database and local settings:

```bash
mysqldump -u carta -p carta_arcanum > carta_arcanum_pre_upgrade.sql
cp .env .env.pre_upgrade
cp .env.local .env.local.pre_upgrade 2>/dev/null || true
```

Fetch and switch to the release branch or tag you want to run:

```bash
git fetch origin
git checkout stable
git pull --ff-only origin stable
```

Install updated dependencies:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Apply database migrations:

```bash
python manage.py migrate
```

If the release includes a new rules file, import that file after confirming the
version in `rules/`:

```bash
python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
```

Do not remove `installer.lock` during a normal upgrade. Keeping it prevents the
first-run installer from reopening on an existing database.

Run a quick health check:

```bash
python manage.py check
```

Start the app again:

```bash
sudo systemctl start carta
```

For a manual test server, use:

```bash
python manage.py runserver 0.0.0.0:8000
```

If the upgrade fails, stop the app, restore the database backup, restore the
previous checkout, reinstall dependencies, and start the app again.

## Troubleshooting First Start

If `runserver` reports this MySQL authentication error:

```text
'cryptography' package is required for sha256_password or caching_sha2_password auth methods
```

install the current requirements again inside the virtual environment:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

If the checkout is older and `requirements.txt` does not include
`cryptography`, install it directly:

```bash
pip install "cryptography>=42.0,<46.0"
```

During first install, `runserver` may warn that it cannot check database
migrations before MySQL is configured. That warning is expected; open the
installer in the browser and enter the MySQL connection there.

If the browser shows `DisallowedHost`, add the public hostname to
`DJANGO_ALLOWED_HOSTS` in `.env`, then restart the app. For
`carta.golden-blades.com`, use:

```text
DJANGO_ALLOWED_HOSTS=carta.golden-blades.com,127.0.0.1,localhost
```

If installer forms fail CSRF checks through the public hostname, also set:

```text
DJANGO_CSRF_TRUSTED_ORIGINS=http://carta.golden-blades.com,https://carta.golden-blades.com
```

## Optional Service Setup

For a first test install, running `python manage.py runserver 0.0.0.0:8000`
from the repository folder is enough. For a longer-running test server, use a
proper WSGI server later; this temporary systemd unit keeps the development
server running for testers.

Create `/etc/systemd/system/carta.service`:

```ini
[Unit]
Description=Carta Arcanum test server
After=network.target mysql.service

[Service]
Type=simple
User=carta
Group=carta
WorkingDirectory=/opt/carta
Environment=DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,your-server-ip
Environment=DJANGO_CSRF_TRUSTED_ORIGINS=http://your-server-ip,https://your-server-ip
ExecStart=/opt/carta/.venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Adjust `User`, `Group`, `WorkingDirectory`, `DJANGO_ALLOWED_HOSTS`, and
`DJANGO_CSRF_TRUSTED_ORIGINS` for the server. Then enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now carta
sudo systemctl status carta
```

View logs with:

```bash
sudo journalctl -u carta -f
```

## Configuration

Django configuration should be read from environment variables. Keep secrets
and database credentials out of version control. The optional web installer
writes local database settings to `.env.local`, which is ignored by git.

Common local settings are shown in `.env.example`. The Carta-specific settings
are:

- `CARTA_CURRENT_RULES_FILE`: rules JSON imported by the installer.
- `CARTA_INSTALLER_ENV_FILE`: local env file written by the installer.
- `CARTA_INSTALLER_LOCK_FILE`: lock file that prevents accidental installer
  reruns.
- `CARTA_SLOW_QUERY_MS`: optional slow-query logging threshold in milliseconds.
  Set to `0` or leave unset to disable it.

Superusers can also edit database-backed application settings from
`Settings -> Application Status`. These are intended for non-secret operational
values such as the displayed site name, maintenance notice, restart command,
restart-needed flag, and email backend settings.

Email sending can use Django's console backend for development, a local SMTP
relay, a provider SMTP service, or another Django email backend. Linux server
mail often needs extra system configuration, so use the status page's email
test button after changing email settings.

## Future Performance Notes

The admin/settings branch adds indexes for user status filters, audit log
lookups, invitation status filters, and active house/kingdom ACL membership
queries, owned buildings by owner/status, holding accounts by
owner/scope/activity, holding balances by account/item, and holding ledger
lookups. As the app grows, likely future index candidates include deeper
production/rules references, planned event queues, map coordinates, and solver
snapshots. Use slow-query logs and database `EXPLAIN` output before adding those
indexes so the schema follows real usage instead of guesswork.

## Checks

These commands do not require a running MySQL server:

```bash
python -m ruff check .
python -m ruff format --check .
python manage.py check
python -m pytest dashboard/tests tests
```

The full suite uses MySQL because Carta Arcanum targets MySQL from day one:

```bash
python -m pytest
```
