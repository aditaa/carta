from django.urls import path

from solver import views

app_name = "solver"

urlpatterns = [
    path("", views.index, name="index"),
]
