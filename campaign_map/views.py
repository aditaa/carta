from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from campaign_map.services import active_maps, selected_map


@login_required
def index(request):
    map_version = selected_map(request.GET.get("map"))
    return render(
        request,
        "campaign_map/index.html",
        {
            "map_version": map_version,
            "map_versions": active_maps(),
        },
    )
