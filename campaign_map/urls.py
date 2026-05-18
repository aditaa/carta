from django.urls import path

from campaign_map import views

app_name = "campaign_map"

urlpatterns = [
    path("", views.index, name="index"),
]
