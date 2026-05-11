from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from holdings.forms import HoldingAdjustmentForm, HoldingTransferForm
from holdings.models import HoldingAccount
from holdings.services import editable_holding_accounts, visible_holding_accounts


@login_required
def index(request):
    accounts = visible_holding_accounts(request.user).prefetch_related("balances")
    return render(request, "holdings/index.html", {"accounts": accounts})


@login_required
def detail(request, account_id):
    account = get_visible_account_or_404(request.user, account_id)
    account = (
        HoldingAccount.objects.filter(id=account.id)
        .select_related("user", "house", "kingdom")
        .prefetch_related("balances", "ledger_entries__related_account")
        .get()
    )
    return render(request, "holdings/detail.html", {"account": account})


@login_required
def adjust(request, account_id):
    account = get_editable_account_or_404(request.user, account_id)
    if request.method == "POST":
        form = HoldingAdjustmentForm(request.POST)
        if form.is_valid():
            try:
                form.save(account)
            except ValidationError as error:
                form.add_error(None, error)
            else:
                # Handle HTMX request - return updated account balances
                if request.headers.get("HX-Request"):
                    accounts = visible_holding_accounts(request.user).prefetch_related("balances")
                    return render(request, "holdings/_account_balances.html", {
                        "accounts": accounts,
                        "updated_account_id": account.id
                    })
                return redirect("holdings:index")
    else:
        form = HoldingAdjustmentForm()
    
    # Handle HTMX request for form display
    if request.headers.get("HX-Request"):
        return render(request, "holdings/_adjust_form.html", {
            "account": account, 
            "form": form
        })
    
    return render(
        request,
        "holdings/adjust.html",
        {"account": account, "form": form},
    )


@login_required
def transfer_between_accounts(request, account_id):
    source = get_editable_account_or_404(request.user, account_id)
    destinations = editable_holding_accounts(request.user)
    if request.method == "POST":
        form = HoldingTransferForm(request.POST, source=source, destinations=destinations)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                return redirect("holdings:index")
    else:
        form = HoldingTransferForm(source=source, destinations=destinations)
    return render(
        request,
        "holdings/transfer.html",
        {"source": source, "form": form},
    )


def get_visible_account_or_404(user, account_id) -> HoldingAccount:
    account = get_object_or_404(HoldingAccount, id=account_id)
    if not visible_holding_accounts(user).filter(id=account.id).exists():
        raise Http404
    return account


def get_editable_account_or_404(user, account_id) -> HoldingAccount:
    account = get_object_or_404(HoldingAccount, id=account_id)
    if not editable_holding_accounts(user).filter(id=account.id).exists():
        raise Http404
    return account
