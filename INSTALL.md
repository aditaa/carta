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

## Planned Django Quick Start

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

Then run:

```bash
python manage.py migrate
python manage.py import_rules rules/carta-arcanum-2.1.4.rules.json
python manage.py runserver
```

For the guided first-run installer, start the server after installing
dependencies and visit the app URL. The first page redirects to the installer
until setup is complete:

```text
http://127.0.0.1:8000/install/
```

The installer checks prerequisites, validates the MySQL connection, saves local
MySQL settings to `.env.local`, creates the first superuser, runs migrations,
imports the current rules file, and writes `installer.lock` when setup is
complete.

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
ExecStart=/opt/carta/.venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Adjust `User`, `Group`, `WorkingDirectory`, and `DJANGO_ALLOWED_HOSTS` for the
server. Then enable it:

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
