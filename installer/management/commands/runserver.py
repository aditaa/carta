from django.contrib.staticfiles.management.commands.runserver import (
    Command as BaseRunserverCommand,
)


class Command(BaseRunserverCommand):
    def check_migrations(self):
        try:
            super().check_migrations()
        except Exception as exc:
            self.stderr.write(
                self.style.WARNING(
                    "Could not check database migrations. If this is a first "
                    "install, continue to the web installer and configure MySQL "
                    f"there. Original error: {exc}"
                )
            )
