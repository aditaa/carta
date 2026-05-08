from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from holdings.forms import HoldingAdjustmentForm
from holdings.models import HoldingAccount
from holdings.services import visible_holding_accounts


@login_required
def index(request):
    accounts = visible_holding_accounts(request.user).prefetch_related("balances")
    return render(request, "holdings/index.html", {"accounts": accounts})


@login_required
def adjust(request, account_id):
    account = get_visible_account_or_404(request.user, account_id)
    if request.method == "POST":
        form = HoldingAdjustmentForm(request.POST)
        if form.is_valid():
            try:
                form.save(account)
            except ValidationError as error:
                form.add_error(None, error)
            else:
                return redirect("holdings:index")
    else:
        form = HoldingAdjustmentForm()
    return render(
        request,
        "holdings/adjust.html",
        {"account": account, "form": form},
    )


def get_visible_account_or_404(user, account_id) -> HoldingAccount:
    account = get_object_or_404(HoldingAccount, id=account_id)
    if not visible_holding_accounts(user).filter(id=account.id).exists():
        raise Http404
    return account
