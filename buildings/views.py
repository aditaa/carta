from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from buildings.services import registry_summary, visible_owned_buildings


@login_required
def index(request):
    buildings = visible_owned_buildings(request.user)
    return render(
        request,
        "buildings/index.html",
        {
            "buildings": buildings,
            "summary": registry_summary(buildings),
        },
    )
