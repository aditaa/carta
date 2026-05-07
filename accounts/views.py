from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from accounts.forms import EmailAuthenticationForm, FirstAdminCreationForm


class CartaLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_users"] = get_user_model().objects.exists()
        return context


def first_admin_setup(request):
    if get_user_model().objects.exists():
        return redirect("accounts:login")

    if request.method == "POST":
        form = FirstAdminCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard:home")
    else:
        form = FirstAdminCreationForm()

    return render(request, "accounts/setup.html", {"form": form})
