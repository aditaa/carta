from django.urls import path

from buildings import views

app_name = "buildings"

urlpatterns = [
    path("", views.index, name="index"),
]
