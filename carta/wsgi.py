"""WSGI config for Carta Arcanum."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carta.settings")

application = get_wsgi_application()
