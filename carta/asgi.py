"""ASGI config for Carta Arcanum."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carta.settings")

application = get_asgi_application()
