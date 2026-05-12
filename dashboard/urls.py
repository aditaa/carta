from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("owners/<str:owner_type>/<int:owner_id>/", views.owner_detail, name="owner_detail"),
    path("health/", views.health, name="health"),
]
