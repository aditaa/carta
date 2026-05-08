from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from holdings.services import visible_holding_accounts


@login_required
def index(request):
    accounts = visible_holding_accounts(request.user).prefetch_related("balances")
    return render(request, "holdings/index.html", {"accounts": accounts})
