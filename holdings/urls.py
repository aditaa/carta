from django.urls import path

from holdings import views

app_name = "holdings"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:account_id>/adjust/", views.adjust, name="adjust"),
]
