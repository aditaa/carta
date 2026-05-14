from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    ReadOnlyPasswordHashField,
    SetPasswordForm,
)
from django.forms import inlineformset_factory

from accounts.models import ApplicationSetting, DenizenProfile, MembershipInvitation, User
from ownership.models import House, HouseMembership, Kingdom, KingdomMembership


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "display_name")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class FirstAdminCreationForm(UserCreationForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        user.is_superuser = True
        if commit:
            user.save()
        return user


class ManagedUserCreationForm(UserCreationForm):
    role_preset = forms.ChoiceField(required=False)
    is_active = forms.BooleanField(required=False, initial=True)
    is_staff = forms.BooleanField(required=False)
    is_superuser = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = (
            "email",
            "display_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )
        widgets = {
            "user_permissions": forms.SelectMultiple(attrs={"size": 12}),
            "groups": forms.SelectMultiple(attrs={"size": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.services import role_preset_choices

        self.fields["role_preset"].choices = role_preset_choices()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = self.cleaned_data["is_active"]
        user.is_staff = self.cleaned_data["is_staff"]
        user.is_superuser = self.cleaned_data["is_superuser"]
        if commit:
            user.save()
            self.save_m2m()
            from accounts.services import apply_role_preset

            apply_role_preset(user, self.cleaned_data["role_preset"])
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "display_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )


class UserAccessForm(forms.ModelForm):
    role_preset = forms.ChoiceField(required=False)

    class Meta:
        model = User
        fields = (
            "email",
            "display_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )
        widgets = {
            "user_permissions": forms.SelectMultiple(attrs={"size": 12}),
            "groups": forms.SelectMultiple(attrs={"size": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.services import role_preset_choices

        self.fields["role_preset"].choices = role_preset_choices()

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            from accounts.services import apply_role_preset

            apply_role_preset(user, self.cleaned_data["role_preset"])
        return user


class DenizenProfileStatusForm(forms.ModelForm):
    class Meta:
        model = DenizenProfile
        fields = (
            "character_name",
            "pronouns",
            "contact",
            "status",
            "system_account",
            "religion",
            "profile_note",
        )


class HouseMembershipAccessForm(forms.ModelForm):
    class Meta:
        model = HouseMembership
        fields = ("house", "role", "active")


class KingdomMembershipAccessForm(forms.ModelForm):
    class Meta:
        model = KingdomMembership
        fields = ("kingdom", "role", "active")


class ApplicationSettingForm(forms.ModelForm):
    class Meta:
        model = ApplicationSetting
        fields = ("value",)
        widgets = {"value": forms.Textarea(attrs={"rows": 3})}


class HouseForm(forms.ModelForm):
    class Meta:
        model = House
        fields = ("key", "name", "kingdom", "description")


class KingdomForm(forms.ModelForm):
    class Meta:
        model = Kingdom
        fields = ("key", "name", "description")


class AdminPasswordChangeForm(SetPasswordForm):
    pass


class OwnPasswordChangeForm(PasswordChangeForm):
    pass


class MembershipInvitationForm(forms.ModelForm):
    target_type = forms.ChoiceField(
        choices=(("house", "House"), ("kingdom", "Kingdom")),
        initial="house",
    )

    class Meta:
        model = MembershipInvitation
        fields = ("invitee", "target_type", "house", "kingdom", "role")

    def __init__(self, *args, manager=None, **kwargs):
        super().__init__(*args, **kwargs)
        if manager is None or manager.is_superuser:
            self.fields["invitee"].queryset = User.objects.filter(is_active=True)
            self.fields["house"].queryset = House.objects.all()
            self.fields["kingdom"].queryset = Kingdom.objects.all()
            return
        self.fields["invitee"].queryset = User.objects.filter(
            is_active=True,
            is_staff=False,
            is_superuser=False,
        ).exclude(id=manager.id)
        self.fields["house"].queryset = House.objects.filter(
            memberships__user=manager,
            memberships__active=True,
            memberships__role="admin",
        )
        self.fields["kingdom"].queryset = Kingdom.objects.filter(
            memberships__user=manager,
            memberships__active=True,
            memberships__role="admin",
        )

    def clean(self):
        cleaned_data = super().clean()
        invitee = cleaned_data.get("invitee")
        target_type = cleaned_data.get("target_type")
        house = cleaned_data.get("house")
        kingdom = cleaned_data.get("kingdom")
        if target_type == "house":
            cleaned_data["kingdom"] = None
            if house is None:
                self.add_error("house", "Choose a house.")
            elif invitee:
                if HouseMembership.objects.filter(user=invitee, active=True).exists():
                    self.add_error("invitee", "This user already belongs to a house.")
                if MembershipInvitation.objects.filter(
                    invitee=invitee,
                    house=house,
                    status=MembershipInvitation.Status.PENDING,
                ).exists():
                    self.add_error("invitee", "This user already has a pending house invitation.")
        elif target_type == "kingdom":
            cleaned_data["house"] = None
            if kingdom is None:
                self.add_error("kingdom", "Choose a kingdom.")
            elif invitee:
                if KingdomMembership.objects.filter(user=invitee, active=True).exists():
                    self.add_error("invitee", "This user already belongs to a kingdom.")
                if MembershipInvitation.objects.filter(
                    invitee=invitee,
                    kingdom=kingdom,
                    status=MembershipInvitation.Status.PENDING,
                ).exists():
                    self.add_error(
                        "invitee",
                        "This user already has a pending kingdom invitation.",
                    )
        return cleaned_data

    def save(self, commit=True):
        invitation = super().save(commit=False)
        invitation.house = self.cleaned_data.get("house")
        invitation.kingdom = self.cleaned_data.get("kingdom")
        if commit:
            invitation.save()
        return invitation


HouseMembershipAccessFormSet = inlineformset_factory(
    User,
    HouseMembership,
    form=HouseMembershipAccessForm,
    extra=1,
    can_delete=True,
)

KingdomMembershipAccessFormSet = inlineformset_factory(
    User,
    KingdomMembership,
    form=KingdomMembershipAccessForm,
    extra=1,
    can_delete=True,
)
