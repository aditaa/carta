from django import forms


class InstallerSuperUserForm(forms.Form):
    email = forms.EmailField()
    display_name = forms.CharField(max_length=150)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def session_payload(self) -> dict[str, str]:
        return {
            "email": self.cleaned_data["email"],
            "display_name": self.cleaned_data["display_name"],
            "password": self.cleaned_data["password1"],
        }


class DatabaseConfigForm(forms.Form):
    host = forms.CharField(max_length=255, initial="127.0.0.1")
    port = forms.IntegerField(min_value=1, max_value=65535, initial=3306)
    database = forms.CharField(max_length=120, initial="carta_arcanum")
    test_database = forms.CharField(max_length=120, initial="test_carta_arcanum")
    user = forms.CharField(max_length=120, initial="carta")
    password = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(render_value=True),
    )

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ("host", "database", "test_database", "user", "password"):
            value = cleaned_data.get(field_name)
            if isinstance(value, str) and any(character in value for character in "\r\n"):
                self.add_error(field_name, "This value cannot contain line breaks.")
        return cleaned_data
