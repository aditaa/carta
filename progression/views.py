from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from progression.services import latest_ruleset, phase_catalog, title_catalog


@login_required
def index(request):
    ruleset = latest_ruleset()
    phases = []
    titles = []
    if ruleset is not None:
        phases = phase_catalog(ruleset)
        titles = title_catalog(ruleset)
    return render(
        request,
        "progression/index.html",
        {
            "ruleset": ruleset,
            "phases": phases,
            "titles": titles,
        },
    )
