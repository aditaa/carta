from django.contrib.auth.views import LogoutView
from django.urls import path

from accounts.views import CartaLoginView, first_admin_setup

app_name = "accounts"

urlpatterns = [
    path("setup/", first_admin_setup, name="setup"),
    path("login/", CartaLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
