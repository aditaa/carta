from django.contrib import messages
from django.contrib.auth import get_user_model, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, PasswordResetView
from django.core.mail import get_connection, send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.bug_reports import bug_report_diagnostics, bug_report_issue_url
from accounts.forms import (
    AdminPasswordChangeForm,
    ApplicationSettingForm,
    BugReportForm,
    DenizenProfileStatusForm,
    EmailAuthenticationForm,
    FirstAdminCreationForm,
    HouseForm,
    HouseMembershipAccessFormSet,
    KingdomForm,
    KingdomMembershipAccessFormSet,
    ManagedUserCreationForm,
    MembershipInvitationForm,
    OwnPasswordChangeForm,
    UserAccessForm,
)
from accounts.models import (
    ApplicationSetting,
    AuditLogEntry,
    DenizenProfile,
    MembershipInvitation,
)
from accounts.permissions import AuditAction
from accounts.services import (
    application_setting_map,
    can_manage_user,
    changed_fields,
    ensure_default_application_settings,
    git_changed_files,
    log_audit,
    manageable_user_queryset,
    model_snapshot,
    reset_git_checkout,
    restore_git_file,
    start_upgrade_job,
    status_health_checks,
    upgrade_available,
    upgrade_job_status,
    validate_email_settings,
    validate_release_branch,
)
from buildings.models import OwnedBuilding
from holdings.models import HoldingAccount
from ownership.models import House, HouseMembership, Kingdom, KingdomMembership


def _is_superuser(user) -> bool:
    return user.is_authenticated and user.is_active and user.is_superuser


def _is_user_manager(user) -> bool:
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return (
        HouseMembership.objects.filter(user=user, active=True, role="admin").exists()
        or KingdomMembership.objects.filter(user=user, active=True, role="admin").exists()
    )


superuser_required = user_passes_test(_is_superuser, login_url="accounts:login")
user_manager_required = user_passes_test(_is_user_manager, login_url="accounts:login")


def _has_house_admin(user) -> bool:
    return (
        user.is_authenticated
        and user.is_active
        and (
            user.is_superuser
            or HouseMembership.objects.filter(user=user, active=True, role="admin").exists()
        )
    )


def _has_kingdom_admin(user) -> bool:
    return (
        user.is_authenticated
        and user.is_active
        and (
            user.is_superuser
            or KingdomMembership.objects.filter(user=user, active=True, role="admin").exists()
        )
    )


house_admin_required = user_passes_test(_has_house_admin, login_url="accounts:login")
kingdom_admin_required = user_passes_test(_has_kingdom_admin, login_url="accounts:login")


class CartaLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_users"] = get_user_model().objects.exists()
        return context


class CartaPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = "/accounts/password/reset/done/"

    def form_valid(self, form):
        email_settings = application_setting_map()
        connection = _email_connection_from_settings(email_settings)
        form.save(
            request=self.request,
            use_https=self.request.is_secure(),
            token_generator=self.token_generator,
            from_email=email_settings.get("email_from_address", ""),
            email_template_name=self.email_template_name,
            subject_template_name=self.subject_template_name,
            html_email_template_name=self.html_email_template_name,
            extra_email_context=self.extra_email_context,
            connection=connection,
        )
        return HttpResponseRedirect(self.get_success_url())


@login_required
def report_bug(request):
    diagnostics = bug_report_diagnostics()
    if request.method == "POST":
        form = BugReportForm(request.POST)
        if form.is_valid():
            return redirect(
                bug_report_issue_url(
                    form.cleaned_data,
                    include_diagnostics=form.cleaned_data["include_diagnostics"],
                )
            )
    else:
        form = BugReportForm(
            initial={
                "title": "Bug report",
                "include_diagnostics": True,
            }
        )
    return render(
        request,
        "accounts/report_bug.html",
        {"form": form, "diagnostics": diagnostics},
    )


def _email_connection_from_settings(email_settings):
    port = email_settings.get("email_port", "25")
    return get_connection(
        backend=email_settings.get(
            "email_backend",
            "django.core.mail.backends.console.EmailBackend",
        ),
        host=email_settings.get("email_host", "localhost"),
        port=int(port) if port.isdigit() else 25,
        username=email_settings.get("email_username", ""),
        password=email_settings.get("email_password", ""),
        use_tls=email_settings.get("email_use_tls", "").lower() == "true",
        use_ssl=email_settings.get("email_use_ssl", "").lower() == "true",
    )


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


@superuser_required
def settings_home(request):
    user_model = get_user_model()
    checks = status_health_checks()
    context = {
        "user_count": user_model.objects.count(),
        "active_user_count": user_model.objects.filter(is_active=True).count(),
        "staff_user_count": user_model.objects.filter(is_staff=True).count(),
        "superuser_count": user_model.objects.filter(is_superuser=True).count(),
        "house_count": House.objects.count(),
        "kingdom_count": Kingdom.objects.count(),
        "active_house_membership_count": HouseMembership.objects.filter(active=True).count(),
        "active_kingdom_membership_count": KingdomMembership.objects.filter(active=True).count(),
        "audit_entry_count": AuditLogEntry.objects.count(),
        "health_checks": checks,
        "all_health_checks_ok": all(check.ok for check in checks),
        "upgrade_available": upgrade_available(),
    }
    return render(request, "accounts/settings_home.html", context)


@superuser_required
def application_status(request):
    ensure_default_application_settings()
    settings_formset_class = modelformset_factory(
        ApplicationSetting,
        form=ApplicationSettingForm,
        extra=0,
    )

    if request.method == "POST":
        formset = settings_formset_class(
            request.POST,
            queryset=ApplicationSetting.objects.all(),
        )
        if formset.is_valid():
            submitted_settings = {
                form.instance.key: form.cleaned_data["value"] for form in formset.forms
            }
            email_validation = validate_email_settings(submitted_settings)
            release_branch_valid, release_branch_error = validate_release_branch(
                submitted_settings.get("release_branch", "")
            )
            validation_errors = list(email_validation.errors)
            if not release_branch_valid:
                validation_errors.append(release_branch_error)
            if validation_errors:
                for error in validation_errors:
                    formset._non_form_errors.append(error)
            else:
                before = dict(ApplicationSetting.objects.values_list("key", "value"))
                formset.save()
                after = dict(ApplicationSetting.objects.values_list("key", "value"))
                log_audit(
                    request.user,
                    AuditAction.APPLICATION_SETTINGS_UPDATED,
                    request.user,
                    {"changes": changed_fields(before, after)},
                )
                messages.success(request, "Application settings updated.")
                return redirect("accounts:application_status")
    else:
        formset = settings_formset_class(queryset=ApplicationSetting.objects.all())

    checks = status_health_checks()
    return render(
        request,
        "accounts/application_status.html",
        {
            "health_checks": checks,
            "all_health_checks_ok": all(check.ok for check in checks),
            "formset": formset,
            "changed_files": git_changed_files(),
            "upgrade_available": upgrade_available(),
        },
    )


@superuser_required
def send_test_email(request):
    if request.method == "POST":
        recipient = request.POST.get("recipient") or request.user.email
        email_settings = application_setting_map()
        try:
            send_mail(
                "Carta Arcanum test email",
                "Carta Arcanum email delivery is configured.",
                email_settings.get("email_from_address", ""),
                [recipient],
                connection=_email_connection_from_settings(email_settings),
            )
        except Exception as exc:
            messages.error(request, f"Test email failed: {exc}")
        else:
            log_audit(
                request.user,
                AuditAction.TEST_EMAIL_SENT,
                request.user,
                {"recipient": recipient},
            )
            messages.success(request, "Test email sent.")
    return redirect("accounts:application_status")


@superuser_required
def start_upgrade(request):
    if request.method != "POST":
        return redirect("accounts:application_status")
    job_id = start_upgrade_job()
    job = upgrade_job_status(job_id)
    action = (
        AuditAction.UPGRADE_REUSED_RUNNING_JOB
        if job.get("message") != "Starting upgrade"
        else AuditAction.UPGRADE_STARTED
    )
    log_audit(request.user, action, request.user, {"job_id": job_id})
    messages.success(request, "Upgrade started.")
    return redirect(reverse("accounts:upgrade_status", args=[job_id]))


@superuser_required
def upgrade_status(request, job_id: str):
    job = upgrade_job_status(job_id)
    if not job:
        return render(
            request,
            "accounts/upgrade_status.html",
            {"job_id": job_id, "job": None},
            status=404,
        )
    if request.headers.get("HX-Request") == "true":
        return render(request, "accounts/_upgrade_status_panel.html", {"job": job})
    return render(request, "accounts/upgrade_status.html", {"job_id": job_id, "job": job})


@superuser_required
def upgrade_status_json(request, job_id: str):
    job = upgrade_job_status(job_id)
    if not job:
        return JsonResponse(
            {"status": "missing", "error": "Upgrade job was not found."},
            status=404,
        )
    return JsonResponse(job)


@superuser_required
def fix_git_file(request):
    if request.method == "POST":
        path = request.POST.get("path", "")
        try:
            restore_git_file(path)
        except Exception as exc:
            messages.error(request, str(exc))
        else:
            log_audit(request.user, AuditAction.GIT_FILE_RESTORED, request.user, {"path": path})
            messages.success(request, f"{path} restored from Git.")
    return redirect("accounts:application_status")


@superuser_required
def reset_git_files(request):
    if request.method == "POST":
        try:
            reset_git_checkout()
        except Exception as exc:
            messages.error(request, str(exc))
        else:
            log_audit(request.user, AuditAction.GIT_CHECKOUT_RESET, request.user)
            messages.success(request, "Git checkout reset to the committed state.")
    return redirect("accounts:application_status")


@superuser_required
def audit_log(request):
    entries = AuditLogEntry.objects.select_related("actor").all().order_by("-created_at")
    page = Paginator(entries, 50).get_page(request.GET.get("page"))
    return render(request, "accounts/audit_log.html", {"page": page})


@superuser_required
def audit_log_detail(request, entry_id):
    entry = get_object_or_404(AuditLogEntry.objects.select_related("actor"), pk=entry_id)
    return render(request, "accounts/audit_log_detail.html", {"entry": entry})


@house_admin_required
def house_admin_list(request):
    houses = (
        House.objects.all()
        if request.user.is_superuser
        else House.objects.filter(
            memberships__user=request.user,
            memberships__active=True,
            memberships__role="admin",
        )
    )
    page = Paginator(houses.distinct().order_by("name"), 50).get_page(request.GET.get("page"))
    return render(request, "accounts/house_admin_list.html", {"page": page})


@house_admin_required
def house_admin_detail(request, house_id):
    houses = (
        House.objects.all()
        if request.user.is_superuser
        else House.objects.filter(
            memberships__user=request.user,
            memberships__active=True,
            memberships__role="admin",
        )
    )
    house = get_object_or_404(houses, pk=house_id)
    if request.method == "POST":
        before = model_snapshot(house, ("key", "name", "description", "kingdom_id"))
        form = HouseForm(request.POST, instance=house)
        if form.is_valid():
            form.save()
            after = model_snapshot(house, ("key", "name", "description", "kingdom_id"))
            log_audit(
                request.user,
                AuditAction.HOUSE_UPDATED,
                house,
                {"changes": changed_fields(before, after)},
            )
            messages.success(request, "House updated.")
            return redirect(reverse("accounts:house_admin_detail", args=[house.id]))
    else:
        form = HouseForm(instance=house)
    context = {
        "house": house,
        "form": form,
        "members": house.memberships.select_related("user"),
        "pending_invitations": house.membership_invitations.filter(
            status=MembershipInvitation.Status.PENDING
        ),
        "building_count": OwnedBuilding.objects.filter(house=house).count(),
        "holding_count": HoldingAccount.objects.filter(house=house).count(),
    }
    return render(request, "accounts/house_admin_detail.html", context)


@kingdom_admin_required
def kingdom_admin_list(request):
    kingdoms = (
        Kingdom.objects.all()
        if request.user.is_superuser
        else Kingdom.objects.filter(
            memberships__user=request.user,
            memberships__active=True,
            memberships__role="admin",
        )
    )
    page = Paginator(kingdoms.distinct().order_by("name"), 50).get_page(request.GET.get("page"))
    return render(request, "accounts/kingdom_admin_list.html", {"page": page})


@kingdom_admin_required
def kingdom_admin_detail(request, kingdom_id):
    kingdoms = (
        Kingdom.objects.all()
        if request.user.is_superuser
        else Kingdom.objects.filter(
            memberships__user=request.user,
            memberships__active=True,
            memberships__role="admin",
        )
    )
    kingdom = get_object_or_404(kingdoms, pk=kingdom_id)
    if request.method == "POST":
        before = model_snapshot(kingdom, ("key", "name", "description"))
        form = KingdomForm(request.POST, instance=kingdom)
        if form.is_valid():
            form.save()
            after = model_snapshot(kingdom, ("key", "name", "description"))
            log_audit(
                request.user,
                AuditAction.KINGDOM_UPDATED,
                kingdom,
                {"changes": changed_fields(before, after)},
            )
            messages.success(request, "Kingdom updated.")
            return redirect(reverse("accounts:kingdom_admin_detail", args=[kingdom.id]))
    else:
        form = KingdomForm(instance=kingdom)
    context = {
        "kingdom": kingdom,
        "form": form,
        "members": kingdom.memberships.select_related("user"),
        "houses": kingdom.houses.all(),
        "pending_invitations": kingdom.membership_invitations.filter(
            status=MembershipInvitation.Status.PENDING
        ),
        "building_count": OwnedBuilding.objects.filter(kingdom=kingdom).count(),
        "holding_count": HoldingAccount.objects.filter(kingdom=kingdom).count(),
    }
    return render(request, "accounts/kingdom_admin_detail.html", context)


@user_manager_required
def user_access_list(request):
    users = (
        manageable_user_queryset(request.user)
        .annotate(
            house_acl_count=Count("house_memberships", filter=Q(house_memberships__active=True)),
            kingdom_acl_count=Count(
                "kingdom_memberships",
                filter=Q(kingdom_memberships__active=True),
            ),
        )
        .order_by("email")
    )
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "active")
    staff_filter = request.GET.get("staff", "")
    if query:
        users = users.filter(
            Q(email__icontains=query)
            | Q(display_name__icontains=query)
            | Q(denizen_profile__character_name__icontains=query)
        )
    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)
    if staff_filter == "staff":
        users = users.filter(is_staff=True)
    elif staff_filter == "standard":
        users = users.filter(is_staff=False, is_superuser=False)

    page = Paginator(users, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "accounts/user_access_list.html",
        {
            "page": page,
            "query": query,
            "status_filter": status_filter,
            "staff_filter": staff_filter,
            "can_add_users": request.user.is_superuser,
        },
    )


@user_manager_required
def cancel_invitation(request, invitation_id):
    invitation = get_object_or_404(
        MembershipInvitation,
        pk=invitation_id,
        status=MembershipInvitation.Status.PENDING,
    )
    if not request.user.is_superuser:
        allowed = False
        if invitation.house_id:
            allowed = HouseMembership.objects.filter(
                user=request.user,
                house=invitation.house,
                role="admin",
                active=True,
            ).exists()
        if invitation.kingdom_id:
            allowed = KingdomMembership.objects.filter(
                user=request.user,
                kingdom=invitation.kingdom,
                role="admin",
                active=True,
            ).exists()
        if not allowed:
            return redirect("accounts:user_access_list")
    if request.method == "POST":
        invitation.status = MembershipInvitation.Status.CANCELLED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at"])
        log_audit(
            request.user,
            AuditAction.MEMBERSHIP_INVITATION_CANCELLED,
            invitation,
            {"target": invitation.target_label},
        )
        messages.success(request, "Invitation cancelled.")
    return redirect("accounts:invite_user")


@user_manager_required
def invite_user(request):
    if request.method == "POST":
        form = MembershipInvitationForm(request.POST, manager=request.user)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.inviter = request.user
            invitation.save()
            log_audit(
                request.user,
                AuditAction.MEMBERSHIP_INVITATION_CREATED,
                invitation,
                {"invitee": str(invitation.invitee), "target": invitation.target_label},
            )
            messages.success(request, "Invitation created.")
            return redirect("accounts:user_access_list")
    else:
        form = MembershipInvitationForm(manager=request.user)
    pending_invitations = MembershipInvitation.objects.filter(
        status=MembershipInvitation.Status.PENDING
    )
    if not request.user.is_superuser:
        house_ids = form.fields["house"].queryset.values("id")
        kingdom_ids = form.fields["kingdom"].queryset.values("id")
        pending_invitations = pending_invitations.filter(
            Q(house_id__in=house_ids) | Q(kingdom_id__in=kingdom_ids)
        )
    return render(
        request,
        "accounts/invite_user.html",
        {"form": form, "pending_invitations": pending_invitations},
    )


@user_manager_required
def user_create(request):
    if request.method == "POST":
        form = ManagedUserCreationForm(request.POST)
        forms_are_valid = form.is_valid()
        if forms_are_valid and not request.user.is_superuser:
            if (
                form.cleaned_data["is_staff"]
                or form.cleaned_data["is_superuser"]
                or form.cleaned_data["groups"]
                or form.cleaned_data["user_permissions"]
            ):
                form.add_error(None, "Only superusers can grant platform permissions.")
                forms_are_valid = False
        if forms_are_valid:
            user = form.save()
            DenizenProfile.objects.get_or_create(user=user)
            log_audit(
                request.user,
                AuditAction.USER_CREATED,
                user,
                {"is_active": user.is_active, "is_staff": user.is_staff},
            )
            messages.success(request, "User created.")
            return redirect(reverse("accounts:user_access_detail", args=[user.pk]))
    else:
        form = ManagedUserCreationForm()

    return render(request, "accounts/user_create.html", {"form": form})


@user_manager_required
def user_access_detail(request, user_id):
    target_user = get_object_or_404(manageable_user_queryset(request.user), pk=user_id)
    profile, _ = DenizenProfile.objects.get_or_create(user=target_user)

    if request.method == "POST":
        before_user = model_snapshot(
            target_user,
            ("email", "display_name", "is_active", "is_staff", "is_superuser"),
        )
        before_profile = model_snapshot(
            profile,
            ("character_name", "pronouns", "contact", "status", "system_account", "religion"),
        )
        access_form = UserAccessForm(request.POST, instance=target_user)
        profile_form = DenizenProfileStatusForm(request.POST, instance=profile)
        house_formset = HouseMembershipAccessFormSet(
            request.POST,
            instance=target_user,
            prefix="houses",
        )
        kingdom_formset = KingdomMembershipAccessFormSet(
            request.POST,
            instance=target_user,
            prefix="kingdoms",
        )

        forms_are_valid = all(
            [
                access_form.is_valid(),
                profile_form.is_valid(),
                house_formset.is_valid(),
                kingdom_formset.is_valid(),
            ]
        )
        if forms_are_valid and target_user.pk == request.user.pk:
            if not access_form.cleaned_data["is_active"]:
                access_form.add_error("is_active", "You cannot deactivate your own account.")
                forms_are_valid = False
            if not access_form.cleaned_data["is_staff"]:
                access_form.add_error("is_staff", "You cannot remove your own settings access.")
                forms_are_valid = False
            if not access_form.cleaned_data["is_superuser"] and request.user.is_superuser:
                access_form.add_error(
                    "is_superuser",
                    "You cannot remove your own superuser status here.",
                )
                forms_are_valid = False
        if forms_are_valid and not request.user.is_superuser:
            if (
                access_form.cleaned_data["is_staff"]
                or access_form.cleaned_data["is_superuser"]
                or access_form.cleaned_data["groups"]
                or access_form.cleaned_data["user_permissions"]
                or access_form.cleaned_data["role_preset"]
            ):
                access_form.add_error(None, "Only superusers can grant platform permissions.")
                forms_are_valid = False
            admin_house_ids = set(
                HouseMembership.objects.filter(
                    user=request.user,
                    active=True,
                    role="admin",
                ).values_list("house_id", flat=True)
            )
            admin_kingdom_ids = set(
                KingdomMembership.objects.filter(
                    user=request.user,
                    active=True,
                    role="admin",
                ).values_list("kingdom_id", flat=True)
            )
            for form in house_formset.forms:
                if form.cleaned_data.get("DELETE"):
                    continue
                house = form.cleaned_data.get("house")
                if house and house.id not in admin_house_ids:
                    form.add_error("house", "You can only manage memberships for your houses.")
                    forms_are_valid = False
            for form in kingdom_formset.forms:
                if form.cleaned_data.get("DELETE"):
                    continue
                kingdom = form.cleaned_data.get("kingdom")
                if kingdom and kingdom.id not in admin_kingdom_ids:
                    form.add_error(
                        "kingdom",
                        "You can only manage memberships for your kingdoms.",
                    )
                    forms_are_valid = False

        if forms_are_valid:
            with transaction.atomic():
                access_form.save()
                profile_form.save()
                house_formset.save()
                kingdom_formset.save()
                after_user = model_snapshot(
                    target_user,
                    ("email", "display_name", "is_active", "is_staff", "is_superuser"),
                )
                after_profile = model_snapshot(
                    profile,
                    (
                        "character_name",
                        "pronouns",
                        "contact",
                        "status",
                        "system_account",
                        "religion",
                    ),
                )
                log_audit(
                    request.user,
                    AuditAction.USER_ACCESS_UPDATED,
                    target_user,
                    {
                        "user_changes": changed_fields(before_user, after_user),
                        "profile_changes": changed_fields(before_profile, after_profile),
                    },
                )
            messages.success(request, "User access settings updated.")
            return redirect(reverse("accounts:user_access_detail", args=[target_user.pk]))
    else:
        access_form = UserAccessForm(instance=target_user)
        profile_form = DenizenProfileStatusForm(instance=profile)
        house_formset = HouseMembershipAccessFormSet(instance=target_user, prefix="houses")
        kingdom_formset = KingdomMembershipAccessFormSet(instance=target_user, prefix="kingdoms")

    context = {
        "target_user": target_user,
        "access_form": access_form,
        "profile_form": profile_form,
        "house_formset": house_formset,
        "kingdom_formset": kingdom_formset,
        "effective_permissions": sorted(target_user.get_all_permissions()),
    }
    return render(request, "accounts/user_access_detail.html", context)


@user_manager_required
def user_delete(request, user_id):
    target_user = get_object_or_404(manageable_user_queryset(request.user), pk=user_id)
    related_counts = {
        "house_memberships": target_user.house_memberships.count(),
        "kingdom_memberships": target_user.kingdom_memberships.count(),
        "owned_buildings": OwnedBuilding.objects.filter(user=target_user).count(),
        "holding_accounts": HoldingAccount.objects.filter(user=target_user).count(),
    }

    if request.method == "POST":
        if target_user.pk == request.user.pk:
            messages.error(request, "You cannot disable your own account.")
            return redirect(reverse("accounts:user_access_detail", args=[target_user.pk]))

        display_name = target_user.display_name
        target_user.is_active = False
        target_user.save(update_fields=["is_active"])
        DenizenProfile.objects.filter(user=target_user).update(
            status=DenizenProfile.Status.INACTIVE
        )
        log_audit(
            request.user,
            AuditAction.USER_DISABLED,
            target_user,
            {"changes": {"is_active": {"old": True, "new": False}}},
        )
        messages.success(request, f"{display_name} was disabled.")
        return redirect("accounts:user_access_list")

    return render(
        request,
        "accounts/user_confirm_delete.html",
        {"target_user": target_user, "related_counts": related_counts},
    )


@user_manager_required
def user_enable(request, user_id):
    target_user = get_object_or_404(manageable_user_queryset(request.user), pk=user_id)
    if request.method == "POST":
        target_user.is_active = True
        target_user.save(update_fields=["is_active"])
        DenizenProfile.objects.filter(user=target_user).update(status=DenizenProfile.Status.ACTIVE)
        log_audit(
            request.user,
            AuditAction.USER_ENABLED,
            target_user,
            {"changes": {"is_active": {"old": False, "new": True}}},
        )
        messages.success(request, f"{target_user.display_name} was enabled.")
    return redirect(reverse("accounts:user_access_detail", args=[target_user.pk]))


@user_manager_required
def remove_house_membership(request, membership_id):
    membership = get_object_or_404(HouseMembership, pk=membership_id)
    if (
        not request.user.is_superuser
        and not HouseMembership.objects.filter(
            user=request.user,
            house=membership.house,
            role="admin",
            active=True,
        ).exists()
    ):
        return redirect("accounts:user_access_list")
    if request.method == "POST":
        membership.active = False
        membership.save(update_fields=["active"])
        log_audit(
            request.user,
            AuditAction.HOUSE_MEMBERSHIP_REMOVED,
            membership.user,
            {"house": str(membership.house)},
        )
        messages.success(request, "House membership removed.")
    return redirect(reverse("accounts:user_access_detail", args=[membership.user_id]))


@user_manager_required
def remove_kingdom_membership(request, membership_id):
    membership = get_object_or_404(KingdomMembership, pk=membership_id)
    if (
        not request.user.is_superuser
        and not KingdomMembership.objects.filter(
            user=request.user,
            kingdom=membership.kingdom,
            role="admin",
            active=True,
        ).exists()
    ):
        return redirect("accounts:user_access_list")
    if request.method == "POST":
        membership.active = False
        membership.save(update_fields=["active"])
        log_audit(
            request.user,
            AuditAction.KINGDOM_MEMBERSHIP_REMOVED,
            membership.user,
            {"kingdom": str(membership.kingdom)},
        )
        messages.success(request, "Kingdom membership removed.")
    return redirect(reverse("accounts:user_access_detail", args=[membership.user_id]))


@login_required(login_url="accounts:login")
def change_own_password(request):
    if request.method == "POST":
        form = OwnPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            log_audit(request.user, AuditAction.OWN_PASSWORD_CHANGED, request.user)
            messages.success(request, "Password changed.")
            return redirect("dashboard:home")
    else:
        form = OwnPasswordChangeForm(request.user)
    return render(request, "accounts/password_change.html", {"form": form})


@user_manager_required
def admin_change_password(request, user_id):
    target_user = get_object_or_404(manageable_user_queryset(request.user), pk=user_id)
    if not can_manage_user(request.user, target_user):
        return redirect("accounts:user_access_list")
    if request.method == "POST":
        form = AdminPasswordChangeForm(target_user, request.POST)
        if form.is_valid():
            form.save()
            log_audit(request.user, AuditAction.USER_PASSWORD_CHANGED, target_user)
            messages.success(request, "Password updated.")
            return redirect(reverse("accounts:user_access_detail", args=[target_user.pk]))
    else:
        form = AdminPasswordChangeForm(target_user)
    return render(
        request,
        "accounts/admin_password_change.html",
        {"form": form, "target_user": target_user},
    )


@login_required(login_url="accounts:login")
def my_invitations(request):
    invitations = MembershipInvitation.objects.filter(
        invitee=request.user,
        status=MembershipInvitation.Status.PENDING,
    )
    return render(request, "accounts/my_invitations.html", {"invitations": invitations})


@login_required(login_url="accounts:login")
def respond_to_invitation(request, invitation_id):
    invitation = get_object_or_404(
        MembershipInvitation,
        pk=invitation_id,
        invitee=request.user,
        status=MembershipInvitation.Status.PENDING,
    )
    if request.method != "POST":
        return redirect("accounts:my_invitations")

    response = request.POST.get("response")
    if response == "accept":
        if invitation.house_id:
            if (
                HouseMembership.objects.filter(user=request.user, active=True)
                .exclude(house=invitation.house)
                .exists()
            ):
                messages.error(request, "You already belong to another house.")
                return redirect("accounts:my_invitations")
            membership, _ = HouseMembership.objects.get_or_create(
                user=request.user,
                house=invitation.house,
                defaults={"role": invitation.role, "active": True},
            )
        else:
            if (
                KingdomMembership.objects.filter(user=request.user, active=True)
                .exclude(kingdom=invitation.kingdom)
                .exists()
            ):
                messages.error(request, "You already belong to another kingdom.")
                return redirect("accounts:my_invitations")
            membership, _ = KingdomMembership.objects.get_or_create(
                user=request.user,
                kingdom=invitation.kingdom,
                defaults={"role": invitation.role, "active": True},
            )
        membership.role = invitation.role
        membership.active = True
        membership.save()
        invitation.status = MembershipInvitation.Status.ACCEPTED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at"])
        log_audit(
            request.user,
            AuditAction.MEMBERSHIP_INVITATION_ACCEPTED,
            invitation,
            {"target": invitation.target_label},
        )
        messages.success(request, "Invitation accepted.")
    elif response == "decline":
        invitation.status = MembershipInvitation.Status.DECLINED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at"])
        log_audit(
            request.user,
            AuditAction.MEMBERSHIP_INVITATION_DECLINED,
            invitation,
            {"target": invitation.target_label},
        )
        messages.success(request, "Invitation declined.")
    return redirect("accounts:my_invitations")
