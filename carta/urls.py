from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("buildings/", include("buildings.urls")),
    path("map/", include("campaign_map.urls")),
    path("holdings/", include("holdings.urls")),
    path("install/", include("installer.urls")),
    path("progression/", include("progression.urls")),
    path("solver/", include("solver.urls")),
    path("", include("dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
