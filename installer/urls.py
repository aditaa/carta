from django.urls import path

from installer.views import application_setup, database_setup, index, superuser_setup

app_name = "installer"

urlpatterns = [
    path("", index, name="index"),
    path("database/", database_setup, name="database"),
    path("superuser/", superuser_setup, name="superuser"),
    path("application/", application_setup, name="application"),
]
