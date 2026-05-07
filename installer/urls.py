from django.urls import path

from installer.views import application_setup, database_setup, index

app_name = "installer"

urlpatterns = [
    path("", index, name="index"),
    path("database/", database_setup, name="database"),
    path("application/", application_setup, name="application"),
]
