from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from buildings.forms import OwnedBuildingForm
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


@login_required
def create(request):
    if request.method == "POST":
        form = OwnedBuildingForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return redirect("buildings:index")
    else:
        form = OwnedBuildingForm(request.user)
    return render(request, "buildings/form.html", {"form": form})
