from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from rulesets.models import Ruleset
from solver.forms import SolverTargetForm
from solver.services import solve_required_chain


@login_required
def index(request):
    ruleset = Ruleset.objects.order_by("-imported_at", "-id").first()
    form = SolverTargetForm(ruleset, request.GET or None)
    result = None
    if request.GET and form.is_valid() and ruleset is not None:
        result = solve_required_chain(ruleset=ruleset, target=form.solver_target())
    return render(
        request,
        "solver/index.html",
        {
            "form": form,
            "result": result,
            "ruleset": ruleset,
        },
    )
