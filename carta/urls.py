from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("buildings/", include("buildings.urls")),
    path("holdings/", include("holdings.urls")),
    path("install/", include("installer.urls")),
    path("progression/", include("progression.urls")),
    path("solver/", include("solver.urls")),
    path("", include("dashboard.urls")),
]
