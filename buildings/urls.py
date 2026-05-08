from django.urls import path

from buildings import views

app_name = "buildings"

urlpatterns = [
    path("", views.index, name="index"),
    path("new/", views.create, name="create"),
    path("<int:building_id>/edit/", views.edit, name="edit"),
    path("<int:building_id>/delete/", views.delete, name="delete"),
]
