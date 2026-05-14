from django.urls import path

from progression import views

app_name = "progression"

urlpatterns = [
    path("", views.index, name="index"),
]
