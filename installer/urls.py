from django.urls import path

from installer.views import (
    application_setup,
    application_setup_status,
    database_setup,
    index,
    superuser_setup,
)

app_name = "installer"

urlpatterns = [
    path("", index, name="index"),
    path("database/", database_setup, name="database"),
    path("superuser/", superuser_setup, name="superuser"),
    path("application/", application_setup, name="application"),
    path("application/status/<str:job_id>/", application_setup_status, name="application_status"),
]
